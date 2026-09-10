# Project MCPs

Declare MCPs once in `.allset`. AllSet applies native settings for Codex,
Claude Code, and Cursor on that project's VM whenever you open or connect. The
terminal you use does not affect configuration.

A project with Trigger.dev:

```json
{
  "version": 1,
  "name": "dashboard",
  "repository": "acme/dashboard",
  "backend": "box",
  "mcps": {
    "trigger": {
      "preset": "trigger",
      "project_ref": "proj_YOUR_PROJECT"
    }
  }
}
```

Inside the local repository:

```sh
allset mcp list
allset mcp sync
allset mcp login trigger
allset
```

From another directory, append the project: `allset mcp sync dashboard` or
`allset mcp login trigger dashboard`. List reads declarations only; it is not a
server health check. Sync and login require the existing Box to be running and
fully restored. Neither resumes a VM or changes its auto-stop deadline. Use
`--dry-run` on sync/login to inspect dispatch without connecting.

A project without .allset can declare the same `mcps` object on its entry
in the local shortcut registry. A manifest, when present, is authoritative; it
is not merged with registry MCPs. `allset init` carries existing declarations
into the new file. Update the manifest when working through folder discovery,
and the registry when using a named shortcut from another directory.

## Trigger.dev

The preset uses the official CLI, pinned to `trigger.dev@4.4.6`, with the declared
project reference. It uses a project-named native login in an isolated
`XDG_CONFIG_HOME` under `~/.local/share/allset/mcp/PROJECT/SERVER/config` on the
VM (Python 3.11+ is required for native config projection). It clears inherited `TRIGGER_ACCESS_TOKEN` and `TRIGGER_API_URL` so they cannot
override that login. The first connection downloads the package through npx;
subsequent connections use its cache. Node/npm must already be installed.

Sign-in uses Trigger's native `login --profile PROJECT --no-browser` flow. Open
the URL in the browser profile for the intended account. The resulting personal
access token stays in that VM's private native config. An application
`TRIGGER_SECRET_KEY` is not a substitute for this CLI login. Revoked/expired auth
requires repeating `allset mcp login trigger`; AllSet never switches to a
personal or unrelated login automatically.

`read_only` defaults to true. The native `--readonly` flag hides deploy, trigger,
and cancel operations. Trigger 4.4.6 still exposes local dev-server start/stop
and profile-management tools. This is not a blanket no-write guarantee. Likewise,
`project_ref` selects the default project; it does not reduce the account's
server-side permissions or prohibit explicit project overrides. Choose the
appropriate account and agent approvals. Set `"read_only": false` only when the
project needs the additional task/deployment tools.

## Other servers

Add any supported stdio or HTTPS MCP by its official configuration. Pin package
versions where possible; server commands execute code on the VM.

```json
{
  "mcps": {
    "docs": {
      "url": "https://developers.openai.com/mcp"
    },
    "internal-api": {
      "url": "https://mcp.example.com/mcp",
      "bearer_token_env_var": "PROJECT_MCP_TOKEN",
      "agents": ["codex", "claude", "cursor"]
    },
    "internal-tools": {
      "command": "/opt/project-tools/mcp-server",
      "args": ["--stdio"],
      "env_vars": ["PROJECT_TOOLS_TOKEN"]
    }
  }
}
```

The internal examples are placeholders, not installed services. `agents` is
optional and defaults to all three. Environment references name variables in the
**remote agent's environment**. AllSet does not copy laptop environment values,
fetch arbitrary Infisical paths, or supply a token just because it is named.
Start that agent with the project's existing secret-injection setup when needed.
For HTTP OAuth servers, use the chosen agent's native MCP login on the VM; it
owns its OAuth storage and refresh behavior. AllSet's dedicated MCP login
command currently handles the Trigger preset only.

Do not place secrets in URLs, args, or config. There is no inline `env` or token
field. Unknown fields and ambiguous transports fail validation. URL credential
syntax and obvious credential query parameters are rejected; that does not make
arbitrary command arguments safe to publish.

## Native client settings and lifecycle

Generated settings live in the VM user's `~/.codex/config.toml`,
`~/.claude.json`, and `~/.cursor/mcp.json`, so project worktrees share the same MCP
setup and project account. Agents using custom config-home overrides need their
own adapter; this version targets the standard native locations.

AllSet preserves unrelated settings and MCPs. It rejects conflicting unmanaged
server names or edits to its managed entries. Writes are private and atomic per
file; a private declaration journal allows an interrupted multi-client update to
finish on retry. It refuses to assign the same remote home to another project.

Omit `mcps` to leave MCPs unmanaged. Use `"mcps": {}` and sync to remove AllSet's
entries. Removing declarations does not revoke credentials or stop existing MCP
processes; native login files remain available for reuse.

Codex declarations use native `required = true` and a 60-second startup timeout,
so startup/resume waits for configured integrations or reports a failure. An
unavailable declared MCP can therefore prevent Codex startup; fix the integration
or remove its declaration and sync. Claude/Cursor retain their native readiness
and approval behavior; they do not receive Codex-specific fields.

Check the client's `/mcp` status instead of asking the model to list tools: a
turn submitted while an optional server is starting can omit that server, even
if it connects moments later.

Sync never restarts agents or Herdr. Start a new agent session, or use the
client's native MCP reload where available. In Codex, `/mcp` shows connected
servers; `codex mcp get trigger --json` inspects the saved registration. Claude
also exposes `/mcp`; Cursor uses `cursor-agent mcp list`. Cursor may require
`cursor-agent mcp enable trigger` from each remote workspace before loading it.
That approval is client/workspace-specific, separate from server authentication.
An already-running conversation may retain the old tool list until restarted or
resumed through the client. Config installation does not imply an agent login.

Stopping a Box stops MCP processes too. Files, native auth, and npx caches persist;
opening the project reapplies declarations, and the next agent starts its MCPs.
Shared machine templates must contain reusable tools only. Never template or fork
a signed-in project's home into another project; this increment does not create
templates or implement template credential scrubbing.

References: [Trigger MCP](https://trigger.dev/docs/mcp-introduction),
[Trigger tools](https://trigger.dev/docs/mcp-tools),
[Codex MCP](https://learn.chatgpt.com/docs/extend/mcp),
[Claude MCP](https://code.claude.com/docs/en/mcp),
[Cursor MCP](https://cursor.com/docs/mcp).
