import json
import pytest
from graphpaper.models import Project,Settings,Angle,Review,PolishCandidate
from graphpaper.editorial import contract,context,system,fingerprint,review_stamp,stale_angles
from graphpaper.pipeline import Job,make_angles,make_outline,write_draft,review_draft,revise
from graphpaper.storage import Store
from graphpaper.ingest import digest
from graphpaper.export import export
from .conftest import ScriptedClients
from .polemic_fixtures import project,VOICE


@pytest.mark.parametrize('mode',['nonfiction','polemic','fiction','science'])
def test_modes_have_independent_editorial_purposes(mode):
    p=project(mode)
    c=contract(p)
    assert c['mode']==mode
    assert 'No fabricated facts' in c['nonnegotiable']
    if mode=='science':assert 'conclusions follow' in c['purpose']
    elif mode=='fiction':assert 'narrative' in c['purpose']
    else:assert 'Argument-led' in c['purpose']


def test_evidence_slider_changes_detail_not_stance_or_truth():
    p=project();p.brief.rigor=0;low=contract(p)
    p.brief.rigor=100;high=contract(p)
    assert low['purpose']==high['purpose'] and low['thesis']==high['thesis']
    assert low['nonnegotiable']==high['nonnegotiable']
    assert low['evidence_instruction']!=high['evidence_instruction']
    assert 'NOT a request for ideological balance' in high['evidence_instruction']


def test_force_does_not_change_the_argument():
    p=project();p.brief.rhetorical_force=0;low=contract(p)
    p.brief.rhetorical_force=100;high=contract(p)
    assert low['thesis']==high['thesis'] and low['purpose']==high['purpose']
    assert low['delivery']!=high['delivery']


def test_opposing_author_gets_same_fidelity_not_a_baked_in_moral_position():
    a=project();b=project(opposite=True)
    ca,cb=contract(a),contract(b)
    assert ca['purpose']==cb['purpose'] and ca['objection_policy']==cb['objection_policy']
    assert ca['thesis']!=cb['thesis']
    assert cb['thesis']==b.brief.thesis


def test_ordinary_nonfiction_respects_argument_without_requiring_new_mode():
    p=Project();p.brief.direction='Argue against the waste of public money.'
    assert 'when it supplies an argument' in contract(p)['purpose']
    p.brief.stance_policy='explore'
    assert 'without a preselected verdict' in contract(p)['purpose']


@pytest.mark.parametrize('stage',['angles','outline','draft','review','revise','polish'])
def test_each_stage_receives_explicit_thesis_and_non_neutrality_contract(stage):
    p=project();instructions=system(p,stage)
    assert p.brief.thesis in instructions
    assert 'does not require neutrality' in instructions
    assert 'Do not invent facts' in instructions


def test_voice_arrives_at_angle_generation_jev_and_outline():
    p=project();c=ScriptedClients();j=Job(p.id,'test')
    make_angles(p,c,j)
    payloads=[json.loads(x[2]) for x in c.calls if x[0]=='complete']
    assert 'samples' in payloads[0]['author_voice']
    assert payloads[0]['author_voice']['samples'][0]['source_id']=='S3'
    assert 'The committee' in str(payloads[0]['author_voice'])
    states=[x[1] for x in c.calls if x[0]=='decide']
    assert all('author_voice' in s and 'editorial_contract' in s for s in states)
    for s in states:
        if 'candidates' in s:
            assert all('S3' not in motif['source_ids'] for motif in s['candidates'])
    assert p.angles[0].scores['stance_fidelity']==.85
    assert p.angles[0].scores['voice_fidelity']==.85
    p.selected_angle=p.angles[0].id;make_outline(p,c,j)
    outline=json.loads([x for x in c.calls if x[0]=='complete'][-1][2])
    assert outline['author_voice']['samples'][0]['source_id']=='S3'
    assert p.brief.thesis in str(outline['editorial_contract'])


def test_no_jev_still_gets_full_voice_and_intention():
    p=project();c=ScriptedClients(Settings(model='fixture',jev_provider='off'))
    make_angles(p,c,Job(p.id,'angles'))
    assert p.angles and p.angles[0].score is None
    assert 'author_voice' in json.loads([x for x in c.calls if x[0]=='complete'][0][2])


def test_stale_voice_profile_still_supplies_current_samples():
    p=project();p.voice_profile.sample_hash='obsolete'
    value=context(p)['author_voice']
    assert value['profile_needs_refresh'] and not value['instructions']
    assert value['samples'][0]['excerpts'][0] == VOICE


def test_voice_off_is_respected_without_erasing_explicit_argument():
    p=project();p.voice_profile.enabled=False
    value=context(p)
    assert value['author_voice']=={'enabled':False}
    assert value['editorial_contract']['thesis']==p.brief.thesis


def test_angle_freshness_tracks_actual_voice_and_brief_changes():
    p=project();c=ScriptedClients();make_angles(p,c,Job(p.id,'angles'))
    assert not stale_angles(p)
    old=p.angles_context_hash;p.brief.rigor=100
    assert stale_angles(p) and fingerprint(p)!=old
    before=p.angles.copy();p.sources[2].text+=' Another authorial sample.'
    assert stale_angles(p) and p.angles==before


def test_legacy_project_is_readable_and_legacy_angles_marked_for_refresh():
    p=Project.model_validate({'title':'Existing','mode':'nonfiction','angles':[{'title':'Old angle','thesis':'An old thesis'}]})
    assert p.brief.stance_policy=='auto' and p.brief.rhetorical_force==70
    assert stale_angles(p)


def test_drafting_review_and_revision_retain_voice_context(tmp_path):
    p=project();c=ScriptedClients(Settings(model='fixture',refine=False));j=Job(p.id,'test');store=Store(tmp_path);store.create(p)
    make_angles(p,c,j);p.selected_angle=p.angles[0].id;make_outline(p,c,j)
    write_draft(p,c,store,j)
    assert p.draft and '[S1]' in p.draft
    assert p.review.context_hash==review_stamp(p)
    calls=[json.loads(x[2]) for x in c.calls if x[0]=='complete']
    assert all('author_voice' in x for x in calls)
    c.calls=[];p.brief.thesis='A deliberately different author position.'
    revise(p,c,j,store,instruction='Use the updated thesis.')
    calls=[json.loads(x[2]) for x in c.calls if x[0]=='complete']
    assert calls[0]['task'].startswith('Act as a rigorous')  # stale review rerun
    assert all(x['editorial_contract']['thesis']==p.brief.thesis for x in calls)


def test_reviewer_reports_stance_drift_without_calling_moral_judgment_a_fact():
    class Drift(ScriptedClients):
        def complete(self,system,user,**kwargs):
            result=super().complete(system,user,**kwargs)
            result['authorial_assessment']={'intent_preserved':False,'stance_preserved':False,'voice_preserved':True,'summary':'The draft turned the verdict into an open question.'}
            result['issues']=[{'severity':'major','category':'authorial_drift','problem':'Thesis neutralized.','suggestion':'Restore the stated judgment.'}]
            return result
    p=project();p.draft='This may warrant a discussion. [S1]'
    review=review_draft(p,Drift(),Job(p.id,'review'))
    assert review.authorial_assessment['stance_preserved'] is False
    assert review.issues[0]['category']=='authorial_drift'


def test_polemic_exports_retain_source_bibliography():
    p=project();p.draft='# An argument\n\nA factual premise. [S1]'
    data,_,_=export(p,'md')
    assert b'## Sources' in data and b'Synthetic evidence note' in data


def test_atomic_mode_switch_preserves_existing_work(client,app):
    p=project('nonfiction');p.draft='My existing draft. [S1]';p.angles=[Angle(title='Original angle',thesis='Original argument')]
    app.state.store.create(p);app.state.store.snapshot(p,'Existing version')
    before=p.model_dump();settings=app.state.store.settings()
    response=client.post('/api/projects/'+p.id+'/writing-mode',json={'version':p.version,'mode':'polemic'})
    assert response.status_code==200,response.text
    after=response.json()
    assert after['mode']=='polemic'
    for key in ['id','sources','graph','angles','outline','draft','voice_profile','usage','story_state']:
        assert after[key]==before[key],key
    assert app.state.store.revisions(p.id)[0]['draft']==p.draft
    assert app.state.store.settings()==settings
    status=client.get('/api/projects/'+p.id+'/editorial/status').json()
    assert status['angles_stale'] and status['voice_samples']==1
    assert client.post('/api/projects/'+p.id+'/writing-mode',json={'version':p.version,'mode':'fiction'}).status_code==409


def test_mode_changes_reject_active_jobs_unknown_modes_and_foreign_fields(client,app):
    p=project();app.state.store.create(p)
    base='/api/projects/'+p.id+'/writing-mode'
    assert client.post(base,json={'version':0,'mode':'unknown'}).status_code==400
    assert client.post(base,json={'version':0,'mode':'nonfiction','draft':'overwrite'}).status_code==400
    j=Job(p.id,'graph');j.state='running';app.state.runner.jobs[j.id]=j
    assert client.post(base,json={'version':0,'mode':'nonfiction'}).status_code==400
    j.state='cancelled'


def test_user_edited_angles_and_outline_become_current_not_discarded(client,app):
    p=project();app.state.store.create(p);base='/api/projects/'+p.id
    value=client.patch(base,json={'version':p.version,'angles':[{'title':'My angle','thesis':p.brief.thesis}]}).json()
    assert value['angles_context_hash']
    assert not client.get(base+'/editorial/status').json()['angles_stale']


def test_polemic_creation_default_and_roundtrip(client):
    r=client.post('/api/projects',json={'title':'My argument','mode':'polemic'})
    assert r.status_code==200
    p=r.json();assert p['brief']['stance_policy']=='preserve'
    backup=client.get('/api/projects/'+p['id']+'/export/json').json()
    restored=client.post('/api/import',json=backup)
    assert restored.status_code==200 and restored.json()['mode']=='polemic'


def test_review_freshness_includes_changes_to_the_selected_argument():
    p=project();p.angles=[Angle(id='chosen',title='Title',thesis='First selected claim')];p.selected_angle='chosen'
    previous=review_stamp(p);p.angles[0].thesis='The author changed this selected claim'
    assert review_stamp(p)!=previous
    assert context(p)['selected_argument']['thesis']==p.angles[0].thesis
    assert context(p,include_selection=False)['selected_argument'] is None
