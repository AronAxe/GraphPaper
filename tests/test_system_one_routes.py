from graphpaper.models import Project,Angle,Node,Edge,Source,Evidence
import pytest


def make(app):
    p=Project(mode='polemic');p.angles=[Angle(id='a',title='Forceful thesis',thesis='Make the actual argument.',scores={'craft':.9,'novelty':.8,'stance_fidelity':.95,'reasoning_preserved':.95,'voice_fidelity':.94,'grounded':.9})]
    app.state.store.create(p);return p


def test_decision_desk_is_available_without_model_calls(client,app):
    p=make(app)
    r=client.get('/api/projects/'+p.id+'/system-one')
    assert r.status_code==200,r.text
    assert r.json()['state']=={} and r.json()['preference_model']['active'] is False


def test_explicit_feedback_is_saved_and_can_be_retracted(client,app):
    p=make(app);root='/api/projects/'+p.id+'/system-one'
    r=client.post(root+'/feedback',json={'version':p.version,'angle_id':'a','label':1,'correction':'Keep the punchline.'})
    assert r.status_code==200,r.text
    assert client.get(root).json()['feedback'][0]['correction']=='Keep the punchline.'
    ident=r.json()['id'];r=client.delete(root+'/feedback/'+ident)
    assert r.status_code==200 and client.get(root).json()['feedback']==[]


def test_stale_feedback_cannot_label_a_replaced_angle(client,app):
    p=make(app);r=client.post('/api/projects/'+p.id+'/system-one/feedback',json={'version':999,'angle_id':'a','label':0})
    assert r.status_code==409


def test_train_and_export_report_truthful_insufficient_data(client,app):
    p=make(app)
    r=client.post('/api/projects/'+p.id+'/system-one/train',json={})
    assert r.status_code==200 and r.json()['status']=='insufficient_data'
    exported=client.get('/api/projects/'+p.id+'/export/system-one')
    assert exported.status_code==200 and 'evaluation_design' in exported.json()


def test_manual_alignment_merge_preserves_quotes_and_supports_undo(client,app):
    p=make(app);p.graph.nodes=[Node(id='n1',label='Entity',evidence=[Evidence(source_id='S1',quote='one')]),Node(id='n2',label='Entity alias',evidence=[Evidence(source_id='S1',quote='two')]),Node(id='n3',label='Third')]
    p.graph.edges=[Edge(id='e1',source='n2',target='n3')];p.draft='Keep the manuscript.'
    p=app.state.store.save(p,p.version);before=p.graph.model_dump()
    r=client.post('/api/projects/'+p.id+'/graph/edit',json={'version':p.version,'operation':'merge-nodes','id':'n2','values':{'into':'n1'}})
    assert r.status_code==200,r.text
    after=r.json()['project'];assert len(after['graph']['nodes'])==2 and after['graph']['edges'][0]['source']=='n1'
    assert [x['quote'] for x in after['graph']['nodes'][0]['evidence']]==['one','two']
    restored=client.post('/api/projects/'+p.id+'/graph/undo',json={'version':after['version']})
    assert restored.json()['project']['graph']==before
    assert restored.json()['project']['draft']=='Keep the manuscript.'


def test_native_system_one_export_uses_local_store_and_no_model(tmp_path,monkeypatch):
    import sys,json
    from types import SimpleNamespace
    from unittest.mock import Mock
    from graphpaper.storage import Store
    from graphpaper.desktop import DesktopBridge
    store=Store(tmp_path/'data');p=Project();store.create(p);target=tmp_path/'decisions.json'
    monkeypatch.setitem(sys.modules,'webview',SimpleNamespace(FileDialog=SimpleNamespace(SAVE=1)))
    bridge=DesktopBridge(store);bridge._window=Mock();bridge._window.create_file_dialog.return_value=[str(target)]
    result=bridge.save_export(p.id,'system-one')
    assert result.get('saved'),result
    assert json.loads(target.read_text())['evaluation_design']


def test_recorded_feedback_never_accepts_forged_feature_scores(client,app):
    p=make(app)
    r=client.post('/api/projects/'+p.id+'/system-one/feedback',json={'version':p.version,'angle_id':'a','label':1,'features':{'craft':1}})
    assert r.status_code in (400,422)
