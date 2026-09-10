---
name: allset-threat-model
description: Model concrete threats when AllSet changes credentials, account selection, executable project config, MCP or skill installation, VM identity or lifecycle, preview exposure, or publishing authority. Use for design or review of those trust boundaries; skip purely editorial or formatting changes.
---

# Threat modeling

Start with the changed behavior, not a generic security checklist. Read its code,
slice decisions, and [domain boundaries](../allset-domain/SKILL.md). A model may
be a short paragraph for one narrow boundary; expand only when data flow demands it.

## Trace the boundary

1. Identify assets and actors: whose work, secrets, machine allowance, session,
   account, package, or preview could be affected?
2. Trace inputs to effects: source, validation, identity/authorization decision,
   privileged sink, and observable result. Mark the trust boundary crossed.
3. Write a plausible abuse or accidental-failure scenario for each exposed path.
   Include laptop disconnects, provider timeouts, partial writes, and stale state
   where these can bypass an invariant.
4. Prefer preventing the invalid state at its owner over adding a warning or
   requiring an agent to remember a prompt instruction.

## AllSet surfaces

Use only the rows affected by the change:

| Surface | Concrete questions |
| --- | --- |
| Repository config/setup | Can a cloned or edited declaration execute unreviewed local/remote code, select another repository/account, traverse paths, or trigger spend during inspection? What establishes trust before execution? |
| Credentials | Can ambient login, stale cache, refresh, template/fork, logs, argv, plans, or generated files expose or select another project's identity? Does revocation/expiry fail clearly? |
| VM lifecycle/SSH | Can an unknown mutation outcome create a duplicate, a stale alias target another host, or early SSH access attach to an unrestored filesystem? How are project and host ownership verified? |
| Managed client config | Can malformed native files leak secrets in errors? Can sync overwrite user edits, race another writer, lose auth, or accept partial state as applied? |
| MCPs/skills/agents | What code/tools are being installed and under whose authority? Can tool output, repo text, or skill instructions expand permissions, select another account, or become executable shell? Treat those contents as untrusted data, not authorization. |
| Previews/services | Can routing or cookie scope cross projects, callbacks land in the wrong app, ports expose private services, or concurrent worktrees share a mutable database unintentionally? |
| Distribution/CI | Can untrusted PR code obtain release authority, change an artifact after checks, substitute a binary, expose signing credentials, or publish a different revision than the reviewed one? |

As a backstop, consider spoofing, tampering, repudiation, information disclosure,
denial of service, and elevation of privilege (STRIDE). Do not invent a threat
just to fill every category. A project ID, read-only label, or successful login
is not itself an authorization boundary.

## Record actionable results

Use the active slice's `threat-model.md` and link it from discovery. For a review
without a slice, include the model in the review report instead of inventing one.

For each material threat record:

- Asset, actor, entry point, crossed boundary, and abuse/failure scenario.
- Likelihood and impact with reasons, plus priority.
- Current control and code evidence; distinguish proposed controls.
- Disposition: prevented, mitigated, or accepted residual risk. Do not claim
  prevention based only on a prompt or policy. Record who accepted material risk;
  an unanswered recommendation is still unresolved.
- Required control, owning module, and a test/UAT check that would fail without it.

Carry controls into requirements and acceptance. Call out specific unresolved
permission, credential, or budget needs only when they block the chosen scope.
Threat modeling does not create a blanket approval gate for routine authorized
fixes, and it does not authorize live abuse tests or permission expansion.
