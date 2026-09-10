"""Project-owned MCP projection into native clients; never restarts an agent."""
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib

CLIENTS = ('codex', 'claude', 'cursor')
BEGIN = '# BEGIN ALLSET MCPS\n'
END = '# END ALLSET MCPS\n'
TRIGGER_VERSION = '4.4.6'


def private_write(path, content):
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise ValueError('Refusing a symlink in native config path: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError('Refusing to replace a symlink: ' + str(path))
    fd, tmp = tempfile.mkstemp(prefix='.allset-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def trigger_command(home, project, server, m, login=False):
    # An inherited token must not override this project's named native login.
    root = home / '.local/share/allset/mcp' / project / server / 'config'
    args = ['-u', 'TRIGGER_ACCESS_TOKEN', '-u', 'TRIGGER_API_URL',
            'XDG_CONFIG_HOME=' + str(root), 'npx', '--yes',
            'trigger.dev@' + TRIGGER_VERSION, 'login' if login else 'mcp',
            '--profile', project, '--skip-telemetry']
    if login:
        args.append('--no-browser')
    else:
        args += ['--project-ref', m['project_ref']]
        if m.get('read_only', True):
            args.append('--readonly')
    return '/usr/bin/env', args


def render(home, project, servers):
    entries = {client: {} for client in CLIENTS}
    for name, m in sorted(servers.items()):
        for client in m.get('agents') or CLIENTS:
            if m.get('preset') == 'trigger':
                command, args = trigger_command(home, project, name, m)
                entry = {'command': command, 'args': args}
            elif m.get('command'):
                entry = {'command': m['command'], 'args': m.get('args', [])}
                if m.get('env_vars'):
                    if client == 'codex':
                        entry['env_vars'] = m['env_vars']
                    else:
                        prefix = 'env:' if client == 'cursor' else ''
                        entry['env'] = {key: '${' + prefix + key + '}' for key in m['env_vars']}
            else:
                entry = {'url': m['url']}
                key = m.get('bearer_token_env_var')
                if key:
                    if client == 'codex':
                        entry['bearer_token_env_var'] = key
                    else:
                        prefix = 'env:' if client == 'cursor' else ''
                        entry['headers'] = {'Authorization': 'Bearer ${' + prefix + key + '}'}
                if client == 'claude':
                    entry['type'] = 'http'
            if client == 'codex':
                # A project-declared integration must be present in the first turn.
                # Optional MCP startup lets Codex silently omit still-loading tools.
                entry['required'] = True
                entry['startup_timeout_sec'] = 60
            entries[client][name] = entry
    return entries


def split_toml(text):
    if BEGIN not in text and END not in text:
        return text, ''
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('Invalid AllSet MCP markers in Codex config')
    before, rest = text.split(BEGIN)
    block, after = rest.split(END)
    return before + after, BEGIN + block + END


def toml_block(entries):
    if not entries:
        return ''
    lines = [BEGIN.rstrip()]
    for name, entry in sorted(entries.items()):
        lines.append('[mcp_servers.' + json.dumps(name) + ']')
        for key, value in entry.items():
            lines.append(key + ' = ' + json.dumps(value))
        lines.append('')
    return '\n'.join(lines) + END


def read_text(path):
    if path.is_symlink():
        raise ValueError('Native config cannot be a symlink: ' + str(path))
    return path.read_text() if path.exists() else ''


def apply(home, project, repository, servers):
    root = home / '.local/share/allset/mcp'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / 'apply.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state_path = root / 'managed.json'
        state = json.loads(read_text(state_path) or '{}')
        identity = {'project': project, 'repository': repository}
        if state and state.get('identity') != identity:
            raise ValueError('This home already belongs to another project; refusing shared MCP credentials')
        wanted = render(home, project, servers)
        previous = state.get('entries', {c: {} for c in CLIENTS})
        pending = state.get('pending', previous)
        paths = {'codex': home / '.codex/config.toml',
                 'claude': home / '.claude.json', 'cursor': home / '.cursor/mcp.json'}
        writes = []
        for client, path in paths.items():
            original = read_text(path)
            owned = set(previous[client]) | set(pending[client])
            if client == 'codex':
                base, block = split_toml(original)
                acceptable = {toml_block(previous[client]), toml_block(pending[client])}
                if block not in acceptable:
                    raise ValueError('Codex managed MCP settings changed; reconcile before syncing')
                parsed = tomllib.loads(base)
                if set(parsed.get('mcp_servers', {})) & set(wanted[client]):
                    raise ValueError('Codex already has an unmanaged MCP with this name')
                updated = base.rstrip() + ('\n\n' if base.strip() else '') + toml_block(wanted[client])
                tomllib.loads(updated)
            else:
                document = json.loads(original or '{}')
                current = document.get('mcpServers', {})
                for name in owned | set(wanted[client]):
                    value = current.get(name)
                    if name not in owned:
                        if name in current:
                            raise ValueError(client + ' already has an unmanaged MCP named ' + name)
                    elif value not in (previous[client].get(name), pending[client].get(name)):
                        raise ValueError(client + ' managed MCP changed: ' + name)
                remaining = {k: v for k, v in current.items() if k not in owned}
                desired = {**remaining, **wanted[client]}
                if current == desired:
                    updated = original
                else:
                    document['mcpServers'] = desired
                    updated = json.dumps(document, indent=2) + '\n'
            if original != updated:
                writes.append((path, original, updated))
        # Journal contains only owned MCP declarations, never native auth/settings.
        private_write(state_path, json.dumps({'identity': identity, 'entries': previous, 'pending': wanted}))
        for path, original, updated in writes:
            if read_text(path) != original:
                raise ValueError('Native settings changed during sync; rerun after that edit finishes')
            private_write(path, updated)
        private_write(state_path, json.dumps({'identity': identity, 'entries': wanted}))
        for name, m in servers.items():
            if m.get('preset') == 'trigger':
                folder = home / '.local/share/allset/mcp' / project / name / 'config'
                folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        print(json.dumps({'project': project, 'mcps': sorted(servers), 'clients': CLIENTS,
                          'changed_files': len(writes), 'agents_restarted': False}))


def main(request):
    os.umask(0o077)
    home = Path.home()
    project = request['project']
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', project):
        raise ValueError('Invalid project')
    if request['operation'] == 'sync':
        apply(home, project, request['repository'], request['mcps'])
    elif request['operation'] == 'login':
        name = request['server']
        m = request['mcps'][name]
        if m.get('preset') != 'trigger':
            raise ValueError('Use the selected agent native MCP login for this custom server')
        command, args = trigger_command(home, project, name, m, login=True)
        os.execv(command, [command, *args])
    else:
        raise ValueError('Unknown MCP operation')


if __name__ == '__main__':
    try:
        main(json.loads(sys.argv[1]))
    except Exception as error:
        # Native config parsing can include secret text. Never echo exception bodies.
        if isinstance(error, ValueError) and not isinstance(error, (json.JSONDecodeError, tomllib.TOMLDecodeError)):
            print('allset mcp: ' + str(error), file=sys.stderr)
        else:
            print('allset mcp: configuration sync failed (' + type(error).__name__ + '); no agent was restarted', file=sys.stderr)
        sys.exit(1)
