from __future__ import annotations
import pytest
from graphpaper.models import Project, Source, Settings
from graphpaper.pipeline import Job, build_graph, make_angles, make_outline, write_draft, revise, review_draft
from graphpaper.storage import Store
from graphpaper.demo import make_demo
from graphpaper.ingest import digest
from .conftest import ScriptedClients


@pytest.mark.parametrize('mode',['nonfiction','fiction'])
def test_full_pipeline_both_modes(tmp_path,mode):
    p=Project(mode=mode,title='Integration test')
    p.brief.direction='A choice in a shared place.'
    if mode=='nonfiction':p.sources=[Source(id='S1',title='Source',text='People make choices about shared space.',digest=digest('People make choices about shared space.'))]
    store=Store(tmp_path);store.create(p);job=Job(p.id,'test');c=ScriptedClients(job=job)
    build_graph(p,c,store,job)
    assert len(p.graph.nodes)==3
    assert p.graph.coverage['processed_chunks']==p.graph.coverage['chunks']
    make_angles(p,c,job)
    assert p.angles and not p.selected_angle
    assert 0<=p.angles[0].score<=100
    p.selected_angle=p.angles[0].id
    make_outline(p,c,job)
    assert sum(s.target_words for s in p.outline)==p.brief.target_words
    write_draft(p,c,store,job)
    assert p.draft.startswith('# A test direction') and p.review.summary
    assert len(store.revisions(p.id))>=3
    if mode=='fiction':
        assert p.story_state['characters'][0]['name']=='Mira'
        assert '[S1]' not in p.draft
    else:assert '[S1]' in p.draft
    original=p.draft;revise(p,c,job,store,instruction='Improve the ending.')
    assert p.draft!=original
    assert any('revision candidate' in r['label'] for r in store.revisions(p.id))


def test_cached_extraction_reuses_exact_source_no_calls(tmp_path):
    p=make_demo();p.graph.nodes=[];store=Store(tmp_path);store.create(p);job=Job(p.id,'graph');c=ScriptedClients(job=job)
    build_graph(p,c,store,job);calls=job.usage['calls']
    build_graph(p,c,store,job)
    assert job.usage['calls']==calls


def test_no_jev_still_works_without_fake_probabilities(tmp_path):
    p=make_demo();c=ScriptedClients(Settings(model='test',jev_provider='off'));job=Job(p.id,'angles')
    make_angles(p,c,job)
    assert all(a.score is None and not a.scores for a in p.angles)


def test_stale_graph_blocked_until_rebuild():
    p=make_demo();p.graph.warnings.append('Sources changed after the last graph build. Rebuild before relying on coverage.')
    with pytest.raises(ValueError,match='Rebuild'):make_angles(p,ScriptedClients(),Job(p.id,'angles'))


def test_automatic_revision_keeps_original_without_jev(tmp_path):
    p=make_demo();original=p.draft;store=Store(tmp_path);store.create(p)
    c=ScriptedClients(Settings(model='test',jev_provider='off'));j=Job(p.id,'revise')
    revise(p,c,j,store,automatic=True)
    assert p.draft==original
    assert any(r['draft']!=original for r in store.revisions(p.id))


def test_automatic_revision_cannot_add_fabricated_reference(tmp_path):
    class BadRevision(ScriptedClients):
        def complete(self,system,user,**kwargs):
            text=super().complete(system,user,**kwargs)
            return text+' [S999]' if 'Revise this complete piece' in user else text
    p=make_demo();original=p.draft;store=Store(tmp_path);store.create(p)
    revise(p,BadRevision(),Job(p.id,'revise'),store,automatic=True)
    assert p.draft==original
