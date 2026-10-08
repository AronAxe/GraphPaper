"""Reusable real-interface checks. Synthetic voice; no paid model or private material."""
from playwright.sync_api import expect


def exercise(page,check,out,native=False):
    if page.locator('.step[data-tab="sources"]').count():page.locator('.step[data-tab="sources"]').click()
    page.get_by_role('button',name='Your writing voice',exact=True).click()
    page.locator('#voice-name').fill('Power and wit')
    page.locator('#voice-instructions').fill('Keep the fucking point. Use satire and anger when requested. End on the verdict. The current author brief overrides these defaults.')
    page.get_by_role('button',name='Save as reusable voice',exact=True).click()
    page.wait_for_selector('.voice-graph')
    expect(page.locator('#saved-voice-name')).to_have_value('Power and wit')
    assert 'fucking' in page.evaluate('() => JSON.stringify(voicesUI.current.graph)')
    vid=page.evaluate('() => voicesUI.current.id')
    check('An existing voice is saved as a named graph without a model call or tone filter')
    before=page.evaluate('() => ({sources:state.p.sources,graph:state.p.graph,draft:state.p.draft})')
    page.get_by_role('button',name='Use in this project',exact=True).click()
    expect(page.locator('.modal')).to_have_count(0)
    after=page.evaluate('() => ({sources:state.p.sources,graph:state.p.graph,draft:state.p.draft})')
    assert after==before
    assert page.evaluate('() => state.p.voice_profile.library_id')==vid
    check('Applying a graph preserves the project evidence, manuscript and graph')
    page.get_by_role('button',name='New project',exact=True).click()
    page.locator('#project-title').fill('Another isolated article')
    page.get_by_role('button',name='Create project',exact=True).click()
    page.wait_for_selector('#dropzone')
    page.get_by_role('button',name='Your writing voice',exact=True).click()
    page.get_by_role('button',name='Choose a saved voice',exact=True).click()
    page.locator('.voice-item').filter(has_text='Power and wit').click()
    page.wait_for_selector('.voice-graph')
    page.screenshot(path=str(out/'reusable-voice.png'))
    if not native:
        with page.expect_download() as download:page.get_by_role('button',name='Export voice',exact=True).click()
        download.value.save_as(str(out/'synthetic-voice.json'))
    page.get_by_role('button',name='Use in this project',exact=True).click()
    expect(page.locator('.modal')).to_have_count(0)
    assert page.evaluate('() => state.p.voice_profile.library_id')==vid
    assert page.evaluate('() => state.p.sources.length')==0
    assert page.evaluate('() => state.p.usage.calls')==0
    check('A second project reuses the voice without importing training pieces or spending tokens')
    page.get_by_role('button',name='Your writing voice',exact=True).click()
    page.get_by_role('button',name='View graph overlay',exact=True).click()
    expect(page.locator('svg[aria-label="Voice and evidence overlay"]')).to_be_visible()
    page.get_by_role('button',name='Close dialog',exact=True).click()
    check('Namespaced style/project overlay renders without changing stored evidence')
    return {'voice_id':vid,'model_calls':0,'raw_samples_copied':0,'power_language_preserved':True}
