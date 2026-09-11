# AllSet

Open your project on a remote machine. Bring your terminal and your coding agent.

```sh
cd your-project
allset
```

AllSet reads a shared `.allset` file, resolves your project's environment, and
opens a shell in the terminal you're already using. Account bindings belong to
you; the configuration belongs to the project. Box is the first compute provider.

**Early alpha:** this repository implements strict project discovery, guided
first-time Box setup, explicit coding-client account bindings, native MCP and
skill projection, and scoped Infisical delivery to new client processes. Private
choices and credentials remain under `~/.local/share/box-herdr`; `.allset` holds
only shared requirements. Real provider/browser acceptance is still environment-
dependent and tracked separately from local/mock evidence. Issues and
contributions are welcome.

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

Run `allset` in the project for the continuous onboarding walkthrough. When
`.allset` is missing, it uses the Git identity and sole compute provider as defaults, asks for
the coding clients and expected accounts, displays Box scope/lifetime terms,
uses native sign-in where required, prepares the repository and integrations,
and enters through the caller's selected connection interface. A returning open
reuses completed state and repairs an incomplete onboarding journal.
The coding-agent chooser uses arrow keys, Space, and Enter; Codex starts selected.
Set `ALLSET_ACCESSIBLE=1` for line-oriented prompts.

To work with your preferred coding agent, ask it to run `allset config guide`
in this repository and walk through the supported configuration with you.
`allset init` reopens this review even when `.allset` already exists; there is
no need to delete it. Agents and scripts can use `allset init --yes` to accept
the configuration without prompts. It never replaces an existing file or
creates a VM. Explicit `init` is configuration-only and never performs provider
or account setup.

Opening a workspace shows live preparation phases with a spinner and elapsed
time. File restoration and connection waits explain what is happening; the
finished view summarizes the checkout and saved account bindings. The display
ends before SSH or Herdr takes over. Redirected output and `TERM=dumb` use plain
lines; `NO_COLOR` disables color. Saved logins are labeled as saved, not verified.

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

Commit `.allset` with the project. Keep credentials out of it. Optional `aliases`,
agent-specific MCP declarations, repository-relative `skills`, and
`session_environment` secret references are supported. Agent/provider account
choices and the Infisical identity/credential reference remain private. App setup,
services, and previews remain optional compatibility-profile behavior and do not
gate coding-session onboarding. Unknown fields fail validation.

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
allset config claude          # Repair Claude sign-in for this project
allset config codex           # Sign in to Codex for this project
allset config cursor          # Sign in to Cursor for this project
allset collect               # Save the default worktree's changes locally
allset stop                  # Save results and stop the entire project VM
allset resume                # Resume the saved VM and open the project
```

Then run `codex`, `claude`, or `cursor-agent` in the remote shell and work normally.
AllSet does not require a task prompt or choose an agent for you. Agent login,
GitHub access, and Infisical authentication are separate identities.

To repair an agent login, run `allset config claude` (or `codex` / `cursor`)
from your local project directory. AllSet connects to its existing running Box,
opens the native sign-in flow, verifies the account, saves that client's login,
and returns to your prompt. Use the browser link shown by the client and the
account selected for this project. Outside the repo, use
`allset config claude dashboard`; `allset login dashboard claude` also works.

Sign-in leaves project configuration, other client logins, Infisical, GitHub,
MCP settings and existing agent sessions alone. A missing/stopped machine or
missing client tells you to run `allset` first. It does not create or resume a
VM, install tools, or accept `--ttl`. `--dry-run --json` shows dispatch without
connecting. An interrupted, failed or wrong-account sign-in stays marked as
needing login until a verified `allset config CLIENT` succeeds; background
credential collection cannot silently accept that unverified login.

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
cache monitor; use `allset config CLIENT [PROJECT]` for sign-in, and an unobserved
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
