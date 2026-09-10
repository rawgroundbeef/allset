package wiring

import (
	"io"
	"os"
	"path/filepath"
	"testing"
)

func TestRegistryLocationAndExplicitOverrideDoNotWriteState(t *testing.T) {
	home := t.TempDir()
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("ALLSET_CONFIG", "")
	check := func(want string) {
		t.Helper()
		if got := Default(home, io.Discard, io.Discard).ConfigPath; got != want {
			t.Fatalf("registry path = %s, want %s", got, want)
		}
		if _, err := os.Stat(want); !os.IsNotExist(err) {
			t.Fatal("resolving registry created state", err)
		}
	}
	check(filepath.Join(home, ".config", "allset", "config.json"))
	root := t.TempDir()
	t.Setenv("XDG_CONFIG_HOME", root)
	check(filepath.Join(root, "allset", "config.json"))
	override := filepath.Join(root, "custom.json")
	t.Setenv("ALLSET_CONFIG", override)
	check(override)
}
