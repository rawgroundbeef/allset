package config

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestDiscoveryDoesNotCrossGitWorktreeBoundaries(t *testing.T) {
	root, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(root, ".git"), 0700); err != nil {
		t.Fatal(err)
	}
	manifest := Manifest{Version: 1, Project: registry().Projects[0]}
	if err := WriteProject(filepath.Join(root, ProjectFilename), manifest); err != nil {
		t.Fatal(err)
	}
	child := filepath.Join(root, "apps", "web")
	if err := os.MkdirAll(child, 0700); err != nil {
		t.Fatal(err)
	}
	l, err := Discover(child)
	if err != nil || l.Root != root || l.ManifestPath != filepath.Join(root, ProjectFilename) {
		t.Fatal(l, err)
	}
	// A nested checkout or linked worktree must not inherit the outer manifest.
	if err := os.WriteFile(filepath.Join(child, ".git"), []byte("gitdir: /not/read/by/discovery"), 0600); err != nil {
		t.Fatal(err)
	}
	l, err = Discover(child)
	if err != nil || l.Root != child || l.ManifestPath != "" {
		t.Fatal(l, err)
	}
}

func TestManifestSessionRequirementsAreStrictAndContainNoValues(t *testing.T) {
	valid := Manifest{Version: 1, Project: Project{Name: "demo", Repository: "acme/demo", Backend: "box",
		MCPs:   map[string]MCP{"tools": {Command: "/opt/tools", EnvVars: []string{"TOOLS_TOKEN"}}},
		Skills: map[string]Skill{"fixture": {Path: ".agents/skills/fixture", Agents: []string{"codex"}}},
		SessionEnvironment: map[string]SessionVariable{"TOOLS_TOKEN": {
			SecretPath: "/allset", SecretKey: "TOOLS_TOKEN", Agents: []string{"codex"}, MCPs: []string{"tools"},
		}},
	}}
	if err := valid.Validate(); err != nil {
		t.Fatal(err)
	}
	for _, mutate := range []func(*Manifest){
		func(m *Manifest) { m.Skills["fixture"] = Skill{Path: "../private"} },
		func(m *Manifest) { m.SessionEnvironment["token"] = m.SessionEnvironment["TOOLS_TOKEN"] },
		func(m *Manifest) {
			value := m.SessionEnvironment["TOOLS_TOKEN"]
			value.MCPs = []string{"missing"}
			m.SessionEnvironment["TOOLS_TOKEN"] = value
		},
		func(m *Manifest) {
			m.MCPs["tools"] = MCP{Command: "/opt/tools", EnvVars: []string{"OTHER_TOKEN"}}
		},
		func(m *Manifest) {
			m.MCPs["tools"] = MCP{Command: "/opt/tools", EnvVars: []string{"TOOLS_TOKEN"}, Agents: []string{"claude"}}
		},
		func(m *Manifest) {
			value := m.SessionEnvironment["TOOLS_TOKEN"]
			value.Agents = []string{"codex", "codex"}
			m.SessionEnvironment["TOOLS_TOKEN"] = value
		},
	} {
		copy := valid
		copy.MCPs = map[string]MCP{"tools": valid.MCPs["tools"]}
		copy.Skills = map[string]Skill{"fixture": valid.Skills["fixture"]}
		copy.SessionEnvironment = map[string]SessionVariable{"TOOLS_TOKEN": valid.SessionEnvironment["TOOLS_TOKEN"]}
		mutate(&copy)
		if err := copy.Validate(); err == nil {
			t.Fatal("invalid session requirement accepted", copy)
		}
	}
}

func TestProjectRejectsTerminalUnknownSecretsAndSymlinkAndNeverClobbers(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, ProjectFilename)
	base := `{"version":1,"name":"shop-app","repository":"example/shop","backend":"box"`
	for _, ending := range []string{`,"terminal":"herdr"}`, `,"token":"SECRET"}`, `,"version":2}`, `,"setup":["unimplemented"]}`} {
		if err := os.WriteFile(path, []byte(base+ending), 0600); err != nil {
			t.Fatal(err)
		}
		if _, err := LoadProject(path); err == nil || bytes.Contains([]byte(err.Error()), []byte("SECRET")) {
			t.Fatal(err)
		}
	}
	os.Remove(path)
	m := Manifest{Version: 1, Project: registry().Projects[0]}
	if err := WriteProject(path, m); err != nil {
		t.Fatal(err)
	}
	before, _ := os.ReadFile(path)
	m.Name = "other"
	if WriteProject(path, m) == nil {
		t.Fatal("existing project overwritten")
	}
	after, _ := os.ReadFile(path)
	if !bytes.Equal(before, after) {
		t.Fatal("project changed")
	}
	link := filepath.Join(root, "link.json")
	if err := os.Symlink(path, link); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadProject(link); err == nil {
		t.Fatal("symlink accepted")
	}
}

func TestManifestCannotRebindSavedRepositoryOrAccountIdentity(t *testing.T) {
	f := registry()
	for _, p := range []Project{
		{Name: "shop-app", Repository: "other/repo", Backend: "box"},
		{Name: "other", Repository: "example/shop", Backend: "box"},
		{Name: "shop", Repository: "other/repo", Backend: "box"},
		{Name: "shop-app", Repository: "example/shop", Backend: "another-service"},
	} {
		if CheckLocalBinding(f, p) == nil {
			t.Fatal("accepted conflicting binding", p)
		}
	}
	if err := CheckLocalBinding(f, f.Projects[0]); err != nil {
		t.Fatal(err)
	}
}

func TestV2PreferencesMigrateReadOnlyAndV3RejectsTerminal(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.json")
	raw := []byte(`{"version":2,"projects":[{"name":"dashboard","repository":"acme/dashboard","backend":"box","terminal":"herdr"}]}`)
	if err := os.WriteFile(path, raw, 0600); err != nil {
		t.Fatal(err)
	}
	f, err := Load(path)
	if err != nil || f.Version != 3 || f.Projects[0].Backend != "box" {
		t.Fatal(f, err)
	}
	after, _ := os.ReadFile(path)
	if !bytes.Equal(raw, after) {
		t.Fatal("migration wrote on read")
	}
	raw = bytes.Replace(raw, []byte(`"version":2`), []byte(`"version":3`), 1)
	if err := os.WriteFile(path, raw, 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(path); err == nil {
		t.Fatal("new registry accepted a terminal preference")
	}
}
