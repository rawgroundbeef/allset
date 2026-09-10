package config

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
)

const ProjectFilename = ".allset"

var ErrNoProject = errors.New("run allset inside a Git project, or use allset PROJECT")

// Manifest is the repository-owned entry point. Personal account bindings and
// observed machine state stay outside the repository, keyed by project identity.
type Manifest struct {
	Schema  string `json:"$schema,omitempty"`
	Version int    `json:"version"`
	Project
}

func (m Manifest) Validate() error {
	if m.Version != 1 {
		return errors.New("unsupported project config version; expected 1")
	}
	if m.Schema != "" && m.Schema != "allset.schema.json" && m.Schema != "./allset.schema.json" {
		return errors.New("$schema must reference allset.schema.json exported by allset config schema --project")
	}
	return (File{Version: 3, Projects: []Project{m.Project}}).Validate()
}

func LoadProject(path string) (Manifest, error) {
	var m Manifest
	info, err := os.Lstat(path)
	if err != nil {
		return m, err
	}
	if !info.Mode().IsRegular() {
		return m, fmt.Errorf("%s must be a regular file, not a symlink", filepath.Base(path))
	}
	if err := ReadJSON(path, &m, true); err != nil {
		return m, err
	}
	return m, m.Validate()
}

func WriteProject(path string, m Manifest) error {
	if err := m.Validate(); err != nil {
		return err
	}
	return WriteDocumentNew(path, m)
}

// Location bounds discovery to the nearest Git worktree. An unrelated nested
// repository must never inherit its parent's project or authentication binding.
type Location struct{ Root, ManifestPath string }

func Discover(start string) (Location, error) {
	absolute, err := filepath.Abs(start)
	if err != nil {
		return Location{}, err
	}
	absolute, err = filepath.EvalSymlinks(absolute)
	if err != nil {
		return Location{}, err
	}
	nearest := ""
	for dir := absolute; ; dir = filepath.Dir(dir) {
		if nearest == "" {
			path := filepath.Join(dir, ProjectFilename)
			if _, err := os.Lstat(path); err == nil {
				nearest = path
			} else if !errors.Is(err, os.ErrNotExist) {
				return Location{}, err
			}
		}
		if _, err := os.Lstat(filepath.Join(dir, ".git")); err == nil {
			return Location{Root: dir, ManifestPath: nearest}, nil
		} else if !errors.Is(err, os.ErrNotExist) {
			return Location{}, err
		}
		if parent := filepath.Dir(dir); parent == dir {
			break
		}
	}
	if nearest != "" {
		return Location{Root: filepath.Dir(nearest), ManifestPath: nearest}, nil
	}
	return Location{}, ErrNoProject
}

// CheckLocalBinding rejects manifest edits that would silently select another
// saved project or account. A new manifest can operate without a global registry.
func CheckLocalBinding(f File, p Project) error {
	key, err := RepositoryKey(p.Repository)
	if err != nil {
		return err
	}
	for _, saved := range f.Projects {
		savedKey, _ := RepositoryKey(saved.Repository)
		for _, name := range append([]string{saved.Name}, saved.Aliases...) {
			if name == p.Name && (saved.Name != p.Name || savedKey != key || saved.Backend != p.Backend) {
				return fmt.Errorf("project config conflicts with saved binding for %s; reconcile it before opening", saved.Name)
			}
		}
		if savedKey == key && (saved.Name != p.Name || saved.Backend != p.Backend) {
			return fmt.Errorf("repository already belongs to %s; keep that project identity", saved.Name)
		}
	}
	return nil
}
