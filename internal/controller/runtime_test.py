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
import onboarding
import session_context
import skills
import worker
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
        for outcome in ('success', 'failed', 'wrong-account', 'unverified', 'unsafe-identity',
                        'missing-credentials', 'extra-client'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                controller = types.SimpleNamespace(STATE=Path(tmp))
                profile = {'name': 'dashboard', 'agent_profile': 'work', 'clients': ['claude']}
                owner = {'project': 'dashboard', 'ssh_alias': 'box-dashboard'}
                binding = {'version': 1, 'name': 'work', 'providers': {
                    'claude': {'account_email': 'work@example.test'} if outcome == 'wrong-account' else {}}}
                agent_auth.private_write(Path(tmp) / 'agent-profiles/work/profile.json', binding)
                other = agent_auth.cache_path(controller, profile, 'codex')
                agent_auth.private_write(other, {'fixture': 'other login unchanged'})
                before = other.read_bytes()
                credential = {'claudeAiOauth': {'accessToken': 'synthetic-access'}}
                selected = agent_auth.cache_path(controller, profile, 'claude')
                old_credential = {'claudeAiOauth': {'accessToken': 'old-synthetic-access'}}
                agent_auth.private_write(selected, {'project': 'dashboard', 'profile': 'work',
                                                     'provider': 'claude', 'contents': old_credential})
                identity = {'logged_in': outcome != 'unverified',
                            'email': ('personal@example.test' if outcome == 'wrong-account'
                                      else 'bad\x1b[31m@example.test' if outcome == 'unsafe-identity'
                                      else 'work@example.test')}
                response = {} if outcome == 'missing-credentials' else {'claude': credential}
                if outcome == 'extra-client': response['codex'] = {'tokens': {'access_token': 'unexpected'}}
                with patch.object(agent_auth, 'config', return_value=binding), \
                     patch.object(agent_auth.subprocess, 'call', return_value=9 if outcome == 'failed' else 0) as native, \
                     patch.object(agent_auth, 'native_identity', return_value=identity) as verify, \
                     patch.object(agent_auth, 'exchange', return_value=response) as exchange:
                    if outcome in ('wrong-account', 'unverified', 'unsafe-identity', 'missing-credentials', 'extra-client'):
                        with self.assertRaises(RuntimeError):
                            agent_auth.login(controller, owner, profile, 'claude')
                    else:
                        self.assertEqual(agent_auth.login(controller, owner, profile, 'claude'), 9 if outcome == 'failed' else 0)
                    self.assertIn('claude auth login --claudeai', native.call_args.args[0][-1])
                    self.assertNotIn('--email', native.call_args.args[0][-1])
                    if outcome == 'success':
                        request = exchange.call_args.args[2]
                        self.assertEqual(set(request['files']), {'claude'})
                        saved = agent_auth.read_private(selected)
                        self.assertEqual(saved['contents'], credential)
                        self.assertEqual(saved['project'], 'dashboard')
                        saved_binding = agent_auth.read_private(Path(tmp) / 'agent-profiles/work/profile.json')
                        self.assertEqual(saved_binding['providers']['claude']['account_email'], 'work@example.test')
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

    def test_native_sign_in_rejects_unselected_client_before_authentication(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = types.SimpleNamespace(STATE=Path(tmp))
            profile = {'name': 'dashboard', 'agent_profile': 'work', 'clients': ['codex']}
            binding = {'version': 1, 'name': 'work', 'providers': {'codex': {}}}
            agent_auth.private_write(Path(tmp) / 'agent-profiles/work/profile.json', binding)
            with patch.object(agent_auth.subprocess, 'call') as native:
                with self.assertRaisesRegex(ValueError, 'not selected'):
                    agent_auth.login(controller, {'project': 'dashboard'}, profile, 'claude')
            native.assert_not_called()

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

    def test_coding_only_profile_requires_owned_safe_provider_environment(self):
        profile = {'version': 2, 'name': 'dashboard', 'repository': 'example/dashboard', 'base': 'main',
                   'template': None, 'box_environment': 'allset-dashboard-fixture', 'setup_commands': [],
                   'services': [], 'preview_service': '', 'coding_only': True, 'clients': ['codex'],
                   'provider_binding': {'provider': 'box', 'billing_scope': 'personal-org',
                                        'environment': 'allset-dashboard-fixture', 'safe_for_third_parties': True,
                                        'account_identity': {'email': 'box@example.test'}}}
        self.assertEqual(validate(profile), profile)
        broken = json.loads(json.dumps(profile)); broken['provider_binding']['safe_for_third_parties'] = False
        with self.assertRaises(ValueError): validate(broken)

    def test_coding_only_checkout_never_runs_app_or_fallback_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp); checkout = state / 'checkout'; checkout.mkdir()
            meta = {'base_sha': 'abc123', 'setup_token': 'token', 'cwd': str(checkout),
                    'session_interface': 'ssh', 'project_profile': {'coding_only': True, 'setup_commands': []}}
            with patch.object(worker.subprocess, 'check_output', return_value='abc123\n'), \
                 patch.object(worker, 'run') as run:
                worker.prepare(meta, state)
            self.assertEqual(len(run.call_args_list), 1)
            self.assertEqual(run.call_args_list[0].args[0][0], 'bash')

    def test_source_checkout_uses_only_the_selected_github_account_without_token_argv(self):
        calls = []
        def command(args, **kwargs):
            calls.append((args, kwargs.get('env')))
            if 'ls-remote' in args:
                return types.SimpleNamespace(stdout='ref: refs/heads/main HEAD\n')
            if 'rev-parse' in args:
                return types.SimpleNamespace(stdout='abc123\n')
            return types.SimpleNamespace(stdout='')
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, 'command', side_effect=command), \
             patch.object(github_auth, 'run_native', return_value='selected-token'), \
             patch.object(github_auth, 'verify_account'):
            sha, _, _ = c.source_checkout('acme/dashboard', '', Path(tmp),
                github={'provider': 'github-cli', 'account_login': 'fixture-user'}, clean=True)
        self.assertEqual(sha, 'abc123')
        self.assertNotIn('selected-token', ' '.join(str(arg) for args, _ in calls for arg in args))
        fetch = next((args, env) for args, env in calls if 'fetch' in args)
        self.assertEqual(fetch[1]['GH_TOKEN'], 'selected-token')
        self.assertEqual(fetch[1]['GIT_CONFIG_GLOBAL'], os.devnull)

    def test_skill_projection_preserves_supporting_files_and_rejects_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); home = root / 'home'; checkout = root / 'checkout'
            source = checkout / '.agents/skills/fixture'; source.mkdir(parents=True)
            (source / 'SKILL.md').write_text('fixture'); (source / 'support.txt').write_text('support')
            result = skills.apply(home, 'dashboard', checkout,
                {'fixture': {'path': '.agents/skills/fixture', 'agents': ['codex', 'claude']}},
                selected_clients=['codex'])
            self.assertEqual(result['skills'], ['fixture'])
            self.assertEqual((home / '.agents/skills/fixture/support.txt').read_text(), 'support')
            self.assertFalse((home / '.claude/skills/fixture').exists())
            linked = checkout / 'linked-skill'; linked.symlink_to(source, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                skills.apply(home, 'dashboard', checkout,
                    {'linked': {'path': 'linked-skill', 'agents': ['codex']}}, selected_clients=['codex'])
            (home / '.agents/skills/fixture/SKILL.md').write_text('user edit')
            with self.assertRaisesRegex(ValueError, 'unmanaged edits'):
                skills.apply(home, 'dashboard', checkout,
                    {'fixture': {'path': '.agents/skills/fixture', 'agents': ['codex', 'claude']}},
                    selected_clients=['codex'])

    def test_session_secret_delivery_selects_only_declared_values(self):
        context = {'clients': ['codex'], 'infisical': True, 'session_environment': {
            'FIXTURE_TOKEN': {'secret_path': '/allset', 'secret_key': 'TOKEN', 'agents': ['codex']}}}
        binding = {'name': 'dashboard', 'infisical': {'instance': 'https://example.test',
            'organization_id': 'org', 'project_id': 'project', 'principal_id': 'principal', 'environment': 'dev'}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(session_context.Path, 'home', return_value=Path(tmp)), \
             patch.object(session_context.infisical_context, 'token_environment', return_value={'INFISICAL_TOKEN': 'broker'}), \
             patch.object(session_context.subprocess, 'run', return_value=types.SimpleNamespace(
                 returncode=0, stdout=json.dumps([{'secretKey': 'TOKEN', 'secretValue': 'selected'},
                                                  {'secretKey': 'OTHER', 'secretValue': 'excluded'}]))) as run:
            directory = Path(session_context.__file__).resolve().parent
            binding_path = directory / 'infisical-binding.json'
            # Exercise the pure boundary with a temporary module directory through patched __file__.
            module = Path(tmp) / 'session_context.py'; module.write_text('')
            with patch.object(session_context, '__file__', str(module)):
                binding_path = Path(tmp) / 'infisical-binding.json'; binding_path.write_text(json.dumps(binding))
                env = session_context._secret_environment(context, 'codex')
            self.assertEqual(env['FIXTURE_TOKEN'], 'selected')
            self.assertNotIn('OTHER', env); self.assertNotIn('INFISICAL_TOKEN', env)
            self.assertNotIn('selected', ' '.join(run.call_args.args[0]))
            self.assertIn('--projectId=project', run.call_args.args[0])
            self.assertIn('--env=dev', run.call_args.args[0])

    def test_box_identity_uses_native_status_account_identifier(self):
        # Structure observed from Box 0.1.228 status --org personal; values synthetic.
        status = {
            'account': {'identifier': 'box@example.test', 'loginState': 'active',
                        'plan': 'trial', 'status': 'active', 'suspension': None},
            'api': {'healthy': True, 'error': None, 'status': 'healthy', 'url': 'https://box.example.test'},
            'config': {'apiUrl': 'https://box.example.test', 'channel': 'stable', 'path': '/fixture/box.json'},
        }
        self.assertEqual(onboarding._account_identity(status), {'email': 'box@example.test'})
        status['config']['email'] = 'unrelated@example.test'
        self.assertEqual(onboarding._account_identity(status), {'email': 'box@example.test'})
        profile = {'provider_binding': {'billing_scope': 'personal',
                                       'account_identity': {'email': 'box@example.test'}}}
        controller = types.SimpleNamespace(box=lambda *args: status)
        onboarding.verify_provider_binding(controller, profile)
        status['account']['identifier'] = 'other@example.test'
        with self.assertRaisesRegex(ValueError, 'does not match'):
            onboarding.verify_provider_binding(controller, profile)

    def test_box_identity_rejects_missing_inactive_or_ambiguous_account(self):
        cases = [
            {'config': {'email': 'not-an-account@example.test'}},
            {'account': {}, 'billing': {'email': 'not-an-account@example.test'}},
            {'account': {'identifier': 'box@example.test', 'loginState': 'logged_out'}},
            {'account': {'identifier': None, 'loginState': 'active'}},
            {'account': {'identifier': 'box@example.test\n', 'loginState': 'active'}},
            {'account': {'identifier': 'box\x1b[31m@example.test', 'loginState': 'active'}},
            {'account': {'identifier': 'not-an-email', 'loginState': 'active'}},
            {'account': {'identifier': 'box@example.test', 'email': 'other@example.test'}},
        ]
        for status in cases:
            with self.subTest(status=status), self.assertRaises(ValueError):
                onboarding._account_identity(status)
        self.assertEqual(onboarding._account_identity({'account': {'email': 'box@example.test'}}),
                         {'email': 'box@example.test'})
        self.assertEqual(onboarding._account_identity({'account': {'accountId': 'account-fixture'}}),
                         {'id': 'account-fixture'})

    def test_onboarding_reconciles_environment_timeout_and_records_safe_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); calls = []; listed = 0
            class FakeBoxError(RuntimeError): pass
            def box(*args):
                nonlocal listed
                calls.append(args)
                if args[0] == 'status':
                    return {'account': {'identifier': 'box@example.test', 'loginState': 'active',
                                        'plan': 'trial', 'status': 'active', 'suspension': None}}
                if args[0] == 'limits': return {'fixture': True}
                if args[:2] == ('env', 'list'):
                    listed += 1
                    return {'environments': [] if listed == 1 else [{'name': environment[0]}]}
                if args[:2] == ('env', 'new'):
                    environment.append(args[2]); raise subprocess.TimeoutExpired('box env new', 180)
                if args[:2] == ('env', 'set'):
                    return {'environment': {'name': environment[0], 'safeForThirdParties': True}}
                raise AssertionError(args)
            controller = types.SimpleNamespace(STATE=root, BOX=Path('/fake/box'), BoxCommandError=FakeBoxError,
                                               box=box, check_allowance=lambda *args, **kwargs: None)
            request = {'project': {'name': 'dashboard', 'repository': 'acme/dashboard', 'backend': 'box'},
                       'clients': [{'client': 'codex'}]}
            environment = []
            output = io.StringIO()
            with patch.object(onboarding, '_public_repository', return_value=True), \
                    patch('builtins.input', side_effect=['']) as confirm, \
                    contextlib.redirect_stdout(output):
                profile, clients = onboarding.ensure_profile(controller, request)
            confirm.assert_called_once_with('Create the project environment? [Y/n]: ')
            self.assertEqual(clients, ['codex'])
            self.assertIn('Next: prepare Box, then open browser sign-in for Codex.', output.getvalue())
            self.assertNotIn('Personal skill', output.getvalue())
            self.assertNotIn('GitHub account', output.getvalue())
            self.assertNotIn('Box billing [', output.getvalue())
            self.assertIn('  Billing  personal', output.getvalue())
            self.assertIn('  Machine  small · up to 2 hours', output.getvalue())
            self.assertTrue(profile['provider_binding']['safe_for_third_parties'])
            self.assertEqual(sum(call[:2] == ('env', 'new') for call in calls), 1)
            saved_journal = json.loads((root / 'projects/dashboard/onboarding.json').read_text())
            self.assertEqual(saved_journal['stage'], 'profile-saved')
            self.assertEqual(saved_journal['account_identity'], {'email': 'box@example.test'})
            self.assertEqual(saved_journal['providers'], {'codex': {}})
            saved_agents = json.loads((root / 'agent-profiles/dashboard-agents/profile.json').read_text())
            self.assertEqual(saved_agents['providers'], {'codex': {}})
            foreign = types.SimpleNamespace(box=lambda *args: {'account': {'email': 'other@example.test'}})
            with self.assertRaisesRegex(ValueError, 'does not match'):
                onboarding.verify_provider_binding(foreign, profile)

    def test_onboarding_decline_or_interruption_does_not_create_environment(self):
        for answer in ('n', 'no', 'invalid', EOFError(), KeyboardInterrupt()):
            with self.subTest(answer=answer), tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ):
                root = Path(tmp)
                calls = []
                def box(*args):
                    calls.append(args)
                    if args == ('status', '--org', 'personal'):
                        return {'account': {'identifier': 'box@example.test', 'loginState': 'active'}}
                    if args == ('limits', '--org', 'personal'):
                        return {}
                    raise AssertionError('Unexpected provider mutation: ' + str(args))
                controller = types.SimpleNamespace(STATE=root, box=box, check_allowance=lambda *args, **kwargs: None)
                request = {'project': {'name': 'dashboard', 'repository': 'acme/dashboard', 'backend': 'box'},
                           'clients': [{'client': 'codex'}]}
                expected_error = type(answer) if isinstance(answer, BaseException) else ValueError
                with patch.object(onboarding, '_public_repository', return_value=True), \
                        patch('builtins.input', side_effect=[answer]), contextlib.redirect_stdout(io.StringIO()), \
                        self.assertRaises(expected_error):
                    onboarding.ensure_profile(controller, request)
                self.assertEqual(calls, [('status', '--org', 'personal'), ('limits', '--org', 'personal')])
                self.assertEqual(list(root.iterdir()), [])

    def test_public_repository_probe_ignores_ambient_credentials(self):
        completed = types.SimpleNamespace(returncode=0)
        with patch.object(onboarding.subprocess, 'run', return_value=completed) as run:
            self.assertTrue(onboarding._public_repository('https://github.com/octocat/hello-world'))
        argv = run.call_args.args[0]
        environment = run.call_args.kwargs['env']
        self.assertIn('credential.helper=', argv)
        self.assertEqual(argv[-1], 'https://github.com/octocat/hello-world.git')
        self.assertEqual(environment['GIT_CONFIG_NOSYSTEM'], '1')
        self.assertEqual(environment['GIT_TERMINAL_PROMPT'], '0')
        self.assertNotIn('GH_TOKEN', environment)

    def test_existing_profile_with_unverified_identity_still_requires_native_login(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = {'name': 'dashboard', 'repository': 'acme/dashboard',
                       'agent_profile': 'dashboard-agents', 'clients': ['codex']}
            agent_auth.private_write(root / 'projects/dashboard/profile.json', profile)
            agent_auth.private_write(root / 'agent-profiles/dashboard-agents/profile.json', {
                'version': 1, 'name': 'dashboard-agents', 'providers': {'codex': {}}})
            agent_auth.private_write(root / 'credentials/dashboard/agents/codex.json', {
                'project': 'dashboard', 'profile': 'dashboard-agents', 'provider': 'codex',
                'contents': {'tokens': {'access_token': 'synthetic-access'}}})
            controller = types.SimpleNamespace(STATE=root)
            request = {'project': {'name': 'dashboard', 'repository': 'acme/dashboard', 'backend': 'box'}}
            with patch.object(onboarding, 'validate', side_effect=lambda value: value):
                saved, pending = onboarding.ensure_profile(controller, request)
            self.assertEqual(saved, profile)
            self.assertEqual(pending, ['codex'])

    def test_interrupted_onboarding_rejects_a_different_box_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal = root / 'projects/dashboard/onboarding.json'
            journal.parent.mkdir(parents=True)
            journal.write_text(json.dumps({
                'version': 1, 'project': 'dashboard', 'repository': 'acme/dashboard', 'provider': 'box',
                'stage': 'environment-created', 'environment': 'allset-dashboard-0123456789',
                'billing_scope': 'personal-org', 'account_identity': {'email': 'first@example.test'},
                'providers': {'codex': {'account_email': 'work@example.test'}},
                'personal_skills': [], 'github': None, 'infisical': None,
                'environment_create_attempted': True}))
            journal.chmod(0o600)
            controller = types.SimpleNamespace(
                STATE=root, BOX=Path('/fake/box'), BoxCommandError=RuntimeError,
                box=lambda *args: {'account': {'email': 'second@example.test'}} if args[0] == 'status' else {},
                check_allowance=lambda *args, **kwargs: None)
            request = {'project': {'name': 'dashboard', 'repository': 'acme/dashboard', 'backend': 'box'}}
            with self.assertRaisesRegex(ValueError, 'interrupted onboarding journal'):
                onboarding.ensure_profile(controller, request)

    def test_verified_environment_stage_is_checked_without_repeating_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); calls = []
            journal = root / 'projects/dashboard/onboarding.json'
            journal.parent.mkdir(parents=True)
            journal.write_text(json.dumps({
                'version': 1, 'project': 'dashboard', 'repository': 'acme/dashboard', 'provider': 'box',
                'stage': 'environment-safe', 'environment': 'allset-dashboard-0123456789',
                'billing_scope': 'personal-org', 'account_identity': {'email': 'box@example.test'},
                'providers': {'codex': {'account_email': 'work@example.test'}},
                'personal_skills': [], 'github': None, 'infisical': None,
                'environment_create_attempted': True}))
            journal.chmod(0o600)
            def box(*args):
                calls.append(args)
                if args[0] == 'status': return {'account': {'email': 'box@example.test'}}
                if args[0] == 'limits': return {}
                if args[:2] == ('env', 'list'):
                    return {'environments': [{'name': 'allset-dashboard-0123456789',
                                              'safeForThirdParties': True}]}
                raise AssertionError(args)
            controller = types.SimpleNamespace(STATE=root, BOX=Path('/fake/box'), BoxCommandError=RuntimeError,
                                               box=box, check_allowance=lambda *args, **kwargs: None)
            request = {'project': {'name': 'dashboard', 'repository': 'acme/dashboard', 'backend': 'box'}}
            profile, clients = onboarding.ensure_profile(controller, request)
            self.assertEqual(clients, ['codex'])
            self.assertEqual(profile['box_environment'], 'allset-dashboard-0123456789')
            self.assertFalse(any(call[:2] == ('env', 'set') for call in calls))

    def test_session_install_preserves_a_native_local_binary_behind_the_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp); local = home / '.local/bin'; local.mkdir(parents=True)
            command = local / 'codex'; command.write_bytes(b'\x00native-client'); command.chmod(0o700)
            checkout = home / 'checkout'; checkout.mkdir()
            with patch.object(session_context.Path, 'home', return_value=home):
                context = session_context.install(['codex'], None, 'dashboard', str(checkout), {})
            native = Path(context['native']['codex'])
            self.assertEqual(native.read_bytes(), b'\x00native-client')
            self.assertIn(session_context.MARKER, command.read_text())
            self.assertNotEqual(native, command)

    def test_session_launch_preserves_argv_cwd_and_uses_curated_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); checkout = root / 'checkout'; child = checkout / 'nested'; child.mkdir(parents=True)
            native = root / 'native-codex'; native.write_text('fixture')
            context = {'project': 'dashboard', 'checkout': str(checkout), 'native': {'codex': str(native)},
                       'clients': ['codex'], 'session_environment': {}, 'infisical': False}
            module = root / 'session_context.py'; module.write_text('')
            (root / 'context.json').write_text(json.dumps(context))
            before = Path.cwd()
            try:
                os.chdir(child)
                with patch.object(session_context, '__file__', str(module)), \
                     patch.object(session_context.os, 'execve', side_effect=RuntimeError('exec')) as execute:
                    with self.assertRaisesRegex(RuntimeError, 'exec'):
                        session_context.main('codex', ['resume', '--last'])
                self.assertEqual(execute.call_args.args[0], str(native))
                self.assertEqual(execute.call_args.args[1], [str(native), 'resume', '--last'])
            finally:
                os.chdir(before)


result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeTests))
raise SystemExit(0 if result.wasSuccessful() else 1)
