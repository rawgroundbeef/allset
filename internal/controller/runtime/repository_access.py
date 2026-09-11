"""Configure project Git remotes and verify remote access without moving a checkout."""

import json
import re
import shlex


def github_repository(value):
    """Accept an explicit GitHub owner/repository or credential-free HTTPS/SSH origin."""
    if not isinstance(value, str):
        raise ValueError('Repository must identify a GitHub owner/repository')
    value = value.strip().rstrip('/').removesuffix('.git')
    for prefix in ('https://github.com/', 'git@github.com:', 'ssh://git@github.com/'):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*', value):
        raise ValueError('Repository must be a credential-free GitHub owner/repository')
    return value


# This helper runs on the project Box. Native gh resolves the configured
# account; no credential is read back, copied into Git config or logged.
REMOTE_SCRIPT = r'''import json,os,shlex,shutil,subprocess,sys,urllib.parse
cwd,repository,provider=sys.argv[1:]
expected='https://github.com/'+repository+'.git'
def git(*args,check=True):
 """Run noninteractive Git without leaking credential-helper output on failure."""
 r=subprocess.run(['git','-C',cwd,*args],capture_output=True,text=True,
                  env={**os.environ,'GIT_TERMINAL_PROMPT':'0'},timeout=60)
 if check and r.returncode:
  raise SystemExit('Project Git operation failed; verify repository access. Credential output withheld.')
 return r
def identity(url):
 """Identify the repo, accepting native Box credential injection only for exact GitHub HTTPS URLs."""
 if provider=='box' and url.startswith('https://'):
  parsed=urllib.parse.urlsplit(url)
  if parsed.hostname=='github.com' and parsed.port in (None,443) and not parsed.query and not parsed.fragment:
   return parsed.path.strip('/').removesuffix('.git').lower()
  return None
 url=url.strip().rstrip('/').removesuffix('.git')
 for prefix in ('https://github.com/','git@github.com:','ssh://git@github.com/'):
  if url.startswith(prefix):return url[len(prefix):].lower()
 return None
git('rev-parse','--git-common-dir')
existing=git('config','--get-all','remote.origin.url',check=False)
urls=existing.stdout.splitlines()
push_urls=git('config','--get-all','remote.origin.pushurl',check=False).stdout.splitlines()
if any(identity(url)!=repository.lower() for url in push_urls):
 raise SystemExit('Existing origin push URL belongs to a different repository; left unchanged.')
if urls:
 if len(urls)!=1 or identity(urls[0])!=repository.lower():
  raise SystemExit('Existing origin belongs to a different repository; left unchanged.')
else:
 git('remote','add','origin',expected)
if provider in ('box','github-cli'):
 if not shutil.which('gh'):raise SystemExit('Project GitHub integration requires the gh CLI.')
 # Box may inject a token-bearing HTTPS origin on upgrade/resume. Replace it
 # with the same credential-free repo URL and use its managed gh credential file.
 git('remote','set-url','origin',expected)
 if push_urls:git('config','--local','--replace-all','remote.origin.pushurl',expected)
 helper='credential.https://github.com.helper'
 # Reset inherited helpers; use the declared native account context explicitly.
 git('config','--local','--replace-all',helper,'')
 client='/home/user/.local/bin/gh' if provider=='github-cli' else 'gh'
 git('config','--local','--add',helper,'!'+client+' auth git-credential')
 git('config','--local','credential.https://github.com.useHttpPath','true')
 probe=git('ls-remote','--exit-code','origin','HEAD',check=False)
 if probe.returncode:
  raise SystemExit('GitHub access is unavailable for '+repository+
   '. Check the configured project GitHub account before opening an agent. No checkout was changed.')
 print(json.dumps({'repository':repository,'origin_configured':True,'github_verified':True}))
elif provider=='unconfigured':
 print(json.dumps({'repository':repository,'origin_configured':True,'github_verified':False}))
else:
 raise SystemExit('Unsupported project GitHub authentication provider')
'''


def configure(remote, meta, cwd, repository, github=None):
    """Restore a missing origin and optionally require native Box GitHub access before declaring readiness.

    An existing foreign origin is never overwritten. Native token-bearing Box
    origins are normalized to the same repository without copying or logging
    their credentials. Configuration is shared by
    this source repository's Git worktrees; HEADs, branches and worktree files
    remain unchanged. Native credential files are never transmitted to the laptop.
    """
    repo = github_repository(repository)
    provider = github['provider'] if github else 'unconfigured'
    if provider not in ('box', 'github-cli', 'unconfigured'):
        raise ValueError('Unsupported project GitHub authentication provider')
    result = remote(meta, shlex.join(['python3', '-c', REMOTE_SCRIPT, cwd, repo, provider]), timeout=75)
    return json.loads(result)
