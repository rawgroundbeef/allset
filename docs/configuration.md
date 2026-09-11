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

Without a file, bare interactive `allset` starts the guided configuration flow.
It shows an existing repository registration for review before saving it,
without changing account bindings. For an unfamiliar repository it explains shared and
private settings, infers the origin, asks for a name and compute service, and
saves a strict project config. Setup then returns without creating, resuming,
or connecting to a VM. Run `allset` again to open the environment.
Named shortcuts and noninteractive use of saved registrations do not write a
repository file. `allset init` reopens the review even when `.allset` exists;
keeping that configuration leaves the file unchanged. Noninteractive init
requires `--yes`.

The review offers terminal setup, a copyable prompt for the user's preferred
coding agent, or cancellation. The agent prompt asks it to run `allset config
guide`, inspect the repository and bindings, and discuss supported settings.
Selecting this handoff changes no files and starts no agent or VM. New native provider setup
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
