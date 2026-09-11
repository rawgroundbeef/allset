import copy
import subprocess
import unittest
from unittest.mock import patch

from workspace import ensure_herdr_workspace, ensure_herdr_machine, herdr_catalog, herdr_catalog_environment


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.workspaces = []
        self.created = {"workspace_id": "w7", "label": "dashboard / project"}
        self.failure = None
        self.disappear = False

    def remote(self, *args):
        self.calls.append(args)
        if args == ("workspace", "list"):
            return {"workspaces": copy.deepcopy(self.workspaces)}
        self.assertEqual(args, ("workspace", "create", "--cwd", "/home/user/a project/'$()",
                                "--label", "dashboard / project", "--no-focus"))
        if not self.disappear:
            self.workspaces.append(self.created)
        if self.failure:
            raise self.failure

    def ensure(self):
        return ensure_herdr_workspace(self.remote, label="dashboard / project",
                                      directory="/home/user/a project/'$()")

    def test_create_then_reuse_without_focus_or_pane_commands(self):
        self.assertEqual(self.ensure(), self.created)
        self.workspaces[0]["panes"] = [{"agent": "codex"}, {"agent": "claude"}]
        before = copy.deepcopy(self.workspaces)
        self.calls.clear()
        self.ensure()
        self.assertEqual(self.calls, [("workspace", "list")])
        self.assertEqual(self.workspaces, before)

    def test_create_timeout_reconciles_without_retry(self):
        self.failure = subprocess.TimeoutExpired("herdr", 60)
        self.assertEqual(self.ensure(), self.created)
        self.assertEqual(sum(c[1] == "create" for c in self.calls), 1)

    def test_failed_create_never_attaches_or_retries(self):
        self.disappear = True
        self.failure = RuntimeError("server unavailable")
        with self.assertRaisesRegex(RuntimeError, "server unavailable"):
            self.ensure()
        self.assertEqual(sum(c[1] == "create" for c in self.calls), 1)

    def test_duplicate_labels_fail_without_mutation(self):
        self.workspaces = [self.created, dict(self.created, workspace_id="w8")]
        with self.assertRaisesRegex(RuntimeError, "Multiple"):
            self.ensure()
        self.assertEqual(self.calls, [("workspace", "list")])


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.profiles = []
        self.created = dict(id="opaque-profile", target="project-host", session="agents",
                            label="dashboard", enabled=True)
        self.timeout = False

    def local(self, *args):
        self.calls.append(args)
        if args == ("list", "--json"):
            return copy.deepcopy(self.profiles)
        if args == ("enable", "opaque-profile"):
            self.profiles[0]["enabled"] = True
            return
        self.assertEqual(args, ("add", "project-host", "--label", "dashboard", "--remote-session", "agents"))
        self.profiles.append(self.created)
        if self.timeout:
            raise subprocess.TimeoutExpired("herdr", 180)

    def ensure(self):
        return ensure_herdr_machine(self.local, host="project-host", session="agents", label="dashboard")

    def test_create_timeout_reconciles_and_reuse_preserves_custom_label(self):
        self.timeout = True
        self.assertEqual(self.ensure(), self.created)
        self.assertEqual(sum(c[0] == "add" for c in self.calls), 1)
        self.profiles[0]["label"] = "My work"
        self.calls.clear()
        self.assertEqual(self.ensure()["label"], "My work")
        self.assertEqual(self.calls, [("list", "--json")])

    def test_enable_uses_returned_id(self):
        self.profiles = [dict(self.created, enabled=False)]
        self.assertTrue(self.ensure()["enabled"])
        self.assertIn(("enable", "opaque-profile"), self.calls)

    def test_different_target_or_session_with_same_label_is_not_retargeted(self):
        for field, value in (("target", "another-host"), ("session", "other-session")):
            self.profiles = [dict(self.created, **{field: value})]
            self.calls.clear()
            with self.assertRaisesRegex(RuntimeError, "another target"):
                self.ensure()
            self.assertEqual(self.calls, [("list", "--json")])

    def test_duplicate_target_is_not_selected_arbitrarily(self):
        self.profiles = [self.created, dict(self.created, id="another-profile")]
        with self.assertRaisesRegex(RuntimeError, "Multiple"):
            self.ensure()
        self.assertEqual(self.calls, [("list", "--json")])

    def test_matching_profile_with_ambiguous_sidebar_label_fails(self):
        self.profiles = [self.created, dict(self.created, id="other", target="another-host")]
        with self.assertRaisesRegex(RuntimeError, "same sidebar label"):
            self.ensure()
        self.assertEqual(self.calls, [("list", "--json")])

    def test_caller_catalog_without_inheriting_remote_socket_or_pane(self):
        fallback = {"PATH": "/bin", "HERDR_CONFIG_PATH": "/adapter/config.toml",
                    "HERDR_SOCKET_PATH": "/foreign/socket", "HERDR_PANE_ID": "p99"}
        self.assertEqual(herdr_catalog_environment(fallback, {"HERDR_ENV": "1"}), {"PATH": "/bin"})
        self.assertEqual(herdr_catalog_environment(fallback, {"HERDR_ENV": "1", "HERDR_CONFIG_PATH": "/caller/config.toml"}),
                         {"PATH": "/bin", "HERDR_CONFIG_PATH": "/caller/config.toml"})
        self.assertEqual(herdr_catalog_environment(fallback, {}),
                         {"PATH": "/bin", "HERDR_CONFIG_PATH": "/adapter/config.toml"})

    def test_native_setup_has_no_approval_input_or_takeover_flags(self):
        environment = {"HERDR_CONFIG_PATH": "/caller/config.toml"}
        with patch("workspace.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "")
            herdr_catalog("/installed/herdr", environment, "add", "project-host", "--label", "dashboard", "--remote-session", "agents")
            args, kwargs = run.call_args
            self.assertEqual(args[0], ["/installed/herdr", "machine", "add", "project-host", "--label", "dashboard", "--remote-session", "agents"])
            self.assertEqual(kwargs["env"], environment)
            self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(kwargs["timeout"], 180)


if __name__ == "__main__":
    unittest.main()
