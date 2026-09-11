"""Restore and save explicitly bound project agent logins over private SSH streams."""

import contextlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading

from agent_credentials import has_login, login_contents

# Only provider login files are transferred; configurations, prompts and repositories are excluded.
REMOTE_FILES = {'codex': '.codex/auth.json', 'claude': '.claude/.credentials.json',
                'cursor': '.config/cursor/auth.json'}


def login_command(provider, binding):
    """Use the provider's native browser flow, with only a configured email hint."""
    if provider == 'claude':
        args = ['claude', 'auth', 'login', '--claudeai']
        email = binding.get('providers', {}).get(provider, {}).get('account_email')
        if email:
            args += ['--email', email]
        return args
    if provider == 'codex':
        return ['codex', 'login']
    if provider == 'cursor':
        return ['env', 'NO_OPEN_BROWSER=1', 'cursor-agent', 'login']
    raise ValueError('Unsupported agent credential provider')


def private_write(path, value):
    """Atomically replace a credential file that is private from its first byte."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + '.tmp-' + str(os.getpid()) + '-' + str(threading.get_ident()))
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle: json.dump(value, handle)
    os.replace(temp, path)


def read_private(path):
    """Refuse public or symlinked cache files before reading their contents."""
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError('Agent credential reference must be a private regular file: ' + str(path))
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Unexpectedly large agent credential file')
    return json.loads(path.read_text())


def config(controller, profile):
    """Read the named agent profile without falling back to the laptop's active login."""
    name = profile.get('agent_profile')
    if not name: return None
    path = controller.STATE / 'agent-profiles' / name / 'profile.json'
    value = json.loads(path.read_text())
    if value.get('name') != name:
        raise ValueError('Agent profile name does not match its registry entry')
    if set(value.get('providers', {})) - REMOTE_FILES.keys():
        raise ValueError('Unsupported agent credential provider')
    return value


def cache_path(controller, profile, provider):
    """Give each project a separate refresh cache even when its account profile is shared."""
    return controller.STATE / 'credentials' / profile['name'] / 'agents' / (provider + '.json')


def exchange(controller, meta, request):
    """Send credentials on stdin and consume them privately, never through argv or errors."""
    script = Path(__file__).with_name('agent_credentials.py').read_text() + '''
import json,os,sys,uuid
from pathlib import Path
r=json.load(sys.stdin);out={}
for name,item in r['files'].items():
 p=Path('/home/user')/item['path']
 if p.is_symlink() or p.parent.is_symlink(): raise SystemExit(2)
 if r['action']=='read':
  if p.is_file():
   if p.stat().st_size>1048576: raise SystemExit(2)
   value=json.loads(p.read_text())
   if has_login(name,value): out[name]=login_contents(name,value)
 elif r['action']=='restore':
  p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  before=p.read_bytes() if p.exists() else None
  existing=json.loads(before) if before is not None else {}
  if has_login(name,existing): out[name]='kept';continue
  contents=login_contents(name,item['contents'])
  if not has_login(name,contents): out[name]='missing';continue
  # A Claude file can also hold this Box's MCP logins. Preserve those in place.
  updated={**existing,**contents} if name=='claude' else contents
  temporary=p.with_name(p.name+'.restore-'+uuid.uuid4().hex)
  fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f: json.dump(updated,f)
  if (p.read_bytes() if p.exists() else None)!=before:
   temporary.unlink();out[name]='changed';continue
  os.replace(temporary,p)
  out[name]='restored'
 else: raise SystemExit(2)
print(json.dumps(out))
'''
    result = controller.command(controller.ssh_args(meta) + [shlex.join(['python3', '-c', script])],
                                data=json.dumps(request), timeout=30, check=False)
    if result.returncode:
        raise RuntimeError('Project agent credential transfer failed; credential contents withheld')
    return json.loads(result.stdout)


def restore(controller, meta, profile):
    """Restore missing or empty native logins; preserve live credentials and explicit logout."""
    binding = config(controller, profile)
    if not binding: return
    if meta.get('project') != profile['name']:
        raise ValueError('Refusing to send agent credentials to a different project Box')
    files = {}
    for provider in REMOTE_FILES:
        cache = cache_path(controller, profile, provider)
        if cache.exists():
            saved = read_private(cache)
            if (saved.get('project'), saved.get('profile'), saved.get('provider')) != (
                    profile['name'], binding['name'], provider):
                raise ValueError('Agent credential cache belongs to a different project or profile')
            if saved.get('logged_out') or saved.get('needs_login'): continue
            contents = saved['contents']
        elif binding.get('providers', {}).get(provider, {}).get('credential_ref'):
            source = Path(binding['providers'][provider]['credential_ref']).expanduser()
            contents = read_private(source)
        else:
            continue
        if has_login(provider, contents):
            files[provider] = {'path': REMOTE_FILES[provider], 'contents': login_contents(provider, contents)}
    if files:
        restored = exchange(controller, meta, {'action': 'restore', 'files': files})
        for provider, status in restored.items():
            if status == 'restored':
                private_write(cache_path(controller, profile, provider), {'project': profile['name'],
                    'profile': binding['name'], 'provider': provider, 'contents': files[provider]['contents']})


def capture(controller, meta, profile, providers=None, *, authenticated=False):
    """Save this Box's current logins into its own cache; do not update shared account sources."""
    binding = config(controller, profile)
    if not binding: return
    if meta.get('project') != profile['name']:
        raise ValueError('Refusing to capture agent credentials from a different project Box')
    selected = set(REMOTE_FILES) if providers is None else set(providers)
    if selected - REMOTE_FILES.keys():
        raise ValueError('Unsupported agent credential provider')
    contents = exchange(controller, meta, {'action': 'read',
        'files': {name: {'path': REMOTE_FILES[name]} for name in selected}})
    for provider, value in contents.items():
        path = cache_path(controller, profile, provider)
        previous = read_private(path) if path.exists() else {}
        needs_login = bool(previous.get('needs_login') and previous.get('contents') == value and not authenticated)
        private_write(cache_path(controller, profile, provider), {'project': profile['name'],
            'profile': binding['name'], 'provider': provider, 'contents': value, 'needs_login': needs_login})
    for provider in selected - contents.keys():
        cache = cache_path(controller, profile, provider)
        if cache.exists():
            private_write(cache, {'project': profile['name'], 'profile': binding['name'],
                'provider': provider, 'logged_out': True})


def require_login(controller, profile, provider):
    """Record a confirmed provider rejection so opening a Box does not restore the same bad login."""
    path = cache_path(controller, profile, provider)
    value = read_private(path)
    value['needs_login'] = True
    private_write(path, value)


def print_accounts(controller, profile):
    """Show saved account bindings without claiming that cached tokens passed a live request."""
    binding = config(controller, profile)
    if not binding:
        return
    for provider in ('codex', 'claude', 'cursor'):
        path = cache_path(controller, profile, provider)
        cached = read_private(path) if path.exists() else {}
        selected = binding.get('providers', {}).get(provider, {})
        label = selected.get('account_email', binding['name'])
        state = 'saved login' if has_login(provider, cached.get('contents')) else 'sign-in needed'
        if cached.get('logged_out') or cached.get('needs_login'):
            state = 'sign-in needed'
        print(provider + ': ' + label + ' — ' + state, flush=True)


def login(controller, meta, profile, provider):
    """Run one native sign-in, then immediately save only that project's selected provider."""
    binding = config(controller, profile)
    if not binding:
        raise ValueError('This project has no agent account profile configured')
    if meta.get('project') != profile['name']:
        raise ValueError('Refusing to sign in on a different project Box')
    print('Sign in to ' + provider + ' for ' + profile['name'] + ' (' + binding['name'] + ').', flush=True)
    print('Open the link in your local browser. Use the account for this project.', flush=True)
    args = ['ssh', '-tt']
    if provider == 'codex':
        # Native browser auth works for organizations that disable device codes.
        args += ['-o', 'ExitOnForwardFailure=yes', '-L', '127.0.0.1:1455:127.0.0.1:1455']
    args += [meta['ssh_alias'], shlex.join(login_command(provider, binding))]
    result = subprocess.call(args)
    if result == 0:
        identity = native_identity(controller, meta, provider)
        expected = binding.get('providers', {}).get(provider, {}).get('account_email')
        if not identity.get('logged_in') or not identity.get('email'):
            raise RuntimeError('Could not verify the signed-in account; login was not cached.')
        if expected and identity['email'].casefold() != expected.casefold():
            raise RuntimeError('Signed in as ' + identity['email'] + ', but this project expects ' + expected +
                               '. Repeat the native sign-in with the intended account; login was not cached.')
        capture(controller, meta, profile, [provider], authenticated=True)
        path = cache_path(controller, profile, provider)
        saved = read_private(path) if path.exists() else {}
        if not has_login(provider, saved.get('contents')):
            raise RuntimeError('Sign-in ended without a saved provider credential; inspect the native login result.')
        print(provider + ' login saved for ' + profile['name'] + ' as ' + identity['email'] + '.', flush=True)
    return result


def native_identity(controller, meta, provider):
    """Read only public identity from native status; tokens and raw provider output stay remote."""
    if provider not in REMOTE_FILES:
        raise ValueError('Unsupported agent credential provider')
    script = '''import base64,json,re,subprocess,sys
from pathlib import Path
provider=sys.argv[1]
commands={'claude':['claude','auth','status'],'codex':['codex','login','status'],'cursor':['cursor-agent','status']}
r=subprocess.run(commands[provider],capture_output=True,text=True,timeout=30)
identity={'logged_in':r.returncode==0,'email':None}
try:
 if provider=='claude':
  value=json.loads(r.stdout);identity.update(logged_in=value.get('loggedIn') is True,email=value.get('email'),organization=value.get('orgId'))
 elif provider=='codex' and r.returncode==0:
  value=json.loads((Path.home()/'.codex/auth.json').read_text())
  payload=value['tokens']['id_token'].split('.')[1]
  claims=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
  identity['email']=claims.get('email')
 elif provider=='cursor' and r.returncode==0:
  match=re.search(r'Logged in as\\s+([^\\s\\x1b]+@[^\\s\\x1b]+)',r.stdout+r.stderr)
  if match:identity['email']=match.group(1)
except (ValueError,KeyError,TypeError,IndexError,OSError):pass
print(json.dumps(identity))
'''
    return json.loads(controller.remote(meta, shlex.join(['python3', '-c', script, provider]), timeout=35))


@contextlib.contextmanager
def monitor(controller, meta, profile):
    """Save refreshed logins while attached and on detach; offline auto-stop still may need sign-in."""
    stopped = threading.Event()

    def poll():
        """Keep network errors out of the terminal and leave the last good private cache intact."""
        while not stopped.wait(15):
            try: capture(controller, meta, profile)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError): pass

    thread = threading.Thread(target=poll, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stopped.set(); thread.join(timeout=35)
        try: capture(controller, meta, profile)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            print('Agent login cache could not be updated; a later resume may require sign-in.', file=sys.stderr)
