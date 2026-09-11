#!/usr/bin/env python3
"""Project shortcuts over the native Box CLI, with a plain remote Herdr terminal."""

import argparse
import contextlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid

import projects
import agent_auth
import repository_access
import progress

c = projects.c

# Native verbs always win, even if a future project is given the same name.
NATIVE_COMMANDS = set('onboard login logout api-key webhook env new org info list extend delete deletion '
    'stop resume prompt interrupt events limits fork ssh exec host desktop browser scp forward dashboard '
    'status data-retention snapshots snapshot self-update completions help'.split())


def repository_key(value):
    """Compare GitHub SSH/HTTPS remotes without depending on a local checkout's name."""
    value = value.strip().removesuffix('.git').rstrip('/')
    value = re.sub(r'^(?:https://github.com/|git@github.com:)', '', value)
    return value.lower()


def resolve_project(value=None, cwd=None):
    """Resolve an explicit alias or registered Git remote; never infer a credential binding."""
    profiles = [json.loads(p.read_text()) for p in projects.PROJECTS.glob('*/profile.json')]
    if value not in (None, '.'):
        matches = [p['name'] for p in profiles if value in (p['name'], *p.get('aliases', []))]
    else:
        result = subprocess.run(['git', '-C', str(cwd or Path.cwd()), 'remote', 'get-url', 'origin'],
                                capture_output=True, text=True)
        if result.returncode: return None
        key = repository_key(result.stdout)
        matches = [p['name'] for p in profiles if repository_key(p['repository']) == key]
    if len(matches) > 1:
        raise ValueError('More than one project matches; repair the duplicate aliases or repository bindings.')
    return matches[0] if matches else None


def terminal(meta, profile):
    """Find the project shell by its live label; leave its cwd and any running agent untouched."""
    label = profile['name'] + ' / project'
    workspaces = c.rh(meta, 'workspace', 'list')['workspaces']
    matches = [w for w in workspaces if w.get('label') == label]
    if len(matches) != 1:
        raise RuntimeError('Expected one project terminal workspace; inspect Herdr before attaching.')
    panes = c.rh(meta, 'pane', 'list', '--workspace', matches[0]['workspace_id'])['panes']
    if len(panes) != 1:
        raise RuntimeError('This workspace has multiple panes; select the intended one in Herdr.')
    return panes[0]


def prepare_repository(meta, profile, *, create_terminal=True):
    """Create the project shell's checkout once, preserving every existing branch and user pane."""
    progress.stage('repository', 'Preparing your project', 'Checking the saved checkout')
    with projects.project_lock(profile['name']):
        record = projects.PROJECTS / profile['name'] / 'shell.json'
        if record.exists():
            saved = json.loads(record.read_text())
            checkout = c.load(saved['task_id'])
            if (checkout.get('project') != profile['name'] or checkout.get('role') != 'shell'
                    or checkout.get('machine_id') != meta['machine_id']):
                raise ValueError('Project shell checkout record has an unexpected owner')
        else:
            task = 'shell-' + profile['name'] + '-' + uuid.uuid4().hex[:6]
            checkout = {'task_id': task, 'project': profile['name'], 'role': 'shell',
                'project_profile': profile, 'branch': 'box/' + task, 'phase': 'fetching',
                'base_repo': meta.get('base_repo', '/home/user/projects/' + profile['name'] + '/source'),
                **{k: meta[k] for k in ('machine_id', 'ssh_alias', 'ip', 'archive_after', 'herdr_profile_id') if k in meta}}
            c.save(checkout); projects.atomic(record, {'task_id': task})
        checkout.update(**{k: meta[k] for k in ('ssh_alias', 'ip', 'archive_after')})
        checkout['project_profile'] = profile
        checkout['session_interface'] = 'herdr' if create_terminal else 'ssh'
        if checkout['phase'] != 'shell-ready':
            progress.stage('repository', 'Preparing your project', 'Setting up the first checkout and coding tools')
            directory = c.STATE / 'tasks' / checkout['task_id']
            bundle = directory / 'source.bundle'
            if not checkout.get('base_sha'):
                sha, bundle, url = c.source_checkout(
                    profile['repository'], profile['base'], directory,
                    github=profile.get('github') if profile.get('coding_only') else None,
                    clean=profile.get('coding_only') is True)
                checkout.update(base_sha=sha, repository=url); c.save(checkout)
            c.configure_task(checkout, bundle, with_agent=False)
        access = repository_access.configure(c.remote, meta, checkout['cwd'], checkout['repository'], profile.get('github'),
                                             require_access=profile.get('coding_only') is True)
        if access['github_verified']:
            progress.note('GitHub access verified: ' + access['repository'])
        else:
            progress.note('GitHub access is not configured for ' + profile['name'] + '.')
        if create_terminal:
            label = profile['name'] + ' / project'
            workspaces = c.rh(meta, 'workspace', 'list')['workspaces']
            if not any(w.get('label') == label for w in workspaces):
                c.rh(meta, 'workspace', 'create', '--cwd', checkout['cwd'], '--label', label, '--no-focus')
            pane = terminal(meta, profile)
            c.rh(meta, 'workspace', 'focus', pane['workspace_id'])
        branch = c.remote(meta, shlex.join(['git', '-C', checkout['cwd'], 'branch', '--show-current'])).strip()
        progress.note('Repository: ' + checkout['cwd'])
        progress.note('Branch: ' + (branch or '(detached HEAD)'))
        return checkout


def login_project(profile, provider):
    """Repair one login on the owned running VM, without preparing other accounts."""
    if provider not in agent_auth.REMOTE_FILES:
        raise ValueError('Unsupported agent credential provider')
    if not agent_auth.config(c, profile):
        raise ValueError('This project has no agent account binding; use allset config guide to configure it')
    name = profile['name']
    # Hold the project operation lock through native sign-in, but release the
    # display before the interactive client owns the terminal.
    with contextlib.ExitStack() as stack:
        with progress.Progress(summary='Ready for ' + provider.title() + ' sign-in'):
            progress.stage('connection', 'Connecting to ' + name, 'Waiting for project access')
            stack.enter_context(projects.project_lock(name))
            try:
                meta = projects.machine(name)
                pointer = json.loads((projects.PROJECTS / name / 'machine.json').read_text())
            except FileNotFoundError:
                raise ValueError('No saved project machine; run allset ' + name + ' first') from None
            if (meta.get('project') != name or meta.get('role') != 'project'
                    or meta.get('task_id') != pointer.get('task_id')
                    or meta.get('machine_id') != pointer.get('machine_id')):
                raise ValueError('Saved machine ownership mismatch; no sign-in started')
            info = c.box('info', meta['machine_id'])['box']
            if info.get('id') != meta['machine_id']:
                raise ValueError('Box returned a different machine; no sign-in started')
            if info['state'] not in ('ready', 'idle', 'running'):
                raise ValueError('Project is not running; run allset ' + name + ' first, then retry sign-in')
            c.refresh_ssh(meta)
            projects.wait_project_filesystem(meta, timeout=0)
            binary = {'claude': 'claude', 'codex': 'codex', 'cursor': 'cursor-agent'}[provider]
            progress.stage('client', 'Checking ' + provider.title())
            if c.remote(meta, 'command -v ' + shlex.quote(binary) + ' >/dev/null && echo ready || true').strip() != 'ready':
                raise ValueError(provider.title() + ' is not installed on this Box; run allset ' + name + ' to prepare its tools')
        return agent_auth.login(c, meta, profile, provider)


def shell(name, ttl=7200, *, login_provider=None):
    """Attach to a persistent remote PTY without nesting the Herdr interface or starting an agent."""
    profile = projects.project(name)
    if login_provider:
        return login_project(profile, login_provider)
    if profile.get('agent_profile'):
        print('Agent account profile: ' + profile['agent_profile'], flush=True)
    meta = projects.open_project(name, ttl=ttl, create_terminal=False)
    prepare_repository(meta, profile)
    agent_auth.print_accounts(c, profile)
    pane = terminal(meta, profile)
    print('Remote terminal: ' + name + '. Choose your agent here. Detach with Ctrl+b, then q.', flush=True)
    argv = ['ssh', '-tt', meta['ssh_alias'], shlex.join([
        '/home/user/.local/bin/herdr', '--session', c.SESSION,
        'terminal', 'attach', pane['terminal_id']])]
    with agent_auth.monitor(c, meta, profile):
        return subprocess.call(argv)


def main(argv=None):
    """Keep every native Box command available; only registered project names become shortcuts."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == '--project':
        if len(args) < 2:
            raise ValueError('An explicit project name is required')
        # Go already resolved this project. A name such as "dashboard" must
        # never be reinterpreted as a native Box command by the old wrapper.
        name, args = args[1], args[1:]
    else:
        name = None if args and (args[0] in NATIVE_COMMANDS or args[0].startswith('-')) else resolve_project(args[0] if args else None)
    if name is None:
        if args and args[0] == '.':
            raise ValueError('This repository has no project profile yet; register it once with box-herdr project-add.')
        os.execv(c.BOX, [str(c.BOX), *args])
        return 0
    parser = argparse.ArgumentParser(prog='box ' + (args[0] if args else name),
                                     description='Open this project Box. Agent and app sign-ins stay project-specific.')
    parser.add_argument('--ttl', type=int, default=7200)
    parser.add_argument('--login', choices=('claude', 'codex', 'cursor'),
                        help='Complete and save one native agent sign-in, then return to Local')
    parsed = parser.parse_args(args[1:] if args else [])
    return shell(name, ttl=parsed.ttl, login_provider=parsed.login)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('allset: sign-in or connection interrupted; no VM stop requested', file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        print('allset:', str(error), file=sys.stderr)
        sys.exit(1)
