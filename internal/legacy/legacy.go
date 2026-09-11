// Package legacy adapts private prototype state to AllSet's bundled controller.
package legacy

import (
	"context"
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/controller"
	"github.com/rawgroundbeef/allset/internal/execution"
	"github.com/rawgroundbeef/allset/internal/mcps"
	boxapi "github.com/rawgroundbeef/allset/internal/providers/box"
	"github.com/rawgroundbeef/allset/internal/strategy"
	"github.com/rawgroundbeef/allset/internal/terminal"
)

type Backend struct{ Root, Box, Python string }

//go:embed open.py
var prepareBridge string

//go:embed mcp.py
var mcpBridge string

var openBridge = terminal.Bridge + "\n" + terminal.WorkspaceBridge + "\n" + mcpBridge + "\n" + prepareBridge

type Profile struct {
	Name         string   `json:"name"`
	Aliases      []string `json:"aliases"`
	Repository   string   `json:"repository"`
	AgentProfile string   `json:"agent_profile"`
	CodingOnly   bool     `json:"coding_only"`
	Clients      []string `json:"clients"`
	Github       *struct {
		Provider string `json:"provider"`
	} `json:"github"`
}

func (b Backend) OnboardingPending(p config.Project) (bool, error) {
	profile, err := b.CheckBinding(p)
	if err != nil || !profile.CodingOnly {
		return false, err
	}
	var journal struct {
		Project string `json:"project"`
		Stage   string `json:"stage"`
	}
	err = config.ReadJSON(filepath.Join(b.Root, "projects", p.Name, "onboarding.json"), &journal, false)
	if errors.Is(err, os.ErrNotExist) {
		return true, nil
	}
	if err != nil {
		return false, fmt.Errorf("cannot read onboarding journal: %w", err)
	}
	if journal.Project != p.Name {
		return false, errors.New("onboarding journal belongs to another project")
	}
	valid := map[string]bool{"environment-intent": true, "environment-created": true, "environment-safe": true, "profile-saved": true, "complete": true}
	if !valid[journal.Stage] {
		return false, errors.New("onboarding journal has an invalid stage")
	}
	return journal.Stage != "complete", nil
}

type Machine struct {
	Project      string `json:"project"`
	TaskID       string `json:"task_id"`
	ID           string `json:"machine_id"`
	State        string `json:"box_state"`
	Phase        string `json:"phase"`
	ArchiveAfter string `json:"archive_after"`
	SSHAlias     string `json:"ssh_alias"`
}

type Status = strategy.Status

func (b Backend) profile(name string) (Profile, error) {
	var p Profile
	if !config.ValidID(name) {
		return p, errors.New("invalid project identifier")
	}
	err := config.ReadJSON(filepath.Join(b.Root, "projects", name, "profile.json"), &p, false)
	if err != nil {
		return p, fmt.Errorf("cannot read installed profile for %s: %w", name, err)
	}
	if p.Name != name {
		return p, errors.New("installed project identity does not match its directory")
	}
	return p, nil
}

func (b Backend) Import() (config.File, error) {
	out := config.File{Version: 3, Projects: []config.Project{}}
	entries, err := os.ReadDir(filepath.Join(b.Root, "projects"))
	if err != nil {
		return out, err
	}
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		p, err := b.profile(entry.Name())
		if err != nil {
			return out, err
		}
		out.Projects = append(out.Projects, config.Project{Name: p.Name, Aliases: p.Aliases, Repository: p.Repository, Backend: "box"})
	}
	if len(out.Projects) == 0 {
		return out, errors.New("no installed Box/Herdr profiles found")
	}
	sort.Slice(out.Projects, func(i, j int) bool { return out.Projects[i].Name < out.Projects[j].Name })
	return out, out.Validate()
}

// CheckBinding prevents a config edit or stale registration from opening another account's project.
func (b Backend) CheckBinding(p config.Project) (Profile, error) {
	installed, err := b.profile(p.Name)
	if err != nil {
		return installed, err
	}
	want, err := config.RepositoryKey(p.Repository)
	if err != nil {
		return installed, err
	}
	got, err := config.RepositoryKey(installed.Repository)
	if err != nil {
		return installed, err
	}
	if want != got {
		return installed, errors.New("repository binding changed; reconcile the project profile before opening it")
	}
	return installed, nil
}

var boxID = regexp.MustCompile(`^bx_[a-zA-Z0-9]+$`)

func (b Backend) Machine(p config.Project) (Machine, error) {
	var pointer, machine Machine
	err := config.ReadJSON(filepath.Join(b.Root, "projects", p.Name, "machine.json"), &pointer, false)
	if err != nil {
		return machine, err
	}
	if !config.ValidID(pointer.TaskID) || !boxID.MatchString(pointer.ID) {
		return machine, errors.New("invalid saved machine pointer")
	}
	err = config.ReadJSON(filepath.Join(b.Root, "tasks", pointer.TaskID, "task.json"), &machine, false)
	if err != nil {
		return machine, fmt.Errorf("cannot read saved machine state: %w", err)
	}
	if machine.Project != p.Name || machine.TaskID != pointer.TaskID || machine.ID != pointer.ID {
		return machine, errors.New("saved machine ownership mismatch")
	}
	return machine, nil
}

func (b Backend) Status(ctx context.Context, p config.Project, cached bool) (Status, error) {
	s := Status{Project: p.Name, State: "unassigned", Source: "local-registration", CheckedAt: time.Now().UTC().Format(time.RFC3339)}
	m, err := b.Machine(p)
	if errors.Is(err, os.ErrNotExist) {
		// A missing pointer means unassigned; a pointer with missing task data is corruption.
		if _, pointerErr := os.Stat(filepath.Join(b.Root, "projects", p.Name, "machine.json")); errors.Is(pointerErr, os.ErrNotExist) {
			return s, nil
		}
	}
	if err != nil {
		return s, err
	}
	s.MachineID = m.ID
	if cached {
		s.Source = "cached-not-live"
		s.State = m.State
		if s.State == "" {
			s.State = "unknown"
		}
		s.AutoStop = m.ArchiveAfter
		return s, nil
	}
	live, err := (boxapi.Client{Executable: b.Box}).Info(ctx, m.ID)
	if err != nil {
		return s, err
	}
	live.Project, live.CheckedAt = p.Name, s.CheckedAt
	return live, nil
}

type Plan = execution.Plan

func (b Backend) Plan(p config.Project, operation, agent string, ttl int, attach string) (Plan, error) {
	plan := Plan{Project: p.Name, Operation: operation, Backend: "box", Executable: b.Python}
	if _, err := b.CheckBinding(p); err != nil {
		return plan, err
	}
	// This is a logical path in the bundle, never executable code from b.Root.
	runtimeRoot := "bundled-controller"
	switch operation {
	case "mcp-sync", "mcp-login":
		if p.MCPs == nil {
			return plan, errors.New("no mcps declared in this project config")
		}
		if operation == "mcp-login" {
			m, ok := p.MCPs[agent]
			if !ok || m.Preset != "trigger" {
				return plan, errors.New("native login here supports declared Trigger presets; use your agent MCP login for custom HTTP servers")
			}
			plan.Interactive = true
		}
		if _, err := b.Machine(p); err != nil {
			return plan, err
		}
		payload, err := json.Marshal(p)
		if err != nil {
			return plan, err
		}
		script := mcpBridge + "\ntry:\n sys.exit(mcp_main())\nexcept Exception as error:\n print('allset:', str(error), file=sys.stderr)\n sys.exit(1)\n"
		plan.Args = []string{"-c", script, runtimeRoot, string(payload), mcps.Runtime, operation, agent}
	case "open", "resume", "login":
		if operation == "login" {
			if agent != "claude" && agent != "codex" && agent != "cursor" {
				return plan, errors.New("agent must be claude, codex, or cursor")
			}
			if _, err := b.Machine(p); err != nil {
				return plan, fmt.Errorf("agent sign-in requires a valid saved machine; open the project first: %w", err)
			}
			plan.Args = []string{filepath.Join(runtimeRoot, "project_shell.py"), "--project", p.Name, "--login", agent}
			plan.Interactive = true
		} else {
			if ttl < 1 || ttl > 7200 {
				return plan, errors.New("this migration retains the existing 1–7200 second trial limit")
			}
			if !terminal.Valid(attach) && attach != "terminal" {
				return plan, errors.New("attachment must be workspace, herdr, ssh, none, or terminal")
			}
			plan.Args = []string{"-c", openBridge, runtimeRoot, p.Name, fmt.Sprint(ttl), attach}
			plan.Attachment, plan.Interactive = attach, attach != "none" && attach != "workspace"
		}
	case "connect", "stop":
		if _, err := b.Machine(p); err != nil {
			return plan, errors.New("no valid saved machine; use allset open for initial setup")
		}
		if operation == "connect" {
			if !terminal.Valid(attach) && attach != "terminal" {
				return plan, errors.New("attachment must be workspace, herdr, ssh, none, or terminal")
			}
			plan.Args = []string{"-c", openBridge, runtimeRoot, p.Name, "0", attach, "connect"}
			plan.Attachment, plan.Interactive = attach, attach != "none" && attach != "workspace"
		} else {
			plan.Args = []string{filepath.Join(runtimeRoot, "projects.py"), operation, p.Name}
		}
	case "collect":
		var shell struct {
			TaskID string `json:"task_id"`
		}
		if err := config.ReadJSON(filepath.Join(b.Root, "projects", p.Name, "shell.json"), &shell, false); err != nil {
			return plan, errors.New("no saved project shell to collect")
		}
		if !config.ValidID(shell.TaskID) {
			return plan, errors.New("invalid saved shell identifier")
		}
		var task struct {
			Project string `json:"project"`
			Role    string `json:"role"`
		}
		if err := config.ReadJSON(filepath.Join(b.Root, "tasks", shell.TaskID, "task.json"), &task, false); err != nil {
			return plan, err
		}
		if task.Project != p.Name || task.Role != "shell" {
			return plan, errors.New("saved shell ownership mismatch")
		}
		plan.Args = []string{filepath.Join(runtimeRoot, "projects.py"), "collect", shell.TaskID}
	default:
		return plan, errors.New("unsupported lifecycle operation")
	}
	if (p.MCPs != nil || p.Skills != nil || p.SessionEnvironment != nil) &&
		(operation == "open" || operation == "resume" || operation == "connect") {
		payload, err := json.Marshal(p)
		if err != nil {
			return plan, err
		}
		if operation != "connect" {
			plan.Args = append(plan.Args, "open")
		}
		plan.Args = append(plan.Args, string(payload), mcps.Runtime)
	}
	if !filepath.IsAbs(plan.Executable) {
		return plan, errors.New("Python 3.11+ is required by the bundled Box runtime")
	}
	plan.Args = controller.Arguments(b.Root, b.Box, filepath.Join(b.Root, "bin", "herdr"), plan.Args)
	return plan, nil
}

func (b Backend) OnboardingPlan(p config.Project, clients []strategy.ClientBinding, ttl int, attach string) (Plan, error) {
	plan := Plan{Project: p.Name, Operation: "onboard", Backend: "box", Executable: b.Python,
		Attachment: attach, Interactive: true}
	if _, err := b.CheckBinding(p); err == nil {
		pending, pendingErr := b.OnboardingPending(p)
		if pendingErr != nil {
			return plan, pendingErr
		}
		if !pending {
			return b.Plan(p, "open", "", ttl, attach)
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return plan, err
	}
	if ttl < 1 || ttl > 7200 {
		return plan, errors.New("this migration retains the existing 1–7200 second trial limit")
	}
	if !terminal.Valid(attach) && attach != "terminal" {
		return plan, errors.New("attachment must be workspace, herdr, ssh, none, or terminal")
	}
	_, existingErr := b.CheckBinding(p)
	if len(clients) == 0 && existingErr != nil {
		if _, journalErr := os.Stat(filepath.Join(b.Root, "projects", p.Name, "onboarding.json")); journalErr != nil {
			return plan, strategy.ErrOnboardingChoicesRequired
		}
	}
	seen := map[string]bool{}
	for _, binding := range clients {
		if (binding.Client != "claude" && binding.Client != "codex" && binding.Client != "cursor") || seen[binding.Client] {
			return plan, errors.New("clients must uniquely select claude, codex, or cursor")
		}
		if !strings.Contains(strings.TrimSpace(binding.ExpectedAccount), "@") || strings.ContainsAny(binding.ExpectedAccount, "\x00\r\n") {
			return plan, errors.New("each selected client requires its expected account email")
		}
		seen[binding.Client] = true
	}
	payload, err := json.Marshal(struct {
		Project config.Project           `json:"project"`
		Clients []strategy.ClientBinding `json:"clients"`
	}{p, clients})
	if err != nil {
		return plan, err
	}
	plan.Args = []string{"-c", openBridge, "bundled-controller", p.Name, fmt.Sprint(ttl), attach, "onboard", string(payload), mcps.Runtime}
	plan.Args = controller.Arguments(b.Root, b.Box, filepath.Join(b.Root, "bin", "herdr"), plan.Args)
	if !filepath.IsAbs(plan.Executable) {
		return plan, errors.New("Python 3.11+ is required by the bundled Box runtime")
	}
	return plan, nil
}
