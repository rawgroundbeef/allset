package legacy

import (
	"encoding/json"
	"path/filepath"
	"strings"
	"testing"
)

func TestInspectionWhitelistsMetadataWithoutOpeningCredentialReference(t *testing.T) {
	b, p := fixture(t)
	missingCredential := filepath.Join(t.TempDir(), "not-present", "auth.json")
	put(t, b.Root, "projects/dashboard/profile.json", map[string]any{
		"name": p.Name, "repository": p.Repository, "agent_profile": "dashboard-work",
		"github": map[string]string{"provider": "box"},
		"infisical": map[string]string{
			"instance": "https://app.infisical.com", "organization_id": "work-org",
			"project_id": "work-project", "environment": "dev", "user_email": "user@work.example",
			"principal_id": "work-user", "credential_ref": missingCredential, "token": "SECRET_TOKEN",
		},
		"setup_commands": []string{"echo SECRET_COMMAND"},
		"services": []map[string]any{{"name": "app", "cwd": "apps/app", "secret_paths": []string{"/app"},
			"command": []string{"echo", "SECRET_ARG"}, "env": map[string]string{"TOKEN": "SECRET_ENV"}}},
		"credentials": "SECRET_EXTRA", "preview_domain": "dashboard.localhost",
	})
	view, err := b.Inspect(p)
	if err != nil {
		t.Fatal(err)
	}
	encoded, err := json.Marshal(view)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(encoded), "SECRET") {
		t.Fatal("private/unrecognized profile values were exposed")
	}
	if view.Infisical.CredentialRef != missingCredential || view.Infisical.OrganizationID != "work-org" ||
		view.AgentAccountProfile != "dashboard-work" || view.SetupCommandCount != 1 ||
		len(view.Services) != 1 || view.Services[0].SecretPaths[0] != "/app" || view.ReadinessChecked {
		t.Fatal(view)
	}
	wrong := p
	wrong.Repository = "personal/different"
	if _, err := b.Inspect(wrong); err == nil {
		t.Fatal("inspected an account after a repository binding mismatch")
	}
}

func TestShellOnlyInspectionDoesNotInventAuthentication(t *testing.T) {
	b, p := fixture(t)
	put(t, b.Root, "projects/dashboard/profile.json", map[string]any{
		"name": p.Name, "repository": p.Repository, "shell_only": true, "infisical": nil,
		"setup_commands": []string{}, "services": []string{},
	})
	v, err := b.Inspect(p)
	if err != nil || v.Infisical != nil || !v.ShellOnly || v.Services == nil || v.ReadinessChecked {
		t.Fatal(v, err)
	}
}
