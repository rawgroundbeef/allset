package cli

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/strategy"
)

func TestBareAllSetUsesNearestProjectManifestWithoutGlobalRegistry(t *testing.T) {
	a, out, plans := appFixture(t)
	root := a.CurrentDir
	p := config.Project{Name: "dashboard", Repository: "acme/dashboard", Backend: "box"}
	if err := config.WriteProject(filepath.Join(root, config.ProjectFilename), config.Manifest{Version: 1, Project: p}); err != nil {
		t.Fatal(err)
	}
	a.CurrentDir = filepath.Join(root, "apps", "admin")
	if err := os.MkdirAll(a.CurrentDir, 0700); err != nil {
		t.Fatal(err)
	}
	a.ConfigPath = filepath.Join(root, "missing-registry.json")
	if code := a.Run(context.Background(), nil); code != 0 {
		t.Fatal(code, out.String())
	}
	if len(*plans) != 1 || (*plans)[0].Project != "dashboard" || (*plans)[0].Attachment != "ssh" {
		t.Fatal(*plans)
	}
}

func TestExistingManifestOpensAndInitPreservesContents(t *testing.T) {
	a, out, plans := appFixture(t)
	path := filepath.Join(a.CurrentDir, config.ProjectFilename)
	body := []byte(`{"$schema":"allset.schema.json","version":1,"name":"dashboard","repository":"acme/dashboard","backend":"box"}`)
	if err := os.WriteFile(path, body, 0600); err != nil {
		t.Fatal(err)
	}
	for _, args := range [][]string{{"init"}, {"config", "show", "--project"}, nil} {
		if code := a.Run(context.Background(), args); code != 0 {
			t.Fatal(args, code, out.String())
		}
	}
	if len(*plans) != 1 || (*plans)[0].Project != "dashboard" {
		t.Fatal(*plans)
	}
	if after, err := os.ReadFile(path); err != nil || !bytes.Equal(body, after) {
		t.Fatal("existing project file changed", err)
	}
}

func TestBrokenOrForeignManifestNeverFallsBackToRegisteredProject(t *testing.T) {
	for _, body := range []string{
		`{not valid`,
		`{"version":1,"name":"dashboard","repository":"another/repo","backend":"box"}`,
		`{"version":1,"name":"another","repository":"acme/dashboard","backend":"box"}`,
		`{"version":1,"name":"dashboard","repository":"acme/dashboard","backend":"box","terminal":"herdr"}`,
	} {
		a, out, plans := appFixture(t)
		if err := os.WriteFile(filepath.Join(a.CurrentDir, config.ProjectFilename), []byte(body), 0600); err != nil {
			t.Fatal(err)
		}
		if code := a.Run(context.Background(), nil); code != 1 || len(*plans) != 0 {
			t.Fatal(code, out.String(), *plans)
		}
	}
}

func TestInitReusesSavedBindingWithoutTouchingAccountsOrLaunching(t *testing.T) {
	a, out, plans := appFixture(t)
	before, _ := os.ReadFile(a.ConfigPath)
	if code := a.Run(context.Background(), []string{"init"}); code != 0 {
		t.Fatal(code, out.String())
	}
	m, err := config.LoadProject(filepath.Join(a.CurrentDir, config.ProjectFilename))
	if err != nil || m.Name != "dashboard" || m.Backend != "box" {
		t.Fatal(m, err)
	}
	if code := a.Run(context.Background(), []string{"init"}); code != 0 {
		t.Fatal(code, out.String())
	}
	after, _ := os.ReadFile(a.ConfigPath)
	if !bytes.Equal(before, after) || len(*plans) != 0 || strings.Contains(out.String(), "SECRET") {
		t.Fatal("init changed profile or dispatched")
	}
}

func TestMissingConfigEntersSetupAndReportsUnimplementedProviderPreparation(t *testing.T) {
	a, out, plans := appFixture(t)
	a.Capture = func(context.Context, string, ...string) ([]byte, error) {
		return []byte("git@github.com:new/project.git"), nil
	}
	a.In = strings.NewReader("\n\n")
	if code := a.Run(context.Background(), nil); code != 1 {
		t.Fatal(code, out.String())
	}
	m, err := config.LoadProject(filepath.Join(a.CurrentDir, config.ProjectFilename))
	if err != nil || m.Name != "project" || m.Repository != "https://github.com/new/project" {
		t.Fatal(m, err)
	}
	if len(*plans) != 0 {
		t.Fatal("incomplete setup launched a VM")
	}
	if !strings.Contains(out.String(), "Compute provider") {
		t.Fatal("setup did not run")
	}
}

func TestFirstRunDryRunAndReadOnlyNeverCreateConfigurationOrPrompt(t *testing.T) {
	for _, args := range [][]string{{"--dry-run", "--json"}, {"status"}, {"doctor", "--offline"}} {
		a, out, plans := appFixture(t)
		a.Capture = func(context.Context, string, ...string) ([]byte, error) {
			return []byte("git@github.com:new/project.git"), nil
		}
		a.In = strings.NewReader("should not be consumed\n")
		if code := a.Run(context.Background(), args); code != 1 {
			t.Fatal(code, out.String())
		}
		if _, err := os.Stat(filepath.Join(a.CurrentDir, config.ProjectFilename)); !errors.Is(err, os.ErrNotExist) {
			t.Fatal("read-only command wrote config")
		}
		if len(*plans) != 0 || strings.Contains(out.String(), "Compute provider") {
			t.Fatal("read-only command started setup")
		}
	}
}

func TestBareDryRunFlagsAndInitCancellation(t *testing.T) {
	a, out, plans := appFixture(t)
	if code := a.Run(context.Background(), []string{"--dry-run", "--json"}); code != 0 || len(*plans) != 0 || !strings.Contains(out.String(), `"attachment": "ssh"`) {
		t.Fatal(code, out.String())
	}
	a.Capture = func(context.Context, string, ...string) ([]byte, error) {
		return []byte("https://github.com/new/project"), nil
	}
	a.In = strings.NewReader("")
	out.Reset()
	if code := a.Run(context.Background(), nil); code != 1 || !strings.Contains(out.String(), "cancelled") {
		t.Fatal(code, out.String())
	}
	if _, err := os.Stat(filepath.Join(a.CurrentDir, config.ProjectFilename)); !errors.Is(err, os.ErrNotExist) {
		t.Fatal("cancelled setup wrote config")
	}
}

func TestInitDoesNotEchoCredentialBearingOrigin(t *testing.T) {
	a, out, _ := appFixture(t)
	a.Capture = func(context.Context, string, ...string) ([]byte, error) {
		return []byte("https://SECRET@github.com/org/project"), nil
	}
	if code := a.Run(context.Background(), []string{"init", "--yes"}); code != 1 || strings.Contains(out.String(), "SECRET") {
		t.Fatal(code, out.String())
	}
}

func TestFreshConfigContinuesToInstalledStrategyAndReopenSkipsQuestions(t *testing.T) {
	a, out, plans := appFixture(t)
	s := &testService{}
	a.Strategies = strategy.Registry{"test-service": s}
	a.Capture = func(context.Context, string, ...string) ([]byte, error) {
		return []byte("git@github.com:new/repo.git"), nil
	}
	a.In = strings.NewReader("demo\n\n")
	if code := a.Run(context.Background(), nil); code != 0 {
		t.Fatal(code, out.String())
	}
	if len(*plans) != 1 || (*plans)[0].Project != "demo" || (*plans)[0].Backend != "test-service" {
		t.Fatal(*plans)
	}
	before, err := os.ReadFile(filepath.Join(a.CurrentDir, config.ProjectFilename))
	if err != nil {
		t.Fatal(err)
	}
	a.In = strings.NewReader("")
	out.Reset()
	if code := a.Run(context.Background(), nil); code != 0 {
		t.Fatal(code, out.String())
	}
	after, _ := os.ReadFile(filepath.Join(a.CurrentDir, config.ProjectFilename))
	if !bytes.Equal(before, after) || len(*plans) != 2 || strings.Contains(out.String(), "Compute provider") {
		t.Fatal("reopen repeated setup")
	}
	*plans = nil
	for _, args := range [][]string{{"config", "show"}, {"config", "show", "--project"}, {"config", "show", "--json"}, {"config", "validate", "--project"}, {"config", "path", "--project"}} {
		out.Reset()
		if code := a.Run(context.Background(), args); code != 0 || len(*plans) != 0 {
			t.Fatal(args, code, out.String())
		}
	}
}
