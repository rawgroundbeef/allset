# Setup and startup UX acceptance

Status: local/mock checks executed, 2026-09-11. Visual acceptance in the user's
normal terminal and live cloud startup remain unverified.

## Prerequisites

- Branch `fix/setup-review`, based on main `c1ceb59`; Go, Python 3.11+ and Docker.
- Build with `python3 scripts/build-release.py NEW_OUTPUT_DIRECTORY`; run
  `python3 scripts/test-container.py PATH_TO_LINUX_ARCHIVE` for the Docker engine
  architecture. The fixture uses synthetic account data, no network, no host
  home, and no provider mutation. It preserves the project branch and files.

## Primary workflow

1. In a fixture repo with a saved registration but no `.allset`, run `allset`
   in a terminal. Review the project identity/provider/MCP names. Choose cancel
   or the coding-agent prompt; verify no file, provider, account or cache change.
2. Repeat and choose terminal configuration. Verify `.allset` contains the saved
   settings, then the process exits without opening a VM. An unfamiliar repo
   asks for name/provider and reports any missing private setup as incomplete.
3. Run `allset init` with that file present. Choose the agent prompt and verify
   the manifest and registrations are byte-identical. No agent or VM starts.
4. Run `allset --attach none` separately. Observe readable preparation phases
   and a summary; native MCP JSON is absent. Verify selected synthetic login
   restore and native MCP settings, with branch/uncommitted work unchanged.
5. Run preparation through a PTY. Observe changing spinner frames during waits,
   elapsed time and completed phases, then clean final output. Redirected output
   has no ANSI controls. `NO_COLOR` removes color while keeping feedback.
6. Repeat workspace connect: only one machine/workspace registration exists.
   Stopped/foreign bindings fail without resume or fallback. Collection preserves
   the checkout and index. These are existing preservation checks.

## Failure and handoff checks

- Go-driven runtime PTYs exercise success, failure and interruption; no redraw
  thread or active display survives the scope. The native SSH/Herdr bridge checks
  this boundary before its client starts. No failure reports workspace success.
- MCP failure retains the shipped runtime's curated conflict message and does
  not print raw transport output or successful protocol JSON.
- EOF/cancellation during first setup leaves files/private bindings unchanged.
- Ctrl+C stops the local wait; it does not request a VM stop or replacement.
  A resume already submitted may continue remotely. Reconcile the same project.

## Evidence and pass criterion

Go race tests, vet and build passed. The Linux arm64 archive passed the offline
container flow, including PTY animation. Provider CLI/SSH readiness are simulated;
actual bundled scripts perform Git, synthetic account and native MCP file work.
No real agent authentication, MCP tool availability or filesystem hydration is
proven here. Local code review was not independent.

Pass: first-run setup is reviewable and cannot open a VM; a separate configured
run gives truthful progress and releases the terminal before native attachment.
