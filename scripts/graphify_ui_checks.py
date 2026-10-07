"""Reusable graphical checks; real Graphify and provider transport, synthetic inference."""
from pathlib import Path
import sys
import time
from playwright.sync_api import expect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.graphify_http_fixture import FixtureServer


def exercise(page,check,out):
    with FixtureServer() as provider:
        page.locator('[data-action="settings"]').click()
        page.locator('#s-provider').select_option('openai-compatible')
        page.locator('#s-base_url').fill(provider.url)
        page.locator('#s-model').fill('fixture-writer')
        page.locator('#s-extraction_model').fill('fixture-extractor')
        page.locator('#s-allow_cloud').uncheck()
        page.locator('#s-remember_keys').uncheck()
        page.get_by_text('Advanced limits & Graphify',exact=True).click()
        page.locator('#s-graph_engine').select_option('graphify')
        page.locator('#s-graphify_executable').fill('')
        page.locator('#s-graphify_timeout_seconds').fill('90')
        page.get_by_role('button',name='Load available models',exact=True).click()
        expect(page.locator('#modal-status')).to_contain_text('models loaded',timeout=15000)
        page.locator('#s-extraction_reasoning_effort').select_option('high')
        page.get_by_role('button',name='Check Graphify runtime',exact=True).click()
        expect(page.locator('#graphify-runtime-status')).to_contain_text('Ready: Graphify 0.9.80',timeout=30000)
        page.screenshot(path=str(out/'graphify-settings.png'))
        check('Graphify runtime is available through the real graphical status check')
        page.get_by_role('button',name='Save connections',exact=True).click()
        expect(page.locator('.modal')).to_have_count(0)
        settings=page.evaluate('() => state.settings')
        assert settings['graph_engine']=='graphify'
        assert settings['extraction_model']=='fixture-extractor'
        assert settings['extraction_reasoning_effort']=='high'
        check('External engine, extraction model and reasoning settings save from the interface')
        page.evaluate('''async () => {
            for (const [title,text,role] of [
                ['Synthetic operations','Eva maintains the Observatory. The Observatory records variable stars.','evidence'],
                ['Synthetic funding','A research grant funds the Observatory. The grant requires public summaries.','evidence'],
                ['Voice fixture','PRIVATE_VOICE_FIXTURE_DO_NOT_EXTRACT','voice']]) {
                state.p=await api('/projects/'+state.p.id+'/sources/text',{title,text,role});
            }
            state.tab='sources'; render();
        }''')
        page.locator('[data-action="run-graph"]').first.click()
        deadline=time.monotonic()+100
        while time.monotonic()<deadline:
            job=page.evaluate('() => state.job && ({state:state.job.state,error:state.job.error})')
            if job and job['state']=='completed':break
            if job and job['state'] in {'failed','cancelled'}:raise AssertionError(job)
            page.wait_for_timeout(100)
        else:raise AssertionError('Native external extraction timed out')
        page.wait_for_selector('#graph-svg')
        page.wait_for_function("() => state.p.graph.coverage?.engine==='external_graphify' && state.p.graph.nodes.length>0")
        project=page.evaluate('() => state.p')
        graph=project['graph']
        assert graph['coverage']['engine']=='external_graphify'
        assert graph['nodes'] and graph['edges']
        assert graph['coverage']['model_requests']==len(provider.requests)==project['usage']['calls']
        assert all(r['model']=='fixture-extractor' and r.get('reasoning_effort')=='high' for r in provider.requests)
        assert all('PRIVATE_VOICE_FIXTURE' not in str(r) for r in provider.requests)
        check('Build graph runs the actual external Graphify worker through the selected model and effort')
        check('Only evidence sources reach inference; no second Native extraction or uncounted request')
        page.screenshot(path=str(out/'graphify-graph.png'))
        page.get_by_role('button',name='Eva',exact=True).click()
        provenance=page.locator('.evidence-card').filter(has_text='Source-file provenance')
        expect(provenance).to_be_visible()
        provenance.get_by_role('button',name='S1',exact=True).click()
        expect(page.locator('.source-text')).to_contain_text('Eva maintains the Observatory')
        page.get_by_role('button',name='Close dialog',exact=True).click()
        check('External graph source provenance opens the correct original document')
        return {'nodes':len(graph['nodes']),'edges':len(graph['edges']),
            'model_requests':len(provider.requests),'runtime':graph['coverage']['runtime_version'],
            'engine':graph['engine'],'reasoning':'high','model':'fixture-extractor','live_model':False}
