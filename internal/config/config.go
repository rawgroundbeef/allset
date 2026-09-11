// Package config owns the explicit project registry, separate from credentials and runtime state.
package config

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

const MaxBytes = 1 << 20

var ErrUnregistered = errors.New("this repository is not configured; run allset init")

var identifier = regexp.MustCompile(`^[a-z0-9][a-z0-9-]{0,62}$`)
var reserved = map[string]bool{"help": true, "version": true, "projects": true, "backends": true, "init": true, "mcp": true, "config": true, "open": true, "resume": true, "connect": true, "status": true, "doctor": true, "login": true, "stop": true, "collect": true}

type File struct {
	Schema   string    `json:"$schema,omitempty"`
	Version  int       `json:"version"`
	Projects []Project `json:"projects"`
}

// Project declares a repository and compute service. The caller owns its terminal.
// Credentials and observed runtime state belong outside this registration.
type Project struct {
	Name               string                     `json:"name"`
	Aliases            []string                   `json:"aliases,omitempty"`
	Repository         string                     `json:"repository"`
	Backend            string                     `json:"backend"`
	MCPs               map[string]MCP             `json:"mcps,omitzero"`
	Skills             map[string]Skill           `json:"skills,omitzero"`
	SessionEnvironment map[string]SessionVariable `json:"session_environment,omitzero"`
}

func ValidID(s string) bool { return identifier.MatchString(s) }

// RepositoryKey normalizes equivalent Git SSH/HTTPS addresses without accepting embedded credentials.
func RepositoryKey(s string) (string, error) {
	s = strings.TrimSpace(s)
	if strings.HasPrefix(s, "git@") && !strings.Contains(s, "://") {
		parts := strings.SplitN(strings.TrimPrefix(s, "git@"), ":", 2)
		if len(parts) != 2 {
			return "", errors.New("repository SSH address requires a host and path")
		}
		s = "https://" + parts[0] + "/" + parts[1]
	}
	if !strings.Contains(s, "://") {
		parts := strings.Split(s, "/")
		if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
			return "", errors.New("repository must be owner/repo or an SSH/HTTPS URL")
		}
		s = "https://github.com/" + s
	}
	u, err := url.Parse(s)
	if err != nil || u.Hostname() == "" || (u.Scheme != "https" && u.Scheme != "ssh") {
		return "", errors.New("repository must be an SSH/HTTPS URL")
	}
	if u.RawQuery != "" || u.Fragment != "" || (u.User != nil && !(u.Scheme == "ssh" && u.User.String() == "git")) {
		return "", errors.New("repository URL must not include credentials, query parameters, or fragments")
	}
	path := strings.TrimSuffix(strings.Trim(u.Path, "/"), ".git")
	if path == "" || strings.ContainsAny(path, "\x00\r\n\t ") || strings.ContainsAny(u.Host, "\x00\r\n\t ") {
		return "", errors.New("repository address is invalid")
	}
	for _, part := range strings.Split(path, "/") {
		if part == "" || part == "." || part == ".." {
			return "", errors.New("repository path is invalid")
		}
	}
	key := strings.ToLower(u.Host) + "/" + path
	if strings.EqualFold(u.Host, "github.com") {
		key = strings.ToLower(key)
	}
	return key, nil
}

func (f File) Validate() error {
	if f.Schema != "" && f.Schema != "registry.schema.json" && f.Schema != "./registry.schema.json" {
		return errors.New("$schema must reference the local registry.schema.json exported by allset config schema")
	}
	if f.Version != 3 {
		return errors.New("unsupported registry version; expected 3")
	}
	if f.Projects == nil {
		return errors.New("projects must be an array; use an empty array for no registrations")
	}
	names, repositories := map[string]bool{}, map[string]bool{}
	for _, p := range f.Projects {
		if err := ValidateMCPs(p.MCPs); err != nil {
			return err
		}
		if err := ValidateSessionRequirements(p.Skills, p.SessionEnvironment, p.MCPs); err != nil {
			return err
		}
		if !ValidID(p.Backend) || p.Backend == "box-herdr" {
			return errors.New("backend must identify a compute service; use box for the previous installation")
		}
		for _, name := range append([]string{p.Name}, p.Aliases...) {
			if !ValidID(name) || reserved[name] {
				return errors.New("project names and aliases must be lowercase identifiers, not command names")
			}
			if names[name] {
				return fmt.Errorf("duplicate project name or alias: %s", name)
			}
			names[name] = true
		}
		key, err := RepositoryKey(p.Repository)
		if err != nil {
			return fmt.Errorf("project %s: %w", p.Name, err)
		}
		if repositories[key] {
			return errors.New("multiple projects bind the same repository; repository inference would be ambiguous")
		}
		repositories[key] = true
	}
	return nil
}

// unique rejects duplicate JSON keys, including nested keys, before ordinary typed decoding.
func unique(d *json.Decoder, strict bool) error {
	return uniqueValue(d, 0, strict)
}

func uniqueValue(d *json.Decoder, depth int, strict bool) error {
	if depth > 64 {
		return errors.New("JSON nesting exceeds the config limit")
	}
	t, err := d.Token()
	if err != nil {
		return err
	}
	if strict && t == nil {
		return errors.New("null is not a supported registry value")
	}
	delim, ok := t.(json.Delim)
	if !ok {
		return nil
	}
	switch delim {
	case '{':
		seen := map[string]bool{}
		for d.More() {
			key, err := d.Token()
			if err != nil {
				return err
			}
			s, ok := key.(string)
			if !ok {
				return errors.New("invalid object key")
			}
			if seen[s] {
				return errors.New("duplicate JSON field")
			}
			seen[s] = true
			if err := uniqueValue(d, depth+1, strict); err != nil {
				return err
			}
		}
	case '[':
		for d.More() {
			if err := uniqueValue(d, depth+1, strict); err != nil {
				return err
			}
		}
	default:
		return errors.New("invalid JSON delimiter")
	}
	_, err = d.Token()
	return err
}

func Decode(b []byte, target any, strict bool) error {
	if len(b) > MaxBytes {
		return errors.New("JSON document exceeds 1 MiB")
	}
	d := json.NewDecoder(bytes.NewReader(b))
	if err := unique(d, strict); err != nil {
		return errors.New("invalid JSON or duplicate fields")
	}
	if _, err := d.Token(); err != io.EOF {
		return errors.New("expected exactly one JSON document")
	}
	d = json.NewDecoder(bytes.NewReader(b))
	if strict {
		d.DisallowUnknownFields()
	}
	if err := d.Decode(target); err != nil {
		return errors.New("JSON fields or types do not match the supported schema")
	}
	return nil
}

func readDocument(path string) ([]byte, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return io.ReadAll(io.LimitReader(f, MaxBytes+1))
}

func ReadJSON(path string, target any, strict bool) error {
	b, err := readDocument(path)
	if err != nil {
		return err
	}
	return Decode(b, target, strict)
}

func Load(path string) (File, error) {
	// Historical terminal preferences are accepted only in historical documents.
	// They never become a requirement of a project or leak into new config output.
	b, err := readDocument(path)
	if err != nil {
		return File{}, err
	}
	var raw struct {
		Version int `json:"version"`
	}
	if err := Decode(b, &raw, false); err != nil {
		return File{}, err
	}
	if raw.Version == 1 || raw.Version == 2 {
		var old struct {
			Schema   string `json:"$schema,omitempty"`
			Version  int    `json:"version"`
			Projects []struct {
				Project
				Terminal *string `json:"terminal,omitempty"`
			} `json:"projects"`
		}
		if err := Decode(b, &old, true); err != nil {
			return File{}, err
		}
		f := File{Schema: old.Schema, Version: 3}
		if old.Projects != nil {
			f.Projects = []Project{}
		}
		for _, item := range old.Projects {
			p := item.Project
			if old.Version == 1 {
				if p.Backend != "box-herdr" || item.Terminal != nil {
					return f, errors.New("ambiguous v1 registry")
				}
				p.Backend = "box"
			} else if item.Terminal == nil || (*item.Terminal != "herdr" && *item.Terminal != "ssh" && *item.Terminal != "none") {
				return f, errors.New("invalid historical terminal preference")
			}
			f.Projects = append(f.Projects, p)
		}
		return f, f.Validate()
	}
	var f File
	if err := Decode(b, &f, true); err != nil {
		return f, err
	}
	return f, f.Validate()
}

func (f File) Resolve(name string) (Project, error) {
	for _, p := range f.Projects {
		for _, candidate := range append([]string{p.Name}, p.Aliases...) {
			if name == candidate {
				return p, nil
			}
		}
	}
	return Project{}, errors.New("unknown project; run allset projects")
}

func (f File) ResolveRepository(remote string) (Project, error) {
	key, err := RepositoryKey(remote)
	if err != nil {
		return Project{}, err
	}
	for _, p := range f.Projects {
		candidate, _ := RepositoryKey(p.Repository)
		if candidate == key {
			return p, nil
		}
	}
	return Project{}, ErrUnregistered
}

// WriteNew publishes a complete private config without replacing any existing path, even in a race.
func WriteNew(path string, f File) error {
	if err := f.Validate(); err != nil {
		return err
	}
	return WriteDocumentNew(path, f)
}

// WriteDocumentNew atomically publishes a document without clobbering existing work.
func WriteDocumentNew(path string, value any) error {
	b, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0700); err != nil {
		return err
	}
	temp, err := os.CreateTemp(dir, ".allset-*")
	if err != nil {
		return err
	}
	defer os.Remove(temp.Name())
	if _, err := temp.Write(append(b, '\n')); err != nil {
		temp.Close()
		return err
	}
	if err := temp.Sync(); err != nil {
		temp.Close()
		return err
	}
	if err := temp.Close(); err != nil {
		return err
	}
	if err := os.Link(temp.Name(), path); err != nil {
		return fmt.Errorf("config was not replaced: %w", err)
	}
	return nil
}
