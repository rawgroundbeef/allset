#!/usr/bin/env python3
"""One persistent Box per project, with independent task worktrees and app instances."""

import argparse
import contextlib
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shlex
import signal
import re
import socket
import subprocess
import sys
import time
import uuid

from profiles import validate, credential, check_token
import agent_auth
import github_auth
import infisical_context

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('controller', ROOT / 'box-herdr.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
PROJECTS = c.STATE / 'projects'


def atomic(path, value):
    """Replace a private state record without exposing partial writes."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.chmod(0o600); temp.replace(path)


def project(name):
    """Read an explicit project profile, never infer an Infisical login from the shell."""
    if not name or Path(name).name != name:
        raise ValueError('Use an installed project name')
    return validate(json.loads((PROJECTS / name / 'profile.json').read_text()))


@contextlib.contextmanager
def project_lock(name):
    """Serialize launch/resume within a project while independent projects continue working."""
    path = PROJECTS / name
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (path / 'operation.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def tasks(name):
    """Find only task records assigned to this project, excluding template and machine records."""
    records = [json.loads(p.read_text()) for p in (c.STATE / 'tasks').glob('*/task.json')]
    return [m for m in records if m.get('project') == name and m.get('role') != 'project']


def machine(name):
    """Resolve the single durable Box assigned to a project."""
    record = json.loads((PROJECTS / name / 'machine.json').read_text())
    return c.load(record['task_id'])


def show(meta):
    """Label daily-use handles with their project, task and explicit billing deadline."""
    meta = dict(meta)
    if meta.get('box_state') in ('stopped', 'archived') and meta.get('phase') != 'agent-stopped':
        meta['phase'] = 'project-stopped'
    print(json.dumps({k: meta[k] for k in ('project', 'task_id', 'machine_id', 'phase', 'branch',
          'base_sha', 'ssh_alias', 'workspace_id', 'pane_id', 'agent_name', 'agent_session',
          'archive_after', 'results_directory', 'box_state') if k in meta}, indent=2))
    if meta.get('project'):
        print('Open project: box', meta['project'])
    print('Interface: herdr')
    for name, url in meta.get('preview_urls', {}).items():
        print(name + ':', url)


def stage_auth(meta, profile):
    """Place this project's credential only in remote RAM; never in a snapshot or task record."""
    infisical_context.stage(c, meta, profile)


def request_resume(meta, profile, ttl):
    """Reconcile a timed-out native resume with Box state without submitting a second resume."""
    print('Resuming saved Box ' + meta['machine_id'] + '...', flush=True)
    try:
        c.box('resume', meta['machine_id'], '--ttl', str(ttl), '--environment', profile['box_environment'])
    except subprocess.TimeoutExpired:
        info = c.box('info', meta['machine_id'])['box']
        if info['state'] not in ('provisioning', 'provisioned', 'cloning', 'ready', 'idle', 'running'):
            raise RuntimeError('Resume timed out; Box state is ' + info['state'] +
                               (': ' + info['error'] if info.get('error') else '') +
                               '. The saved machine has not been replaced.') from None
        meta.update(box_state=info['state'], phase='resuming', ttl_seconds=ttl)
        c.save(meta)
        print('Box accepted the resume and is still starting. Waiting for the same machine...', flush=True)


def restored_filesystem_ready(state):
    """Require the permanent home mount and completed hydration before starting persistent processes."""
    if state.get('restore_error'):
        raise RuntimeError('Box filesystem restoration reported an error; no project process was started.')
    filesystem = state.get('filesystem')
    if not isinstance(filesystem, str) or not filesystem:
        raise RuntimeError('Cannot determine the restored home filesystem; refusing to start project processes.')
    return filesystem in ('ext2', 'ext3', 'ext4', 'xfs', 'btrfs') and state.get('phase') in (None, 'done')


def restore_progress(state, elapsed):
    """Show elapsed wait and validated downloaded bytes without inventing a completion percentage."""
    details = [str(max(0, int(elapsed))) + 's elapsed']
    fetched = state.get('bytes_fetched')
    if type(fetched) is int and fetched >= 0:
        details.append(str(fetched // (1024 * 1024)) + ' MiB downloaded')
    return ('Box is restoring files (' + ', '.join(details) +
            '); the project will open when restoration finishes.')


def wait_project_filesystem(meta, timeout=900):
    """Wait out Box's lazy-home mount replacement; SSH readiness alone does not protect open cwd/socket handles.

    Box can expose SSH while home is a temporary FUSE mount. Starting Herdr then
    leaves cwd and Unix sockets on a detached mount when hydration finishes.
    Inspect the mount and the provider's hydration status when present, without
    logging status contents or restarting anything. Unknown readiness fails closed.
    """
    probe = '''import json,subprocess
from pathlib import Path
mounts=json.loads(subprocess.check_output(['findmnt','--json','--target','/home/user','--output','FSTYPE'],text=True))
status=Path('/var/lib/ascii-lazy/status.json')
data=json.loads(status.read_text()) if status.exists() else {}
print(json.dumps({'filesystem':mounts['filesystems'][0]['fstype'],
 'phase':data.get('phase'),'restore_error':bool(data.get('error')),
 'bytes_fetched':data.get('bytesFetched')}))
'''
    started = time.monotonic()
    deadline = started + timeout
    announced = False
    while True:
        state = json.loads(c.remote(meta, shlex.join(['sudo', 'python3', '-c', probe]), timeout=20))
        if restored_filesystem_ready(state):
            if announced: print('Box filesystem restoration complete.', flush=True)
            return
        if time.monotonic() >= deadline:
            raise RuntimeError('Box is still restoring its filesystem. No project process was started; retry box ' +
                               meta['project'] + ' when restoration finishes. Its auto-stop deadline is unchanged.')
        print(restore_progress(state, time.monotonic() - started), flush=True)
        announced = True
        time.sleep(min(30, max(0, deadline - time.monotonic())))


def ensure_project(profile, ttl, *, prepare_apps=True, reconcile_agents=True, prepare_sessions=True):
    """Reuse the project Box; shell access needs neither app credentials nor an agent login."""
    name = profile['name']
    record = PROJECTS / name / 'machine.json'
    if record.exists():
        meta = machine(name)
        info = c.box('info', meta['machine_id'])['box']
        if info['state'] in ('stopped', 'archived'):
            with c.creation_lock():
                c.check_allowance(c.box('limits'), ttl, rate=c.billing_rate(info),
                                  reserved_seconds=c.reserved_allowance(meta['machine_id'], horizon_seconds=ttl))
                request_resume(meta, profile, ttl)
    else:
        # Validate auth before reserving compute, but never persist the returned value.
        if prepare_apps: credential(profile)
        meta = {'task_id': 'project-' + name, 'project': name, 'role': 'project', 'label': name,
                'phase': 'creating', 'remote_state': '/home/user/.box-herdr/projects/' + name}
        c.save(meta)
        try:
            c.create(meta, ttl, profile['template'], profile['box_environment'])
        finally:
            if meta.get('machine_id'):
                atomic(record, {'task_id': meta['task_id'], 'machine_id': meta['machine_id']})
    print('Connecting to ' + name + ' over SSH...', flush=True)
    c.refresh_ssh(meta)
    wait_project_filesystem(meta)
    print('SSH connected. Checking remote tooling...', flush=True)
    c.write_remote(meta, '/home/user/.boxignore', c.PROJECT_IGNORES)
    c.write_remote(meta, meta['remote_state'] + '/bootstrap.sh', (ROOT / 'bootstrap.sh').read_text())
    bootstrap = ['bash', meta['remote_state'] + '/bootstrap.sh']
    if prepare_sessions: bootstrap.append('--with-herdr')
    c.remote(meta, shlex.join(['bash', '-lc', shlex.join(bootstrap)]), timeout=300)
    infisical_context.configure(c, meta, profile)
    if prepare_apps: stage_auth(meta, profile)
    agent_auth.restore(c, meta, profile)
    github_auth.stage(c, meta, profile)
    if prepare_sessions:
        print('Connecting ' + name + ' to Herdr...', flush=True)
        status = c.remote(meta, '/home/user/.local/bin/herdr --session agents status')
        if 'status: not running' in status:
            if c.remote(meta, 'pgrep -u user -x herdr || true').strip():
                raise RuntimeError('A Herdr process exists but its socket is unavailable. Inspect it before restarting.')
            c.register(meta, prepare=True)
        else:
            c.register(meta)
    meta['phase'] = 'running'; c.save(meta)
    if prepare_sessions: print('Herdr connected.', flush=True)
    # A restored ID can name a different pane; recover ownership from the native
    # conversation reference and task cwd before sending any terminal command.
    for task in tasks(name):
        task.update(ssh_alias=meta['ssh_alias'], ip=meta['ip'], archive_after=meta['archive_after'], box_state=meta.get('box_state'),
                    **({'herdr_profile_id': meta['herdr_profile_id']} if meta.get('herdr_profile_id') else {}))
        if prepare_sessions and reconcile_agents and task.get('agent_session') and task.get('phase') != 'agent-stopped':
            sync_panes(task, wait=True)
        c.save(task)
    return meta


def start_task(profile, owner, name, prompt, base):
    """Allocate a fresh task branch/worktree inside the existing project Box."""
    slug = ''.join(ch if ch.isalnum() else '-' for ch in name.lower()).strip('-')[:22]
    if not slug:
        raise ValueError('Task name must contain letters or numbers')
    task_id = profile['name'] + '-' + slug + '-' + uuid.uuid4().hex[:6]
    meta = {'task_id': task_id, 'project': profile['name'], 'project_profile': profile,
            'label': profile['name'] + ' / ' + name, 'agent_name': task_id,
            'branch': 'box/' + task_id, 'prompt': prompt, 'phase': 'fetching',
            'base_repo': owner.get('base_repo', '/home/user/projects/' + profile['name'] + '/source'),
            **{k: owner[k] for k in ('machine_id', 'ssh_alias', 'ip', 'archive_after', 'herdr_profile_id')}}
    c.save(meta)
    sha, bundle, url = c.source_checkout(profile['repository'], base, c.STATE / 'tasks' / task_id)
    meta.update(base_sha=sha, repository=url); c.save(meta)
    try:
        c.configure_task(meta, bundle)
    except BaseException:
        # Failure of one task must never stop its sibling agents or their VM.
        meta['phase'] = 'setup-failed'; c.save(meta)
        raise
    # Herdr's machine label represents the project; its workspace labels represent tasks.
    c.local_herdr('machine', 'rename', owner['herdr_profile_id'], '--label', profile['name'])
    show(meta)
    return meta


def allocate_ports(meta):
    """Reserve disjoint recorded port blocks within this project's VM, checking live listeners."""
    if meta.get('service_ports'):
        return
    used = {p for task in tasks(meta['project']) for p in
            [*task.get('service_ports', {}).values(), task.get('gateway_port', 0)]}
    for block in range(45100, 60100, 20):
        ports = list(range(block, block + len(meta['project_profile']['services']) + 1))
        if used.intersection(ports):
            continue
        script = 'import socket\ns=[]\nfor p in ' + repr(ports) + ':\n x=socket.socket();x.bind(("127.0.0.1",p));s.append(x)\nprint("free")'
        try:
            if c.remote(meta, shlex.join(['python3', '-c', script])).strip() != 'free':
                continue
        except RuntimeError:
            continue
        meta['gateway_port'] = ports[-1]
        meta['service_ports'] = {s['name']: p for s, p in zip(meta['project_profile']['services'], ports)}
        c.save(meta); return
    raise RuntimeError('No free preview port block on this project Box')


def tunnel(meta):
    """Keep a stable per-task local listener; SSH connections recover without releasing its port."""
    path = c.STATE / 'tasks' / meta['task_id'] / 'tunnel.json'
    config = json.loads(path.read_text()) if path.exists() else {}
    if config.get('pid'):
        result = c.command(['ps', '-p', str(config['pid']), '-o', 'command='], check=False)
        if str(path) in result.stdout and 'preview-tunnel.py' in result.stdout:
            return config
    config.update(ssh_alias=meta['ssh_alias'], remote_port=meta['gateway_port'],
                  control_path=str(c.STATE / 'ssh' / (meta['machine_id'] + '.mux')), state='starting')
    atomic(path, config)
    with (path.parent / 'tunnel.log').open('a') as log:
        subprocess.Popen([sys.executable, str(ROOT / 'preview-tunnel.py'), str(path)],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    for _ in range(30):
        saved = json.loads(path.read_text())
        if saved.get('state') == 'listening':
            return saved
        time.sleep(0.2)
    raise RuntimeError('Local preview port is occupied; existing service preserved. Inspect ' + str(path.parent / 'tunnel.log'))


def sync_panes(meta, *, wait=False):
    """Resolve task ownership from its conversation and cwd, then map service tabs by label."""
    for attempt in range(30 if wait else 1):
        agents = c.rh(meta, 'agent', 'list')['agents']
        matches = [a for a in agents if a.get('agent_session', {}).get('value') ==
                   meta.get('agent_session', {}).get('value') and a.get('cwd') == meta['cwd']]
        if len(matches) == 1:
            agent = matches[0]
            meta.update(pane_id=agent['pane_id'], workspace_id=agent['workspace_id'])
            break
        if len(matches) > 1:
            raise RuntimeError('Duplicate conversation references; inspect Herdr before targeting a pane.')
        if wait: time.sleep(2)
    else:
        raise RuntimeError('Saved agent is not restored yet. Attach box-herdr connect ' + meta['project'] +
                           ', then retry; no sibling panes were changed.')
    panes = c.rh(meta, 'pane', 'list', '--workspace', meta['workspace_id'])['panes']
    tabs = c.rh(meta, 'tab', 'list', '--workspace', meta['workspace_id'])['tabs']
    labels = {t['tab_id']: t['label'] for t in tabs}
    wanted = {'gateway_pane': 'preview routing', **{'service_pane_' + s['name']: s['name']
              for s in meta['project_profile']['services']}}
    for key, label in wanted.items():
        matches = [p for p in panes if labels.get(p['tab_id']) == label and
                   p.get('cwd') == meta['cwd'] and not p.get('agent_session')]
        if len(matches) > 1:
            raise RuntimeError('Ambiguous service tab ' + label + '; inspect Herdr before restarting it.')
        meta.pop(key, None)
        if matches: meta[key] = matches[0]['pane_id']
    c.save(meta)


def run_pane(meta, key, label, argv):
    """Start a service only in its saved Herdr pane, without retargeting or restarting sibling panes."""
    if key not in meta:
        tab = c.rh(meta, 'tab', 'create', '--workspace', meta['workspace_id'], '--label', label,
                   '--cwd', meta['cwd'], '--no-focus')
        meta[key] = tab['root_pane']['pane_id']; c.save(meta)
    c.remote(meta, shlex.join(['/home/user/.local/bin/herdr', '--session', c.SESSION,
                             'pane', 'run', meta[key], shlex.join(argv)]))


def listening(meta, port):
    """Check only an owned loopback TCP endpoint, with no database or feature mutations."""
    code = 'import socket;s=socket.socket();s.settimeout(1);print(s.connect_ex(("127.0.0.1",' + str(port) + ')))'
    return c.remote(meta, shlex.join(['python3', '-c', code])).strip() == '0'


def preview(meta):
    """Start the configured app/API once per worktree and expose project/task-labeled local URLs."""
    profile = meta['project_profile']
    sync_panes(meta)
    stage_auth(meta, profile)
    allocate_ports(meta)
    local = tunnel(meta)
    primary = PROJECTS / meta['project'] / 'primary-task.json'
    if not primary.exists(): atomic(primary, {'task_id': meta['task_id']})
    if profile.get('preview_domain'):
        is_primary = json.loads(primary.read_text())['task_id'] == meta['task_id']
        task_suffix = '' if is_primary else '-' + meta['task_id'][-6:]
        meta['preview_urls'] = {service['name']: 'https://' + service['name'] + '-box' + task_suffix +
                               '.' + profile['preview_domain']
                               for service in profile['services'] if service.get('http', True)}
        listing = c.command(['portless', 'list']).stdout
        existing = {host: int(port) for host, port in re.findall(r'https?://([^/\s]+)\s+->\s+localhost:(\d+)', listing)}
        owned = meta.setdefault('portless_routes', {})
        for url in meta['preview_urls'].values():
            host = url.removeprefix('https://')
            base = host.removesuffix('.localhost')
            # Portless can generate aliases for multiple configured TLDs. Guard
            # all matching aliases, including static routes that native --force
            # protection does not distinguish by owner.
            for other, port in existing.items():
                if other.startswith(base + '.') and port not in (local['local_port'], owned.get(host)):
                    raise RuntimeError('Preview alias is already used by another local route: ' + other)
            c.command(['portless', 'alias', host, str(local['local_port'])])
            owned[host] = local['local_port']; c.save(meta)
    else:
        host = (meta['task_id'] if meta['task_id'].startswith(meta['project'])
                else meta['project'] + '-' + meta['task_id']) + '.localhost'
        meta['preview_urls'] = {s['name']: f'http://{s["name"]}.{host}:{local["local_port"]}'
                                for s in profile['services'] if s.get('http', True)}
    state = meta['remote_state']
    c.save(meta)
    for name in ('app-runtime.py', 'infisical_context.py', 'service-exec.py', 'profiles.py', 'preview-gateway.mjs'):
        c.write_remote(meta, state + '/' + name, (ROOT / name).read_text())
    c.write_remote(meta, state + '/task.json', json.dumps(meta))
    for service in profile['services']:
        port = meta['service_ports'][service['name']]
        if not listening(meta, port):
            run_pane(meta, 'service_pane_' + service['name'], service['name'],
                     ['python3', state + '/app-runtime.py', state, service['name']])
            for _ in range(45):
                if listening(meta, port): break
                time.sleep(2)
            else:
                raise RuntimeError(service['name'] + ' did not start; inspect its Herdr pane. Other services remain running.')
    if not listening(meta, meta['gateway_port']):
        run_pane(meta, 'gateway_pane', 'preview routing',
                 ['node', state + '/preview-gateway.mjs', state + '/task.json'])
        for _ in range(15):
            if listening(meta, meta['gateway_port']): break
            time.sleep(1)
        else: raise RuntimeError('Preview gateway did not start')
    meta['preview_enabled'] = True; c.save(meta)
    primary = PROJECTS / meta['project'] / 'primary-task.json'
    if not primary.exists(): atomic(primary, {'task_id': meta['task_id']})
    show(meta)


def stop_task(meta):
    """Collect this task and stop only its agent/app panes; retain its branch, VM and siblings."""
    if meta.get('phase') == 'agent-stopped':
        print('Agent already stopped; saved results:', meta.get('results_directory')); return
    sync_panes(meta)
    output = c.collect_task(meta)
    meta['preview_on_agent_resume'] = meta.get('preview_enabled', False)
    # Native close sends termination to the pane's process tree, including app children.
    panes = {meta.get('pane_id'), meta.get('gateway_pane'),
             *(v for k, v in meta.items() if k.startswith('service_pane_'))} - {None}
    for pane in panes:
        c.rh(meta, 'pane', 'close', pane)
    for key in list(meta):
        if key in ('pane_id', 'gateway_pane', 'workspace_id') or key.startswith('service_pane_'):
            meta.pop(key)
    meta.update(phase='agent-stopped', preview_enabled=False); c.save(meta)
    print('Task stopped; project Box and sibling agents remain running. Results:', output)


def resume_task(meta):
    """Reopen a deliberately stopped agent's native conversation in its saved worktree."""
    if meta.get('pane_id'):
        raise ValueError('Agent pane already exists; connect to the project to continue it.')
    if not meta.get('agent_session'):
        raise ValueError('No recorded native conversation is available to resume')
    tab = c.rh(meta, 'workspace', 'create', '--cwd', meta['cwd'], '--label', meta['label'], '--no-focus')
    meta.update(workspace_id=tab['workspace']['workspace_id'], pane_id=tab['root_pane']['pane_id'])
    c.save(meta)
    c.rh(meta, 'agent', 'start', meta['agent_name'], '--kind', 'codex', '--pane', meta['pane_id'],
         '--timeout', '60000', '--', 'resume', meta['agent_session']['value'], '--no-alt-screen', timeout=90)
    meta['phase'] = 'resuming'; c.save(meta)
    # Codex's integration reports a resumed conversation after its first turn.
    # Submit one bounded read-only check, then require the original native ID.
    c.rh(meta, 'agent', 'prompt', meta['agent_name'],
         'Resume check only: confirm your current worktree and summarize the last completed task. Do not run commands or change files, services, credentials or Git state.')
    sync_panes(meta, wait=True)
    meta['phase'] = 'running'; c.save(meta)
    if meta.get('preview_on_agent_resume'): preview(meta)
    show(meta)


def login_project(profile, owner):
    """Request human sign-in in this project's own VM context without switching local accounts."""
    c.refresh_ssh(owner)
    tab = c.rh(owner, 'workspace', 'create', '--cwd', '/home/user',
               '--label', profile['name'] + ' / Infisical sign-in', '--no-focus')
    owner['login_pane_id'] = tab['root_pane']['pane_id']; c.save(owner)
    argv = ['/home/user/.local/bin/infisical', 'login', '--interactive', '--domain=' + profile['infisical']['instance'],
            '--organization-id=' + profile['infisical']['organization_id']]
    c.remote(owner, shlex.join(['/home/user/.local/bin/herdr', '--session', c.SESSION,
                               'pane', 'run', owner['login_pane_id'], shlex.join(argv)]))
    print('Open box-herdr connect ' + profile['name'] + '; complete Infisical sign-in in ' + owner['login_pane_id'])
    print('Then run box-herdr auth-capture ' + profile['name'] + '. Other project authentication is unchanged.')


def capture_auth(profile, owner):
    """Capture only a successfully validated project login; retain other project credentials verbatim."""
    c.refresh_ssh(owner)
    result = c.command(['ssh', owner['ssh_alias'], '/home/user/.local/bin/infisical user get token --plain --silent'],
                       timeout=45, check=False)
    if result.returncode:
        raise RuntimeError('Project sign-in is incomplete; finish its Infisical pane first.')
    token = result.stdout.strip()
    check_token(profile, token)
    atomic(Path(profile['infisical']['credential_ref']).expanduser(), {'method': 'user-token', 'token': token})
    c.remote(owner, 'rm -f /home/user/.box-herdr/infisical/logged-out')
    stage_auth(owner, profile)
    print('Refreshed only', profile['name'], 'authentication. Existing app processes continue running.')


def open_project(name, *, ttl=7200, create_terminal=True, prepare_sessions=True):
    """Resume a project; checkout-based callers create their own terminal instead of a generic one."""
    if create_terminal and not prepare_sessions:
        raise ValueError('A Herdr terminal requires explicit session preparation')
    profile = project(name)
    with project_lock(name):
        print('Opening ' + name + '...', flush=True)
        owner = ensure_project(profile, ttl, prepare_apps=False, reconcile_agents=False, prepare_sessions=prepare_sessions)
        if create_terminal:
            label = name + ' / terminal'
            workspaces = c.rh(owner, 'workspace', 'list')['workspaces']
            if not any(w.get('label') == label for w in workspaces):
                c.rh(owner, 'workspace', 'create', '--cwd', '/home/user', '--label', label, '--no-focus')
        if prepare_sessions: show(owner)
        if prepare_sessions: print('SSH: ssh ' + owner['ssh_alias'], flush=True)
        return owner


def main():
    """Expose project lifecycle separately from agent lifecycle, preserving legacy result records."""
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    add = actions.add_parser('project-add'); add.add_argument('file', type=Path)
    actions.add_parser('projects'); actions.add_parser('ui'); actions.add_parser('limits')
    opened = actions.add_parser('open', help='Resume project Boxes and open Herdr; choose your own agent')
    opened.add_argument('projects', nargs='+')
    opened.add_argument('--ttl', type=int, default=7200)
    for action in ('up', 'resume', 'extend', 'stop', 'status', 'connect', 'auth-login', 'auth-capture'):
        sub = actions.add_parser(action); sub.add_argument('project')
        if action in ('up', 'resume', 'extend'): sub.add_argument('--ttl', type=int, default=7200)
    launch = actions.add_parser('launch'); launch.add_argument('project'); launch.add_argument('--name', required=True)
    launch.add_argument('--task-file', type=Path, required=True, help='Initial instructions for explicit automated Codex work')
    launch.add_argument('--base')
    launch.add_argument('--ttl', type=int, default=7200)
    launch.add_argument('--no-preview', action='store_true', help='Start only the coding agent')
    for action in ('preview', 'collect', 'agent-stop', 'agent-resume', 'agent-status'):
        sub = actions.add_parser(action); sub.add_argument('task')
    args = parser.parse_args()
    if args.action == 'open':
        # Validate all names before resuming any VM; repeated names open only once.
        names = list(dict.fromkeys(args.projects))
        for name in names: project(name)
        for name in names:
            open_project(name, ttl=args.ttl)
        os.execve(c.HERDR, [str(c.HERDR), '--session', 'box-workers'], c.herdr_env())
        return
    if args.action == 'project-add':
        profile = validate(json.loads(args.file.read_text()))
        path = PROJECTS / profile['name'] / 'profile.json'
        if path.exists() and (PROJECTS / profile['name'] / 'machine.json').exists():
            old = project(profile['name'])
            for key in ('repository', 'infisical'):
                if old[key] != profile[key]:
                    raise ValueError('An assigned Box cannot change repository or authentication binding; use a new project name.')
        atomic(path, profile); print('Installed project:', profile['name']); return
    if args.action == 'projects':
        for path in sorted(PROJECTS.glob('*/profile.json')):
            p = json.loads(path.read_text()); print(p['name'], p['repository'],
                (p.get('infisical') or {}).get('instance', 'shell only; app setup pending'))
        return
    if args.action == 'ui': os.execve(c.HERDR, [str(c.HERDR), '--session', 'box-workers'], c.herdr_env())
    if args.action == 'limits': print(json.dumps(c.box('limits'), indent=2)); return
    if args.action in ('preview', 'collect', 'agent-stop', 'agent-resume', 'agent-status'):
        meta = c.load(args.task)
        info = c.box('info', meta['machine_id'])['box']
        meta.update(box_state=info['state'], archive_after=info.get('archiveAfter'))
        if args.action == 'agent-status':
            show(meta)
            if info['state'] in ('ready', 'idle', 'running'):
                print(json.dumps(c.rh(meta, 'agent', 'list'), indent=2))
            return
        if info['state'] in ('stopped', 'archived'):
            raise RuntimeError('Project Box is stopped; run box-herdr resume ' + meta['project'] + ' first.')
        with project_lock(meta['project']):
            c.refresh_ssh(meta)
            if args.action == 'preview': preview(meta)
            elif args.action == 'collect': print(c.collect_task(meta))
            elif args.action == 'agent-resume': resume_task(meta)
            else: stop_task(meta)
        return
    profile = project(args.project)
    prompt = args.task_file.read_text() if args.action == 'launch' else None
    with project_lock(args.project):
        if args.action in ('up', 'resume', 'launch'):
            owner = ensure_project(profile, args.ttl)
            if args.action == 'launch':
                started = start_task(profile, owner, args.name, prompt, args.base or profile['base'])
                if not args.no_preview: preview(started)
            else:
                for task in tasks(args.project):
                    if task.get('preview_enabled'): preview(task)
                show(owner)
            return
        owner = machine(args.project)
        info = c.box('info', owner['machine_id'])['box']
        if args.action == 'extend':
            c.check_allowance(c.box('limits'), args.ttl, starting=False, rate=c.billing_rate(info),
                              reserved_seconds=c.reserved_allowance(owner['machine_id'], horizon_seconds=args.ttl))
            c.box('extend', owner['machine_id'], '--ttl', str(args.ttl))
            c.wait_box(owner); show(owner); return
        if args.action == 'auth-login': login_project(profile, owner); return
        if args.action == 'auth-capture': capture_auth(profile, owner); return
        if args.action == 'status':
            print(args.project, owner['machine_id'], info['state'], 'auto-stop', info.get('archiveAfter'))
            for task in tasks(args.project):
                task.update(box_state=info['state'], archive_after=info.get('archiveAfter')); show(task)
            if info['state'] in ('ready', 'idle', 'running'): print(json.dumps(c.rh(owner, 'agent', 'list'), indent=2))
            return
        if args.action == 'connect':
            if info['state'] in ('stopped', 'archived'): raise RuntimeError('Run box-herdr resume ' + args.project)
            c.refresh_ssh(owner)
            os.execve(c.HERDR, [str(c.HERDR), '--remote', owner['ssh_alias'], '--session', c.SESSION], c.herdr_env())
        if args.action == 'stop':
            if info['state'] not in ('stopped', 'archived'):
                c.refresh_ssh(owner)
                agent_auth.capture(c, owner, profile)
                for task in tasks(args.project):
                    if task.get('cwd'): c.collect_task(task)
                c.box('stop', owner['machine_id']); c.wait_box(owner, stopped=True)
            if owner.get('herdr_profile_id') and c.HERDR.is_file():
                c.local_herdr('machine', 'disable', owner['herdr_profile_id'])
            owner['phase'] = 'stopped'; c.save(owner)
            print('Project Box stopped; machine billing paused. All project agents require process restoration on resume.')


if __name__ == '__main__':
    try: main()
    except (Exception, KeyboardInterrupt) as error:
        print('box-herdr:', str(error), file=sys.stderr); sys.exit(1)
