# Project environments from any terminal

A project selects a compute backend, such as Box. It does not select the user's
terminal. The user runs `allset` in a repository from whichever interface they
already opened. AllSet resolves the project's environment and connects there.

## Boundaries

- `internal/config` owns strict repository manifests, the local shortcut registry,
  discovery bounded by Git worktrees, identity validation, and read-only migration.
- `internal/cli` owns current-project resolution, init interaction, and command
  dispatch. It does not know Box machine IDs or account storage formats.
- `internal/strategy` defines provider-independent project operations, status,
  diagnosis, and execution plans. `internal/wiring` selects installed strategies.
- `internal/providers/box` owns native read-only Box information queries.
- `internal/strategies/box` composes compute with the existing workspace adapter.
- `internal/terminal` implements connection transports selected per invocation.
  Auto means ordinary SSH in the current terminal, regardless of HERDR_ENV or
  cmux environment variables. Native Herdr views and prepare-only mode require
  explicit flags. There is no terminal field in project or registry config.
- `internal/execution` bounds child processes and performs terminal handoff.
- `internal/legacy` is the temporary workspace compatibility boundary, not a
  backend. Existing provisioning, allowance guards, auth, and workspace setup
  remain there during extraction.

The installed service registry currently contains only Box. Other compute
services require a real strategy, not a renamed Box adapter. Missing strategies
never fall back to Box. Contract tests use an unrelated fake provider without Box,
Python, or Herdr; this is not a second live cloud implementation.

## Discovery and init

The repository manifest has its own version (1), separate from registry version 3.
Discovery walks upward to the nearest Git worktree root, including linked
worktrees whose `.git` is a file. It never crosses a nested checkout boundary.
The nearest .allset must match origin and any saved project binding.
Malformed documents, unsupported fields, symlinks, and identity conflicts fail;
they never fall through into inference or first-time provisioning.

Absent a manifest, existing registry inference remains available for continuity.
An unknown repository enters init only during interactive open. Init creates a
strict file atomically, without clobbering files or copying accounts. Dry runs,
status, doctor, config inspection, cancellation, and validation never provision
or start the init flow. Config creation does not imply environment readiness.

Global registry v1/v2 documents normalize read-only to v3. The v1 bespoke backend
maps to Box; v2 terminal fields are accepted only as historical data and discarded.
New manifests and v3 registries reject terminal fields. Existing accounts, VM
pointers, authentication caches, and project profiles are not rewritten.

## Remaining extraction

The repository file currently declares the project binding, not complete
workspace requirements. Box preparation still invokes the installed controller,
which installs/reuses remote Herdr and registers it locally. The new default
connection does not open that UI, but preparation still has this dependency.
Removing the field is not full removal of the coupling.

The default SSH shell also lacks disconnect persistence. Existing Herdr panes
remain available explicitly. A provider-independent persistent shell transport
that works within the user's current terminal is still required to complete the
original resilience requirement without forcing a local UI.

A new manifest cannot yet bootstrap a new project's full local provider profile.
Init records the project choices and reports incomplete setup. Next implement
native requirements for tools/setup/services, per-user account binding and
supported login flows, plus idempotent apply and readiness probes. Do not accept
fields as implemented before their lifecycle is implemented and verified.

Existing provider allowance, creation lock, timeout reconciliation, filesystem
restoration, project ownership, and active-work preservation checks remain in the
adapter. These must survive extraction into native provider methods. Only the
Box info method has moved so far. Connect never resumes a stopped machine.

## Verification

Local tests cover discovery/root boundaries, init without credentials, cancellation,
noninteractive/dry-run guarantees, credential-bearing origins, malformed/foreign
manifests, old-format migration, unsupported strategies, and current-terminal
routing. Connection adapter tests use subprocess stubs. Full new-project provisioning, three apps/previews, and parallel
agent worktree isolation remain outstanding. See PROGRESS.md for current evidence.
