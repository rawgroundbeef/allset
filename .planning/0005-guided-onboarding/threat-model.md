# Remote session account and integration boundaries

Status: controls implemented and exercised locally with synthetic boundaries on
2026-09-11; real provider/account/session proof remains unexecuted.

Actors are the developer, repository/integration/skill sources, external account
and compute services, and concurrent AllSet/client processes. Assets are account
credentials, scoped secrets, model/compute allowance, project work, and ongoing
conversations. The key flow is chosen private bindings to the intended remote
client launch and its MCP/tool processes.

| Failure scenario | Priority and reason | Existing evidence | Required control and proof |
| --- | --- | --- | --- |
| Ambient or another project's account becomes the new session's identity | High: common multi-account laptop setup; access/spend under the wrong identity | Native login/status and project-scoped credential caches cover configured projects | The first native OAuth flow establishes and records the status-verified identity. Later sign-ins must match that binding before credentials are cached. Different synthetic projects/accounts cannot cross. |
| Unrelated status fields are mistaken for Box account identity | High: billing/config contacts do not establish the signed-in account | Real Box 0.1.228 reports `account.identifier` and `account.loginState`; the adapter reads only account fields and preserves the private email/id format | Reject inactive, malformed, missing, or conflicting identities before mutation. Regression tests cover unrelated contacts, current native fields, legacy fields, and changed-account refusal. |
| Ambient Git credentials make a private repository look public during setup | High: setup could omit the required account binding, provision compute, then fail or use unrelated authority | Public-access detection runs `git ls-remote` with an isolated temporary home, no system/global config, no credential helper, and prompting disabled | Keep the probe credential-free and bounded. Unit tests must assert the sterile environment and arguments; real private-repository behavior remains UAT evidence. |
| Accepting a full source URL leaks inline credentials or selects ambient SSH auth | High impact: source-fetch authority must match the selected project account | Source preparation validates with `repository_access.github_repository` before auth/fetch, uses HTTPS for clean/named-account flows, and never treats an explicit URL as a local path | Mitigated by rejecting credential-bearing URLs, queries/fragments, foreign hosts and traversal before subprocess/account calls. Tests preserve legacy SSH transport, validate clean canonical fetches, and prove local work is unchanged. |
| Provider defaults inject account-wide credentials before selected bindings apply | High: installed Box help says new named environments enable injection by default | Native environment toggles and create no-env option exist; live behavior is unverified | Create/verify an owned environment with ambient injection disabled before compute creation. Preserve unrelated provider environments; test that selected bindings are the only applied identities. |
| A declared MCP secret name is marked configured but never reaches the remote process | High likelihood in current boundary; selected integration cannot work | Current MCP projection names environment variables but does not inject arbitrary Infisical paths | Bind approved secret sources and scopes to the actual client/MCP launch; prove an authenticated harmless call from that session without printing values. |
| Session receives unrelated secrets or secret-broker credentials | High impact: tools execute with inherited authority | Infisical context and existing child-env stripping are reusable controls | Deliver only the configured scope; keep broker credentials outside ordinary child contexts unless that client explicitly needs broker access. Test disjoint scopes, log/argv redaction, and changed laptop environment. |
| New login/context update changes an existing conversation's account | High impact to ongoing work and billing | Standard remote homes are currently shared within a project; no generic per-session home adapter exists | Verify native launch/config ownership before choosing storage strategy. Never overwrite a context being used under a different identity; apply deliberate updates to future launches without restarting existing conversations. |
| Wrong/cancelled native login is collected as usable credentials | High: partial auth is routine | Existing project lock, needs-login marker, selected-client validation | Preserve those checks through onboarding and automatic launch. Reject wrong identity, retain unrelated/previous material, and retry only the failed capability. |
| Skipping an interrupted login silently accepts its partial credentials | High impact: a native CLI can write credentials before AllSet verifies identity | Guided auth holds the project operation lock; skip writes project/profile/client-bound `needs_login` and `onboarding_skipped` state | Mitigated by excluding the client from restore/background capture and per-client MCP auth. Only verified explicit repair clears the marker. Synthetic tests cover skip, warm reuse, cache ownership, and repair. Skipping does not revoke or remove remote native credentials; same-user isolation remains out of scope. |
| Sign-in repair fetches project secrets or fails outside the checkout | Medium likelihood: native SSH authentication starts at home after wrappers are installed | Installed wrappers route only native login/status directly to the preserved executable, excluding scoped and broker variables | Mitigated by testing the actual installed wrapper without Infisical companions, outside the checkout. Normal conversation commands must retain cwd and scoped-secret checks. |
| MCP or skill content expands onboarding authority | High: executable MCPs and skill instructions are externally supplied | MCP transport/schema checks and managed-file ownership exist; skill application does not | Install only selected sources in owned native scopes. Source text is not consent for new accounts, secret scope, purchases, or sandbox changes. Test malformed paths and conflicting user edits. |
| Tool/template reuse carries another project's credentials | High impact: leaks accounts across environments | Existing template invariants and separate project caches | Reusable tooling contains no account homes, tokens, or project contexts. First-time packaged proof cannot rely on the developer's real home. |
| Interrupted provider mutation creates duplicate machines | High: expected retry path can spend allowance/split work | Existing creation/resume reconciliation | Persist/reconcile the owned operation before repeating it; inject timeout after remote success and prove one machine. |
| Speed optimization skips identity checks or drops active work | High impact despite a legitimate latency goal | Existing ownership, restore, and non-takeover guards | Reuse unchanged preparation, not stale identity assumptions. Test revoked auth, foreign pointer, partial restore, and concurrent active sessions on the warm path. |
| File copy or saved cache is reported as a usable session | Medium/high: false completion was the original failure | Native status/auth and MCP APIs exist, but end-to-end proof is missing | Verify client account use and the selected MCP/skill/secret outcomes from the intended session; distinguish configured, ready, pending, and explicitly skipped. |

Automatic context binding does not establish strong OS isolation between
same-Unix-user processes. No new sandbox claim or permission relaxation is part
of this slice. App service execution and preview routing were removed from
scope; preserve their existing controls without adding new orchestration.

The implementation adds strict shared declarations, private identity-bound
journals, no-ambient Box environment setup, timeout reconciliation, managed-file
conflict checks, future-process launch wrappers, and scoped secret selection.
Local fault tests cover the principal wrong-account, duplicate-mutation,
unmanaged-edit, argv/cwd, and secret-filtering paths. No live credential
operation, provider mutation, first-turn integration proof, or material residual-
risk acceptance has occurred; those remain explicit UAT evidence gaps.
