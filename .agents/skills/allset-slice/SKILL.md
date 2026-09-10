---
name: allset-slice
description: Plan one AllSet vertical slice through discovery, decisions, user acceptance, PRD, and a fresh-context handoff. Use for feature planning, public-alpha preparation, acceptance alignment, and resumable implementation briefs; skip the full pipeline for routine fixes.
---

# Slice planning

Read [AGENTS.md](../../../AGENTS.md) and resume from existing artifacts. Use the
repository-local companion skills linked below, not similarly named personal
skills. The pipeline serves the requested scope; explicit user instructions to
skip or change planning take precedence, and must be recorded.

## 1. Establish scope

Inspect Git state and preserve active work. For a new branch/task create a fresh
worktree from the verified base; do not switch an occupied worktree. Pick the next
four-digit prefix in `.planning/`, starting at `0001`. A slice keeps its number
across multiple PRs. Create files only when there is real content for that stage.

Define one demonstrable outcome. Split milestones that cannot share a meaningful
acceptance workflow instead of treating an entire product roadmap as one PR.

## 2. Discover and decide

Run [allset-grill](../allset-grill/SKILL.md). Write:

- `.planning/{NNNN-slug}/discovery.md`: request, refined problem, code/doc evidence,
  constraints, non-goals, current limitations, and open questions.
- `decisions.md`: accepted choices with reasons, rejected alternatives, pending
  decisions, and links to reusable glossary or ADR changes.
- `follow-ups.md`: dated findings and deferred work using the order below.

Use [allset-domain](../allset-domain/SKILL.md) for changed concepts. For new or
changed account/secret handling, executable config/MCPs, privileged provider
actions, preview exposure, or release authority, run
[allset-threat-model](../allset-threat-model/SKILL.md). Record controls in the
slice; they must become acceptance checks and requirements.

## 3. Align through UAT

Use [allset-uat](../allset-uat/SKILL.md) to write `uat.md` **before** the PRD.
Show the concrete workflow, expected result, durable side effects, and guardrails.
Separate future acceptance steps from executable checks that already exist.

Present that document and obtain explicit confirmation that it describes the
intended behavior before writing the PRD. Do not treat silence or a general
"continue" given before the document existed as approval of its contents. While
waiting, investigate independent facts and record them without deciding the
pending behavior. Explain this alignment gate and link to this skill when asking.

## 4. Specify and hand off

After acceptance is agreed, use [allset-prd](../allset-prd/SKILL.md) for `prd.md`.
Resolve contradictions in the upstream document rather than concealing them in
implementation notes. If multiple PRs are needed, state order and dependencies.

Then write `bootstrap.md` containing:

- Goal and artifact read order, with repository-relative paths.
- Accepted constraints, scope, and excluded work.
- Verified module pointers and applicable local skills.
- Branch sequence, verification gates, and acceptance environment requirements.
- The instruction to work from these documents, not remembered conversation.

Read the full set cold in that order. Challenge unsupported code references,
unobservable acceptance claims, missing recovery paths, contradictory scope, and
unstated account/budget requirements. Fix each problem in its owning artifact.
Use an independent reviewer only when delegation is explicitly authorized under
AGENTS.md; otherwise disclose that the consistency review is not independent.

Report the review result and bootstrap path. Default to a fresh implementation
context for a planning handoff; do not quietly begin implementation in the same
planning turn. If the user explicitly requests implementation here, follow that
scope and record the exception rather than inventing another permission gate.

## 5. Implement and verify

Load the bootstrap and relevant pattern/domain skills. Preserve unrelated work,
implement the agreed behavior, and run AGENTS.md verification gates. Use
[allset-review](../allset-review/SKILL.md) on the final diff; fix blocking findings
and rerun the affected checks. Honor the same delegation policy and disclose
whether review was independent. Never substitute a mock result for real UAT.

## Artifact maintenance

Keep follow-ups in this order:

1. Bugs Discovered
2. Deferred Slice Ideas
3. Product Questions
4. Cleanup / Refactor Notes
5. Environment / Testing Notes

Date concrete findings, link evidence, and note when an item is scheduled or
rejected. Do not silently delete unresolved work. Amend stale artifacts without
regenerating approved decisions. Keep current acceptance blockers in discovery
or UAT as well; moving them to follow-ups does not make the slice complete.

Planning is ready when discovery, decisions, approved UAT, PRD, and bootstrap
agree and the consistency review has no blocking findings. Implementation is
ready when relevant gates and the agreed acceptance workflow pass. If blocked,
report the work as incomplete, with the blocker and unverified behavior explicit.
