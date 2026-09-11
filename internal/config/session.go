package config

import (
	"errors"
	"fmt"
	"path/filepath"
	"strings"
)

// Skill names a repository-owned skill directory. Personal skill locations are
// private account choices and never belong in this shared declaration.
type Skill struct {
	Path   string   `json:"path"`
	Agents []string `json:"agents,omitempty"`
}

// SessionVariable declares a value that a configured secret source must supply
// to future client processes. It contains a reference, never a secret value.
type SessionVariable struct {
	SecretPath string   `json:"secret_path"`
	SecretKey  string   `json:"secret_key"`
	Agents     []string `json:"agents,omitempty"`
	MCPs       []string `json:"mcps,omitempty"`
}

func validateAgents(agents []string) error {
	seen := map[string]bool{}
	for _, agent := range agents {
		if (agent != "codex" && agent != "claude" && agent != "cursor") || seen[agent] {
			return errors.New("agents must uniquely select codex, claude, or cursor")
		}
		seen[agent] = true
	}
	return nil
}

func ValidateSessionRequirements(skills map[string]Skill, environment map[string]SessionVariable, mcps map[string]MCP) error {
	if len(skills) > 32 {
		return errors.New("at most 32 skills per project are supported")
	}
	for name, skill := range skills {
		if !ValidID(name) {
			return errors.New("skill names must be lowercase identifiers")
		}
		path := filepath.Clean(skill.Path)
		if skill.Path == "" || filepath.IsAbs(skill.Path) || path == "." || path == ".." || strings.HasPrefix(path, ".."+string(filepath.Separator)) || path != skill.Path {
			return fmt.Errorf("skill %s: path must be a normalized directory inside the repository", name)
		}
		if err := validateAgents(skill.Agents); err != nil {
			return fmt.Errorf("skill %s: %w", name, err)
		}
	}
	if len(environment) > 64 {
		return errors.New("at most 64 session environment requirements are supported")
	}
	for name, variable := range environment {
		if !envName.MatchString(name) {
			return errors.New("session environment names must be uppercase environment variable names")
		}
		if variable.SecretPath == "" || !strings.HasPrefix(variable.SecretPath, "/") || strings.Contains(variable.SecretPath, "..") {
			return fmt.Errorf("session environment %s: secret_path must be an absolute Infisical path without traversal", name)
		}
		if variable.SecretKey == "" || strings.ContainsAny(variable.SecretKey, "\x00\r\n") {
			return fmt.Errorf("session environment %s: secret_key is required", name)
		}
		if err := validateAgents(variable.Agents); err != nil {
			return fmt.Errorf("session environment %s: %w", name, err)
		}
		seen := map[string]bool{}
		if len(variable.MCPs) > 0 && len(variable.Agents) == 0 {
			return fmt.Errorf("session environment %s: MCP secret recipients require explicit agents", name)
		}
		for _, server := range variable.MCPs {
			mcp, ok := mcps[server]
			if !ok || seen[server] {
				return fmt.Errorf("session environment %s: mcps must uniquely name declared servers", name)
			}
			used := mcp.BearerTokenEnvVar == name
			for _, environmentName := range mcp.EnvVars {
				used = used || environmentName == name
			}
			if !used {
				return fmt.Errorf("session environment %s: MCP %s does not reference this variable", name, server)
			}
			if len(mcp.Agents) > 0 {
				for _, agent := range variable.Agents {
					matched := false
					for _, target := range mcp.Agents {
						matched = matched || agent == target
					}
					if !matched {
						return fmt.Errorf("session environment %s: agent %s is not a target of MCP %s", name, agent, server)
					}
				}
			}
			seen[server] = true
		}
	}
	return nil
}
