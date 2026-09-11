import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('bridge',Path(__file__).with_name('mcp.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class Transport(unittest.TestCase):
 def test_startup_preserves_curated_failure_without_dumping_protocol_or_transport(self):
  owner={'machine_id':'bx_saved'}
  fake=types.SimpleNamespace(c=types.SimpleNamespace(ssh_args=lambda target:['ssh','fixture']))
  payload={'name':'dashboard','repository':'acme/dashboard','mcps':{}}
  result=types.SimpleNamespace(returncode=1,stdout='synthetic-secret',
    stderr='raw transport synthetic-secret\nallset mcp: Codex managed MCP settings changed; reconcile before syncing\n')
  with patch.object(b.subprocess,'run',return_value=result) as run:
   with self.assertRaisesRegex(RuntimeError,'managed MCP settings changed') as error:
    b.sync_mcps(fake,owner,payload,'runtime',quiet=True)
   self.assertNotIn('synthetic-secret',str(error.exception))
   self.assertTrue(run.call_args.kwargs['capture_output'])
  result.returncode=0
  with patch.object(b.subprocess,'run',return_value=result), contextlib.redirect_stdout(io.StringIO()) as out:
   b.sync_mcps(fake,owner,payload,'runtime',quiet=True)
  self.assertEqual(out.getvalue(),'')

 def test_stopped_or_restoring_vm_never_applies(self):
  for state in ('stopped','restoring','ready'):
   with self.subTest(state=state), tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'dashboard').mkdir()
    fake=types.ModuleType('projects');fake.PROJECTS=root
    fake.project=lambda name:{'name':name}
    fake.machine=lambda name:{'machine_id':'bx_saved'}
    def box(op,id):
     self.assertEqual((op,id),('info','bx_saved'))
     return {'box':{'state':state}}
    fake.c=types.SimpleNamespace(box=box,refresh_ssh=lambda owner:None)
    def not_ready(owner,timeout):
     self.assertEqual(timeout,0)
     raise RuntimeError('still hydrating')
    fake.wait_project_filesystem=not_ready
    old=sys.argv;sys.argv=['bridge',tmp,json.dumps({'name':'dashboard','repository':'acme/dashboard','mcps':{}}),'runtime','mcp-sync','']
    sys.modules['projects']=fake
    try:
     with self.assertRaises(RuntimeError): b.mcp_main()
    finally:
     sys.argv=old;sys.modules.pop('projects',None)
if __name__=='__main__': unittest.main()
