"""GraphPaper 0.2 UI checks. HTTP in CI; explicit in-process bridge on restricted hosts."""
from __future__ import annotations
import argparse
import base64
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from graphpaper.server import create_app
from graphpaper.models import Settings
from tests.conftest import ScriptedClients
from playwright.sync_api import sync_playwright


class StudioClients(ScriptedClients):
    def complete(self,system,user,**kwargs):
        try:raw=json.loads(user)
        except ValueError:return super().complete(system,user,**kwargs)
        task=raw.get('task','')
        if task.startswith('Build an editable author voice'):
            self._record('voice')
            return {'name':'Precise and personal','instructions':'Use direct verbs and varied sentence length. Keep humor dry; preserve uncertainty when it matters.','observations':['The samples favor concrete verbs.']}
        if task.startswith(('HUMANIZE','DESLOP')):
            self._record('polish')
            return raw['draft'].replace('It is important to note that ','')
        if task.startswith('Compare original and proposed prose'):
            self._record('polish-review')
            return {'meaning_preserved':True,'summary':'Removed filler while preserving the claim.','warnings':[],'improvements':['Direct opening.']}
        return super().complete(system,user,**kwargs)


def wait(page,action):
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        status=page.evaluate('() => state.job && ({state:state.job.state,action:state.job.action,error:state.job.error})')
        if status and status['action']==action:
            if status['state']=='completed':return
            if status['state']=='failed':raise AssertionError(status)
        page.wait_for_timeout(100)
    raise AssertionError('Job did not complete: '+action)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');parser.add_argument('--chromium');parser.add_argument('--out',default='test-results/studio');args=parser.parse_args()
    out=ROOT/args.out;out.mkdir(parents=True,exist_ok=True)
    report={'mode':'in-process HTTP bridge' if args.offline else 'real HTTP','live_models':False,'checks':[],'page_errors':[],'ok':False}
    with tempfile.TemporaryDirectory() as tmp:
        app=create_app(tmp);app.state.runner.clients_factory=StudioClients
        app.state.store.set_settings(Settings(model='test/model',allow_cloud=True,remember_keys=False).model_dump())
        client=TestClient(app);client.get('/');client.headers['X-GraphPaper']='1'
        server=None
        if not args.offline:
            import uvicorn
            sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
            thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
            while not server.started:time.sleep(.05)
        def bridge(req):
            kwargs={'headers':req.get('headers',{})}
            if req.get('form') is not None:
                files=[];data={}
                for part in req['form']:
                    if 'bytes' in part:files.append((part['name'],(part['filename'],base64.b64decode(part['bytes']),part['type'])))
                    else:data[part['name']]=part['value']
                kwargs.update(files=files,data=data)
            else:kwargs['content']=req.get('body')
            r=client.request(req['method'],req['url'],**kwargs)
            return {'status':r.status_code,'headers':dict(r.headers),'body':base64.b64encode(r.content).decode()}
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,**({'executable_path':args.chromium} if args.chromium else {}))
            page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(12000)
            page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            try:
                if args.offline:
                    html=(ROOT/'ui/index.html').read_text()
                    for name in ['styles.css','studio.css']:html=html.replace(f'<link rel="stylesheet" href="/static/{name}">','<style>'+(ROOT/'ui'/name).read_text()+'</style>')
                    for name in ['app.js','studio.js']:html=html.replace(f'<script src="/static/{name}" defer></script>','')
                    ico='data:image/svg+xml;base64,'+base64.b64encode((ROOT/'ui/icon.svg').read_bytes()).decode()
                    html=html.replace('/static/icon.svg',ico)
                    page.expose_function('__studioRequest',bridge);page.set_content(html)
                    page.evaluate('''() => {window.fetch=async(url,opt={})=>{let form=null,body=opt.body;if(body instanceof FormData){form=[];for(const [name,v] of body.entries()){if(v instanceof File){const bytes=new Uint8Array(await v.arrayBuffer());let binary='';for(const b of bytes)binary+=String.fromCharCode(b);form.push({name,filename:v.name,type:v.type,bytes:btoa(binary)});}else form.push({name,value:v});}body=undefined;}const r=await window.__studioRequest({url:String(url),method:opt.method||'GET',headers:opt.headers||{},body,form});return new Response(Uint8Array.from(atob(r.body),c=>c.charCodeAt(0)),{status:r.status,headers:r.headers});};}''')
                    for name in ['app.js','studio.js']:page.add_script_tag(content=(ROOT/'ui'/name).read_text().replace('/static/icon.svg',ico))
                else:page.goto(f'http://127.0.0.1:{port}/')
                page.wait_for_selector('.welcome')
                page.get_by_role('button',name='New project',exact=True).click();page.locator('#project-title').fill('A voice of your own');page.get_by_role('button',name='Create project',exact=True).click();page.wait_for_selector('.studio-strip')
                pid=page.evaluate('state.p.id');base='/api/projects/'+pid
                page.get_by_role('button',name='Your writing voice',exact=True).click()
                with page.expect_file_chooser() as chosen:page.get_by_role('button',name='Upload samples',exact=True).click()
                sample=('I would rather explain a thing than pretend it is mysterious. Some sentences are short. Others need room for qualifications, because precision matters more than a slogan. '*8).encode()
                chosen.value.set_files({'name':'my-essay.md','mimeType':'text/markdown','buffer':sample})
                page.wait_for_selector('.studio-sample');assert client.get(base).json()['sources'][0]['role']=='voice'
                report['checks'].append('Voice sample upload through the actual file input')
                page.get_by_role('button',name='Learn my writing style',exact=True).click();wait(page,'voice')
                page.get_by_role('button',name='Your writing voice',exact=True).click();assert 'direct verbs' in page.locator('#voice-instructions').input_value()
                page.locator('#voice-instructions').fill('Use precise verbs. Vary rhythm. Leave deliberate wit alone.')
                page.get_by_role('button',name='Save voice settings',exact=True).click()
                assert client.get(base).json()['voice_profile']['instructions'].startswith('Use precise')
                report['checks'].append('Learn, inspect and edit a persistent author voice profile')
                page.get_by_role('button',name='Your writing voice',exact=True).click();page.screenshot(path=str(out/'voice.png'),full_page=True);page.get_by_role('button',name='Close dialog',exact=True).click()
                page.get_by_role('button',name='Project folder',exact=True).click();info=client.get(base+'/workspace').json()
                (Path(info['inbox'])/'Evidence'/'research.md').write_text('A source with a specific factual claim.',encoding='utf-8')
                page.get_by_role('button',name='Import files now',exact=True).click()
                page.wait_for_timeout(500);assert len(client.get(base).json()['sources'])==2
                page.screenshot(path=str(out/'folder.png'),full_page=True);page.get_by_role('button',name='Close dialog',exact=True).click()
                report['checks'].append('Project folder import and automatic source ownership')
                (Path(info['inbox'])/'Voice'/'second-voice.txt').write_text('Another representative piece of my writing. '*30)
                page.locator('.nav-link[data-tab="sources"]').click()
                deadline=time.monotonic()+13
                while time.monotonic()<deadline and len(client.get(base).json()['sources'])<3:page.wait_for_timeout(200)
                assert len(client.get(base).json()['sources'])==3
                report['checks'].append('Idle folder watcher detects and imports new files without an AI call')
                page.locator('.nav-link[data-tab="write"]').click();page.locator('#manuscript').fill('It is important to note that the measured value was 12.5% [S2].')
                page.wait_for_timeout(800);page.get_by_role('button',name='Inspect prose',exact=True).click();page.wait_for_selector('.studio-metrics');assert page.locator('.severity').count()>0
                page.get_by_role('button',name='Close dialog',exact=True).click();report['checks'].append('Local explainable prose inspection')
                page.get_by_role('button',name='Humanize',exact=True).click();page.get_by_role('button',name='Create proposed edit',exact=True).click();wait(page,'humanize')
                assert client.get(base).json()['draft'].startswith('It is important')
                page.get_by_role('button',name='Compare proposed edit',exact=True).click();page.wait_for_selector('.studio-compare');page.screenshot(path=str(out/'humanizer.png'),full_page=True)
                page.get_by_role('button',name='Accept this edit',exact=True).click();page.wait_for_selector('#manuscript');assert page.locator('#manuscript').input_value()=='the measured value was 12.5% [S2].'
                report['checks'].append('Humanizer proposal, side-by-side comparison and explicit acceptance')
                page.locator('#manuscript').fill('It is important to note that another point remains unchanged.');page.wait_for_timeout(800)
                page.get_by_role('button',name='Deslop',exact=True).click();page.get_by_role('button',name='Create proposed edit',exact=True).click();wait(page,'deslop')
                page.get_by_role('button',name='Compare proposed edit',exact=True).click();page.get_by_role('button',name='Discard proposal',exact=True).click()
                assert client.get(base).json()['draft'].startswith('It is important')
                report['checks'].append('Separate deslopping pass and non-destructive rejection')
                page.locator('[data-action="settings"]').click();page.locator('#s-provider').select_option('codex')
                assert page.locator('#s-model').input_value()==''
                page.screenshot(path=str(out/'codex.png'),full_page=True);page.get_by_role('button',name='Save connections',exact=True).click()
                assert client.get('/api/settings').json()['provider']=='codex'
                report['checks'].append('Codex subscription provider selectable without an API key')
                page.set_viewport_size({'width':1000,'height':800});page.locator('.nav-link[data-tab="sources"]').click()
                assert page.evaluate('document.documentElement.scrollWidth')<=1000
                report['checks'].append('New controls fit a smaller desktop window')
                assert not report['page_errors'],report['page_errors']
                report['ok']=True
            except Exception:
                report['error']=traceback.format_exc();page.screenshot(path=str(out/'failure.png'),full_page=True);raise
            finally:
                (out/'report.json').write_text(json.dumps(report,indent=2));browser.close()
                app.state.runner.pool.shutdown(wait=True,cancel_futures=True)
                if server:server.should_exit=True;thread.join(timeout=5);sock.close()
                client.close()
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
