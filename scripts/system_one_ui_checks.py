"""Inspect the real decision desk with clearly synthetic structured judgments."""
import json
from pathlib import Path
from playwright.sync_api import expect


def exercise(page,check,out,native=False):
    original=page.evaluate('() => state.p.id')
    fixture={'title':'System One — synthetic workflow check','mode':'polemic','brief':{'thesis':'Preserve the intended judgment.','direction':'Do not replace a conclusion with a committee meeting.'},
        'sources':[{'id':'S1','title':'Synthetic notes','text':'A deliberately synthetic source for UI testing.','role':'evidence'}],
        'graph':{'nodes':[{'id':'n1','label':'The argument','kind':'claim'},{'id':'n2','label':'Its consequence','kind':'concept'}],
                 'edges':[{'id':'e1','source':'n1','target':'n2','relation':'supports'}]},
        'angles':[{'id':'a1','title':'A sharp argument','thesis':'A categorical moral judgment with a separate factual premise.',
                   'scores':{'craft':.9,'novelty':.8,'stance_fidelity':.96,'voice_fidelity':.96,'grounded':.9,'reasoning_preserved':.96},'decision':'Ready to develop','score':86}],
        'system_one':{'decisions':[{'id':'fixture','stage':'Synthetic intent check','status':'evaluated','model':'synthetic fixture — not live JEV','route':'fixture',
            'question_count':2,'elapsed_ms':0,'policy':'system-one-1','state_hash':'synthetic','questions':{
                'intent':{'type':'noul','instructions':'Does the proposal preserve the intended argument?'},
                'action':{'type':'choice','instructions':'What should the application do?','criteria':{'author_review':'Show it to the author.','revise':'Repair a known error.','research':'Find missing evidence.'}}},
            'answers':{'intent':{'type':'noul','noul':.96},'action':{'type':'choice','choice':'author_review','confidence':.85,'probabilities':{'author_review':.9,'revise':.05,'research':.05}}}}],
            'angle_policies':{'a1':{'eligible':True,'action':'ready','reasons':['The proposal preserves the requested argument.']}}}}
    pid=page.evaluate('async (data) => {const p=await api("/import",data);await setProject(p);return p.id;}',fixture)
    page.locator('[data-action="s1-open"]').click();page.wait_for_selector('.s1-desk')
    expect(page.get_by_role('heading',name='Fast judgments. Your decisions.',exact=True)).to_be_visible()
    expect(page.get_by_text('96% yes',exact=True)).to_be_visible();expect(page.get_by_text('synthetic fixture — not live JEV',exact=True)).to_be_visible()
    check('System One desk renders typed probabilities and identifies synthetic test material')
    page.locator('[data-action="s1-reject"]').click();page.locator('#s1-correction').fill('Keep my categorical conclusion and comic timing.')
    page.locator('[data-action="s1-save-feedback"]').click();expect(page.locator('.modal')).to_have_count(0)
    expect(page.locator('.s1-stats > div').nth(3).locator('b')).to_have_text('1')
    assert page.evaluate('() => s1UI.data.feedback[0].label')==0
    assert 'categorical' in page.evaluate('() => s1UI.data.feedback[0].correction')
    check('An explicit author correction persists without rewriting the manuscript')
    page.locator('.s1-receipt').filter(has=page.get_by_text('Saved corrections & local learning')).first.locator('summary').click()
    page.locator('[data-action="s1-train"]').click()
    expect(page.locator('.toast').filter(has_text='Use both prefer and reject')).to_be_visible()
    assert page.evaluate('() => s1UI.data.preference_model.status')=='not_trained'
    check('Insufficient labels do not fabricate a trained preference model')
    report=page.evaluate('async () => api("/projects/"+state.p.id+"/export/system-one")')
    assert report['feedback'][0]['correction'].startswith('Keep my categorical')
    assert report['evaluation_design']['metrics']
    check('Decision/feedback export includes actual judgments and evaluation metadata')
    page.locator('[data-action="s1-settings"]').click();expect(page.locator('#s1-routing')).not_to_be_checked()
    page.locator('#s1-fast-model').fill('');page.locator('#s1-deep-model').fill('')
    page.locator('[data-action="s1-save-settings"]').click();expect(page.locator('.modal')).to_have_count(0)
    assert page.evaluate('() => state.settings.system_one_routing') is False
    check('Model routing remains opt-in and preserves author-selected models')
    page.screenshot(path=str(Path(out)/'system-one.png'),full_page=True)
    if not native:
        page.set_viewport_size({'width':1000,'height':800});page.wait_for_timeout(100)
        assert page.evaluate('() => document.documentElement.scrollWidth')<=1000
        check('Decision desk fits a smaller Windows-sized viewport')
    # Restore the original test project, preserving downstream native save/close checks.
    page.evaluate('async id => openProject(id)',original)
    return {'fixture_project':pid,'restored_project':original,'live_jev':False}
