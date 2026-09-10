---
name: allset-review
description: Review an AllSet diff, branch, or PR for correctness, domain boundaries, security, performance, maintainability, and test coverage. Use for a final review or merge-readiness check; report actionable findings without modifying implementation.
---

# Review the behavior

Establish the requested scope and base from Git; exclude unrelated dirty files.
Read [AGENTS.md](../../../AGENTS.md), the patch, relevant callers/tests, and slice
acceptance. If no remote/default branch exists, use the documented local base.
Do not invent an upstream or review the whole repository by accident.

Run these passes in order:

1. **Correctness and ownership:** trace input through decision, side effect, and
   result. Check identity, transitions, errors, cancellation, and contracts using
   [allset-domain](../allset-domain/SKILL.md) and
   [allset-patterns](../allset-patterns/SKILL.md).
2. **Security:** inspect changed trust boundaries and credential handling. Load
   [allset-threat-model](../allset-threat-model/SKILL.md) when warranted. Test
   cross-project selection, secret-bearing error paths, and managed-file conflicts
   when those paths are changed.
3. **Performance/resources:** consider bounded polling, subprocess lifetime,
   output size, repeated dependency work, locks, API fan-out, and unintended VM
   usage. Tie each concern to an actual path and plausible workload.
4. **Maintainability:** find duplicated policy, provider details leaking into the
   CLI, unnecessary abstraction, misleading names, and migration coupling.
5. **Testing/evidence:** look for meaningful negative and recovery coverage;
   distinguish fake contracts from real provider, agent, and browser verification.
   A green unit suite does not close an unexecuted acceptance requirement.

## Findings

Each finding needs a precise file/line, triggering scenario, observed effect,
impact, and smallest useful fix direction. Report issues caused or worsened by
the diff. Do not fill the report with speculative risks or style preferences.

- **Request changes:** actionable bug, violated invariant, security problem,
  material resource regression, or missing coverage for risky changed behavior.
- **Warn:** concrete non-blocking cleanup or follow-up. Keep it separate from
  release blockers; an acceptance failure cannot be downgraded by moving it here.

Report findings first, then verification and a verdict of APPROVE or REQUEST
CHANGES. APPROVE means no blocking finding in the reviewed scope; it is neither
publication authorization nor evidence that unrun live workflows passed. Say
explicitly when there are no findings and what remains unverified.

## Execution and follow-ups

This is a read-only code review. Run relevant checks within the existing scope;
do not repair code, log into accounts, provision, or restart active services as
part of inspection. An implementation task may address findings afterward.
Record commands/results and environmental blockers accurately.

If the scope has an unambiguous active slice, append deferred warnings to its
`follow-ups.md` in the appropriate existing category, dated and linked to code.
Otherwise keep them in the report. Do not guess a slice or edit reviewed code.

AGENTS.md governs delegation. Use an independent reviewer when explicitly
authorized; otherwise perform the passes locally and label the review as not
independent. Never imply a self-review was a separate agent's review.
