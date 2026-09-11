package legacy

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestConnectUsesSelectedTerminalWithoutResumeOrRepositoryPreparation(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Skip("Python required by the compatibility bridge")
	}
	for _, tc := range []struct {
		mode, state, owner string
		ok                 bool
	}{
		{"herdr", "running", "dashboard", true}, {"ssh", "idle", "dashboard", true},
		{"none", "ready", "dashboard", true}, {"terminal", "running", "dashboard", true},
		{"herdr", "stopped", "dashboard", false}, {"ssh", "running", "another-project", false},
		{"terminal", "stopped", "dashboard", false}, {"terminal", "running", "another-project", false},
		{"terminal", "running", "restoring", false},
		{"workspace", "running", "dashboard", true}, {"workspace", "stopped", "dashboard", false},
		{"workspace", "running", "another-project", false}, {"workspace", "running", "restoring", false},
		{"workspace", "running", "wrong-machine", false}, {"workspace", "running", "relative-directory", false},
	} {
		t.Run(tc.mode+"-"+tc.state+"-"+tc.owner, func(t *testing.T) {
			root := t.TempDir()
			installProgressFixture(t, root)
			put(t, root, "profiles/dashboard/shell.json", map[string]string{"task_id": "shell-dashboard"})
			files := map[string]string{
				"projects.py": `import os,sys,contextlib
from pathlib import Path
PROJECTS=Path(__file__).parent/'profiles'
def project(name): return {'name':name}
def machine(name): return {'machine_id':'bx_saved','ssh_alias':'box-dashboard'}
project_lock=lambda name: contextlib.nullcontext()
def wait_project_filesystem(owner,timeout):
 assert timeout==0
 if os.environ['FAKE_OWNER']=='restoring': raise RuntimeError('filesystem still restoring')
 print('filesystem-ready')
class C:
 HERDR=sys.executable
 SESSION='agents'
 def box(self,operation,id):
  assert operation=='info' and id=='bx_saved'
  return {'box':{'state':os.environ['FAKE_STATE']}}
 def refresh_ssh(self,owner): print('refresh')
 def herdr_env(self):
  assert os.environ['FAKE_MODE'] in ('herdr','workspace')
  return {'MARKER':'preserved'}
 def rh(self,owner,*args):
  assert args==('workspace','list'), 'connect changed an existing workspace'
  assert owner['machine_id']=='bx_saved'
  return {'workspaces':[{'workspace_id':'w_saved','label':'dashboard / project','panes':['codex','claude']}]}
 def load(self,id):
  assert id=='shell-dashboard'
  fault=os.environ['FAKE_OWNER']
  return {'project':'dashboard' if fault in ('wrong-machine','relative-directory') else fault,'role':'shell',
   'machine_id':'bx_wrong' if fault=='wrong-machine' else 'bx_saved',
   'cwd':'relative' if fault=='relative-directory' else '/home/user/a project'}
c=C()
def open_project(*args,**kwargs): raise AssertionError('connect resumed or prepared a VM')
`,
				"project_shell.py": `def prepare_repository(*args): raise AssertionError('connect changed repository')
def terminal(*args): return {'terminal_id':'term_saved'}
`,
				"agent_auth.py": `import contextlib
def print_accounts(*args): pass
@contextlib.contextmanager
def monitor(*args):
 yield
 print('monitor-end')
`,
				"subprocess.py": `import os,shlex,json
DEVNULL=-3
class Result:
 returncode=0
 stdout=json.dumps([{'id':'native_profile','label':'dashboard','target':'box-dashboard','session':'agents','enabled':True}])
def run(argv,env,stdin,capture_output,text,timeout):
 assert os.environ['FAKE_MODE']=='workspace'
 assert argv[1:]==['machine','list','--json']
 return Result()
def call(argv,env):
 import progress,threading
 assert not progress.active() and not any(t.name=="allset-progress" for t in threading.enumerate())
 assert env==({'MARKER':'preserved'} if os.environ['FAKE_MODE']=='herdr' else dict(os.environ))
 assert '--takeover' not in argv
 mode=os.environ['FAKE_MODE']
 if mode=='herdr': assert argv[1:]==['--remote','box-dashboard','--session','agents']
 else:
  assert argv[:4]==['ssh','-tt','--','box-dashboard']
  if mode=='ssh': assert shlex.split(argv[-1])[:3]==['cd','--','/home/user/a project']
  else: assert 'terminal attach term_saved' in argv[-1]
 print('connected')
 return 0
`,
			}
			for name, content := range files {
				if err := os.WriteFile(filepath.Join(root, name), []byte(content), 0600); err != nil {
					t.Fatal(err)
				}
			}
			prefix := "import sys;sys.path.insert(0,sys.argv[1]);\n"
			cmd := exec.Command(python, "-c", prefix+openBridge, root, "dashboard", "0", tc.mode, "connect")
			cmd.Env = append(os.Environ(), "FAKE_STATE="+tc.state, "FAKE_OWNER="+tc.owner, "FAKE_MODE="+tc.mode)
			out, err := cmd.CombinedOutput()
			if tc.ok && err != nil {
				t.Fatal(err, string(out))
			}
			if !tc.ok && (err == nil || strings.Contains(string(out), "connected") || strings.Contains(string(out), "Herdr workspace ready")) {
				t.Fatal("unsafe connection", string(out))
			}
			if tc.ok && tc.mode != "none" && tc.mode != "workspace" && !strings.Contains(string(out), "monitor-end") {
				t.Fatal(string(out))
			}
			if tc.ok && tc.mode == "workspace" && !strings.Contains(string(out), "select dashboard > dashboard / project") {
				t.Fatal(string(out))
			}
		})
	}
}

func TestOpenAppliesMCPsAfterPreparationWithoutAttaching(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Fatal(err)
	}
	root := t.TempDir()
	installProgressFixture(t, root)
	files := map[string]string{
		"projects.py": `import sys
class C:
 def ssh_args(self,owner): return ['ssh','project-dashboard']
c=C()
def project(name): return {'name':name}
def open_project(name,ttl,create_terminal,prepare_sessions):
 assert prepare_sessions is False
 assert name=='dashboard' and create_terminal is False
 print('prepared')
 return {'ssh_alias':'project-dashboard'}
def wait_project_filesystem(owner,timeout): print('filesystem-ready')
`,
		"project_shell.py": `def prepare_repository(owner,profile,create_terminal):
 assert create_terminal is False
 print('repository-ready')
`,
		"agent_auth.py": `def print_accounts(*args): pass
`,
		"subprocess.py": `import json,shlex
class Result: returncode=0
def run(argv,timeout,capture_output,text):
 assert capture_output is True and text is True
 assert argv[:2]==['ssh','project-dashboard']
 command=shlex.split(argv[-1])
 assert command[:3]==['python3','-c','runtime-placeholder']
 request=json.loads(command[3])
 assert request['project']=='dashboard' and request['mcps']['trigger']['project_ref']=='proj_work'
 print('mcp-applied')
 return Result()
`,
	}
	for name, data := range files {
		if err := os.WriteFile(filepath.Join(root, name), []byte(data), 0600); err != nil {
			t.Fatal(err)
		}
	}
	payload := `{"name":"dashboard","repository":"acme/dashboard","mcps":{"trigger":{"preset":"trigger","project_ref":"proj_work"}}}`
	prefix := "import sys;sys.path.insert(0,sys.argv[1]);\n"
	out, err := exec.Command(python, "-c", prefix+openBridge, root, "dashboard", "7200", "none", "open", payload, "runtime-placeholder").CombinedOutput()
	if err != nil {
		t.Fatal(err, string(out))
	}
	if !strings.Contains(string(out), "prepared\nrepository-ready\nfilesystem-ready\nPreparing your MCP settings\nmcp-applied\n") {
		t.Fatal(string(out))
	}
}

func TestMCPTransportRejectsStoppedAndRestoringVMs(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Fatal(err)
	}
	out, err := exec.Command(python, "-m", "unittest", "mcp_bridge_test").CombinedOutput()
	if err != nil {
		t.Fatal(err, string(out))
	}
}
