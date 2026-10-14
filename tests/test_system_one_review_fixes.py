"""Regression cases found during whole-branch integration review."""
import httpx,json
from graphpaper.models import Project,Source,Angle,Settings
from graphpaper.pipeline import Job
from graphpaper.providers import Clients,ProviderError
from graphpaper.storage import Store
from graphpaper.secrets import Vault
from graphpaper.system_one import Engine,noul
from tests.test_system_one_workflow import DecisionClient,answer


def test_decisions_receive_explicit_author_corrections(tmp_path):
    from graphpaper.s1_learning import add_feedback
    p=Project();store=Store(tmp_path);add_feedback(store,p,'a',0,{},'Keep my punchline.')
    c=DecisionClient();Engine(c,p,store).evaluate('test',[{'id':'a'}],{'fit':noul('Fits?')})
    assert 'Keep my punchline.' in str(c.calls[0][0])


def test_judgment_fanout_reserves_capacity_for_the_writer(tmp_path):
    vault=Vault(tmp_path);vault.set('typesafe','fixture',False);job=Job('p','test')
    calls=[]
    def handler(req):
        calls.append(req);data=json.loads(req.content)
        return httpx.Response(200,json={'answers':{k:answer(q) for k,q in data['questions'].items()}})
    c=Clients(Settings(allow_cloud=True,jev_provider='typesafe',max_calls=5),vault,job,transport=httpx.MockTransport(handler))
    result=Engine(c).evaluate('test',[{'id':str(i),'text':str(i)*20000} for i in range(5)],{'fit':noul('Fits?')},reserve=2)
    assert result=={} and calls==[]


def test_existing_angle_audit_has_project_evidence():
    from graphpaper.s1_editorial import assess_angles
    p=Project();p.sources=[Source(id='S1',title='Source',text='A relevant reported observation.')]
    p.angles=[Angle(id='a',title='Observation',thesis='A relevant observation.',source_ids=['S1'])]
    c=DecisionClient();assess_angles(p,c)
    assert 'A relevant reported observation.' in str(c.calls[0][0]['candidates'])


def test_no_scene_assessment_is_not_a_successful_repair():
    from graphpaper.s1_science import scene_check
    class Down(DecisionClient):
        def decide(self,*args):raise ProviderError('unavailable')
    assert scene_check(Project(mode='fiction'),Down(),'New scene.',{}) is None


def test_uncertain_scene_assessment_does_not_authorize_a_change():
    from graphpaper.s1_science import scene_check
    c=DecisionClient(judge=lambda state,k,q:answer(q,.5))
    assert scene_check(Project(mode='fiction'),c,'New scene.',{}) is None
