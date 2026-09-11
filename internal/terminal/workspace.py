"""Native Herdr workspace handoff without attaching or steering a client."""

import json
import subprocess


def herdr_catalog_environment(fallback, caller):
    # Catalog commands are local; never inherit a pane/socket target. A native
    # caller with no override uses Herdr's default config. Outside Herdr, retain
    # the installed adapter's catalog unless the caller explicitly names one.
    environment = {key: value for key, value in fallback.items() if not key.startswith("HERDR_")}
    config = caller.get("HERDR_CONFIG_PATH")
    if not config and caller.get("HERDR_ENV") != "1":
        config = fallback.get("HERDR_CONFIG_PATH")
    if config:
        environment["HERDR_CONFIG_PATH"] = config
    return environment


def ensure_herdr_workspace(remote, *, label, directory):
    def existing():
        matches = [w for w in remote("workspace", "list")["workspaces"]
                   if w.get("label") == label]
        if len(matches) > 1:
            raise RuntimeError("Multiple Herdr workspaces have the project label; inspect them before reconnecting")
        return matches[0] if matches else None

    workspace = existing()
    if workspace is None:
        try:
            remote("workspace", "create", "--cwd", directory, "--label", label, "--no-focus")
        except Exception:
            # Creation may have succeeded before the response was lost. Observe
            # once; do not repeat a mutation with an uncertain outcome.
            workspace = existing()
            if workspace is None:
                raise
        else:
            workspace = existing()
    if not workspace or not workspace.get("workspace_id"):
        raise RuntimeError("Herdr workspace creation could not be verified; inspect before retrying")
    # A workspace may contain multiple tabs, panes, and agents. Reusing it must
    # not select a pane, change its cwd, send input, or steal another client's focus.
    return workspace


def herdr_catalog(executable, environment, *args):
    result = subprocess.run([executable, "machine", *args], env=environment,
                            stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=180)
    if result.returncode:
        raise RuntimeError("Herdr machine catalog command failed; inspect the connection in Herdr")
    return json.loads(result.stdout) if args[0] == "list" else None


def ensure_herdr_machine(local, *, host, session, label):
    def existing():
        profiles = local("list", "--json")
        matches = [p for p in profiles if p.get("target") == host and p.get("session") == session]
        if len(matches) > 1:
            raise RuntimeError("Multiple Herdr machine profiles target this project session; inspect the catalog")
        if not matches and any(p.get("label") == label for p in profiles):
            raise RuntimeError("Herdr machine label already belongs to another target; inspect the catalog")
        if matches and sum(p.get("label") == matches[0].get("label") for p in profiles) > 1:
            raise RuntimeError("Multiple Herdr machines have the same sidebar label; inspect the catalog")
        return matches[0] if matches else None

    profile = existing()
    if profile is None:
        try:
            # The remote workspace call already established the named server.
            # No stdin means native setup cannot approve replacing that server.
            local("add", host, "--label", label, "--remote-session", session)
        except Exception:
            profile = existing()
            if profile is None:
                raise
        else:
            profile = existing()
    if not profile or not profile.get("id") or not profile.get("label"):
        raise RuntimeError("Herdr machine registration could not be verified; inspect before retrying")
    if not profile.get("enabled"):
        local("enable", profile["id"])
        profile = existing()
        if not profile or not profile.get("enabled"):
            raise RuntimeError("Herdr machine is still disabled")
    return profile
