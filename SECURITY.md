# Security

Report vulnerabilities using
[GitHub private vulnerability reporting](https://github.com/rawgroundbeef/allset/security/advisories/new).
Include a minimal reproduction, affected version, and impact. Do not include
active credentials or personal project data. Please keep exploitable details out
of public issues while a fix is being prepared.

AllSet is experimental. Security fixes target the current alpha; older alpha
versions do not have a separate maintenance commitment.

Project configuration can declare executable MCP commands. Review a repository's
configuration before opening its environment. A shared config is not permission
to use another person's credentials or spend on compute. Remote agents and MCPs
run under the selected VM user's permissions; project labels and worktrees are
not additional security sandboxes.

Keep credentials out of manifests, templates, diagnostics, issue reports, and
source control. See [MCP behavior](docs/mcps.md) for native configuration ownership,
authentication, and the limits of Trigger's read-only mode.
