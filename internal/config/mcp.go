package config

import (
	"errors"
	"fmt"
	"net/url"
	"regexp"
	"strings"
)

// MCP declares a native server or a supported preset. Credentials are supplied
// by native login or referenced environment variables, never inline values.
type MCP struct {
	Preset            string   `json:"preset,omitempty"`
	ProjectRef        string   `json:"project_ref,omitempty"`
	ReadOnly          *bool    `json:"read_only,omitempty"`
	Command           string   `json:"command,omitempty"`
	Args              []string `json:"args,omitempty"`
	URL               string   `json:"url,omitempty"`
	EnvVars           []string `json:"env_vars,omitempty"`
	BearerTokenEnvVar string   `json:"bearer_token_env_var,omitempty"`
	Agents            []string `json:"agents,omitempty"`
}

var envName = regexp.MustCompile(`^[A-Z_][A-Z0-9_]*$`)
var triggerRef = regexp.MustCompile(`^proj_[a-zA-Z0-9]+$`)

func ValidateMCPs(servers map[string]MCP) error {
	if len(servers) > 32 {
		return errors.New("at most 32 MCP servers per project are supported")
	}
	for name, m := range servers {
		if !ValidID(name) {
			return errors.New("MCP names must be lowercase identifiers")
		}
		fail := func(message string) error { return fmt.Errorf("MCP %s: %s", name, message) }
		seen := map[string]bool{}
		for _, agent := range m.Agents {
			if (agent != "codex" && agent != "claude" && agent != "cursor") || seen[agent] {
				return fail("agents must uniquely select codex, claude, or cursor")
			}
			seen[agent] = true
		}
		if m.Preset != "" {
			if m.Preset != "trigger" {
				return fail("unknown preset; use trigger, or declare command/args or url")
			}
			if !triggerRef.MatchString(m.ProjectRef) {
				return fail("Trigger requires an explicit project_ref from trigger.config.ts")
			}
			if m.Command != "" || m.URL != "" || len(m.Args) > 0 || len(m.EnvVars) > 0 || m.BearerTokenEnvVar != "" {
				return fail("a preset cannot be mixed with custom transport or authentication")
			}
			continue
		}
		if m.ProjectRef != "" || m.ReadOnly != nil {
			return fail("project_ref and read_only require the trigger preset")
		}
		if (m.Command == "") == (m.URL == "") {
			return fail("choose exactly one of command or url")
		}
		if m.URL != "" {
			u, err := url.Parse(m.URL)
			if err != nil || u.Scheme != "https" || u.Hostname() == "" || u.User != nil || u.Fragment != "" {
				return fail("URL must use HTTPS without embedded credentials or fragments")
			}
			for key := range u.Query() {
				key = strings.ToLower(key)
				if strings.Contains(key, "token") || strings.Contains(key, "secret") || strings.Contains(key, "password") || strings.Contains(key, "key") {
					return fail("URL must not contain credential query parameters")
				}
			}
			if len(m.Args) > 0 || len(m.EnvVars) > 0 {
				return fail("args and env_vars require a stdio command")
			}
		} else {
			if strings.ContainsAny(m.Command, "\x00\r\n") || strings.TrimSpace(m.Command) != m.Command {
				return fail("invalid server command")
			}
			if m.BearerTokenEnvVar != "" {
				return fail("bearer_token_env_var requires an HTTP URL")
			}
			for _, arg := range m.Args {
				if strings.ContainsRune(arg, 0) {
					return fail("invalid server argument")
				}
			}
		}
		for _, name := range append(append([]string{}, m.EnvVars...), m.BearerTokenEnvVar) {
			if name != "" && !envName.MatchString(name) {
				return fail("credential references must be environment variable names, not values")
			}
		}
	}
	return nil
}
