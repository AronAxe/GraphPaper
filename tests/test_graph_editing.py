"""Graph edits are explicit, versioned and isolated from the writing pipeline."""
import importlib.util
import json
from fastapi.testclient import TestClient
from graphpaper.server import create_app


def client_for(tmp_path):
    app=create_app(tmp_path)
    client=TestClient(app)
    client.get('/')
    client.headers['X-GraphPaper']='1'
    return app,client


def test_graph_editor_exists():
    assert importlib.util.find_spec('graphpaper.graph_editor') is not None, 'Persistent click-to-edit graph endpoints are missing'


def test_edit_and_undo_preserve_manuscript_sources_and_voice(tmp_path):
    app,c=client_for(tmp_path)
    p=c.post('/api/demo',json={'mode':'nonfiction'}).json()
    original=json.loads(json.dumps(p))
    n=p['graph']['nodes'][0]
    r=c.post(f"/api/projects/{p['id']}/graph/edit",json={'version':p['version'],'operation':'node.update','id':n['id'],'values':{'label':'An uncompromising argument','description':'Keep the fucking bite.'}})
    assert r.status_code==200,r.text
    q=r.json()
    assert q['graph']['nodes'][0]['label']=='An uncompromising argument'
    assert q['graph']['nodes'][0]['status']=='proposed'
    for key in ['draft','sources','angles','outline','voice_profile','usage']:
        assert q[key]==original[key]
    assert q['graph']['nodes'][0]['evidence']==n['evidence']
    undo=c.post(f"/api/projects/{p['id']}/graph/undo",json={'version':q['version']})
    assert undo.status_code==200,undo.text
    assert undo.json()['graph']==original['graph']
    assert undo.json()['draft']==original['draft']


def test_graph_edits_conflict_and_validate(tmp_path):
    app,c=client_for(tmp_path)
    p=c.post('/api/demo',json={}).json();pid=p['id'];n=p['graph']['nodes'][0]
    base={'version':p['version'],'operation':'node.update','id':n['id']}
    for values in [{'label':''},{'label':'x'*201},{'evidence':[]},{'status':'sourced'},{'kind':'x'*81}]:
        r=c.post(f'/api/projects/{pid}/graph/edit',json={**base,'values':values})
        assert r.status_code==400,(values,r.text)
    r=c.post(f'/api/projects/{pid}/graph/edit',json={**base,'version':-1,'values':{'label':'stale'}})
    assert r.status_code==409
    assert c.get(f'/api/projects/{pid}').json()['graph']==p['graph']


def test_create_connect_delete_and_restart_undo(tmp_path):
    app,c=client_for(tmp_path)
    p=c.post('/api/projects',json={'title':'Editing fixture'}).json();pid=p['id']
    def edit(op,**data):
        nonlocal p
        r=c.post(f'/api/projects/{pid}/graph/edit',json={'operation':op,'version':p['version'],**data})
        assert r.status_code==200,r.text
        p=r.json();return p
    edit('node.add',values={'label':'Source premise','kind':'concept'});a=p['graph']['nodes'][0]['id']
    edit('node.add',values={'label':'Conclusion','kind':'claim'});b=p['graph']['nodes'][1]['id']
    edit('edge.add',values={'source':a,'target':b,'relation':'supports','description':'My proposed connection'})
    e=p['graph']['edges'][0]['id']
    edit('edge.update',id=e,values={'relation':'contradicts'})
    assert p['graph']['edges'][0]['relation']=='contradicts'
    before=p['graph'];edit('node.delete',id=a)
    assert not p['graph']['edges']
    other_app,other=client_for(tmp_path)
    r=other.post(f'/api/projects/{pid}/graph/undo',json={'version':p['version']})
    assert r.status_code==200,r.text
    assert r.json()['graph']==before


def test_invalid_target_and_missing_id_do_not_write(tmp_path):
    app,c=client_for(tmp_path)
    p=c.post('/api/demo',json={}).json();pid=p['id']
    for operation,data in [('edge.add',{'values':{'source':p['graph']['nodes'][0]['id'],'target':'missing','relation':'supports'}}),('node.update',{'id':'missing','values':{'label':'bad'}}),('invented',{}),([],{}),({}, {})]:
        r=c.post(f'/api/projects/{pid}/graph/edit',json={'version':p['version'],'operation':operation,**data})
        assert r.status_code in (400,404),r.text
    assert c.get(f'/api/projects/{pid}').json()['version']==p['version']


def test_active_job_blocks_graph_edit(tmp_path):
    app,c=client_for(tmp_path)
    p=c.post('/api/demo',json={}).json()
    app.state.runner.active=lambda _:True
    r=c.post(f"/api/projects/{p['id']}/graph/edit",json={'version':p['version'],'operation':'node.delete','id':p['graph']['nodes'][0]['id']})
    assert r.status_code==400


def test_undo_refuses_intervening_graph_rebuild(tmp_path):
    app,c=client_for(tmp_path)
    p=c.post('/api/demo',json={}).json();pid=p['id']
    p=c.post(f'/api/projects/{pid}/graph/edit',json={'version':p['version'],'operation':'node.update','id':p['graph']['nodes'][0]['id'],'values':{'label':'changed'}}).json()
    p=c.post(f'/api/projects/{pid}/graph/import',json={'nodes':[{'id':'other','label':'Rebuilt'}],'edges':[]}).json()
    r=c.post(f'/api/projects/{pid}/graph/undo',json={'version':p['version']})
    assert r.status_code==409
    assert c.get(f'/api/projects/{pid}').json()['graph']==p['graph']
