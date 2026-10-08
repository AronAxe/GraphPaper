import copy
import json
import time
import pytest
from graphpaper.models import Project,Source,VoiceProfile,Graph,Node,Edge,Settings
from graphpaper.style_graph import text_graph,view,overlay,for_profile,StyleGraph
from graphpaper.voice import voice_context,sample_pack
from graphpaper.editorial import context,contract
from graphpaper.voice_library import VoiceLibrary
from .conftest import ScriptedClients


def voice_project():
    return Project(title='First article',voice_profile=VoiceProfile(name='Unapologetic',instructions='Keep the sarcasm. Use fucking strong language when requested. Finish with the verdict.'),sources=[Source(id='S1',title='Evidence',text='Documented observation.'),Source(id='S2',title='My writing',text='TRAINING_TEXT_ONLY '+('Original prose with wit and rhythm. '*30),role='voice')],graph=Graph(nodes=[Node(id='voice',label='An evidence concept',kind='claim')]),draft='Current writing.')


def test_graph_roundtrip_and_power_language_are_not_sanitized():
    text='Use fucking strong language.\nKeep anger, ridicule and jokes.\nThe author can change the tone.'
    graph=text_graph(text,'My voice')
    assert StyleGraph.model_validate_json(graph.model_dump_json())==graph
    assert 'fucking' in graph.model_dump_json()
    assert all(e.target in {n.id for n in graph.nodes} for e in graph.edges)


def test_small_graph_view_is_edge_closed_without_clipping_habits():
    graph=text_graph('\n'.join('Habit '+str(i)+': '+str(i)*450 for i in range(24)))
    result=view(graph,2500);ids={n['id'] for n in result['nodes']}
    assert len(json.dumps(result,ensure_ascii=False,separators=(',',':')).encode())<=2500
    assert all(e['source'] in ids and e['target'] in ids for e in result['edges'])
    assert all(n['instruction']==next(x.instruction for x in graph.nodes if x.id==n['id']) for n in result['nodes'])
    assert not result['coverage']['complete']


def test_save_apply_does_not_copy_training_or_mutate_other_projects(tmp_path):
    from graphpaper.storage import Store
    store=Store(tmp_path);library=VoiceLibrary(store);original=voice_project();store.create(original)
    saved=library.create(original.voice_profile,[s for s in original.sources if s.role=='voice'])
    another=Project(title='Second article');before=another.sources.copy();library.apply(another,saved)
    assert another.sources==before and not another.voice_profile.sample_ids
    result=voice_context(another)
    assert not result['samples'] and result['graph']['nodes']
    assert 'TRAINING_TEXT_ONLY' not in json.dumps(result)
    assert library.list()[0]['samples']==1
    assert store.get(original.id)==original
    library.delete(saved.id,saved.version)
    assert voice_context(another)==result


def test_overlay_namespaces_colliding_ids_and_does_not_change_evidence():
    p=voice_project();p.voice_profile.graph=for_profile(p.voice_profile).model_dump()
    before=p.graph.model_dump();result=overlay(p)
    ids={n['id'] for n in result['nodes']}
    assert 'style:voice' in ids and 'evidence:voice' in ids
    assert any(e['layer']=='overlay' for e in result['edges'])
    assert p.graph.model_dump()==before


def test_graph_preferences_do_not_cap_current_article_force():
    p=voice_project();p.brief.rhetorical_force=100;p.brief.direction='Use forceful language and do not soften the conclusion.'
    assert 'current author brief' in contract(p)['voice_precedence'].lower()
    value=context(p,compact=True)
    assert value['author_voice']['graph']['nodes']
    assert 'samples' not in value['author_voice']
    assert p.brief.direction in str(value)


def test_many_training_pieces_respect_the_actual_excerpt_budget():
    p=Project(sources=[Source(id=f'S{i}',title='Writing',text='word '*1000,role='voice') for i in range(24)])
    samples=sample_pack(p,1800)
    assert sum(len(t) for s in samples for t in s['excerpts'])<=1800


def test_library_api_reuse_export_and_conflict(client,app):
    p=voice_project();app.state.store.create(p)
    response=client.post('/api/voices',json={'project_id':p.id,'version':0,'name':'My voice'})
    assert response.status_code==200,response.text
    v=response.json();assert v['graph']['nodes']
    other=client.post('/api/projects',json={'title':'Second'}).json()
    applied=client.post('/api/projects/'+other['id']+'/voice/apply',json={'version':0,'voice_id':v['id']})
    assert applied.status_code==200 and not applied.json()['sources']
    assert applied.json()['voice_profile']['library_id']==v['id']
    assert client.post('/api/projects/'+other['id']+'/voice/apply',json={'version':0,'voice_id':v['id']}).status_code==409
    exported=client.get('/api/voices/'+v['id']+'/export').json()
    assert 'TRAINING_TEXT_ONLY' not in json.dumps(exported)
    restored=client.post('/api/voices/import',json=exported)
    assert restored.status_code==200 and restored.json()['id']!=v['id']
    assert not restored.json()['samples']
    assert app.state.store.get(p.id)==p


def test_new_training_is_not_project_evidence_and_learns_once(client,app):
    app.state.runner.clients_factory=ScriptedClients
    app.state.store.set_settings(Settings(model='fixture',allow_cloud=True).model_dump())
    v=client.post('/api/voices',json={'name':'Reusable'}).json()
    v=client.post('/api/voices/'+v['id']+'/samples/text',json={'title':'Training','text':'Original writing with rhythm and wit. '*40}).json()
    assert not client.get('/api/bootstrap').json()['projects']
    j=client.post('/api/voices/'+v['id']+'/learn',json={'version':v['version']}).json()
    for _ in range(200):
        status=client.get('/api/jobs/'+j['id']).json()
        if status['state'] not in {'queued','running'}:break
        time.sleep(.02)
    assert status['state']=='completed',status
    saved=client.get('/api/voices/'+v['id']).json()
    assert saved['graph']['nodes'] and status['usage']['calls']==1
    assert not client.get('/api/bootstrap').json()['projects']


def test_invalid_graph_and_outdated_library_save_fail_without_mutation(client):
    v=client.post('/api/voices',json={'instructions':'My direct style.'}).json()
    assert client.patch('/api/voices/'+v['id'],json={'version':999,'name':'Overwrite'}).status_code==409
    invalid={'nodes':[{'id':'a','label':'A'}],'edges':[{'source':'a','target':'missing'}]}
    assert client.patch('/api/voices/'+v['id'],json={'version':v['version'],'graph':invalid}).status_code==400
    assert client.get('/api/voices/'+v['id']).json()['profile']==v['profile']


def test_existing_project_schema_still_loads_and_voice_graph_is_optional():
    p=Project.model_validate({'title':'Old work','voice_profile':{'instructions':'A direct style.'}})
    assert not p.voice_profile.library_id
    assert for_profile(p.voice_profile).nodes
    assert p.sources==[]
