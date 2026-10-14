"""Explicit local author feedback and a small held-out preference ranker.

This learns taste from labeled JEV features, not truth or a censorship policy.
No dependency on a training service; no private text is sent anywhere by fitting.
"""
from __future__ import annotations
import json
import math
from .models import now
from .system_one import POLICY_VERSION,fingerprint,number

FEATURES=('craft','novelty','stance_fidelity','reasoning_preserved','voice_fidelity','grounded')
MIN_LABELS=40


def scope(p):
    return ('voice:'+p.voice_profile.library_id if p.voice_profile.library_id else 'project:'+p.id)+':'+p.mode


def initialize(store):
    with store.connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS s1_feedback(
            id TEXT PRIMARY KEY, scope TEXT NOT NULL, project_id TEXT NOT NULL,
            candidate_id TEXT NOT NULL, label INTEGER NOT NULL, features TEXT NOT NULL,
            correction TEXT NOT NULL, created TEXT NOT NULL, schema TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS s1_feedback_scope ON s1_feedback(scope,created);
            CREATE TABLE IF NOT EXISTS s1_rankers(scope TEXT PRIMARY KEY,data TEXT NOT NULL);
        ''')


def add_feedback(store,p,candidate_id,label,features,correction=''):
    if type(label) is not int or label not in (0,1):raise ValueError('Feedback is an explicit prefer/reject label.')
    if not isinstance(candidate_id,str) or not candidate_id or len(candidate_id)>200:raise ValueError('Invalid candidate ID.')
    correction=str(correction).strip()
    if len(correction)>2000:raise ValueError('Keep each reusable correction below 2,000 characters.')
    safe={k:float(v) for k,v in features.items() if k in FEATURES and number(v)}
    initialize(store);ident=fingerprint([scope(p),p.id,candidate_id])[:24]
    event={'id':ident,'scope':scope(p),'project_id':p.id,'candidate_id':candidate_id,'label':label,'features':safe,'correction':correction,'created':now(),'schema':POLICY_VERSION}
    with store.connect() as c:
        c.execute('DELETE FROM s1_rankers WHERE scope=?',(scope(p),))
        c.execute('INSERT OR REPLACE INTO s1_feedback VALUES(?,?,?,?,?,?,?,?,?)',(ident,scope(p),p.id,candidate_id,label,json.dumps(safe),correction,event['created'],POLICY_VERSION))
    return event


def history(store,p):
    if store is None:return []
    initialize(store)
    with store.connect() as c:rows=c.execute('SELECT * FROM s1_feedback WHERE scope=? ORDER BY created DESC LIMIT 2000',(scope(p),)).fetchall()
    return [{**dict(r),'features':json.loads(r['features'])} for r in rows]


def guidance(p,store):
    corrections=[r['correction'] for r in history(store,p) if r['correction']][:5]
    if not corrections:return None
    return {'corrections':list(dict.fromkeys(corrections)),'precedence':'Author-supplied reusable preferences. The current project instruction wins over older corrections. These are not empirical evidence or a vocabulary filter.'}


def remove_feedback(store,p,ident):
    initialize(store)
    with store.connect() as c:
        result=c.execute('DELETE FROM s1_feedback WHERE scope=? AND id=?',(scope(p),ident))
        if not result.rowcount:raise KeyError('Feedback not found in this voice/project scope.')
        c.execute('DELETE FROM s1_rankers WHERE scope=?',(scope(p),))


def reset_model(store,p):
    initialize(store)
    with store.connect() as c:c.execute('DELETE FROM s1_rankers WHERE scope=?',(scope(p),))


def vector(features):return [features.get(k,.5) for k in FEATURES]


def sigmoid(z):return 1/(1+math.exp(-max(-30,min(30,z))))


def fit(rows):
    weights=[0.]*len(FEATURES);bias=0.
    # Fixed deterministic L2 logistic regression; no random data leakage.
    for _ in range(500):
        grad=[0.]*len(weights);gb=0.
        for r in rows:
            x=vector(r['features']);err=sigmoid(sum(w*v for w,v in zip(weights,x))+bias)-r['label']
            gb+=err
            for i,v in enumerate(x):grad[i]+=err*v
        for i in range(len(weights)):weights[i]-=.35*(grad[i]/len(rows)+.005*weights[i])
        bias-=.35*gb/len(rows)
    return weights,bias


def baseline(features):
    return .6*features.get('craft',.5)+.4*features.get('novelty',.5)


def train(store,p):
    rows=list(reversed([r for r in history(store,p) if r['schema']==POLICY_VERSION and len(r['features'])==len(FEATURES)]))
    projects=list(dict.fromkeys(r['project_id'] for r in rows))
    if len(rows)<MIN_LABELS or len(projects)<4 or len({r['label'] for r in rows})<2:
        return {'status':'insufficient_data','active':False,'labels':len(rows),'projects':len(projects),
            'required_labels':MIN_LABELS,'required_projects':4,'reason':'Use both prefer and reject feedback across at least four projects sharing this voice and mode.'}
    held=set(projects[-max(1,len(projects)//4):]);training=[r for r in rows if r['project_id'] not in held];holdout=[r for r in rows if r['project_id'] in held]
    if len({r['label'] for r in training})<2:
        return {'status':'insufficient_data','active':False,'reason':'Training projects need both preference labels.'}
    w,b=fit(training)
    brier=sum((sigmoid(sum(a*v for a,v in zip(w,vector(r['features'])))+b)-r['label'])**2 for r in holdout)/len(holdout)
    base=sum((baseline(r['features'])-r['label'])**2 for r in holdout)/len(holdout)
    promoted=brier+.01<base
    result={'status':'promoted' if promoted else 'not_better_than_baseline','active':promoted,'features':list(FEATURES),'weights':w,'bias':b,
        'schema':POLICY_VERSION,'trained_at':now(),'labels':len(rows),'train_projects':[g for g in projects if g not in held],
        'holdout_projects':list(held),'holdout_count':len(holdout),'brier':brier,'baseline_brier':base,
        'validation':'held-out projects, not random rows','use':'Bounded preference ranking only. Never overrides authorial/factual constraints.',
        'dataset_hash':fingerprint([(r['id'],r['label'],r['features']) for r in rows])}
    initialize(store)
    with store.connect() as c:c.execute('INSERT OR REPLACE INTO s1_rankers VALUES(?,?)',(scope(p),json.dumps(result)))
    return result


def model(store,p):
    if store is None:return {'active':False,'status':'not_trained'}
    initialize(store)
    with store.connect() as c:r=c.execute('SELECT data FROM s1_rankers WHERE scope=?',(scope(p),)).fetchone()
    return json.loads(r['data']) if r else {'active':False,'status':'not_trained'}


def adjustment(p,store,features):
    if features.get('eligible') is False:return 0.
    m=model(store,p)
    if not m.get('active') or m.get('schema')!=POLICY_VERSION:return 0.
    prediction=sigmoid(sum(w*v for w,v in zip(m['weights'],vector(features)))+m['bias'])
    return max(-.1,min(.1,.2*(prediction-.5)))


def evaluation_export(store,p):
    rows=history(store,p)
    return {'schema':POLICY_VERSION,'scope':scope(p),'created':now(),'feedback':rows,'preference_model':model(store,p),
        'decisions':p.system_one.get('decisions',[]),'evaluation_design':{'compare':['direct writing','graph without JEV','graph with System One'],
        'metrics':['author preference','intent fidelity','unsupported additions','editing minutes','elapsed time','provider cost'],
        'instruction':'Use the same sources, writing model, target and comparable budget. Separate holdout projects. Synthetic transport tests are not evidence of live editorial improvement.'}}
