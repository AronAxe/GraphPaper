"""Explicit manual graph editing; no inference, no source rewrite, atomic one-step undo."""
from __future__ import annotations

import hashlib
import json
from fastapi import Request
from starlette.concurrency import run_in_threadpool
from .models import Project, Node, Edge, Graph, now, uid
from .storage import Conflict


def graph_digest(graph):
    return hashlib.sha256(graph.model_dump_json().encode('utf-8')).hexdigest()


def apply_edit(p: Project, raw: dict) -> Project:
    if not isinstance(raw, dict) or set(raw)-{'version','operation','id','values'}:
        raise ValueError('Unsupported graph edit.')
    operation=raw.get('operation','')
    if not isinstance(operation,str) or operation not in {'node.add','node.update','node.delete','edge.add','edge.update','edge.delete'}:
        raise ValueError('Choose a node or relationship edit.')
    p=p.model_copy(deep=True)
    entity,action=operation.split('.')
    values=raw.get('values',{})
    allowed={'label','kind','description'} if entity=='node' else {'source','target','relation','description'}
    if not isinstance(values,dict) or set(values)-allowed:
        raise ValueError('Only editable graph fields are accepted; source anchors are preserved.')
    for k,v in values.items():
        if not isinstance(v,str):raise ValueError('Graph fields must be text.')
        maximum={'label':200,'kind':80,'relation':80,'description':4000 if entity=='node' else 2000,'source':300,'target':300}[k]
        if len(v)>maximum or (k!='description' and not v.strip()):
            raise ValueError(f'{k} must contain text, up to {maximum} characters.')
    collection=p.graph.nodes if entity=='node' else p.graph.edges
    cls=Node if entity=='node' else Edge
    item=next((x for x in collection if x.id==raw.get('id')),None)
    if action!='add' and item is None:raise KeyError(raw.get('id'))
    if action=='delete':
        collection.remove(item)
        if entity=='node':
            p.graph.edges=[e for e in p.graph.edges if e.source!=item.id and e.target!=item.id]
            p.brief.pinned_nodes=[i for i in p.brief.pinned_nodes if i!=item.id]
            p.brief.excluded_nodes=[i for i in p.brief.excluded_nodes if i!=item.id]
    else:
        if action=='add':
            required={'label'} if entity=='node' else {'source','target','relation'}
            if not required<=values.keys():raise ValueError('Required graph fields are missing.')
            changed=cls.model_validate({'id':uid('n_' if entity=='node' else 'e_'),'status':'proposed',**values})
        else:
            changed=cls.model_validate(item.model_dump()|values|{'status':'proposed'})
        if entity=='edge':
            ids={n.id for n in p.graph.nodes}
            if changed.source not in ids or changed.target not in ids:
                raise ValueError('Both ends of the relationship must exist in this project.')
        if action=='add':collection.append(changed)
        else:collection[collection.index(item)]=changed
    if len(p.graph.nodes)>5000 or len(p.graph.edges)>20000:raise ValueError('Graph size limit reached.')
    if hasattr(p,'angles_context_hash'):p.angles_context_hash=''
    if hasattr(p,'outline_context_hash'):p.outline_context_hash=''
    return p


def register(app, store, runner):
    def transact(pid, raw, undo=False):
        if not isinstance(raw,dict):raise ValueError('Expected a graph edit object.')
        with store.lock, store.connect() as c:
            if runner.active(pid):raise ValueError('Finish or cancel the active job before editing its graph.')
            row=c.execute('SELECT data FROM projects WHERE id=?',(pid,)).fetchone()
            if not row:raise KeyError(pid)
            p=Project.model_validate_json(row[0]);expected=raw.get('version')
            if isinstance(expected,bool) or not isinstance(expected,int) or expected!=p.version:
                raise Conflict('The project changed. Refresh before saving; newer work was not overwritten.')
            key='graph-undo:'+pid
            if undo:
                previous=c.execute('SELECT data FROM cache WHERE key=?',(key,)).fetchone()
                if not previous:raise ValueError('There is no manual graph edit to undo.')
                previous=json.loads(previous[0])
                if previous['after']!=graph_digest(p.graph):
                    raise Conflict('The graph has changed since that edit. Undo will not replace a newer graph.')
                p.graph=Graph.model_validate(previous['graph'])
                p.brief.pinned_nodes=previous['pinned'];p.brief.excluded_nodes=previous['excluded']
                if hasattr(p,'angles_context_hash'):p.angles_context_hash=''
                if hasattr(p,'outline_context_hash'):p.outline_context_hash=''
                c.execute('DELETE FROM cache WHERE key=?',(key,))
            else:
                old=p
                p=apply_edit(p,raw)
                previous={'graph':old.graph.model_dump(),'pinned':old.brief.pinned_nodes,'excluded':old.brief.excluded_nodes,'after':graph_digest(p.graph)}
                c.execute('INSERT OR REPLACE INTO cache VALUES(?,?)',(key,json.dumps(previous)))
            p.version=expected+1;p.updated=now()
            result=c.execute('UPDATE projects SET version=?,updated=?,data=? WHERE id=? AND version=?',(p.version,p.updated,p.model_dump_json(),pid,expected))
            if not result.rowcount:raise Conflict('The project changed before the graph could be saved.')
            return p

    @app.post('/api/projects/{pid}/graph/edit')
    async def graph_edit(pid: str, request: Request):
        return await run_in_threadpool(transact,pid,await request.json())

    @app.post('/api/projects/{pid}/graph/undo')
    async def graph_undo(pid: str, request: Request):
        return await run_in_threadpool(transact,pid,await request.json(),True)
