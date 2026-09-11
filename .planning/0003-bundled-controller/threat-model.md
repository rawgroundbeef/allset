# Bundled-code boundary

Scope: move executable controller source into the distributed Go artifact while
preserving private account/state and the existing provider lifecycle.

| Failure or abuse scenario | Impact and priority | Control and evidence | Disposition |
| --- | --- | --- | --- |
| Packaging accidentally includes a developer's profiles, credentials or operational notes. | High disclosure impact; likely with a broad directory copy. P1. | Explicit `go:embed` source allowlist; archive inventory test; public synthetic fixtures; source scan. | Mitigated. Review additions to the allowlist as public source. |
| A stale private controller or repository-local Python module replaces bundled code. | High: code executes with access to project credentials/provider authority. P1. | `-I -S`, an explicit revision cache import path, Go-supplied native/state paths, and poisoning tests for caller/private modules and inherited internal variables. | Prevented for the tested import paths. Python and native executables remain trusted host prerequisites. |
| Concurrent extraction or a modified/symlink cache executes partial/substituted code. | High code integrity impact; accidental partial writes are plausible. P1. | Private cache, flock, temporary directory and atomic rename; exact file inventory/bytes/mode/owner checks before import. Tampering and symlink regression tests. | Mitigated. Not a defense against an attacker already controlling this user; no sandbox claim. |
| Bundling accidentally copies a personal project default, or loses identity checks and reads another account. | High credential/compute impact. P1. | Remove project-specific fallback setup/environment/repo; preserve explicit private bindings. Tests refuse missing environment, foreign project auth, changed repo and missing profile. | Prevented for covered entry points. Existing private profile creation remains a separate incomplete workflow. |
| Packaging tests accidentally use real accounts or provision paid compute. | High private-data impact and unwanted spend. P1. | Test build context contains only archive plus three harness files. Runtime has no network, host mounts or socket; synthetic tools reject provider mutations. Resource limits and cleanup target only the harness's unique container/image. | Prevented for container runtime; image build uses network only for Ubuntu packages. |
| Code extraction alters reconnect, timeout reconciliation, or active-work preservation. | High work-loss/duplicate-VM impact. P1. | Keep existing controller behavior; run existing transport tests and bundled lifecycle/auth faults. Container asserts same workspace, unchanged branch/uncommitted file, and only Box info calls. | Mitigated; full real provisioning, stop/resume and browser authentication are not proven by mocks. |

Controller source still uses native remote tooling/bootstrap and legacy private
profile formats. This packaging change does not grant new authentication,
publication, provisioning or stop authority. Release signing and upstream tool
trust are not expanded here; no package release is part of this test.
