package config

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestHistoricalBackendIsNormalizedWithoutWritingOrGuessing(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.json")
	raw := []byte(`{"version":1,"projects":[{"name":"dashboard","repository":"work/repo","backend":"box-herdr"}]}`)
	if err := os.WriteFile(path, raw, 0600); err != nil {
		t.Fatal(err)
	}
	f, err := Load(path)
	if err != nil || f.Version != 3 || f.Projects[0].Backend != "box" {
		t.Fatal(f, err)
	}
	after, _ := os.ReadFile(path)
	if !bytes.Equal(after, raw) {
		t.Fatal("read-only load wrote a migration")
	}
	for _, raw := range []string{
		`{"version":1,"projects":[{"name":"dashboard","repository":"work/repo","backend":"other"}]}`,
		`{"version":1,"projects":[{"name":"dashboard","repository":"work/repo","backend":"box-herdr","terminal":"ssh"}]}`,
		`{"version":2,"projects":[{"name":"dashboard","repository":"work/repo","backend":"box-herdr","terminal":"herdr"}]}`,
		`{"version":2,"projects":[{"name":"dashboard","repository":"work/repo","backend":"box"}]}`,
	} {
		if err := os.WriteFile(path, []byte(raw), 0600); err != nil {
			t.Fatal(err)
		}
		if _, err := Load(path); err == nil {
			t.Fatal("accepted ambiguous configuration", raw)
		}
	}
}

func TestComputeIdentifiersAreNotAClosedListOfOurProviders(t *testing.T) {
	f := registry()
	f.Projects[0].Backend = "another-service"
	if err := f.Validate(); err != nil {
		t.Fatal(err)
	}
}
