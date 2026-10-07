import json
import pytest
from graphpaper.models import Settings,Angle,Section,PolishCandidate
from graphpaper.pipeline import Job,write_draft
from graphpaper.argument_draft import use_whole_draft
from graphpaper.editorial import review_stamp
from graphpaper.polish import polish_draft
from graphpaper.storage import Store
from graphpaper.ingest import digest
from .conftest import ScriptedClients
from .polemic_fixtures import project


def ready_project(mode='polemic'):
    p=project(mode);p.angles=[Angle(id='argument',title='The argument',thesis=p.brief.thesis,source_ids=['S1','S2'])];p.selected_angle='argument'
    p.outline=[Section(title=t,purpose='Advance the author thesis',source_ids=['S1','S2'],target_words=300) for t in ['Opening','Develop the comparison','The verdict']]
    return p


def test_short_polemic_is_not_three_independent_restarts(tmp_path):
    p=ready_project();store=Store(tmp_path);store.create(p);clients=ScriptedClients(Settings(model='fixture',refine=False))
    write_draft(p,clients,store,Job(p.id,'draft'))
    calls=[json.loads(x[2]) for x in clients.calls if x[0]=='complete']
    assert len([x for x in calls if x['task'].startswith('Write the complete argumentative essay')])==1
    assert not any(x['task'].startswith('Write only this section') for x in calls)
    assert calls[0]['author_voice']['samples']
    assert len(calls[0]['approved_outline'])==3 and calls[0]['target_words']==900
    assert p.review.context_hash==review_stamp(p)
    assert store.revisions(p.id)


def test_long_and_exploratory_work_retains_existing_section_workflow():
    p=ready_project();p.outline[0].target_words=4000
    assert not use_whole_draft(p)
    p=ready_project('nonfiction');p.brief.stance_policy='explore'
    assert not use_whole_draft(p)
    p.brief.stance_policy='preserve';assert use_whole_draft(p)
    p.mode='science';assert not use_whole_draft(p)
    p.mode='fiction';assert not use_whole_draft(p)


class PolishFixture:
    def __init__(self,drift=False):self.calls=[];self.drift=drift
    def complete(self,system,user,**kwargs):
        data=json.loads(user);self.calls.append((system,data))
        if kwargs.get('json_mode'):
            return {'meaning_preserved':True,'stance_preserved':not self.drift,'voice_preserved':True,'summary':'A synthetic fidelity check.','warnings':['Position changed.'] if self.drift else [],'improvements':[]}
        return data['draft']


@pytest.mark.parametrize('mode',['humanize','deslop','both'])
def test_polish_and_its_critic_receive_voice_and_stance(mode):
    p=ready_project();p.draft='The invitation is ugly. Moral judgment is not a permission slip. [S1]'
    clients=PolishFixture();polish_draft(p,clients,Job(p.id,mode),mode)
    assert len(clients.calls)==2
    for instructions,request in clients.calls:
        assert p.brief.thesis in instructions
        assert request['author_voice']['samples'] and request['editorial_contract']['mode']=='polemic'
    assert p.polish.context_hash==review_stamp(p) and p.polish.draft==p.draft


def test_stance_drift_is_a_meaning_warning_even_if_facts_unchanged():
    p=ready_project();p.draft='A moral judgment with a precise factual basis. [S1]'
    polish_draft(p,PolishFixture(drift=True),Job(p.id,'deslop'),'deslop')
    assert p.polish.review['meaning_preserved'] is False
    assert p.draft=='A moral judgment with a precise factual basis. [S1]'


def test_stale_polish_cannot_be_applied_over_a_new_brief(client,app):
    p=ready_project();p.draft='Existing thesis. [S1]';p.polish=PolishCandidate(mode='deslop',original_hash=digest(p.draft),context_hash=review_stamp(p),draft=p.draft,review={'meaning_preserved':True})
    p.brief.thesis='The author changed the argument.';app.state.store.create(p)
    response=client.post('/api/projects/'+p.id+'/craft/accept',json={'version':p.version})
    assert response.status_code==409,response.text
    assert app.state.store.get(p.id).draft==p.draft
