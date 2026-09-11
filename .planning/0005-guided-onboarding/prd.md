# Remote coding session onboarding

Status: requirements from user-approved UAT, 2026-09-11. Implementation pending.
Approval: the user replied "approve" after the corrected remote-session
[acceptance walkthrough](uat.md) was presented. This approval covers the product
contract and planning continuation, not live account/provider operations.

## Problem and outcome

First-time `allset` currently ends at configuration review or an external agent
prompt. Opening still depends on pre-existing private profiles. A saved login or
native MCP registration does not automatically supply the credentials, skills,
or process environment that a remote coding session needs.

After this slice, a developer configures chosen coding clients and integrations
once, enters the remote project environment, and starts a configured client
normally. Its first turn can use the intended model account, MCPs, skills, and
secret access. Returning entry reuses that setup without another configuration
walkthrough.

The repository's programming language and application health are irrelevant to
this outcome. [Decisions D-07–D-10](decisions.md) supersede the earlier app plan.

## Scope

Box-backed first-time and existing-project onboarding; Claude Code, Codex, and
Cursor Agent; project/repository access; existing stdio/HTTPS/Trigger MCP
declarations and their native auth; repository and explicitly selected personal
skills; Infisical and explicitly selected secret references; automatic remote
client launch context; safe retry and fast reuse.

Application dependency installation, framework detection, dev servers, app
previews, migrations, new compute providers, general skill marketplaces, and
arbitrary secret-service adapters are excluded. Preserve existing optional app
features and connection interfaces. Do not build a new chat UI, model gateway,
or agent-session manager.

## Behavior and acceptance mapping

| ID | Requirement | Acceptance |
| --- | --- | --- |
| R-01 | Bare interactive `allset` resolves the Git project, reviews only missing choices, saves agreed settings, and continues into the environment in one invocation. Existing configured projects skip first-time review. | [First-time 1–4](uat.md#first-time-flow), warm return |
| R-02 | Missing private bindings are created through supported native flows. Choose Box identity/billing scope explicitly on first association, verify repository access, and record ownership before compute use. No developer-specific environment or snapshot is assumed. | First-time 2, 4, 7; interrupted setup |
| R-03 | User selection of clients is private per developer/project. Native sign-in guides only missing/invalid selected accounts; already authorized valid choices are reused. A wrong identity cannot become a usable cache. | First-time 2, 6–7; expired connection |
| R-04 | Starting a configured client normally inside the prepared remote project applies its context before execution. Keep cwd, argv, stdin/TTY, signals, exit status, and native session/resume semantics. No extra sync/config/secret-wrapper command is required. | First-time 5–6; another session; warm return |
| R-05 | Apply selected MCPs to the actual native client context. Honor target clients, OAuth/native preset auth, stdio variables, and HTTPS bearer refs. Required variables must reach the process that uses them. | First-time 3, 5–6; unavailable integration |
| R-06 | Make selected repository and personal skills discoverable by target clients, including supporting files. Preserve source identity and existing edits; do not flatten distinct same-named sources or overwrite unmanaged content. | First-time 3, 5–6; config/skill conflicts |
| R-07 | Infisical connects independently of app services. Bind the selected instance, identity, project, environment, paths/keys and recipients privately; fetch/inject only that scope through a native supported flow. A client-only setup needs no Infisical account. | First-time 3–6; secret fixture; minimal path |
| R-08 | Report configured, authenticated, ready, pending, and explicitly skipped states accurately. Offer repair of one failed capability or deliberate continuation without it. Do not silently drop integrations or produce a success checkmark from file presence. | First-time 6–7; unavailable/expired integration |
| R-09 | Re-entry preserves machine identity, worktrees/branches, existing conversations, native user settings, and services. Context changes apply to future launches without changing identities beneath running conversations. | Warm return, another session/project, conflicts |
| R-10 | Persist incomplete work and reconcile provider mutations with unknown outcomes. Retry continues the same project operation and cannot create a replacement machine from a corrupt/foreign pointer. | Interrupted setup, cold resume |
| R-11 | Configuration-only init, inspection, status, diagnosis, validation and dry-run remain free of provider/auth mutation. Noninteractive first-time execution without complete prior choices reports the missing interactive step and performs no onboarding. | Read-only/config-only |
| R-12 | Warm entry and launch reuse unchanged tools/config/context. Record timings and operation counts; avoid redundant downloads, bootstrap, auth prompts, or model requests as readiness probes. | Warm return; latency evidence |
| R-13 | Shared declarations contain requirements/references; private bindings contain account choices; credential stores contain values. No credential values appear in args, printable plans, generated shared files, errors, or templates. | First-time 7; different-project, secret, malformed-input tests |

## Interaction contract

The CLI offers one primary path into the remote project environment. The initial
display contains the resolved project and, when known, saved provider context.
Missing setup asks for coding-client selections and required account connections.
Configured integrations are summarized with a way to customize or add selections.
Do not ask for a terminal, language, framework, dev server, or preview.

Prepare a reviewable selection before first private account association or
compute creation. Browser sign-in and unavoidable native trust dialogs remain
interactive; AllSet handles orchestration and remembers completed choices.
Never present a prompt telling users to move setup into another application.
The agent guide remains a supported way for an agent to inspect and operate the
same underlying workflow. Update `internal/config/agent-guide.md` and its
`allset config guide` output to cover chosen client logins, MCP auth, skill
sources, Infisical/secret scope, private account bindings, and incomplete setup.
It must identify supported commands and fields, distinguish config-only review
from an authorized setup/open operation, and explain any remaining native human
sign-in step. Remove language/app inspection from the default setup checklist.
Verify the guide against the same minimal/full-context and read-only scenarios;
do not document unimplemented adapters as usable.

Enter through the selected invocation/caller transport after context preparation.
For ordinary SSH, the user can type the configured native client command. For a
Herdr workspace handoff, the selected remote workspace must already have the same
client launch behavior. Do not automatically create an agent conversation, select
a random prior conversation, steal focus, or inject text into an existing pane.

If a selected optional integration fails, preserve it as pending and provide a
retry or explicit continue-without action. The resulting summary names the
skipped integration rather than claiming complete integration readiness.
If the selected coding client itself cannot authenticate, repair it or choose a
different configured client; a shell connection alone is not client readiness.

## Owned configuration and data

Use explicit types and versioned private records; the following are proposed
implementation contracts, not fields supported by the current binary.

| Owner | Data and rules |
| --- | --- |
| Shared project declaration | Existing identity/provider/aliases/MCP contract, plus implemented optional repository skill references and session environment variable requirements. No personal account, local home path, token, secret value, terminal field, or app lifecycle requirement. |
| Private project bindings | Selected clients, their account identities and native credential references, provider/billing/environment association, repository identity, selected personal skill references, and named secret sources/scopes/recipient mappings. |
| Credential storage | Native login stores and project-owned refresh caches, permission-restricted from first write. Reference them from bindings; never serialize values into setup plans. |
| Preparation journal | Project/provider owner, chosen config revision, completed/pending stages, exact resource identifiers and mutation outcome. A saved choice is distinct from verified auth or applied context. |
| Remote launch context | Bound project/worktree/client, native config locations, managed MCP/skill revision, authorized secret delivery, and credential-cache ownership. Record context identity separately from the native conversation ID. |

Implementation may choose precise additive JSON field names without another
product interview. Keep schema/parser/help/docs synchronized and reject unknown
or contradictory fields. Keep manifest v1 and registry v3 compatible with current
documents; omitted new declarations must not erase user-managed native content.
Explicit removal removes only AllSet-owned entries, not unrelated credentials
or files. Validate changed requirements and atomically apply them with conflict
detection. Do not rewrite existing private profiles wholesale from partial
inspection output.

Keep existing private state references readable in place. New typed onboarding
records may adapt the compatibility controller, but do not require moving all
existing accounts/VM state into a new layout before this feature works.

## Provider and repository preparation

Use the native Box CLI and current project ownership/allowance controls. Planning
inspected only `--help`; real provider behavior remains to be proved.

- Native `box login` supports browser methods and stdin key input. Use sign-in
  for missing auth; do not blindly invoke a broad onboarding command that can
  expand into unreviewed plan/account setup.
- Native `box env new` creates a named environment whose credential injection
  defaults are enabled. A fresh AllSet environment must be configured and
  verified to withhold account-wide GitHub, Box, agent, and secret injection
  before creating/resuming compute. Native `env set` exposes these toggles and
  a master no-injection switch; `new --no-env` is a creation backstop.
- Never mutate a user's unrelated/default named environment or silently adopt
  an existing same-named environment. Own and journal the environment association.
  Preserve explicitly configured legacy provider injection choices after
  verifying their intended binding; do not upgrade running environments blindly.
- New projects use the provider's supported clean base with no private named
  snapshot. Existing explicit owned template choices remain compatible. Verify
  coding-tool availability and install missing selected tools through supported
  native/bootstrap adapters.
- Preserve the current bounded usage behavior: proposed creation uses the
  existing small-machine/two-hour defaults, shown with native account allowance
  and lifetime information before acceptance. Do not disable auto-stop, purchase,
  upgrade, increase concurrency, or switch billing scope to make setup succeed.
  Read actual provider rate/limits; do not hardcode a currency-price claim.
- Scope Box command execution to the selected account/billing association;
  ambient provider variables cannot retarget later mutations. A missing or
  foreign association is not a reason to provision a replacement.
- Reuse native GitHub access paths already implemented after the user selects
  one. A private repo with no usable selected credential guides native GitHub
  sign-in. Public repository reads need not force an unrelated account login.
  Non-GitHub Git remotes keep supported explicit SSH/HTTPS behavior; do not
  pretend the GitHub account adapter supports another host.
- Prepare the repository/worktree without executing its application install,
  lifecycle, or test scripts. Split coding-environment preparation from existing
  app/task setup explicitly; empty fake app commands are not a readiness check.

## Client launch and native integrations

Add a small remote launch adapter with an explicit owner/context protocol.
Install entry points for the configured client commands in the prepared project
shell/workspace path; resolve the underlying native binary explicitly to avoid
wrapper recursion. Pass arbitrary user client args through as argv, preserving
native interactive and resume behavior.

The adapter resolves the owned project/worktree, selected client and binding,
prepares/verifies required native context, supplies secrets privately, then execs
the native client. It must not globally export all tokens in shell startup files,
change arbitrary local laptop environments, or redirect sessions from unrelated
directories. A session launch record/context owns the chosen inputs, not a
globally mutable "current account".

Validate actual native configuration/auth/skill paths for supported installed
client versions. Codex, Claude and Cursor have different scope mechanisms; a
configuration-home override alone is not proof that every native auth/MCP/skill
file moved. Keep account contexts isolated when changing an identity, and refuse
unsafe in-place switching if a native client cannot preserve an active context.
Do not silently migrate native conversation history or start an empty substitute
for a user's requested resume. Same-Unix-user process isolation is not claimed.

Use the existing MCP projection/journal machinery, adapting its explicit target
context beyond standard home assumptions. Native MCP auth and workspace trust
remain native; custom HTTPS OAuth should be guided through the target client's
supported login flow. Trigger keeps its current pinned native preset behavior.
A generic environment-variable name is insufficient until the target remote
process receives it from its selected source.

For skills, support repository-contained skill directories and explicitly
selected personal skill directories through native per-client projection.
Copy only selected directories/supporting files, preserve scoped semantics, and
record a source digest/revision. External source references must be deliberately
selected and pinned/resolved before applying; an entire marketplace/catalog is
not required. Reject source escapes, collisions, or unmanaged edited targets
instead of overwriting them. Shared config cannot carry an absolute personal
path. Do not auto-execute skill instructions during onboarding.

Infisical binding belongs to the session/integration path independently of
`services` or `shell_only`. Reuse the native identity validation and token
environment mechanisms, selecting explicit paths/keys and target client/MCP
recipients. Environment inputs and conflicting secret mappings must resolve
deterministically or fail clearly. Broker credentials do not become ordinary
child variables unless the selected capability explicitly needs broker access.
Fetch values at the relevant launch/apply boundary; keep them off command lines
and disk-backed shared configuration. Changes affect new processes; do not
restart active agents when a secret changes.

## Readiness and performance

Keep separate observations for declared, installed/configured, authenticated,
and available-to-client. Use safe native auth/status, resource checks, and MCP
connection/tool discovery where supported; use the real first-turn UAT for model
response, harmless tool call, skill invocation, and secret delivery proof.

Do not send a paid model prompt or call arbitrary MCP tools automatically on every
open to create a readiness checkmark. Do not treat cached token presence or file
projection as proof of service access. If safe verification cannot establish a
claim, name that state accurately and keep the selected capability pending.

Cache unchanged non-secret preparation by relevant source/tool/boot/context
revision. Authentication rejection, changed account selection, config conflict,
restored filesystem state, and native session startup remain meaningful
invalidation boundaries. Bound subprocess output/time and polling; serialize
auth/provider mutations with existing ownership locks. Do not parallelize native
sign-ins sharing stdin or race secret/cache writers.

Measure fresh onboarding (excluding separately reported human sign-in time),
warm open to terminal/workspace readiness, and client launch to usable prompt.
Record cold provider restoration separately. Warm acceptance forbids redundant
installs and login prompts; no arbitrary subsecond SLA is introduced.

## Module responsibilities and verified pointers

All paths below exist at the planning base. New modules are labeled proposed.

| Boundary | Current code | Required change |
| --- | --- | --- |
| CLI interaction/intent | [internal/cli/setup.go](../../internal/cli/setup.go), [internal/cli/project.go](../../internal/cli/project.go), [internal/cli/cli.go](../../internal/cli/cli.go) | Separate config-only init from continuous onboarding; render curated choices and resumable outcomes. No provider IDs or credential parsing in CLI. |
| Shared config | [internal/config/config.go](../../internal/config/config.go), [internal/config/project.go](../../internal/config/project.go), [internal/config/mcp.go](../../internal/config/mcp.go), [internal/config/allset.schema.json](../../internal/config/allset.schema.json), [internal/config/registry.schema.json](../../internal/config/registry.schema.json) | Add only implemented skill/environment references; strict validation and compatible omitted/empty semantics. |
| Workflow/provider boundary | [internal/strategy/strategy.go](../../internal/strategy/strategy.go), [internal/strategies/box/box.go](../../internal/strategies/box/box.go) | Add the smallest explicit onboarding/binding/prepare operations; distinguish missing from invalid bindings. Read-only methods remain read-only. |
| Native Box | [internal/providers/box/box.go](../../internal/providers/box/box.go), [internal/controller/runtime/box-herdr.py](../../internal/controller/runtime/box-herdr.py), [internal/controller/runtime/projects.py](../../internal/controller/runtime/projects.py) | Native account/environment preparation and scoped provider operations; preserve allowance, ownership, creation locks, restore and retry logic. |
| Existing binding adapter | [internal/legacy/legacy.go](../../internal/legacy/legacy.go), [internal/legacy/inspect.go](../../internal/legacy/inspect.go) | Map existing profiles without overwriting accounts or pretending partial inspection is an editable profile. |
| Repository/tool setup | [internal/controller/runtime/project_shell.py](../../internal/controller/runtime/project_shell.py), [internal/controller/runtime/worker.py](../../internal/controller/runtime/worker.py), [internal/controller/runtime/bootstrap.sh](../../internal/controller/runtime/bootstrap.sh) | Explicit coding-only preparation; selected client/integration tools; no app dependency gate. |
| Agent accounts | [internal/controller/runtime/agent_auth.py](../../internal/controller/runtime/agent_auth.py), [internal/controller/runtime/agent_credentials.py](../../internal/controller/runtime/agent_credentials.py) | First-time binding creation and context-aware login/cache; preserve needs-login and background-capture guards. |
| Repository/secrets | [internal/controller/runtime/github_auth.py](../../internal/controller/runtime/github_auth.py), [internal/controller/runtime/repository_access.py](../../internal/controller/runtime/repository_access.py), [internal/controller/runtime/infisical_context.py](../../internal/controller/runtime/infisical_context.py), [internal/controller/runtime/profiles.py](../../internal/controller/runtime/profiles.py) | Native independent identities; session-scoped secret delivery without mandatory app profile. |
| Native MCPs | [internal/mcps/mcps.go](../../internal/mcps/mcps.go), [internal/mcps/runtime.py](../../internal/mcps/runtime.py) | Explicit target context, native auth/readiness, supplied remote variables, and managed-file journal. |
| Remote launch/skills | Proposed `internal/session` and `internal/skills`, with minimal bundled runtime adapters if required | One shared launch contract and per-client native projection; no new model or session-manager framework. |
| Transport/display | [internal/legacy/open.py](../../internal/legacy/open.py), [internal/terminal/](../../internal/terminal/), [internal/controller/runtime/progress.py](../../internal/controller/runtime/progress.py) | Finish context preparation before handoff; preserve transport selection, TTY lifecycle, existing sessions, and truthful progress. |
| Packaged runtime | [internal/controller/bootstrap.py](../../internal/controller/bootstrap.py), runtime inventory and tests | Explicitly include any new runtime source in the embedded allowlist; test a package without repository/private controller files. |

## Delivery and verification

Implement as one cohesive feature branch with reviewable internal commits:
(1) typed configuration/private bindings and workflow states,
(2) native provider/account setup plus coding-only repository preparation,
(3) client launch context/MCP/skills/secrets,
(4) continuous UX, recovery and warm reuse, documentation and acceptance.
Do not ship the initial menu change alone while integrations still require
manual repair. Use a fresh implementation worktree from the recorded planning
commit and follow repository worktree rules.

Focused tests should cover the actual changed contracts: no-profile first run;
minimal/full integration paths; foreign identities; no ambient provider injection;
rejected/expired auth; secret recipient scoping and output redaction; native
config/skill conflicts; passthrough client args/cwd/exit/resume; timeout after
provider success; active-conversation preservation; warm operation counts; and
read-only commands. Package tests must run without host accounts.

Required implementation gates from repository root:

```sh
go test -race ./...
go vet ./...
go build -o bin/allset ./cmd/allset
```

Format changed Go with `gofmt`. Runtime tests require Python 3.11+. Use
`scripts/build-release.py` and `scripts/test-container.py` for the packaged
offline fixture. Then execute authorized real/interactive [UAT](uat.md),
reporting unverified parts as incomplete. No real provider or model calls were
made during planning. Complete the local review skill; delegation requires
explicit authorization.

Rollback should preserve valid manifests, private credentials, journals,
machine pointers, and native user settings. Do not downgrade by deleting setup
state or replacing the machine. New fields must fail clearly in older binaries;
record the supported version rather than claim backward readers understand them.

## Open issues and follow-ups

No unresolved product choice blocks implementation planning. Exact additive
field names, native-version adapters, and private record layouts are ordinary
implementation choices within the behavior above. If source/native capability
evidence disproves a requirement, update the owning artifact and report the
specific gap; do not quietly reduce the approved UAT.

Live provider account/billing response parsing, native browser callbacks,
configuration-home/auth coverage, refresh across stop, and native skill/MCP
availability require implementation-time verification. They are acceptance
risks, not claims of completed support. Provider comparisons remain in
[follow-ups](follow-ups.md).
