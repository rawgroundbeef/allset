package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/execution"
	"github.com/rawgroundbeef/allset/internal/legacy"
	boxstrategy "github.com/rawgroundbeef/allset/internal/strategies/box"
	"github.com/rawgroundbeef/allset/internal/strategy"
)

func appFixture(t *testing.T) (App, *bytes.Buffer, *[]execution.Plan) {
	t.Helper()
	t.Setenv("HERDR_ENV", "")
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".git"), 0700); err != nil {
		t.Fatal(err)
	}
	output := &bytes.Buffer{}
	plans := &[]execution.Plan{}
	b := legacy.Backend{Root: filepath.Join(root, "legacy"), Box: "/missing/box", Python: "/usr/bin/python3"}
	write := func(path string, v any) {
		t.Helper()
		path = filepath.Join(b.Root, path)
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		raw, _ := json.Marshal(v)
		if err := os.WriteFile(path, raw, 0600); err != nil {
			t.Fatal(err)
		}
	}
	write("projects/dashboard/profile.json", map[string]any{"name": "dashboard", "repository": "acme/dashboard", "agent_profile": "dashboard-work", "credentials": "SECRET"})
	f := config.File{Version: 3, Projects: []config.Project{{Name: "dashboard", Aliases: []string{"joy"}, Repository: "acme/dashboard", Backend: "box"}}}
	path := filepath.Join(root, "config.json")
	if err := config.WriteNew(path, f); err != nil {
		t.Fatal(err)
	}
	a := App{ConfigPath: path, Strategies: strategy.Registry{"box": boxstrategy.Strategy{Controller: b, LookPath: func(s string) (string, error) { return "/usr/bin/" + s, nil }}}, Import: func(string) (config.File, error) { return b.Import() }, Out: output, Err: output, Interactive: true, CurrentDir: root,
		Exec:     func(p execution.Plan) error { *plans = append(*plans, p); return nil },
		LookPath: func(s string) (string, error) { return "/usr/bin/" + s, nil },
		Capture: func(context.Context, string, ...string) ([]byte, error) {
			return []byte("git@github.com:acme/dashboard.git\n"), nil
		},
	}
	return a, output, plans
}

func TestAliasAndRepoInferenceDispatchWithoutPrompt(t *testing.T) {
	for _, args := range [][]string{{"joy"}, {"."}, {}, {"open", "dashboard"}, {"resume", "dashboard"}} {
		a, out, plans := appFixture(t)
		if err := config.WriteProject(filepath.Join(a.CurrentDir, config.ProjectFilename), config.Manifest{
			Version: 1, Project: config.Project{Name: "dashboard", Repository: "acme/dashboard", Backend: "box"},
		}); err != nil {
			t.Fatal(err)
		}
		if code := a.Run(context.Background(), args); code != 0 {
			t.Fatal(args, code, out.String())
		}
		if len(*plans) != 1 {
			t.Fatal("not dispatched once")
		}
		p := (*plans)[0]
		if p.Project != "dashboard" || !p.Interactive || p.Args[len(p.Args)-3] != "dashboard" || p.Attachment != "ssh" {
			t.Fatal("wrong project, attachment, or interactivity")
		}
		for _, arg := range p.Args {
			if arg == "--task-file" || arg == "--login" {
				t.Fatal("forced prompt or login")
			}
		}
	}
}

func TestDryRunNeverExecutesAndJSONIsUsable(t *testing.T) {
	a, out, plans := appFixture(t)
	seedLoginMachine(t, a)
	if code := a.Run(context.Background(), []string{"login", "joy", "codex", "--dry-run", "--json"}); code != 0 {
		t.Fatal(code, out.String())
	}
	if len(*plans) != 0 {
		t.Fatal("dry-run executed")
	}
	var p execution.Plan
	if err := json.Unmarshal(out.Bytes(), &p); err != nil {
		t.Fatal(err)
	}
	if p.Project != "dashboard" || p.Args[len(p.Args)-1] != "codex" {
		t.Fatal(p)
	}
}

func TestInvalidArgumentsCannotDispatch(t *testing.T) {
	for _, args := range [][]string{
		{"dashboard", "--ttl", "7201"}, {"dashboard", "--ttl", "0"}, {"dashboard", "--force"},
		{"dashboard", "unexpected"}, {"dashboard", "--json"}, {"unknown"},
		{"login", "dashboard", "invented"}, {"login"}, {"status", "dashboard", "--ttl", "1"},
	} {
		a, out, plans := appFixture(t)
		if code := a.Run(context.Background(), args); code != 1 {
			t.Fatal(args, code, out.String())
		}
		if len(*plans) != 0 {
			t.Fatal("invalid input dispatched")
		}
	}
}

func TestReadOnlyCommandsNeverDispatchLifecycleOrReadSecrets(t *testing.T) {
	for _, args := range [][]string{{"projects", "--json"}, {"config", "validate"}, {"status", "dashboard", "--cached", "--json"}, {"doctor", "dashboard", "--offline", "--json"}} {
		a, out, plans := appFixture(t)
		code := a.Run(context.Background(), args)
		if args[0] != "doctor" && code != 0 {
			t.Fatal(args, code, out.String())
		}
		if args[0] == "doctor" && code == 0 {
			t.Fatal("incomplete readiness reported success")
		}
		if len(*plans) != 0 {
			t.Fatal("read-only command executed lifecycle")
		}
		if strings.Contains(out.String(), "SECRET") {
			t.Fatal("credential value printed")
		}
	}
}

func TestNonInteractiveOpenRequiresDryRun(t *testing.T) {
	a, out, plans := appFixture(t)
	a.Interactive = false
	if a.Run(context.Background(), []string{"dashboard"}) != 1 || len(*plans) != 0 {
		t.Fatal(out.String())
	}
	out.Reset()
	if a.Run(context.Background(), []string{"dashboard", "--dry-run"}) != 0 || len(*plans) != 0 {
		t.Fatal(out.String())
	}
}

func TestConfigImportPreservesExistingRegistration(t *testing.T) {
	a, out, _ := appFixture(t)
	before, _ := os.ReadFile(a.ConfigPath)
	if code := a.Run(context.Background(), []string{"config", "import", "box-herdr"}); code != 1 {
		t.Fatal(code, out.String())
	}
	after, _ := os.ReadFile(a.ConfigPath)
	if !bytes.Equal(before, after) {
		t.Fatal("import replaced existing config")
	}
}

func TestHelpDoesNotRequireConfigOrTools(t *testing.T) {
	a, out, _ := appFixture(t)
	a.ConfigPath = "/absent/config.json"
	if a.Run(context.Background(), []string{"--help"}) != 0 || !strings.Contains(out.String(), "AllSet") {
		t.Fatal(out.String())
	}
}

func TestHerdrCallerPreparesWorkspaceWithoutInteractiveAttachment(t *testing.T) {
	a, out, plans := appFixture(t)
	t.Setenv("HERDR_ENV", "1")
	t.Setenv("CMUX_WORKSPACE_ID", "existing")
	if code := a.Run(context.Background(), []string{"dashboard"}); code != 0 {
		t.Fatal(code, out.String())
	}
	if len(*plans) != 1 || (*plans)[0].Interactive || (*plans)[0].Attachment != "workspace" {
		t.Fatal(*plans)
	}
	*plans = nil
	a.Interactive = false
	if code := a.Run(context.Background(), []string{"dashboard"}); code != 0 || len(*plans) != 1 || (*plans)[0].Project != "dashboard" {
		t.Fatal(code, out.String(), *plans)
	}
	*plans = nil
	if code := a.Run(context.Background(), []string{"dashboard", "--dry-run", "--json"}); code != 0 || len(*plans) != 0 || !strings.Contains(out.String(), `"attachment": "workspace"`) {
		t.Fatal(code, out.String(), *plans)
	}
	*plans = nil
	if a.Run(context.Background(), []string{"dashboard", "--attach", "invented"}) != 1 || len(*plans) != 0 {
		t.Fatal(out.String())
	}
}

func TestCmuxKeepsSSHAndHerdrHonorsExplicitOverrides(t *testing.T) {
	for _, tc := range []struct{ herdr, mode, want string }{
		{"", "auto", "ssh"}, {"0", "auto", "ssh"},
		{"1", "ssh", "ssh"}, {"1", "none", "none"},
		{"1", "herdr", "herdr"}, {"1", "terminal", "terminal"},
		{"", "workspace", "workspace"},
	} {
		t.Run(tc.herdr+tc.mode, func(t *testing.T) {
			a, out, plans := appFixture(t)
			t.Setenv("HERDR_ENV", tc.herdr)
			t.Setenv("CMUX_WORKSPACE_ID", "unrelated-machine")
			if code := a.Run(context.Background(), []string{"dashboard", "--attach", tc.mode}); code != 0 || len(*plans) != 1 || (*plans)[0].Attachment != tc.want || (*plans)[0].Project != "dashboard" {
				t.Fatal(code, out.String(), *plans)
			}
		})
	}
}

func TestConfigurationInspectionIsReadOnlyAndSeparatesRegistryFromProfile(t *testing.T) {
	a, out, plans := appFixture(t)
	a.Capture = func(context.Context, string, ...string) ([]byte, error) {
		t.Fatal("config inspection contacted a process")
		return nil, nil
	}
	before, _ := os.ReadFile(a.ConfigPath)
	if code := a.Run(context.Background(), []string{"config", "show"}); code != 0 {
		t.Fatal(code, out.String())
	}
	var registry config.File
	if err := json.Unmarshal(out.Bytes(), &registry); err != nil || len(registry.Projects) != 1 {
		t.Fatal(err, out.String())
	}
	out.Reset()
	if code := a.Run(context.Background(), []string{"config", "show", "joy", "--json"}); code != 0 {
		t.Fatal(code, out.String())
	}
	var view legacy.ProfileInspection
	if err := json.Unmarshal(out.Bytes(), &view); err != nil || view.Project.Name != "dashboard" ||
		view.AgentAccountProfile != "dashboard-work" || view.ReadinessChecked {
		t.Fatal(err, out.String())
	}
	after, _ := os.ReadFile(a.ConfigPath)
	if !bytes.Equal(before, after) || len(*plans) != 0 || strings.Contains(out.String(), "SECRET") {
		t.Fatal("inspection changed configuration, executed lifecycle, or exposed secrets")
	}
	for _, args := range [][]string{{"config", "show", "joy", "extra"}, {"config", "show", "--json=false"}, {"config", "show", "unknown"}} {
		if a.Run(context.Background(), args) != 1 || len(*plans) != 0 {
			t.Fatal(args, out.String())
		}
	}
}

func TestConfigGuidanceWorksWithoutRegistrationOrProvider(t *testing.T) {
	for _, command := range []string{"schema", "guide"} {
		a, out, plans := appFixture(t)
		a.ConfigPath = "/missing/config.json"
		a.Strategies = strategy.Registry{}
		if a.Run(context.Background(), []string{"config", command}) != 0 || len(*plans) != 0 {
			t.Fatal(command, out.String())
		}
		if command == "schema" && !json.Valid(out.Bytes()) {
			t.Fatal("schema is not JSON")
		}
		if command == "guide" && !strings.Contains(out.String(), "requires authorized interactive UAT") {
			t.Fatal("guide does not distinguish configured state from real acceptance")
		}
	}
}
