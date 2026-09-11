# Agent sign-in boundary — 2026-09-11

The developer explicitly requests one client's authentication for a project.
CLI input and Git origin/manifest resolve the project; the strategy validates
its private binding and machine pointer. Runtime rechecks the owned machine and
live provider identity, authenticated SSH, restored filesystem and installed
client before allowing native authentication. Account choices remain private.

| Failure scenario | Control and evidence | Status |
| --- | --- | --- |
| A shared manifest or ambient UI selects another project's Box/account | Existing origin/binding checks, saved-pointer validation, runtime owner/provider-ID check; CLI and runtime foreign-target tests | Prevented in tested paths |
| A project named like a Box verb invokes that native command | Explicit project argument from Go; packaged `dashboard` login regression | Prevented |
| Repairing Claude starts compute or restores unrelated accounts | Running-machine-only login path bypasses preparation; container permits only provider info and checks other caches/files | Prevented in tested paths |
| Browser sign-in yields a wrong account, invalid result, missing credentials or another client's payload | Native identity must match the expected account when configured; selected usable credential set validated before cache replacement; fault tests | Prevented from replacing the selected cache |
| Background collection copies incomplete/rejected native credentials | Project lock during auth, nonblocking monitor capture, and durable needs-login marker skipped until verified explicit sign-in; lock/failure tests | Mitigated |
| A failed attempt erases previous credential material or changes a shared source | Preserve previous contents while marking retry; validate the entire authenticated response before writing; cache/source isolation tests | Prevented in tested paths |

The native client can change its own remote credential file during browser auth;
AllSet does not claim rollback of that file or restart existing agents. A rejected
account requires repeating the same explicit sign-in command. Native provider
browser behavior and account access remain unverified here. No real sign-in,
service credential, VM lifecycle mutation or abuse probe was used for testing.

Local review found and addressed the command-name collision and background
capture window. Review was not independent. No additional publication or account
permission follows from this model; the user's implementation/main-push scope
controls delivery.
