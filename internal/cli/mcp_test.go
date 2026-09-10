package cli

import (
	"context"
	"encoding/json"
	"github.com/rawgroundbeef/allset/internal/config"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestMCPCommandsKeepProjectRoutingAndDryRunReadOnly(t *testing.T) {
	a, out, plans := appFixture(t)
	for path, content := range map[string]string{
		"legacy/projects/dashboard/machine.json":   `{"task_id":"project-dashboard","machine_id":"bx_saved"}`,
		"legacy/tasks/project-dashboard/task.json": `{"task_id":"project-dashboard","project":"dashboard","machine_id":"bx_saved"}`,
		"legacy/controller/projects.py":            `{}`,
	} {
		p := filepath.Join(a.CurrentDir, path)
		os.MkdirAll(filepath.Dir(p), 0700)
		os.WriteFile(p, []byte(content), 0600)
	}
	raw, _ := os.ReadFile(a.ConfigPath)
	var f config.File
	json.Unmarshal(raw, &f)
	f.Projects[0].MCPs = map[string]config.MCP{"trigger": {Preset: "trigger", ProjectRef: "proj_work"}}
	raw, _ = json.Marshal(f)
	os.WriteFile(a.ConfigPath, raw, 0600)
	for _, args := range [][]string{{"mcp", "list", "dashboard"}, {"mcp", "sync", "dashboard", "--dry-run"}, {"mcp", "login", "trigger", "dashboard", "--dry-run"}} {
		out.Reset()
		if a.Run(context.Background(), args) != 0 {
			t.Fatal(out.String())
		}
		if len(*plans) != 0 {
			t.Fatal("read-only MCP command executed")
		}
		if !strings.Contains(out.String(), "dashboard") {
			t.Fatal("missing project")
		}
	}
	out.Reset()
	if a.Run(context.Background(), []string{"mcp", "sync", "dashboard"}) != 0 {
		t.Fatal(out.String())
	}
	if len(*plans) != 1 || (*plans)[0].Operation != "mcp-sync" || (*plans)[0].Project != "dashboard" {
		t.Fatal(*plans)
	}
}
