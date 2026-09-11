#!/usr/bin/env python3
"""Run setup and collect results inside one owned Box task workspace."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile


def run(args, cwd=None, **kwargs):
    """Run a checked argv command without interpreting arguments as shell code."""
    return subprocess.run(args, cwd=cwd, check=True, **kwargs)


def save(path, data):
    """Atomically replace a non-secret task status record."""
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def prepare(meta, state):
    """Prepare pinned tools, then run only explicitly declared compatibility setup."""
    status = {'state': 'preparing', 'base_sha': meta['base_sha'],
              'setup_token': meta['setup_token']}
    save(state / 'setup.json', status)
    try:
        with (state / 'setup.log').open('w') as log:
            actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                            cwd=meta['cwd'], text=True).strip()
            if actual != meta['base_sha']:
                raise ValueError('Task checkout does not match the requested source')
            bootstrap = ['bash', str(state / 'bootstrap.sh')]
            if meta.get('session_interface', 'herdr') != 'ssh': bootstrap.append('--with-herdr')
            run(bootstrap, stdout=log, stderr=subprocess.STDOUT)
            if meta.get('project_profile'):
                if not meta['project_profile'].get('coding_only'):
                    for script in meta['project_profile']['setup_commands']:
                        run(['bash', '-lc', script], cwd=meta['cwd'], stdout=log, stderr=subprocess.STDOUT)
            else:
                run(['bash', str(state / 'prepare.sh'), meta['cwd']],
                    stdout=log, stderr=subprocess.STDOUT)
        lockfile = next((Path(meta['cwd']) / name for name in ('pnpm-lock.yaml', 'bun.lock', 'package-lock.json')
                         if (Path(meta['cwd']) / name).exists()), None)
        status.update(state='ready', lock_sha256=hashlib.sha256(lockfile.read_bytes()).hexdigest() if lockfile else None)
    except Exception as error:
        status.update(state='failed', error=type(error).__name__)
        raise
    finally:
        save(state / 'setup.json', status)


def collect(meta, state):
    """Save commits, tracked changes and untracked files without changing the index."""
    cwd = Path(meta['cwd'])
    out = state / 'results'
    out.mkdir(exist_ok=True)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd, text=True).strip()
    with (out / 'changes.patch').open('wb') as target:
        run(['git', 'diff', '--binary', meta['base_sha']], cwd=cwd, stdout=target)
    with (out / 'working-tree.patch').open('wb') as target:
        run(['git', 'diff', '--binary', 'HEAD'], cwd=cwd, stdout=target)
    names = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=cwd)
    untracked = [os.fsdecode(name) for name in names.split(b'\0') if name]
    with tarfile.open(out / 'untracked.tar.gz', 'w:gz') as archive:
        for name in untracked:
            path = Path(name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe untracked path')
            archive.add(cwd / path, arcname=name, recursive=False)
    bundle = out / 'commits.bundle'
    if head != meta['base_sha']:
        run(['git', 'bundle', 'create', str(bundle), 'HEAD', '^' + meta['base_sha']], cwd=cwd)
    elif bundle.exists():
        bundle.unlink()
    save(out / 'manifest.json', {**meta, 'head_sha': head, 'untracked': untracked,
         'has_commits': head != meta['base_sha']})
    with tarfile.open(state / 'results.tar.gz', 'w:gz') as archive:
        for path in sorted(out.iterdir()):
            archive.add(path, arcname=path.name, recursive=False)
    print(json.dumps({'head_sha': head, 'archive': str(state / 'results.tar.gz')}))


def main():
    """Dispatch only a task whose metadata lives in the dedicated state directory."""
    action, location = sys.argv[1:]
    state = Path(location).resolve()
    if state.parent != Path.home() / '.box-herdr/tasks':
        raise ValueError('Unexpected task state location')
    meta = json.loads((state / 'task.json').read_text())
    {'prepare': prepare, 'collect': collect}[action](meta, state)


if __name__ == '__main__':
    main()
