import importlib.util
from graphpaper.models import Project
from graphpaper.storage import Store


def api():
    assert importlib.util.find_spec('graphpaper.s1_learning'),'Persistent author feedback implementation is missing'
    from graphpaper import s1_learning
    return s1_learning


def test_corrections_reused_by_voice_but_not_unrelated_projects(tmp_path):
    m=api();store=Store(tmp_path);p=Project(mode='polemic');p.voice_profile.library_id='v_aaaaaaaaaaaa'
    m.add_feedback(store,p,'a',1,{},'Keep my categorical conclusion; do not insert a compromise.')
    q=Project(mode='polemic');q.voice_profile.library_id=p.voice_profile.library_id
    assert 'categorical' in str(m.guidance(q,store))
    assert not m.guidance(Project(mode='polemic'),store)


def test_no_fake_training_when_there_are_too_few_labels(tmp_path):
    m=api();p=Project();store=Store(tmp_path)
    report=m.train(store,p)
    assert report['status']=='insufficient_data' and report['active'] is False


def test_training_uses_project_heldout_and_records_baseline(tmp_path):
    m=api();store=Store(tmp_path)
    p=Project();p.voice_profile.library_id='v_aaaaaaaaaaaa'
    for group in range(8):
        p.id='p_'+f'{group:012x}'
        for j in range(12):
            label=j%2;features={'craft':float(label),'novelty':.5,'stance_fidelity':.95,'voice_fidelity':.9,'grounded':.9,'reasoning_preserved':.9}
            m.add_feedback(store,p,f'g{group}a{j}',label,features)
    result=m.train(store,p)
    assert result['status'] in {'promoted','not_better_than_baseline'}
    assert not set(result['train_projects']) & set(result['holdout_projects'])
    assert result['holdout_count']>0 and 'baseline_brier' in result
    assert result['validation']=='held-out projects, not random rows'


def test_preference_adjustment_cannot_promote_an_intent_failure(tmp_path):
    m=api();store=Store(tmp_path);p=Project()
    a={'eligible':False,'craft':1}
    assert m.adjustment(p,store,a)==0


def test_feedback_upsert_prevents_repeated_clicks_becoming_extra_labels(tmp_path):
    m=api();store=Store(tmp_path);p=Project()
    m.add_feedback(store,p,'same',1,{'craft':.8});m.add_feedback(store,p,'same',0,{'craft':.8})
    rows=m.history(store,p)
    assert len(rows)==1 and rows[0]['label']==0


def test_delete_feedback_invalidates_trained_preference(tmp_path):
    m=api();store=Store(tmp_path);p=Project()
    event=m.add_feedback(store,p,'a',1,{})
    m.remove_feedback(store,p,event['id'])
    assert m.history(store,p)==[]
