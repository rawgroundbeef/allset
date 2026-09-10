---
name: allset-grill
description: Stress-test an AllSet proposal against code, domain language, and existing decisions. Use when the user asks to grill, challenge scope, resolve architecture or product choices, or sharpen requirements before planning.
---

# Grill with durable decisions

Read [CONTEXT.md](../../../CONTEXT.md), current architecture, and the active slice
before asking questions. Treat accepted user decisions as settled unless new
evidence exposes a contradiction. Do not make the user repeat repository facts.

1. State the problem and the observable outcome in the domain's language.
2. Inspect the code and relevant official documentation to settle factual claims.
   Separate current behavior, proposed behavior, assumptions, and unknowns.
3. Find the next decision that materially changes scope, ownership, cost, trust,
   or acceptance. Challenge vague terms such as "instant", "ready", "persistent",
   "supports", and "automatic" with a concrete success and failure scenario.
4. Ask **one focused question**, give a recommendation and its trade-off, and
   explain any useful work that can proceed while it is unanswered. Wait for an
   answer before treating that choice as settled. Routine reversible choices
   within the user's authorization do not require another approval.
5. Record the answer where it belongs and continue from the remaining uncertainty.

## Where decisions live

- `discovery.md`: problem, evidence, constraints, non-goals, and open questions.
- `decisions.md`: accepted choices and rationale, rejected alternatives, and a
  separately labeled pending queue. A recommendation is not an accepted decision.
- CONTEXT.md: reusable domain definitions and ownership only. Keep implementation
  details and one-off feature choices out of the glossary.
- `docs/adr/NNNN-slug.md`: a durable architectural decision only when it is costly
  to reverse, surprising without context, and the result of a real trade-off.
  Create the directory lazily; a short statement of context, choice, and reason
  is enough. Record proposed/accepted/superseded status honestly.

Use [allset-domain](../allset-domain/SKILL.md) for disputed concepts and
[allset-threat-model](../allset-threat-model/SKILL.md) for a changed trust boundary.
When scope is coherent, feed the evidence into
[allset-slice](../allset-slice/SKILL.md). A list of promising milestones is still
discovery until the user-facing acceptance behavior is concrete.
