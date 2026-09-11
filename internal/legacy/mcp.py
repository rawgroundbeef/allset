"""MCP transport adapter. All client rendering stays in the provider-neutral runtime."""
import fcntl
import json
from pathlib import Path
import shlex
import subprocess
import sys


def sync_mcps(projects, owner, payload, runtime, *, quiet=False):
    if payload.get('mcps') is None:
        return
    request = {'operation': 'sync', 'project': payload['name'],
               'repository': payload['repository'], 'mcps': payload['mcps']}
    argv = projects.c.ssh_args(owner) + [shlex.join(['python3', '-c', runtime, json.dumps(request)])]
    result = subprocess.run(argv, timeout=60, **({"capture_output": True, "text": True} if quiet else {}))
    if result.returncode:
        message = 'MCP sync failed; existing agent sessions were left running'
        if quiet:
            # The shipped runtime curates these diagnostics and withholds parser
            # exception bodies, which can include credentials. Do not echo raw
            # transport output or the successful JSON protocol into startup.
            for line in result.stderr.splitlines():
                if line.startswith('allset mcp: '):
                    message += '. ' + ''.join(ch for ch in line[12:600] if ch.isprintable())
                    break
        raise RuntimeError(message)


def mcp_main():
    controller, payload, runtime, operation, server = sys.argv[1:]
    payload = json.loads(payload)
    sys.path.insert(0, controller)
    import projects
    name = payload['name']
    # Fail promptly when another open/resume owns the project, instead of hanging.
    with (projects.PROJECTS / name / 'operation.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another operation is preparing ' + name + '; retry MCP sync when it finishes') from None
        projects.project(name)
        owner = projects.machine(name)
        info = projects.c.box('info', owner['machine_id'])['box']
        if info['state'] not in ('ready', 'idle', 'running'):
            raise RuntimeError('Project is stopped; open it with allset ' + name + ' first')
        projects.c.refresh_ssh(owner)
        projects.wait_project_filesystem(owner, timeout=0)
        sync_mcps(projects, owner, payload, runtime)
        if operation == 'mcp-login':
            request = {'operation': 'login', 'project': name, 'repository': payload['repository'],
                       'mcps': payload['mcps'], 'server': server}
            command = shlex.join(['python3', '-c', runtime, json.dumps(request)])
            return subprocess.call(['ssh', '-tt', '--', owner['ssh_alias'], command])
    print("MCP settings applied. Open a new agent session or use its native MCP reload; no existing agent was restarted.")
    return 0
