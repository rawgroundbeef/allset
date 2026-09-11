"""Synthetic checks against the actual shipped controller, without external CLIs."""
import contextlib
import json
import io
import os
import pty
import select
import time
import tempfile
import types
import fcntl
import progress
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import projects
import project_shell
import agent_auth
import github_auth
import infisical_context
from profiles import validate

c = projects.c


class RuntimeTests(unittest.TestCase):
    def test_explicit_project_is_not_reinterpreted_as_native_box_command(self):
        with patch.object(project_shell, 'resolve_project', side_effect=AssertionError('project re-resolved')), \
             patch.object(project_shell, 'shell', return_value=0) as shell:
            self.assertEqual(project_shell.main(['--project', 'dashboard', '--login', 'claude']), 0)
            shell.assert_called_once_with('dashboard', ttl=7200, login_provider='claude')

    def test_attached_monitor_skips_capture_while_native_login_owns_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = types.SimpleNamespace(STATE=Path(tmp))
            project = Path(tmp) / 'projects/dashboard'
            project.mkdir(parents=True)
            with (project / 'operation.lock').open('a') as lock, patch.object(agent_auth, 'capture') as capture:
                fcntl.flock(lock, fcntl.LOCK_EX)
                agent_auth.capture_when_idle(controller, {}, {'name': 'dashboard'})
                capture.assert_not_called()
                fcntl.flock(lock, fcntl.LOCK_UN)
                agent_auth.capture_when_idle(controller, {}, {'name': 'dashboard'})
                capture.assert_called_once()

    def test_progress_plain_output_and_failure_cleanup(self):
        for error in (None, RuntimeError('fixture failure'), KeyboardInterrupt()):
            output = io.StringIO()
            try:
                with progress.Progress(output) as display:
                    progress.stage('files', 'Restoring your files', 'Waiting for the saved filesystem')
                    progress.note('Codex: sign-in needed')
                    if error is not None:
                        raise error
            except (RuntimeError, KeyboardInterrupt):
                pass
            text = output.getvalue()
            self.assertNotIn('\x1b', text)
            self.assertIn('Restoring your files', text)
            self.assertIn('Codex: sign-in needed', text)
            self.assertEqual('Workspace prepared' in text, error is None)
            self.assertEqual('Stopped waiting' in text, isinstance(error, KeyboardInterrupt))
            self.assertFalse(progress.active())
            self.assertIsNone(display.worker)

    def test_progress_real_tty_animates_and_releases_terminal_on_every_exit(self):
        for error in (None, RuntimeError('fixture'), KeyboardInterrupt()):
            master, slave = pty.openpty()
            try:
                with os.fdopen(os.dup(slave), 'w', buffering=1) as output, patch.dict(os.environ, {'TERM': 'xterm', 'NO_COLOR': '1'}):
                    try:
                        with progress.Progress(output) as display:
                            progress.stage('files', 'Restoring your files', 'Downloading the saved filesystem')
                            deadline = time.monotonic() + 2
                            while display.frame < 3 and time.monotonic() < deadline:
                                time.sleep(0.02)
                            self.assertGreaterEqual(display.frame, 3, 'spinner stopped while preparation waited')
                            progress.stage('tools', 'Checking your tools')
                            progress.note('Branch: example\x1b[31m\nlabel')
                            if error is not None:
                                raise error
                    except (RuntimeError, KeyboardInterrupt):
                        pass
                    self.assertFalse(progress.active())
                    self.assertFalse(display.worker.is_alive())
                    output.write('TERMINAL-HANDOFF\n')
                    output.flush()
                chunks = []
                while select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 65536)
                        if not chunk: break
                        chunks.append(chunk)
                    except OSError:
                        break
                text = b''.join(chunks).decode()
                self.assertGreaterEqual(text.count('\r\x1b[2K'), 3)
                self.assertNotIn('\x1b[31m', text, 'account/project label injected terminal control')
                self.assertNotIn('\x1b[36m', text, 'NO_COLOR ignored')
                self.assertEqual('Workspace prepared' in text, error is None)
                self.assertTrue(text.rstrip().endswith('TERMINAL-HANDOFF'), 'display wrote after terminal handoff')
            finally:
                os.close(master)
                if slave is not None: os.close(slave)

    def test_single_client_login_never_prepares_or_resumes_the_environment(self):
        profile = {'name': 'dashboard', 'agent_profile': 'work'}
        owner = {'project': 'dashboard', 'role': 'project', 'task_id': 'project-dashboard',
                 'machine_id': 'bx_saved', 'ssh_alias': 'box-saved'}
        for fault in ('none', 'stopped', 'foreign', 'wrong-id', 'restoring', 'missing-client', 'no-binding'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'dashboard').mkdir()
                (root / 'dashboard/machine.json').write_text(json.dumps(owner))
                target = dict(owner, project='foreign') if fault == 'foreign' else owner
                def native_login(controller, meta, selected_profile, provider):
                    self.assertFalse(progress.active(), 'spinner survived into native sign-in')
                    self.assertEqual((meta, selected_profile, provider), (owner, profile, 'claude'))
                    return 7
                with patch.object(projects, 'PROJECTS', root), \
                     patch.object(projects, 'project', return_value=profile), \
                     patch.object(projects, 'machine', return_value=target), \
                     patch.object(projects, 'open_project', side_effect=AssertionError('sign-in prepared other accounts or resumed compute')), \
                     patch.object(agent_auth, 'config', return_value=None if fault == 'no-binding' else {'name': 'work'}), \
                     patch.object(c, 'box', return_value={'box': {'id': 'bx_other' if fault == 'wrong-id' else 'bx_saved',
                                                                'state': 'stopped' if fault == 'stopped' else 'running'}}) as box, \
                     patch.object(c, 'refresh_ssh') as ssh, \
                     patch.object(projects, 'wait_project_filesystem', side_effect=RuntimeError('restoring') if fault == 'restoring' else None) as filesystem, \
                     patch.object(c, 'remote', return_value='' if fault == 'missing-client' else 'ready') as remote, \
                     patch.object(agent_auth, 'login', side_effect=native_login) as login:
                    if fault == 'none':
                        self.assertEqual(project_shell.shell('dashboard', login_provider='claude'), 7)
                        filesystem.assert_called_once_with(owner, timeout=0)
                        self.assertIn('command -v claude', remote.call_args.args[1])
                    else:
                        with self.assertRaises((ValueError, RuntimeError)):
                            project_shell.shell('dashboard', login_provider='claude')
                        login.assert_not_called()
                    if fault in ('no-binding', 'foreign'):
                        box.assert_not_called()
                    else:
                        box.assert_called_once_with('info', 'bx_saved')
                    if fault in ('no-binding', 'foreign', 'stopped', 'wrong-id'):
                        ssh.assert_not_called()

    def test_native_sign_in_verifies_identity_and_caches_only_selected_client(self):
        for outcome in ('success', 'failed', 'wrong-account', 'unverified', 'missing-credentials', 'extra-client'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                controller = types.SimpleNamespace(STATE=Path(tmp))
                profile = {'name': 'dashboard', 'agent_profile': 'work'}
                owner = {'project': 'dashboard', 'ssh_alias': 'box-dashboard'}
                binding = {'name': 'work', 'providers': {'claude': {'account_email': 'work@example.test'}}}
                other = agent_auth.cache_path(controller, profile, 'codex')
                agent_auth.private_write(other, {'fixture': 'other login unchanged'})
                before = other.read_bytes()
                credential = {'claudeAiOauth': {'accessToken': 'synthetic-access'}}
                selected = agent_auth.cache_path(controller, profile, 'claude')
                old_credential = {'claudeAiOauth': {'accessToken': 'old-synthetic-access'}}
                agent_auth.private_write(selected, {'project': 'dashboard', 'profile': 'work',
                                                     'provider': 'claude', 'contents': old_credential})
                identity = {'logged_in': outcome != 'unverified',
                            'email': 'personal@example.test' if outcome == 'wrong-account' else 'work@example.test'}
                response = {} if outcome == 'missing-credentials' else {'claude': credential}
                if outcome == 'extra-client': response['codex'] = {'tokens': {'access_token': 'unexpected'}}
                with patch.object(agent_auth, 'config', return_value=binding), \
                     patch.object(agent_auth.subprocess, 'call', return_value=9 if outcome == 'failed' else 0) as native, \
                     patch.object(agent_auth, 'native_identity', return_value=identity) as verify, \
                     patch.object(agent_auth, 'exchange', return_value=response) as exchange:
                    if outcome in ('wrong-account', 'unverified', 'missing-credentials', 'extra-client'):
                        with self.assertRaises(RuntimeError):
                            agent_auth.login(controller, owner, profile, 'claude')
                    else:
                        self.assertEqual(agent_auth.login(controller, owner, profile, 'claude'), 9 if outcome == 'failed' else 0)
                    self.assertIn('claude auth login --claudeai --email work@example.test', native.call_args.args[0][-1])
                    if outcome == 'success':
                        request = exchange.call_args.args[2]
                        self.assertEqual(set(request['files']), {'claude'})
                        saved = agent_auth.read_private(selected)
                        self.assertEqual(saved['contents'], credential)
                        self.assertEqual(saved['project'], 'dashboard')
                    else:
                        expected_reads = 1 if outcome in ('missing-credentials', 'extra-client') else 0
                        self.assertEqual(exchange.call_count, expected_reads)
                        pending = agent_auth.read_private(selected)
                        self.assertTrue(pending['needs_login'])
                        self.assertEqual(pending['contents'], old_credential)
                        agent_auth.capture(controller, owner, profile, ['claude'])
                        self.assertEqual(exchange.call_count, expected_reads)  # No later monitor accepts the rejected login.
                    if outcome == 'failed': verify.assert_not_called()
                    self.assertEqual(other.read_bytes(), before)

    def test_forwarded_ssh_endpoint_and_invalid_endpoint(self):
        self.assertEqual(c.ssh_destination({'sshEndpoint': '127.0.0.1:2200'}), ('127.0.0.1', 2200))
        self.assertEqual(c.ssh_destination({'ip': '127.0.0.1'}), ('127.0.0.1', 22))
        for endpoint in ('evil;command:22', '127.0.0.1:0', '127.0.0.1:99999'):
            with self.assertRaises(ValueError): c.ssh_destination({'sshEndpoint': endpoint})

    def test_restoration_is_more_than_ssh_access(self):
        self.assertFalse(projects.restored_filesystem_ready({'filesystem': 'fuse', 'phase': 'loading'}))
        self.assertFalse(projects.restored_filesystem_ready({'filesystem': 'ext4', 'phase': 'loading'}))
        self.assertTrue(projects.restored_filesystem_ready({'filesystem': 'ext4', 'phase': 'done'}))
        with self.assertRaises(RuntimeError): projects.restored_filesystem_ready({'filesystem': 'ext4', 'restore_error': True})

    def test_resume_timeout_reconciles_same_machine_without_retry(self):
        owner = {'machine_id': 'bx_saved'}
        calls = []
        def box(*args, **kwargs):
            calls.append(args)
            if args[0] == 'resume': raise subprocess.TimeoutExpired('box', 180)
            self.assertEqual(args, ('info', 'bx_saved'))
            return {'box': {'state': 'provisioning'}}
        with patch.object(c, 'box', box), patch.object(c, 'save'):
            projects.request_resume(owner, {'box_environment': 'fixture'}, 7200)
        self.assertEqual(sum(call[0] == 'resume' for call in calls), 1)
        self.assertEqual(owner['machine_id'], 'bx_saved')

    def test_creation_needs_explicit_environment_before_any_side_effect(self):
        with patch.object(c, 'box', side_effect=AssertionError('unexpected provider call')):
            with self.assertRaisesRegex(ValueError, 'explicit Box environment'): c.create({}, 7200)

    def test_continuous_vm_allowance_uses_bounded_window(self):
        response = {'pageInfo': {'hasMore': False}, 'boxes': [
            {'id': 'bx_other', 'state': 'running', 'archiveAfter': None, 'billingMultiplier': 0.5}]}
        with patch.object(c, 'box', return_value=response):
            self.assertEqual(c.reserved_allowance(horizon_seconds=7200), 3600)
            with self.assertRaises(RuntimeError): c.reserved_allowance()
        response['pageInfo']['hasMore'] = True
        with patch.object(c, 'box', return_value=response):
            with self.assertRaises(RuntimeError): c.reserved_allowance(horizon_seconds=7200)

    def test_plain_preparation_does_not_opt_into_sessions(self):
        with patch.object(projects, 'project', return_value={'name': 'dashboard'}), \
             patch.object(projects, 'project_lock', return_value=contextlib.nullcontext()), \
             patch.object(projects, 'ensure_project', return_value={'project': 'dashboard'}) as ensure, \
             patch.object(projects, 'show', side_effect=AssertionError('session display')), \
             patch.object(c, 'rh', side_effect=AssertionError('Herdr call')):
            projects.open_project('dashboard', create_terminal=False, prepare_sessions=False)
        self.assertFalse(ensure.call_args.kwargs['prepare_sessions'])
        self.assertFalse(ensure.call_args.kwargs['reconcile_agents'])

    def test_agent_transfer_rejects_foreign_project_before_reading_credentials(self):
        profile = {'name': 'dashboard', 'agent_profile': 'work'}
        with patch.object(agent_auth, 'config', return_value={'name': 'work'}), \
             patch.object(agent_auth, 'read_private', side_effect=AssertionError('credential read')), \
             patch.object(agent_auth, 'exchange', side_effect=AssertionError('transfer')):
            with self.assertRaises(ValueError): agent_auth.restore(c, {'project': 'different'}, profile)
            with self.assertRaises(ValueError): agent_auth.capture(c, {'project': 'different'}, profile)

    def test_github_foreign_target_cannot_read_ambient_account(self):
        profile = {'name': 'dashboard', 'github': {'provider': 'github-cli', 'account_login': 'fixture-user'}}
        with patch.object(github_auth, 'run_native', side_effect=AssertionError('native credential read')):
            with self.assertRaises(ValueError): github_auth.stage(c, {'project': 'different', 'role': 'project'}, profile)

    def test_secret_bindings_cannot_mix_with_shell_only(self):
        profile = {'version': 1, 'name': 'dashboard', 'repository': 'example/dashboard', 'base': 'main',
                   'template': None, 'box_environment': 'fixture', 'setup_commands': [], 'services': [], 'shell_only': True}
        self.assertEqual(validate(profile), profile)
        with self.assertRaises(ValueError): validate(dict(profile, infisical={'token': 'synthetic'}))


result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeTests))
raise SystemExit(0 if result.wasSuccessful() else 1)
