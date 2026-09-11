package legacy

import (
	"path/filepath"

	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/controller"
)

// InfisicalBinding contains identity metadata and a credential reference, never its contents.
type InfisicalBinding struct {
	Instance       string `json:"instance"`
	OrganizationID string `json:"organization_id"`
	ProjectID      string `json:"project_id"`
	Environment    string `json:"environment"`
	UserEmail      string `json:"user_email,omitempty"`
	PrincipalID    string `json:"principal_id"`
	CredentialRef  string `json:"credential_ref"`
}

// ServiceBinding omits arbitrary commands and environment values from inspection output.
type ServiceBinding struct {
	Name        string   `json:"name"`
	Cwd         string   `json:"cwd"`
	SecretPaths []string `json:"secret_paths"`
	HTTP        *bool    `json:"http,omitempty"`
}

type ProfileInspection struct {
	Kind                string            `json:"kind"`
	Project             config.Project    `json:"registration"`
	ProfilePath         string            `json:"profile_path"`
	Owner               string            `json:"configuration_owner"`
	RuntimeRevision     string            `json:"runtime_revision"`
	AgentAccountProfile string            `json:"agent_account_profile,omitempty"`
	Infisical           *InfisicalBinding `json:"infisical"`
	Base                string            `json:"base,omitempty"`
	Template            string            `json:"template,omitempty"`
	BoxEnvironment      string            `json:"box_environment,omitempty"`
	ShellOnly           bool              `json:"shell_only"`
	SetupCommandCount   int               `json:"setup_command_count"`
	Services            []ServiceBinding  `json:"services"`
	PreviewDomain       string            `json:"preview_domain,omitempty"`
	PreviewService      string            `json:"preview_service,omitempty"`
	GitHubProvider      string            `json:"github_provider,omitempty"`
	ReadinessChecked    bool              `json:"readiness_checked"`
	Omitted             []string          `json:"omitted"`
}

// Inspect reads only the registered profile. It never opens a credential reference,
// account cache, runtime record, or provider connection. Output is a partial view,
// not an editable replacement for the source profile.
func (b Backend) Inspect(p config.Project) (ProfileInspection, error) {
	view := ProfileInspection{Kind: "project-configuration-inspection", Project: p,
		ProfilePath: filepath.Join(b.Root, "projects", p.Name, "profile.json"),
		Owner:       "allset-private-profile", RuntimeRevision: controller.Revision, Services: []ServiceBinding{},
		Omitted: []string{"credential values and account caches", "setup and service command bodies", "environment values", "runtime state", "unrecognized profile fields"}}
	profile, err := b.CheckBinding(p)
	if err != nil {
		return view, err
	}
	var metadata struct {
		Infisical      *InfisicalBinding `json:"infisical"`
		Base           string            `json:"base"`
		Template       string            `json:"template"`
		BoxEnvironment string            `json:"box_environment"`
		ShellOnly      bool              `json:"shell_only"`
		SetupCommands  []string          `json:"setup_commands"`
		Services       []ServiceBinding  `json:"services"`
		PreviewDomain  string            `json:"preview_domain"`
		PreviewService string            `json:"preview_service"`
	}
	if err := config.ReadJSON(view.ProfilePath, &metadata, false); err != nil {
		return view, err
	}
	view.AgentAccountProfile, view.Infisical = profile.AgentProfile, metadata.Infisical
	view.Base, view.Template, view.BoxEnvironment = metadata.Base, metadata.Template, metadata.BoxEnvironment
	view.ShellOnly, view.SetupCommandCount = metadata.ShellOnly, len(metadata.SetupCommands)
	if metadata.Services != nil {
		view.Services = metadata.Services
	}
	view.PreviewDomain, view.PreviewService = metadata.PreviewDomain, metadata.PreviewService
	if profile.Github != nil {
		view.GitHubProvider = profile.Github.Provider
	}
	return view, nil
}
