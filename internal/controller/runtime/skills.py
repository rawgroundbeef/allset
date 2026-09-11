"""Project-owned skill projection for supported native coding clients."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

CLIENT_ROOTS = {'codex': '.agents/skills', 'claude': '.claude/skills', 'cursor': '.cursor/skills'}


def digest(directory):
    total = 0
    value = hashlib.sha256()
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('Skill sources cannot contain symlinks')
        if not path.is_file():
            continue
        relative = path.relative_to(directory).as_posix()
        data = path.read_bytes()
        total += len(data)
        if total > 8 * 1024 * 1024:
            raise ValueError('Skill source exceeds the 8 MiB limit')
        value.update(relative.encode() + b'\0' + data)
    return value.hexdigest()


def apply(home, project, checkout, declarations, personal_sources=None, selected_clients=None):
    root = home / '.local/share/allset/skills' / project
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / 'apply.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state_path = root / 'managed.json'
        state = json.loads(state_path.read_text()) if state_path.exists() else {'entries': {}}
        previous = state.get('entries', {})
        wanted = {}
        combined = dict(declarations)
        for name, source in (personal_sources or {}).items():
            if name in combined: raise ValueError('Repository and personal skills collide: ' + name)
            combined[name] = {'path': source, 'agents': [], 'personal': True}
        for name, declaration in sorted(combined.items()):
            candidate = Path(declaration['path']) if declaration.get('personal') else checkout / declaration['path']
            if candidate.is_symlink():
                raise ValueError('Skill source cannot be a symlink: ' + name)
            if not declaration.get('personal'):
                relative = Path(declaration['path'])
                current = checkout
                for part in relative.parts:
                    current = current / part
                    if current.is_symlink():
                        raise ValueError('Skill source path cannot contain symlinks: ' + name)
            source = candidate.resolve()
            if not declaration.get('personal'):
                try:
                    source.relative_to(checkout.resolve())
                except ValueError:
                    raise ValueError('Skill source escapes the project checkout: ' + name) from None
            if not source.is_dir() or not (source / 'SKILL.md').is_file():
                raise ValueError('Skill source requires a directory containing SKILL.md: ' + name)
            source_digest = digest(source)
            targets = declaration.get('agents') or selected_clients or CLIENT_ROOTS
            if selected_clients is not None:
                targets = [client for client in targets if client in selected_clients]
            for client in targets:
                target = home / CLIENT_ROOTS[client] / name
                key = client + '/' + name
                old = previous.get(key)
                if target.exists() and (old is None or digest(target) != old['digest']):
                    raise ValueError('Native skill target has unmanaged edits: ' + key)
                source_label = 'personal:' + name if declaration.get('personal') else declaration['path']
                wanted[key] = {'source': source_label, 'digest': source_digest}
                if target.exists() and old == wanted[key] and digest(target) == source_digest:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                temporary = Path(tempfile.mkdtemp(prefix='.allset-', dir=target.parent))
                shutil.rmtree(temporary)
                shutil.copytree(source, temporary)
                if target.exists(): shutil.rmtree(target)
                temporary.replace(target)
        for key, old in previous.items():
            if key in wanted: continue
            client, name = key.split('/', 1)
            target = home / CLIENT_ROOTS[client] / name
            if target.exists() and digest(target) != old['digest']:
                raise ValueError('Removed skill has unmanaged edits: ' + key)
            if target.exists(): shutil.rmtree(target)
        desired_state = {'project': project, 'entries': wanted}
        if state != desired_state:
            temporary = state_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(desired_state, indent=2) + '\n')
            temporary.chmod(0o600); temporary.replace(state_path)
    return {'project': project, 'skills': sorted(declarations), 'targets': sorted(wanted)}


def main(request):
    os.umask(0o077)
    result = apply(Path.home(), request['project'], Path(request['checkout']), request.get('skills') or {},
                   request.get('personal_sources') or {}, request.get('clients'))
    print(json.dumps(result))
