# Releases

Source is public during the alpha. A versioned binary does not imply that the
prototype workspace-controller dependency has been extracted.

## Native binaries

CI checks formatting, race tests (including embedded Python runtime tests), vet,
building, and read-only CLI smoke commands on Linux and macOS. Forked PR jobs
receive no cloud or publishing credentials and create no VMs.

After merging a version change in `internal/cli/cli.go`, a maintainer tags that
main-branch revision, for example `v0.5.0-alpha.1`. Pushing the tag runs the same
checks, verifies tag/version agreement and main ancestry, then builds Go binaries
for macOS/Linux on arm64/amd64. `scripts/build-release.py` packages the binaries,
README, and MIT license with SHA-256 checksums. The release workflow publishes
that checked tag to GitHub; prerelease tags produce prereleases.

```sh
python3 scripts/build-release.py dist/release
```

The destination must not already exist. Cross-compilation proves that all four
targets build; only the host binaries execute in local/CI checks. Windows is not
supported by the current Unix-specific adapter.

A failed upload must not overwrite released bytes. The job keeps its build output
as an Actions artifact. If a release already exists, creation fails: inspect its
assets and checksums before completing missing uploads. Never move a published
tag or use `--clobber`. Fix a bad release with a new version and clearly mark the
broken release. Do not silently substitute a rebuilt binary.

## npm publishing plan — not implemented yet

The exact package is `allset`; the Go binary remains the implementation. The next
distribution increment will package native binaries with a small platform-selecting
launcher, use an explicit package file allowlist, and smoke-test an actual packed
installation from a temporary directory with no cloud credentials.

The package is not owned or published yet. Bootstrap it through the maintainer's
supported npm sign-in, then configure a trusted publisher for `rawgroundbeef/allset`
and the dedicated npm publishing workflow. Use GitHub-hosted runners, Node
22.14.0+ and npm 11.5.1+, with OIDC and provenance instead of a long-lived token.
Choose direct publishing for ordinary tag-driven releases when configuring that
publisher; staging is also supported by npm. Package setup and a real publish
must be verified before adding an npm install command to the README.
[Official npm trusted publishing](https://docs.npmjs.com/trusted-publishers/).

The future npm job must consume the checked revision, publish alpha versions to
an `alpha` dist-tag, and reconcile partial publication by checking the existing
version and integrity. Package and GitHub publication are separate outcomes.
Publishing one does not establish that the other succeeded.

## CI authority

Actions are pinned to full commit SHAs and checked for updates by Dependabot.
Read-only permissions are the default; only the tag publication job gets release
write access. No `pull_request_target` job executes contributor code.
[GitHub secure workflow guidance](https://docs.github.com/en/actions/reference/security/secure-use).
