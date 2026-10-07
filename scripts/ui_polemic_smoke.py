"""Real local HTTP UI checks for mode conversion, brief controls and voice-aware stages.

Model responses are explicitly synthetic; a separate opt-in script tests Codex.
"""
from pathlib import Path
import argparse
import json
import socket
import sys
import tempfile
import threading
import time
import traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright,expect
from graphpaper.server import create_app
from graphpaper.models import Settings,Angle
from tests.polemic_fixtures import project
from tests.conftest import ScriptedClients
import uvicorn


class EditorialClients(ScriptedClients):
    observed=[]
    def complete(self,system,user,**kwargs):
        data=json.loads(user);self.observed.append(data)
        result=super().complete(system,user,**kwargs)
        if data['task'].startswith('Propose up to six'):
            result['angles'][0].update(title='The enthusiasm is the indictment',thesis=data['editorial_contract']['thesis'],hook='The demonstration did not need a conscience to expose the lack of one in its sales pitch.',counterargument='')
        if data['task'].startswith('Act as a rigorous'):
            result['authorial_assessment']={'intent_preserved':True,'stance_preserved':True,'voice_preserved':True,'summary':'Synthetic assessment: the chosen position is retained.'}
        return result


def wait(page,action):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        status=page.evaluate('() => state.job && ({action:state.job.action,state:state.job.state,error:state.job.error})')
        if status and status['action']==action:
            if status['state']=='completed':
                # Job completion precedes the UI's project refresh.
                p=page.evaluate('() => state.p')
                if action=='angles' and p['angles_context_hash']:return
                if action=='outline' and p['outline_context_hash']:return
                if action=='draft' and p['review']['context_hash']:return
                if action not in {'angles','outline','draft'}:return
            if status['state'] in {'failed','cancelled'}:raise AssertionError(status)
        page.wait_for_timeout(100)
    raise AssertionError('UI stage did not complete: '+action)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'test-results/polemic-ui')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    report={'real_http_browser':True,'live_model':False,'synthetic_material':True,'checks':[],'page_errors':[],'ok':False}
    def check(label):report['checks'].append(label);print('PASS',label,flush=True)
    with tempfile.TemporaryDirectory(prefix='GraphPaper-polemic-ui-') as temp:
        app=create_app(Path(temp));app.state.runner.clients_factory=EditorialClients
        app.state.store.set_settings(Settings(model='fixture',allow_cloud=True,refine=False).model_dump())
        p=project('nonfiction');p.angles=[Angle(title='Old cautious angle',thesis='The essay would ask whether criticism may be warranted.')]
        p.draft='An existing author manuscript. [S1]';app.state.store.create(p);app.state.store.snapshot(p,'Existing manuscript')
        original=p.model_dump();pid=p.id
        client=TestClient(app);client.get('/');client.headers['X-GraphPaper']='1'
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,log_level='error'));thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        while not server.started:time.sleep(.05)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1040});page.set_default_timeout(12000)
            page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            try:
                page.goto(f'http://127.0.0.1:{port}/');page.wait_for_selector('.welcome')
                expect(page.locator('.welcome-card')).to_have_count(4)
                page.screenshot(path=str(out/'four-modes.png'),full_page=True)
                check('Four distinct modes are available, including Polemic')
                page.locator('[data-action="open-project"][data-id="'+pid+'"]').click();page.wait_for_selector('#graph-svg')
                page.get_by_role('button',name='Nonfiction · Change',exact=True).click()
                page.locator('#writing-mode').select_option('polemic')
                page.get_by_role('button',name='Apply writing mode',exact=True).click()
                expect(page.locator('.modal')).to_have_count(0)
                after=client.get('/api/projects/'+pid).json()
                assert after['mode']=='polemic'
                for key in ['sources','graph','draft','voice_profile','angles']:assert after[key]==original[key]
                check('Existing project converts to Polemic without replacing its sources, graph, voice or draft')
                page.locator('.nav-link[data-tab="angles"]').click()
                expect(page.locator('#editorial-status')).to_contain_text('predate the current brief')
                check('Old angles are explicitly marked stale instead of pretending the brief rewrote them')
                page.get_by_role('button',name='Creative brief',exact=True).click()
                page.locator('#b-thesis').fill('The enthusiasm is the indictment. Make that case, not a neutral inquiry.')
                page.locator('#b-rhetorical_force').evaluate("el => {el.value=95;el.dispatchEvent(new Event('input',{bubbles:true}));}")
                page.get_by_role('button',name='Save brief',exact=True).click()
                expect(page.locator('.modal')).to_have_count(0)
                page.locator('#rigor').evaluate("el => {el.value=10;el.dispatchEvent(new Event('input',{bubbles:true}));}");page.evaluate('() => flush()')
                brief=client.get('/api/projects/'+pid).json()['brief']
                assert brief['rhetorical_force']==95 and brief['rigor']==10
                assert brief['thesis'].startswith('The enthusiasm is the indictment')
                check('Thesis, rhetorical force and evidence detail save as separate controls')
                page.get_by_role('button',name='Refresh angles with my voice',exact=True).click()
                wait(page,'angles');page.wait_for_selector('.angle-card')
                expect(page.locator('.angle-card')).to_contain_text('The enthusiasm is the indictment')
                angle_request=next(x for x in EditorialClients.observed if x['task'].startswith('Propose up to six'))
                assert 'The committee' in str(angle_request['author_voice'])
                assert angle_request['editorial_contract']['rhetorical_force']==95
                assert angle_request['editorial_contract']['evidence_detail']==10
                assert client.get('/api/projects/'+pid).json()['graph']==original['graph']
                page.locator('#toasts').evaluate('el => el.replaceChildren()');page.screenshot(path=str(out/'polemic-angles.png'),full_page=True)
                check('Refreshing angles uses actual voice and intent inputs without rebuilding the graph')
                page.get_by_role('button',name='Take this angle',exact=True).click()
                page.get_by_role('button',name='Develop outline',exact=True).first.click()
                wait(page,'outline');page.wait_for_selector('.outline-section')
                request=next(x for x in EditorialClients.observed if x['task'].startswith('Build an editable outline'))
                assert request['author_voice']['samples'] and request['editorial_contract']['mode']=='polemic'
                check('The outline receives the same author voice and argumentative contract')
                page.get_by_role('button',name='Write draft',exact=True).first.click()
                wait(page,'draft');page.wait_for_selector('#manuscript')
                expect(page.locator('.evidence-card').filter(has_text='Authorial fidelity')).to_be_visible()
                review=next(x for x in reversed(EditorialClients.observed) if x['task'].startswith('Act as a rigorous'))
                assert review['author_voice']['samples'] and review['editorial_contract']['thesis']==brief['thesis']
                check('Drafting and the reviewer receive the authorial contract and report fidelity separately')
                response=client.get('/api/projects/'+pid+'/export/md')
                assert response.status_code==200 and '## Sources' in response.text
                check('Polemic retains normal citation and bibliography export')
                page.get_by_role('button',name='Polemic · Change',exact=True).click()
                page.locator('#writing-mode').select_option('nonfiction')
                page.get_by_role('button',name='Apply writing mode',exact=True).click()
                expect(page.locator('.modal')).to_have_count(0)
                assert client.get('/api/projects/'+pid).json()['brief']['stance_policy']=='preserve'
                check('Argument-led intent also works in ordinary nonfiction; changing labels is not the sole fix')
                page.set_viewport_size({'width':1000,'height':800});page.wait_for_timeout(100)
                assert page.evaluate('() => document.documentElement.scrollWidth')<=1000
                check('Controls fit a smaller desktop window')
                assert not report['page_errors'];report['ok']=True
            except Exception:
                report['error']=traceback.format_exc();page.screenshot(path=str(out/'failure.png'),full_page=True);raise
            finally:
                (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
                browser.close();server.should_exit=True;thread.join(timeout=5);sock.close();client.close();app.state.runner.pool.shutdown(wait=True,cancel_futures=True)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
