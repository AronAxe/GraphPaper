"""Real backend + loopback HTTP; all model responses explicitly synthetic.

Set GRAPHPAPER_REQUIRE_BACKEND_TESTS=1 in CI so missing dependencies fail rather
than turning an absent backend into successful compatibility evidence.
"""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
SCRIPT=ROOT/'skills/graphpaper/scripts/gp.py'
spec=importlib.util.spec_from_file_location('gp_skill_backend',SCRIPT)
gp=importlib.util.module_from_spec(spec);spec.loader.exec_module(gp)


def dependencies():
    try:
        import uvicorn
        from graphpaper.server import create_app
        spec=importlib.util.spec_from_file_location('gp_scripted_clients',ROOT/'tests/conftest.py')
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        return uvicorn,create_app,fixture.ScriptedClients
    except (ModuleNotFoundError,FileNotFoundError):
        if os.environ.get('GRAPHPAPER_REQUIRE_BACKEND_TESTS')=='1': raise
        raise unittest.SkipTest('GraphPaper source requirements not present; CI requires them explicitly')


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uvicorn,cls.factory,cls.scripted=dependencies()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='graphpaper-skill-test-')
        self.root=Path(self.temp.name)
        self.app=type(self).factory(self.root/'data')
        self.app.state.runner.clients_factory=type(self).scripted
        sock=socket.socket();sock.bind(('127.0.0.1',0))
        self.url='http://127.0.0.1:'+str(sock.getsockname()[1])
        self.server=self.uvicorn.Server(self.uvicorn.Config(self.app,log_level='error',access_log=False))
        self.thread=threading.Thread(target=lambda:self.server.run(sockets=[sock]),daemon=True)
        self.thread.start()
        until=time.monotonic()+10
        while not self.server.started and self.thread.is_alive() and time.monotonic()<until: time.sleep(.01)
        self.assertTrue(self.server.started)
        self.c=gp.Client(self.url)
        self.c.configure({'model':'synthetic/test-model','graph_engine':'native','max_candidates':6,'max_calls':80,'refine':False,'jev_provider':'openrouter'},[],allow_cloud=True)

    def tearDown(self):
        for job in self.app.state.runner.jobs.values(): job.cancel.set()
        self.app.state.runner.pool.shutdown(wait=True,cancel_futures=True)
        self.server.should_exit=True;self.thread.join(10)
        self.assertFalse(self.thread.is_alive())
        self.temp.cleanup()

    def create(self,mode='nonfiction'):
        return self.c.request('POST','/api/projects',{'title':'Synthetic agent example','mode':mode})

    def job(self,pid,action):
        job=self.c.request('POST',f'/api/projects/{pid}/jobs',{'action':action})
        return self.c.wait(job['id'],30,interval=.01)

    def test_pipeline_creates_graph_angles_outline_draft_and_exports(self):
        for mode in ('nonfiction','polemic','fiction'):
            with self.subTest(mode=mode):
                p=self.create(mode);pid=p['id'];url='/api/projects/'+pid
                role='canon' if mode=='fiction' else 'evidence'
                p=self.c.request('POST',url+'/sources/text',{'title':'Synthetic notes','text':'An invented example: Mira studies a shared public space. Individual choice can have an unintended consequence.','role':role})
                for action in ('graph','angles'):
                    self.assertEqual(self.job(pid,action)['state'],'completed')
                p=self.c.request('GET',url)
                self.assertTrue(p['graph']['nodes']);self.assertTrue(p['angles'])
                p=self.c.request('PATCH',url,{'version':p['version'],'selected_angle':p['angles'][0]['id']})
                self.job(pid,'outline');self.job(pid,'draft')
                p=self.c.request('GET',url)
                self.assertTrue(p['draft']);self.assertTrue(p['review']['summary'])
                exported=self.c.request('GET',url+'/export/md',binary=True)
                self.assertIn(p['draft'].splitlines()[0].encode(),exported)
                self.assertTrue(self.c.request('GET',url+'/revisions'))
                self.assertIn('state',self.c.request('GET',url+'/system-one'))
                self.assertTrue(any(a['usage']['calls'] for a in p['activity']))

    def test_inbox_once_and_fetch_not_second_upload(self):
        p=self.create();url='/api/projects/'+p['id']
        info=self.c.request('GET',url+'/workspace')
        folder=Path(info['inbox']);(folder/'Evidence'/'once.txt').write_text('A single imported source.',encoding='utf-8')
        scan=self.c.request('POST',url+'/workspace/scan',{'force':True})
        self.assertEqual(sum(e['status']=='imported' for e in scan['events']),1)
        self.c.request('POST',url+'/workspace/scan',{'force':True})
        p=self.c.request('GET',url)
        self.assertEqual(len(p['sources']),1);self.assertEqual(p['usage']['calls'],0)

    def test_voice_library_reuse_is_not_project_evidence(self):
        voice=self.c.request('POST','/api/voices',{'name':'Synthetic sharp voice','instructions':'Use direct arguments and varied rhythm; preserve deliberate force.'})
        path=self.root/'voice.txt';path.write_text('A synthetic sample used only to test storage separation.',encoding='utf-8')
        self.c.upload('/api/voices/'+voice['id']+'/samples/file',path)
        for _ in range(2):
            p=self.create('polemic')
            p=self.c.request('POST','/api/projects/'+p['id']+'/voice/apply',{'version':p['version'],'voice_id':voice['id']})
            self.assertEqual(p['sources'],[]);self.assertEqual(p['usage']['calls'],0)
            self.assertEqual(p['voice_profile']['library_id'],voice['id'])
        payload=self.c.request('GET','/api/voices/'+voice['id']+'/export')
        self.assertEqual(payload['format'],'graphpaper-voice-1')
        self.assertFalse(payload['profile']['sample_ids'])

    def test_stale_save_and_failure_preserve_existing_draft(self):
        p=self.create();url='/api/projects/'+p['id']
        p2=self.c.request('PATCH',url,{'version':p['version'],'draft':'Keep the original author argument.'})
        with self.assertRaises(gp.ClientError) as e:
            self.c.request('PATCH',url,{'version':p['version'],'draft':'Not authorized to erase newer work.'})
        self.assertEqual(e.exception.status,409)
        with self.assertRaises(gp.JobError): self.job(p['id'],'angles')
        self.assertEqual(self.c.request('GET',url)['draft'],p2['draft'])
        self.assertIsInstance(self.c.request('POST',url+'/craft/audit',{}),dict)

    def test_science_plan_uses_real_contract_and_no_author_attestations(self):
        p=self.create('science');url='/api/projects/'+p['id']
        plan={**p['research']['plan'],'question':'Synthetic research question for API testing','databases':['pubmed','semantic_scholar','arxiv','crossref','europe_pmc']}
        p=self.c.request('PUT',url+'/research/plan',{'version':p['version'],'plan':plan})
        self.assertEqual(p['research']['plan']['databases'],plan['databases'])
        self.assertFalse(p['research']['acknowledgements'])
        self.assertFalse(self.c.request('GET',url+'/research/readiness')['submission_allowed'])


class HeadlessProcessTests(unittest.TestCase):
    def test_real_serve_command_persists_without_a_desktop(self):
        dependencies()
        with tempfile.TemporaryDirectory(prefix='graphpaper-agent-host-') as d:
            root=Path(d)/'workspace'
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            log=Path(d)/'host.log'
            with log.open('wb') as output:
                proc=subprocess.Popen([sys.executable,str(SCRIPT),'serve','--repo',str(ROOT),'--data-dir',str(root),'--port',str(port)],stdout=output,stderr=output,cwd=ROOT)
                try:
                    c=gp.Client('http://127.0.0.1:'+str(port),timeout=1)
                    end=time.monotonic()+20
                    while True:
                        try:
                            info=c.request('GET','/api/bootstrap');break
                        except gp.ClientError:
                            if proc.poll() is not None or time.monotonic()>end:
                                self.fail(log.read_text(encoding='utf-8',errors='replace'))
                            time.sleep(.1)
                    self.assertEqual(Path(info['settings']['data_directory']).resolve(),root.resolve())
                    self.assertFalse(info['settings']['allow_cloud'])
                    p=c.request('POST','/api/projects',{'title':'Agent-only project','mode':'nonfiction'})
                    self.assertTrue((root/'studio.sqlite3').is_file())
                    result=subprocess.run([sys.executable,str(SCRIPT),'--url',c.url,'doctor'],capture_output=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertTrue(json.loads(result.stdout)['ready'])
                    self.assertEqual(json.loads(result.stdout)['projects'][0]['id'],p['id'])
                finally:
                    proc.terminate()
                    try: proc.wait(timeout=10)
                    except subprocess.TimeoutExpired: proc.kill();proc.wait(timeout=5)
            self.assertNotIn('Python.Runtime',log.read_text(encoding='utf-8',errors='replace'))


if __name__=='__main__': unittest.main()
