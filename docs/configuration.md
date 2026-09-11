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

Without a file, an existing repository registration still opens immediately.
`allset init` materializes that registration in the repository without changing
accounts, runtime state, or existing files. For an unfamiliar repository, bare
interactive `allset` runs the same setup flow: infer the origin, ask for a name
and compute service, and save a strict project config. New native provider setup
is not implemented yet, so a missing local Box profile is reported as incomplete
and no VM is provisioned. Dry runs and read-only commands never run this flow.

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
| Repository `.allset` | Shared environment requirements; currently identity/repository/compute and native MCPs. Setup, services, agents, and skills are the next extension. |
| Local project account profiles | Personal/work account choices, Infisical instance/org/project/principal and scoped credential references. Retained as private data under `~/.local/share/box-herdr`, separate from bundled controller code. |
| Secure credential store | Authentication material, supplied separately from source and templates. |
| Local runtime state | Actual VM IDs, SSH identities, worktrees, panes, ports, setup revisions. |

Future reconciliation should reuse the persistent project VM, detect configuration
and dependency changes, and update only owned setup. It must preserve active
agents, isolate concurrent app instances, and never infer credentials from another
project's current login. Defining these fields alone would not implement them.

## MCP declarations

`mcps` is supported in project files and registry entries. See [native MCP setup](mcps.md) for Trigger.dev, custom servers, credential references, and lifecycle behavior.
