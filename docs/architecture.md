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
  Auto with `HERDR_ENV=1` requests a native remote workspace handoff; elsewhere
  it opens ordinary SSH. Explicit transports override that choice. Caller UI
  context never chooses the target VM, session, project, or account. There is
  no terminal field in repository or registry config.
- `internal/execution` bounds child processes and performs terminal handoff.
- `internal/legacy` adapts existing private profiles/state and builds execution
  plans; it is not a backend. `internal/controller` embeds the versioned Python
  runtime for provisioning, allowance guards, auth, and workspace setup.

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

Absent a manifest, interactive current-project open enters configuration review
and, after approval, continues into guided environment onboarding. Saved registry bindings
are displayed for an explicit choice before creating the file. The review also
offers a configuration-only prompt for the user’s coding agent and cancellation.
Explicit `init` reopens the configuration-only review without overwriting it. Named shortcuts and noninteractive calls keep
registry inference for continuity. An unknown repository enters init only during
interactive open. Init creates a
strict file atomically, without clobbering files or copying accounts. Dry runs,
status, doctor, config inspection, cancellation, dry-run, and validation never
provision or initiate sign-in. Config creation alone does not imply readiness.

Global registry v1/v2 documents normalize read-only to v3. The v1 bespoke backend
maps to Box; v2 terminal fields are accepted only as historical data and discarded.
New manifests and v3 registries reject terminal fields. Existing accounts, VM
pointers, authentication caches, and project profiles are not rewritten.

## Bundled runtime

The Go executable contains the source allowlist in `internal/controller/runtime`.
It invokes Python in isolated mode and atomically installs the embedded archive
under `$XDG_CACHE_HOME/allset/controller/<sha256>` (default `~/.cache`). Each
execution verifies file names, bytes, ownership and private permissions before
importing code. Unexpected files, modified files and symlink paths fail without
overwriting them. This protects against accidental cache substitution; it is not
a sandbox against another process already controlling the same user account.

Planning, status, doctor and inspection never extract code. The Go plan supplies
the state directory and native Box/Herdr paths explicitly; inherited internal
variables cannot redirect them. Project data and credentials are not embedded.
The existing `~/.local/share/box-herdr` remains the private state location, but
its `controller/` directory is no longer an executable dependency of AllSet.
Other separately installed wrappers may still use that directory; no migration
or deletion is performed. Python 3.11+ and native provider/connection tools remain
prerequisites. Remote tool bootstrap currently targets Linux x86_64 Box images.

## Remaining extraction

The repository file currently declares project bindings, not complete workspace
requirements. Box preparation uses the bundled compatibility controller.
The controller accepts an explicit session-preparation flag: normal SSH
and prepare-only use tooling and repository setup without Herdr. Agent login
checks the owned running machine, restored filesystem and selected client, then
runs native sign-in without project/tool/account preparation.
Herdr transports, including auto from a Herdr pane, install its tooling/hooks,
register the machine, and prepare a workspace. The binary and controller now
upgrade together; there is no separate controller-code installation step.

The bundled preparation runtime reports explicit phases to a scoped progress
display. TTY output animates one current row, with completed rows and a final
checkout/account summary; redirected output and `TERM=dumb` use plain lines.
`NO_COLOR` disables color. The display stops and joins its redraw worker before
native terminal handoff, and on exceptions/cancellation. It does not estimate
percentages, poll providers itself, or change lifecycle decisions. Native MCP
sync keeps its standalone output; opening summarizes that result instead of
printing its JSON protocol. Saved credentials are not labeled as live sign-ins.

Private account bindings can select Box's GitHub integration or an explicit existing
GitHub CLI account. The latter uses the native local account store, validates the
account and repository, stages the credential in private remote RAM, and supplies
native `GH_TOKEN` through a project-owned gh dispatcher. It does not copy the
laptop's entire configuration directory, switch its active account, or narrow the
existing token's permissions. This adapter is bundled, but its private account
bindings are not part of the shared `.allset` manifest.

SSH, PTY, and workspace handoffs validate the saved checkout's project, machine,
role, and absolute directory. Auth and declared MCP preparation remain separate
from terminal attachment. No running session is migrated and no takeover flag is added. Foreground
process persistence is not promised by ordinary SSH; stopping the VM ends its
processes regardless of connection interface.

The workspace adapter creates or reuses one uniquely labeled remote workspace
without focusing it or assuming a single pane. It reconciles creation failures
against live state before considering another mutation. It then checks the
caller's native machine catalog for the exact SSH alias and remote session,
adds or enables that profile if needed, and prints the sidebar location. Native
machine setup has no approval input, so it cannot approve replacing a server.
Duplicate labels or target profiles fail rather than selecting one arbitrarily.
`HERDR_CONFIG_PATH` selects the caller's catalog; outside Herdr without an
override, the existing controller's dedicated catalog remains the fallback.
The CLI exits without nesting another client, sending pane input, or starting
an agent. Herdr 0.9.0 does not expose automatic machine selection for an existing
client. Because the command returns, its attached credential-cache monitor does
not continue running; native sign-in and the bundled controller remain the
account owners. Remote refresh durability across VM stop remains a limitation.

A new manifest can bootstrap a coding-only private profile without an existing
snapshot or app profile. The developer explicitly selects client identities and
Box billing scope. A unique journaled environment is configured with native
credential injection disabled before a small, bounded-lifetime machine is created.
Unknown provider outcomes reconcile the recorded environment before retry.

Repository-relative skills are copied with supporting files into selected native
client scopes under a digest journal. MCP declarations retain their native managed
file journal. Selected session variables are fetched from the private Infisical
binding at client launch and placed only in the future client process environment;
broker credentials are removed before exec. AllSet-owned client entry points
preserve cwd, argv, TTY, signals, exit status, and native resume semantics by
replacing the process with the resolved native binary. Existing conversations are
not restarted. Coding-only preparation does not run application install, service,
preview, or database commands.

Existing provider allowance, creation lock, timeout reconciliation, filesystem
restoration, project ownership, and active-work preservation checks remain in the
adapter. These must survive extraction into native provider methods. Only the
Box info method has moved so far. Connect never resumes a stopped machine.

## Verification

Local tests cover discovery/root boundaries, init without credentials, cancellation,
noninteractive/dry-run guarantees, credential-bearing origins, malformed/foreign
manifests, old-format migration, unsupported strategies, and current-terminal
routing. Runtime tests execute the actual embedded Python source against synthetic
state and failure responses, including provider-environment reconciliation, skill
conflicts, and scoped launch-environment selection. The optional packaged-container
check runs a release archive offline, without the repository or host home, using
simulated Box, SSH and Herdr boundaries. It exercises actual repository checks,
synthetic credential restore, native MCP projection, and workspace reuse. Neither
test proves cloud provisioning, real sign-ins, tool installation, filesystem
restoration, or a model/tool response. See PROGRESS.md for current evidence.

## Individual agent sign-in

`allset config claude|codex|cursor [PROJECT]` resolves the current repository or
explicit project and dispatches the same login operation as `allset login
PROJECT CLIENT`. Config review, display and validation keep their existing
semantics. Only these explicit client commands enter interactive sign-in.

The Box strategy requires a valid saved owner; runtime rechecks ownership and
live state before SSH and filesystem readiness. Login cannot create/resume a
machine or apply unrelated accounts/services. It holds the project operation
lock through native auth, with the progress display released before the client
owns stdin. The native result and expected account determine whether the selected
credential is cached. A pending/rejected login remains marked `needs_login`;
automatic credential collection skips it until verified explicit sign-in.
Attached monitors also skip capture while another project operation holds the
lock. No shared source credential or other client's cache is rewritten by login.
