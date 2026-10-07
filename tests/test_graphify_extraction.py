"""Exercise the public Graphify CLI using synthetic text/provider fixtures."""
import threading
import time
import pytest
from graphpaper.models import Graph,Node,Project,Settings
from graphpaper.graphify_worker import probe
from .graphify_fixtures import FixtureClients,fixture_settings,add_sources


def wait_for_job(client,jid,seconds=50):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        result=client.get('/api/jobs/'+jid).json()
        if result['state'] not in {'queued','running'}:return result
        time.sleep(.1)
    raise AssertionError('The isolated extraction did not finish')


def prepare(client,app,cls=FixtureClients):
    if not probe()['available']:pytest.skip('Optional Graphify runtime not installed')
    cls.seen=[];cls.entered=threading.Event()
    app.state.runner.clients_factory=cls
    app.state.store.set_settings(fixture_settings().model_dump())
    project=client.post('/api/projects',json={'title':'Synthetic Graphify test'}).json()
    add_sources(client,project['id'])
    return project['id']


def test_public_graphify_action(client,app):
    pid=prepare(client,app)
    settings=app.state.store.settings()
    job=client.post('/api/projects/'+pid+'/jobs',json={'action':'graph'}).json()
    result=wait_for_job(client,job['id'])
    assert result['state']=='completed',result
    p=client.get('/api/projects/'+pid).json()
    assert p['graph']['coverage']['engine']=='external_graphify'
    assert p['graph']['coverage']['sources']==2
    assert p['graph']['nodes'] and p['graph']['edges']
    assert p['usage']['calls']==p['graph']['coverage']['model_requests']==len(FixtureClients.seen)
    assert all('voice sample' not in x['user'].lower() for x in FixtureClients.seen)
    assert all(x['model']=='extract-fixture' and x['effort']=='high' for x in FixtureClients.seen)
    assert any(n['source_ids'] for n in p['graph']['nodes'])
    assert all(n['status']=='imported' for n in p['graph']['nodes'])
    assert app.state.store.settings()==settings


@pytest.mark.parametrize('behavior',['malformed','error'])
def test_failed_extraction_keeps_prior_project(client,app,behavior):
    class Failed(FixtureClients):pass
    Failed.behavior=behavior
    pid=prepare(client,app,Failed)
    p=app.state.store.get(pid)
    p.graph=Graph(nodes=[Node(id='prior',label='Prior graph')])
    app.state.store.save(p,p.version)
    before=app.state.store.get(pid);settings=app.state.store.settings()
    job=client.post('/api/projects/'+pid+'/jobs',json={'action':'graph'}).json()
    result=wait_for_job(client,job['id'])
    assert result['state']=='failed',result
    after=app.state.store.get(pid)
    assert after.graph==before.graph and after.sources==before.sources
    assert after.draft==before.draft and app.state.store.settings()==settings


def test_previous_release_data_has_compatible_defaults():
    p=Project.model_validate({'id':'old','title':'Existing project','graph':{'nodes':[{'id':'n','label':'Existing'}]}})
    assert p.graph.nodes[0].source_ids==[]
    settings=Settings.model_validate({'provider':'codex','extraction_reasoning_effort':'high'})
    assert settings.graphify_timeout_seconds==1200


def test_cancel_running_graphify_job(client,app,monkeypatch):
    import graphpaper.graphify_adapter as adapter
    original_owner=adapter.OwnedProcess
    owners=[]
    class ObservedOwner(original_owner):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);owners.append(self)
    monkeypatch.setattr(adapter,'OwnedProcess',ObservedOwner)
    class Slow(FixtureClients):behavior='slow'
    pid=prepare(client,app,Slow)
    before=app.state.store.get(pid)
    job=client.post('/api/projects/'+pid+'/jobs',json={'action':'graph'}).json()
    # Wait for actual inference readiness, not a fixed cold-start assumption.
    # Fail immediately with the backend error if startup fails.
    ready_deadline=time.monotonic()+60
    while not Slow.entered.wait(.1):
        startup=client.get('/api/jobs/'+job['id']).json()
        assert startup['state'] in {'queued','running'},startup
        assert time.monotonic()<ready_deadline, startup

    response=client.post('/api/jobs/'+job['id']+'/cancel')
    assert response.status_code==200
    result=wait_for_job(client,job['id'],15)
    assert result['state']=='cancelled',result
    assert owners and all(owner.proc.poll() is not None for owner in owners)
    after=app.state.store.get(pid)
    assert after.graph==before.graph and after.sources==before.sources


def test_total_extraction_timeout_is_effective(client,app,monkeypatch):
    import graphpaper.graphify_adapter as adapter
    original_scope=adapter.JobScope
    monkeypatch.setattr(adapter,'JobScope',lambda parent,seconds:original_scope(parent,.3))
    pid=prepare(client,app)
    job=client.post('/api/projects/'+pid+'/jobs',json={'action':'graph'}).json()
    result=wait_for_job(client,job['id'],15)
    assert result['state']=='failed' and 'timeout' in result['error'].lower(),result
    assert app.state.store.get(pid).graph.nodes==[]


def test_missing_backend_does_not_change_the_existing_graph(client,app,tmp_path):
    pid=prepare(client,app)
    settings=fixture_settings().model_copy(update={'graphify_executable':str(tmp_path/'not-installed.exe')})
    app.state.store.set_settings(settings.model_dump())
    p=app.state.store.get(pid);p.graph=Graph(nodes=[Node(id='prior',label='Prior graph')]);app.state.store.save(p,p.version)
    before=app.state.store.get(pid)
    job=client.post('/api/projects/'+pid+'/jobs',json={'action':'graph'}).json()
    result=wait_for_job(client,job['id'],15)
    assert result['state']=='failed'
    assert app.state.store.get(pid).graph==before.graph
    assert app.state.store.settings()==settings.model_dump()


def test_public_console_entry_point_as_custom_runtime(client,app):
    from pathlib import Path
    import os,sys,sysconfig
    pid=prepare(client,app)
    executable=Path(sysconfig.get_path('scripts'))/('graphify.exe' if os.name=='nt' else 'graphify')
    assert executable.is_file()
    settings=fixture_settings().model_copy(update={'graphify_executable':str(executable)})
    app.state.store.set_settings(settings.model_dump())
    job=client.post('/api/projects/'+pid+'/jobs',json={'action':'graph'}).json()
    result=wait_for_job(client,job['id'])
    assert result['state']=='completed',result
    p=client.get('/api/projects/'+pid).json()
    assert p['graph']['coverage']['runtime_selection']=='custom'
    assert p['graph']['nodes'] and p['graph']['coverage']['model_requests']>0
