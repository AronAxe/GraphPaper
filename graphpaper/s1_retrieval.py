"""Cheap lexical/graph nomination followed by focused semantic selection."""
from __future__ import annotations
import json
from .system_one import Engine,noul,score,normalized,probability,fingerprint
from .editorial import context


def rerank_pack(p,clients,pack,query,budget=38000,required_ids=None):
    if not getattr(clients.settings,'system_one_retrieval',True) or not Engine(clients).enabled:return pack
    passages=pack.get('passages',[])
    items=[{'id':'passage_'+str(i),**item} for i,item in enumerate(passages[:18])]
    questions={'relevance':noul('Does this passage help answer the exact query, rather than merely share its vocabulary?'),
        'direct_support':noul('Does this passage directly substantiate a material step of the requested argument or canon question?'),
        'contradiction':noul('Does this passage supply concrete contrary evidence that materially changes an asserted factual premise?'),
        'example':noul('Does this passage provide a useful specific example or explicit analogy for the requested piece?')}
    rows=Engine(clients,p).evaluate('passage selection',items,questions,{'query':query,**context(p,compact=True)})
    if not rows:return pack
    def rank(item):
        a=rows.get(item['id'],{})
        return (.5*probability(a,'relevance')+.3*probability(a,'direct_support')+.15*probability(a,'example')+.05*probability(a,'contradiction'))
    ordered=sorted(items,key=rank,reverse=True)
    # Required-source coverage is deliberate, not permission to overwhelm the budget.
    mandatory=[];seen=set();required=set(required_ids or [])
    for item in ordered:
        if item['source_id'] in required and item['source_id'] not in seen:
            mandatory.append(item);seen.add(item['source_id'])
    sequence=mandatory+[i for i in ordered if i not in mandatory]
    chosen=[];size=0
    for item in sequence:
        row={k:v for k,v in item.items() if k!='id'}
        n=len(json.dumps(row,ensure_ascii=False))
        if size+n<=budget:
            chosen.append(row);size+=n
    return {**pack,'passages':chosen,'retrieved_passages':len(chosen),'selection':'System One semantic reranking',
        'semantic_candidates':len(items),'required_sources_missing':sorted(required-{x['source_id'] for x in chosen}),
        'note':'Semantically ranked whole excerpts, not the whole corpus. Missing coverage is explicit; relevance is not proof.'}


def task_voice(p,clients,task,budget=6500):
    from .style_graph import for_profile,view
    profile=p.voice_profile
    if not profile.enabled or not profile.strength or not profile.library_id:return None
    graph=for_profile(profile)
    items=[{'id':n.id,'habit':n.instruction,'targets':n.targets,'kind':n.kind} for n in graph.nodes if n.kind!='voice']
    rows=Engine(clients,p).evaluate('voice habits for '+task,items,{'relevant':noul('Is this writing habit relevant to the current rhetorical task? Current author instructions override stored preferences; never reject a habit merely for strong language.')},
        {'task':task,'mode':p.mode,'current_instruction':p.brief.direction,'thesis':p.brief.thesis,'force':p.brief.rhetorical_force})
    if not rows:return {'enabled':True,'name':profile.name,'influence_percent':profile.strength,'graph':view(graph,budget),'rule':'Current instructions override these flexible style habits.'}
    weighted=graph.model_copy(deep=True)
    for n in weighted.nodes:
        if n.id in rows:n.weight=(n.weight*.35+probability(rows[n.id],'relevant')*.65)
    result=view(weighted,budget)
    return {'enabled':True,'name':profile.name,'influence_percent':profile.strength,'graph':result,
            'rule':'Task-selected flexible habits, not a word filter. Current author instructions override every saved preference.','selection':'System One task relevance'}
