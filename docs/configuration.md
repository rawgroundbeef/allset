# Configuration from the current project

```sh
cd ~/Projects/dashboard/dashboard
allset
```

The user brings the terminal. AllSet brings the project environment. Terminal
emulators and session interfaces are not declared as project dependencies.

## Implemented entry point

`.allset` is a JSON file in the repository declaring version, name, repository, and backend.
It can optionally include aliases and a local `allset.schema.json` reference.
The current schema is exported by `allset config schema --project`.

```json
{
  "version": 1,
  "name": "dashboard",
  "repository": "acme/dashboard",
  "backend": "box"
}
```

Bare `allset` and `allset .` discover the nearest file up to the current Git
worktree root, verify the checkout's origin, and resolve the actual compute
strategy. A nested repository cannot inherit its parent's config. A mismatched
or invalid file never falls back to some other saved project.

`init` preserves an existing `.allset` unchanged. Schema exports are named
`allset.schema.json`.

Without a file, bare interactive `allset` starts the guided onboarding flow.
It uses an existing repository registration without asking the developer to
reconfirm known values. For an unfamiliar repository it infers the origin, project
name, and sole available compute service, then
saves a strict project config. It then asks which coding clients to prepare and
continues through Box association, native sign-in and verified account binding, coding-only
repository preparation, integration application, and connection in one invocation.
Named shortcuts and noninteractive use of saved registrations do not write a
repository file. `allset init` reopens the review even when `.allset` exists;
keeping that configuration leaves the file unchanged. Noninteractive init
requires `--yes`.

The normal path shows a compact project summary and asks only for choices it cannot
infer. Project-name and single-provider defaults are accepted silently, and saved
settings are not reconfirmed. `allset config guide` remains available when
the developer wants agent-assisted configuration. Continuing creates a versioned
private profile and uniquely named Box environment, disables ambient provider
credential injection before compute creation, and journals each stage for retry.
Dry runs and read-only commands never run this flow.

In a terminal, coding-agent selection is a checkbox list: arrow keys move,
Space selects, and Enter continues. Codex is selected initially. Set
`ALLSET_ACCESSIBLE=1` to use a plain line-oriented prompt instead.

This is a real config discovery/init path, not yet an automatic installer for
arbitrary projects. Existing setup/services/credentials continue to live in the
local compatibility profiles. The manifest does not accept unsupported fields.

## Inspect and edit with an agent

```sh
allset config show                    # This manifest, otherwise registry
allset config show --project
allset config path --project
allset config validate --project      # Origin and installed provider binding
allset config show dashboard            # Partial local account/service bindings
allset config guide
allset --dry-run --json
```

An agent should read AGENTS.md, runtimes, package scripts, services, and existing
identity bindings; infer routine choices and ask only for missing accounts,
sign-ins, and material decisions. It can create a file noninteractively with
`allset init --name NAME --backend box --yes`. That writes configuration only.
It must distinguish successful validation from successful provisioning or login.

The local shortcut registry is version 3. v1/v2 files load without being rewritten;
the historical terminal preference is discarded. The project file is version 1:
it is a different document with a separate schema, not a single-project registry.
Use `config show --registry`, `config schema`, and `config validate` for the registry.

The default local registry is `~/.config/allset/config.json`.
`XDG_CONFIG_HOME` relocates its parent directory. `--config PATH` overrides
`ALLSET_CONFIG`, which overrides the default path. The command prints the actual
registry path with `allset config path`. Reading configuration never moves files
or touches authentication.

## Target configuration model

| Location | Purpose |
| --- | --- |
| Repository `.allset` | Shared identity/repository/compute, native MCPs, repository-relative skills, and named session secret requirements. |
| Local project account profiles | Coding-client identities verified by native sign-in, Infisical instance/org/project/principal and scoped credential references. Retained as private data under `~/.local/share/box-herdr`, separate from bundled controller code. |
| Secure credential store | Authentication material, supplied separately from source and templates. |
| Local runtime state | Actual VM IDs, SSH identities, worktrees, panes, ports, setup revisions. |

Reconciliation reuses the persistent project VM and completed onboarding stages,
updates only AllSet-owned MCP/skill/session entries, and refuses conflicting user
edits. Context changes affect future client launches; active conversations are not
restarted or switched.

## Skills and session environment

`skills` maps a stable name to a repository-relative directory containing
`SKILL.md`, with optional `agents`. AllSet copies the complete selected directory
to each supported native discovery scope, records its digest, and refuses to
overwrite unmanaged edits. Existing private profiles may also contain explicitly
selected absolute personal skill directories; first-time setup does not ask for
optional personal skills on the default path. Adding new personal directories is
not yet exposed in that minimal flow.

`session_environment` maps an uppercase variable name to an Infisical
`secret_path` and `secret_key`, plus explicit client recipients and optional MCP
names. These are references, not values. First-time setup records the chosen
Infisical instance, identity, project, environment, and private credential-file
reference outside the repository. A project declaring no session variables does
not require Infisical.

## MCP declarations

`mcps` is supported in project files and registry entries. See [native MCP setup](mcps.md) for Trigger.dev, custom servers, credential references, and lifecycle behavior.

## Repair an individual agent login

Run `allset config claude`, `allset config codex`, or `allset config cursor` in
the local project directory. These are explicit native sign-in commands, not
shared configuration edits. They use the selected project's existing running
Box and private account binding. An explicit project or alias can follow the
client: `allset config claude dashboard`.

Follow the native browser flow and choose the account for this project. AllSet
records the identity reported by native status before saving that client's credentials. Failed,
cancelled or mismatched sign-ins remain marked for retry, and background capture
cannot accept them. Use the same command to retry. VM preparation and missing
account bindings remain separate: open with `allset` first, or use
`allset config guide` for incomplete private setup. Sign-in does not resume a
stopped VM and does not accept a TTL. Dry-run remains read-only.
