---
name: allset-uat
description: Define or execute observable AllSet user acceptance checks. Use for a slice UAT, CLI smoke test, coworker onboarding proof, preview verification, lifecycle recovery, or a manual demo; distinguish planned checks from actual evidence.
---

# User acceptance

Read the request, slice discovery/decisions, current command contracts, and
[AGENTS.md](../../../AGENTS.md). Derive checks from behavior a developer can
observe, including durable side effects. Do not turn internal function names into
acceptance criteria or claim an unsupported command already exists.

Write the active slice's `uat.md` with:

1. **Scope and status:** what is being proven; draft, agreed, or executed, with date.
2. **Prerequisites:** revision/artifact, host platform, actors/account bindings,
   repository fixture, provider allowance, and needed services. Name secure
   references, never secret values. Separate public fixtures from private UAT.
3. **Primary workflow:** starting state, exact command/action, expected visible
   result, and durable state to inspect. Label proposed commands as proposed.
4. **Guardrails and recovery:** relevant negative cases and how to reconnect,
   retry, or clean up without affecting active work.
5. **Pass criterion and evidence:** one demo-ready statement plus result, artifact
   revision, observed output, and any remaining manual step for each check.

## Choose checks for the changed promise

| Promise | Evidence that matters |
| --- | --- |
| Clean onboarding | Built/packaged artifact on a clean account context, with no developer's private controller or credentials |
| Open/reuse/resume | Same intended project machine, actual filesystem/worktree ready, no duplicate VM after timeout |
| Multiple agents | Distinct worktrees/branches and app ports; stopping one preserves the other's process and changes |
| Project authentication | Correct service identity and intended resource access; refresh/restart of one project leaves another usable |
| Persistent work | Disconnect client, reconnect to the same running session; separately stop/resume and record what restarts |
| Usable previews | Labeled URLs reach intended branch and backend; login/callback/cookie behavior and HMR where applicable |
| Integrations | Declared MCP starts in a new target agent session and exposes expected tools; registration alone is insufficient |
| Collect/stop | Separate changes are recoverable before cleanup; VM state and any continuing usage are recorded |
| Release/install | Packaged artifact installs and reports expected revision; no unexpected auth/cloud calls during inspection |

Select relevant rows; do not demand every workflow for an unrelated change.
Use bounded, reversible tasks. Honor the user's resource limits and existing
services. Stopping a VM affects every session on it; dropping a UI connection
does not stop the VM. Never run migrations or mutate live data merely to make
an acceptance check pass without the applicable authorization.

State evidence as **local/mock**, **real remote**, **interactive**, or
**unverified**. A login screen is not a successful authenticated workflow. When
human interaction is essential, prepare everything else and provide the exact
URL and a short check. Do not ask users to paste credentials or do shell work
the agent can do. Never mark a pending human step as passed.

The [slice skill](../allset-slice/SKILL.md) owns the UAT alignment gate. A standalone
request to execute already authorized UAT does not need a second approval just
because this skill was loaded.
