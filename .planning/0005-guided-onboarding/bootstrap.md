# Implement remote coding session onboarding

The user approved the corrected UAT on 2026-09-11. Build a continuous first-time
`allset` flow that connects chosen coding clients and integrations once, then
automatically supplies their credentials, MCPs, skills, and secrets to the
intended remote session. Returning entry should reuse this setup.

## Workspace and read order

Use a fresh implementation worktree under the repository's AGENTS.md rules.
The planning branch is `feat/guided-onboarding`; its code base was `origin/main`
at `c08116394127b44ef87d2777ce6b7d9ebbc5536f`. Start from the final planning commit
so these documents and glossary travel with implementation. Verify current Git
state; preserve occupied worktrees and unrelated changes.

Read in order:

1. `AGENTS.md` — ownership, workflow, tools, verification, and delegation rules.
2. `CONTEXT.md` — project environment, account binding, and session context.
3. `.planning/0005-guided-onboarding/discovery.md` — corrected user goal and
   current code/native evidence.
4. `.planning/0005-guided-onboarding/decisions.md` — accepted scope; D-07–D-10
   supersede the app-focused interpretation.
5. `.planning/0005-guided-onboarding/uat.md` — user-approved observable contract.
6. `.planning/0005-guided-onboarding/threat-model.md` — controls that tests must
   prove at the credential/provider/session boundaries.
7. `.planning/0005-guided-onboarding/prd.md` — requirements, module ownership,
   implementation sequence, delivery and verification.
8. `.planning/0005-guided-onboarding/follow-ups.md` and `plan-review.md` — deferred
   provider research, evidence limits, and planning consistency findings.
9. `docs/architecture.md`, `docs/configuration.md`, `docs/mcps.md` — currently
   shipped behavior, to be updated with the actual final implementation.

Load repository-local `allset-patterns`, `allset-domain`,
`allset-threat-model`, and `allset-uat` before their relevant work. Use
`allset-review` for final review. Do not load an unrelated app's standards or
delegate without explicit user permission.

## The finish line

A developer with no AllSet private profile runs bare `allset`, selects clients
and connects missing accounts/integrations through native flows, enters their
owned Box environment, and starts a configured client normally. The first turn
can use the correct model account, selected MCP, skill, and scoped secret access.
The next entry reuses the setup automatically.

There is no programming-language gate, app dependency install, dev server,
preview, or database migration in this completion criterion. Do not revive the
superseded app-hosting plan or remove existing optional app features.

Keep `allset init` configuration-only. The user already chose their terminal;
preserve invocation/caller transport and native agent conversation semantics.
Preparing an environment is not permission to start an arbitrary conversation
or redirect a running one. Native browser login and workspace trust may still
need user interaction; guide them in place and remember completed choices.

## Execution sequence

1. Add explicit typed shared/private/journal/context contracts behind existing
   module boundaries; make missing setup distinct from corrupt/foreign bindings.
2. Implement no-profile Box/account setup and coding-only repository preparation.
3. Implement native client launch context, managed MCP/skill application, and
   scoped secret delivery. Preserve native argv/TTY/exit/resume behavior.
4. Wire continuous first-time UX and warm reuse; implement recovery and truthful
   status, update current docs/guide/schema/help, then execute verification.

One coherent branch; internal commits can follow this order. Do not mark the
task finished after writing a manifest or making a cleaner menu. Follow the PRD
module table for verified paths; proposed modules are new, not hidden features.

## Important code-backed constraints

- `internal/cli/setup.go` currently ends first run at save/agent/cancel.
  `internal/cli/cli.go` sends missing-manifest open to configuration-only init.
- `internal/strategies/box/box.go` currently validates a pre-existing private
  profile before planning. New setup needs an explicit mutation path without
  weakening Validate/Inspect/Status/Diagnose/Plan's read-only contracts.
- `internal/controller/runtime/profiles.py` couples Infisical to app profiles;
  `project_shell.py`/`worker.py` currently run app setup while preparing a
  checkout. Separate coding preparation and session secret access deliberately.
- `agent_auth.py` has expected-account validation, project cache ownership,
  needs-login markers, and capture locks. Retain them while adding context-aware
  first-time bindings/launch. Standard-home assumptions are not session isolation.
- `internal/mcps/runtime.py` currently writes standard native homes; env refs
  alone do not supply values. Adapt target ownership and secret delivery together.
- Skill declarations/application are not implemented in current main. Build and
  verify selected native discovery; a copied folder is not sufficient proof.
- Native Box `env new` defaults to stored-credential injection. For a new
  AllSet-owned provider environment, explicitly configure/verify no ambient
  account injection before provisioning; apply selected account bindings through
  the intended adapters. Do not alter unrelated/default provider environments.
- Use a clean provider base for a brand-new project; no private snapshot is a
  prerequisite. Existing creation locks, allowance checks, bounded lifetime,
  filesystem restoration, and timeout reconciliation remain mandatory.
- Normal opening must not send test prompts or arbitrary tool calls just to
  claim readiness. Real end-to-end UAT proves these capabilities when authorized;
  ordinary status uses supported safe observations.
- A ready remote shell is not a claim that every selected account/integration is
  usable. Report pending/skipped connections separately and repair only those.

## Native evidence and implementation checks

Discovery records links for Codex/Claude/Cursor MCPs, skills, configuration and
Infisical injection. Installed Box CLI help was inspected without provider calls.
The public Box documentation URL could not be opened through the browser tool;
native help is the provider evidence used so far.

Verify installed client versions and actual auth/MCP/skill scope behavior before
using config-home overrides. Avoid hardcoding a universal home layout or
assuming a wrapper preserves every resume behavior without tests. If a native
capability cannot fulfill the contract, report the specific limitation and fix
the upstream plan instead of silently dropping the feature.

## Verification and authorized scope

Run from the implementation repo root:

```sh
go test -race ./...
go vet ./...
go build -o bin/allset ./cmd/allset
```

Format Go; use Python 3.11+ for runtime tests. Extend meaningful fault tests and
the offline packaged harness through `scripts/build-release.py` and
`scripts/test-container.py`. Keep native/browser/model/provider proof distinct
from mocks. Use the approved UAT for real first-turn and warm-return acceptance.

Planning has not authorized real VM/account operations, spending, releases,
publishing, or app/database mutations. Prepare local/offline work and precise
real-test conditions first, then request any missing actual account/budget input.
No user should paste credentials or do shell work the agent can perform.

Update `PROGRESS.md`, record genuine out-of-scope findings in follow-ups, and
perform the repository-local final review. Planning review was not independent;
there was no delegation authorization. Do not call an implementation complete
while required real acceptance remains unverified.

Implement from these documents, not remembered conversation.
