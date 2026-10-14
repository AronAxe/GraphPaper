"""End-to-end control decisions using typed, explicitly synthetic fixtures."""
import importlib.util
import json
import pytest
from graphpaper.models import Project, Source, Node, Edge, Graph, Settings, Angle
from graphpaper.ingest import digest
from graphpaper.storage import Store


def module(name):
    assert importlib.util.find_spec('graphpaper.'+name), name+' is not implemented'
    return __import__('graphpaper.'+name,fromlist=['*'])


def answer(q,value=.94):
    if q['type']=='noul':return {'type':'noul','noul':value}
    criteria=q['criteria'];keys=list(criteria) if q['type']=='choice' else list(map(str,range(len(criteria))))
    selected=keys[0] if q['type']=='choice' else keys[-1]
    probabilities={k:float(k==selected) for k in keys}
    return {'type':q['type'],'confidence':1,'probabilities':probabilities,**({'choice':selected} if q['type']=='choice' else {'score':len(keys)-1,'legend':dict(zip(keys,criteria))})}


class DecisionClient:
    def __init__(self,tmp_path=None,judge=None,settings=None):
        self.settings=settings or Settings(model='writer',allow_cloud=True,refine=False)
        self.system_one_store=Store(tmp_path) if tmp_path else None
        self.calls=[];self.job=None;self.judge=judge
    def jev_route(self):return 'off' if self.settings.jev_provider=='off' else 'typesafe'
    def decide(self,state,questions):
        self.calls.append((state,questions))
        if self.jev_route()=='off':return None
        return {k:self.judge(state,k,q) if self.judge else answer(q,.03 if any(t in k for t in ['added_allegation','irrelevant_caveat','needs_research','contradiction','repetitive','meaning_drift','lost_reasoning']) else .94) for k,q in questions.items()}


def project():
    p=Project(mode='polemic');p.brief.thesis='Condemn deliberate cruelty without pretending consciousness is proven.'
    p.sources=[Source(id='S1',title='Source',text='A narrow reported finding.',digest=digest('A narrow reported finding.'))]
    p.graph=Graph(nodes=[Node(id='a',label='First'),Node(id='b',label='Second'),Node(id='c',label='Third')],edges=[Edge(id='ab',source='a',target='b'),Edge(id='bc',source='b',target='c')])
    return p


def test_all_angles_evaluated_together_and_failed_fidelity_gets_repair():
    m=module('s1_editorial');p=project();c=DecisionClient()
    p.angles=[Angle(id='a'+str(i),title='Proposition '+str(i),thesis=p.brief.thesis) for i in range(6)]
    m.assess_angles(p,c)
    assert len(c.calls)==1
    assert all(a.decision=='Ready to develop' for a in p.angles)
    def fail(state,k,q):return answer(q,.04 if k.endswith('stance_fidelity') else .94)
    c.judge=fail;m.assess_angles(p,c)
    assert all(a.decision=='Restore author intent' for a in p.angles)
    assert p.angles[0].id in p.system_one['angle_policies']


def test_retrieval_reranks_concrete_relevance_not_words():
    m=module('s1_retrieval');p=project()
    def judge(state,k,q):
        index=int(k.split('_')[0][1:]);return answer(q,.05 if index==0 else .97)
    c=DecisionClient(judge=judge)
    pack={'passages':[{'source_id':'S1','text':'keyword only','start':0,'end':12},{'source_id':'S2','text':'The needed direct evidence.','start':0,'end':26}],'total_passages':2}
    out=m.rerank_pack(p,c,pack,'Find the direct evidence',budget=3000)
    assert out['passages'][0]['source_id']=='S2'
    assert out['selection']=='System One semantic reranking'


def test_semantic_retrieval_preserves_required_source_ids_when_budget_fits():
    m=module('s1_retrieval');p=project();c=DecisionClient()
    pack={'passages':[{'source_id':'S1','text':'Evidence','start':0,'end':8},{'source_id':'S2','text':'Other','start':0,'end':5}],'total_passages':2}
    out=m.rerank_pack(p,c,pack,'question',3000,required_ids=['S2'])
    assert 'S2' in [i['source_id'] for i in out['passages']]


def test_changed_passages_check_cannot_hide_global_deletions():
    m=module('s1_editorial')
    before='First claim.\n\n'+('Long unchanged body. '*200)+'\n\nFinal moral conclusion.'
    after=before.replace('Final moral conclusion.','')
    changes=m.changed_passages(before,after)
    assert any('Final moral conclusion.' in x['original'] for x in changes)


def test_uncertain_polish_routes_to_editor_without_accepting_change():
    m=module('s1_editorial');p=project();c=DecisionClient(judge=lambda state,k,q:answer(q,.5))
    report=m.assess_edit(p,c,'The conduct is vile.','The conduct may invite scrutiny.')
    assert report['decision']=='escalate' and report['meaning_preserved'] is None


def test_graph_exploration_extends_without_changing_evidence():
    m=module('s1_graph');p=project();c=DecisionClient();original=p.graph.model_dump_json()
    motifs=[{'id':'m1','node_ids':['a','b'],'edge_ids':['ab'],'nodes':[n.model_dump() for n in p.graph.nodes[:2]],'edges':[p.graph.edges[0].model_dump()],'source_ids':['S1'],'structural_rank':3,'motif':'relationship','judgments':{'fit':{'type':'noul','noul':.95}}}]
    out=m.explore(p,c,motifs)
    assert any('c' in r['node_ids'] for r in out)
    assert p.graph.model_dump_json()==original


def test_alignment_is_a_proposal_never_silent_collapse():
    m=module('s1_graph');p=project();p.graph.nodes.append(Node(id='a2',label='First idea'))
    c=DecisionClient();before=p.graph.model_dump_json();rows=m.alignment(p,c)
    assert p.graph.model_dump_json()==before
    assert isinstance(rows,list) and 'alignment' in p.system_one


def test_science_screening_is_advice_not_exclusion():
    m=module('s1_science')
    from graphpaper.science_models import ResearchRecord,ScholarlyMeta
    p=Project(mode='science');p.research.records=[ResearchRecord(id='r1',metadata=ScholarlyMeta(title='Clinical study'),abstract='Sample findings.')]
    c=DecisionClient();m.screen(p,c)
    assert p.research.records[0].decision=='unscreened'
    assert 'r1' in p.system_one['screening']


def test_routing_never_chooses_unapproved_model():
    m=module('s1_routing');p=project();c=DecisionClient()
    assert m.select_model(p,c,'draft','Write the essay')['model']=='writer'
    c.settings.system_one_routing=True
    assert m.select_model(p,c,'draft','Write the essay')['model']=='writer'
    assert not c.calls


def test_high_confidence_polish_check_saves_the_second_full_llm_call():
    from graphpaper.polish import polish_draft
    from graphpaper.pipeline import Job
    p=project();p.draft='It is important to note that this moral judgment is deliberate.'
    class Client(DecisionClient):
        writes=0
        def complete(self,system,user,**kwargs):
            self.writes+=1
            if kwargs.get('json_mode'):raise AssertionError('A high-confidence local comparison should not ask for a second full generative review.')
            return json.loads(user)['draft'].replace('It is important to note that ','')
    c=Client();polish_draft(p,c,Job(p.id,'deslop'),'deslop')
    assert c.writes==1
    assert p.polish.review['decision']=='present'
    assert p.draft.startswith('It is important')


def test_live_adapter_routing_preserves_explicit_provider_and_uses_approved_effort(tmp_path):
    import httpx
    from graphpaper.providers import Clients
    from graphpaper.secrets import Vault
    p=project();v=Vault(tmp_path);v.set('llm','fixture',False);v.set('typesafe','fixture',False);requests=[]
    def transport(req):
        data=json.loads(req.content);requests.append((str(req.url),data))
        if 'questions' in data:
            return httpx.Response(200,json={'answers':{k:answer(q,.95 if k.endswith('difficult') else .03) for k,q in data['questions'].items()}})
        return httpx.Response(200,json={'choices':[{'message':{'content':'Written prose.'},'finish_reason':'stop'}]})
    settings=Settings(provider='openai-compatible',base_url='https://writer.example/v1',model='usual',jev_provider='typesafe',allow_cloud=True,
        system_one_routing=True,system_one_deep_model='author-approved-deep')
    c=Clients(settings,v,transport=httpx.MockTransport(transport));c.system_one_project=p;c.system_one_store=Store(tmp_path/'db')
    assert c.complete('Write.',json.dumps({'task':'Synthesize the complex argument.'}))=='Written prose.'
    writing=[r for r in requests if r[0].endswith('/chat/completions')]
    assert writing[0][0]=='https://writer.example/v1/chat/completions'
    assert writing[0][1]['model']=='author-approved-deep' and c.settings.model=='usual'


def test_failed_optional_angle_repair_does_not_erase_generated_angles():
    m=module('s1_editorial');p=project();p.angles=[Angle(id='a',title='Original generated proposal',thesis='Inspect this proposal.')]
    p.system_one={'angle_policies':{'a':{'action':'repair_intent','reasons':['Restore the conclusion.']}}}
    class Client(DecisionClient):
        def complete(self,*args,**kwargs):
            from graphpaper.providers import ProviderError
            raise ProviderError('Temporary writer unavailable')
    from graphpaper.pipeline import Job
    m.repair_angles(p,Client(),Job(p.id,'angles'))
    assert p.angles[0].title=='Original generated proposal'
