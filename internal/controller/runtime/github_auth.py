"""Bind a project VM to an explicitly selected native GitHub CLI account."""

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import sys


RAM_ROOT = Path("/run/allset-github")

def validate(binding):
    """Accept supported providers and a named local account, never inline tokens."""
    if binding == {'provider': 'box'}:
        return binding
    if (not isinstance(binding, dict) or set(binding) != {'provider', 'account_login'}
            or binding['provider'] != 'github-cli'
            or not isinstance(binding['account_login'], str)
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', binding['account_login'])):
        raise ValueError('GitHub binding requires Box or github-cli with an explicit account_login; no credentials inline.')
    return binding


def clean_environment():
    """Do not let ambient tokens or GitHub debug logging override the named account."""
    return {key: value for key, value in os.environ.items() if key not in {
        'GH_TOKEN', 'GITHUB_TOKEN', 'GH_ENTERPRISE_TOKEN', 'GITHUB_ENTERPRISE_TOKEN',
        'GH_DEBUG', 'DEBUG', 'GH_HOST', 'GH_REPO', 'GH_CONFIG_DIR'}}


def run_native(argv, *, env, data=None):
    """Withhold native output on auth failures; it may contain credentials."""
    try:
        result = subprocess.run(argv, input=data, env=env, capture_output=True, text=True, timeout=40)
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError('GitHub account validation could not finish; existing context preserved.') from None
    if result.returncode:
        raise ValueError('GitHub authentication or repository access failed for the configured account; native output withheld.')
    return result.stdout.strip()


def verify_account(binary, env, login, repository):
    """Verify real GitHub identity and repository permission without modifying either."""
    actual = run_native([binary, 'api', '--hostname', 'github.com', 'user', '--jq', '.login'], env=env)
    if actual.lower() != login.lower():
        raise ValueError('GitHub credential belongs to a different account; existing context preserved.')
    actual_repo = run_native([binary, 'api', '--hostname', 'github.com', 'repos/' + repository,
                             '--jq', '.full_name'], env=env)
    if actual_repo.lower() != repository.lower():
        raise ValueError('GitHub repository identity does not match this project.')


def stage(controller, meta, profile):
    """Supply one pinned local account over SSH stdin, only to its assigned project VM."""
    binding = profile.get('github')
    if not binding:
        return
    validate(binding)
    if binding['provider'] == 'box':
        return
    if meta.get('project') != profile['name'] or meta.get('role') != 'project':
        raise ValueError('GitHub target does not belong to this project.')
    from repository_access import github_repository
    repository = github_repository(profile['repository'])
    from profiles import identifier
    identifier(profile['name'])
    env = clean_environment()
    # --user selects an existing native account without switching the Mac's login.
    token = run_native(['gh', 'auth', 'token', '--hostname', 'github.com', '--user', binding['account_login']], env=env)
    if not token or any(ch.isspace() for ch in token):
        raise ValueError('The configured GitHub account has no usable native credential.')
    verify_account('gh', {**env, 'GH_TOKEN': token}, binding['account_login'], repository)
    target = '/home/user/.box-herdr/github_auth.py'
    controller.write_remote(meta, target, Path(__file__).read_text())
    script = ('import json,sys;sys.path.insert(0,"/home/user/.box-herdr");'
              'from github_auth import install;install(json.load(sys.stdin))')
    request = {'project': profile['name'], 'account_login': binding['account_login'],
               'repository': repository, 'token': token}
    result = controller.command(controller.ssh_args(meta) + [shlex.join(['python3', '-c', script])],
                                data=json.dumps(request), timeout=150, check=False)
    if result.returncode:
        raise ValueError('Project GitHub credential setup failed; remote output withheld. Reconcile this same project before retrying.')
    import progress
    progress.note('GitHub account: ' + binding['account_login'] + ' (' + profile['name'] + ')')


def private_directory(path):
    """Reject symlinks and shared or foreign runtime directories before writing secrets."""
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if path.is_symlink() or not path.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('GitHub runtime directory is not private; existing files preserved.')


def install(request):
    """Use native headless gh authentication from RAM without touching other logins."""
    name = request['project']
    if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,29}', name):
        raise ValueError('Invalid project name')
    validate({'provider': 'github-cli', 'account_login': request['account_login']})
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*', request['repository']):
        raise ValueError('Invalid project repository')
    filesystem = subprocess.check_output(['findmnt', '-n', '-o', 'FSTYPE', '-T', str(RAM_ROOT.parent)], text=True).strip()
    if filesystem != 'tmpfs':
        raise ValueError('GitHub credentials require RAM-backed /run.')
    if not RAM_ROOT.exists() and not RAM_ROOT.is_symlink():
        subprocess.run(['sudo', '-n', 'install', '-d', '-m', '700', '-o', str(os.getuid()),
                        '-g', str(os.getgid()), str(RAM_ROOT)], capture_output=True, check=True)
    private_directory(RAM_ROOT)
    parent = RAM_ROOT / name
    private_directory(parent)
    context = parent / 'github'
    private_directory(context)
    wrapper = Path.home() / '.local/bin/gh'
    marker = '# allset project GitHub: ' + name + ' account: ' + request['account_login']
    body = ('#!/bin/sh\n' + marker + '\nexec /usr/bin/python3 '
            '/home/user/.box-herdr/github_auth.py --dispatch ' + shlex.quote(name) + ' '
            + shlex.quote(request['account_login']) + ' "$@"\n')
    previous_body = ('#!/bin/sh\n' + marker + '\n'
            'unset GH_TOKEN GITHUB_TOKEN GH_ENTERPRISE_TOKEN GITHUB_ENTERPRISE_TOKEN GH_DEBUG DEBUG GH_HOST GH_REPO\n'
            'export GH_CONFIG_DIR=' + shlex.quote(str(context)) + '\n'
            'exec /usr/bin/gh "$@"\n')
    if wrapper.is_symlink() or (wrapper.exists() and wrapper.read_text() not in (body, previous_body)):
        raise ValueError('Existing gh dispatcher has another owner; left unchanged.')
    for part in (wrapper.parent, wrapper.parent.parent):
        if part.is_symlink() or part.stat().st_uid != os.getuid() or part.stat().st_mode & 0o022:
            raise ValueError('GitHub dispatcher parent is not an owned directory.')
    target = context / 'credential.json'
    if target.is_symlink() or (target.exists() and (not target.is_file() or target.stat().st_mode & 0o077)):
        raise ValueError('Existing GitHub credential file is not private.')
    token = request['token']
    if not isinstance(token, str) or not token or any(ch.isspace() for ch in token):
        raise ValueError('Invalid GitHub credential')
    # Native headless GH_TOKEN takes precedence over Box-injected gh logins.
    # Verify before the atomic replacement so failed refreshes preserve working auth.
    env = {**clean_environment(), 'GH_CONFIG_DIR': str(context), 'GH_TOKEN': token, 'GH_PROMPT_DISABLED': '1'}
    verify_account('/usr/bin/gh', env, request['account_login'], request['repository'])
    previous_mask = os.umask(0o077)
    try:
        atomic_file(target, json.dumps(request), 0o600)
        atomic_file(wrapper, body, 0o755)
    finally:
        os.umask(previous_mask)


def atomic_file(path, contents, mode):
    """Keep incomplete credentials and executable dispatchers invisible to concurrent readers."""
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(contents)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def dispatch(name, login, args):
    """Make ordinary gh use only this project's RAM credential through supported GH_TOKEN."""
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,29}', name):
        raise ValueError('Invalid project name')
    path = RAM_ROOT / name / 'github/credential.json'
    info = path.lstat()
    if path.is_symlink() or not path.is_file() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('GitHub credential is unavailable; reopen this project with allset.')
    request = json.loads(path.read_text())
    if (request.get('project'), request.get('account_login')) != (name, login):
        raise ValueError('GitHub account binding mismatch; existing context preserved.')
    env = {**clean_environment(), 'GH_CONFIG_DIR': str(path.parent), 'GH_TOKEN': request['token']}
    os.execve('/usr/bin/gh', ['gh', *args], env)


if __name__ == '__main__':
    try:
        if len(sys.argv) < 4 or sys.argv[1] != '--dispatch':
            raise ValueError('Use the project gh command.')
        dispatch(sys.argv[2], sys.argv[3], sys.argv[4:])
    except (OSError, ValueError, KeyError):
        print('Project GitHub credential is unavailable or invalid; reopen this project with allset.', file=sys.stderr)
        sys.exit(1)
