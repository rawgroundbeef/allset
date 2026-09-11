# Remote coding session onboarding acceptance

Status: **user-approved on 2026-09-11; local/mock implementation evidence
executed; real acceptance pending authorization**. The user replied "approve"
after this corrected walkthrough was presented. This replaces the unapproved
app/preview-focused draft.

## Outcome

A developer runs `allset`, connects the accounts and integrations they want,
and enters their remote project environment. Their chosen coding client works
on its first turn with the correct identity, MCPs, skills, and secret access.
Returning to the project does not repeat setup.

## Prerequisites

- Record the implementation/package revision when executing. Use a supported
  local host and Box environment; no developer-private AllSet profile, controller
  installation, authenticated template, or account cache may be assumed.
- Local/mock checks use temporary homes, synthetic identities/credentials, a
  disposable repository, and fake provider/native-client boundaries.
- Real remote and browser checks require scoped authorization for Box and the
  chosen accounts. Use disposable resources and existing allowed compute limits.
  A planning approval is not a provider mutation or sign-in authorization.
- Use a repository that intentionally has no app start command and no successful
  application dependency installation. This must not block the coding session.
- Full-context fixture: selected client accounts, a harmless MCP read operation,
  a fixture skill, and a scoped test secret consumed by a harmless command/MCP.
  Also test the minimal client-only path without MCPs, skills, or Infisical.

## First-time flow

The steps describe the visible milestones. Native sign-in that needs a remote
client runs after its tools are prepared, within this same walkthrough and
before handoff; it is not a prerequisite for allocating the first environment.

1. **Run one command.** In the local repository, run `allset` with no manifest,
   registration, private project profile, or saved machine. See the project
   identity and guided path into a remote coding environment. No language,
   framework, dev-server, or preview questions appear.
2. **Choose coding tools and connect accounts.** Select Claude Code, Codex,
   Cursor, or the subset to make available. Existing authorized project choices
   are visible and reusable. Missing connections use native sign-in within the
   walkthrough; the user does not paste tokens or move a setup prompt elsewhere.
   Provider, repository, coding-client, and integration identities are distinct.
3. **Choose integrations.** Review configured MCPs and skills; connect selected
   ones. If using Infisical, select its intended identity, project, environment,
   and secret scope. The user does not edit remote config files or memorize an
   injection command. Unselected services do not require accounts.
4. **Prepare automatically.** Present actual compute/lifetime terms before first
   allocation. AllSet creates private bindings, prepares one owned Box, waits
   for restored storage, makes the correct repository accessible, and installs
   necessary coding/integration tools. No app dependency install, service
   startup, database access, or preview probe is needed for completion.
5. **Enter the remote environment.** Continue through the chosen terminal or
   workspace interface. Start a configured client normally. Before its first
   turn, the chosen account, native MCP settings/auth, selected skills, and
   required secret delivery are already in place. No separate AllSet config,
   MCP sync, credential copy, or secret-wrapper command is required.
6. **Prove the session works.** In an authorized real check, obtain a minimal
   native model response using the OAuth-verified account. Discover and call the
   configured harmless MCP tool from this target session. Invoke the fixture
   skill and observe its non-secret marker. Let a harmless command or MCP use
   the test secret, reporting only success/failure, never its value.
7. **Inspect saved results.** Shared declarations contain only supported
   requirements, never credentials or personal account selections. Private
   bindings and session context target the correct developer/project/client.
   Show separate successful results for the client and selected integrations.
   A saved cache or config file alone cannot produce their ready checkmarks.

## Return and recovery

- **Warm return:** run `allset` again. Reuse the same owned environment and
  authorized bindings with no setup questions, redundant installation, or
  unnecessary browser login. A newly started configured client receives context
  automatically. Record elapsed time and the actual repeated operations.
- **Another session/project:** opening another session or project must not change
  the identity/configuration under an already running conversation. Different
  project contexts cannot receive each other's credentials. This verifies
  correct binding, not an OS sandbox between same-user processes.
- **One expired connection:** expire/reject one synthetic client or integration.
  Repair only it through the guided flow. Preserve unrelated accounts and work.
  Do not mark the affected capability ready or accept its rejected credential
  through background capture. Native refresh may run when supported.
- **Interrupted setup:** stop after a provider mutation has succeeded but before
  the local result is recorded. Repeat `allset`; reconcile the same machine and
  continue the incomplete stage. Do not allocate a duplicate or claim that
  cancellation stopped billing. Preserve deliberate completed choices.
- **Unavailable integration:** report the specific capability and offer retry
  or an explicit choice to continue without it. Continuing without it does not
  label it connected; remaining tools work. Do not silently drop selected tools.
- **Config/skill conflicts:** preserve unrelated native settings and user-edited
  skills. A conflict has an actionable retry path and no false success result.
  Skill/MCP source content cannot authorize new accounts or privileged actions.
- **Native permissions:** keep client-native trust/approval controls. Setup
  automation must not silently disable sandboxes or approve unrelated tools.
- **Cold resume:** after a separately authorized VM stop, restore the intended
  environment, credentials, and selected integration context before the next
  client launch. Measure cloud restoration separately from warm entry.
- **Read-only/config-only:** inspection, validation, status, diagnosis, dry-run,
  and explicit `allset init` never create/resume compute or initiate native login.

## Demo pass criterion

**From no AllSet profile, one `allset` walkthrough gets the developer into the
correct remote project environment, where their chosen coding client can answer
and use its configured MCP, skill, and secret access on its first turn; the next
entry reuses that setup automatically.**

## Evidence status

### First source fetch follow-up — 2026-09-11

The user's live retry reached repository preparation, then failed because the
checkout adapter rejected a full GitHub URL accepted by shared configuration.
The prior packaged flow started with a prepared checkout, so it did not cover
this initial source-fetch branch. The fix accepts validated GitHub URL forms,
shorthand, and local origins without mutating shared settings or live state.

**Local/mock:** first-fetch tests now start without a source cache or known base
SHA and run real Git through default-branch discovery, fetch, and bundle creation.
The Linux arm64 archive in `/private/tmp/allset-guided-release-20260911-21` passes
the same source-fetch boundary with only its network endpoint substituted.
This is first-source-fetch evidence, not a claim of complete cold VM preparation.
**Real public network:** the exact `https://github.com/octocat/hello-world` source
fetched and bundled in a temporary local cache at commit
`7fd1a60b01f91b314f59955a4e4d4e80d8edf11d`. No Box/account operation was used.
**Next real check:** rerun the existing implementation command below, preserving
the saved project and machine. Full live remote preparation and OAuth remain
unverified.

### Sequential sign-in follow-up — 2026-09-11

The user requested a visible, continuous Codex → Claude Code → Cursor sequence
for the chosen subset, with loading feedback, native browser links, verified
success, and a way to skip. The implemented flow prepares Box first, then numbers
the selected sign-ins. Ctrl+C during sign-in offers retry/skip/quit. Enter retries;
quit preserves completed logins, and skip remains explicitly unconnected with an
individual repair command. Final SSH handoff follows those decisions.

**Local/mock + interactive terminal:** one/two/three-client tests cover ordered
identity verification and credential save, retry without repeating completed
clients, foreign-cache refusal, skipped-cache exclusion, quit/EOF, and repair.
Real PTY tests exercise animation release before native links and preserve stdin.
The Linux arm64 offline archive in
`/private/tmp/allset-guided-release-20260911-19` exercises the packaged onboarding
entrypoint, three synthetic native sign-ins, verification before SSH handoff,
interrupt/skip, and warm return. Provider, repository-access, SSH, and account
boundaries are synthetic; real browser/model success remains unverified.

**Next real check:** from the existing `allset-onboarding-test-20260911` checkout,
run `/private/tmp/allset-guided-onboarding-impl-20260911/bin/allset --attach ssh`.
Observe Box preparation followed by each selected numbered account step. Complete
the native browser links using the intended accounts; confirm each public account
receipt precedes the next client and SSH comes last. Optionally interrupt one
step and choose skip, then verify only it is reported unconnected on return.
Do not reset project state or create a replacement fixture/VM just to retry.

### Slice evidence

| Category | Status |
| --- | --- |
| Source and native documentation inspection | Performed; gaps recorded in discovery |
| Local/mock implementation tests | Passed on macOS arm64, 2026-09-11: strict shared/private contracts, continuous and resumed CLI paths, no app/fallback execution, Box identity and timeout guards, managed skill conflicts, scoped secret filtering, and native argv/cwd preservation |
| Packaged offline implementation test | Passed with the Linux amd64 release archive in a network-disabled container, 2026-09-11; Box, SSH, Herdr, native login, and MCP boundaries were simulated |
| Real provider status and pre-creation prompt | Passed 2026-09-11 against Box 0.1.228: `account.identifier`/`loginState: active` parsed, live allowance checked, account/billing/machine terms shown; declined creation and confirmed no profile/journal/machine record |
| Real remote creation and native OAuth checks | Unverified |
| Interactive model/MCP/skill/secret proof | Unverified |
| Cold and warm latency measurements | Unverified |
| Human alignment on this walkthrough | Approved by the user, 2026-09-11 |

Implementation commit `5d332d6` is based on planning commit `79f0f87`; its gate
results are recorded in `PROGRESS.md`. No VM, provider account,
browser session, or real credential was mutated during these checks. The demo
pass criterion remains unproven until the authorized real first-turn and warm-
return checks execute. Do not present mocks as real auth.
