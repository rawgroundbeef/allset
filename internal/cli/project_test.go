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

func TestBareOpenCreatesMissingManifestFromSavedBindingAndContinues(t *testing.T) {
	for _, args := range [][]string{nil, {"."}, {"open"}, {"open", "."}} {
		a, out, plans := appFixture(t)
		root := a.CurrentDir
		a.CurrentDir = filepath.Join(root, "apps", "admin")
		if err := os.MkdirAll(a.CurrentDir, 0700); err != nil {
			t.Fatal(err)
		}
		registry, err := config.Load(a.ConfigPath)
		if err != nil {
			t.Fatal(err)
		}
		before, err := os.ReadFile(a.ConfigPath)
		if err != nil {
			t.Fatal(err)
		}
		input := strings.NewReader("must not be consumed\n")
		a.In = input
		if code := a.Run(context.Background(), args); code != 0 {
			t.Fatal(args, code, out.String())
		}
		manifest, err := config.LoadProject(filepath.Join(root, config.ProjectFilename))
		if err != nil || manifest.Name != registry.Projects[0].Name || manifest.Repository != registry.Projects[0].Repository ||
			manifest.Backend != registry.Projects[0].Backend || strings.Join(manifest.Aliases, ",") != "joy" {
			t.Fatal("saved project binding was not preserved", manifest, err)
		}
		if len(*plans) != 1 || (*plans)[0].Project != manifest.Name || input.Len() != len("must not be consumed\n") {
			t.Fatal("open did not reuse its saved binding without questions")
		}
		after, _ := os.ReadFile(a.ConfigPath)
		if !bytes.Equal(before, after) || strings.Contains(out.String(), "SECRET") {
			t.Fatal("registration changed or private data leaked")
		}
		if _, err := os.Stat(filepath.Join(a.CurrentDir, config.ProjectFilename)); !errors.Is(err, os.ErrNotExist) {
			t.Fatal("config was not bounded to the project root")
		}
	}
}

func TestOnlyInteractiveCurrentProjectOpenCreatesMissingManifest(t *testing.T) {
	for _, args := range [][]string{{"--dry-run", "--json"}, {"status", "--cached"}, {"doctor", "--offline"}, {"dashboard"}} {
		a, out, _ := appFixture(t)
		want := 0
		if args[0] == "doctor" {
			want = 1 // The fixture intentionally lacks the native Box executable.
		}
		if code := a.Run(context.Background(), args); code != want {
			t.Fatal(args, code, out.String())
		}
		if _, err := os.Stat(filepath.Join(a.CurrentDir, config.ProjectFilename)); !errors.Is(err, os.ErrNotExist) {
			t.Fatal("read-only or named command wrote a repository manifest", args, err)
		}
	}
	// Preserve scripted use of existing registrations without an implicit write.
	a, out, plans := appFixture(t)
	a.Interactive = false
	if code := a.Run(context.Background(), []string{"--attach", "none"}); code != 0 || len(*plans) != 1 {
		t.Fatal(code, out.String())
	}
	if _, err := os.Stat(filepath.Join(a.CurrentDir, config.ProjectFilename)); !errors.Is(err, os.ErrNotExist) {
		t.Fatal("noninteractive open wrote a repository manifest", err)
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
	if !strings.Contains(out.String(), "Compute provider") || !strings.Contains(out.String(), "allset config guide") ||
		!strings.Contains(out.String(), "Account choices and credentials stay private") {
		t.Fatal("guided setup or agent instructions were missing")
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
