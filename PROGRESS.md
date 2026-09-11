# AllSet progress

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

- Extract standalone provider preparation and implement/test npm distribution.
- npm publication is pending packaging and supported maintainer sign-in.
- Extract the prototype controller before claiming standalone onboarding.
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
