# Remote coding session onboarding decisions

Status: corrected acceptance approved by the user, 2026-09-11.
The user replied "approve" after the session-first UAT was presented.

## Current decisions

### D-01 — One continuous first-time flow

Bare `allset` carries a first-time developer into the intended remote project
environment. Saving a file or copying a prompt into a different application
cannot be the main outcome. Explicit `allset init` remains configuration-only.

### D-02 — No pre-existing AllSet profile required

The user explicitly confirmed first-time onboarding from no private AllSet
profile. The CLI must create the necessary private bindings through supported
flows; the developer's existing private controller state is not a prerequisite.

### D-03 — Box first; provider research follows

Box is the initial compute provider. Record later research into VM providers and
a possible provider-selection step separately. Do not expose unsupported
providers or let terminal choice select compute/account identity.

### D-04 — Short planning pass, then focused implementation

Use the repository-local slice/grill workflow. Planning work has not opened a
VM, changed accounts, or saved hey.lol's manifest. The user-facing acceptance
walkthrough precedes requirements and implementation handoff.

### D-07 — Ready means the remote coding session can work

The user's explicit clarification supersedes the app-focused planning. AllSet's
job is to prepare chosen coding clients and automatically bind their accounts,
MCPs, skills, Infisical, and other configured secret access to the intended
remote session. Application language, dependency installation, app startup, and
preview availability do not determine onboarding completion.

Prepare the owned environment, repository access, selected tools, and integration
context. The developer can start the chosen client normally in that environment
and use it immediately without extra auth/config/sync/injection commands.

### D-08 — Connect once; apply to the intended session automatically

First-time setup shows existing authorized project bindings, asks only for
missing choices, and guides necessary native sign-in. Reuse selected valid
bindings on subsequent entries and launches. Automatically apply the correct
context before client startup, including required MCP process environment.

Do not silently select ambient laptop accounts, copy unrelated credentials, or
switch identities beneath a running conversation. Client, MCP, Infisical,
GitHub, and compute identities remain independent. Future launches receive
deliberate changes; existing sessions are not restarted to apply them.

### D-09 — Integrations are selected capabilities, not mandatory accounts

Configure the MCPs, skills, and secret access the developer/project selects.
A project with no Infisical or no MCPs must still reach a working coding session.
Once selected, a capability is not reported ready based only on a declaration
or file copy; verify the usable native-client result.

Infisical and existing explicit secret references are part of this slice's
delivery path. This does not promise adapters for every secret service, MCP
vendor login, or skill marketplace. Unsupported cases must identify the exact
missing capability without misrepresenting successful setup.

### D-10 — Fast reuse and truthful recovery

Returning entry should reuse the owned environment, tools, credentials,
configuration, and integration caches. Do not repeat bootstrap or browser login
when no relevant change or failed verification requires it.

First-time provider startup and native sign-in may take time; show progress and
measure stages. No numerical SLA or process survival across VM stop is promised.
A failed/abandoned connection stays pending; retry continues at the affected
stage. It must not create a duplicate machine or overwrite unrelated accounts.

## Superseded planning

### D-05 — App and preview required: superseded by D-07

The assistant interpreted a short "correct" response as requiring a running app
and verified preview. The user's explicit session/account-focused clarification
overrides that interpretation. Neither app startup nor preview verification is
an acceptance gate for this slice.

### D-06 — Generic application requirements: narrowed by D-07

The user rejected a programming-language support list. That correction remains.
The later tools/setup/services contract was still too app-focused. Only coding
tool and integration prerequisites belong in the onboarding critical path.

## Implementation questions

Resolve from source and current native documentation: supported client config
and launch scopes, binding creation, MCP readiness/auth, skill placement,
Infisical credential/environment delivery, and safe retry. The PRD records the proposed adapters and
known limitations; verify actual native behavior during implementation. Do not turn implementation questions
into requests for the user to select languages or describe app services.
