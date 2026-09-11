package cli

import (
	"bytes"
	"strings"
	"testing"
)

func TestOperationHeadingCapturedIsPlain(t *testing.T) {
	t.Setenv("TERM", "xterm-256color")
	var out bytes.Buffer
	app := App{In: strings.NewReader(""), Out: &out}
	app.printOperation("hello-world", "onboarding")
	if got, want := out.String(), "hello-world · onboarding\n"; got != want {
		t.Fatalf("captured heading = %q, want %q", got, want)
	}
}
