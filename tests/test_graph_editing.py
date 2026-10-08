"""Real API edits; no inference, no installed user projects."""
import copy
import pytest
from graphpaper.models import Project, Graph, Node, Edge, Source, Evidence, Angle


def seeded(app):
    p=Project(title='Graph editing fixture',sources=[Source(id='S1',title='Source',text='Original quotation.')],
        graph=Graph(nodes=[Node(id='n1',label='First',status='sourced',evidence=[Evidence(source_id='S1',quote='Original quotation.',verified=True)],source_ids=['S1']),Node(id='n2',label='Second')],edges=[Edge(id='e1',source='n1',target='n2',relation='supports')],engine='Graphify'),draft='Keep my fucking argument.',angles=[Angle(title='Kept angle',thesis='My argument.')])
    p.voice_profile.instructions='Power language stays.'
    app.state.store.create(p)
    return p


def edit(client,p,op,id=None,**values):
    return client.post(f'/api/projects/{p.id}/graph/edit',json={'version':p.version,'operation':op,'id':id,'values':values})


def test_edit_node_keeps_manuscript_voice_evidence_and_marks_angles_stale(client,app):
    p=seeded(app)
    response=edit(client,p,'node','n1',label='An uncompromising claim',kind='claim',description='Not a polite question.')
    assert response.status_code==200,response.text
    saved=response.json()['project'];node=saved['graph']['nodes'][0]
    assert node['label']=='An uncompromising claim' and node['status']=='proposed'
    assert node['evidence']==p.graph.nodes[0].model_dump()['evidence']
    assert saved['sources']==p.model_dump()['sources'] and saved['draft']==p.draft
    assert saved['voice_profile']==p.voice_profile.model_dump() and len(saved['angles'])==1
    assert saved['angles_context_hash']=='' and saved['usage']['calls']==0


def test_node_and_connection_creation_and_reloading(client,app):
    p=seeded(app)
    response=edit(client,p,'node',label='New idea',kind='theme',description='New thought')
    assert response.status_code==200,response.text
    value=response.json();p=Project.model_validate(value['project']);nid=value['selected_id']
    response=edit(client,p,'edge',source=nid,target='n1',relation='contradicts',description='Explains the disagreement.')
    assert response.status_code==200,response.text
    value=response.json();p=Project.model_validate(value['project'])
    assert len(p.graph.nodes)==3 and len(p.graph.edges)==2
    assert client.get(f'/api/projects/{p.id}').json()['graph']==p.graph.model_dump()


def test_deleting_node_removes_only_incident_edges_and_undo_restores_it(client,app):
    p=seeded(app);p.brief.pinned_nodes=['n1'];app.state.store.save(p,p.version)
    before=p.graph.model_dump()
    result=edit(client,p,'delete-node','n1');assert result.status_code==200,result.text
    value=result.json();saved=value['project']
    assert len(saved['graph']['nodes'])==1 and saved['graph']['edges']==[]
    assert saved['brief']['pinned_nodes']==[]
    result=client.post(f'/api/projects/{p.id}/graph/undo',json={'version':saved['version']})
    assert result.status_code==200,result.text
    restored=result.json()['project']
    assert restored['graph']==before and restored['brief']['pinned_nodes']==['n1']
    assert restored['draft']==p.draft


@pytest.mark.parametrize('values',[{'label':''},{'label':'x'*201},{'status':'sourced'},{'source_ids':['S99']},{'kind':'x'*81}])
def test_invalid_or_provenance_spoofing_edits_are_atomic(client,app,values):
    p=seeded(app);before=p.model_dump()
    result=edit(client,p,'node','n1',**values)
    assert result.status_code==400,result.text
    assert app.state.store.get(p.id).model_dump()==before


def test_invalid_edge_target_and_stale_edit_do_not_overwrite(client,app):
    p=seeded(app)
    assert edit(client,p,'edge','e1',target='absent').status_code==400
    assert edit(client,p,'edge','e1',relation='questions').status_code==200
    assert edit(client,p,'node','n1',label='Stale').status_code==409
    assert app.state.store.get(p.id).graph.nodes[0].label=='First'


def test_edit_is_blocked_while_extraction_runs(client,app,monkeypatch):
    p=seeded(app);monkeypatch.setattr(app.state.runner,'active',lambda pid:True)
    assert edit(client,p,'node','n1',label='Do not apply').status_code==400
    assert app.state.store.get(p.id).version==p.version


def test_undo_never_overwrites_a_subsequent_graph_rebuild(client,app):
    p=seeded(app);result=edit(client,p,'node','n1',label='Edited').json()
    p=Project.model_validate(result['project']);p.graph=Graph(nodes=[Node(id='new',label='Fresh extraction')]);app.state.store.save(p,p.version)
    response=client.post(f'/api/projects/{p.id}/graph/undo',json={'version':p.version})
    assert response.status_code==409
    assert app.state.store.get(p.id).graph.nodes[0].id=='new'


def test_undo_keeps_pin_choices_made_after_the_graph_edit(client,app):
    p=seeded(app);p.brief.pinned_nodes=['n1'];app.state.store.save(p,p.version)
    value=edit(client,p,'node','n1',label='Edited').json()
    p=Project.model_validate(value['project']);p.brief.pinned_nodes=['n2'];app.state.store.save(p,p.version)
    response=client.post(f'/api/projects/{p.id}/graph/undo',json={'version':p.version})
    assert response.status_code==200,response.text
    assert response.json()['project']['brief']['pinned_nodes']==['n2']
