package mcps

import (
	"os/exec"
	"testing"
)

func TestNativeConfigRuntime(t *testing.T) {
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Fatal("Python 3.11+ required for runtime tests")
	}
	out, err := exec.Command(python, "-m", "unittest", "runtime_test").CombinedOutput()
	if err != nil {
		t.Fatalf("%v\n%s", err, out)
	}
}
