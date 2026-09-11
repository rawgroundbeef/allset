# Individual agent sign-in acceptance

Status: local/mock checks executed, 2026-09-11. Native browser authentication
on a real Box remains unverified. Worktree `fix/project-agent-login` starts from
main `39802a0`, which already contains the setup review and startup display.

## Prerequisites and workflow

Use Go, Python 3.11+ and the packaged offline Docker harness documented in
[setup acceptance](uat.md). Fixtures contain a registered project, its owned
running VM record, selected account metadata, and synthetic client credentials.
No real service or account is called.

1. In the local project directory run `allset config claude`. Observe a short
   connection/client check, then native sign-in with the expected account shown.
   Complete sign-in, verify the reported identity and return to the local prompt.
2. Verify only Claude's project cache changes. The manifest, registry, shared
   account sources, other client caches, remote MCP auth, branch and working files
   remain unchanged. No bootstrap, Herdr, create/resume or service setup occurs.
3. Use `allset config codex` and `allset config cursor`; CLI tests prove the
   same project selection and native-client dispatch. Outside a repo, an explicit
   project/alias works: `allset config claude dashboard`.
4. `--dry-run --json` emits a plan without connecting or writing state.
   Invalid origin/binding, missing machine and noninteractive execution fail.
5. Stopped/mismatched/restoring machines or a missing client cannot reach sign-in.
   The command directs the user to open the project when preparation is needed.
6. Native failure, cancellation, unverified/wrong identity, missing credential
   material or an extra unselected client in the response cannot replace the
   previous selected cache. That cache stays marked for explicit retry.
   Background collection skips pending/rejected logins and locked projects.

## Evidence and limits

Go regression tests exercise routing for all three clients and actual bundled
runtime ownership/auth/cache logic with fake subprocess boundaries. The Linux
arm64 packaged command passes a simulated Claude login/status followed by the
actual selected-credential transfer and cache write. The fixture project name
`dashboard` also proves native Box verbs cannot override the resolved project.

The native CLI itself controls browser prompts and its remote login file. A
wrong account can change that native file even though AllSet rejects caching it;
repeat sign-in with the intended account. Existing agent processes are not
restarted. Actual browser flow, account service access, Codex callback forwarding
and Cursor sign-in are unverified by these local/mock checks.

Pass: one local command signs in the selected client for the intended running
project, verifies it before saving and leaves other project/client state alone.
