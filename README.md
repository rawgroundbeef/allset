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
validation, existing project connections, and native MCP configuration. VM setup
still requires a separately installed prototype Box workspace controller at
`~/.local/share/box-herdr`. That controller is not distributed here. A fresh
checkout can build the CLI and create config, but cannot yet provision a complete
environment on a new laptop. [Extraction work](docs/architecture.md#remaining-extraction)
is the next priority. Issues and contributions are welcome.

## Build

Use Go 1.25 or newer:

```sh
go build -o bin/allset ./cmd/allset
./bin/allset --help
```

Python 3.11+, Git, SSH, the Box CLI, and the existing controller are needed for
the current Box adapter. Node/npm is needed for the Trigger.dev MCP preset.
There is no published npm installation to recommend yet.

## Configure a project

```sh
allset init
allset config show
allset config validate --project
allset --dry-run --json
```

An agent can inspect the repository and use `allset config guide` to help write
the configuration with you. `init` infers the Git origin and reuses a saved
project binding when available. It never replaces an existing file or creates a
VM. Missing provider setup is reported as incomplete.

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
fields; unknown fields fail validation. Existing controller profiles retain
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
allset login dashboard codex  # Agent sign-in through the existing controller
allset collect               # Save the default worktree's changes locally
allset stop                  # Save results and stop the entire project VM
allset resume                # Resume the saved VM and open the project
```

Then run `codex`, `claude`, or `cursor-agent` in the remote shell and work normally.
AllSet does not require a task prompt or choose an agent for you. Agent login,
GitHub access, and Infisical authentication are separate identities.

The default connection is ordinary SSH: its agent processes are **not guaranteed
to survive disconnecting**. For existing persistent remote Herdr sessions, use
`allset --attach herdr`; Ctrl+b, then q detaches the client. `--attach none`
prepares without attaching. No mode takes over another client or restarts agents.
Stopping the VM ends every process even though its files persist.

The current controller retains a maximum two-hour trial auto-stop deadline.
Opening an already running VM does not extend that deadline. Status reports VM
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

These tests use temporary files and fake providers. They do not create VMs or
use real credentials. See [SECURITY.md](SECURITY.md) for private vulnerability
reports and [LICENSE](LICENSE) for the MIT license.
