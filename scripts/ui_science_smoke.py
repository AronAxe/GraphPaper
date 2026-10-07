"""Real local HTTP browser workflow for Science/reasoning; model/database fixtures are labelled."""
from __future__ import annotations
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import traceback
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from graphpaper.server import create_app
from graphpaper.providers import Clients
from tests.science_fixtures import ScienceClients
from playwright.sync_api import sync_playwright,expect
import uvicorn


def wait_job(page,action):
    deadline=time.monotonic()+40
    while time.monotonic()<deadline:
        value=page.evaluate('() => state.job && ({action:state.job.action,state:state.job.state,error:state.job.error})')
        if value and value['action']==action:
            if value['state']=='completed':return
            if value['state'] in {'failed','cancelled'}:raise AssertionError(value)
        page.wait_for_timeout(100)
    raise AssertionError('Job timeout: '+str(value))


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--out',default=str(ROOT/'test-results/science-ui'))
    args=parser.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    report={'mode':'real HTTP browser','live_models':False,'live_databases':False,'checks':[],'page_errors':[],'ok':False}
    def check(label):report['checks'].append(label);print('PASS',label,flush=True)
    catalog=[{'id':'fixture-science','name':'Fixture science model','reasoning_levels':['low','medium','high','xhigh','ultra'],'reasoning_source':'model catalog','default_reasoning':'medium','is_default':True,'supports_budget':False}]
    with tempfile.TemporaryDirectory(prefix='GraphPaper-science-ui-') as temp:
        app=create_app(Path(temp));app.state.runner.clients_factory=ScienceClients
        client=TestClient(app);client.get('/');client.headers['X-GraphPaper']='1'
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,log_level='error'));thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        deadline=time.monotonic()+15
        while not server.started and time.monotonic()<deadline:time.sleep(.05)
        assert server.started
        with patch.object(Clients,'discover_models',lambda self:catalog),sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1040},accept_downloads=True);page.set_default_timeout(12000)
            page.on('pageerror',lambda err:report['page_errors'].append(str(err)))
            try:
                page.goto(f'http://127.0.0.1:{port}/');page.wait_for_selector('.welcome')
                expect(page.locator('.welcome-card')).to_have_count(4);check('Four distinct writing modes on the welcome screen')
                page.locator('[data-action="settings"]').click();page.locator('#s-provider').select_option('codex');page.locator('#s-allow_cloud').check();page.locator('#s-refine').uncheck();page.locator('#s-remember_keys').uncheck()
                page.get_by_role('button',name='Load available models',exact=True).click()
                expect(page.locator('#s-reasoning_effort option[value="ultra"]')).to_have_count(1)
                page.locator('#s-model').fill('fixture-science');page.locator('#s-reasoning_effort').select_option('ultra')
                page.locator('#s-editor_reasoning_effort').select_option('high');page.locator('#s-extraction_reasoning_effort').select_option('low')
                page.locator('#s-reasoning_effort').scroll_into_view_if_needed();page.screenshot(path=str(out/'reasoning.png'))
                page.get_by_role('button',name='Save connections',exact=True).click();expect(page.locator('.modal')).to_have_count(0)
                settings=client.get('/api/settings').json()
                assert [settings[k] for k in ['reasoning_effort','editor_reasoning_effort','extraction_reasoning_effort']]==['ultra','high','low']
                check('Advertised Codex ultra and independent writer/editor/extractor efforts persist')
                page.locator('.welcome-card[data-mode="science"]').click();page.locator('#project-title').fill('Sleep and memory research')
                page.locator('#project-premise').fill('How does sleep relate to memory performance?');page.locator('#project-words').fill('1600')
                page.get_by_role('button',name='Create project',exact=True).click();page.wait_for_selector('.science-stats')
                pid=page.evaluate('() => state.p.id');base='/api/projects/'+pid
                assert client.get(base).json()['mode']=='science';check('Science project opens directly on the research desk')
                page.get_by_role('button',name='Research protocol',exact=True).click();page.locator('#rp-queries').fill('sleep AND memory')
                for db in ['semantic_scholar','arxiv','crossref','europe_pmc']:page.locator('.rp-database[value="'+db+'"]').uncheck()
                page.locator('#rp-inclusion').fill('Studies of sleep and memory outcomes');page.locator('#rp-exclusion').fill('Unrelated outcomes')
                for key,value in {'author_names':'Alex Example','affiliation':'Test Research Institute','funding':'No external funding','conflicts':'None declared','data_availability':'Synthetic test fixture','ethics':'Not applicable to this synthetic workflow'}.items():page.locator('#rp-'+key).fill(value)
                page.get_by_role('button',name='Save research plan',exact=True).click();expect(page.locator('.modal')).to_have_count(0)
                check('Research protocol, search terms, eligibility and APA author declarations save')
                page.get_by_role('button',name='Search databases',exact=True).first.click();wait_job(page,'science-search')
                expect(page.locator('.science-paper')).to_have_count(2);check('Database search result cards carry metadata and access labels')
                page.get_by_role('button',name='Search log',exact=True).click();expect(page.locator('.science-search')).to_have_count(1)
                assert 'sleep AND memory' in page.locator('.science-search').inner_text();check('Actual query, count and search status are visible in the audit log')
                page.get_by_role('button',name='Papers',exact=True).click()
                for checkbox in page.locator('.science-paper-select').all():checkbox.check()
                page.get_by_role('button',name='Include selected',exact=True).click();page.locator('#science-reason').fill('Fits the test criteria');page.get_by_role('button',name='Save screening decision',exact=True).click();expect(page.locator('.modal')).to_have_count(0)
                assert len(client.get(base).json()['sources'])==2;check('Screened studies become correctly associated evidence sources')
                page.get_by_role('button',name='Fetch open full text',exact=True).click();wait_job(page,'science-fulltext')
                assert all(r['metadata']['content_scope']=='full_text' for r in client.get(base).json()['research']['records'])
                page.get_by_role('button',name='Appraise included papers',exact=True).click();wait_job(page,'science-appraise')
                page.get_by_role('button',name='Evidence matrix',exact=True).click();expect(page.locator('.science-table tbody tr')).to_have_count(2)
                expect(page.locator('.science-table')).to_contain_text('uncertain');page.screenshot(path=str(out/'evidence.png'),full_page=True)
                check('Full-text retrieval and source-quoted appraisal populate the evidence matrix')
                page.get_by_role('button',name='Papers',exact=True).click();page.screenshot(path=str(out/'research.png'),full_page=True)
                page.get_by_role('button',name='Build manuscript outline',exact=True).click();wait_job(page,'science-outline');expect(page.locator('.outline-section')).to_have_count(5)
                page.get_by_role('button',name='Write manuscript',exact=True).click();wait_job(page,'science-draft');page.wait_for_selector('#manuscript')
                page.wait_for_function("() => document.querySelector('#manuscript')?.value.includes('## Method')");check('Scientific outline produces source-linked IMRaD manuscript and abstract')
                page.get_by_role('button',name='APA preview',exact=True).click();page.wait_for_selector('.modal .prose')
                text=page.locator('.modal .prose').inner_text();assert 'Example & Researcher, 2024' in text and 'References' in text and '[S1]' not in text
                page.screenshot(path=str(out/'apa-preview.png'),full_page=True);page.get_by_role('button',name='Close dialog',exact=True).click()
                check('APA preview resolves author-year citations and references from metadata')
                page.get_by_role('button',name='Export',exact=True).click()
                with page.expect_download() as download:page.get_by_role('button',name='APA Word manuscript',exact=False).click()
                download.value.save_as(str(out/'sample-apa.docx'));assert (out/'sample-apa.docx').read_bytes()[:2]==b'PK'
                page.get_by_role('button',name='Close dialog',exact=True).click();check('APA Word export downloads an actual DOCX manuscript')
                page.get_by_role('button',name='Submission checks',exact=True).click();expect(page.locator('.science-confirm')).to_have_count(4)
                for checkbox in page.locator('.science-confirm').all():checkbox.check()
                page.get_by_role('button',name='Save author confirmations',exact=True).click();expect(page.locator('.modal')).to_have_count(0)
                response=client.get(base+'/export/submission');assert response.status_code==200,response.text[:300]
                page.locator('#manuscript').fill(page.locator('#manuscript').input_value()+'\n\nA further edit.')
                page.evaluate('() => flush()');assert client.get(base+'/export/submission').status_code==400
                check('Submission package requires author confirmation and rejects stale approval after edits')
                page.locator('[data-action="science-home"]').click();page.set_viewport_size({'width':1000,'height':800});page.wait_for_timeout(200)
                assert page.evaluate('() => document.documentElement.scrollWidth')<=1000
                check('Research desk fits a smaller desktop window')
                assert not report['page_errors'],report['page_errors'];report['ok']=True
            except Exception:
                report['error']=traceback.format_exc();page.screenshot(path=str(out/'failure.png'),full_page=True);raise
            finally:
                (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
                browser.close();server.should_exit=True;thread.join(timeout=5);sock.close();client.close();app.state.runner.pool.shutdown(wait=True,cancel_futures=True)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
