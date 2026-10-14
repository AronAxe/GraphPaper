"""Task-specific graph exploration and identity proposals; evidence is immutable here."""
from __future__ import annotations
from difflib import SequenceMatcher
from .system_one import Engine,noul,choice,score,probability,normalized,rank_records,choice_action,YES
from .editorial import context


def assess_motifs(p,clients,candidates):
    from .pipeline import compact_motif
    questions={'fit':noul('Does this graph structure advance the specific author’s argument or requested story rather than suggest a neutral substitute?'),
        'grounded':noul('Are this structure’s factual premises anchored to supplied evidence or canon? Moral evaluations and explicit analogies are separate from empirical identity.'),
        'craft':score('How much concrete argumentative or dramatic development does this structure provide?', ['Disconnected labels.','A usable relation with little development.','A specific mechanism or consequential contrast.','Several linked steps capable of sustaining a compelling progression.']),
        'novelty':score('How much new perspective does this connection offer for the brief?', ['Repeats the obvious subject.','Adds a specific example.','Connects distinct supplied ideas productively.','Reveals a specific unexpected bridge or reversal.'])}
    rows=Engine(clients,p).evaluate('graph opportunities',[compact_motif(c) for c in candidates],questions,context(p,compact=True,include_selection=False))
    for c in candidates:c['judgments']=rows.get(c['id'],{})
    ranked=rank_records(candidates)
    p.system_one['graph_priorities']={c['id']:{'node_ids':c['node_ids'],'edge_ids':c['edge_ids'],'assessed':bool(c['judgments']),
        'relevance':probability(c['judgments'],'fit') if c['judgments'] else None} for c in ranked}
    return ranked


def explore(p,clients,candidates):
    if not getattr(clients.settings,'system_one_exploration',True) or not Engine(clients).enabled:return candidates
    nodes={n.id:n for n in p.graph.nodes};edges={e.id:e for e in p.graph.edges}
    excluded=set(p.brief.excluded_nodes);seen={tuple(sorted(c['node_ids'])) for c in candidates}
    pool=[]
    for base in candidates[:4]:
        present=set(base['node_ids'])
        for edge in p.graph.edges:
            if len(pool)>=16:break
            if (edge.source in present)==(edge.target in present):continue
            new=edge.target if edge.source in present else edge.source
            if new in excluded or new not in nodes:continue
            ids=list(dict.fromkeys(base['node_ids']+[new]));key=tuple(sorted(ids))
            if key in seen:continue
            seen.add(key)
            es=list(dict.fromkeys(base['edge_ids']+[edge.id]))
            source_ids=sorted(set(base['source_ids'])|set(nodes[new].source_ids)|set(edge.source_ids)|{v.source_id for v in nodes[new].evidence if v.verified})
            pool.append({'id':'expand_'+base['id']+'_'+str(len(pool)),'motif':'guided graph expansion','nodes':[nodes[n].model_dump() for n in ids],
                'edges':[edges[e].model_dump() for e in es if e in edges],'node_ids':ids,'edge_ids':es,'source_ids':source_ids,'structural_rank':base['structural_rank']})
    if not pool:return candidates
    assessed=assess_motifs(p,clients,pool)
    # Keep uncertain alternatives visible, but only expand from positively assessed branches.
    promising=[c for c in assessed if c.get('judgments') and probability(c['judgments'],'fit')>=YES][:4]
    p.system_one['exploration']={'nominated':len(pool),'retained':len(promising),'depth':1,'scope':'Bounded expansion of four promising motif neighborhoods; stored evidence unchanged.'}
    return rank_records(candidates+promising)


def alignment(p,clients):
    pool=[];nodes=p.graph.nodes
    # Normalization nominates possible identity pairs; semantic similarity is not identity.
    for i,a in enumerate(nodes[:500]):
        for b in nodes[i+1:500]:
            if a.kind!=b.kind:continue
            ratio=SequenceMatcher(a=a.label.casefold(),b=b.label.casefold()).ratio()
            if ratio<.62:continue
            def compact(n):
                return {'id':n.id,'label':n.label,'kind':n.kind,'description':n.description,
                        'source_ids':n.source_ids,'evidence':[v.model_dump() for v in n.evidence[:2]],
                        'scope':'At most two original quote anchors per node, not exhaustive evidence.'}
            pool.append({'id':a.id+'|'+b.id,'left':compact(a),'right':compact(b)})
            if len(pool)>=24:break
        if len(pool)>=24:break
    qs={'identity':choice('How are these two nodes related? Keep distinct propositions separate even when they use similar vocabulary.',
        {'same':'The same entity or proposition in the same scope.','related':'Related but distinct entities, claims or interpretations.','different':'No meaningful identity relation.','uncertain':'Insufficient context to decide.'})}
    rows=Engine(clients,p).evaluate('entity alignment',pool,qs,{'task':'Propose identity matches without merging or deleting evidence.'})
    proposals=[{'left':x['left']['id'],'right':x['right']['id'],'judgment':rows.get(x['id'],{}).get('identity',{}),
                'recommendation':choice_action(rows.get(x['id'],{}).get('identity'),'uncertain'),'applied':False} for x in pool]
    p.system_one['alignment']=proposals
    return proposals
