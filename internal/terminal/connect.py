"""Terminal adapters consume an SSH target; they know no compute provider APIs."""

import shlex
import subprocess


def connect_terminal(mode, target, *, herdr, session, environment):
    """Connect without replacing another client or starting a coding agent."""
    if mode == "herdr":
        argv = [herdr, "--remote", target["host"], "--session", session]
    elif mode == "ssh":
        # Ordinary SSH is intentionally distinct from a persistent agent session.
        script = "cd -- " + shlex.quote(target["directory"]) + ' && exec "${SHELL:-/bin/bash}" -l'
        argv = ["ssh", "-tt", "--", target["host"], script]
    elif mode == "terminal":
        script = shlex.join([target["remote_herdr"], "--session", session,
                             "terminal", "attach", target["terminal_id"]])
        argv = ["ssh", "-tt", "--", target["host"], script]
    else:
        raise ValueError("Unsupported terminal adapter")
    return subprocess.call(argv, env=environment)
