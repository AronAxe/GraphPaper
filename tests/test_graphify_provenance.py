from graphpaper.models import Project,Source,Node,Edge,Graph
from graphpaper.graph import mine_motifs
from graphpaper.pipeline import make_angles,Job
from .conftest import ScriptedClients


def test_external_file_provenance_reaches_angle_evaluation_without_becoming_proof():
    p=Project(sources=[Source(id='S1',title='Synthetic source',text='Eva maintains the Observatory. This is a synthetic fixture.')])
    p.graph=Graph(nodes=[Node(id='eva',label='Eva',status='imported',source_ids=['S1']),Node(id='site',label='Observatory',status='imported',source_ids=['S1'])],
        edges=[Edge(source='eva',target='site',relation='maintains',status='imported',source_ids=['S1'])],coverage={'engine':'external_graphify'})
    motifs=mine_motifs(p)
    assert motifs[0]['source_ids']==['S1']
    clients=ScriptedClients()
    make_angles(p,clients,Job(p.id,'angles'))
    decisions=[call for call in clients.calls if call[0]=='decide' and 'candidates' in call[1]]
    assert decisions
    excerpt=decisions[0][1]['candidates'][0]['source_context'][0]
    assert excerpt['source_id']=='S1' and 'Eva maintains' in excerpt['text']
    assert 'not proof' in excerpt['scope']
    assert p.angles[0].source_ids==['S1']
    assert p.graph.nodes[0].status=='imported' and not p.graph.nodes[0].evidence


def test_unavailable_and_voice_sources_do_not_become_angle_support():
    p=Project(sources=[Source(id='S1',title='Voice',text='Style only',role='voice')])
    p.graph=Graph(nodes=[Node(id='a',label='A',source_ids=['S1','S99']),Node(id='b',label='B')],edges=[Edge(source='a',target='b')])
    assert all(not c['source_ids'] for c in mine_motifs(p))
