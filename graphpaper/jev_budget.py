"""Automatic, exact-size JEV batching. No raw voice samples and no text clipping.

60 KB is this application's transport budget, not a claimed JEV model limit.
A decision that cannot be represented faithfully is left unscored; it cannot
abort completed writing or masquerade as a verified automatic revision gate.
"""
from __future__ import annotations
import copy
import json
import re
from dataclasses import dataclass

MAX_BYTES=60000
TARGET_BYTES=26000
MAX_QUESTIONS=100


def wire_bytes(payload):
    return len(json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8'))


def compact_state(state):
    if not isinstance(state,dict):return state
    result=copy.deepcopy(state)
    # Training prose does not belong in a decision request. Saved graph is the representation.
    for key in ('author_voice','voice','voice_references'):
        value=result.get(key)
        if isinstance(value,dict):
            graph=value.get('graph')
            if graph is None and value.get('instructions'):
                from .style_graph import text_graph,view
                graph=view(text_graph(value['instructions'],value.get('name','Voice')))
            result[key]={k:v for k,v in value.items() if k in {'enabled','name','influence_percent','rule','profile_needs_refresh'}}
            if graph:result[key]['graph']=graph
            result[key]['scope']='Compact voice graph; no training articles. Follow the current author instruction over a saved habit.'
    # Duplicate profile and contract text need not travel twice. These are same-state pointers.
    brief=result.get('brief');contract=result.get('editorial_contract')
    if isinstance(brief,dict) and isinstance(contract,dict):
        brief={k:v for k,v in brief.items() if k not in {'pinned_nodes','excluded_nodes'}}
        for key in ('direction','thesis'):
            if key in brief and brief[key]==contract.get(key):brief.pop(key)
        result['brief']=brief
        result['_brief_note']='Direction and thesis shared with editorial_contract; pin/exclusion choices are already reflected in candidate selection.'
    # The editor's claims are already reproduced in the deterministic citation audit.
    findings=result.get('editorial_findings')
    if isinstance(findings,dict) and isinstance(result.get('citation_audit'),dict):
        findings.pop('claims',None)
    return result


@dataclass
class Batch:
    state:dict|str
    questions:dict


class Unrepresentable(ValueError):pass


def plan(state,questions,model):
    if not questions:raise ValueError('JEV needs at least one typed question.')
    state=compact_state(state)
    groups=[]
    candidates=state.get('candidates') if isinstance(state,dict) else None
    if isinstance(candidates,list) and candidates:
        assigned=set()
        # Original keys and candidate IDs are retained; do not renumber c3 into c0.
        for index,candidate in enumerate(candidates):
            qs={k:q for k,q in questions.items() if re.match(r'^c'+str(index)+r'_',k)}
            if qs:
                groups.append(({**state,'candidates':[candidate]},qs));assigned.update(qs)
        remainder={k:q for k,q in questions.items() if k not in assigned}
        if remainder:groups.append((state,remainder))
    else:groups=[(state,questions)]
    output=[]
    for scoped,qs in groups:
        current={}
        threshold=MAX_BYTES if wire_bytes({'state':scoped})>TARGET_BYTES*0.75 else TARGET_BYTES
        for key,question in qs.items():
            proposed={**current,key:question}
            payload={'model':model,'state':scoped,'questions':proposed}
            size=wire_bytes(payload)
            if current and (size>threshold or len(proposed)>MAX_QUESTIONS):
                output.append(Batch(scoped,current));current={key:question}
            else:current=proposed
            if wire_bytes({'model':model,'state':scoped,'questions':current})>MAX_BYTES:
                # Last lossless reduction: intern repeated long strings as graph-style references.
                packed=intern(scoped)
                if wire_bytes({'model':model,'state':packed,'questions':current})>MAX_BYTES:
                    raise Unrepresentable('An indivisible decision exceeds the bounded JEV view. No prose, thesis or evidence was clipped.')
                scoped=packed
        if current:output.append(Batch(scoped,current))
    # Adjacent candidate groups share the same brief/voice. Pack them when the exact payload fits.
    combined=[]
    for b in output:
        if combined and isinstance(b.state,dict) and isinstance(combined[-1].state,dict):
            old=combined[-1];a=dict(old.state);c=dict(b.state)
            ac=a.pop('candidates',None);bc=c.pop('candidates',None)
            if ac is not None and bc is not None and a==c and not set(old.questions)&set(b.questions):
                nodes=ac+[v for v in bc if v not in ac]
                merged=Batch({**a,'candidates':nodes},{**old.questions,**b.questions})
                if len(merged.questions)<=MAX_QUESTIONS and wire_bytes({'model':model,'state':merged.state,'questions':merged.questions})<=TARGET_BYTES:
                    combined[-1]=merged;continue
        combined.append(b)
    assert all(wire_bytes({'model':model,'state':b.state,'questions':b.questions})<=MAX_BYTES for b in combined)
    assert set().union(*(set(b.questions) for b in combined))==set(questions)
    return combined


def intern(state):
    """Lossless repeated-text references, unlike destructive context truncation."""
    counts={}
    def count(value):
        if isinstance(value,str) and len(value)>240:counts[value]=counts.get(value,0)+1
        elif isinstance(value,dict):
            for v in value.values():count(v)
        elif isinstance(value,list):
            for v in value:count(v)
    count(state)
    symbols={text:'t'+str(i) for i,(text,n) in enumerate(counts.items()) if n>1}
    if not symbols:return state
    def walk(value):
        if isinstance(value,str) and value in symbols:return {'text_ref':symbols[value]}
        if isinstance(value,dict):return {k:walk(v) for k,v in value.items()}
        if isinstance(value,list):return [walk(v) for v in value]
        return value
    return {'state':walk(state),'texts':{ident:text for text,ident in symbols.items()},
        'encoding':'text_ref values point to verbatim strings in texts; nothing has been shortened.'}


def dispatch(clients,state,questions):
    from .providers import ProviderError
    route=clients.jev_route()
    if route=='off':return None
    bare=clients.settings.jev_model.removeprefix('~typesafe/').removeprefix('typesafe/')
    model=('~typesafe/jev-latest' if bare=='jev-latest' else 'typesafe/'+bare) if route=='openrouter' else bare
    url='https://openrouter.ai/api/alpha/decisions' if route=='openrouter' else 'https://api.typesafe.ai/v1/systemone'
    try:batches=plan(state,questions,model)
    except Unrepresentable:
        if clients.job:clients.job.note('JEV: left this oversized indivisible decision unscored; the author brief and evidence were not truncated. Writing and saved work are retained.')
        return None
    if clients.job and len(batches)>clients.settings.max_calls-clients.job.usage['calls']:
        clients.job.note('JEV: remaining request budget cannot cover this decision batch. Kept it unscored without spending partial requests.')
        return None
    if clients.job and len(batches)>1:clients.job.note(f'JEV: automatically sized {len(batches)} compact decision requests; training articles are excluded.')
    key=clients.vault.get(route) or (clients.llm_key() if route=='openrouter' and clients.settings.provider=='openrouter' else '')
    output={}
    for index,b in enumerate(batches):
        payload={'model':model,'state':b.state,'questions':b.questions}
        size=wire_bytes(payload)
        if size>MAX_BYTES:raise AssertionError('JEV preflight failed')
        data=clients.post(url,payload,key,'JEV')
        answers=data.get('answers',{})
        if not isinstance(answers,dict):raise ProviderError('JEV returned invalid typed answers.')
        import math
        for name,q in b.questions.items():
            a=answers.get(name,{})
            if not isinstance(a,dict) or a.get('type')!=q['type']:raise ProviderError('JEV returned an invalid answer type for '+name+'.')
            if q['type']=='noul':
                v=a.get('noul')
                if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1:raise ProviderError('JEV returned an invalid probability.')
            elif q['type']=='choice' and a.get('choice') not in q['criteria']:raise ProviderError('JEV returned a choice outside the declared options.')
            output[name]=a
        if clients.job and clients.job.receipts:
            clients.job.receipts[-1].update({'request_bytes':size,'decision_questions':len(b.questions),'decision_batch':index+1,'decision_batches':len(batches)})
    return output
