# AllSet progress

## Remote coding session onboarding implementation — 2026-09-11

- Added the requested inline visual polish: a bold project heading, cyan active
  steps/spinner, green completion/account checks, amber skip/recovery marks, and
  dimmed metadata. TTY preparation now replaces one live row and leaves one
  completion receipt, not repeated successful internal phases. Native sign-in
  bytes, stdin, authentication decisions, and verification/save order are
  unchanged. `NO_COLOR` disables styling; redirected output, `TERM=dumb`, `CI`,
  and `ALLSET_ACCESSIBLE` also avoid redraws. No fullscreen/alternate buffer,
  new dependency, credential operation, or live environment change was added.
  **Local/mock + interactive terminal:** race suite, vet, CLI build, and diff
  whitespace passed. Actual PTY checks cover colored marks, one completion row,
  metadata control-character sanitization, plain/accessibility fallbacks, and
  release before native input/handoff. A synthetic PTY preview was inspected.
  The Linux arm64 archive under `/private/tmp/allset-guided-release-20260911-22`
  passed the offline packaged harness, including Go/runtime styling fallbacks,
  sequential verified sign-ins, interrupt/skip, and warm reuse. The existing
  implementation binary was rebuilt; the installed `allset` was not replaced.
  **Review:** local/non-independent correctness, ownership, security, resources,
  maintainability, and coverage passes found no blocking issue in this cosmetic
  diff. **Next:** see the new styling on the next ordinary connection; no account
  reset or repeat onboarding is needed for visual verification.
- **Real remote + interactive, user-reported:** the user's successful transcript
  after `0cfc77b` shows Box/project preparation, Codex → Claude Code → Cursor native
  browser sign-ins with verified account receipts, then SSH into the project
  checkout. This supersedes the earlier live preparation/OAuth evidence gaps
  below. It does not prove the remaining first-turn model/MCP/skill/secret or warm
  return criteria. No account identifiers or OAuth URLs were copied into evidence.
- Fixed the user's first-checkout failure for
  `https://github.com/octocat/hello-world`: shared configuration accepted the full
  URL, but source preparation only accepted shorthand or a local path. It now
  reuses the runtime GitHub validator for URL/shorthand/local origins. Clean and
  named-account fetches use HTTPS; legacy explicit SSH transport is preserved.
  Explicit URLs cannot be mistaken for local paths, and unsafe URLs fail before
  account lookup or network calls. No live profile, journal, checkout, machine,
  credential, or installed `allset` was modified; the implementation binary was
  rebuilt at its existing path.
  **Local/mock:** regression failed before the fix and passes afterward; native
  Git exercises default-branch discovery, shallow fetch, bundle contents, URL
  variants, and unchanged local origin/index/uncommitted work. Race suite, vet,
  build, and diff whitespace passed. The Linux arm64 archive in
  `/private/tmp/allset-guided-release-20260911-21` passed the offline packaged
  first-source-fetch check and existing sequential-login/interrupt/reuse checks.
  Previous packaged onboarding coverage began with an existing checkout and
  missed this failure; source-fetch coverage now starts with no cache/base SHA.
  **Real public network:** the exact `octocat/hello-world` URL fetched and bundled
  commit `7fd1a60b01f91b314f59955a4e4d4e80d8edf11d` in a disposable local directory,
  without Box or account operations. **Review:** local/non-independent; no
  blocking finding in this fix. **Unverified:** complete live remote preparation
  and native OAuth. Next: rerun the same implementation command from the existing
  test project; no state reset is needed for this parser fix.
- Added the requested sequential sign-in UX: selected clients run in Codex,
  Claude Code, Cursor order, with numbered steps, loading indicators, native
  browser links, and per-account receipts only after identity verification and
  credential save. Native output owns the display once it begins. Failed or
  interrupted sign-in offers retry/skip/quit; Enter retries. Completed accounts
  survive interruption, explicit skips remain unconnected, and SSH comes last.
  Guided sign-ins now hold the project operation lock so attached monitors
  cannot accept partial credentials. Project-bound skip markers suppress restore,
  capture, repeated prompts, and the skipped client's MCP login; explicit verified
  repair clears them. No live credentials, VM state, or installed binary changed.
- Expanded packaged coverage exposed and fixed two handoff/repair defects:
  embedded bridge assets now resolve from the verified controller directory,
  not an undefined `__file__`; installed wrappers run native auth/status without
  requiring conversation cwd, importing absent Infisical companions, or fetching
  project secrets. Ordinary conversation cwd/secret checks remain intact.
- **Local/mock + interactive terminal:** race suite, vet, CLI build, and diff
  whitespace passed. Tests cover 1/2/3-client order, verified save before advance,
  retry, skip/resume/repair, foreign cache, quit/EOF, child cleanup, terminal stdin,
  and loading-display release. The Linux arm64 archive under
  `/private/tmp/allset-guided-release-20260911-19` passed the offline container
  through three synthetic native accounts and SSH handoff, interrupted sign-in,
  skip and warm return. Repository access, Box, SSH, and auth are simulated.
  **Review:** local, non-independent correctness/ownership, security, resources,
  maintainability, and coverage review; no remaining blocking finding in this
  follow-up. **Unverified:** live browser authentication and the full first-turn
  model/MCP/skill/secret acceptance. Next: retry the rebuilt implementation binary
  in the existing `hello-world` fixture; keep the existing project/Box state.
- Creation confirmation now defaults to Yes (`[Y/n]`) after the account, billing,
  and machine terms are displayed. **Local/mock:** Enter proceeds through the
  existing creation/reconciliation test; `n`, invalid input, EOF, and Ctrl-C make
  no environment/profile/journal writes. Race tests, vet, and CLI build passed.
  The user's subsequent run created the `hello-world` Box. **Real provider
  read-only:** its saved machine ID matches a live idle Box, while onboarding is
  still `profile-saved` and all three agent identities/caches remain empty. This
  proves compute exists, not completed preparation or coding-client authentication.
- Fixed a live Box status mismatch: Box `0.1.228` returns the signed-in email in
  `account.identifier` with `loginState: active`. Onboarding now normalizes that
  field into the private email binding, rejects inactive/invalid/conflicting
  identities, and ignores unrelated config/billing contacts. Existing private
  `email`/`id` bindings keep their format; mismatch checks still precede mutation.
  **Real provider read-only + interactive:** rebuilt executable in the user's
  `hello-world` fixture read the live account and allowance, displayed personal
  billing and machine terms, and reached the creation confirmation. Answered `n`;
  no private profile, journal, or machine record was created. Native `env list`
  also confirmed the `safeForThirdParties` field shape without changing an environment.
  **Local/mock:** race tests, vet, and build passed; current native response shape,
  legacy fields, malformed/inactive identities, unrelated contacts, and changed
  accounts have regression coverage. Cloud creation and OAuth remain unverified.
- Implemented the approved slice from planning commit `79f0f87` in the fresh
  worktree `/private/tmp/allset-guided-onboarding-impl-20260911` on
  `feat/guided-onboarding-implementation` as implementation commit `5d332d6`.
  The occupied planning worktree and `feat/guided-onboarding` branch were
  preserved unchanged.
- Bare interactive `allset` now continues from shared configuration review into
  deliberate coding-client choice, native OAuth identity binding, private Box
  scope/account binding,
  bounded compute consent, coding-only checkout preparation, native sign-ins,
  MCP/skill projection, scoped Infisical session values, and the selected caller
  handoff. Explicit `allset init`, inspection, status, diagnosis, and dry-run do
  not enter this mutation path.
- Follow-up UX feedback removed the three-option setup preamble, internal ownership
  narration, and redundant project-name/provider questions from the normal path.
  New repositories accept inferred defaults silently and show one compact identity
  before the first private choice. Coding-agent choice is now a visible checkbox
  list with Codex selected and an explicit keyboard legend; the line-oriented
  accessible fallback explains its input grammar. Saved settings are not
  reconfirmed, and cancellation before validated private choices leaves no partial
  `.allset`; agent guidance remains an explicit `allset config guide` command.
  Later feedback removed the empty personal-skills question, detects public GitHub
  repositories without ambient credentials, uses and previews personal Box
  billing without asking for it, and states that selected-client sign-in follows
  Box preparation.
- Shared `.allset` contracts now support strict repository-relative skills,
  session environment references, and explicit native HTTP MCP OAuth. Private
  profiles retain provider/client/GitHub/Infisical choices. The onboarding journal
  pins the repository, random owned environment, Box billing scope and account
  identity, and reconciles an uncertain native environment-creation result before
  retry. Ambient Box credential injection is disabled and verified before compute.
- Coding-only setup runs the pinned tool bootstrap and repository access checks,
  never app dependency/setup fallbacks, services, previews, or database work.
  Managed skill copies include supporting files and refuse symlinks, oversize
  sources, collisions, and user edits. Future selected client processes receive
  only declared Infisical values; broker variables are removed, native argv/cwd
  and process semantics are preserved, and existing conversations are not restarted.
- **Local/mock:** `go test -race ./...`, `go vet ./...`, CLI build, Python syntax,
  schema parsing, and diff whitespace passed from the implementation root. Fault
  tests cover continuous and resumed entry, configuration-only init, coding-only
  setup exclusion, Box account mismatch and timed-out environment reconciliation,
  native executable preservation, skill conflicts/supporting files, and scoped
  launch environment/argv/cwd behavior. A disposable real TTY checkout rendered
  `hello-world`, `octocat/hello-world · Box`, then all 3 coding agents with Codex
  selected and `space select · ↑ up · ↓ down · enter submit`. A second real TTY
  check advanced directly to private setup without a project-name, single-provider,
  or coding-client account-email prompt, then cancelled without a provider call.
  After the optional-prompt fix, a fresh public-repository TTY selected all 3 and
  rendered `Next: prepare Box, then open browser sign-in for Codex, Claude Code,
  Cursor.` followed by `Box billing [personal]:`; cancellation again made no
  provider call.
- **Packaged local/mock:** four macOS/Linux amd64/arm64 archives built in
  `/private/tmp/allset-guided-release-20260911-17`. The Linux
  amd64 archive passed the network-disabled container proof: continuous setup and
  cancellation guards, bundled runtime, synthetic login restore, native MCP
  projection, terminal display, workspace reuse, work collection, and ownership
  failures. Box, SSH, Herdr, native accounts, and MCPs were simulated.
- **Interrupted local setup:** the reported `hello-world` interruption left only
  the shared `.allset`; no private profile, onboarding journal, machine record,
  environment, or terminal had been created. The development binary resumes that
  state as `hello-world · onboarding`. The installed binary is an older build with
  the same prerelease version string and still reports the pre-slice limitation.
- Installed read-only native versions inspected: Box `0.1.228-ascii-prod1`, Codex
  `0.154.0`, Claude Code `2.1.268`, Cursor Agent `2026.08.04-aaa8809`, and
  Infisical `0.43.121`. No VM, provider environment, browser login, credential,
  release, or installed AllSet binary was changed.
- **Self-review, not independent:** domain, provider/account, credential, managed-
  file, recovery, native process, performance, maintainability, and test boundaries
  were checked using the repository review guidance. Findings fixed before final
  gates included preserving native local client binaries, pinning Box identity
  across interrupted onboarding, pre-validating private bindings before mutation,
  and allowing a manifest created by configuration-only init to continue later.
- **Unverified:** Box environment safety mutations, cloud creation/
  restoration, browser/native account flows, model response, MCP call, skill
  invocation, secret consumption, active-conversation behavior, and cold/warm
  timing. The approved demo pass criterion is therefore not yet claimed.
- Next: with explicit Box/account authorization and disposable scope, execute the
  real first-turn, interruption, warm-return, and cold-resume checks in
  [.planning/0005-guided-onboarding/uat.md](.planning/0005-guided-onboarding/uat.md).

## Remote coding session onboarding planning — 2026-09-11

- User accepted a continuous bare-`allset` setup/open flow, including developers
  with no existing AllSet profile. Box is the initial provider; research into
  additional VM providers and a provider-choice step is a recorded follow-up.
- Planning is isolated on `feat/guided-onboarding` from `origin/main` at
  `c081163`. [Discovery](.planning/0005-guided-onboarding/discovery.md),
  [decisions](.planning/0005-guided-onboarding/decisions.md), and a preliminary
  [threat model](.planning/0005-guided-onboarding/threat-model.md) capture the
  current evidence and implementation risks.
- The user explicitly refocused completion on configured coding clients and
  automatic account/MCP/skill/Infisical/secret binding to remote sessions. App
  dependency installation, language detection, services, and previews are out
  of the completion criteria. The earlier app-focused interpretation is
  superseded. [Acceptance](.planning/0005-guided-onboarding/uat.md) was rewritten
  around a usable first agent turn and fast returning entry and was explicitly
  approved by the user on 2026-09-11.
- Completed the [PRD](.planning/0005-guided-onboarding/prd.md) and
  [implementation bootstrap](.planning/0005-guided-onboarding/bootstrap.md).
  [Local consistency review](.planning/0005-guided-onboarding/plan-review.md)
  found no remaining planning blocker after clarifying native sign-in order,
  provider injection defaults, and the AI guide's responsibilities. Review was
  not independent. Documentation links, module paths, and formatting were checked.
- Next: use the bootstrap in a fresh implementation context from the final
  planning commit; implement the complete session workflow and execute its gates.
- Current gaps include new private profile/account creation, native session
  context application, automatic MCP secret delivery, and skill support.
  Selected native docs and existing runtime boundaries were inspected. No
  implementation, VM operation, account change, or hey.lol manifest write has
  occurred. Real authentication, integration use, and latency remain unverified.

## Individual agent sign-in — 2026-09-11

- User request: repair one configured project's agent login with a short command.
  Added `allset config claude`, `allset config codex`, and `allset config cursor`.
  The current repo is inferred through existing origin/manifest/binding checks;
  an explicit project or alias can follow the client name. Existing `login
  PROJECT CLIENT` uses the same path. Inspection and dry-run stay read-only.
- Login now uses the owned running VM, checks its restored filesystem and chosen
  client, and enters native sign-in. It does not resume/provision compute, set
  up tools/repositories, restore other logins, or configure Infisical/GitHub/MCPs.
  Open a stopped or unprepared project first. Login no longer accepts `--ttl`.
- The project lock spans native auth; the preparation spinner ends before the
  client takes the terminal. First sign-in records the identity verified by native
  status; later sign-ins enforce it. Only an authenticated matching identity and
  usable selected-client credentials
  can replace that cache. Failed/cancelled sign-in retains previous credential
  material marked for retry. Attached monitors skip locked projects and pending
  logins, including after rejection; they cannot silently accept failed auth.
- Packaged testing caught the old wrapper interpreting the project `dashboard`
  as a native Box command. The Go plan now passes an explicit project target so
  the wrapper cannot re-resolve it or dispatch a provider command by accident.
- **Local/mock:** Go race tests, vet and build passed during implementation.
  Regression checks cover each shortcut, named/current project, missing/foreign
  bindings, dry-run/TTY enforcement, stopped/restoring VMs, missing clients,
  native account mismatch, cancellation/failure, credential response scope,
  previous-cache preservation and background capture during/after sign-in.
- **Packaged local/mock:** Linux arm64 executable passed project-local Claude
  native sign-in/status/capture with simulated native CLI and synthetic accounts.
  Other client caches, source credentials, MCP auth, manifest, registry and active
  work were unchanged. Only provider `info` calls occurred. Earlier setup,
  startup-display, workspace-reuse, collection and failure checks still passed.
- Review is local, not independent. The auth boundary and remaining real-provider
  verification are recorded in [sign-in acceptance](.planning/0004-setup-ux/agent-login-uat.md)
  and [threat model](.planning/0004-setup-ux/threat-model.md).
- **Unverified:** real browser/provider authentication, particularly Codex's
  localhost callback and Cursor's native flow. No live VM or credential was
  changed for this feature. Next: use the command in the normal local project
  terminal; incomplete private account/profile onboarding remains separate.

## Setup review and startup display — 2026-09-11

- Corrected the previous first-run UX: its tests proved silent config restoration
  followed by opening, which did not meet the requested guided setup. Interactive
  `allset` without `.allset` now reviews saved settings and returns without any
  create/resume/connect operation. The choices are terminal configuration,
  a copyable prompt for the user's coding agent, or cancel. `allset init` can
  replay the review with an existing file; deletion is unnecessary.
- Startup now reports actual preparation phases with a TTY spinner, elapsed time,
  completed rows, and a checkout/account summary. Restoration waits show fetched
  bytes when available, without estimating percentages. Account labels retain
  the distinction between a saved login and verified access. MCP protocol JSON
  is suppressed during opening; curated configuration errors remain visible.
- The display ends before native SSH/Herdr handoff and on failure/interruption.
  Redirected output and `TERM=dumb` remain plain; `NO_COLOR` disables color.
  The display does not own provider polling or change resume/restore decisions.
- **Local/mock:** Go race suite, vet and build passed. CLI tests cover replay,
  saved registrations, cancellation/EOF, agent handoff and configuration-only
  first runs. Real PTY tests cover animation during waits and cleanup on success,
  error and interruption; bridge tests assert no redraw worker reaches native
  handoff. Review was local, not independent; the stop-wait narration was
  corrected during review. No remaining blocking finding in this scope.
- **Packaged local/mock:** offline Linux arm64 container passed missing-config
  review/cancel/agent handoff with zero provider/cache/auth changes, followed by
  a separate open. The executable animated in a PTY and used plain redirected
  output. Existing workspace reuse, native MCP projection, synthetic account
  restore, collection and ownership failures still passed. Docker resources
  were cleaned up. See [UX acceptance](.planning/0004-setup-ux/uat.md).
- **Real remote:** only a read-only Memeputer status check during investigation;
  no VM was created/resumed/stopped to test this change. Live cloud hydration,
  real sign-ins and visual acceptance in the user's Herdr pane are unverified.
- Next: user feedback on setup and startup in the normal terminal. Complete
  private provider/account onboarding remains a separate gap; the agent option
  supplies a prompt and does not launch an agent automatically.

## Bare project setup — 2026-09-11 (superseded UX)

- User requirement: running `allset` without `.allset` starts setup automatically,
  with a guided walkthrough that can be used with the preferred coding agent.
- Fixed the saved-registration gap: interactive current-project open now creates
  the missing project file using existing settings, then opens the environment.
  Unfamiliar repositories still ask for name/provider; the prompts now explain
  shared versus private settings, defaults/cancellation, and the agent guide.
  Existing files are preserved. Named shortcuts, scripted use of saved
  registrations, dry-run and read-only commands do not create project files.
- Work isolated in `fix/bare-project-setup` from main `9dcfacf`; application
  worktrees and live environments are untouched. Reused existing initialization,
  origin verification, account binding and atomic no-overwrite behavior.
- **Local/mock:** full Go race suite, vet, build, diff whitespace, changed
  documentation links and secret scan passed. CLI regressions cover saved
  bindings, nested directories, read-only/named/scripted entry, malformed files,
  cancellation and the guided prompts. Review was local, not independent; no
  blocking findings in the entry-point change. Existing origin/binding checks
  and atomic creation prevent cross-project fallback or config overwrite.
- **Packaged local/mock:** the offline Linux arm64 Docker test passed a PTY-backed
  first run in an unfamiliar Git repo: the walkthrough saved configuration and
  accurately reported missing account/provider setup, with no provider call.
  A saved-project first run created `.allset`, preserved registry/MCP settings,
  and opened successfully; repeat-open left the file unchanged and skipped setup.
  Existing workspace reuse and collection checks also passed. Docker resources
  were cleaned up. No live VM or real sign-in was used for this change.
- Remaining: the walkthrough configures project identity/provider declarations;
  full private account/provider onboarding is still incomplete. The default is
  terminal guidance plus `allset config guide` for any agent; launching a chosen
  agent from setup remains a product question, not implemented behavior.

## Bundled controller — 2026-09-10

- Accepted: remove the private controller-code dependency and verify a packaged
  executable in a clean container. Fresh worktree `fix/bundled-controller` from
  main `90ce7c6`; existing project worktrees, services and credentials preserved.
- The Go binary embeds an explicit 16-file Python/shell/JavaScript source
  allowlist. It no longer loads code from the private `controller/` folder.
  Removed developer-specific environment/template/repository/setup fallbacks.
  Private profiles, credential references, VM records and native CLIs stay in
  place. A supported new-project profile setup flow remains incomplete.
- Lifecycle execution uses isolated Python and an atomically installed,
  revision-specific cache. Existing cache contents are verified before import;
  modified/unsafe files fail without overwrite. Inspect/doctor/status/dry-run
  do not extract code or mutate accounts. Inspection reports the runtime revision.
- **Local/mock:** `go test -race ./...`, `go vet ./...`, CLI build, source syntax,
  diff whitespace and document links passed. Bundled faults cover concurrent
  first-use, cache tampering/symlinks, import isolation, exit status, Linux argv
  size, foreign account selection, allowance bounds and resume reconciliation.
  Gitleaks found no leaks in the source tree.
- **Packaged local/mock:** four macOS/Linux archives built. The Linux arm64
  archive passed the offline Docker harness with no source checkout, host home,
  credentials or socket mounted. Actual bundled code prepared synthetic saved
  state, restored a fake login, preserved native MCP settings, reused one Herdr
  workspace, and collected tracked/untracked changes without changing the index.
  Missing/foreign bindings and stopped-machine connect failed without fallback.
  Only simulated Box info calls occurred; no provider mutation was allowed.
  The harness removed its container/image; shared Docker build caches remain.
  Linux CI now runs the same packaged test on amd64.
- **Real remote:** the built executable successfully handed off to an existing
  running project's native Herdr workspace. No VM was created/resumed/stopped,
  no agent was started, and no private controller code was changed.
- **Installed:** the verified binary replaced `~/.local/bin/allset` atomically;
  the previous binary is retained under `~/.local/share/allset/backups/`.
- **Self-review, not independent:** correctness/ownership, code provenance,
  credential exclusion, resource bounds, maintainability and evidence checked.
  No blocking findings in the packaging change. Existing upstream tooling and
  same-user host trust remain prerequisites; the runtime cache is not a sandbox.
- **Unverified:** the container simulates Box/SSH/Herdr, tool bootstrap and
  restoration. It does not prove real sign-ins, Infisical/MCP APIs, cloud
  provisioning, stop/resume or interactive agent detection.
- Next: implement a supported private project/account setup flow from declared
  project requirements. See [decisions](.planning/0003-bundled-controller/decisions.md),
  [UAT](.planning/0003-bundled-controller/uat.md), and
  [scoped threats](.planning/0003-bundled-controller/threat-model.md).

## Herdr sidebar handoff — 2026-09-10

- Accepted: run AllSet in a Herdr Local pane, prepare the selected project's
  remote workspace, return, and select it in the existing sidebar. No plugin,
  nested client, automatic agent launch, or migration of an existing SSH agent.
- Fresh worktree `fix/herdr-workspace-handoff` starts from main `97b76e3` and carries
  the already-installed uncommitted `fix/plain-ssh-setup` changes. Earlier SSH-only
  defaults documented below are superseded for Herdr callers by this decision.
- Implemented caller-aware auto routing plus explicit `--attach workspace`.
  Explicit SSH, prepare-only, separate Herdr client, and PTY modes remain available.
  Project/account identity still comes from validated configuration and ownership.
- Native remote workspace create/reuse preserves multiple panes, running agents,
  and focus. Lost responses reconcile before another mutation. The caller's
  native catalog is checked for the exact host/session; ambiguity fails safely.
- **Local/mock:** full race suite, vet, build, diff whitespace, document links,
  and built-artifact dry-runs passed. Fault tests cover stopped/restoring VMs,
  foreign/relative checkout records, duplicate labels/targets, and lost responses.
- **Installed:** the verified binary replaced `~/.local/bin/allset` atomically;
  previous binary saved to `~/.local/share/allset/backups/`.
- **Real remote:** Joymore reached its existing auto-stop deadline during work.
  The same saved VM resumed, completed filesystem restoration and preparation,
  and now has the native `joymore / project` workspace. Reconnect returned to
  the caller and preserved its workspace/pane/terminal IDs and cwd, with one
  enabled exact host/session catalog entry. No new VM or test agent was created.
  The existing two-hour auto-stop policy remains; no other project VM changed.
- **Account readiness observed:** Codex saved login is available; Claude/Cursor
  need sign-in, and this profile's GitHub access is unconfigured. These are not
  established by a successful workspace handoff. MCP sync changed zero files
  and reported no restarted agents.
- **Interactive/unverified:** sidebar click and real agent detection remain to
  be exercised; Herdr 0.9.0 has no API to select another machine in the current
  client. The returning handoff has no attachment-scoped login-cache monitor.
- Next: select the prepared Joymore workspace in Herdr and launch the chosen
  agent there to exercise the interactive Agents-list check. See
  [decisions](.planning/0002-herdr-workspace/decisions.md),
  [UAT](.planning/0002-herdr-workspace/uat.md), and
  [scoped threats](.planning/0002-herdr-workspace/threat-model.md).

## Decisions

- AllSet-only naming: `allset`, `.allset`, `ALLSET_CONFIG`.
- Free Go CLI under MIT; public source at `rawgroundbeef/allset`.
- Quiet alpha with issue-driven iteration; no coworker release gate.
- Box is compute; terminal interfaces and project account bindings stay separate.

## Completed in source

- Canonical executable/module/schema/config paths; alternate product aliases removed.
- Generic public examples; private prototype history excluded from the public snapshot.
- Repository-owned skills and domain/context docs.
- MIT, contribution/security guidance, issue forms, Linux/macOS CI, native release workflow.

## Verification

Local verification on macOS arm64:

- `go test -race ./...`, `go vet ./...`, and `git diff --check` passed.
- Four macOS/Linux arm64/amd64 native archives built; contents and checksums passed.
- Extracted macOS arm64 binary passed version/help/schema/backend smoke checks.
- Documentation links passed; Gitleaks 8.30.1 reported no findings in the source tree.
- Local review covered naming/identity, managed-file ownership, publication authority,
  resource behavior, and test gaps. This was a self-review, not an independent agent review.

The public repository is live. The first [CI run](https://github.com/rawgroundbeef/allset/actions/runs/34438370846)
passed on both GitHub-hosted Linux and macOS runners for initial commit `6cbfb8b`.
Private vulnerability reporting is enabled. The tag release workflow is present
but has not been exercised by publishing a release; npm packaging remains pending.
Remote provisioning, agent persistence, browser login/previews, and multi-agent
isolation were not tested by this source preparation work.

## Blockers and next action

- Implement supported new-project configuration and test npm distribution.
- npm publication is pending packaging and supported maintainer sign-in.
- Controller code is bundled; private profile creation still blocks complete
  fresh-laptop onboarding from `.allset` alone.
- See [.planning/0001-public-alpha/follow-ups.md](.planning/0001-public-alpha/follow-ups.md)
  for the remaining product workflows.


## Persistent terminal correction — 2026-09-10

Historical default; superseded by the ordinary SSH decision below.

- User requirement: closing a laptop disconnects the client; a running remote agent should continue, and the next open should return to its existing terminal.
- Work is isolated on `fix/persistent-terminal`; existing application worktrees and services were preserved. This fixes the existing CLI workflow while the proposed per-session VM/macOS product remains a separate, unimplemented direction.
- Default `auto` attachment now resolves to the existing raw remote-terminal transport. Herdr owns the remote shell; the user's terminal app presents it. Full Herdr UI and plain SSH remain explicit alternatives.
- Removed the special terminal-open bypass so MCP/no-MCP projects share preparation, account monitoring, and saved checkout ownership checks. Connect checks filesystem readiness without waiting, creating, or resuming a VM. No takeover/server replacement is added.
- Synthetic checks cover generic targets, hostile quoting, repeated attachment to the same terminal, child exit propagation, foreign checkout rejection, stopped/restoring machines, and ambient cmux/Herdr independence.
- Real remote proof: in an isolated Herdr test session, Codex ran a bounded task. The SSH client was explicitly disconnected. A new SSH observation confirmed the same PID and process start time still running; reattachment reached the same terminal. The agent subsequently exited zero with the expected answer. Normal Ctrl+b/q detach also succeeded. The temporary test server was stopped; the production agent server remained available. This used Codex exec inside the persistent pane; physical laptop sleep, overnight continuity, and interactive approval dialogs were not tested.
- Account was independently verified as standard/active after user payment. At user authorization, native Box no-auto-stop was applied to one existing small project VM and confirmed as archiveAfter=null. Other project VM deadlines were not changed. No extra VM, plan purchase, or top-up was made by this work.
- A private installed-controller budget guard was also corrected: an existing continuously running VM reserves compute across the requested bounded operation window instead of rejecting every other project launch. Timed VM reservations, inventory completeness, and unknown-window failures remain. Four synthetic tests passed. This controller fix remains local, not a claim of public Go extraction.
- Local installation: updated Go binary and controller guard installed with backups under ~/.local/state/allset/persistent-terminal-20260910/. Replacing the executable affects new invocations, not already-running clients. No public push/release performed.
- Verification: go test -race ./..., go vet ./..., go build -o bin/allset ./cmd/allset, git diff --check. All passed after the final transport/readiness changes.
- Installed CLI verification: default allset connect hey-lol attached in 6.53 seconds. Bare allset from the Hey project directory attached in 19.38 seconds with the persistent terminal announcement. Both detached with Ctrl+b/q and exited zero; no agent input or takeover was sent. Capture contents were discarded; only timing and exit evidence were saved privately.
- Self-review (not independent): correctness/ownership, security, resources, maintainability, and evidence checked. No blocking issue found in the changed connection scope.
- Narrow threat model: wrong project/machine or shell injection could attach to another user's process; existing explicit host/session and the widened checkout validation plus argv/quoting tests mitigate this. A disconnect must never become stop/takeover authority; raw attachment has neither mutation. Disabling auto-stop is a separate authorized provider mutation and is not inferred from account payment. Remaining resource risk: balance exhaustion or provider interruption can still stop a VM; bounded reservations do not guarantee unlimited future funding.
- Limitations: VM stop still ends processes. Current create/resume defaults remain two hours; manual stop/resume requires reviewing auto-stop again. Existing plain-SSH agents are not migrated. An occupied raw terminal is refused, never taken over. Work kept only in /tmp is not recovered by this change; the earlier missing-worktree recovery remains separate. Full multi-project app/preview/credential acceptance remains outstanding.
- Next: observe one natural laptop-close/reopen cycle through the verified bare allset entry point without changing active work. Resolve any remaining missing uncommitted work from the previous temporary checkout separately.


## Ordinary SSH default — 2026-09-10

- Current user decision: prepare the repository, tooling, and explicitly bound credentials, then open ordinary SSH. Do not choose Herdr, tmux, a pane, or an agent for the user. Existing session interfaces remain opt-in.
- Work isolated in `fix/plain-ssh-setup`; the earlier persistence worktree and all active application branches/services remain intact. `auto` now resolves to SSH. `open`, preparation-only, and agent login skip session-runtime installation, hooks, registration, and pane creation. Explicit Herdr modes retain their previous preparation.
- Updated the separately installed controller alongside the Go binary. Repository preparation needs no Herdr identity; ownership includes project, machine, role and absolute checkout directory. Restoration messages now describe project readiness. No existing server was restarted or session migrated.
- Local gates passed: `go test -race ./...`, `go vet ./...`, `go build -o bin/allset ./cmd/allset`, and `git diff --check`. Four private controller tests cover ordinary preparation on new/existing machines, checkout ownership and explicit-only Herdr bootstrap. These private adapter changes are not shipped in this source tree.
- Real remote proof: installed bare `allset` from a newly registered project opened its correct branch/directory and exited successfully. Instrumentation made every local Herdr registration, pane, environment, and runtime helper throw; none was invoked. No agent or app was automatically launched.
- Configured that project's existing independent Infisical identity and personal agent account. Frozen dependencies and three representative isolated unit tests pass; native Codex authentication succeeds. App startup, preview routing, browser authentication, and full multi-project acceptance are still unverified.
- The Box GitHub connection lacked access to the selected repository. A private adapter now supports an explicit existing native GitHub CLI account, selected with `gh auth token --user` without switching the local account. It validates the account and repository before sending the credential through authenticated SSH stdin into private tmpfs. A project-owned dispatcher supplies supported `GH_TOKEN` to native gh; Git uses that dispatcher explicitly. No credential value is committed, logged, placed in argv, or added to a reusable template.
- Credential threat checks: ambient Box tokens must not override the named account; foreign machine/project targets fail before credential reads; unowned dispatchers and shared/symlink credential storage are refused; failed authentication preserves the prior credential. Seven synthetic tests pass. Account pinning does not reduce the existing token's GitHub permissions; no additional permission was requested. Credentials are refreshed on open and lost on VM stop, while public binding metadata persists.
- Remote GitHub identity, repository API access and Git remote reads pass through the project credential. Native gh file-login initially retained a different token without the needed repo access; the supported headless environment flow resolves it without changing Box permissions or another project's login. No cause beyond that observed mismatch is claimed.
- Public extraction/onboarding, previews, remaining interactive agent auth, and a distributable full project requirements schema remain outstanding. No public push, publication, purchase, or extra VM resulted from this correction.
- Final bare-CLI remote acceptance: correct project checkout/branch, native GitHub account and remote refs, Infisical app-secret injection, and native Codex login all succeeded; child exit zero, Herdr helpers forbidden. Shell readiness took 61.43 seconds and full read-only probe 74.22 seconds. The workflow is functional but fast/instant startup remains unmet; profile unchanged-project preparation before claiming that milestone.
