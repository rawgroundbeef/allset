---
name: allset-patterns
description: Apply AllSet implementation patterns for Go CLI code, strict JSON configuration, provider adapters, subprocesses, native MCP projection, and recovery. Use while implementing, refactoring, or reviewing these areas.
---

# Implementation patterns

Read [AGENTS.md](../../../AGENTS.md) and
[architecture](../../../docs/architecture.md). Use
[allset-domain](../allset-domain/SKILL.md) when ownership or terminology changes.

## Keep contracts at their boundaries

- `internal/cli` resolves intent and renders results; it must not learn provider
  machine IDs or credential storage formats. Keep entry points thin.
- `internal/strategy` owns the provider-independent contract. Add the smallest
  interface needed by real behavior, and prove it with a provider-neutral fake.
  An unavailable provider fails explicitly instead of falling back to Box.
- `internal/providers/box` contains native compute queries;
  `internal/strategies/box` composes them with workspace behavior. Extract from
  `internal/legacy` behind tests without losing identity, allowance, or recovery
  checks. Do not add unrelated features to the compatibility bridge.
- `internal/terminal` targets explicit hosts and sessions. UI selection and
  ambient Herdr/cmux variables must not silently retarget a local command.
- `internal/mcps` translates declarations into supported agent formats; share
  desired meaning, not one client's flags or authentication cache with another.

## Go and process contracts

- Prefer explicit dependencies, small concrete types, and errors that callers can
  classify. Use interfaces at external boundaries; avoid a framework of wrappers
  around every function. Pass `context.Context` through blocking operations.
- Comments explain ownership, side effects, and non-obvious recovery constraints.
  Use normal Go documentation conventions, not another repository's JSDoc rules.
- Bound subprocess duration/output and propagate cancellation. Build argv arrays
  instead of interpolating shell text. Where shell syntax is required, separate
  the fixed script from untrusted arguments and test quoting at that boundary.
- Keep credentials out of argv, printable plans, logs, and errors. Return curated
  metadata instead of raw provider/CLI responses that may contain secrets.
- Preserve stdin/TTY and child exit behavior on interactive handoff. Keep JSON
  output parseable and diagnostics separate. Do not report success after a failed
  subprocess or leave a detached helper with no recorded lifecycle owner.
- Embedded Python remains a bounded adapter/runtime implementation. Keep its
  protocol explicit and test it through the Go boundary as well as focused faults.

## Configuration and managed files

- Parse external input once into a validated type. Reject unsupported fields,
  versions, malformed paths, and contradictory identities before side effects.
  Keep schemas, parser behavior, help, examples, and exit behavior consistent.
- Preserve Git discovery boundaries, including linked worktrees. Broken or
  mismatched config must not fall through to guessed accounts or provisioning.
- Apply only declared, implemented capabilities. A saved document or generated
  native config does not prove installation, authentication, or readiness.
- Distinguish files/entries owned by AllSet from user-managed content. Check
  ownership and concurrent edits, lock at the scope of shared mutable state, and
  use atomic writes. Refuse a conflict without clobbering the user's changes.
- Version migrations explicitly. Inspection stays read-only. Renaming product
  labels must not accidentally orphan credential references, locks, journals,
  or native client ownership markers.

## Lifecycle and verification

A mutation timeout means unknown outcome. Reconcile the intended resource before
retrying; never assume it failed. Readiness must establish the correct machine,
restored files, valid worktree, completed setup, and required app/integration probes
for the operation being promised. Use bounded waits with stage/progress output.

Test changed contracts using synthetic accounts and temporary homes/worktrees.
High-value faults include a mutation that succeeds before timing out, stale host
identity, partial restore, expired auth, cross-project binding, concurrent config
edits, a required MCP failing to start, and disconnect/stop confusion. Select the
faults relevant to the diff. Fakes do not prove a real provider or browser flow.

Run the applicable gates in AGENTS.md. Update the contract docs and progress
evidence with behavior changes. Load
[allset-threat-model](../allset-threat-model/SKILL.md) when changing trust or
privilege boundaries; a formatting-only edit needs no threat exercise.
