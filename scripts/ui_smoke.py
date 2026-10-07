"""Real Chromium UI exercise against the real backend, with a deterministic AI double.

Normal mode tests HTTP/cookies/CSP. --offline uses an in-process HTTP bridge when a
managed browser forbids ALL navigation. That mode is explicit in the report.
Neither mode calls a live model or measures prose quality.
"""
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

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from graphpaper.server import create_app
from tests.conftest import ScriptedClients
from playwright.sync_api import sync_playwright


def wait_for_completion(page, action=None):
    """CSP-safe polling of the actual job state; do not weaken the app policy."""
    deadline = time.monotonic() + 30
    last = None
    while time.monotonic() < deadline:
        last = page.evaluate("() => state.job ? ({state: state.job.state, action: state.job.action, error: state.job.error}) : null")
        if last and (action is None or last["action"] == action):
            if last["state"] == "completed":
                return
            if last["state"] in {"failed", "cancelled"}:
                raise AssertionError("UI job did not succeed: " + json.dumps(last))
        page.wait_for_timeout(100)
    raise AssertionError("UI job did not complete: " + json.dumps(last))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--chromium')
    parser.add_argument('--out',default=str(ROOT/'test-results/ui'))
    args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    report={'mode':'in-process HTTP bridge' if args.offline else 'HTTP browser','live_models':False,'checks':[],'page_errors':[],'ok':False}
    def check(name):report['checks'].append(name)
    with tempfile.TemporaryDirectory(prefix='graphpaper-ui-') as tmp:
        app=create_app(tmp);app.state.runner.clients_factory=ScriptedClients
        client=TestClient(app);client.get('/');client.headers['X-GraphPaper']='1'
        server=None
        if not args.offline:
            import uvicorn
            sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
            thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
            while not server.started:time.sleep(.05)
        def bridge(req):
            opts={'headers':req.get('headers',{})}
            if req.get('form') is not None:
                files=[];data={}
                for part in req['form']:
                    if 'bytes' in part:files.append((part['name'],(part['filename'],base64.b64decode(part['bytes']),part['type'])))
                    else:data[part['name']]=part['value']
                opts.update(files=files,data=data)
            else:opts['content']=req.get('body')
            res=client.request(req['method'],req['url'],**opts)
            return {'status':res.status_code,'headers':dict(res.headers),'body':base64.b64encode(res.content).decode()}
        with sync_playwright() as pw:
            options={'headless':True}
            if args.chromium:options['executable_path']=args.chromium
            browser=pw.chromium.launch(**options)
            page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
            page.on('pageerror',lambda err:report['page_errors'].append(str(err)))
            page.set_default_timeout(12000)
            try:
                if args.offline:
                    html=(ROOT/'ui/index.html').read_text().replace('<link rel="stylesheet" href="/static/styles.css">','<style>'+(ROOT/'ui/styles.css').read_text()+'</style>').replace('<script src="/static/app.js" defer></script>','')
                    icon='data:image/svg+xml;base64,'+base64.b64encode((ROOT/'ui/icon.svg').read_bytes()).decode()
                    html=html.replace('/static/icon.svg',icon)
                    page.expose_function('__graphpaperTestRequest',bridge)
                    page.set_content(html)
                    page.evaluate('''() => {window.fetch=async(url,opt={})=>{let form=null,body=opt.body;if(body instanceof FormData){form=[];for(const [name,v] of body.entries()){if(v instanceof File){const bytes=new Uint8Array(await v.arrayBuffer());let binary='';for(const b of bytes)binary+=String.fromCharCode(b);form.push({name,filename:v.name,type:v.type,bytes:btoa(binary)});}else form.push({name,value:v});}body=undefined;}const r=await window.__graphpaperTestRequest({url:String(url),method:opt.method||'GET',headers:opt.headers||{},body,form});return new Response(Uint8Array.from(atob(r.body),c=>c.charCodeAt(0)),{status:r.status,headers:r.headers});};}''')
                    page.add_script_tag(content=(ROOT/'ui/app.js').read_text().replace('/static/icon.svg',icon))
                else:page.goto(f'http://127.0.0.1:{port}/')
                page.wait_for_selector('.welcome');page.screenshot(path=str(out/'welcome.png'),full_page=True);check('Welcome and empty state')
                page.get_by_role('button',name='The city after dark',exact=True).click();page.wait_for_selector('#graph-svg');page.wait_for_timeout(400)
                assert page.locator('[data-node]').count()==18
                sample_id=page.evaluate('state.p.id')
                page.screenshot(path=str(out/'graph.png'),full_page=True);check('Illustrative graph renders with 18 nodes')
                page.locator('[data-node]').first.click();page.wait_for_selector('.evidence-card h3')
                page.get_by_role('button',name='Pin idea',exact=True).click();page.wait_for_timeout(800)
                # Autosave is debounced; await actual persistence rather than
                # assuming a hosted browser+server completes it within 800 ms.
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    if len(client.get('/api/projects/'+sample_id).json()['brief']['pinned_nodes'])==1:
                        break
                    page.wait_for_timeout(100)
                else:
                    raise AssertionError('Graph pin was not persisted by autosave')
                check('Inspect graph node and persist pin')
                page.get_by_role('button',name='Find a path',exact=True).click();page.get_by_role('button',name='Find path',exact=True).click();page.wait_for_selector('#graph-svg');check('Path query and highlight')
                page.locator('.nav-link[data-tab="angles"]').click();page.wait_for_selector('.angle-card')
                page.screenshot(path=str(out/'angles.png'),full_page=True)
                page.locator('[data-action="edit-angle"]').first.click();page.locator('#a-title').fill('Darkness as a public good');page.get_by_role('button',name='Save & select',exact=True).click();page.wait_for_selector('.angle-card.selected');check('Edit and select an angle')
                page.locator('.nav-link[data-tab="outline"]').click();page.locator('[data-outline="purpose"]').first.fill('A revised opening purpose.');page.wait_for_timeout(800)
                page.locator('[data-action="move-section"][data-offset="1"]').first.click();page.wait_for_timeout(800);check('Edit and reorder outline')
                page.locator('.nav-link[data-tab="write"]').click();page.wait_for_selector('#manuscript')
                before=page.locator('#manuscript').input_value();page.locator('#manuscript').fill(before+'\n\nA manually edited ending.');page.wait_for_timeout(950)
                assert client.get('/api/projects/'+sample_id).json()['draft'].endswith('A manually edited ending.')
                assert page.locator('#draft-preview').inner_text().endswith('A manually edited ending.')
                page.screenshot(path=str(out/'writing.png'),full_page=True);check('Manuscript autosave and safe live preview')
                page.locator('.citation').first.click();page.wait_for_selector('.source-text');page.get_by_role('button',name='Close dialog',exact=True).click();check('Clickable source references')
                page.get_by_role('button',name='Version history',exact=True).click();page.wait_for_selector('.version-item');page.get_by_role('button',name='Read',exact=True).first.click();page.get_by_role('button',name='Restore this version',exact=True).click();page.wait_for_selector('#manuscript');check('Read and restore earlier version')
                page.get_by_role('button',name='Export',exact=True).click();page.wait_for_selector('.export-options')
                assert page.get_by_role('button',name='Word document',exact=False).count()==1
                # Verify resulting bytes through backend; OS save dialog is a native-shell concern.
                r=client.get('/api/projects/'+sample_id+'/export/docx');assert r.content[:2]==b'PK'
                page.get_by_role('button',name='Close dialog',exact=True).click();check('Export options and valid Word output')
                page.locator('[data-action="settings"]').click();page.locator('#s-model').fill('deterministic/test-model');page.locator('#s-allow_cloud').check();page.locator('#s-remember_keys').uncheck();page.locator('#s-refine').uncheck();page.get_by_role('button',name='Save connections',exact=True).click();page.wait_for_selector('.workspace-head');check('Configure provider through UI (mock transport only)')
                page.get_by_role('button',name='New project',exact=True).click();page.locator('#project-title').fill('UI integration essay');page.locator('#project-premise').fill('Explore choices and public space.');page.get_by_role('button',name='Create project',exact=True).click();page.wait_for_selector('#dropzone')
                with page.expect_file_chooser() as chooser:page.locator('#dropzone').click()
                chooser.value.set_files({'name':'notes.md','mimeType':'text/markdown','buffer':b'# Source notes\n\nPeople make choices about shared space. A design decision can have unintended consequences.'})
                page.wait_for_selector('.source-card');check('Browser file-input upload and source ingestion')
                pid=page.evaluate('state.p.id')
                page.get_by_role('button',name='Build graph',exact=True).click();page.wait_for_selector('#graph-svg');wait_for_completion(page)
                page.get_by_role('button',name='Discover angles',exact=True).click();page.wait_for_selector('.angle-card');wait_for_completion(page)
                assert '85 / 100' in page.locator('.angle-score').first.inner_text()
                page.get_by_role('button',name='Take this angle',exact=True).first.click()
                page.get_by_role('button',name='Develop outline',exact=True).click();page.wait_for_selector('.outline-section');wait_for_completion(page)
                page.get_by_role('button',name='Write draft',exact=True).first.click();wait_for_completion(page, 'draft');page.wait_for_selector('#manuscript')
                assert client.get('/api/projects/'+pid).json()['review']['summary']
                check('Complete graph → JEV → angle → outline → draft → review path with deterministic AI')
                page.get_by_role('button',name='Revise with a direction',exact=True).click();page.locator('#revision-instruction').fill('Improve the ending.');page.get_by_role('button',name='Revise draft',exact=True).click();wait_for_completion(page, 'revise');check('Explicit revision job and versioning')
                page.get_by_role('button',name='New project',exact=True).click();page.locator('#project-title').fill('UI integration fiction');page.locator('#project-mode').select_option('fiction');page.locator('#project-premise').fill('Mira must choose who gets to keep a memory.');page.get_by_role('button',name='Create project',exact=True).click();page.wait_for_selector('#dropzone')
                page.get_by_role('button',name='Build graph',exact=True).click();page.wait_for_selector('#graph-svg');wait_for_completion(page)
                page.get_by_role('button',name='Discover angles',exact=True).click();page.wait_for_selector('.angle-card');wait_for_completion(page)
                page.get_by_role('button',name='Take this angle',exact=True).click();page.get_by_role('button',name='Develop outline',exact=True).click();page.wait_for_selector('.outline-section');wait_for_completion(page)
                page.get_by_role('button',name='Write draft',exact=True).first.click();wait_for_completion(page, 'draft')
                page.get_by_role('button',name='Story ledger',exact=True).click();page.wait_for_selector('.source-text');assert 'Mira' in page.locator('.source-text').inner_text();page.get_by_role('button',name='Close dialog',exact=True).click();check('Fiction from premise, scene generation and continuity ledger')
                page.locator(f'[data-action="open-project"][data-id="{sample_id}"]').click();page.wait_for_selector('#graph-svg')
                page.get_by_role('button',name='Switch theme',exact=True).click();page.wait_for_timeout(500);page.screenshot(path=str(out/'light.png'),full_page=True);check('Light theme')
                page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300)
                width=page.evaluate('document.documentElement.scrollWidth');assert width<=393,f'Mobile overflow: {width}'
                page.screenshot(path=str(out/'mobile.png'),full_page=True);check('Responsive 390px layout without horizontal overflow')
                assert not report['page_errors'],report['page_errors']
                report['ok']=True
            except Exception:
                report['error']=traceback.format_exc();page.screenshot(path=str(out/'failure.png'),full_page=True)
                raise
            finally:
                (out/'report.json').write_text(json.dumps(report,indent=2))
                browser.close()
                app.state.runner.pool.shutdown(wait=True,cancel_futures=True)
                if server:
                    server.should_exit=True;thread.join(timeout=5);sock.close()
                client.close()
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
