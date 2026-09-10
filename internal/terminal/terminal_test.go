package terminal

import (
	"os/exec"
	"testing"
)

func TestCallerKeepsItsTerminalUnlessItRequestsAnIntegration(t *testing.T) {
	for _, tc := range []struct{ override, want string }{
		{"auto", "ssh"}, {"ssh", "ssh"}, {"none", "none"}, {"herdr", "herdr"}, {"terminal", "terminal"},
	} {
		got, err := Resolve(tc.override)
		if err != nil || got != tc.want {
			t.Fatal(tc, got, err)
		}
	}
	if _, err := Resolve("invented-ui"); err == nil {
		t.Fatal("unknown adapter accepted")
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
`
	if out, err := exec.Command(python, "-c", script).CombinedOutput(); err != nil {
		t.Fatal(err, string(out))
	}
}
