---
name: allset-prd
description: Write an AllSet PRD from discovered requirements, accepted decisions, and agreed UAT. Use when formalizing a feature or public-alpha slice into implementable scope and module responsibilities.
---

# Requirements from acceptance

Read the active slice's discovery, decisions, and UAT, plus
[CONTEXT.md](../../../CONTEXT.md) and relevant architecture/code. Within the
[slice pipeline](../allset-slice/SKILL.md), confirm that UAT alignment happened
before writing the PRD. For a standalone drafting request, label unapproved
assumptions and open decisions; do not manufacture acceptance or approvals.

Write `prd.md` with:

- **Problem and outcome:** developer pain and the observable improvement.
- **Scope/non-goals:** the smallest coherent slice and excluded promises.
- **Requirements:** numbered behavior, actor/ownership, relevant failure cases,
  and durable side effects. Link each requirement to a UAT scenario.
- **Module responsibilities:** current entry points, owning types/workflows,
  I/O boundaries, and any new contract. Link verified paths; label new ones as
  proposed. Use [allset-patterns](../allset-patterns/SKILL.md).
- **Trust and lifecycle:** applicable threat controls, reconciliation, credential
  expiry, active-work preservation, compatibility, and resource accounting.
- **Delivery/verification:** PR order when needed, focused tests, AGENTS.md gates,
  live acceptance prerequisites, and rollback/recovery for the changed behavior.
- **Open issues/follow-ups:** unresolved choices and dependencies with ownership.

Requirements must distinguish declared, configured, authenticated, ready, and
verified behavior. Supporting an interface with a fake does not establish a live
provider implementation. Do not promise transparent persistence, arbitrary
providers, or unattended OAuth simply because they are desirable.

If requirements conflict with UAT or a decision, return to that artifact and
resolve the conflict. Ask one focused question only when evidence cannot settle
it. Keep proposed options out of accepted requirements. Reference decisions and
UAT rather than duplicating them; the PRD explains what must be implemented and
where responsibility belongs.
