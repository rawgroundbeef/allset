# Scoped handoff threats — 2026-09-10

Assets are the developer's project/account binding and the active VM's processes,
worktrees, and native Herdr sessions. The new input is caller interface context;
the effects are native workspace creation and local machine registration.

| Failure | Likelihood / impact | Control and owner | Evidence / disposition |
| --- | --- | --- | --- |
| Ambient UI selection opens another project's VM or account | Plausible / high | Config and existing strategy validate the project; the terminal adapter receives its explicit host and session. HERDR_ENV and HERDR_CONFIG_PATH affect only interface/catalog. | CLI routing and foreign checkout tests; mitigated. |
| Reconnect steals focus, kills an agent, or fails on split panes | Previously present / high | Workspace adapter reuses unique labels without pane targeting, input, focus, or takeover; native catalog setup has stdin closed. | Full bridge split-workspace tests and native invocation assertions; mitigated. |
| Lost create/add response duplicates a workspace or profile | Plausible / medium | Observe live state after failure; never immediately repeat the mutation. Reject ambiguous matches. | Timeout and duplicate-label/profile tests; mitigated. |
| Stale checkout or unrestored/stopped VM receives a workspace | Plausible / high | Existing ownership and filesystem checks precede the adapter; connect cannot resume or prepare a repository. | Connect fault tests; mitigated. |

Residual: external Herdr clients do not share AllSet's project lock. Concurrent
manual edits can produce ambiguous labels; subsequent calls fail and preserve
them. Native Herdr still owns catalog write locking. No new credentials, account
selection, public endpoint, server replacement authority, or publication is added.
