import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

spec = importlib.util.spec_from_file_location('runtime', Path(__file__).with_name('runtime.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class NativeConfigs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.servers = {'trigger': {'preset': 'trigger', 'project_ref': 'proj_dashboard'}}

    def apply(self, servers=None, project='dashboard'):
        r.apply(self.home, project, 'acme/dashboard', self.servers if servers is None else servers)

    def test_idempotent_native_configs_preserve_unmanaged_settings(self):
        r.private_write(self.home / '.codex/config.toml', '# user comment\nmodel = "kept"\n[mcp_servers.mine]\nurl = "https://example.com"\n')
        r.private_write(self.home / '.claude.json', json.dumps({'oauthAccount': {'marker': 'retained'}, 'mcpServers': {'mine': {'url': 'https://example.com'}}}))
        self.apply()
        paths = [self.home / '.codex/config.toml', self.home / '.claude.json', self.home / '.cursor/mcp.json']
        first = [p.read_bytes() for p in paths]
        self.apply()
        self.assertEqual(first, [p.read_bytes() for p in paths])
        codex = tomllib.loads(paths[0].read_text())
        self.assertEqual(codex['model'], 'kept')
        self.assertIs(codex['mcp_servers']['trigger']['required'], True)
        self.assertIn('# user comment', paths[0].read_text())
        for index, client in enumerate(r.CLIENTS):
            document = tomllib.loads(paths[index].read_text()) if client == 'codex' else json.loads(paths[index].read_text())
            servers = document['mcp_servers' if client == 'codex' else 'mcpServers']
            args = servers['trigger']['args']
            self.assertIn('--readonly', args)
            self.assertIn('--profile', args)
            self.assertIn('dashboard', args)
            self.assertIn('TRIGGER_ACCESS_TOKEN', args)
            self.assertEqual(paths[index].stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(paths[1].read_text())['oauthAccount'], {'marker': 'retained'})

    def test_native_json_reformat_does_not_cause_unnecessary_writes(self):
        self.apply()
        path = self.home / '.claude.json'
        native = json.loads(path.read_text())
        native['nativeAddedSetting'] = True
        path.write_text(json.dumps(native, separators=(',', ':')))
        before = path.read_bytes()
        self.apply()
        self.assertEqual(before, path.read_bytes())

    def test_other_project_rejected_and_trigger_auth_homes_are_distinct(self):
        self.apply()
        with self.assertRaisesRegex(ValueError, 'another project'):
            self.apply(project='shop')
        a = r.render(self.home, 'dashboard', self.servers)
        b = r.render(self.home, 'shop', self.servers)
        self.assertNotEqual(a['codex']['trigger']['args'], b['codex']['trigger']['args'])

    def test_conflict_preflight_leaves_all_clients_untouched(self):
        r.private_write(self.home / '.cursor/mcp.json', '{"mcpServers":{"trigger":{"command":"my-server"}}}')
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            self.apply()
        self.assertFalse((self.home / '.codex/config.toml').exists())
        self.assertFalse((self.home / '.claude.json').exists())

    def test_edited_managed_entry_is_not_overwritten(self):
        self.apply()
        path = self.home / '.cursor/mcp.json'
        d = json.loads(path.read_text()); d['mcpServers']['trigger']['command'] = 'edited'
        path.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.apply()
        self.assertEqual(json.loads(path.read_text()), d)

    def test_recover_interrupted_apply_and_remove_only_owned(self):
        self.apply()
        changed = copy.deepcopy(self.servers)
        changed['trigger']['read_only'] = False
        original = r.private_write
        def fail_on_cursor(path, text):
            if path.name == 'mcp.json':
                raise OSError('simulated interrupted write')
            original(path, text)
        r.private_write = fail_on_cursor
        try:
            with self.assertRaises(OSError): self.apply(changed)
        finally:
            r.private_write = original
        self.apply(changed)
        self.apply({})
        self.assertNotIn('trigger', tomllib.loads((self.home / '.codex/config.toml').read_text()).get('mcp_servers', {}))

    def test_client_native_environment_references(self):
        servers = {'api': {'url': 'https://example.com/mcp', 'bearer_token_env_var': 'API_TOKEN'},
                   'stdio': {'command': 'server', 'env_vars': ['API_TOKEN']}}
        entries = r.render(self.home, 'dashboard', servers)
        self.assertEqual(entries['codex']['api']['bearer_token_env_var'], 'API_TOKEN')
        for name in servers:
            self.assertIs(entries['codex'][name]['required'], True)
            self.assertEqual(entries['codex'][name]['startup_timeout_sec'], 60)
            self.assertNotIn('required', entries['claude'][name])
            self.assertNotIn('required', entries['cursor'][name])
        self.assertEqual(entries['claude']['api']['headers']['Authorization'], 'Bearer ${API_TOKEN}')
        self.assertEqual(entries['cursor']['api']['headers']['Authorization'], 'Bearer ${env:API_TOKEN}')
        self.assertEqual(entries['codex']['stdio']['env_vars'], ['API_TOKEN'])
        self.assertEqual(entries['cursor']['stdio']['env']['API_TOKEN'], '${env:API_TOKEN}')

if __name__ == '__main__': unittest.main()
