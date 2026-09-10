package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/execution"
	"github.com/rawgroundbeef/allset/internal/strategy"
)

// This strategy deliberately has no Box, Herdr, Python, local-profile, or bx_ID
// dependency. The dispatcher must work without reaching any of those adapters.
type testService struct {
	calls      []string
	attachment string
}

func (s *testService) Validate(p config.Project) error {
	s.calls = append(s.calls, "validate")
	return nil
}
func (s *testService) Inspect(p config.Project) (any, error) {
	s.calls = append(s.calls, "inspect")
	return map[string]string{"backend": p.Backend}, nil
}
func (s *testService) Status(_ context.Context, p config.Project, _ bool) (strategy.Status, error) {
	s.calls = append(s.calls, "status")
	return strategy.Status{Project: p.Name, MachineID: "vendor/region/instance", State: "stopped", Source: "test-service"}, nil
}
func (s *testService) Diagnose(_ context.Context, p config.Project, _ bool) strategy.Diagnosis {
	s.calls = append(s.calls, "diagnose")
	return strategy.Diagnosis{Project: p.Name, Overall: "ready", Checks: []strategy.Check{}}
}
func (s *testService) Plan(p config.Project, operation, agent string, ttl int, attach string) (execution.Plan, error) {
	s.calls = append(s.calls, "plan")
	s.attachment = attach
	return execution.Plan{Project: p.Name, Backend: p.Backend, Operation: operation, Executable: "/test-service", Args: []string{operation}, Attachment: attach}, nil
}

func TestServiceStrategyOwnsValidationDiagnosisAndDispatch(t *testing.T) {
	for _, args := range [][]string{{"demo"}, {"connect", "demo"}, {"status", "demo", "--json"}, {"doctor", "demo", "--offline"}, {"config", "show", "demo"}, {"config", "validate"}} {
		t.Run(args[0], func(t *testing.T) {
			root := t.TempDir()
			path := filepath.Join(root, "config.json")
			f := config.File{Version: 3, Projects: []config.Project{{Name: "demo", Repository: "any/repo", Backend: "test-service"}}}
			if err := config.WriteNew(path, f); err != nil {
				t.Fatal(err)
			}
			s := &testService{}
			out := &bytes.Buffer{}
			var dispatched []execution.Plan
			a := App{ConfigPath: path, Strategies: strategy.Registry{"test-service": s}, Out: out, Err: out,
				Exec: func(p execution.Plan) error { dispatched = append(dispatched, p); return nil }}
			if code := a.Run(context.Background(), args); code != 0 {
				t.Fatal(code, out.String())
			}
			if args[0] == "demo" || args[0] == "connect" {
				if len(dispatched) != 1 || dispatched[0].Backend != "test-service" || s.attachment != "ssh" {
					t.Fatal(dispatched, s.calls)
				}
			} else if len(dispatched) != 0 {
				t.Fatal("read-only operation executed a plan")
			}
			if args[0] == "status" && !bytes.Contains(out.Bytes(), []byte("vendor/region/instance")) {
				t.Fatal("provider machine identity altered")
			}
		})
	}
}

func TestUninstalledBackendNeverFallsBackToBox(t *testing.T) {
	a, out, plans := appFixture(t)
	raw, err := os.ReadFile(a.ConfigPath)
	if err != nil {
		t.Fatal(err)
	}
	var f config.File
	if err := json.Unmarshal(raw, &f); err != nil {
		t.Fatal(err)
	}
	f.Projects[0].Backend = "uninstalled"
	raw, _ = json.Marshal(f)
	if err := os.WriteFile(a.ConfigPath, raw, 0600); err != nil {
		t.Fatal(err)
	}
	for _, args := range [][]string{{"dashboard"}, {"status", "dashboard"}, {"config", "validate"}, {"config", "show", "dashboard"}} {
		out.Reset()
		if a.Run(context.Background(), args) != 1 || len(*plans) != 0 || !bytes.Contains(out.Bytes(), []byte("no installed strategy")) {
			t.Fatal(args, out.String())
		}
	}
	out.Reset()
	a.ConfigPath = "/missing/config.json"
	if a.Run(context.Background(), []string{"backends", "--json"}) != 0 || out.String() != "[\n  \"box\"\n]\n" {
		t.Fatal(out.String())
	}
}
