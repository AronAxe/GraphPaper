"""Reusable style graphs, with explicit layers and no word/tone blacklist."""
from __future__ import annotations
import hashlib
import json
import re
from pydantic import BaseModel,ConfigDict,Field,model_validator


def encoded(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)


class StyleNode(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    id:str=Field(min_length=1,max_length=100)
    label:str=Field(min_length=1,max_length=100)
    instruction:str=Field('',max_length=600)
    kind:str=Field('style',max_length=60)
    weight:float=Field(1,ge=0,le=1)
    targets:list[str]=Field(default_factory=lambda:['all'],max_length=12)


class StyleEdge(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source:str=Field(max_length=100)
    target:str=Field(max_length=100)
    relation:str=Field('guides',max_length=80)


class StyleGraph(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    schema_version:int=1
    nodes:list[StyleNode]=Field(default_factory=list,max_length=32)
    edges:list[StyleEdge]=Field(default_factory=list,max_length=64)
    source_hash:str=''
    @model_validator(mode='after')
    def validate_graph(self):
        ids=[n.id for n in self.nodes]
        if len(ids)!=len(set(ids)):raise ValueError('Voice graph node IDs must be unique.')
        if any(e.source not in ids or e.target not in ids for e in self.edges):raise ValueError('Voice graph contains a dangling relationship.')
        if len(encoded(self.model_dump()).encode())>30000:raise ValueError('Keep this reusable voice graph below 30 KB; training articles belong in its separate sample library.')
        return self


def text_graph(instructions,name='My voice'):
    """Lossless deterministic migration of an existing <=12,000-character profile."""
    raw=instructions.strip()
    if not raw:return StyleGraph()
    pieces=[]
    for paragraph in raw.splitlines():
        paragraph=paragraph.strip()
        if not paragraph:continue
        # No banned phrases, softening, summarization or rewriting of the author's words.
        pieces.extend(paragraph[i:i+600] for i in range(0,len(paragraph),600))
    if len(pieces)>31:
        pieces=[raw[i:i+600] for i in range(0,len(raw),600)]
    root=StyleNode(id='voice',label=name[:100],kind='voice',instruction='Reusable style preferences. The current author brief takes precedence.')
    nodes=[root]+[StyleNode(id='habit_'+str(i+1),label=(p.split(':',1)[0][:70] if ':' in p else 'Writing habit '+str(i+1)),instruction=p) for i,p in enumerate(pieces)]
    return StyleGraph(nodes=nodes,edges=[StyleEdge(source='voice',target=n.id,relation='expresses') for n in nodes[1:]],source_hash=hashlib.sha256(raw.encode()).hexdigest())


def for_profile(profile):
    graph=StyleGraph.model_validate(profile.graph or {})
    raw=profile.instructions.strip()
    # An edited legacy instruction box regenerates its graph deterministically.
    if graph.nodes and (not graph.source_hash or graph.source_hash==hashlib.sha256(raw.encode()).hexdigest()):return graph
    return text_graph(raw,profile.name)


def view(graph,budget=6500):
    """A node/edge-closed view. Whole style directives are selected, never clipped."""
    graph=StyleGraph.model_validate(graph)
    selected=[]
    def material(nodes):
        ids={n.id for n in nodes}
        return {'nodes':[n.model_dump(exclude={'targets'}) for n in nodes],
            'edges':[e.model_dump() for e in graph.edges if e.source in ids and e.target in ids],
            'coverage':{'shown':len(nodes),'total':len(graph.nodes),'complete':len(nodes)==len(graph.nodes)}}
    for node in sorted(graph.nodes,key=lambda n:(n.kind!='voice',-n.weight,n.id)):
        if len(encoded(material(selected+[node])).encode())<=budget:selected.append(node)
    return material(selected)


def voice_decision(profile):
    if not profile.enabled or not profile.strength:return {'enabled':False}
    return {'enabled':True,'name':profile.name,'influence_percent':profile.strength,'graph':view(for_profile(profile)),
        'rule':'Style, not factual evidence. Current project instructions override saved habits, including their force, vocabulary and use of profanity. Do not sanitize power language.'}


def overlay(project,maximum=100):
    """Compose namespaced node-link graphs without merging style nodes into evidence."""
    import networkx as nx
    from networkx.readwrite import json_graph
    voice=for_profile(project.voice_profile)
    evidence=nx.DiGraph();style=nx.DiGraph()
    evidence.add_node('scope:'+project.id,label=project.title,layer='scope',kind='project')
    for n in project.graph.nodes[:maximum]:
        evidence.add_node('evidence:'+n.id,label=n.label,kind=n.kind,layer='evidence',status=n.status)
    for e in project.graph.edges:
        a,b='evidence:'+e.source,'evidence:'+e.target
        if a in evidence and b in evidence:evidence.add_edge(a,b,relation=e.relation,layer='evidence')
    if project.voice_profile.enabled and project.voice_profile.strength:
        for n in voice.nodes:style.add_node('style:'+n.id,**n.model_dump(exclude={'id'}),layer='style')
        for e in voice.edges:style.add_edge('style:'+e.source,'style:'+e.target,relation=e.relation,layer='style')
    combined=nx.compose(evidence,style)
    for n in voice.nodes:
        key='style:'+n.id
        if key not in combined:continue
        if n.kind=='voice':combined.add_edge(key,'scope:'+project.id,relation='guides_expression',layer='overlay')
        for target in project.graph.nodes[:maximum]:
            if target.kind in n.targets:combined.add_edge(key,'evidence:'+target.id,relation='guides_expression',layer='overlay')
    result=json_graph.node_link_data(combined,edges='edges')
    result['scope']={'evidence_nodes_shown':min(maximum,len(project.graph.nodes)),'evidence_nodes_total':len(project.graph.nodes),
        'note':'Composed style/evidence layers. Style links guide expression, not proof. The stored research graph is unchanged.'}
    return result
