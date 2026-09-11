#!/usr/bin/env python3
"""Apply non-secret per-worktree routing after Infisical has injected configuration."""

import json
import os
from pathlib import Path
import sys


def main():
    """Remove broker credentials from child processes and expand only explicit routing placeholders."""
    state, name = sys.argv[1:]
    meta = json.loads((Path(state) / 'task.json').read_text())
    service = next(s for s in meta['project_profile']['services'] if s['name'] == name)
    values = {**meta['preview_urls'], 'port': str(meta['service_ports'][name]), 'cwd': meta['cwd'],
              **{'port_' + key: str(value) for key, value in meta['service_ports'].items()}}
    env = {k: v for k, v in os.environ.items() if not k.startswith('INFISICAL_')}
    for key, value in service.get('routing_env', {}).items():
        env[key] = value.format_map(values)
    for key in service.get('remove_env', []):
        env.pop(key, None)
    argv = [value.format_map(values) for value in service['command']]
    os.execvpe(argv[0], argv, env)


if __name__ == '__main__':
    main()
