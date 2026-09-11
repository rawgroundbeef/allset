package legacy

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/execution"
	boxapi "github.com/rawgroundbeef/allset/internal/providers/box"
)

func put(t *testing.T, root, path string, value any) {
	t.Helper()
	target := filepath.Join(root, path)
	if err := os.MkdirAll(filepath.Dir(target), 0700); err != nil {
		t.Fatal(err)
	}
	b, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(target, b, 0600); err != nil {
		t.Fatal(err)
	}
}

func fixture(t *testing.T) (Backend, config.Project) {
	t.Helper()
	b := Backend{Root: t.TempDir(), Python: "/usr/bin/python3"}
	p := config.Project{Name: "dashboard", Repository: "acme/dashboard", Backend: "box"}
	put(t, b.Root, "projects/dashboard/profile.json", map[string]any{"name": p.Name, "repository": p.Repository, "infisical": map[string]string{"token": "SECRET"}})
	put(t, b.Root, "projects/dashboard/machine.json", map[string]string{"task_id": "project-dashboard", "machine_id": "bx_example"})
	put(t, b.Root, "tasks/project-dashboard/task.json", Machine{Project: p.Name, TaskID: "project-dashboard", ID: "bx_example", State: "running"})
	put(t, b.Root, "projects/dashboard/shell.json", map[string]string{"task_id": "shell-dashboard"})
	put(t, b.Root, "tasks/shell-dashboard/task.json", map[string]string{"project": p.Name, "role": "shell"})
	return b, p
}

func TestImportCopiesOnlyRegistration(t *testing.T) {
	b, _ := fixture(t)
	f, err := b.Import()
	if err != nil {
		t.Fatal(err)
	}
	raw, _ := json.Marshal(f)
	for _, key := range []string{"SECRET", "infisical", "token", "machine_id"} {
		if bytes.Contains(raw, []byte(key)) {
			t.Fatalf("copied private/runtime field %s", key)
		}
	}
	if len(f.Projects) != 1 || f.Projects[0].Name != "dashboard" {
		t.Fatal(f)
	}
}

func TestRejectMovedIdentityAndCrossProjectMachine(t *testing.T) {
	b, p := fixture(t)
	wrong := p
	wrong.Repository = "personal/repo"
	if _, err := b.CheckBinding(wrong); err == nil {
		t.Fatal("accepted a changed repository")
	}
	put(t, b.Root, "tasks/project-dashboard/task.json", Machine{Project: "shop-app", TaskID: "project-dashboard", ID: "bx_example"})
	if _, err := b.Status(context.Background(), p, true); err == nil {
		t.Fatal("accepted another project's machine")
	}
	put(t, b.Root, "projects/dashboard/machine.json", map[string]string{"task_id": "../../other", "machine_id": "bx_example"})
	if _, err := b.Machine(p); err == nil {
		t.Fatal("accepted state traversal")
	}
}

func TestMissingTaskIsNotTreatedAsUnassigned(t *testing.T) {
	b, p := fixture(t)
	if err := os.Remove(filepath.Join(b.Root, "tasks/project-dashboard/task.json")); err != nil {
		t.Fatal(err)
	}
	if _, err := b.Status(context.Background(), p, true); err == nil {
		t.Fatal("corruption hidden as unassigned")
	}
	if err := os.Remove(filepath.Join(b.Root, "projects/dashboard/machine.json")); err != nil {
		t.Fatal(err)
	}
	s, err := b.Status(context.Background(), p, true)
	if err != nil || s.State != "unassigned" {
		t.Fatal(s, err)
	}
}

func TestPlanTargetsIntendedProjectAndCollectOwnership(t *testing.T) {
	b, p := fixture(t)
	for _, op := range []string{"open", "resume", "connect", "stop", "collect", "login"} {
		plan, err := b.Plan(p, op, "codex", 7200, "herdr")
		if err != nil {
			t.Fatal(op, err)
		}
		if plan.Project != p.Name || strings.Contains(plan.DisplayCommand(), "SECRET") {
			t.Fatal(plan)
		}
		if (op == "open" || op == "resume") && plan.Args[len(plan.Args)-3] != p.Name {
			t.Fatal("wrong bundled runtime project argument")
		}
	}
	if _, err := b.Plan(p, "open", "", 7201, "herdr"); err == nil {
		t.Fatal("trial limit removed")
	}
	if _, err := b.Plan(p, "login", "bad-agent", 7200, "herdr"); err == nil {
		t.Fatal("accepted unsupported agent")
	}
	put(t, b.Root, "tasks/shell-dashboard/task.json", map[string]string{"project": "shop-app", "role": "shell"})
	if _, err := b.Plan(p, "collect", "", 7200, "herdr"); err == nil {
		t.Fatal("collected another project's work")
	}
}

func TestOpenBridgeUsesNativeViewAndNeverTakesOver(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Skip("Python is required by the migration adapter")
	}
	for _, attach := range []string{"none", "ssh", "herdr", "terminal", "workspace"} {
		t.Run(attach, func(t *testing.T) {
			root := t.TempDir()
			installProgressFixture(t, root)
			put(t, root, "profiles/dashboard/shell.json", map[string]string{"task_id": "shell-dashboard"})
			files := map[string]string{
				"projects.py": `import os,sys,contextlib
from pathlib import Path
PROJECTS=Path(__file__).parent/'profiles'
project_lock=lambda name: contextlib.nullcontext()
class C:
 HERDR=sys.executable
 SESSION='agents'
 def herdr_env(self):
  assert os.environ['FAKE_MODE'] in ('herdr','workspace'), 'plain SSH touched local Herdr environment'
  return dict(os.environ, ALLSET_TEST_NATIVE_VIEW='yes')
 def rh(self,owner,*args):
  assert owner['machine_id']=='bx_saved'
  assert args==('workspace','list'), 'handoff changed an existing workspace'
  return {'workspaces':[{'workspace_id':'w_saved','label':'dashboard / project','panes':['codex','claude']}]}
 def load(self,id):
  assert id=='shell-dashboard'
  return {'project':'dashboard','role':'shell','machine_id':'bx_saved','cwd':'/home/user/project'}
c=C()
def project(name):
 assert name=='dashboard'
 return {'name':name}
def open_project(name, ttl, create_terminal, prepare_sessions):
 assert name=='dashboard' and ttl==7200 and create_terminal is False
 assert prepare_sessions==(os.environ['FAKE_MODE'] in ('workspace','herdr','terminal'))
 print('prepare')
 return {'ssh_alias':'box-dashboard','machine_id':'bx_saved'}
`,
				"project_shell.py": `import os
def prepare_repository(owner, profile, create_terminal):
 assert create_terminal==(os.environ['FAKE_MODE'] in ('herdr','terminal'))
 assert owner['ssh_alias']=='box-dashboard' and profile['name']=='dashboard'
 print('repository')
def shell(*args, **kwargs): raise AssertionError('open bypassed shared preparation and ownership validation')
def terminal(owner, profile): return {'terminal_id':'term_saved'}
`,
				"agent_auth.py": `import contextlib
def print_accounts(controller, profile): print('accounts')
@contextlib.contextmanager
def monitor(controller, owner, profile):
 print('monitor-start')
 yield
 print('monitor-end')
`,
			}
			// A subprocess stub records the native view instead of connecting to any VM.
			files["subprocess.py"] = `import os,shlex,json
DEVNULL=-3
class Result:
 returncode=0
 stdout=json.dumps([{'id':'native_profile','label':'dashboard','target':'box-dashboard','session':'agents','enabled':True}])
def run(argv,env,stdin,capture_output,text,timeout):
 assert os.environ['FAKE_MODE']=='workspace'
 assert argv[1:]==['machine','list','--json']
 assert env['HERDR_CONFIG_PATH']=='/caller/herdr.toml'
 return Result()
def call(argv, env):
 import progress,threading
 assert not progress.active() and not any(t.name=="allset-progress" for t in threading.enumerate())
 assert (env.get('ALLSET_TEST_NATIVE_VIEW')=='yes')==(os.environ['FAKE_MODE']=='herdr')
 assert '--takeover' not in argv
 if argv[0]=='ssh':
  assert argv[:4]==['ssh','-tt','--','box-dashboard']
  if os.environ['FAKE_MODE']=='ssh':
   assert shlex.split(argv[4])[:3]==['cd','--','/home/user/project']
   assert 'herdr' not in argv[4] and 'tmux' not in argv[4]
   print('ssh-shell')
  else:
   assert shlex.split(argv[4])==['/home/user/.local/bin/herdr','--session','agents','terminal','attach','term_saved']
   print('terminal')
 else:
  assert argv[1:]==['--remote','box-dashboard','--session','agents']
  print('native-view')
 return 0
`
			for name, content := range files {
				if err := os.WriteFile(filepath.Join(root, name), []byte(content), 0600); err != nil {
					t.Fatal(err)
				}
			}
			// Install the stub before the embedded adapter imports subprocess.
			prefix := "import sys; sys.path.insert(0, sys.argv[1]);\n"
			cmd := exec.Command(python, "-c", prefix+openBridge, root, "dashboard", "7200", attach)
			cmd.Env = append(os.Environ(), "FAKE_MODE="+attach, "HERDR_CONFIG_PATH=/caller/herdr.toml")
			out, err := cmd.CombinedOutput()
			if err != nil {
				t.Fatal(err, string(out))
			}
			if attach == "herdr" && (!bytes.Contains(out, []byte("native-view")) || !bytes.Contains(out, []byte("monitor-end"))) {
				t.Fatal(string(out))
			}
			if attach == "none" && (bytes.Contains(out, []byte("native-view")) || !bytes.Contains(out, []byte("Project prepared"))) {
				t.Fatal(string(out))
			}
			if attach == "terminal" && (!bytes.Contains(out, []byte("terminal\n")) || !bytes.Contains(out, []byte("monitor-end"))) {
				t.Fatal(string(out))
			}
			if attach == "workspace" && (!bytes.Contains(out, []byte("select dashboard > dashboard / project")) || bytes.Contains(out, []byte("monitor-start"))) {
				t.Fatal(string(out))
			}
		})
	}
}

func TestParseBoxInfoRejectsFalseSuccessAndWrongID(t *testing.T) {
	for _, raw := range []string{
		`{"success":false,"timedOut":true,"signal":"SIGTERM","stderr":"SECRET"}`,
		`{"box":{"id":"bx_other","state":"running"}}`,
		`{"box":{"id":"bx_example","state":"running"},"success":false}`,
		`{"box":{"id":"bx_example"}}`,
		`{"box":{"id":"bx_example","id":"bx_other","state":"running"}}`,
		`not JSON SECRET`,
	} {
		_, err := boxapi.ParseInfo([]byte(raw), "bx_example")
		if err == nil {
			t.Fatalf("accepted %s", raw)
		}
		if strings.Contains(err.Error(), "SECRET") {
			t.Fatal("printed provider diagnostics")
		}
	}
	s, err := boxapi.ParseInfo([]byte("{\"event\":\"reading\"}\n{\"box\":{\"id\":\"bx_example\",\"state\":\"stopped\",\"archiveAfter\":null}}\n"), "bx_example")
	if err != nil || s.State != "stopped" {
		t.Fatal(s, err)
	}
}

func script(t *testing.T, content string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "tool")
	if err := os.WriteFile(path, []byte("#!/bin/sh\n"+content), 0700); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestStatusOnlyInvokesInfoForOwnedMachine(t *testing.T) {
	b, p := fixture(t)
	b.Box = script(t, `test "$#" = 4 && test "$1" = --no-update && test "$2" = --json && test "$3" = info && test "$4" = bx_example || exit 9
printf '%s\n' '{"box":{"id":"bx_example","state":"stopped"}}'
`)
	s, err := b.Status(context.Background(), p, false)
	if err != nil || s.State != "stopped" || s.Source != "box" {
		t.Fatal(s, err)
	}
	b.Box = "/missing/box"
	s, err = b.Status(context.Background(), p, true)
	if err != nil || s.State != "running" || s.Source != "cached-not-live" {
		t.Fatal(s, err)
	}
}

func TestCaptureTimeoutFailureAndOutputLimit(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	start := time.Now()
	if _, err := execution.Capture(ctx, script(t, "exec sleep 20\n")); err == nil || !strings.Contains(err.Error(), "timed out") {
		t.Fatal(err)
	}
	if time.Since(start) > 2*time.Second {
		t.Fatal("unbounded command")
	}
	if _, err := execution.Capture(context.Background(), script(t, "echo SECRET >&2\nexit 1\n")); err == nil || strings.Contains(err.Error(), "SECRET") {
		t.Fatal(err)
	}
	if _, err := execution.Capture(context.Background(), script(t, "head -c 1048577 /dev/zero\n")); err == nil {
		t.Fatal("accepted excessive output")
	}
}

func TestMCPApplyIsIncludedOnOpenAndConnect(t *testing.T) {
	b, p := fixture(t)
	p.MCPs = map[string]config.MCP{"trigger": {Preset: "trigger", ProjectRef: "proj_work"}}
	for _, operation := range []string{"open", "resume", "connect", "mcp-sync", "mcp-login"} {
		plan, err := b.Plan(p, operation, "trigger", 7200, "none")
		if err != nil {
			t.Fatal(err)
		}
		joined := strings.Join(plan.Args, " ")
		if !strings.Contains(joined, `"mcps":{"trigger"`) || !strings.Contains(joined, "proj_work") {
			t.Fatal("declarations not passed", operation)
		}
		if operation == "mcp-sync" && plan.Interactive {
			t.Fatal("sync requires login")
		}
	}
	// Empty map means explicit managed removal. Omitted map means leave unmanaged.
	p.MCPs = map[string]config.MCP{}
	plan, err := b.Plan(p, "open", "", 7200, "none")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(strings.Join(plan.Args, " "), `"mcps":{}`) {
		t.Fatal("explicit empty MCP declaration lost")
	}
}

func installProgressFixture(t *testing.T, root string) {
	t.Helper()
	source, err := os.ReadFile("../controller/runtime/progress.py")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "progress.py"), source, 0600); err != nil {
		t.Fatal(err)
	}
}
