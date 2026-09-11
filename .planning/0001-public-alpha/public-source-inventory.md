# Public source preparation

The public repository starts from a selected source snapshot. Private prototype
history, naming research, account/project examples, and machine-specific progress
are excluded. They remain in the original local repository.

The payload includes Go sources, bounded Python adapters, synthetic tests,
repository-owned skills, schemas, MIT license, and contributor documentation.
The Go module uses only the standard library. Embedded Python uses its standard
library. The Trigger preset runs the upstream pinned npm CLI; its code is not
vendored into this source snapshot. The initial snapshot excluded the prototype
controller. The subsequent [bundling fix](../0003-bundled-controller/decisions.md)
adds an explicit source allowlist, without private profiles, credentials, or
prototype history.

Before first push, inspect the exact snapshot, check for secret/private data,
run race tests/vet/build, and smoke-test the native release archives. These checks
address the public payload and packaging, not remote app readiness. Record actual
results in [PROGRESS.md](../../PROGRESS.md).
