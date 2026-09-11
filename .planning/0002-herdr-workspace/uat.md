# Herdr workspace handoff UAT

Scope: accepted AllSet handoff behavior; local and real remote checks executed
on 2026-09-10, with interactive agent detection pending. Artifact: fresh `fix/herdr-workspace-handoff` worktree based on
`97b76e3`, including the already-installed plain-SSH changes.

## Prerequisites

Local/mock checks use Go, Python 3.11+, temporary directories, a synthetic dashboard
project, and subprocess doubles. They do not contact Box or use real credentials.
Private remote proof uses the installed Box controller, the existing Joymore
project binding, its existing SSH alias, and Herdr 0.9.0. Joymore reached its
pre-existing auto-stop deadline during implementation. The authorized live fix
resumes that same saved VM with the existing two-hour default and allowance
checks. No new VM is created. Connect proof follows only after readiness.

## Primary workflow

1. In a Herdr Local pane, run `allset joymore` (or bare `allset` in its local repo).
   Expect preparation, the printed sidebar path `joymore > joymore / project`,
   and return to the local prompt with no interactive SSH/nested client.
2. Select that remote workspace in the sidebar. Start the chosen agent there.
   Expect its row under Joymore in Agents when Herdr detects it.
3. Run `allset connect joymore` from Local again. Expect the same workspace;
   preserve its split panes, agents, branches, services, and focus.
4. Outside Herdr, `allset joymore` retains ordinary SSH behavior. Explicit
   `--attach ssh`, `none`, `herdr`, and `terminal` override the default.

The currently running SSH conversation is not migrated. Do not launch test
agents into a worktree already being edited. Interactive agent detection is a
manual acceptance step, not implied by successful workspace creation.

## Guardrails and recovery

- Dry-run emits workspace dispatch without contacting or changing the VM/catalog.
- Connect refuses stopped/unrestored VMs and foreign or relative checkout records.
- Existing workspaces with several panes are reused without focus or pane calls.
- Duplicate project labels or matching machine profiles fail without guessing.
- Lost create/add responses reconcile once without an immediate mutation retry.
- Reconnect through the sidebar preserves work while the VM runs. VM stop ends
  processes; ordinary SSH and workspace attachment are not migration mechanisms.

## Evidence

Pass criterion: AllSet returns from a Herdr Local pane with one usable project
workspace in the existing sidebar, preserving active work, and a new agent
launched there appears under the correct machine.

- **Local/mock:** focused terminal, legacy, and CLI suites passed. They cover
  routing, no interactive handoff, split panes, ownership, stopped/restoring
  machines, timeouts, catalog collisions, and explicit overrides.
- **Local/mock:** full `go test -race ./...`, `go vet ./...`, build, diff whitespace,
  and changed-document link checks passed. The built artifact's dry-run selected
  noninteractive `workspace` with HERDR_ENV=1 and interactive `ssh` without it.
- **Installed:** `/Users/rawgroundbeef/.local/bin/allset` replaced atomically after
  verification; its SHA-256 matches the built artifact. Previous binary backed up
  under the local AllSet backup directory. Artifact SHA-256:
  `472ff46ee3da2b0388888fe20d98fc37b443f894b6aed8a1fdd8abaa7627b5b8`.
- **Real remote:** `allset joymore --attach workspace` resumed the existing saved
  Joymore VM, waited for permanent filesystem restoration, prepared its tooling
  and account context, and returned successfully with
  `In Herdr's sidebar, select joymore > joymore / project.` The resulting pane
  starts in the saved project worktree. Native MCP sync changed zero files and
  reported no restarted agents. Codex has a saved login; Claude/Cursor require
  sign-in, and GitHub access remains unconfigured in this profile.
- **Real remote reconnect:** installed `allset connect joymore --attach workspace`
  returned the same sidebar handoff. Native API inspection before and after
  verified the same machine, workspace, pane, terminal ID, cwd, workspace list,
  and enabled exact host/session catalog entry. Private curated evidence is in
  `/private/tmp/allset-herdr-workspace-verification.json`; no conversation text or
  credentials were captured. Joymore remains running with its normal auto-stop
  deadline, 2026-09-11 04:31:09 UTC. No other project VM was changed.
- **Interactive:** sidebar selection and real agent detection not yet exercised.
- **Unverified:** clean-account provisioning and post-stop credential refresh.
