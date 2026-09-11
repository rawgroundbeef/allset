"""Executable-only integration proof. No real provider, account or MCP server."""
import json
import os
from pathlib import Path
import pty
import select
import shutil
import subprocess
import tarfile
import time

home = Path('/home/user')
assert os.getuid() == 10001 and Path.home() == home
state = home / '.local/share/box-herdr'
project = state / 'projects/dashboard'
checkout = home / 'tasks/shell-dashboard'
cache = home / '.cache/allset/controller'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value) if not isinstance(value, str) else value)
    path.chmod(0o600)


def calls():
    path = home / 'calls.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def cli(*args, ok=True, contains=None, cwd=None, terminal=False, answers=None):
    master, slave = pty.openpty() if terminal else (None, None)
    try:
        if answers is not None:
            assert terminal
            os.write(master, answers.encode())
        result = subprocess.run(['allset', *args], stdin=slave, cwd=cwd,
                                capture_output=True, text=True, timeout=45)
    finally:
        if terminal:
            os.close(master)
            os.close(slave)
    output = result.stdout + result.stderr
    assert 'synthetic-access' not in output and 'synthetic-refresh' not in output
    # Dry-run contains bundled code; only print bounded output on failure.
    assert (result.returncode == 0) == ok, (args, result.returncode, output[-3000:])
    if contains:
        assert contains in output, (args, output[-3000:])
    return output


def cli_tty(*args):
    """Read a real terminal throughout execution, including the final redraw."""
    master, slave = pty.openpty()
    process = None
    output = bytearray()
    try:
        process = subprocess.Popen(['allset', *args], stdin=slave, stdout=slave, stderr=slave,
                                   env={**os.environ, 'TERM': 'xterm-256color'})
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                output.extend(os.read(master, 65536))
            elif process.poll() is not None:
                break
        else:
            raise AssertionError('TTY preparation timed out')
        text = output.decode()
        assert process.returncode == 0, text[-3000:]
        assert 'synthetic-access' not in text and 'synthetic-refresh' not in text
        return text
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
        os.close(slave)


for target in (home / '.ascii/bin/box', home / 'test-tools/ssh', home / 'test-tools/scp',
               state / 'bin/herdr', home / '.local/bin/herdr', home / 'test-tools/claude'):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile('/opt/checks/transport.py', target)
    target.chmod(0o700)

profile = {'version': 1, 'name': 'dashboard', 'repository': 'example/dashboard',
           'base': 'main', 'template': None, 'box_environment': 'fixture',
           'setup_commands': [], 'services': [], 'shell_only': True, 'agent_profile': 'fixture-account'}
write(project / 'profile.json', profile)
write(home / '.config/allset/config.json', {'version': 3, 'projects': [
    {'name': 'dashboard', 'repository': 'example/dashboard', 'backend': 'box',
     'mcps': {'docs': {'url': 'https://docs.example.test/mcp'}}}]})
owner = {'task_id': 'project-dashboard', 'project': 'dashboard', 'role': 'project',
         'machine_id': 'bx_saved', 'ssh_alias': 'box-herdr-bx_saved', 'ip': '127.0.0.1',
         'ssh_port': 2222, 'archive_after': None, 'box_state': 'ready', 'phase': 'running',
         'remote_state': '/home/user/.box-herdr/projects/dashboard'}
write(project / 'machine.json', {'task_id': owner['task_id'], 'machine_id': owner['machine_id']})
write(state / 'tasks/project-dashboard/task.json', owner)
write(project / 'shell.json', {'task_id': 'shell-dashboard'})
shell = {**owner, 'task_id': 'shell-dashboard', 'role': 'shell', 'phase': 'shell-ready',
         'cwd': str(checkout), 'repository': 'example/dashboard', 'branch': 'fixture-work',
         'remote_state': '/home/user/.box-herdr/tasks/shell-dashboard'}
write(state / 'tasks/shell-dashboard/task.json', shell)
write(home / 'box-state', 'ready')
source = home / 'fixtures/codex.json'
write(source, {'tokens': {'access_token': 'synthetic-access', 'refresh_token': 'synthetic-refresh'}})
write(state / 'agent-profiles/fixture-account/profile.json', {
    'name': 'fixture-account', 'providers': {'codex': {'credential_ref': str(source)},
                                          'claude': {'account_email': 'fixture@example.test'}}})
write(home / '.codex/config.toml', 'model = "fixture-model"\n')
checkout.mkdir(parents=True)
subprocess.run(['git', 'init', '--quiet', '--initial-branch=fixture-work', str(checkout)], check=True)
subprocess.run(['git', '-C', str(checkout), 'remote', 'add', 'origin', 'https://github.com/example/dashboard.git'], check=True)
write(checkout / 'tracked.txt', 'before\n')
subprocess.run(['git', '-C', str(checkout), 'add', 'tracked.txt'], check=True)
subprocess.run(['git', '-C', str(checkout), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
                'commit', '--quiet', '-m', 'Fixture base'], check=True)
shell['base_sha'] = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
write(state / 'tasks/shell-dashboard/task.json', shell)
write(checkout / 'tracked.txt', 'after\n')
write(checkout / 'uncommitted.txt', 'work survives\n')

assert not (state / 'controller').exists()
cli('--version')
cli('--help')
cli('config', 'validate')
inspection = json.loads(cli('config', 'show', 'dashboard'))
assert len(inspection['runtime_revision']) == 64
cli('doctor', 'dashboard', '--offline', '--json', ok=False)
cli('status', 'dashboard', '--cached', '--json')
cli('open', 'dashboard', '--attach', 'none', '--dry-run', '--json')
assert not cache.exists() and not calls(), 'Inspection executed or installed the controller'
print('PASS: inspection and dry-run leave runtime and providers untouched', flush=True)

unfamiliar = home / 'unfamiliar'
unfamiliar.mkdir()
subprocess.run(['git', 'init', '--quiet', str(unfamiliar)], check=True)
subprocess.run(['git', '-C', str(unfamiliar), 'remote', 'add', 'origin', 'https://github.com/example/unfamiliar.git'], check=True)
output = cli(cwd=unfamiliar, terminal=True, answers='\n\ninvalid\n', ok=False, contains='coding clients must uniquely select')
assert 'Coding tools' in output and 'Project name' in output and 'How would you like to continue?' not in output
assert json.loads((unfamiliar / '.allset').read_text())['name'] == 'unfamiliar'
assert not cache.exists() and not calls()
print('PASS: unfamiliar repo enters continuous onboarding; invalid private choices do not contact providers', flush=True)

assert not (checkout / '.allset').exists()
before_registry = (home / '.config/allset/config.json').read_bytes()
for answer in ('n\n', 'invalid\nn\n'):
    cli(cwd=checkout, terminal=True, answers=answer, ok=False, contains='left unchanged')
    assert not (checkout / '.allset').exists() and not cache.exists() and not calls()
assert not (home / '.codex/auth.json').exists(), 'Cancelled setup touched an agent login'
output = cli('--attach', 'none', cwd=checkout, terminal=True, answers='y\n', contains='Workspace prepared')
manifest = json.loads((checkout / '.allset').read_text())
assert manifest['name'] == 'dashboard' and manifest['repository'] == 'example/dashboard'
assert manifest['mcps']['docs']['url'] == 'https://docs.example.test/mcp'
before_manifest = (checkout / '.allset').read_bytes()
before_init_calls = len(calls())
cli('init', cwd=checkout, terminal=True, answers='y\n', contains='Project binding verified')
assert len(calls()) == before_init_calls, 'Replaying setup contacted a provider'
assert 'Set up this project' in output and 'How would you like to continue?' not in output
assert 'Preparing your project' in output and 'Preparing your MCP settings' in output
assert 'changed_files' not in output, 'Startup dumped raw MCP protocol output'
assert (checkout / '.allset').read_bytes() == before_manifest
assert (home / '.config/allset/config.json').read_bytes() == before_registry
print('PASS: compact setup confirms/cancels safely and continues with concise phases', flush=True)
assert cache.is_dir() and not (state / 'controller').exists()
assert json.loads((home / '.codex/auth.json').read_text()) == json.loads(source.read_text())
assert 'fixture-model' in (home / '.codex/config.toml').read_text()
assert 'https://docs.example.test/mcp' in (home / '.codex/config.toml').read_text()
assert (home / '.codex/auth.json').stat().st_mode & 0o077 == 0
assert not any(c['tool'] == 'herdr' for c in calls())
print('PASS: bundled preparation, synthetic login restore and native MCP projection', flush=True)

tty_output = cli_tty('connect', 'dashboard', '--attach', 'none')
assert '\r\x1b[2K' in tty_output and 'Workspace prepared' in tty_output
assert 'Preparing your MCP settings' in tty_output and 'saved login' in tty_output
assert 'changed_files' not in tty_output
assert tty_output.rstrip().endswith('Connect: allset connect dashboard')
print('PASS: packaged startup animates in a terminal and stops before its final handoff', flush=True)

before = len(calls())
before_codex = (home / '.codex/auth.json').read_bytes()
before_cache = (state / 'credentials/dashboard/agents/codex.json').read_bytes()
before_source = source.read_bytes()
write(home / '.claude/.credentials.json', {'mcpOAuth': {'fixture': 'preserve-mcp-login'}})
cli('config', 'claude', cwd=checkout, terminal=True, contains='claude login saved for dashboard as fixture@example.test')
assert (home / '.codex/auth.json').read_bytes() == before_codex
assert (state / 'credentials/dashboard/agents/codex.json').read_bytes() == before_cache
assert source.read_bytes() == before_source
assert (checkout / '.allset').read_bytes() == before_manifest
assert (home / '.config/allset/config.json').read_bytes() == before_registry
selected = json.loads((state / 'credentials/dashboard/agents/claude.json').read_text())
assert set(selected['contents']) == {'claudeAiOauth'}
assert json.loads((home / '.claude/.credentials.json').read_text())['mcpOAuth'] == {'fixture': 'preserve-mcp-login'}
assert not any(c['tool'] == 'herdr' or c['operation'] == 'bootstrap' for c in calls()[before:])
assert [c['operation'] for c in calls()[before:] if c['tool'] == 'box'] == ['info', 'info']
assert [c['operation'] for c in calls()[before:] if c['tool'] == 'claude'] == ['auth login', 'auth status']
print('PASS: project-local Claude sign-in verifies and caches only Claude; other logins, MCP auth and project files survive', flush=True)

# Poison the old path after the first run: it must never become an import source.
write(state / 'controller/projects.py', "raise RuntimeError('PRIVATE CONTROLLER EXECUTED')\n")
cli('connect', 'dashboard', '--attach', 'workspace', contains='Herdr workspace ready: dashboard.')
mcp_before = (home / '.codex/config.toml').read_bytes()
cli('connect', 'dashboard', '--attach', 'workspace', contains='Herdr workspace ready: dashboard.')
assert (home / '.codex/config.toml').read_bytes() == mcp_before
assert sum(c['operation'] == 'workspace-create' for c in calls()) == 1
assert sum(c['operation'] == 'machine-add' for c in calls()) == 1
assert (checkout / 'uncommitted.txt').read_text() == 'work survives\n'
assert subprocess.check_output(['git', '-C', str(checkout), 'branch', '--show-current'], text=True).strip() == 'fixture-work'
assert {c['operation'] for c in calls() if c['tool'] == 'box'} == {'info'}
print('PASS: native workspace created once and reused; branch and work preserved', flush=True)

before_index = subprocess.check_output(['git', '-C', str(checkout), 'ls-files', '--stage'])
cli('collect', 'dashboard')
results, = (state / 'tasks/shell-dashboard/results').iterdir()
assert '+after' in (results / 'working-tree.patch').read_text()
with tarfile.open(results / 'untracked.tar.gz') as archive:
    assert archive.extractfile('uncommitted.txt').read() == b'work survives\n'
assert subprocess.check_output(['git', '-C', str(checkout), 'ls-files', '--stage']) == before_index
assert (checkout / 'tracked.txt').read_text() == 'after\n'
print('PASS: bundled collection recovers tracked/untracked work without changing the index', flush=True)

write(home / 'box-state', 'stopped')
before = len(calls())
cli('config', 'claude', cwd=checkout, terminal=True, ok=False, contains='not running')
assert all(c['tool'] == 'box' and c['operation'] == 'info' for c in calls()[before:])
cli('connect', 'dashboard', '--attach', 'workspace', ok=False, contains='not running')
assert all(c['tool'] == 'box' and c['operation'] == 'info' for c in calls()[before:])
write(home / 'box-state', 'ready')
write(state / 'tasks/shell-dashboard/task.json', {**shell, 'project': 'different'})
before = len(calls())
cli('connect', 'dashboard', '--attach', 'workspace', ok=False, contains='ownership')
assert not any(c['tool'] == 'herdr' for c in calls()[before:])
write(project / 'profile.json', {**profile, 'repository': 'example/different'})
before = len(calls())
cli('open', 'dashboard', '--attach', 'none', ok=False, contains='repository binding changed')
assert len(calls()) == before
(project / 'profile.json').unlink()
cli('open', 'dashboard', '--attach', 'none', terminal=True, answers='invalid\n', ok=False,
    contains='coding clients must uniquely select')
assert len(calls()) == before
print('PASS: stopped and foreign bindings fail; invalid missing-profile choices do not provision or fall back', flush=True)
print('Container proof passed. Cloud services, network, real sign-ins and VM restoration were simulated.', flush=True)
