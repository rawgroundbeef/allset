#!/usr/bin/env python3
"""Launch isolated Box workers and manage their explicitly targeted Herdr sessions.

Uses only the standard library and official Box/Herdr/OpenSSH/Git CLIs. Local
state contains identifiers and task text, never copied authentication secrets.
"""

import argparse
import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import time
import uuid
import repository_access

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ['_ALLSET_STATE_ROOT'])
BOX = Path(os.environ['_ALLSET_BOX_BIN'])
HERDR = Path(os.environ['_ALLSET_HERDR_BIN'])
CONFIG = STATE / 'herdr/config.toml'
SSH_DIR = STATE / 'ssh'
SESSION = 'agents'
# These limits apply to this trial launcher even if the account permits more.
MAX_MACHINES = 3
RATE = 0.5
# Project snapshots retain code/conversations but omit supported provider login files.
PROJECT_IGNORES = ('/.npmrc\n/.codex/auth.json*\n/.claude/.credentials*\n/.config/cursor/auth.json*\n'
                   '/.config/gh/\n/.git-credentials\n/.config/ascii/box/config.json\n'
                   '/.cursor/auth.json\n/.infisical/\n/.config/infisical/\n/infisical-keyring/\n'
                   '**/.next/\n**/.ladle-build/\n')
# Official Herdr 0.9.0 Codex integration version 8, reviewed at installation.
HOOK_SHA256 = '38a90a2a99872d06dcbc978e7613406cdd852dbb07503abd7a113f518d5951f3'


def command(args, *, cwd=None, data=None, timeout=180, check=True):
    """Capture a command without a shell; callers must not print secret-bearing results."""
    result = subprocess.run([str(a) for a in args], cwd=cwd, input=data,
                            capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f'{Path(str(args[0])).name} failed: '
                           f'{(result.stderr or result.stdout)[-3000:]}')
    return result


class BoxCommandError(RuntimeError):
    """Retain Box's structured failure so callers can distinguish timeout from denied access."""

    def __init__(self, result):
        """Attach the native result without depending on camel-case fields in rendered text."""
        self.result = result
        if result.get('timedOut') is True:
            message = 'Box command timed out'
        else:
            message = 'Box command failed: ' + json.dumps(result)
        super().__init__(message)


def box(*args, timeout=180):
    """Call Box with JSON flags before its command to avoid forwarding flags remotely."""
    result = command([BOX, '--no-update', '--json', *args], timeout=timeout, check=False)
    output = result.stdout or result.stderr
    try:
        records = [json.loads(line) for line in output.splitlines() if line.strip()]
    except ValueError:
        if result.returncode:
            raise RuntimeError('box failed: ' + (result.stderr or result.stdout)[-3000:]) from None
        raise
    if not records:
        raise RuntimeError('Box returned no result')
    record = records[-1]
    if result.returncode or (isinstance(record, dict) and record.get('success') is False):
        raise BoxCommandError(record)
    return record


def ssh_args(meta):
    """Keep bulk automation on its own SSH transport, separate from Herdr's live UI."""
    return ['ssh', '-o', 'ControlMaster=auto', '-o', 'ControlPersist=120', '-o',
            'ControlPath=' + str(SSH_DIR / (meta['machine_id'] + '.m')), meta['ssh_alias']]


def remote(meta, script, *, timeout=60, detach=False):
    """Route short/detached commands by Box ID and longer commands through its pinned SSH alias."""
    if detach and meta.get('ssh_alias'):
        log = meta['remote_state'] + '/runner.log'
        launch = ('nohup bash -lc ' + shlex.quote(script) + ' > ' + shlex.quote(log)
                  + ' 2>&1 < /dev/null & echo $!')
        pid = command(ssh_args(meta) + [launch], timeout=90).stdout.strip()
        if not pid.isdigit():
            raise RuntimeError('Background setup PID was not returned; inspect the recorded task.')
        return {'processId': int(pid), 'logPath': log}
    if not detach and meta.get('ssh_alias'):
        return command(ssh_args(meta) + [script], timeout=timeout + 45).stdout
    args = ['exec']
    args += ['--detach'] if detach else ['--timeout', str(min(timeout, 600))]
    result = box(*args, meta['machine_id'], script, timeout=timeout + 45)
    if result.get('success') is False:
        raise RuntimeError('Remote command failed: ' +
                           (result.get('stderr') or result.get('stdout') or str(result))[-3000:])
    return result if detach else result.get('stdout', '')


def herdr_env():
    """Isolate local Herdr config and sockets from all existing user sessions."""
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('HERDR_'):
            env.pop(key)
    env['HERDR_CONFIG_PATH'] = str(CONFIG)
    return env


def local_herdr(*args, timeout=120):
    """Control the dedicated local machine catalog, never the user's default server."""
    result = subprocess.run([str(HERDR), *args], env=herdr_env(),
                            text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def rh(meta, *args, timeout=60):
    """Execute a Herdr command on this host's named session and return its JSON result."""
    output = remote(meta, shlex.join(['/home/user/.local/bin/herdr', '--session',
                                     SESSION, *args]), timeout=timeout)
    response = json.loads(output)
    if 'error' in response:
        raise RuntimeError(str(response['error']))
    return response.get('result', response)


def save(meta):
    """Atomically persist state after every externally visible lifecycle step."""
    directory = STATE / 'tasks' / meta['task_id']
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / 'task.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(meta, indent=2) + '\n')
    temporary.chmod(0o600)
    temporary.replace(target)


def load(task):
    """Resolve a recorded task ID or an unambiguous owned Box ID."""
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', task):
        raise ValueError('Use a recorded task ID or Box ID')
    matches = [json.loads(p.read_text()) for p in (STATE / 'tasks').glob('*/task.json')]
    matches = [m for m in matches if task in (m['task_id'], m.get('machine_id'))]
    if len(matches) != 1:
        raise ValueError(f'Expected one owned task matching {task}; found {len(matches)}')
    return matches[0]


@contextlib.contextmanager
def creation_lock():
    """Serialize local capacity checks and create requests so concurrent launches cannot race."""
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / 'creation.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def billing_rate(info):
    """Read the server-confirmed rate so resized Boxes reserve their actual usage."""
    rate = float(info['billingMultiplier'])
    if not math.isfinite(rate) or rate <= 0:
        raise RuntimeError('Unknown Box billing multiplier.')
    return rate


def check_allowance(limits, ttl, *, starting=True, reserved_seconds=0, rate=RATE):
    """Fail closed on unknown funds, exhausted starts, trial TTL, or concurrent capacity."""
    if starting and not limits.get('canStart'):
        raise RuntimeError('Box cannot start: ' + str(limits.get('startBlockedReason')))
    capacity = min(MAX_MACHINES, int(limits['maxActiveBoxes']))
    if starting and int(limits['activeBoxes']) >= capacity:
        raise RuntimeError(f'Concurrent Box limit reached ({capacity}); stop an owned worker first.')
    if not 60 <= ttl <= 86400:
        raise ValueError('TTL must be 60..86400 seconds; this launcher always bounds usage.')
    if limits.get('accessTier') == 'trial' and ttl > 7200:
        raise ValueError('The Box trial enforces a maximum two-hour TTL.')
    if not math.isfinite(rate) or rate <= 0:
        raise RuntimeError('Unknown Box billing multiplier.')
    remaining = float(limits['creditBalanceSeconds'])
    # Leave five baseline minutes above this worker's maximum reservation.
    if not math.isfinite(remaining) or remaining < reserved_seconds + rate * ttl + 300:
        raise RuntimeError('Insufficient confirmed existing allowance for this bounded run.')
    for period in (('minute', 'hour', 'day') if starting else ()):
        if limits['starts'][period]['remaining'] < 1:
            raise RuntimeError(f'Box {period} start allowance exhausted.')


def reserved_allowance(exclude=None, *, horizon_seconds=None):
    """Reserve other VMs; continuously running Boxes count across this operation's bounded window."""
    listing = box('list')
    if listing['pageInfo']['hasMore']:
        raise RuntimeError('Cannot establish total active Box usage from a partial list.')
    now = datetime.now(timezone.utc)
    seconds = 0
    for machine in listing['boxes']:
        if machine['id'] == exclude or machine['state'] in ('stopped', 'archived'):
            continue
        rate = billing_rate(machine)
        if not machine.get('archiveAfter'):
            if (type(horizon_seconds) not in (int, float) or not math.isfinite(horizon_seconds)
                    or not 60 <= horizon_seconds <= 86400):
                raise RuntimeError('A bounded operation window is required to account for a continuously running Box.')
            seconds += rate * horizon_seconds
            continue
        deadline = datetime.fromisoformat(machine['archiveAfter'].replace('Z', '+00:00'))
        seconds += max(0, (deadline - now).total_seconds()) * rate
    return seconds


def create(meta, ttl, template=None, environment=None):
    """Create once and journal the ID immediately; never retry an ambiguous create."""
    if not isinstance(environment, str) or not environment.strip():
        raise ValueError('An explicit Box environment is required before creating a machine')
    with creation_lock():
        limits = box('limits')
        check_allowance(limits, ttl, reserved_seconds=reserved_allowance(horizon_seconds=ttl))
        meta.update(phase='creating', ttl_seconds=ttl)
        save(meta)
        args = [str(BOX), '--no-update', '--json', 'new', '--type', 'small',
                '--environment', environment, '--ttl', str(ttl)]
        if template:
            args += ['--from', template]
        with subprocess.Popen(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            for line in process.stdout:
                event = json.loads(line)
                if event.get('id'):
                    meta['machine_id'] = event['id']
                    save(meta)
                if event.get('event') == 'error':
                    meta['error'] = event.get('error', 'Box create failed')
                    save(meta)
                if event.get('archiveAfter'):
                    meta['archive_after'] = event['archiveAfter']
                    save(meta)
            if process.wait():
                raise RuntimeError(meta.get('error') or process.stderr.read() or 'Create failed')
        if not meta.get('machine_id'):
            raise RuntimeError('Create result was ambiguous; inspect box list before trying again.')


def wait_box(meta, *, stopped=False, timeout=600):
    """Poll native lifecycle state and retain the current address and auto-stop deadline."""
    deadline = time.monotonic() + timeout
    last_report = 0
    while time.monotonic() < deadline:
        info = box('info', meta['machine_id'])['box']
        meta.update(box_state=info['state'], archive_after=info.get('archiveAfter'),
                    box_type=info.get('type'), billing_multiplier=info.get('billingMultiplier'))
        if info.get('error'):
            meta['error'] = info['error']
        save(meta)
        if info['state'] in (('stopped', 'archived') if stopped else ('ready', 'idle', 'running')):
            return info
        if info['state'] == 'error':
            raise RuntimeError('Box entered error: ' + str(info.get('error')))
        if not stopped and info['state'] in ('stopped', 'archived'):
            raise RuntimeError('Box did not start: ' + str(info.get('error') or info['state']) +
                               '. The saved machine has not been replaced.')
        if time.monotonic() - last_report >= 30:
            print('Box ' + meta['machine_id'] + ': ' + info['state'] + '; waiting...', flush=True)
            last_report = time.monotonic()
        time.sleep(3)
    raise TimeoutError('Box did not reach the requested state; its ID is saved.')


def transient_box_error(error):
    """Identify temporary restore/transport failures without retrying denied access or mutations."""
    return isinstance(error, subprocess.TimeoutExpired) or any(
        marker in str(error).lower() for marker in
        ('timed out', 'connection reset', 'temporarily unavailable', 'box_restoring', 'box_starting'))


def restored_host_key(meta, timeout=900):
    """Fetch the host public key through authenticated Box reads, retrying startup transport failures."""
    started = time.monotonic()
    last_report = -30
    transport_failures = 0
    while True:
        try:
            return remote({'machine_id': meta['machine_id']},
                          'cat /etc/ssh/ssh_host_ed25519_key.pub', timeout=15).strip().split()
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            elapsed = time.monotonic() - started
            execution_timed_out = isinstance(error, BoxCommandError) and error.result.get('timedOut') is True
            if execution_timed_out or 'box_starting' in str(error) or 'box_restoring' in str(error):
                if elapsed >= timeout:
                    raise TimeoutError('Box has not finished preparing its environment; no host key was replaced or agent started.') from None
                if elapsed - last_report >= 30:
                    print(f'Box is preparing its environment ({int(elapsed)}s elapsed); waiting for authenticated SSH access...', flush=True)
                    last_report = elapsed
                time.sleep(min(15, max(0, timeout - elapsed)))
                continue
            transport_failures += 1
            if not transient_box_error(error) or transport_failures == 3:
                raise
            print('Box is running; its command API is still warming up. Retrying host verification...', flush=True)
            time.sleep(2 ** transport_failures)


def ssh_destination(info):
    """Prefer Box's forwarded SSH endpoint; only direct IP access defaults to port 22."""
    endpoint = info.get('sshEndpoint')
    if endpoint in (None, ''):
        return str(ipaddress.ip_address(info['ip'])), 22
    if not isinstance(endpoint, str):
        raise ValueError('Box returned an invalid SSH endpoint')
    match = re.fullmatch(r'(?:\[([^\]]+)\]|([^:\s]+)):([0-9]+)', endpoint)
    if not match:
        raise ValueError('Box returned an invalid SSH endpoint')
    address = str(ipaddress.ip_address(match.group(1) or match.group(2)))
    port = int(match.group(3))
    if not 1 <= port <= 65535:
        raise ValueError('Box returned an invalid SSH port')
    return address, port


def refresh_ssh(meta):
    """Refresh only the owned alias and authenticate changed host keys through the Box API."""
    info = wait_box(meta)
    address, port = ssh_destination(info)
    # A live pinned connection already proves access. Avoid repeating Box's key
    # registration endpoint on every terminal open; changed hosts still use it.
    same_destination = meta.get('ip') == address and meta.get('ssh_port', 22) == port
    if meta.get('ssh_alias') and same_destination:
        try:
            verified = command(ssh_args(meta) + ['true'], timeout=20, check=False)
            if verified.returncode == 0:
                return
        except subprocess.TimeoutExpired:
            pass
    # A resumed project already has its registered user key. Only first setup
    # needs Box's registration flow; authenticate its new host key via box exec.
    if not meta.get('ssh_alias'):
        print('Registering SSH access with Box...', flush=True)
        command([BOX, '--no-update', 'ssh', meta['machine_id'], 'true'], timeout=90)
    print('Verifying the resumed machine identity...', flush=True)
    public_key = restored_host_key(meta)
    if len(public_key) < 2 or public_key[0] != 'ssh-ed25519':
        raise ValueError('Expected an Ed25519 host key from authenticated Box command API')
    alias = 'box-herdr-' + meta['machine_id']
    SSH_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    known = SSH_DIR / 'known_hosts'
    lines = known.read_text().splitlines() if known.exists() else []
    verified = alias + ' ' + ' '.join(public_key[:2])
    previous = next((line for line in lines if line.startswith(alias + ' ')), None)
    if meta.get('ssh_alias') and (not same_destination or (previous and previous != verified)):
        for suffix in ('.m', '.mux'):
            command(['ssh', '-S', str(SSH_DIR / (meta['machine_id'] + suffix)), '-O', 'exit',
                     meta['ssh_alias']], check=False, timeout=20)
    lines = [line for line in lines if not line.startswith(alias + ' ')]
    lines.append(alias + ' ' + ' '.join(public_key[:2]))
    known.write_text('\n'.join(lines) + '\n')
    stanza = (f'Host {alias}\n  HostName {address}\n  User user\n  Port {port}\n'
              f'  IdentityFile {Path.home()}/.ssh/ascii_box_ed25519\n'
              '  IdentitiesOnly yes\n  IdentityAgent none\n  BatchMode yes\n'
              f'  StrictHostKeyChecking yes\n  HostKeyAlias {alias}\n'
              f'  UserKnownHostsFile {known}\n  IPQoS none\n'
              '  ControlMaster no\n  ControlPath none\n'
              '  ServerAliveInterval 15\n  ServerAliveCountMax 3\n  ConnectTimeout 15\n')
    (SSH_DIR / (alias + '.conf')).write_text(stanza)
    (SSH_DIR / 'config').write_text('Include ' + str(SSH_DIR / '*.conf') + '\n')
    user_config = Path.home() / '.ssh/config'
    original = user_config.read_text() if user_config.exists() else ''
    include = 'Include ' + str(SSH_DIR / 'config') + '\n'
    if include not in original:
        if not (SSH_DIR / 'original-config').exists():
            (SSH_DIR / 'original-config').write_text(original)
        user_config.write_text(include + original)
        user_config.chmod(0o600)
    meta.update(ssh_alias=alias, ip=address, ssh_port=port)
    save(meta)
    result = command(ssh_args(meta) + ['true'], timeout=30, check=False)
    if result.returncode and 'Permission denied (publickey)' in result.stderr:
        print('Box requires SSH key registration again; registering the existing key...', flush=True)
        command([BOX, '--no-update', 'ssh', meta['machine_id'], 'true'], timeout=90)
        command(ssh_args(meta) + ['true'], timeout=30)
    elif result.returncode:
        raise RuntimeError('Verified Box host is not accepting SSH yet: ' + result.stderr[-1500:])


def transfer(meta, source, target):
    """Transfer bounded chunks over SSH, resuming verified parts without a stalled SCP/rsync stream."""
    payload = Path(source).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    directory = target + '.parts-' + digest[:12]
    chunk_size = 256 * 1024
    chunks = [payload[n:n + chunk_size] for n in range(0, len(payload), chunk_size)]
    script = ('from pathlib import Path;import hashlib,json;d=Path(' + repr(directory) + ');'
              'd.mkdir(parents=True,exist_ok=True);print(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}))')
    present = json.loads(remote(meta, shlex.join(['python3', '-c', script])))

    def send(item):
        """Acknowledge one durable chunk by digest; retries cannot duplicate or corrupt bytes."""
        index, data = item
        name = f'{index:06d}'
        expected = hashlib.sha256(data).hexdigest()
        if present.get(name) == expected:
            return
        script = ('from pathlib import Path;import sys,hashlib;data=sys.stdin.buffer.read();'
                  'assert hashlib.sha256(data).hexdigest()==' + repr(expected) + ';'
                  'Path(' + repr(directory + '/' + name) + ').write_bytes(data);print("saved")')
        for attempt in range(3):
            try:
                result = subprocess.run(ssh_args(meta) + [shlex.join(['python3', '-c', script])],
                                        input=data, capture_output=True, timeout=45)
                if result.returncode == 0 and result.stdout.strip() == b'saved': return
            except subprocess.TimeoutExpired:
                pass
        raise RuntimeError('SSH chunk transfer failed; verified parts are retained for retry.')

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(send, enumerate(chunks)))
    assemble = ('from pathlib import Path;import hashlib,os;d=Path(' + repr(directory) + ');'
                'data=b"".join((d/f"{i:06d}").read_bytes() for i in range(' + str(len(chunks)) + '));'
                'assert hashlib.sha256(data).hexdigest()==' + repr(digest) + ';'
                'p=Path(' + repr(target + '.verified') + ');p.write_bytes(data);os.replace(p,' + repr(target) + ');print("verified")')
    if remote(meta, shlex.join(['python3', '-c', assemble]), timeout=120).strip() != 'verified':
        raise RuntimeError('Transfer verification failed')


def write_remote(meta, target, data):
    """Send file contents on SSH stdin, keeping credentials and task text out of argv."""
    script = 'umask 077; mkdir -p ' + shlex.quote(str(Path(target).parent)) + '; cat > ' + shlex.quote(target)
    result = command(ssh_args(meta) + [script], data=data, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError('Private SSH file transfer failed; contents withheld.')


def register(meta, *, prepare=False):
    """Save a profile for exactly this Box and remote session, without restarting existing servers."""
    profiles = json.loads(local_herdr('machine', 'list', '--json'))
    profile = next((p for p in profiles if p['target'] == meta['ssh_alias'] and p['session'] == SESSION), None)
    if profile and prepare:
        # Native machine add prepares and daemonizes over ordinary SSH. Remove
        # only our saved connection, after checking the remote server is absent.
        local_herdr('machine', 'remove', profile['id'])
        profile = None
    if profile:
        local_herdr('machine', 'rename', profile['id'], '--label', meta['label'])
        local_herdr('machine', 'enable', profile['id'])
    else:
        try:
            local_herdr('machine', 'add', meta['ssh_alias'], '--label', meta['label'],
                        '--remote-session', SESSION, timeout=180)
        except RuntimeError as error:
            if 'server did not become ready within' not in str(error):
                raise
            # Herdr's native five-second startup budget can expire while a
            # restored session is still opening its panes. Wait for that server;
            # never restart it or discard the restored session.
            print('Herdr is restoring its panes; waiting for the existing server...', flush=True)
            for _ in range(30):
                ready = remote(meta, 'test -S /home/user/.config/herdr/sessions/' + SESSION +
                               '/herdr-client.sock && echo ready || true')
                if ready.strip() == 'ready':
                    break
                time.sleep(2)
            else:
                raise RuntimeError('Herdr startup is still incomplete. Inspect its server log before restarting.') from error
            local_herdr('machine', 'add', meta['ssh_alias'], '--label', meta['label'],
                        '--remote-session', SESSION, timeout=180)
        profiles = json.loads(local_herdr('machine', 'list', '--json'))
        profile = next(p for p in profiles if p['target'] == meta['ssh_alias'] and p['session'] == SESSION)
    meta['herdr_profile_id'] = profile['id']
    save(meta)


def source_checkout(repo, base, directory):
    """Fetch an isolated shallow source cache without checking out or altering the user's worktree."""
    if Path(repo).exists():
        url = command(['git', '-C', repo, 'remote', 'get-url', 'origin']).stdout.strip()
    elif re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
        url = 'https://github.com/' + repo + '.git'
    else:
        raise ValueError('Repository must be a local checkout or GitHub owner/repo')
    if not url.startswith(('https://github.com/', 'git@github.com:')):
        raise ValueError('This launcher currently supports GitHub repositories only')
    command(['git', 'check-ref-format', '--branch', base])
    cache = directory / 'source.git'
    command(['git', 'init', '--bare', str(cache)])
    command(['git', '-C', str(cache), 'fetch', '--depth=1', url, '+' + base + ':refs/heads/box-source'], timeout=300)
    sha = command(['git', '-C', str(cache), 'rev-parse', 'box-source']).stdout.strip()
    bundle = directory / 'source.bundle'
    command(['git', '-C', str(cache), 'bundle', 'create', str(bundle), 'box-source'], timeout=300)
    return sha, bundle, url


def configure_task(meta, bundle, *, with_agent=True):
    """Prepare a unique worktree; shell-only callers stop after dependency setup without an agent."""
    refresh_ssh(meta)
    state = '/home/user/.box-herdr/tasks/' + meta['task_id']
    base_repo = meta.get('base_repo')
    if not base_repo or not Path(base_repo).is_absolute():
        raise ValueError('A project-owned absolute base repository is required')
    meta.update(remote_state=state, cwd='/home/user/tasks/' + meta['task_id'], phase='setup')
    save(meta)
    # Template-only exclusions must not prevent this task's Herdr layout and
    # session references from surviving stop/resume.
    write_remote(meta, '/home/user/.boxignore', PROJECT_IGNORES)
    remote(meta, shlex.join(['mkdir', '-p', state, '/home/user/tasks']))
    exists = remote(meta, f'git -C {base_repo} cat-file -e {meta["base_sha"]} 2>/dev/null && echo yes || true', timeout=300)
    if exists.strip() != 'yes':
        transfer(meta, bundle, state + '/source.bundle')
        # Git bundles do not carry shallow boundaries; transfer the verified root
        # SHA explicitly. Only the controller's source-cache ref may move across
        # disconnected shallow commits; user branches/worktrees are untouched.
        remote(meta, f'mkdir -p {base_repo}; git -C {base_repo} init -q; '
               f'printf "%s\\n" {meta["base_sha"]} >> {base_repo}/.git/shallow; '
               f'git -C {base_repo} fetch {state}/source.bundle +box-source:refs/remotes/task/source', timeout=180)
    existing = remote(meta, 'test -f ' + shlex.quote(meta['cwd'] + '/.git') + ' && echo yes || true')
    if existing.strip() == 'yes':
        branch = remote(meta, shlex.join(['git', '-C', meta['cwd'], 'branch', '--show-current']))
        if branch.strip() != meta['branch']:
            raise RuntimeError('Existing task checkout has an unexpected branch; leaving it untouched.')
    else:
        remote(meta, shlex.join(['git', '-C', base_repo, 'worktree', 'add', '-b',
                                meta['branch'], meta['cwd'], meta['base_sha']]), timeout=300)
    repository_access.configure(remote, meta, meta['cwd'], meta['repository'],
                                meta.get('project_profile', {}).get('github'))
    for setting in ('user.name', 'user.email'):
        identity = command(['git', 'config', '--get', setting]).stdout.strip()
        remote(meta, shlex.join(['git', '-C', meta['cwd'], 'config', setting, identity]))
    prepare_task(meta)
    if not with_agent:
        meta['phase'] = 'shell-ready'; save(meta)
        return
    authenticate(meta)
    register(meta)
    workspace = rh(meta, 'workspace', 'create', '--cwd', meta['cwd'], '--label', meta['label'], '--no-focus')
    meta.update(workspace_id=workspace['workspace']['workspace_id'],
                pane_id=workspace['root_pane']['pane_id'])
    save(meta)
    # Configuration is scoped to this VM; trust only the prepared task directory.
    existing_config = remote(meta, 'cat /home/user/.codex/config.toml 2>/dev/null || true')
    config = existing_config or ('cli_auth_credentials_store = "file"\ncheck_for_update_on_startup = false\n'
              'approval_policy = "on-request"\nsandbox_mode = "workspace-write"\n'
              '[sandbox_workspace_write]\nnetwork_access = true\n'
              '[features]\nhooks = true\n')
    project_key = '[projects.' + json.dumps(meta['cwd']) + ']'
    if project_key not in config:
        config += '\n' + project_key + '\ntrust_level = "trusted"\n'
    write_remote(meta, '/home/user/.codex/config.toml', config)
    start_agent(meta)
    before = next(a for a in rh(meta, 'agent', 'list')['agents'] if a['pane_id'] == meta['pane_id'])
    rh(meta, 'agent', 'prompt', meta['agent_name'], meta['prompt'], timeout=60)
    # Herdr acknowledges terminal input, not execution. Observe an actual state
    # transition before reporting success, and never resubmit an ambiguous task.
    for _ in range(20):
        agent = next(a for a in rh(meta, 'agent', 'list')['agents'] if a['pane_id'] == meta['pane_id'])
        if agent['state_change_seq'] > before['state_change_seq'] and agent.get('agent_session'):
            meta.update(phase='running', agent_status=agent['agent_status'], agent_session=agent['agent_session'])
            save(meta)
            break
        time.sleep(1)
    else:
        raise RuntimeError('Task was sent but execution was not observed. Inspect its pane; do not resubmit blindly.')


def prepare_task(meta):
    """Await this setup run, with matching source and token, before any agent is started."""
    state = meta['remote_state']
    for name in ('bootstrap.sh', 'prepare.sh', 'worker.py'):
        write_remote(meta, state + '/' + name, (ROOT / name).read_text())
    meta['setup_token'] = uuid.uuid4().hex
    write_remote(meta, state + '/task.json', json.dumps(meta))
    setup = remote(meta, shlex.join(['python3', state + '/worker.py', 'prepare', state]), detach=True)
    meta['setup_process_id'] = setup['processId']
    save(meta)
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        output = remote(meta, 'cat ' + state + '/setup.json 2>/dev/null || echo "{}"')
        status = json.loads(output)
        if status.get('setup_token') != meta['setup_token']:
            time.sleep(2)
            continue
        if status.get('state') == 'ready':
            if status['base_sha'] != meta['base_sha']:
                raise RuntimeError('Setup verified the wrong commit')
            meta['lock_sha256'] = status['lock_sha256']
            break
        if status.get('state') == 'failed':
            raise RuntimeError('Dependency setup failed; inspect ' + state + '/setup.log')
        time.sleep(4)
    else:
        raise TimeoutError('Setup did not complete; agent was not started.')


def read_agent(meta):
    """Read plain terminal output; unlike other Herdr operations this is not JSON."""
    return remote(meta, shlex.join(['/home/user/.local/bin/herdr', '--session',
                                  SESSION, 'agent', 'read', meta['pane_id']]))


def start_agent(meta):
    """Resolve only the reviewed Herdr hook's first-run trust dialog before task submission."""
    rh(meta, 'agent', 'start', meta['agent_name'], '--kind', 'codex', '--pane', meta['pane_id'],
       '--timeout', '60000', '--', '--no-alt-screen', timeout=90)
    screen = read_agent(meta)
    if 'hook needs review before it can run' in screen or 'Hooks need review' in screen:
        hooks = json.loads(remote(meta, 'cat /home/user/.codex/hooks.json'))
        expected = {'hooks': {'SessionStart': [{'hooks': [{
            'command': "bash '/home/user/.codex/herdr-agent-state.sh' session",
            'timeout': 10, 'type': 'command'}]}]}}
        digest = remote(meta, 'sha256sum /home/user/.codex/herdr-agent-state.sh').split()[0]
        if hooks != expected or digest != HOOK_SHA256:
            raise RuntimeError('Unexpected Codex hooks require review in the remote pane.')
        if 'Trust all and continue' in screen:
            rh(meta, 'agent', 'send-keys', meta['agent_name'], 'down', 'enter')
        else:
            rh(meta, 'agent', 'send-keys', meta['agent_name'], 't', 'esc', 'ctrl+c', 'ctrl+c')
            for _ in range(20):
                if not any(a['pane_id'] == meta['pane_id'] for a in rh(meta, 'agent', 'list')['agents']):
                    break
                time.sleep(1)
            rh(meta, 'agent', 'start', meta['agent_name'], '--kind', 'codex', '--pane', meta['pane_id'],
               '--timeout', '60000', '--', '--no-alt-screen', timeout=90)
    for _ in range(20):
        agent = next((a for a in rh(meta, 'agent', 'list')['agents'] if a['pane_id'] == meta['pane_id']), {})
        if agent.get('agent_session'):
            meta['agent_session'] = agent['agent_session']
            save(meta)
            return
        # Codex may create its conversation lazily on the first prompt. An
        # interactive blank composer is ready; configure_task must then observe
        # the conversation ID and a real state transition before success.
        if agent.get('interactive_ready') and 'Ask Codex to do anything' in read_agent(meta):
            return
        time.sleep(1)
    raise RuntimeError('Codex conversation ID not recorded; inspect the pane before sending a task.')


def authenticate(meta):
    """Check the Box's own Codex login; never inherit or overwrite a laptop or sibling login."""
    try:
        remote(meta, 'codex login status')
    except RuntimeError:
        raise RuntimeError('Sign in to Codex inside this project Box with its intended account before using launch. '
                           'Use box-herdr open ' + meta.get('project', '') + ' to choose any agent yourself.') from None


def report(meta):
    """Print the daily-use handles and explicit resource deadline."""
    print(json.dumps({k: meta.get(k) for k in (
        'task_id', 'machine_id', 'branch', 'base_sha', 'phase', 'ssh_alias',
        'archive_after', 'herdr_profile_id', 'workspace_id', 'pane_id', 'agent_name',
        'preview_port', 'results_directory', 'agent_status', 'agent_session')}, indent=2))
    print(f'Connect: box-herdr connect {meta["task_id"]}')
    print('Interface: herdr')
    print('VM type:', meta.get('box_type', 'unknown'), 'allowance multiplier:',
          meta.get('billing_multiplier', 'unknown'), 'auto-stop:', meta.get('archive_after'))


def collect_task(meta):
    """Download results into a new timestamped directory and verify the archive paths."""
    state = meta['remote_state']
    for name in ('worker.py',):
        write_remote(meta, state + '/' + name, (ROOT / name).read_text())
    write_remote(meta, state + '/task.json', json.dumps(meta))
    remote(meta, shlex.join(['python3', state + '/worker.py', 'collect', state]), timeout=120)
    output = STATE / 'tasks' / meta['task_id'] / 'results' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    output.mkdir(parents=True, mode=0o700)
    command(['scp', '-l', '8192', meta['ssh_alias'] + ':' + state + '/results.tar.gz', str(output / 'results.tar.gz')], timeout=300)
    with tarfile.open(output / 'results.tar.gz') as archive:
        for member in archive.getmembers():
            if member.name not in {'changes.patch', 'working-tree.patch', 'untracked.tar.gz', 'commits.bundle', 'manifest.json'} or not member.isfile():
                raise ValueError('Unexpected result archive member')
        archive.extractall(output, filter='data')
    meta['results_directory'] = str(output)
    save(meta)
    return output
