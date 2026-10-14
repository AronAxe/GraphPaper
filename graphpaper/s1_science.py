"""System One research triage supplements, never falsifies, the research log."""
from .system_one import Engine,noul,choice,probability,choice_action,YES


def screen(p,clients):
    items=[{'id':r.id,'title':r.metadata.title,'abstract':r.abstract,'content_scope':r.metadata.content_scope} for r in p.research.records if r.decision=='unscreened'][:80]
    qs={'eligibility':choice('Against the explicit protocol, which screening recommendation is justified?',{
        'include':'Accessible information meets the stated inclusion criteria.','exclude':'Accessible information explicitly meets an exclusion criterion.','uncertain':'The accessible record does not settle eligibility.'}),
        'fulltext_needed':noul('Would reading the full text resolve a specific uncertainty about eligibility or the reported method?')}
    rows=Engine(clients,p).evaluate('science screening',items,qs,{'protocol':p.research.plan.model_dump()})
    p.system_one['screening']={ident:{'action':choice_action(a.get('eligibility'),'uncertain'),'answers':a,'applied':False} for ident,a in rows.items()}
    return rows


def prioritize_fulltexts(p,clients,records):
    qs={'needed':noul('Is the missing full text needed to evaluate a specific load-bearing methodological or evidential issue in this research question?'),
        'uncertainty':noul('Is there a material uncertainty that the accessible abstract alone cannot settle?')}
    rows=Engine(clients,p).evaluate('full text priority',[{'id':r.id,'title':r.metadata.title,'abstract':r.abstract,'appraisal':r.appraisal} for r in records[:80]],qs,
        {'question':p.research.plan.question,'protocol':p.research.plan.model_dump()})
    p.system_one['fulltext_priorities']={ident: {'priority':.6*probability(a,'needed')+.4*probability(a,'uncertainty'),'answers':a} for ident,a in rows.items()}
    return sorted(records,key=lambda r:p.system_one['fulltext_priorities'].get(r.id,{}).get('priority',.5),reverse=True)


def check_appraisals(p,clients):
    items=[]
    for r in p.research.records:
        if r.decision!='include' or not r.appraisal:continue
        items.append({'id':r.id,'title':r.metadata.title,'appraisal':r.appraisal,'scope':r.metadata.content_scope})
    qs={'missing_method':noul('Does the appraisal omit or mark unavailable a methodological detail needed for the research question?'),
        'overclaim':noul('Does the appraisal claim access or methodological certainty beyond its declared text scope?')}
    rows=Engine(clients,p).evaluate('appraisal gaps',items[:80],qs,{'question':p.research.plan.question})
    p.system_one['appraisal_gaps']={ident:{'answers':a,'needs_attention':probability(a,'missing_method',0)>=YES or probability(a,'overclaim',0)>=YES} for ident,a in rows.items()}
    return rows


def scene_check(p,clients,scene,previous_ledger,previous_scene=''):
    qs={'canon_conflict':noul('Does the new scene contradict an explicit established canon fact, rather than introduce a plausible new development?'),
        'knowledge_conflict':noul('Does a character act on knowledge the supplied ledger explicitly says they do not have?'),
        'motivation_conflict':noul('Does a major action contradict established motivation without a depicted reason or change?'),
        'repetitive':noul('Does this scene repeat the same dramatic beat as the preceding scene without advancing it?')}
    rows=Engine(clients,p).evaluate('fiction continuity',[{'id':'scene','new_scene':scene,'prior_scene':previous_scene,'ledger':previous_ledger,'canon':p.brief.canon}],qs,
        {'purpose':'Respect the author’s intended story, voice and moral ambiguity.'})
    a=rows.get('scene',{})
    problems=[k for k in qs if probability(a,k,0)>=YES]
    p.system_one.setdefault('continuity',[]).append({'scene_hash':__import__('hashlib').sha256(scene.encode()).hexdigest(),'answers':a,'problems':problems})
    p.system_one['continuity']=p.system_one['continuity'][-40:]
    if problems:return problems
    # A missing or uncertain check is not evidence that a repair succeeded.
    return [] if len(a)==len(qs) and all(probability(a,k)<=1-YES for k in qs) else None
