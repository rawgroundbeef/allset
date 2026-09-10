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

Contributions are under the repository's MIT license. No CLA is required.
