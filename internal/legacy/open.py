"""Prepare through the installed controller; attach without displacing a client."""

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
    if attach == "terminal" and operation == "open" and payload.get("mcps") is None:
        # Explicit compatibility mode; native Herdr refuses an occupied terminal.
        # Never add --takeover or close the existing owner on the user's behalf.
        return project_shell.shell(name, ttl=int(ttl))
    if attach not in ("herdr", "ssh", "none", "terminal"):
        raise ValueError("Unsupported attachment mode")
    profile = projects.project(name)
    if operation == "connect":
        with projects.project_lock(name):
            owner = projects.machine(name)
            info = projects.c.box("info", owner["machine_id"])["box"]
            if info["state"] not in ("ready", "idle", "running"):
                raise RuntimeError("Project is not running; use allset " + name + " to resume it")
            projects.c.refresh_ssh(owner)
    else:
        owner = projects.open_project(name, ttl=int(ttl), create_terminal=False)
        project_shell.prepare_repository(owner, profile)
    if payload.get("mcps") is not None:
        projects.wait_project_filesystem(owner, timeout=0)
        sync_mcps(projects, owner, payload, runtime)
    agent_auth.print_accounts(projects.c, profile)
    if attach == "none":
        print(f"Project prepared: {name}. Use its workspace in your existing interface.")
        print(f"Connect explicitly: allset connect {name} --attach herdr (or --attach ssh)")
        return 0
    target = {"host": owner["ssh_alias"]}
    if attach == "ssh":
        record = json.loads((projects.PROJECTS / name / "shell.json").read_text())
        checkout = projects.c.load(record["task_id"])
        if (checkout.get("project") != name or checkout.get("role") != "shell"
                or checkout.get("machine_id") != owner["machine_id"]
                or not Path(checkout.get("cwd", "")).is_absolute()):
            raise ValueError("Project shell ownership or directory is invalid")
        target["directory"] = checkout["cwd"]
        print("Opening an ordinary SSH shell. Use a session manager for work that must survive disconnection.", flush=True)
    elif attach == "terminal":
        pane = project_shell.terminal(owner, profile)
        target.update(terminal_id=pane["terminal_id"], remote_herdr="/home/user/.local/bin/herdr")
    else:
        print("Opening the native Herdr view. Detach with Ctrl+b, then q.", flush=True)
    with agent_auth.monitor(projects.c, owner, profile):
        return connect_terminal(attach, target, herdr=str(projects.c.HERDR),
                                session=projects.c.SESSION, environment=projects.c.herdr_env())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("allset: interrupted; no stop or takeover requested", file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        print("allset:", str(error), file=sys.stderr)
        sys.exit(1)
