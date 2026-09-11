package terminal

import (
	"os/exec"
	"testing"
)

func TestCallerKeepsItsTerminalUnlessItRequestsAnIntegration(t *testing.T) {
	for _, tc := range []struct {
		override, want string
		inHerdr        bool
	}{
		{"auto", "ssh", false}, {"auto", "workspace", true},
		{"ssh", "ssh", true}, {"none", "none", true},
		{"herdr", "herdr", true}, {"terminal", "terminal", true},
		{"workspace", "workspace", false},
	} {
		got, err := Resolve(tc.override, tc.inHerdr)
		if err != nil || got != tc.want {
			t.Fatal(tc, got, err)
		}
	}
	if _, err := Resolve("invented-ui", true); err == nil {
		t.Fatal("unknown adapter accepted")
	}
}

func TestHerdrWorkspaceRecoveryAndPreservation(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Fatal(err)
	}
	if out, err := exec.Command(python, "-m", "unittest", "workspace_test").CombinedOutput(); err != nil {
		t.Fatal(err, string(out))
	}
}

func TestTerminalBridgeUsesGenericTargetAndQuotesDirectory(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Skip("Python required by the temporary preparation bridge")
	}
	script := Bridge + `
directory="/a project/quote'$(echo hidden)"
seen=[]
def capture(argv, env):
    assert env == {"MARKER": "preserved"}
    assert "--takeover" not in argv
    seen.append(argv)
    return 0
subprocess.call=capture
target={"host":"another-provider-alias", "directory":directory}
connect_terminal("ssh", target, herdr="/local/herdr", session="work", environment={"MARKER":"preserved"})
assert seen[0][:4] == ["ssh", "-tt", "--", "another-provider-alias"]
assert shlex.split(seen[0][4])[:3] == ["cd", "--", directory]
connect_terminal("herdr", target, herdr="/local/herdr", session="work", environment={"MARKER":"preserved"})
assert seen[1] == ["/local/herdr", "--remote", "another-provider-alias", "--session", "work"]
target.update(remote_herdr="/remote tools/herdr", terminal_id="term'; touch /tmp/unwanted")
for _ in range(2):
    connect_terminal("terminal", target, herdr="/unused/local/herdr", session="work", environment={"MARKER":"preserved"})
assert seen[2] == seen[3]  # Reconnect targets the same terminal without creating or taking over one.
assert seen[2][:4] == ["ssh", "-tt", "--", "another-provider-alias"]
assert shlex.split(seen[2][4]) == [target["remote_herdr"], "--session", "work", "terminal", "attach", target["terminal_id"]]
subprocess.call=lambda *args, **kwargs: 19
assert connect_terminal("terminal", target, herdr="unused", session="work", environment={"MARKER":"preserved"}) == 19
`
	if out, err := exec.Command(python, "-c", script).CombinedOutput(); err != nil {
		t.Fatal(err, string(out))
	}
}
