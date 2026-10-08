"""Explicit local graph edits, optimistic saves and reversible graph-only history.

This never calls a model or changes writing voice/position. Quote anchors survive
manual edits as provenance, not automatic validation of a changed claim.
"""
from __future__ import annotations
import hashlib
import json
from typing import Literal
from fastapi import Request
from pydantic import Field
from .models import Model, Node, Edge, Graph, now, uid
from .storage import Conflict


class Edit(Model):
    version: int = Field(ge=0)
    operation: Literal['node','edge','delete-node','delete-edge']
    id: str | None = Field(None,max_length=1000)
    values: dict = Field(default_factory=dict)


def graph_hash(graph):
    return hashlib.sha256(json.dumps(graph.model_dump(),sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def install(app,store,runner):
    with store.connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS graph_history (id TEXT PRIMARY KEY, project_id TEXT, created TEXT, before_graph TEXT, before_pins TEXT, after_hash TEXT)')
        c.execute('CREATE INDEX IF NOT EXISTS graph_history_project ON graph_history(project_id,created)')

    def get(pid,version):
        if runner.active(pid):raise ValueError('Finish or cancel the active job before editing its graph.')
        p=store.get(pid)
        if version!=p.version:raise Conflict('The project has changed. Your graph edit has not been overwritten; refresh the project before applying it.')
        return p

    def result(p,selected_id=None):
        with store.connect() as c:
            row=c.execute('SELECT after_hash FROM graph_history WHERE project_id=? ORDER BY created DESC,rowid DESC LIMIT 1',(p.id,)).fetchone()
        return {'project':p,'selected_id':selected_id,'can_undo':bool(row and row[0]==graph_hash(p.graph))}

    def commit(p,expected,before,undo_id=None):
        # One transaction commits the graph and its undo record; a stale writer
        # cannot leave half an edit or restore somebody else's graph.
        with store.lock,store.connect() as c:
            p.version=expected+1;p.updated=now()
            saved=c.execute('UPDATE projects SET version=?,updated=?,data=? WHERE id=? AND version=?',(p.version,p.updated,p.model_dump_json(),p.id,expected))
            if not saved.rowcount:raise Conflict('Project changed during graph editing. Your newer work was not overwritten.')
            if undo_id:
                c.execute('DELETE FROM graph_history WHERE id=? AND project_id=?',(undo_id,p.id))
            else:
                c.execute('INSERT INTO graph_history VALUES(?,?,?,?,?,?)',(uid('g_'),p.id,now(),before[0],before[1],graph_hash(p.graph)))
                c.execute('DELETE FROM graph_history WHERE project_id=? AND id NOT IN (SELECT id FROM graph_history WHERE project_id=? ORDER BY created DESC,rowid DESC LIMIT 25)',(p.id,p.id))

    @app.get('/api/projects/{pid}/graph/edit-status')
    def status(pid:str):
        return {k:v for k,v in result(store.get(pid)).items() if k!='project'}

    @app.post('/api/projects/{pid}/graph/edit')
    async def graph_edit(pid:str,request:Request):
        raw=Edit.model_validate(await request.json());p=get(pid,raw.version)
        before=(p.graph.model_dump_json(),json.dumps({'pinned':p.brief.pinned_nodes,'excluded':p.brief.excluded_nodes}))
        nodes={n.id:n for n in p.graph.nodes};edges={e.id:e for e in p.graph.edges}
        selected=raw.id;v=raw.values
        if raw.operation in {'node','edge'}:
            node=raw.operation=='node'
            fields={'label','kind','description'} if node else {'source','target','relation','description'}
            if set(v)-fields:raise ValueError('Only the visible graph fields can be edited; source anchors are retained separately.')
            for key,value in v.items():
                if not isinstance(value,str):raise ValueError('Graph fields must contain text.')
                if key!='description' and not value.strip():raise ValueError('A graph label, type or connection cannot be empty.')
                if key in {'kind','relation'} and len(value)>80:raise ValueError('Graph types and relationship names must be at most 80 characters.')
            collection=nodes if node else edges
            if raw.id and raw.id not in collection:raise KeyError(raw.id)
            if raw.id:
                previous=collection[raw.id];data=previous.model_dump()|v
                if any(getattr(previous,k)!=val for k,val in v.items()):data['status']='proposed'
                item=(Node if node else Edge).model_validate(data)
            else:
                item=(Node if node else Edge).model_validate({'id':uid('n_' if node else 'e_'),'status':'proposed'}|v)
            if not node and (item.source not in nodes or item.target not in nodes):raise ValueError('Both connection endpoints must exist in this project.')
            if node:nodes[item.id]=item
            else:edges[item.id]=item
            selected=item.id
        else:
            if v:raise ValueError('Deletion does not accept replacement fields.')
            if raw.operation=='delete-node':
                if raw.id not in nodes:raise KeyError(raw.id)
                del nodes[raw.id]
                edges={key:e for key,e in edges.items() if e.source!=raw.id and e.target!=raw.id}
                p.brief.pinned_nodes=[n for n in p.brief.pinned_nodes if n!=raw.id]
                p.brief.excluded_nodes=[n for n in p.brief.excluded_nodes if n!=raw.id]
            else:
                if raw.id not in edges:raise KeyError(raw.id)
                del edges[raw.id]
            selected=None
        if len(nodes)>5000 or len(edges)>20000:raise ValueError('Graph exceeds 5,000 nodes or 20,000 connections.')
        p.graph.nodes=list(nodes.values());p.graph.edges=list(edges.values())
        p.graph.coverage['manually_edited_at']=now()
        p.angles_context_hash='';p.outline_context_hash=''
        pin_history=json.loads(before[1]);pin_history['after_pinned']=p.brief.pinned_nodes;pin_history['after_excluded']=p.brief.excluded_nodes
        before=(before[0],json.dumps(pin_history))
        commit(p,raw.version,before)
        return result(p,selected)

    @app.post('/api/projects/{pid}/graph/undo')
    async def undo(pid:str,request:Request):
        raw=await request.json()
        if set(raw)!={'version'} or not isinstance(raw['version'],int):raise ValueError('Supply the current project version to undo.')
        p=get(pid,raw['version'])
        with store.connect() as c:
            row=c.execute('SELECT * FROM graph_history WHERE project_id=? ORDER BY created DESC,rowid DESC LIMIT 1',(pid,)).fetchone()
        if not row:raise ValueError('No manual graph edits to undo.')
        if row['after_hash']!=graph_hash(p.graph):raise Conflict('The graph was rebuilt or replaced after this edit. Undo will not overwrite that graph.')
        p.graph=Graph.model_validate_json(row['before_graph']);pins=json.loads(row['before_pins'])
        # Restore edit-induced pin removal, not independent choices made later.
        if p.brief.pinned_nodes==pins.get('after_pinned',pins['pinned']):p.brief.pinned_nodes=pins['pinned']
        if p.brief.excluded_nodes==pins.get('after_excluded',pins['excluded']):p.brief.excluded_nodes=pins['excluded']
        p.angles_context_hash='';p.outline_context_hash=''
        commit(p,raw['version'],None,undo_id=row['id'])
        return result(p)
