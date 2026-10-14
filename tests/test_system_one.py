"""Behavioral contracts for the System One control layer, not live JEV accuracy."""
import importlib.util
import math
import pytest
from graphpaper.models import Settings
from graphpaper.providers import Clients, ProviderError
from graphpaper.pipeline import Job
from graphpaper.secrets import Vault
import httpx


def core():
    assert importlib.util.find_spec('graphpaper.system_one'), 'System One decision layer is missing'
    from graphpaper import system_one
    return system_one


def test_weak_choice_does_not_authorize_a_rewrite():
    s=core()
    a={'type':'choice','choice':'revise','probabilities':{'revise':.34,'research':.33,'author_review':.33},'confidence':.01}
    assert s.choice_action(a,'author_review')=='author_review'


def test_missing_distribution_cannot_authorize_automatic_changes():
    assert core().choice_action({'type':'choice','choice':'revise'},'author_review')=='author_review'


def test_stance_failure_is_not_compensated_by_fluent_prose():
    s=core();row={k:{'type':'noul','noul':v} for k,v in {'stance_fidelity':.05,'voice_fidelity':.98,'reasoning_preserved':.97,'added_allegation':.02,'irrelevant_caveat':.03,'grounded':.99}.items()}
    row['craft']={'type':'score','score':3,'legend':{str(i):str(i) for i in range(4)},'probabilities':{'0':0,'1':0,'2':0,'3':1},'confidence':1}
    assert s.angle_policy(row, preserve=True)['action']=='repair_intent'
    assert s.angle_policy(row,preserve=True)['eligible'] is False


def test_unscored_and_scored_motifs_have_separate_comparable_order():
    s=core()
    rows=[{'id':'raw','structural_rank':999}, {'id':'good','structural_rank':2,'judgments':{'fit':{'type':'noul','noul':.95},'grounded':{'type':'noul','noul':.9}}}]
    assert s.rank_records(rows)[0]['id']=='good'
    assert s.rank_records([rows[0],{'id':'other','structural_rank':1}])[0]['id']=='raw'


def test_independent_candidates_are_fanned_out_in_one_decision_call():
    s=core()
    class Fake:
        settings=Settings(model='fixture')
        job=None
        calls=[]
        def jev_route(self):return 'typesafe'
        def decide(self,state,questions):
            self.calls.append((state,questions))
            return {k:{'type':'noul','noul':.9} for k in questions}
    c=Fake();e=s.Engine(c)
    result=e.evaluate('ranking',[{'id':str(i),'text':'brief candidate'} for i in range(30)],{'fit':s.noul('Does this candidate fit the task?')},{'task':'test'})
    assert len(c.calls)==1 and len(c.calls[0][1])==30
    assert set(result)=={str(i) for i in range(30)}
    assert all(str(i) in c.calls[0][1]['c'+str(i)+'_fit']['instructions'] for i in range(30))


def test_score_validation_and_normalization_match_declared_levels(tmp_path):
    s=core();q=s.score('Level?', ['Absent','Present','Complete'])
    ans={'type':'score','score':1.43,'legend':{'0':'Absent','1':'Present','2':'Complete'},'probabilities':{'0':0,'1':.57,'2':.43},'confidence':.355}
    assert s.validate_answer(q,ans)['score']==1.43
    assert s.normalized(ans)==pytest.approx(.715)
    for v in [True,float('nan'),3,-1]:
        with pytest.raises(ProviderError):s.validate_answer(q,{**ans,'score':v})
    with pytest.raises(ProviderError):s.validate_answer(q,{**ans,'probabilities':{'0':.5,'1':.5,'2':.5}})


def test_uncertain_intent_does_not_mean_unusable_or_softened():
    decision=core().angle_policy({'stance_fidelity':{'type':'noul','noul':.5}},preserve=True)
    assert decision['action']=='author_review' and not decision['automatic']


def test_actual_score_transport_is_validated(tmp_path):
    s=core();v=Vault(tmp_path);v.set('typesafe','fixture',False)
    q=s.score('How specific?', ['Generic','Some detail','Concrete'])
    def handler(req):return httpx.Response(200,json={'answers':{'s':{'type':'score','score':2,'legend':dict(enumerate(q['criteria'])),'probabilities':{'0':0,'1':0,'2':1},'confidence':1}}})
    c=Clients(Settings(model='fixture',allow_cloud=True,jev_provider='typesafe'),v,transport=httpx.MockTransport(handler))
    assert c.decide({'text':'fixture'},{'s':q})['s']['score']==2


def test_decision_cache_requires_exact_context_and_question(tmp_path):
    s=core()
    from graphpaper.storage import Store
    class Fake:
        settings=Settings(model='fixture');job=None;calls=0
        def jev_route(self):return 'typesafe'
        def decide(self,state,qs):self.calls+=1;return {k:{'type':'noul','noul':.9} for k in qs}
    c=Fake();store=Store(tmp_path);e=s.Engine(c,store=store)
    e.evaluate('test',[{'id':'a','text':'one'}],{'fit':s.noul('Fits?')},{'brief':'A'})
    e.evaluate('test',[{'id':'a','text':'one'}],{'fit':s.noul('Fits?')},{'brief':'A'})
    assert c.calls==1
    e.evaluate('test',[{'id':'a','text':'one'}],{'fit':s.noul('Fits?')},{'brief':'B'})
    assert c.calls==2


def test_optional_provider_failure_retains_explicit_unscored_state():
    s=core()
    class Fake:
        settings=Settings(model='fixture');job=None
        def jev_route(self):return 'typesafe'
        def decide(self,*args):raise ProviderError('fixture unavailable')
    e=s.Engine(Fake());assert e.evaluate('test',[{'id':'a'}],{'fit':s.noul('Fits?')})=={}
    assert e.records[-1]['status']=='unavailable'


def test_malformed_choice_distribution_never_passes_as_confident():
    s=core();q=s.choice('Next?',{'revise':'Fix it','keep':'Keep it'})
    with pytest.raises(ProviderError):s.validate_answer(q,{'type':'choice','choice':'revise','probabilities':{'revise':.1,'keep':.9},'confidence':1})


def test_primitive_validation_recomputes_overstated_confidence():
    s=core();q=s.choice('Next?',{'a':'A','b':'B','c':'C'})
    a=s.validate_answer(q,{'type':'choice','choice':'a','probabilities':{'a':.34,'b':.33,'c':.33},'confidence':1})
    assert a['confidence']<.02
    assert s.choice_action(a,'keep')=='keep'


def test_master_switch_stops_decisions_even_when_a_key_is_configured(tmp_path):
    s=core();v=Vault(tmp_path);v.set('typesafe','fixture',False);seen=[]
    c=Clients(Settings(model='fixture',allow_cloud=True,jev_provider='typesafe',system_one_enabled=False),v,transport=httpx.MockTransport(lambda req:seen.append(req)))
    assert s.Engine(c).evaluate('test',[{'id':'a'}],{'test':s.noul('Test?')})=={}
    assert seen==[]


def test_cached_receipt_keeps_the_original_resolved_model(tmp_path):
    from graphpaper.storage import Store
    s=core();job=Job('fixture','test')
    class Fake:
        settings=Settings(model='fixture')
        def jev_route(self):return 'typesafe'
        def decide(self,state,questions):
            self.job.receipts.append({'stage':'JEV','model':'jev-resolved-original'})
            return {k:{'type':'noul','noul':.9} for k in questions}
    c=Fake();c.job=job;e=s.Engine(c,store=Store(tmp_path))
    e.evaluate('test',[{'id':'a'}],{'fit':s.noul('Fits?')})
    job.receipts.append({'stage':'JEV','model':'unrelated-later-model'})
    e.evaluate('test',[{'id':'a'}],{'fit':s.noul('Fits?')})
    assert e.records[-1]['status']=='cached'
    assert e.records[-1]['resolved_model']=='jev-resolved-original'
