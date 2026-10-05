from __future__ import annotations
import io
import json
import time
from graphpaper.models import Settings
from .conftest import ScriptedClients


def test_session_csrf_and_origin(app):
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        assert c.get('/api/bootstrap').status_code==403
        c.get('/');assert c.get('/api/bootstrap').status_code==403
        c.headers['X-GraphPaper']='1'
        assert c.get('/api/bootstrap').status_code==200
        assert c.get('/api/bootstrap',headers={'Origin':'https://evil.example'}).status_code==403
        assert c.get('/api/bootstrap',headers={'Host':'evil.example'}).status_code==403
        r=c.get('/');assert "frame-ancestors 'none'" in r.headers['content-security-policy']
        assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=strict' in r.headers['set-cookie']


def test_create_persist_patch_and_conflict(client):
    p=client.post('/api/projects',json={'title':'My essay','mode':'nonfiction'}).json();base='/api/projects/'+p['id']
    r=client.patch(base,json={'version':0,'draft':'First.'});assert r.status_code==200
    assert r.json()['version']==1
    assert client.patch(base,json={'version':0,'draft':'Overwritten'}).status_code==409
    assert client.get(base).json()['draft']=='First.'
    assert client.patch(base,json={'version':1,'usage':{'cost':99}}).status_code==400


def test_sources_ids_duplicates_roles_and_graph_stale(client):
    p=client.post('/api/demo',json={'mode':'nonfiction'}).json();base='/api/projects/'+p['id']
    r=client.post(base+'/sources/text',json={'title':'More','text':'Unique source with information.'})
    assert r.status_code==200
    assert r.json()['sources'][-1]['id']=='S4'
    assert any(w.startswith('Sources changed after') for w in r.json()['graph']['warnings'])
    assert client.post(base+'/sources/text',json={'title':'Duplicate','text':'Unique source with information.'}).status_code==400
    assert client.patch(base+'/sources/S4',json={'role':'voice'}).json()['sources'][-1]['role']=='voice'
    assert client.patch(base+'/sources/S4',json={'role':'dangerous-role'}).status_code==400
    assert client.patch(base+'/sources/absent',json={'enabled':False}).status_code==404


def test_upload_and_exports(client):
    p=client.post('/api/projects',json={'title':'Uploaded'}).json();base='/api/projects/'+p['id']
    assert client.post(base+'/sources/file',files={'file':('a.md',b'# Article\n\nA passage.','text/markdown')}).status_code==200
    assert client.post(base+'/sources/file',files={'file':('a.exe',b'not allowed')}).status_code==400
    p=client.get(base).json()
    p=client.patch(base,json={'version':p['version'],'draft':'# Title\n\nA passage. [S1]'}).json()
    for kind in ['md','html','docx','json','graph']:
        r=client.get(base+'/export/'+kind);assert r.status_code==200
        assert 'attachment;' in r.headers['content-disposition']
    assert client.get(base+'/export/exe').status_code==400


def test_restore_preserves_current_draft(client):
    p=client.post('/api/demo',json={'mode':'nonfiction'}).json();base='/api/projects/'+p['id'];original=p['draft']
    client.patch(base,json={'version':p['version'],'draft':'Manual rewrite.'})
    versions=client.get(base+'/revisions').json();assert versions
    r=client.post(base+'/revisions/'+versions[-1]['id']+'/restore').json()
    assert r['draft']==original
    assert any(v['draft']=='Manual rewrite.' for v in client.get(base+'/revisions').json())


def test_backup_import_revalidates_claimed_evidence(client):
    p=client.post('/api/demo',json={'mode':'nonfiction'}).json()
    p['graph']['nodes'][0]['evidence']=[{'source_id':'S1','quote':'This quote does not exist.','verified':True,'start':0,'end':26}]
    r=client.post('/api/import',json=p)
    assert r.status_code==200 and r.json()['id']!=p['id']
    assert not r.json()['graph']['nodes'][0]['evidence'][0]['verified']
    p['sources'].append(p['sources'][0]);assert client.post('/api/import',json=p).status_code==400


def test_settings_never_return_credentials(client,app):
    settings=Settings(model='some/model',remember_keys=False).model_dump()
    settings['api_keys']={'openrouter':'test-secret-123','typesafe':'test-typesafe'}
    r=client.put('/api/settings',json=settings)
    assert r.status_code==200 and 'test-secret' not in r.text and 'test-typesafe' not in r.text
    assert r.json()['keys']['openrouter']
    assert r.json()['effective_jev']=='openrouter'
    assert 'test-secret' not in json.dumps(app.state.store.settings())
    settings['api_keys']={'openrouter':''};r=client.put('/api/settings',json=settings)
    assert r.json()['effective_jev']=='typesafe'


def wait(client,jid):
    for _ in range(200):
        r=client.get('/api/jobs/'+jid).json()
        if r['state'] not in ['queued','running']:return r
        time.sleep(.02)
    raise AssertionError('Job failed to finish')


def test_async_pipeline_writes_actual_persisted_result(client,app):
    app.state.runner.clients_factory=ScriptedClients
    app.state.store.set_settings(Settings(model='test/model',allow_cloud=True,refine=False).model_dump())
    p=client.post('/api/demo',json={'mode':'nonfiction'}).json();base='/api/projects/'+p['id']
    r=client.post(base+'/jobs',json={'action':'draft'})
    assert r.status_code==200
    j=wait(client,r.json()['id']);assert j['state']=='completed',j['error']
    p=client.get(base).json()
    assert 'shared space' in p['draft'] and p['review']['summary']
    assert p['usage']['calls']>0
    assert p['activity'][-1]['state']=='completed'
    assert len(client.get(base+'/revisions').json())>=3


def test_failed_job_does_not_replace_work(client,app):
    p=client.post('/api/demo',json={'mode':'nonfiction'}).json();base='/api/projects/'+p['id']
    j=client.post(base+'/jobs',json={'action':'draft'}).json();j=wait(client,j['id'])
    assert j['state']=='failed'
    assert client.get(base).json()['draft']==p['draft']
    assert client.post(base+'/jobs',json={'action':'unknown'}).status_code==400
