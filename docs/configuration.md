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
It shows an existing repository registration for review before saving it,
without changing account bindings. For an unfamiliar repository it explains shared and
private settings, infers the origin, asks for a name and compute service, and
saves a strict project config. It then asks for private coding-client/account
choices and continues through Box association, native sign-in, coding-only
repository preparation, integration application, and connection in one invocation.
Named shortcuts and noninteractive use of saved registrations do not write a
repository file. `allset init` reopens the review even when `.allset` exists;
keeping that configuration leaves the file unchanged. Noninteractive init
requires `--yes`.

The normal path shows a compact project summary and one confirmation for saved
settings. A new repository asks directly for its inferred name and provider; it
does not present a setup-mode menu. `allset config guide` remains available when
the developer wants agent-assisted configuration. Continuing creates a versioned
private profile and uniquely named Box environment, disables ambient provider
credential injection before compute creation, and journals each stage for retry.
Dry runs and read-only commands never run this flow.

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
| Local project account profiles | Personal/work account choices, Infisical instance/org/project/principal and scoped credential references. Retained as private data under `~/.local/share/box-herdr`, separate from bundled controller code. |
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
overwrite unmanaged edits. First-time setup can also select private absolute
personal skill directories; those paths remain in the private profile, and their
bounded contents are transferred to the same managed projection without entering
the shared manifest.

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

Follow the native browser flow with the project's intended account. A successful
native result is verified before AllSet saves that client's credentials. Failed,
cancelled or mismatched sign-ins remain marked for retry, and background capture
cannot accept them. Use the same command to retry. VM preparation and missing
account bindings remain separate: open with `allset` first, or use
`allset config guide` for incomplete private setup. Sign-in does not resume a
stopped VM and does not accept a TTL. Dry-run remains read-only.
