"""Executable checks for the skill helper; no provider keys or desktop required."""
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'skills/graphpaper/scripts/gp.py'


def load():
    spec = importlib.util.spec_from_file_location('gp_skill', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillContract(unittest.TestCase):
    def test_pack_exists(self):
        self.assertTrue(SCRIPT.is_file(), 'No headless helper is available to an agent')
        self.assertTrue((ROOT/'skills/graphpaper/SKILL.md').is_file(), 'No discoverable GraphPaper skill')


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SCRIPT.exists():
            raise unittest.SkipTest('Implementation missing; pack contract is the RED test')
        cls.gp = load()

    def setUp(self):
        self.events = []
        events = self.events
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def reply(self, status, value, **headers):
                data=json.dumps(value).encode()
                self.send_response(status)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(data)))
                for k,v in headers.items(): self.send_header(k.replace('_','-'),v)
                self.end_headers(); self.wfile.write(data)
            def do_GET(self):
                events.append((self.command,self.path,dict(self.headers),b''))
                if self.path=='/': return self.reply(200,{},Set_Cookie='gp_session=test-session; Path=/; HttpOnly')
                if 'gp_session=test-session' not in self.headers.get('Cookie','') or self.headers.get('X-GraphPaper')!='1':
                    return self.reply(403,{'detail':'Session missing'})
                if self.path=='/api/redirect':
                    return self.reply(302,{},Location='http://example.com/no')
                return self.reply(200,{'ok':True})
            def do_POST(self):
                data=self.rfile.read(int(self.headers.get('Content-Length',0)))
                events.append((self.command,self.path,dict(self.headers),data))
                if self.path=='/api/conflict': return self.reply(409,{'detail':'Newer project version; refresh'})
                return self.reply(200,{'ok':True})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.client=self.gp.Client('http://127.0.0.1:'+str(self.server.server_port))

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()

    def test_session_handshake_without_opening_a_browser(self):
        self.assertTrue(self.client.request('GET','/api/bootstrap')['ok'])
        self.assertEqual([e[1] for e in self.events],['/','/api/bootstrap'])
        self.assertEqual(self.events[-1][2]['X-Graphpaper'],'1')

    def test_remote_urls_and_path_escapes_refused(self):
        for url in ['https://example.com','http://0.0.0.0:8765','http://localhost:8765','http://127.0.0.1:8765@evil.com','http://127.0.0.1:8765/?x=1','http://127.0.0.1:8765/#fragment']:
            with self.subTest(url=url), self.assertRaises(ValueError): self.gp.Client(url)
        for path in ['https://evil.com','//evil.com','/api/../foo','/api/%2e%2e/foo','/api/%252e%252e/foo','/api/foo\\bar','/api/foo#fragment']:
            with self.subTest(path=path), self.assertRaises(ValueError): self.client.request('GET',path)
        self.assertFalse(self.events)

    def test_redirect_not_followed(self):
        with self.assertRaises(self.gp.ClientError): self.client.request('GET','/api/redirect')
        self.assertEqual(len(self.events),2)

    def test_conflict_is_not_silently_retried(self):
        with self.assertRaises(self.gp.ClientError) as caught:
            self.client.request('POST','/api/conflict',{'version':1})
        self.assertEqual(caught.exception.status,409)
        self.assertEqual(sum(e[0]=='POST' for e in self.events),1)

    def test_multipart_file_and_role_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'writing sample.txt'
            for original in (b'Specific author voice.\n', b'Specific author voice.\r\n'):
                with self.subTest(original=original):
                    path.write_bytes(original)
                    self.client.upload('/api/projects/p_one/sources/file',path,role='canon')
                    body=self.events[-1][3]
                    self.assertIn(b'name="role"\r\n\r\ncanon',body)
                    self.assertIn(b'filename="writing sample.txt"',body)
                    self.assertIn(original,body)

    def test_output_refuses_accidental_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'draft.md';p.write_bytes(b'keep')
            with self.assertRaises(FileExistsError): self.gp.save_bytes(p,b'new')
            self.assertEqual(p.read_bytes(),b'keep')
            self.gp.save_bytes(p,b'new',overwrite=True)
            self.assertEqual(p.read_bytes(),b'new')

    def test_wait_completed_and_failed_are_different(self):
        with patch.object(self.client,'request',return_value={'id':'j_one','state':'completed'}):
            self.assertEqual(self.client.wait('j_one',1)['state'],'completed')
        with patch.object(self.client,'request',return_value={'id':'j_one','state':'failed','error':'Controlled failure'}):
            with self.assertRaises(self.gp.JobError) as e: self.client.wait('j_one',1)
            self.assertEqual(e.exception.job['state'],'failed')

    def test_wait_timeout_reports_job_without_restarting_it(self):
        with patch.object(self.client,'request',return_value={'id':'j_one','state':'running'}) as req:
            with self.assertRaises(self.gp.JobTimeout) as e: self.client.wait('j_one',.02,interval=.005)
            self.assertEqual(e.exception.job['id'],'j_one')
            self.assertTrue(all(call.args[0]=='GET' for call in req.call_args_list))

    def test_settings_merge_and_explicit_cloud_consent(self):
        old={'provider':'openrouter','model':'keep-model','max_calls':9,'allow_cloud':False,'keys':{},'data_directory':'private'}
        calls=[]
        def request(method,path,body=None):
            calls.append((method,path,body))
            return old if method=='GET' else {'keys':{'typesafe':True}}
        with patch.object(self.client,'request',side_effect=request), patch.dict('os.environ',{'TEST_JEV_KEY':'never-log-this'}):
            self.client.configure({'jev_provider':'typesafe'},['typesafe=TEST_JEV_KEY'],allow_cloud=True)
        body=calls[-1][2]
        self.assertEqual(body['model'],'keep-model');self.assertEqual(body['max_calls'],9)
        self.assertEqual(body['api_keys'],{'typesafe':'never-log-this'})
        self.assertFalse(body['remember_keys']);self.assertTrue(body['allow_cloud'])
        self.assertNotIn('data_directory',body)
        with self.assertRaises(ValueError): self.client.configure({'allow_cloud':True},[],allow_cloud=False)

    def test_ephemeral_key_setup_does_not_erase_existing_credentials(self):
        with patch.object(self.client,'request',return_value={'remember_keys':True,'keys':{'openrouter':True}}) as req, patch.dict('os.environ',{'OTHER_KEY':'secret'}):
            with self.assertRaises(self.gp.ClientError):
                self.client.configure({},['typesafe=OTHER_KEY'])
            self.assertEqual(req.call_count,1)

    def test_explicit_workspace_and_single_writer_lock(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'agent'
            with self.gp.workspace_lock(root):
                self.assertTrue((root/'.graphpaper-agent.json').exists())
                with self.assertRaises(self.gp.ClientError):
                    with self.gp.workspace_lock(root): pass
            with self.gp.workspace_lock(root): pass
            legacy=Path(d)/'desktop';legacy.mkdir();(legacy/'studio.sqlite3').write_bytes(b'unchanged')
            with self.assertRaises(self.gp.ClientError):
                with self.gp.workspace_lock(legacy): pass
            self.assertEqual((legacy/'studio.sqlite3').read_bytes(),b'unchanged')


if __name__=='__main__': unittest.main()
