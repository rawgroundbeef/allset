# Contributing

This is an early alpha. Try it, report issues, and help make the existing paths
reliable. Fresh-laptop provisioning is still incomplete; read the README before
connecting a real environment.

Open an issue with the expected behavior, actual result, CLI version, operating
system, provider, and a minimal redacted config. Remove credentials, private
repository names, account identifiers, and sensitive terminal output. Report
security issues privately using [SECURITY.md](SECURITY.md).

For a change, create a branch in a fresh Git worktree, read [AGENTS.md](AGENTS.md),
and keep the diff focused. Use the repository's `.agents/skills/` when working
with an agent. Ordinary fixes do not require a planning ceremony.

## Local checks

Install Go 1.25+ and Python 3.11+. Tests use synthetic data and subprocess stubs;
cloud accounts and VMs are not required.

```sh
gofmt -w cmd internal
go test -race ./...
go vet ./...
go build -o bin/allset ./cmd/allset
```

Include the behavior fixed, relevant verification, and any remaining limits in
the PR. Add tests for changed identity, auth, lifecycle, and recovery behavior.
Do not add tests that merely restate a rename or formatting change. Preserve
read-only commands and avoid tests that spend allowance or touch real services.

## Packaged container check

With Docker running, build the release archives and select the Linux archive
matching your Docker engine's architecture (`arm64` on Apple Silicon, usually
`amd64` on Linux CI):

```sh
python3 scripts/build-release.py /tmp/allset-release-check
python3 scripts/test-container.py /tmp/allset-release-check/allset_0.5.0-alpha.1_linux_arm64.tar.gz
```

The release output directory must not already exist. The harness builds a
disposable image with only the archive, test scripts, Python and Git. Image
building needs network access for Ubuntu packages; the test container runs
without networking, host mounts, credentials, capabilities or a Docker socket.
It removes its own container and image afterward, leaving shared Docker caches.

Box, SSH, filesystem hydration, system bootstrap and Herdr are simulated.
Repository validation, synthetic credential restore, native MCP file writes,
and workspace orchestration execute the packaged code. An interactive bare
invocation also creates a missing `.allset` from saved settings and reopens
without repeating setup. This verifies the
packaging boundary and preservation of existing work, not real cloud/auth
readiness. The Go suite separately covers cache tampering and lifecycle faults.

Contributions are under the repository's MIT license. No CLA is required.
