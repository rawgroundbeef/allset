# Remote session onboarding follow-ups

## Bugs Discovered

None separately confirmed. New private binding creation, session secret
delivery, and selected skill application are current-slice gaps, not deferrals.

## Deferred Slice Ideas

- **2026-09-11 — Add explicit personal-skill management.** The minimal first-run
  path no longer asks for optional absolute skill directories. Existing private
  profiles retain support, while adding or removing personal skill sources needs
  a separate explicit settings command with the same ownership and conflict checks.
- **2026-09-11 — Compare VM providers and shape provider selection.** Requested
  by the user after first-time Box onboarding. Research persistent remote coding
  environments: native account onboarding, API/CLI support, lifecycle and storage
  persistence, tool compatibility, startup/restore latency, regions/architectures,
  allowance/billing, SSH/session behavior, and credential handling. Use current
  primary sources then. Decide which providers to integrate and whether setup
  should recommend or ask for one. No additional provider is selected now.

## Product Questions

No outstanding language/framework or app-preview question. Those were removed
by the user's explicit focus on remote coding sessions and automatic account/
integration binding. The user-approved acceptance describes the corrected target.

## Cleanup / Refactor Notes

- **2026-09-11 — Align the guide and CLI (completed locally).** Implementation
  updated help, the agent guide, architecture/configuration/MCP docs, schemas,
  and tests around the session-first flow. Historical evidence remains labeled.
- **2026-09-11 — Preserve optional app features.** Existing app preparation and
  previews are not removed, repaired, or required by this slice. The earlier
  preview/Herdr coupling observation must not expand onboarding into app hosting.

## Environment / Testing Notes

- **2026-09-11 — Native behavior needs real evidence.** Existing sign-in coverage
  is local/mock. Fresh remote preparation, correct model-account use, MCP calls,
  skill invocation, secret delivery, and cold/warm timing remain unverified.
- **2026-09-11 — Provider response shapes.** Read-only live checks confirmed Box
  0.1.228's `account.identifier`/`loginState` status fields and environment-list
  `safeForThirdParties` field. The status parser was corrected and the rebuilt
  binary reached creation confirmation. Environment creation/safety mutations
  still require real UAT; read-only field inspection does not prove those effects.
- **2026-09-11 — Native launch behavior.** The wrapper preserves argv by `execve`
  and affects only future launches in the project-owned environment. Real native
  resume/browser/TTY behavior and first-turn discovery remain unverified.
- **2026-09-11 — Local worktrees.** Planning remains in
  `/private/tmp/allset-guided-onboarding-20260911` on `feat/guided-onboarding`.
  Implementation uses the separate preserved worktree
  `/private/tmp/allset-guided-onboarding-impl-20260911` from `79f0f87`.
