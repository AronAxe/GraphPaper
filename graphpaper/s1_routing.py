"""Routing only among author-approved models; no automatic billing/provider switch."""
from .system_one import Engine,noul,probability,YES


def select_model(p,clients,role,task):
    s=clients.settings
    model={'editor':s.editor_model,'extraction':s.extraction_model}.get(role) or s.model
    effort={'editor':s.editor_reasoning_effort,'extraction':s.extraction_reasoning_effort}.get(role,s.reasoning_effort)
    selected={'model':model,'effort':effort,'reason':'Author-selected default.'}
    if not s.system_one_routing or not (s.system_one_fast_model or s.system_one_deep_model):return selected
    qs={'simple':noul('Is this task a local transformation with explicit inputs and no synthesis or difficult reasoning?'),
        'difficult':noul('Does this task require reconciling evidence, preserving a complex argument or resolving a difficult global consistency issue?')}
    rows=Engine(clients,p).evaluate('approved model routing',[{'id':'task','role':role,'task':task}],qs,{'mode':p.mode})
    a=rows.get('task',{})
    if probability(a,'difficult',0)>=YES and s.system_one_deep_model:
        selected={'model':s.system_one_deep_model,'effort':s.system_one_deep_effort,'reason':'Complex task; using the author-approved deep model.'}
    elif probability(a,'simple',0)>=YES and probability(a,'difficult',1)<=1-YES and s.system_one_fast_model:
        selected={'model':s.system_one_fast_model,'effort':s.system_one_fast_effort,'reason':'Local task; using the author-approved fast model.'}
    p.system_one['last_routing']=selected
    return selected


def prepare_call(clients,system,user,role):
    import json
    p=getattr(clients,'system_one_project',None)
    if p is None or not getattr(clients.settings,'system_one_enabled',True):return system,user,None
    try:data=json.loads(user)
    except (ValueError,TypeError):return system,user,None
    if not isinstance(data,dict):return system,user,None
    task=str(data.get('task',''))[:1500]
    selected=select_model(p,clients,role,task)
    if role!='extraction' and p.voice_profile.library_id:
        from .s1_retrieval import task_voice
        voice=task_voice(p,clients,task)
        if voice:
            for key in ('author_voice','voice','voice_references'):
                if key in data:data[key]=voice
    from .s1_learning import guidance
    learned=guidance(p,getattr(clients,'system_one_store',None))
    if learned and clients.settings.system_one_learning:data['author_corrections']=learned
    return system,json.dumps(data,ensure_ascii=False),selected
