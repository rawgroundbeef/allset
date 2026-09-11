package controller

import (
	"archive/zip"
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func runRuntime(t *testing.T, root, script string) ([]byte, error) {
	t.Helper()
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Fatal(err)
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command(python, Arguments(filepath.Join(root, "state"), "/fake/box", "/fake/herdr",
		[]string{"-c", script, "replaced-bundle-path"})...)
	cmd.Dir = root
	cmd.Env = append(os.Environ(), "XDG_CACHE_HOME="+filepath.Join(root, "cache"), "PYTHONPATH="+root,
		"_ALLSET_STATE_ROOT=/foreign-state", "_ALLSET_BOX_BIN=/foreign-box")
	return cmd.CombinedOutput()
}

func TestBundledRuntimeDoesNotImportLocalControllerOrCallerModules(t *testing.T) {
	root := t.TempDir()
	for _, name := range []string{"projects.py", "sitecustomize.py"} {
		if err := os.WriteFile(filepath.Join(root, name), []byte("raise RuntimeError('caller module imported')\n"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	script := `import os,sys
from pathlib import Path
import projects,project_shell,agent_auth,github_auth,infisical_context
root=Path.cwd()
assert projects.c.STATE == root/'state'
assert str(projects.c.BOX)=='/fake/box'
assert str(projects.c.HERDR)=='/fake/herdr'
assert not (root/'state').exists(), 'import mutated private state'
assert Path(projects.__file__).parent == Path(sys.argv[1])
assert 'cache/allset/controller' in projects.__file__
assert not (root/'state/controller').exists()
print('bundled-import-passed')
`
	for range 2 {
		out, err := runRuntime(t, root, script)
		if err != nil || !bytes.Contains(out, []byte("bundled-import-passed")) {
			t.Fatal(err, string(out))
		}
	}
}

func TestModifiedCacheFailsBeforeRunningCodeAndPreservesFiles(t *testing.T) {
	root := t.TempDir()
	if out, err := runRuntime(t, root, "import projects"); err != nil {
		t.Fatal(err, string(out))
	}
	file := filepath.Join(root, "cache", "allset", "controller", Revision, "projects.py")
	changed := []byte("raise RuntimeError('modified code executed')\n")
	if err := os.WriteFile(file, changed, 0600); err != nil {
		t.Fatal(err)
	}
	out, err := runRuntime(t, root, "import projects")
	if err == nil || !bytes.Contains(out, []byte("cache was modified")) || bytes.Contains(out, []byte("modified code executed")) {
		t.Fatal(err, string(out))
	}
	after, _ := os.ReadFile(file)
	if !bytes.Equal(after, changed) {
		t.Fatal("modified file overwritten")
	}
}

func TestSymlinkCacheAndForeignStateAreNotUsed(t *testing.T) {
	root := t.TempDir()
	other := t.TempDir()
	if err := os.Symlink(other, filepath.Join(root, "cache")); err != nil {
		t.Fatal(err)
	}
	out, err := runRuntime(t, root, "raise RuntimeError('must not execute')")
	if err == nil || !bytes.Contains(out, []byte("cannot contain symlinks")) {
		t.Fatal(err, string(out))
	}
	entries, _ := os.ReadDir(other)
	if len(entries) != 0 {
		t.Fatal("wrote through symlink cache")
	}
}

func TestRuntimePreservesChildExitStatus(t *testing.T) {
	out, err := runRuntime(t, t.TempDir(), "import sys;sys.exit(19)")
	if exit, ok := err.(*exec.ExitError); !ok || exit.ExitCode() != 19 {
		t.Fatal(err, string(out))
	}
}

func TestConcurrentFirstUseInstallsOneCompleteRuntime(t *testing.T) {
	root := t.TempDir()
	for range 4 {
		t.Run("concurrent", func(t *testing.T) {
			t.Parallel()
			out, err := runRuntime(t, root, "import projects, project_shell; print('ready')")
			if err != nil || !bytes.Contains(out, []byte("ready")) {
				t.Fatal(err, string(out))
			}
		})
	}
}

func TestLauncherFitsLinuxArgumentLimit(t *testing.T) {
	for _, arg := range Arguments("/state", "/box", "/herdr", []string{"projects.py", "--help"}) {
		// Linux limits each argv string to 32 pages on a 4 KiB-page host.
		// Leave room for a terminator and stop source growth breaking Linux.
		if len(arg) >= 128*1024 {
			t.Fatal("bundled launcher exceeds Linux's per-argument limit")
		}
	}
}

func TestEmbeddedAssetsExcludePrivateProfilesAndCompile(t *testing.T) {
	reader, err := zip.NewReader(bytes.NewReader(payload), int64(len(payload)))
	if err != nil {
		t.Fatal(err)
	}
	if len(reader.File) != 20 {
		t.Fatal("Review the runtime asset allowlist before adding files")
	}
	for _, file := range reader.File {
		if strings.Contains(file.Name, "/") || strings.HasSuffix(file.Name, ".json") || strings.HasSuffix(file.Name, ".pyc") {
			t.Fatal("non-source asset in runtime", file.Name)
		}
	}
	out, err := runRuntime(t, t.TempDir(), `from pathlib import Path
import sys
root=Path(sys.argv[1])
for file in root.glob('*.py'):
 compile(file.read_text(),file.name,'exec')
assert not any(root.glob('*.json'))
print('assets-passed')
`)
	if err != nil || !bytes.Contains(out, []byte("assets-passed")) {
		t.Fatal(err, string(out))
	}
}

func TestControllerOwnershipAuthenticationAndRecovery(t *testing.T) {
	script, err := os.ReadFile("runtime_test.py")
	if err != nil {
		t.Fatal(err)
	}
	out, err := runRuntime(t, t.TempDir(), string(script))
	if err != nil {
		t.Fatal(err, string(out))
	}
}
