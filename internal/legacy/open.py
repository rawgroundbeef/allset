"""Prepare through the bundled controller; attach without displacing a client."""

import os
import json
import hashlib
import fcntl
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def selected_declaration(declaration, profile):
    """Limit project integrations to the coding clients chosen in this private profile."""
    if not profile.get("coding_only") or declaration.get("mcps") is None:
        return declaration
    selected = set(profile.get("clients") or [])
    result = dict(declaration)
    result["mcps"] = {}
    for name, value in declaration["mcps"].items():
        targets = [client for client in (value.get("agents") or selected) if client in selected]
        if targets:
            result["mcps"][name] = {**value, "agents": sorted(targets)}
    return result


def main():
    """Keep preparation/account handling in one existing controller during migration."""
    controller, name, ttl, attach, *extra = sys.argv[1:]
    operation = extra[0] if extra else "open"
    if operation not in ("open", "connect", "onboard") or len(extra) not in (0, 1, 3):
        raise ValueError("Unsupported preparation operation")
    sys.path.insert(0, controller)
    import agent_auth
    import project_shell
    import projects
    import progress
    import shlex

    payload = json.loads(extra[1]) if len(extra) == 3 else {}
    runtime = extra[2] if len(extra) == 3 else ""
    if attach not in ("workspace", "herdr", "ssh", "none", "terminal"):
        raise ValueError("Unsupported attachment mode")
    login_clients = []
    onboarding_lock = None
    if operation == "onboard":
        import onboarding
        lock_path = projects.PROJECTS / name / "onboarding-operation.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        onboarding_lock = lock_path.open("a")
        try:
            fcntl.flock(onboarding_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another onboarding operation is already preparing this project") from None
        profile, login_clients = onboarding.ensure_profile(projects.c, payload)
        declaration = payload["project"]
    else:
        profile = projects.project(name)
        declaration = payload
    declaration = selected_declaration(declaration, profile)
    checkout = None
    with progress.Progress(summary='Box prepared' if operation == 'onboard' else 'Workspace prepared'):
        if operation == "connect":
            progress.stage("machine", "Checking your running machine")
            with projects.project_lock(name):
                owner = projects.machine(name)
                info = projects.c.box("info", owner["machine_id"])["box"]
                if info["state"] not in ("ready", "idle", "running"):
                    raise RuntimeError("Project is not running; use allset " + name + " to resume it")
                projects.c.refresh_ssh(owner)
                projects.wait_project_filesystem(owner, timeout=0)
        else:
            prepare_sessions = attach in ("workspace", "herdr", "terminal")
            owner = projects.open_project(name, ttl=int(ttl), create_terminal=False,
                                          prepare_sessions=prepare_sessions)
            checkout = project_shell.prepare_repository(owner, profile, create_terminal=attach in ("herdr", "terminal"))
        if declaration.get("mcps") is not None:
            if operation != "connect":
                projects.wait_project_filesystem(owner, timeout=0)
            progress.stage("mcps", "Preparing your MCP settings")
            sync_mcps(projects, owner, declaration, runtime, quiet=True)
            progress.note("MCP settings applied for new agent sessions")
        if checkout and (declaration.get("skills") is not None or profile.get("personal_skills")):
            directory = "/home/user/.local/share/allset/skills-runtime"
            projects.c.write_remote(owner, directory + "/skills.py", (Path(controller) / "skills.py").read_text())
            personal_sources = {}
            for skill in profile.get("personal_skills") or []:
                source = Path(skill["path"])
                files = [path for path in sorted(source.rglob("*")) if path.is_file() and not path.is_symlink()]
                total = sum(path.stat().st_size for path in files)
                if source.is_symlink() or not (source / "SKILL.md").is_file() or any(path.is_symlink() for path in source.rglob("*")) or total > 8 * 1024 * 1024:
                    raise ValueError("Personal skill source is missing, unsafe, or exceeds 8 MiB: " + skill["name"])
                digest = hashlib.sha256()
                for path in files:
                    digest.update(path.relative_to(source).as_posix().encode() + b"\0" + path.read_bytes())
                revision = digest.hexdigest()
                target = ("/home/user/.local/share/allset/personal-skill-sources/" + name + "/" +
                          skill["name"] + "/" + revision)
                probe = ("import hashlib,pathlib,sys;p=pathlib.Path(sys.argv[1]);h=hashlib.sha256();"
                         "files=sorted(x for x in p.rglob('*') if x.is_file() and not x.is_symlink());"
                         "[(h.update(x.relative_to(p).as_posix().encode()+b'\\0'+x.read_bytes())) for x in files];"
                         "print('missing' if not p.exists() else h.hexdigest() if p.is_dir() and not p.is_symlink() and not any(x.is_symlink() for x in p.rglob('*')) else 'unsafe')")
                remote_digest = projects.c.remote(owner, shlex.join(["python3", "-c", probe, target])).strip()
                if remote_digest not in ("missing", revision):
                    raise ValueError("Managed personal skill source changed remotely: " + skill["name"])
                with tempfile.TemporaryDirectory() as temporary:
                    archive = Path(temporary) / "skill.tar.gz"
                    with tarfile.open(archive, "w:gz") as bundle:
                        bundle.add(source, arcname=".", recursive=True)
                    if remote_digest == "missing":
                        remote_archive = directory + "/" + skill["name"] + ".tar.gz"
                        projects.c.transfer(owner, archive, remote_archive)
                        extract = ("import pathlib,tarfile,sys;root=pathlib.Path(sys.argv[1]);a=tarfile.open(sys.argv[2]);"
                                   "members=a.getmembers();assert not root.exists() and all((m.isfile() or m.isdir()) and not pathlib.PurePosixPath(m.name).is_absolute() and '..' not in pathlib.PurePosixPath(m.name).parts for m in members);"
                                   "root.mkdir(parents=True);a.extractall(root);pathlib.Path(sys.argv[2]).unlink()")
                        projects.c.remote(owner, shlex.join(["python3", "-c", extract, target, remote_archive]))
                personal_sources[skill["name"]] = target
            request = {"project": name, "checkout": checkout["cwd"], "skills": declaration.get("skills") or {},
                       "personal_sources": personal_sources, "clients": profile.get("clients") or []}
            projects.c.remote(owner, shlex.join(["python3", "-c",
                "import json,sys;sys.path.insert(0,sys.argv[1]);import skills;skills.main(json.loads(sys.argv[2]))",
                directory, json.dumps(request)]))
            progress.note("Skills applied for new agent sessions")
        if operation != 'onboard':
            agent_auth.print_accounts(projects.c, profile)
        target = {"host": owner["ssh_alias"]}
        if attach in ("workspace", "ssh", "terminal"):
            record = json.loads((projects.PROJECTS / name / "shell.json").read_text())
            checkout = projects.c.load(record["task_id"])
            if (checkout.get("project") != name or checkout.get("role") != "shell"
                    or checkout.get("machine_id") != owner["machine_id"]
                    or not Path(checkout.get("cwd", "")).is_absolute()):
                raise ValueError("Project shell ownership or directory is invalid")
            target["directory"] = checkout["cwd"]
        if attach == "workspace":
            progress.stage("workspace", "Opening your Herdr workspace")
            # The VM/session comes only from the validated project owner. Caller
            # Herdr variables choose the local catalog, never the remote target.
            with projects.project_lock(name):
                workspace = ensure_herdr_workspace(
                    lambda *args: projects.c.rh(owner, *args),
                    label=name + " / project", directory=target["directory"])
            environment = herdr_catalog_environment(projects.c.herdr_env(), os.environ)
            machine = ensure_herdr_machine(
                lambda *args: herdr_catalog(str(projects.c.HERDR), environment, *args),
                host=target["host"], session=projects.c.SESSION, label=name)
        if attach == "terminal":
            progress.stage("workspace", "Finding your persistent terminal")
            pane = project_shell.terminal(owner, profile)
            target.update(terminal_id=pane["terminal_id"], remote_herdr="/home/user/.local/bin/herdr")
    if operation == "onboard":
        with projects.project_lock(name):
            skipped_clients = onboarding.authenticate_clients(projects.c, owner, profile, login_clients)
        for server, mcp in (declaration.get("mcps") or {}).items():
            if mcp.get("preset") != "trigger":
                continue
            if set(mcp.get('agents') or profile.get('clients') or []) <= skipped_clients:
                continue
            request = {"operation": "login", "project": name, "repository": declaration["repository"],
                       "mcps": declaration["mcps"], "server": server}
            command = shlex.join(["python3", "-c", runtime, json.dumps(request)])
            if subprocess.call(["ssh", "-tt", "--", owner["ssh_alias"], command]):
                raise RuntimeError("MCP sign-in did not complete for " + server + "; retry onboarding")
        for server, mcp in (declaration.get("mcps") or {}).items():
            if mcp.get("oauth") is not True:
                continue
            targets = mcp.get("agents") or profile.get("clients") or []
            for client in targets:
                if client not in profile.get("clients", []) or client in skipped_clients:
                    continue
                argv = {"codex": ["codex", "mcp", "login", server],
                        "claude": ["claude", "mcp", "login", server],
                        "cursor": ["cursor-agent", "mcp", "login", server]}[client]
                command = "cd -- " + shlex.quote(checkout["cwd"]) + " && " + shlex.join(argv)
                if subprocess.call(["ssh", "-tt", "--", owner["ssh_alias"], command]):
                    raise RuntimeError(client + " MCP sign-in did not complete for " + server + "; retry onboarding")
                if client == "cursor":
                    projects.c.remote(owner, "cd -- " + shlex.quote(checkout["cwd"]) + " && " +
                                      shlex.join(["cursor-agent", "mcp", "enable", server]))
    if checkout and profile.get("clients"):
        import infisical_context
        directory = "/home/user/.local/share/allset/session-runtime"
        for source in ("session_context.py", "infisical_context.py", "profiles.py"):
            projects.c.write_remote(owner, directory + "/" + source, (Path(controller) / source).read_text())
        binding = infisical_context.binding(profile) if profile.get("infisical") else None
        request = {"clients": profile.get("clients") or [], "binding": binding, "project": name,
                   "checkout": checkout["cwd"], "environment": declaration.get("session_environment") or {}}
        script = ("import json,sys;sys.path.insert(0,sys.argv[1]);import session_context;"
                  "r=json.loads(sys.argv[2]);session_context.install(r['clients'],r['binding'],r['project'],r['checkout'],r['environment'])")
        projects.c.remote(owner, shlex.join(["python3", "-c", script, directory, json.dumps(request)]))
    if operation == "onboard":
        journal = projects.PROJECTS / name / "onboarding.json"
        value = json.loads(journal.read_text()); value["stage"] = "complete"; projects.atomic(journal, value)
    if attach == "none":
        print(f"Project prepared: {name}.")
        print(f"Connect: allset connect {name}")
        return 0
    if attach == "workspace":
        print(f"Herdr workspace ready: {name}.")
        print(f"In Herdr's sidebar, select {machine['label']} > {workspace['label']}.")
        print("Start your agent in that remote pane so Herdr can track it under the project.")
        return 0
    if attach == "ssh":
        progress.handoff('Opening SSH shell')
    elif attach == "terminal":
        print("Persistent project terminal. Detach with Ctrl+b, then q; reconnect with allset.", flush=True)
    else:
        print("Opening the native Herdr view. Detach with Ctrl+b, then q.", flush=True)
    with agent_auth.monitor(projects.c, owner, profile):
        return connect_terminal(attach, target,
                                herdr=str(projects.c.HERDR) if attach == "herdr" else "",
                                session=projects.c.SESSION if attach in ("herdr", "terminal") else "",
                                environment=projects.c.herdr_env() if attach == "herdr" else os.environ.copy())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("allset: interrupted; no stop or takeover requested", file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        print("allset:", str(error), file=sys.stderr)
        sys.exit(1)
