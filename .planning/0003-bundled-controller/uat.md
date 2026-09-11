# Packaged controller acceptance

Scope: prove that a built/released executable can execute existing-profile
workflows without the developer's separately installed controller code.
Status: local/mock acceptance passed, 2026-09-10. Real existing-project handoff
also passed; new-project provisioning and real authentication remain separate.

## Local/mock prerequisites

- Go 1.25+, Python 3.11+, Docker; `fix/bundled-controller` based on `90ce7c6`.
- Build archives with `python3 scripts/build-release.py NEW_OUTPUT_DIRECTORY`.
- Run `python3 scripts/test-container.py PATH_TO_LINUX_ARCHIVE` for the Docker
  engine architecture. No Box, Herdr or agent accounts on the host are used.
- Container image has Python/Git and the packaged executable, with synthetic
  project/machine/shell/account data. It has no checkout, host-home mounts,
  Docker socket, network or extra capabilities. Tool installation and provider
  readiness are simulated; Git and native configuration writes execute for real.

## Observable checks

1. Help/version, config validation, cached status and dry-run succeed without
   creating a controller cache or calling a provider.
2. `allset open dashboard --attach none` prepares the saved project without the
   private controller folder, restores only the synthetic bound Codex login,
   preserves unmanaged Codex configuration and applies the declared MCP URL.
3. Poison the old private controller path. `allset connect dashboard --attach
   workspace` still succeeds using the bundled code. Repeat it and verify one
   machine registration/workspace creation, zero MCP file changes, and preserved
   branch/uncommitted work. No Box creation/resume/stop is allowed by the fixture.
4. `allset collect dashboard` uses the shipped worker to save tracked changes
   and untracked files; the checkout and Git index remain unchanged.
5. Stopped VM, foreign shell/repository and missing profile fail without Herdr
   takeover, compute mutation or project fallback.
6. Go-driven runtime tests refuse cache modification/symlinks, ignore caller
   modules/internal path overrides, preserve child exit codes, and cover timeout
   reconciliation, restoration readiness, allowance bounds and foreign auth.

Pass criterion: a packaged executable completes the existing-project preparation
and repeatable workspace handoff in an isolated environment with no private
controller code or real credentials.

## Evidence

All six checks above passed: packaged Linux arm64 container and Go race suite.
The built macOS executable also reconnected an existing running project's Herdr
workspace without a VM lifecycle mutation. See [PROGRESS.md](../../PROGRESS.md).
Real cloud provisioning,
tool downloads, Infisical API access, real MCP tools, browser sign-in, filesystem
hydration and interactive agent detection are **unverified by this container**.
