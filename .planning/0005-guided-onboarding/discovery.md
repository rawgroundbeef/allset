# Remote coding session onboarding

Status: discovery complete; corrected UAT approved, 2026-09-11. No implementation or
live environment operation has been performed by this slice.

## User's outcome

The user clarified the product goal:

> all we care about is setting up their llm's and biniding those creds automatically to their session. mcps, skill, infisical, secrets, whatever. just get them in their remote box and working instantly.

AllSet prepares the developer's remote coding tools and connects the accounts,
MCPs, skills, and secret access those tools need. The developer configures these
once; the intended remote agent session receives them automatically. Entering
the environment and using a configured coding client must not require a second
setup walkthrough, manually copying tokens, syncing MCPs, or remembering a
secret-injection command.

This is the authoritative scope correction. Application dependency installation,
framework detection, service startup, app health, and previews are not completion
requirements. The earlier interpretation of "correct" as requiring a running app
was superseded by this explicit clarification. Programming language is irrelevant
to admission into a remote coding environment.

## Intended workflow

1. Run bare `allset` in the project.
2. Select coding clients and connect missing accounts/integrations through native
   flows. Show existing project-authorized choices and reuse them.
3. AllSet prepares or reuses the owned Box environment, repository access, coding
   tools, and selected integration context.
4. Enter the environment through the developer's chosen interface. Starting a
   configured client normally supplies its correct context before its first turn.
5. Repeat entry or launch another session without repeating setup; repair only
   an expired or incomplete connection.

There is one continuous first-time flow, including a developer without any
private AllSet profile. Shared requirements and personal account choices stay
separate. Explicit `allset init` remains configuration-only.

"Instantly" means minimal interaction and a fast return path that reuses verified
state instead of reinstalling tools or repeating login. Measure cold preparation,
warm entry, and native agent startup separately. Do not claim zero cloud startup
or browser-login latency. No numerical latency guarantee has been chosen.

## Boundaries

- **Project environment:** the developer/project-owned remote place to work.
- **Account binding:** the saved developer-authorized association with an external
  service identity. Selecting a coding-client account does not select GitHub,
  Infisical, MCP, or compute identities.
- **Session context:** the configured client identity, integrations, skills, and
  secret access supplied when a remote agent session starts.
- **Prepared context:** the target client can discover and use its selected
  capabilities. A copied file or saved token alone does not establish this.

Automatic binding applies within previously chosen authority. A newly detected
laptop login is not automatically selected for a project. Existing valid choices
should not be reconfirmed on every session. Context selection does not claim an
OS security sandbox between processes running as the same remote Unix user.

## Current code and gaps

Base: `origin/main` at `c08116394127b44ef87d2777ce6b7d9ebbc5536f`.
Fresh worktree: `feat/guided-onboarding`.

- `internal/cli/setup.go` and `internal/cli/cli.go`: missing-manifest first run
  shows save/agent/cancel and exits through configuration-only init. It cannot
  complete the requested continuous flow.
- `internal/cli/project.go` and `internal/legacy/legacy.go`: manifest creation
  still requires an existing private provider profile to open. New private
  provider and account binding setup is missing.
- `internal/controller/runtime/agent_auth.py`: existing explicitly bound client
  caches, ownership checks, native login/status, pending-login markers, and
  capture locks are useful building blocks. They are not complete first-time
  binding creation or verified session launch.
- `internal/controller/runtime/project_shell.py`: explicit login requires an
  existing agent profile and running prepared machine. Repository preparation
  also invokes app dependency setup; that must not gate this slice's session
  readiness.
- `internal/mcps/runtime.py` and `docs/mcps.md`: current MCP projection uses
  standard remote native homes. Environment references depend on variables
  already being present in the remote agent. Automatic secret delivery to the
  target client/MCP and native authentication completion are not solved by sync.
- `internal/config/agent-guide.md`: skill declarations and arbitrary Infisical
  injection for custom MCPs are explicitly unimplemented.
- `internal/controller/runtime/infisical_context.py`: scoped project/identity
  behavior exists. `profiles.py` couples Infisical to app profiles and forbids it
  for shell-only profiles. Coding sessions must be able to use Infisical without
  an app service declaration.
- `internal/controller/runtime/bootstrap.sh`: current remote baseline assumes
  Linux x86_64 and coding tooling. It must support the selected tools/integrations
  without implying a language restriction on the repository.
- `internal/legacy/open.py`: native transport handoff preserves the chosen
  terminal and existing conversations. Preparation must finish before the target
  agent reads its config and captures its process environment.
- `.planning/0004-setup-ux/agent-login-uat.md`: existing native sign-in evidence is
  local/mock; actual browser/account verification remains outstanding.

## Native documentation checked

- [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp): stdio environment forwarding
  and HTTP bearer-environment references are native mechanisms; AllSet must supply
  the intended remote process context.
- [Codex skills](https://learn.chatgpt.com/docs/build-skills): native repository/user
  discovery exists and skill availability can be checked through the client.
- [Claude settings](https://code.claude.com/docs/en/settings): native config scope
  matters; validate supported homes instead of inventing a universal config path.
- [Claude skills](https://code.claude.com/docs/en/skills) and
  [Cursor skills](https://cursor.com/docs/skills): native discovery locations differ
  by client; selected supporting files must reach the correct scope.
- [Cursor configuration](https://cursor.com/docs/cli/reference/configuration):
  config overrides exist but do not prove all credential/MCP files are rerouted.
- [Cursor CLI](https://cursor.com/docs/cli/reference/parameters): native login,
  identity/status, and MCP login/list/tools operations are available in current
  docs. Check the installed supported version during implementation.
- [Infisical run](https://infisical.com/docs/cli/commands/run): native process
  injection supports selected environment and paths. Recursive access broadens
  scope and must be explicit.

These facts support adapter design. They do not prove a single cross-client
implementation, session isolation, or a working AllSet integration.

## Native Box evidence

Read-only installed CLI help was inspected with `box --no-update` for `login`,
`env new`, `env set`, and `new` on 2026-09-11. `env new` defaults to injecting
stored credentials; `env set` exposes individual injection toggles and a master
no-injection mode. `new --no-env` is a creation backstop. A new AllSet-owned
environment must establish the selected credential boundary explicitly before
provisioning. Never change an unrelated provider environment to achieve this.

Native create accepts an explicit environment, optional snapshot, size, lifetime,
and personal/organization scope. Existing runtime small/two-hour defaults are
implementation starting points, subject to the actual native account allowance
and user acceptance before creation. No private snapshot is required for the
new path. The public Box CLI documentation URL could not be opened through the
browser tool; no provider API or authenticated operation was used as evidence.

## Scope and constraints

In scope: first-time Box/provider binding, chosen Claude/Codex/Cursor accounts,
repository access, configured MCPs, selected skills, Infisical/scoped secret
access, automatic context application, interrupted setup recovery, and fast reuse.

No language/framework wizard, app dependency boot, dev server, preview, app UAT,
database migration, public sharing, provider marketplace, or additional VM
integration is required to pass this slice. Preserve existing optional app and
preview features without expanding or deleting them.

Keep machine ownership, allowance/lifetime, config conflict, private credential,
and active-work safeguards. Read-only commands and explicit init remain free of
environment/auth mutation. New features must not copy entire laptop homes or
authenticated templates. Actual account or compute operations require their
appropriate authorization; planning alone does not grant it.

Provider research and possible selection UI follow this slice; see follow-ups.

## Implementation verification

The PRD assigns these boundaries; verify native behavior during implementation:
native client launch/config scopes, private binding creation, skill source/native
projection, scoped secret delivery, durable retry, and minimum readiness probes.
Reuse existing supported provider/lifetime controls and surface their actual
terms before first creation. There is no requirement to invent a new billing plan.

If a capability cannot be supported by a native client, expose that specific
limitation. Do not silently claim all configured integrations are ready.

See [decisions](decisions.md), [acceptance](uat.md), [threat model](threat-model.md),
and [follow-ups](follow-ups.md). UAT was approved by the user. See the
[PRD](prd.md), [bootstrap](bootstrap.md), and [consistency review](plan-review.md)
for the implementation handoff.
