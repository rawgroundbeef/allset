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
| Provider defaults inject account-wide credentials before selected bindings apply | High: installed Box help says new named environments enable injection by default | Native environment toggles and create no-env option exist; live behavior is unverified | Create/verify an owned environment with ambient injection disabled before compute creation. Preserve unrelated provider environments; test that selected bindings are the only applied identities. |
| A declared MCP secret name is marked configured but never reaches the remote process | High likelihood in current boundary; selected integration cannot work | Current MCP projection names environment variables but does not inject arbitrary Infisical paths | Bind approved secret sources and scopes to the actual client/MCP launch; prove an authenticated harmless call from that session without printing values. |
| Session receives unrelated secrets or secret-broker credentials | High impact: tools execute with inherited authority | Infisical context and existing child-env stripping are reusable controls | Deliver only the configured scope; keep broker credentials outside ordinary child contexts unless that client explicitly needs broker access. Test disjoint scopes, log/argv redaction, and changed laptop environment. |
| New login/context update changes an existing conversation's account | High impact to ongoing work and billing | Standard remote homes are currently shared within a project; no generic per-session home adapter exists | Verify native launch/config ownership before choosing storage strategy. Never overwrite a context being used under a different identity; apply deliberate updates to future launches without restarting existing conversations. |
| Wrong/cancelled native login is collected as usable credentials | High: partial auth is routine | Existing project lock, needs-login marker, selected-client validation | Preserve those checks through onboarding and automatic launch. Reject wrong identity, retain unrelated/previous material, and retry only the failed capability. |
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
