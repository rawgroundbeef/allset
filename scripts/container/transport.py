#!/usr/bin/env python3
"""Synthetic CLI boundaries; invoked only inside the disposable test container.

Box state, SSH transport, system bootstrap and Herdr are simulated. Remote Git,
credential restore and native MCP file projection execute the shipped code.
"""
import json
import base64
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import shutil
import time

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


def assert_login_lock():
    with (home / '.local/share/box-herdr/projects/dashboard/operation.lock').open() as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        raise AssertionError('Native sign-in is racing background credential capture')


if tool == 'git':
    if args == ['-c', 'credential.helper=', 'ls-remote', '--exit-code', 'https://github.com/example/dashboard.git', 'HEAD']:
        record('public-access')
        print('0' * 40 + '\tHEAD')
    else:
        os.execv('/usr/bin/git', ['git', *args])
elif tool in ('codex', 'cursor-agent'):
    record(' '.join(args))
    status = ['login', 'status'] if tool == 'codex' else ['status']
    if args == ['login']:
        assert_login_lock()
        time.sleep(.3)
        print('https://signin.example.test/' + tool, flush=True)
        if (home / 'interrupt-native-login').exists():
            # The harness sends SIGINT to AllSet here; this child must be reaped.
            time.sleep(30)
            raise AssertionError('Native login outlived cancellation')
        if tool == 'codex':
            claims = base64.urlsafe_b64encode(json.dumps({'email': 'fixture@example.test'}).encode()).decode().rstrip('=')
            path = home / '.codex/auth.json'
            value = {'tokens': {'access_token': 'synthetic-access', 'id_token': 'fixture.' + claims + '.fixture'}}
        else:
            path = home / '.config/cursor/auth.json'
            value = {'accessToken': 'synthetic-access'}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        path.chmod(0o600)
        print('Synthetic native sign-in completed', flush=True)
    else:
        assert args == status
        print('Logged in as fixture@example.test' if tool == 'cursor-agent' else 'Logged in using ChatGPT')
elif tool == 'claude':
    record(' '.join(args[:2]))
    if args[:2] == ['auth', 'login']:
        assert_login_lock()
        assert args == ['auth', 'login', '--claudeai']
        print('https://signin.example.test/claude', flush=True)
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
    if args == ['status', '--org', 'personal']:
        emit({'account': {'identifier': 'fixture@example.test', 'loginState': 'active'}})
        raise SystemExit(0)
    assert args == ['info', 'bx_saved'], 'Unexpected provider operation'
    emit({'box': {'id': 'bx_saved', 'state': (home / 'box-state').read_text(),
                  'ip': '127.0.0.1', 'sshEndpoint': '127.0.0.1:2222',
                  'archiveAfter': None, 'type': 'small', 'billingMultiplier': 0.5}})
elif tool == 'ssh':
    assert 'box-herdr-bx_saved' in args, 'Wrong SSH target'
    script = args[-1]
    if script == 'true':
        record('check')
    elif script == 'cd -- /home/user/tasks/shell-dashboard && exec "${SHELL:-/bin/bash}" -l':
        record('shell-handoff')
        state = home / '.local/share/box-herdr'
        assert json.loads((state / 'projects/dashboard/onboarding.json').read_text())['stage'] == 'complete'
        for client in ('codex', 'claude', 'cursor'):
            saved = json.loads((state / f'credentials/dashboard/agents/{client}.json').read_text())
            assert saved.get('contents') and not saved.get('needs_login')
        print('SYNTHETIC SSH SHELL', flush=True)
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
        os.execvp('bash', ['bash', '-c', script])
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
