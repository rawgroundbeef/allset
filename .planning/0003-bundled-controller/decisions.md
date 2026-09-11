# Bundle the controller — 2026-09-10

The user approved removing the private controller-code dependency and requested
a container test to verify it independently of the developer's machine.

- Ship the existing standard-library Python runtime in the Go executable now.
  A Go rewrite and new-project configuration are separate work. Keep the current
  Box/Herdr setup, native executables, private state and credential references.
- Embed an explicit 16-file source allowlist. Exclude private profiles, auth-import
  helpers, template-building commands, local terminal wrappers, caches and notes.
  Remove project-specific fallback environment, template, repository and setup
  commands. Missing configuration must not silently select a developer's project.
- Execute the embedded runtime via isolated Python; install a revision-specific
  private cache only when executing a lifecycle operation. Inspect/dry-run remain
  read-only. Validate existing cache contents and refuse unsafe or modified files.
- Pass native CLI locations and private state explicitly from the Go plan.
  No credential/profile values enter the bundle. No state migration or deletion.
- Prove the package in an offline disposable container with synthetic external
  boundaries and actual bundled scripts. This is local/mock evidence, independent
  of host files, and does not establish real cloud or authentication readiness.

See [scoped threats](threat-model.md) and [acceptance checks](uat.md).
