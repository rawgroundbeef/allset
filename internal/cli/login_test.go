package cli

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/execution"
)

func seedLoginMachine(t *testing.T, a App) {
	t.Helper()
	for name, body := range map[string]string{
		"projects/dashboard/machine.json":   `{"task_id":"project-dashboard","machine_id":"bx_saved"}`,
		"tasks/project-dashboard/task.json": `{"task_id":"project-dashboard","machine_id":"bx_saved","project":"dashboard","role":"project"}`,
	} {
		path := filepath.Join(a.CurrentDir, "legacy", name)
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(body), 0600); err != nil {
			t.Fatal(err)
		}
	}
}

func TestProjectAgentShortcutsUseNativeLoginWithoutProjectSetup(t *testing.T) {
	for _, provider := range []string{"claude", "codex", "cursor"} {
		for _, manifest := range []bool{false, true} {
			a, out, plans := appFixture(t)
			seedLoginMachine(t, a)
			path := filepath.Join(a.CurrentDir, config.ProjectFilename)
			if manifest {
				if err := config.WriteProject(path, config.Manifest{Version: 1, Project: config.Project{
					Name: "dashboard", Repository: "acme/dashboard", Backend: "box",
				}}); err != nil {
					t.Fatal(err)
				}
			}
			before, _ := os.ReadFile(path)
			registry, _ := os.ReadFile(a.ConfigPath)
			if code := a.Run(context.Background(), []string{"config", provider}); code != 0 {
				t.Fatal(code, out.String())
			}
			if len(*plans) != 1 {
				t.Fatal("expected one login dispatch")
			}
			p := (*plans)[0]
			if p.Project != "dashboard" || p.Operation != "login" || !p.Interactive || strings.Join(p.Args[len(p.Args)-3:], " ") != "dashboard --login "+provider {
				t.Fatal("incorrect project/client sign-in")
			}
			after, _ := os.ReadFile(path)
			afterRegistry, _ := os.ReadFile(a.ConfigPath)
			if string(before) != string(after) || string(registry) != string(afterRegistry) || strings.Contains(out.String(), "Project setup:") {
				t.Fatal("sign-in changed configuration or entered setup")
			}
		}
	}
}

func TestAgentShortcutExplicitAliasAndDryRunRemainReadOnly(t *testing.T) {
	a, out, plans := appFixture(t)
	seedLoginMachine(t, a)
	a.CurrentDir = t.TempDir() // An explicit project works outside a Git checkout.
	if code := a.Run(context.Background(), []string{"config", "claude", "joy", "--dry-run", "--json"}); code != 0 {
		t.Fatal(code, out.String())
	}
	var p execution.Plan
	if err := json.Unmarshal(out.Bytes(), &p); err != nil {
		t.Fatal(err)
	}
	if p.Project != "dashboard" || p.Operation != "login" || len(*plans) != 0 {
		t.Fatal("dry-run dispatched or mistargeted")
	}
}

func TestAgentShortcutRefusesForeignUnknownAndNoninteractiveTargets(t *testing.T) {
	for _, fault := range []string{"foreign", "unknown", "noninteractive", "no-machine", "unsupported", "extra", "ttl"} {
		a, out, plans := appFixture(t)
		if fault != "no-machine" {
			seedLoginMachine(t, a)
		}
		args := []string{"config", "claude"}
		switch fault {
		case "foreign":
			if err := config.WriteProject(filepath.Join(a.CurrentDir, config.ProjectFilename), config.Manifest{Version: 1, Project: config.Project{
				Name: "dashboard", Repository: "other/repo", Backend: "box",
			}}); err != nil {
				t.Fatal(err)
			}
		case "unknown":
			args = append(args, "missing-project")
		case "noninteractive":
			a.Interactive = false
		case "unsupported":
			args = []string{"config", "invented-client"}
		case "extra":
			args = append(args, "dashboard", "unexpected")
		case "ttl":
			args = append(args, "--ttl", "7200")
		}
		if code := a.Run(context.Background(), args); code != 1 || len(*plans) != 0 {
			t.Fatal(fault, code, out.String())
		}
	}
}
