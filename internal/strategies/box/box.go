// Package box composes native Box compute with the existing workspace adapter.
// The adapter is an implementation detail, never a project backend identifier.
package box

import (
	"context"
	"errors"
	"fmt"
	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/execution"
	"github.com/rawgroundbeef/allset/internal/legacy"
	"github.com/rawgroundbeef/allset/internal/strategy"
	"os"
	"os/exec"
)

type Strategy struct {
	Controller legacy.Backend
	LookPath   func(string) (string, error)
}

func (s Strategy) lookPath(name string) (string, error) {
	if s.LookPath != nil {
		return s.LookPath(name)
	}
	return exec.LookPath(name)
}
func (s Strategy) Validate(p config.Project) error {
	if p.Backend != "box" {
		return errors.New("Box strategy received a different backend")
	}
	_, err := s.Controller.CheckBinding(p)
	if errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("Box workspace setup for %s is not configured; this version opens existing profiles but does not yet provision a new project from .allset", p.Name)
	}
	return err
}
func (s Strategy) Inspect(p config.Project) (any, error) {
	if err := s.Validate(p); err != nil {
		return nil, err
	}
	return s.Controller.Inspect(p)
}
func (s Strategy) Status(ctx context.Context, p config.Project, cached bool) (strategy.Status, error) {
	if err := s.Validate(p); err != nil {
		return strategy.Status{}, err
	}
	return s.Controller.Status(ctx, p, cached)
}
func (s Strategy) Plan(p config.Project, operation, agent string, ttl int, attach string) (execution.Plan, error) {
	if err := s.Validate(p); err != nil {
		return execution.Plan{}, err
	}
	return s.Controller.Plan(p, operation, agent, ttl, attach)
}

func (s Strategy) Diagnose(ctx context.Context, p config.Project, offline bool) strategy.Diagnosis {
	d := strategy.Diagnosis{Project: p.Name, Overall: "incomplete", Checks: []strategy.Check{}}
	add := func(name, state, detail string) {
		d.Checks = append(d.Checks, strategy.Check{Name: name, State: state, Detail: detail})
		if state == "fail" {
			d.Overall = "failed"
		}
	}
	profile, err := s.Controller.CheckBinding(p)
	if err != nil {
		add("project binding", "fail", err.Error())
		return d
	}
	add("project binding", "pass", "Registered repository matches installed profile")
	for _, tool := range []string{"git", "ssh", "python3"} {
		if _, err := s.lookPath(tool); err != nil {
			add(tool, "fail", "Required executable is missing")
		} else {
			add(tool, "pass", "Installed")
		}
	}
	if info, err := os.Stat(s.Controller.Box); err != nil || !info.Mode().IsRegular() || info.Mode()&0111 == 0 {
		add("Box CLI", "fail", "Native Box CLI is missing or not executable")
	} else {
		add("Box CLI", "pass", "Installed")
	}
	if _, err := s.Controller.Plan(p, "open", "", 7200, "none"); err != nil {
		add("bundled workspace runtime", "fail", err.Error())
	} else {
		add("bundled workspace runtime", "pass", "Controller code is included in the AllSet executable")
	}
	status, err := s.Controller.Status(ctx, p, offline)
	if err != nil {
		add("VM", "fail", err.Error())
	} else if offline {
		add("VM", "unchecked", "Cached state: "+status.State+"; no provider request made")
	} else if status.State == "ready" || status.State == "idle" || status.State == "running" {
		add("VM", "pass", status.MachineID+" is "+status.State+"; application readiness is separate")
	} else {
		add("VM", "pending", status.State+"; use allset "+p.Name+" to open it")
	}
	if profile.Github == nil {
		add("GitHub", "pending", "No native Box GitHub provider is configured for this project")
	} else {
		add("GitHub", "unchecked", "Configured; authenticated repository access has not been probed")
	}
	if profile.AgentProfile == "" {
		add("agent accounts", "pending", "No explicit agent account profile is bound")
	} else {
		add("agent accounts", "unchecked", "Bound to "+profile.AgentProfile+"; native login status has not been probed")
	}
	add("Infisical, MCPs, skills, previews", "unchecked", "Remote readiness probes are not implemented in this version")
	return d
}
