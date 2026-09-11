# AllSet

Open your project on a remote machine. Bring your terminal and your coding agent.

```sh
cd your-project
allset
```

AllSet reads a shared `.allset` file, resolves your project's environment, and
opens a shell in the terminal you're already using. Account bindings belong to
you; the configuration belongs to the project. Box is the first compute provider.

**Early alpha:** this repository implements configuration discovery, strict
validation, existing project connections, and native MCP configuration. The Box
workspace controller is included in the executable. Existing private project
profiles and credentials still live under `~/.local/share/box-herdr`; creating
those bindings from `.allset` is not implemented yet. A fresh checkout can build
the complete CLI, but setting up an unfamiliar project still needs that private
configuration. See [remaining work](docs/architecture.md#remaining-extraction).
Issues and contributions are welcome.

## Build

Use Go 1.25 or newer:

```sh
go build -o bin/allset ./cmd/allset
./bin/allset --help
```

Python 3.11+, Git, SSH, and the native Box CLI at `~/.ascii/bin/box` are needed for
the current Box adapter. Herdr modes also require its native executable at
`~/.local/share/box-herdr/bin/herdr`. Node/npm is needed for the Trigger.dev MCP preset.
There is no published npm installation to recommend yet.

Controller source is versioned in `internal/controller/runtime` and embedded at
build time. Running a lifecycle command extracts a verified copy to
`~/.cache/allset/controller/<revision>` (respecting `XDG_CACHE_HOME`). Inspection
and dry-run do not install it. AllSet does not execute the old private controller
folder. Keep the existing state directory: it still holds your project bindings,
credentials, machine records, and native Herdr installation.

## Configure a project

```sh
allset                       # Start setup if .allset is missing, otherwise open
allset config show
allset config validate --project
allset --dry-run --json
```

Run `allset` in the project for the guided configuration walkthrough. When
`.allset` is missing, interactive open starts setup: it infers the Git origin,
reuses saved project settings when available, or asks for the project name and
compute provider. It saves `.allset` and continues opening when the environment
is configured. Later runs use that file without repeating setup.

To work with your preferred coding agent, ask it to run `allset config guide`
in this repository and walk through the supported configuration with you.
`allset init` remains an explicit configuration-only command for agents and
scripts. It never replaces an existing file or creates a VM. The current
walkthrough covers project configuration; missing provider/account setup is
still reported as incomplete.

```json
{
  "version": 1,
  "name": "dashboard",
  "repository": "acme/dashboard",
  "backend": "box",
  "mcps": {
    "trigger": {
      "preset": "trigger",
      "project_ref": "proj_YOUR_PROJECT"
    }
  }
}
```

Commit `.allset` with the project. Keep credentials out of it. Optional `aliases`
and agent-specific MCP declarations are supported. Setup commands, services,
previews, agent accounts, Infisical bindings, and skills are not yet declarative
fields; unknown fields fail validation. Existing private project profiles retain
those settings privately.

Named shortcuts use `~/.config/allset/config.json`, respecting `XDG_CONFIG_HOME`.
Override it with `ALLSET_CONFIG` or `--config PATH`. Export editor schemas with
`allset config schema --project` and `allset config schema`.
See [configuration](docs/configuration.md) and [MCPs](docs/mcps.md).

## Work in an existing environment

Run these commands locally, from a normal terminal, cmux, or a Herdr Local pane:

```sh
allset                       # Open or resume this project's saved environment
allset dashboard             # Use a registered shortcut
allset status                # VM state; does not start or stop it
allset connect               # Connect only; refuses a stopped VM
allset mcp sync               # Apply declared MCPs on the running VM
allset mcp login trigger      # Project-specific native Trigger sign-in
allset login dashboard codex  # Native agent sign-in for the bound project
allset collect               # Save the default worktree's changes locally
allset stop                  # Save results and stop the entire project VM
allset resume                # Resume the saved VM and open the project
```

Then run `codex`, `claude`, or `cursor-agent` in the remote shell and work normally.
AllSet does not require a task prompt or choose an agent for you. Agent login,
GitHub access, and Infisical authentication are separate identities.

In a Herdr Local pane, `allset` prepares the project's remote Herdr workspace and
returns to the local prompt. Select the printed machine and workspace in Herdr's
sidebar, then launch your agent there. For example, `allset dashboard` prints
`dashboard > dashboard / project`. The remote Herdr server owns the pane, so its
agents can appear under that machine in the Agents list. Existing workspaces,
including split panes and running agents, are reused without changing focus.
An agent already running behind ordinary SSH stays in its original session.

Elsewhere, the default is an ordinary SSH shell in the project directory, with
no session manager installed. Exit the shell to disconnect; run `allset` to
reconnect. Ordinary SSH does not guarantee foreground process survival.

`--attach workspace` explicitly requests the sidebar handoff from any terminal.
`--attach ssh` explicitly opens ordinary SSH even in Herdr. `--attach herdr` opens
a separate Herdr client; `--attach terminal` attaches to a remote Herdr PTY.
`--attach none` prepares tools, credentials, repository, and declared MCPs without
session setup or attachment. Agent sign-in also does not require Herdr. No mode
automatically launches an agent or takes over an existing terminal.

The handoff uses Herdr's native machine catalog and a named remote session. It
honors the caller's `HERDR_CONFIG_PATH`; it never uses the UI's selected machine
to choose a project or account. Herdr currently requires the sidebar click to
select that machine in the existing window. See [Herdr machine connections](https://herdr.dev/docs/connecting-machines/).
Stopping the VM ends its processes. The returning handoff has no attached login
cache monitor; use `allset login PROJECT AGENT` for sign-in, and an unobserved
credential refresh may require sign-in again after a later VM resume.

Create/resume still defaults to a two-hour auto-stop deadline. Opening an already
running VM preserves its provider deadline, including an explicitly disabled
auto-stop. Box's trial requires a deadline of at most two hours; paid access allows
it to be disabled through native Box controls. AllSet does not disable it merely
because an account has paid. Worktrees belong on persistent storage, not `/tmp`.
Status reports VM
state only; it does not prove app, credential, or preview readiness. Collection
currently targets the default worktree, not an arbitrary agent worktree.

## Contribute

Start with [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and
[architecture](docs/architecture.md). The [public alpha plan](docs/public-launch-plan.md)
records the next work and current limits. Run:

```sh
go test -race ./...
go vet ./...
go build -o bin/allset ./cmd/allset
```

These tests use temporary files and fake providers. The optional
[container check](CONTRIBUTING.md#packaged-container-check) tests a release archive
without the source checkout or your private controller. They do not create VMs or
use real credentials. See [SECURITY.md](SECURITY.md) for private vulnerability
reports and [LICENSE](LICENSE) for the MIT license.
