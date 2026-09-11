#!/usr/bin/env python3
"""Start one worktree service with its own Infisical scope and assigned ports."""

import json
import os
from pathlib import Path
import sys

from infisical_context import token_environment


def main():
    """Authenticate without argv secrets, inject the requested scope, then run the app."""
    os.umask(0o077)
    state, service_name = sys.argv[1:]
    meta = json.loads((Path(state) / 'task.json').read_text())
    profile = meta['project_profile']
    native = Path.home() / '.local/bin/infisical-native'
    cli = str(native) if native.exists() else 'infisical'
    auth = profile['infisical']
    service = next(s for s in profile['services'] if s['name'] == service_name)
    if not service['secret_paths']:
        os.chdir(Path(meta['cwd']) / service['cwd'])
        os.execv(sys.executable, [sys.executable, str(Path(__file__).with_name('service-exec.py')), state, service_name])
    env = token_environment(profile, cli)
    # Secrets are scoped exactly as in the profile and are never printed here.
    argv = [cli, 'run', '--domain=' + auth['instance'], '--projectId=' + auth['project_id'],
            '--env=' + auth['environment'], '--silent']
    argv += ['--path=' + path for path in service['secret_paths']]
    if service.get('recursive'):
        argv += ['--recursive']
    # A second stage applies per-worktree routing AFTER Infisical injection.
    argv += ['--', 'python3', str(Path(__file__).with_name('service-exec.py')), state, service_name]
    os.chdir(Path(meta['cwd']) / service['cwd'])
    os.execvpe(argv[0], argv, env)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Project app could not start:', str(error), file=sys.stderr)
        sys.exit(1)
