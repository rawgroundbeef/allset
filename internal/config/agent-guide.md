# Set up AllSet with the user

The entry point is `allset` from the user's local project directory. The user
already chose their terminal or session interface. Do not add a terminal field.

## Inspect before editing

Read the repository's AGENTS.md, setup/startup scripts, package managers, services,
and platform constraints. Then inspect supported configuration:

```sh
allset config path --project
allset config schema --project
allset config show
allset config show --registry
allset config show PROJECT
```

`config show` prints .allset when present, otherwise the shortcut registry.
`config show PROJECT` is partial local-profile inspection. It reads no credentials,
command bodies, environment values, or runtime state. Do not save it over a profile.

## Supported configuration and setup

The repository's .allset supports `version: 1`, `name`, `repository`,
`backend`, optional aliases, `mcps`, and an optional local allset.schema.json reference.

The config is a JSON file named `.allset`, not a directory. Reuse an existing
file. The default local registry is `~/.config/allset/config.json`, respecting
`XDG_CONFIG_HOME`. Override it with `ALLSET_CONFIG` or explicit `--config PATH`.
The local registry uses `version: 3` and a projects array with the same bindings.
Neither declares a terminal. Historical registry v1/v2 files normalize on read
without writes; prior terminal preferences no longer determine connections.

```sh
allset init
allset config validate --project
allset --dry-run --json
```

The normal human entry point is bare `allset`: without a `.allset` file,
interactive open starts the configuration walkthrough automatically, including
for a repository that already has a saved registration. It continues opening
when the environment is configured. Do not require users to remember `init`.

For agent-assisted setup, inspect the supported schema and existing bindings,
explain what you inferred, and ask only for missing project/provider choices.
Use the explicit init command below to save those agreed choices. Clearly report
missing provider/account setup; a saved file does not finish the environment.

Init reuses an existing registration; otherwise it asks for project name/provider.
It creates a file without replacing one or provisioning compute. An authorized
agent can use `allset init --name NAME --backend box --yes` to avoid interactive
questions when the choices are known. Read-only commands and dry runs never init.

**Limitation:** a fully new project's provider/workspace/account preparation is
not implemented yet. An existing local Box profile is still required for opening.
A missing profile after init is an incomplete setup, not a working environment.
Setup/services/previews/agent account/Infisical settings remain in the existing
local controller profiles. Do not copy those wholesale into committed files.
Skill declarations are not implemented yet; unknown fields fail.

## Add project MCPs

Inspect the service's official native MCP docs. Declare `mcps` with either a
supported `preset`, a stdio `command`/`args`, or an HTTPS `url`. For Trigger use
`{"preset":"trigger","project_ref":"proj_FROM_TRIGGER_CONFIG"}`. It is pinned to
4.4.6 and defaults to native --readonly. This hides deploy/trigger/cancel but still
exposes local dev-server controls. The project reference is context, not an
account permission boundary. Do not infer an account from the current laptop login.

Use `agents` to select codex/claude/cursor; omit for all. Credentials use native
login or `env_vars` / `bearer_token_env_var` references to the remote environment.
Never put credential values in URLs, args, files, or inline environment maps.
Arbitrary Infisical injection for custom MCPs is not implemented by this field.

Run `allset mcp list` to inspect declarations, `allset mcp sync` to apply to a
running restored VM, and `allset mcp login SERVER` for a Trigger sign-in.
Append PROJECT when outside its repository. Normal open/connect also applies
configured MCPs. No agent is restarted. Native config conflicts fail rather than
replacing unrelated settings. Use a new session or native reload to pick up tools.

The project manifest is authoritative when present; named shortcuts use the
registry. Keep both current if using both entry forms. Omitted mcps leaves native
settings alone; an explicit empty object removes AllSet-owned entries. Each VM
home belongs to one project. Shared templates must never include native auth or
project-specific config homes. Report separately what was configured, which
account was verified, and whether an actual MCP call succeeded on the VM.

## Preserve identity and work

- The origin and existing saved binding must match the manifest. Never rename a
  project to bypass a mismatch or attach it to another user's saved VM.
- Infer runtime/setup requirements from source, not from another project's state.
- Agent login, GitHub, and Infisical are separate identities. Never use the active
  laptop login as permission to bind a project to it. Ask only when unspecified.
- Keep credentials outside source and shared templates. Use supported sign-in in
  the correct browser/account profile. Never print credential values.
- Respect the current allowance and lifecycle limits before creating/resuming.
  Config creation alone does not authorize upgrades or additional spending.
- Preserve existing worktrees, branches, services, and conversations. Do not
  restart active servers or run migrations to make setup pass.
- Bare allset in a Herdr Local pane prepares a remote workspace and prints its
  sidebar location, then returns. Select that workspace before launching an
  agent so the remote Herdr server can track it. Existing SSH conversations are
  not migrated. Elsewhere, auto opens an ordinary SSH shell in the project directory.
  --attach workspace requests the sidebar handoff explicitly; --attach ssh keeps
  ordinary SSH even in Herdr. --attach herdr opens a separate client and
  --attach terminal attaches to its PTY. Prepare-only and agent sign-in do not
  set up a session manager. Do not migrate or stop existing sessions.
  Ordinary SSH does not guarantee foreground process survival after disconnect.
  VM auto-stop is independent, and paid access alone does not disable it.
- Keep worktrees on persistent VM storage; temporary paths such as /tmp are not
  a safe place for uncommitted work across a VM stop.
- Verify actual repository access, account identity, secret scope, dependencies,
  and app previews separately. Report which checks were performed or blocked.

Next: implement native project requirements and idempotent application so a fresh
checkout can be fully prepared with scoped accounts, tools, services, MCPs, and
skills. Keep provider, credentials, agents, and connection transport independent.
