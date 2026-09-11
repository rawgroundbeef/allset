#!/usr/bin/env python3
"""Synthetic CLI boundaries; invoked only inside the disposable test container.

Box state, SSH transport, system bootstrap and Herdr are simulated. Remote Git,
credential restore and native MCP file projection execute the shipped code.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

home = Path('/home/user')
assert os.getuid() == 10001 and Path('/opt/checks/smoke.py').is_file()
tool = Path(sys.argv[0]).name
args = sys.argv[1:]
log = home / 'calls.jsonl'


def record(operation):
    # Never log script arguments or credential streams, even for synthetic auth.
    with log.open('a') as output:
        output.write(json.dumps({'tool': tool, 'operation': operation}) + '\n')


def emit(value):
    print(json.dumps(value))


if tool == 'claude':
    record(' '.join(args[:2]))
    if args[:2] == ['auth', 'login']:
        assert args == ['auth', 'login', '--claudeai']
        path = home / '.claude/.credentials.json'
        value = json.loads(path.read_text()) if path.exists() else {}
        value['claudeAiOauth'] = {'accessToken': 'synthetic-access', 'refreshToken': 'synthetic-refresh'}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        path.chmod(0o600)
        print('Synthetic native sign-in completed')
    else:
        assert args == ['auth', 'status']
        emit({'loggedIn': True, 'email': 'fixture@example.test', 'orgId': 'fixture-org'})
elif tool == 'box':
    args = [a for a in args if a not in ('--json', '--no-update')]
    record(args[0])
    assert args == ['info', 'bx_saved'], 'Unexpected provider operation'
    emit({'box': {'id': 'bx_saved', 'state': (home / 'box-state').read_text(),
                  'ip': '127.0.0.1', 'sshEndpoint': '127.0.0.1:2222',
                  'archiveAfter': None, 'type': 'small', 'billingMultiplier': 0.5}})
elif tool == 'ssh':
    assert 'box-herdr-bx_saved' in args, 'Wrong SSH target'
    script = args[-1]
    if script == 'true':
        record('check')
    elif 'findmnt' in script and '/var/lib/ascii-lazy/status.json' in script:
        record('filesystem')
        emit({'filesystem': 'ext4', 'phase': 'done'})
    elif script.startswith('bash -lc ') and '/bootstrap.sh' in script:
        record('bootstrap')
        assert (home / '.box-herdr/projects/dashboard/bootstrap.sh').is_file()
        assert '--with-herdr' not in script, 'Plain preparation opted into Herdr'
    else:
        record('remote-command')
        # Safe only in this offline disposable container; nothing from the host
        # is mounted. This executes actual scripts emitted by the packaged CLI.
        raise SystemExit(subprocess.call(['bash', '-c', script]))
elif tool == 'scp':
    record('collect')
    assert args[:2] == ['-l', '8192']
    assert args[2] == 'box-herdr-bx_saved:/home/user/.box-herdr/tasks/shell-dashboard/results.tar.gz'
    target = Path(args[3])
    assert target.is_relative_to(home / '.local/share/box-herdr/tasks/shell-dashboard/results')
    shutil.copyfile(args[2].split(':', 1)[1], target)
elif tool == 'herdr':
    kind = args.pop(0)
    if kind == '--session':
        assert args.pop(0) == 'agents'
        assert args.pop(0) == 'workspace'
        state = home / 'workspaces.json'
        values = json.loads(state.read_text()) if state.exists() else []
        operation = args.pop(0)
        record('workspace-' + operation)
        if operation == 'create':
            assert args == ['--cwd', '/home/user/tasks/shell-dashboard', '--label', 'dashboard / project', '--no-focus']
            assert not values
            values.append({'workspace_id': 'w_fixture', 'label': 'dashboard / project'})
            state.write_text(json.dumps(values))
        else:
            assert operation == 'list'
        emit({'workspaces': values})
    else:
        assert kind == 'machine'
        state = home / 'machines.json'
        values = json.loads(state.read_text()) if state.exists() else []
        operation = args.pop(0)
        record('machine-' + operation)
        if operation == 'add':
            assert args == ['box-herdr-bx_saved', '--label', 'dashboard', '--remote-session', 'agents']
            assert not values
            values.append({'id': 'machine_fixture', 'label': 'dashboard', 'target': 'box-herdr-bx_saved',
                           'session': 'agents', 'enabled': True})
            state.write_text(json.dumps(values))
        else:
            assert operation == 'list' and args == ['--json']
        emit(values)
else:
    raise AssertionError('Unexpected fixture executable')
