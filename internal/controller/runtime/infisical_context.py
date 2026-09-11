#!/usr/bin/env python3
"""Bind ordinary Infisical commands to one project without changing agent processes."""

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import uuid

from profiles import check_token, credential, identifier

# /dev is replaced inside Codex's Linux sandbox; /run remains readable.
# Staging verifies tmpfs before any credential is transferred.
RAM_ROOT = Path('/run/box-herdr')


def prepare_runtime():
    """Require volatile storage and a private user-owned runtime directory before staging."""
    filesystem = subprocess.check_output(
        ['findmnt', '-n', '-o', 'FSTYPE', '-T', str(RAM_ROOT if RAM_ROOT.exists() else RAM_ROOT.parent)],
        text=True).strip()
    if filesystem != 'tmpfs':
        raise ValueError('Project authentication requires RAM-backed /run; no credential was written.')
    if not RAM_ROOT.exists() and not RAM_ROOT.is_symlink():
        subprocess.run(['sudo', '-n', 'install', '-d', '-m', '700', '-o', str(os.getuid()),
                        '-g', str(os.getgid()), str(RAM_ROOT)], check=True, capture_output=True)
    info = RAM_ROOT.lstat()
    if RAM_ROOT.is_symlink() or not RAM_ROOT.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Project authentication runtime directory is not private; existing files preserved.')


def stage(controller, meta, profile, value=None):
    """Replace only this project's RAM credential atomically, respecting an explicit logout."""
    name = identifier(profile['name'])
    ready = controller.remote(meta, 'test ! -f /home/user/.box-herdr/infisical/logged-out && echo ready || echo logged-out').strip()
    if ready != 'ready':
        raise ValueError('Infisical is logged out for ' + name + '; complete its auth-login and auth-capture first.')
    auth = credential(profile) if value is None else value
    script = "import sys;sys.path.insert(0,'/home/user/.box-herdr/infisical');from infisical_context import prepare_runtime;prepare_runtime()"
    controller.remote(meta, shlex.join(['python3', '-c', script]))
    target = str(RAM_ROOT / name / 'auth.json')
    temporary = target + '.next-' + uuid.uuid4().hex
    controller.write_remote(meta, temporary, json.dumps(auth))
    controller.remote(meta, shlex.join(['mv', '-f', temporary, target]))


def binding(profile):
    """Keep only public identity and scope metadata on the project filesystem."""
    return {'name': profile['name'], 'infisical': {
        key: profile['infisical'][key] for key in
        ('instance', 'organization_id', 'project_id', 'principal_id', 'environment', 'user_email')
        if key in profile['infisical']}}


def verify_sandbox_access(controller, meta, profile):
    """Exercise the installed Codex sandbox's credential read without printing any contents."""
    target = str(RAM_ROOT / identifier(profile['name']) / 'auth.json')
    probe = 'from pathlib import Path;Path(' + repr(target) + ').open("rb").read(1)'
    command = 'cd /home/user && ' + shlex.join(['codex', 'sandbox', '--', 'python3', '-c', probe])
    try:
        controller.remote(meta, command, timeout=30)
    except RuntimeError:
        raise ValueError('Project credential was staged but Codex sandbox access failed; inspect the runtime mount before starting work.') from None


def configure(controller, meta, profile):
    """Install the dispatcher and supply this project's valid credential in RAM on every open."""
    if not profile.get('infisical'):
        return
    directory = '/home/user/.box-herdr/infisical'
    for name in ('infisical_context.py', 'profiles.py'):
        controller.write_remote(meta, directory + '/' + name, Path(__file__).with_name(name).read_text())
    value = binding(profile)
    # The public binding is checked remotely before changing any existing context.
    script = ('import sys,json;sys.path.insert(0,' + repr(directory) + ');'
              'from infisical_context import install;install(' + repr(value) + ')')
    controller.remote(meta, shlex.join(['python3', '-c', script]))
    logged_out = controller.remote(meta, 'test ! -f ' + directory + '/logged-out && echo ready || echo logged-out').strip()
    if logged_out == 'logged-out':
        print('Infisical: explicitly logged out for ' + profile['name'] + '; use box-herdr auth-login ' + profile['name'] + '.', flush=True)
        return
    try:
        auth = credential(profile)
    except (ValueError, OSError):
        print('Infisical: ' + profile['name'] + ' needs credential refresh; use box-herdr auth-login ' + profile['name'] + '.', flush=True)
        return
    stage(controller, meta, profile, auth)
    verify_sandbox_access(controller, meta, profile)
    label = value['infisical'].get('user_email', value['infisical']['principal_id'])
    print('Infisical profile: ' + profile['name'] + ' → ' + label, flush=True)


def install(profile):
    """Atomically select a dispatcher while retaining the original signed CLI executable."""
    directory = Path.home() / '.box-herdr/infisical'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / 'binding.json'
    if path.exists() and json.loads(path.read_text()) != profile:
        raise ValueError('This Box already has a different Infisical project binding; existing context preserved.')
    binary = Path.home() / '.local/bin/infisical'
    native = binary.with_name('infisical-native')
    marker = '# box-herdr project Infisical dispatcher'
    with binary.open('rb') as stream:
        head = stream.read(512)
    if head.startswith(b'\x7fELF'):
        binary.replace(native)
    elif marker.encode() not in head or not native.is_file():
        raise ValueError('Unrecognized Infisical executable; inspect before replacing it.')
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(profile)); temp.chmod(0o600); temp.replace(path)
    replacement = binary.with_name('infisical.installing')
    replacement.write_text('#!/bin/sh\n' + marker + '\nexec /usr/bin/python3 ' +
                           shlex.quote(str(directory / 'infisical_context.py')) + ' "$@"\n')
    replacement.chmod(0o755); replacement.replace(binary)


def scoped_arguments(profile, args):
    """Pin project and instance while preserving explicit environments, paths and child argv."""
    split = args.index('--') if '--' in args else len(args)
    flags, child = args[:split], args[split:]
    auth = profile['infisical']
    command = next((arg for arg in flags if arg in
                   ('run', 'export', 'secrets', 'login', 'logout', 'user', 'vault', 'init', 'reset')), None)
    seen = set()
    expected = {'--domain': auth['instance'], '--projectId': auth['project_id'],
                '--organization-id': auth['organization_id']}
    for index, arg in enumerate(flags):
        key, equals, value = arg.partition('=')
        if key == '--token':
            raise ValueError('This Box uses its project credential; explicit token overrides are not accepted.')
        if key not in expected:
            continue
        if not equals:
            if index + 1 >= len(flags):
                raise ValueError('Missing value for ' + key)
            value = flags[index + 1]
        actual = value.rstrip('/').removesuffix('/api') if key == '--domain' else value
        wanted = expected[key].rstrip('/').removesuffix('/api') if key == '--domain' else expected[key]
        if actual != wanted:
            raise ValueError('Infisical ' + key + ' does not match this project; use the other project Box.')
        seen.add(key)
    if '--domain' not in seen:
        flags += ['--domain=' + auth['instance']]
    if command in ('run', 'export', 'secrets') and '--projectId' not in seen:
        flags += ['--projectId=' + auth['project_id']]
    if command in ('run', 'export', 'secrets') and not any(
            a in ('--env', '-e') or a.startswith(('--env=', '-e=')) or
            (a.startswith('-e') and not a.startswith('--') and len(a) > 2) for a in flags):
        flags += ['--env=' + auth['environment']]
    return command, flags + child


def token_environment(profile, native, environ=None):
    """Read the current RAM credential per invocation; never put credentials in argv or output."""
    name = identifier(profile['name'])
    path = RAM_ROOT / name / 'auth.json'
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError('Project credential is not accessible to this process; reopen box ' + name + ' from your Local terminal.')
    auth = json.loads(path.read_text())
    env = {k: v for k, v in (os.environ if environ is None else environ).items()
           if not k.startswith('INFISICAL_') and k != 'TOKEN'}
    env.update(INFISICAL_DOMAIN=profile['infisical']['instance'], INFISICAL_DISABLE_UPDATE_CHECK='true')
    if auth['method'] == 'user-token':
        token = auth['token']
    elif auth['method'] == 'universal-auth':
        login_env = {**env, 'INFISICAL_UNIVERSAL_AUTH_CLIENT_ID': auth['client_id'],
                     'INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET': auth['client_secret']}
        result = subprocess.run([str(native), 'login', '--method=universal-auth', '--plain', '--silent'],
                                env=login_env, capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise ValueError('Project machine identity authentication failed; check its credential and permissions.')
        token = result.stdout.strip()
    else:
        raise ValueError('Unsupported project authentication method')
    check_token(profile, token)
    env['INFISICAL_TOKEN'] = token
    return env


def main():
    """Run the native CLI with project authentication; native human sign-in remains available."""
    os.umask(0o077)
    directory = Path(__file__).resolve().parent
    profile = json.loads((directory / 'binding.json').read_text())
    native = Path.home() / '.local/bin/infisical-native'
    args = sys.argv[1:]
    head = args[:args.index('--')] if '--' in args else args
    if not args or any(arg in ('--version', '--help', '-h') for arg in head):
        os.execv(str(native), [str(native), *args])
    command, args = scoped_arguments(profile, args)
    if command == 'logout':
        (directory / 'logged-out').touch(mode=0o600)
        (RAM_ROOT / identifier(profile['name']) / 'auth.json').unlink(missing_ok=True)
    if command in ('user', 'vault', 'init', 'reset', 'logout') or (command == 'login' and 'status' not in head):
        env = {k: v for k, v in os.environ.items() if not k.startswith('INFISICAL_') and k != 'TOKEN'}
        env['INFISICAL_DOMAIN'] = profile['infisical']['instance']
    else:
        if (directory / 'logged-out').exists():
            raise ValueError('This project is logged out; use box-herdr auth-login ' + profile['name'] + ' from Local.')
        env = token_environment(profile, native)
    if command == 'login' and 'status' in head and '--json' not in head:
        print('Project: ' + profile['name'] + ' | Configured Infisical account: ' +
              profile['infisical'].get('user_email', profile['infisical']['principal_id']), flush=True)
    os.execve(str(native), [str(native), *args], env)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Only fixed diagnostics leave the dispatcher; never echo native auth output or argv.
        message = str(error) if isinstance(error, ValueError) else 'Project authentication could not be loaded.'
        print('Infisical project context: ' + message, file=sys.stderr)
        sys.exit(1)
