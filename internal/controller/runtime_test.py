"""Synthetic checks against the actual shipped controller, without external CLIs."""
import contextlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import projects
import agent_auth
import github_auth
import infisical_context
from profiles import validate

c = projects.c


class RuntimeTests(unittest.TestCase):
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
