"""Prepare through the bundled controller; attach without displacing a client."""

import os
import json
from pathlib import Path
import subprocess
import sys


def main():
    """Keep preparation/account handling in one existing controller during migration."""
    controller, name, ttl, attach, *extra = sys.argv[1:]
    operation = extra[0] if extra else "open"
    if operation not in ("open", "connect") or len(extra) not in (0, 1, 3):
        raise ValueError("Unsupported preparation operation")
    sys.path.insert(0, controller)
    import agent_auth
    import project_shell
    import projects

    payload = json.loads(extra[1]) if len(extra) == 3 else {}
    runtime = extra[2] if len(extra) == 3 else ""
    if attach not in ("workspace", "herdr", "ssh", "none", "terminal"):
        raise ValueError("Unsupported attachment mode")
    profile = projects.project(name)
    if operation == "connect":
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
        project_shell.prepare_repository(owner, profile, create_terminal=attach in ("herdr", "terminal"))
    if payload.get("mcps") is not None:
        if operation != "connect":
            projects.wait_project_filesystem(owner, timeout=0)
        sync_mcps(projects, owner, payload, runtime)
    agent_auth.print_accounts(projects.c, profile)
    if attach == "none":
        print(f"Project prepared: {name}.")
        print(f"Connect: allset connect {name}")
        return 0
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
        print(f"Herdr workspace ready: {name}.")
        print(f"In Herdr's sidebar, select {machine['label']} > {workspace['label']}.")
        print("Start your agent in that remote pane so Herdr can track it under the project.")
        return 0
    if attach == "ssh":
        print("Opening SSH shell. Choose your agent here.", flush=True)
    elif attach == "terminal":
        pane = project_shell.terminal(owner, profile)
        target.update(terminal_id=pane["terminal_id"], remote_herdr="/home/user/.local/bin/herdr")
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
