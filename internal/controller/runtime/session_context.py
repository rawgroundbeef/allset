"""Install client entry points that bind future processes to one project context."""

import json
import hashlib
import fcntl
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

BINARIES = {'codex': 'codex', 'claude': 'claude', 'cursor': 'cursor-agent'}
MARKER = '# allset project session context\n'


def _native_path(name, directory, previous=None):
    if previous and Path(previous).is_file() and os.access(previous, os.X_OK):
        return previous
    local_command = Path.home() / '.local/bin' / BINARIES[name]
    if local_command.is_symlink():
        target = local_command.resolve()
        if target.is_file() and os.access(target, os.X_OK):
            return str(target)
    if local_command.is_file() and os.access(local_command, os.X_OK) and MARKER not in local_command.read_text(errors='ignore'):
        saved = directory / 'native' / BINARIES[name]
        saved.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if saved.exists():
            raise ValueError('Saved native client path already exists: ' + str(saved))
        local_command.replace(saved)
        return str(saved)
    local = str(local_command.parent)
    search = os.pathsep.join(item for item in os.environ.get('PATH', '').split(os.pathsep) if item != local)
    result = shutil.which(BINARIES[name], path=search)
    if not result:
        raise ValueError(name + ' is not installed in the prepared environment')
    return result


def install(clients, infisical_binding, project, checkout, requirements):
    directory = Path.home() / '.local/share/allset/session' / project
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (directory / 'install.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    path = directory / 'context.json'
    old = json.loads(path.read_text()) if path.exists() else {}
    if old and (old.get('project'), old.get('checkout')) != (project, checkout):
        raise ValueError('Existing launch context belongs to another project or checkout')
    native = {name: _native_path(name, directory, old.get('native', {}).get(name)) for name in clients}
    revision = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    binding_revision = hashlib.sha256(json.dumps(infisical_binding, sort_keys=True).encode()).hexdigest()
    context = {'version': 1, 'project': project, 'checkout': checkout, 'native': native,
               'clients': clients, 'session_environment': requirements,
               'infisical': bool(infisical_binding), 'runtime_revision': revision,
               'binding_revision': binding_revision}
    commands = [Path.home() / '.local/bin' / BINARIES[client] for client in clients]
    if old == context and all(command.is_file() and MARKER in command.read_text(errors='ignore') for command in commands):
        return context
    for client in set(old.get('clients', ())) - set(clients):
        command = Path.home() / '.local/bin' / BINARIES[client]
        if command.exists() and MARKER not in command.read_text(errors='ignore'):
            raise ValueError('Removed client command has unmanaged edits: ' + str(command))
        if command.exists(): command.unlink()
    temporary = path.with_suffix('.tmp'); temporary.write_text(json.dumps(context, indent=2) + '\n')
    temporary.chmod(0o600); temporary.replace(path)
    source = Path(__file__).read_text()
    module = directory / 'session_context.py'
    temporary = module.with_suffix('.tmp'); temporary.write_text(source); temporary.chmod(0o600); temporary.replace(module)
    if infisical_binding:
        for name in ('infisical_context.py', 'profiles.py'):
            target = directory / name
            temporary = target.with_suffix('.tmp')
            temporary.write_text(Path(__file__).with_name(name).read_text()); temporary.chmod(0o600); temporary.replace(target)
        binding = directory / 'infisical-binding.json'
        temporary = binding.with_suffix('.tmp'); temporary.write_text(json.dumps(infisical_binding))
        temporary.chmod(0o600); temporary.replace(binding)
    for client in clients:
        command = Path.home() / '.local/bin' / BINARIES[client]
        if command.exists() and MARKER not in command.read_text(errors='ignore'):
            raise ValueError('Refusing to replace an unmanaged client command: ' + str(command))
        replacement = command.with_suffix('.allset-installing')
        replacement.write_text('#!/bin/sh\n' + MARKER + 'exec /usr/bin/python3 ' + shlex.quote(str(module)) +
                               ' ' + shlex.quote(client) + ' "$@"\n')
        replacement.chmod(0o755); replacement.replace(command)
    return context


def _secret_environment(context, client):
    requested = {name: item for name, item in context['session_environment'].items()
                 if client in (item.get('agents') or context['clients'])}
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('INFISICAL_') and key not in requested and key != 'TOKEN'}
    if not requested:
        return environment
    import infisical_context
    directory = Path(__file__).resolve().parent
    if not context.get('infisical'):
        raise ValueError('This session requires an Infisical binding')
    profile = json.loads((directory / 'infisical-binding.json').read_text())
    native = Path.home() / '.local/bin/infisical-native'
    auth_env = infisical_context.token_environment(profile, native)
    by_path = {}
    for name, requirement in requested.items(): by_path.setdefault(requirement['secret_path'], []).append((name, requirement['secret_key']))
    for secret_path, values in by_path.items():
        scope = profile['infisical']
        result = subprocess.run([str(native), 'export', '--format=json', '--silent', '--path=' + secret_path,
                                 '--projectId=' + scope['project_id'], '--env=' + scope['environment'],
                                 '--domain=' + scope['instance']],
                                env=auth_env, capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise ValueError('Scoped session secrets could not be fetched')
        document = json.loads(result.stdout)
        if isinstance(document, dict):
            available = document
        elif isinstance(document, list):
            available = {item.get('secretKey'): item.get('secretValue') for item in document if isinstance(item, dict)}
        else:
            raise ValueError('Scoped session secret response has an unsupported format')
        for variable, key in values:
            if key not in available: raise ValueError('A required scoped session secret is unavailable: ' + variable)
            environment[variable] = available[key]
    return environment


def main(client, args):
    os.umask(0o077)
    directory = Path(__file__).resolve().parent
    context = json.loads((directory / 'context.json').read_text())
    native = context['native'].get(client)
    if not native: raise ValueError('This client is not selected for the project')
    authentication = (client == 'codex' and args[:1] == ['login'] or
                      client == 'claude' and args[:2] in (['auth', 'login'], ['auth', 'status']) or
                      client == 'cursor' and args[:1] in (['login'], ['status']))
    if authentication:
        # SSH sign-in/status starts at home, not the checkout. Native auth needs
        # neither project secrets nor a conversation's working directory.
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith('INFISICAL_') and key != 'TOKEN'
                       and key not in context['session_environment']}
        os.execve(native, [native, *args], environment)
    if Path.cwd().resolve() != Path(context['checkout']).resolve() and Path(context['checkout']).resolve() not in Path.cwd().resolve().parents:
        raise ValueError('Run this configured client inside its owned project checkout')
    os.execve(native, [native, *args], _secret_environment(context, client))


if __name__ == '__main__':
    try:
        main(sys.argv[1], sys.argv[2:])
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else 'Session context could not be prepared.'
        print('allset session: ' + message, file=sys.stderr)
        raise SystemExit(1)
