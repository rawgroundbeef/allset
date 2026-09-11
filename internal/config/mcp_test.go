package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestMCPValidation(t *testing.T) {
	for _, tc := range []struct {
		name  string
		m     MCP
		valid bool
	}{
		{"trigger", MCP{Preset: "trigger", ProjectRef: "proj_work"}, true},
		{"missing-project", MCP{Preset: "trigger"}, false},
		{"mixed", MCP{Preset: "trigger", ProjectRef: "proj_work", Command: "npx"}, false},
		{"https", MCP{URL: "https://example.com/mcp", BearerTokenEnvVar: "WORK_TOKEN"}, true},
		{"embedded", MCP{URL: "https://user:password@example.com/mcp"}, false},
		{"query-token", MCP{URL: "https://example.com/?token=abc"}, false},
		{"stdio", MCP{Command: "npx", Args: []string{"-y", "server@1.2.3"}, EnvVars: []string{"WORK_TOKEN"}}, true},
		{"value", MCP{Command: "server", EnvVars: []string{"secret-value"}}, false},
		{"unknown-agent", MCP{Command: "server", Agents: []string{"whatever"}}, false},
		{"both", MCP{Command: "server", URL: "https://example.com"}, false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			err := ValidateMCPs(map[string]MCP{"server": tc.m})
			if (err == nil) != tc.valid {
				t.Fatalf("valid=%v: %v", tc.valid, err)
			}
		})
	}
}

func TestHTTPOAuthIsExplicitAndCannotMixWithBearerCredentials(t *testing.T) {
	yes := true
	no := false
	servers := map[string]MCP{"docs": {URL: "https://example.test/mcp", OAuth: &yes}}
	if err := ValidateMCPs(servers); err != nil {
		t.Fatal(err)
	}
	server := servers["docs"]
	server.BearerTokenEnvVar = "DOCS_TOKEN"
	servers["docs"] = server
	if err := ValidateMCPs(servers); err == nil {
		t.Fatal("OAuth and bearer token accepted together")
	}
	servers["docs"] = MCP{URL: "https://example.test/mcp", OAuth: &no}
	if err := ValidateMCPs(servers); err == nil {
		t.Fatal("explicit false OAuth accepted as configured authentication")
	}
}
func TestMCPUnknownCredentialFieldsRejected(t *testing.T) {
	path := filepath.Join(t.TempDir(), ".allset")
	os.WriteFile(path, []byte(`{"version":1,"name":"dashboard","repository":"acme/dashboard","backend":"box","mcps":{"trigger":{"preset":"trigger","project_ref":"proj_work","token":"must-not-save"}}}`), 0600)
	if _, err := LoadProject(path); err == nil {
		t.Fatal("accepted an inline credential")
	}
}
