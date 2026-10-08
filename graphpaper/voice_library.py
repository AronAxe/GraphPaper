"""Named, reusable voice graphs. Training text is stored apart from project evidence."""
from __future__ import annotations
import json
from typing import Any
from pydantic import BaseModel,ConfigDict,Field
from .models import VoiceProfile,Source,now,uid
from .storage import Conflict
from .style_graph import for_profile


class SavedVoice(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    id:str=Field(default_factory=lambda:uid('v_'))
    version:int=0
    updated:str=Field(default_factory=now)
    profile:VoiceProfile=Field(default_factory=VoiceProfile)
    usage:dict[str,Any]=Field(default_factory=dict)
    training_revision:int=0
    learned_revision:int=0


def validate_samples(samples):
    if len(samples)>24 or sum(len(s.text) for s in samples)>6000000:
        raise ValueError('Use at most 24 selected training pieces and 6 million characters per saved voice. Original project samples remain untouched.')
    if any(s.role!='voice' for s in samples):raise ValueError('Voice training records must have the voice role.')


class VoiceLibrary:
    def __init__(self,store):
        self.store=store
        with store.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS voices(id TEXT PRIMARY KEY, version INTEGER NOT NULL, data TEXT NOT NULL, samples TEXT NOT NULL)')

    def get(self,vid):
        with self.store.connect() as c:row=c.execute('SELECT data,samples FROM voices WHERE id=?',(vid,)).fetchone()
        if not row:raise KeyError('Saved voice not found.')
        return SavedVoice.model_validate_json(row['data']),[Source.model_validate(x) for x in json.loads(row['samples'])]

    def list(self):
        with self.store.connect() as c:rows=c.execute('SELECT data,samples FROM voices ORDER BY id').fetchall()
        result=[]
        for row in rows:
            v=SavedVoice.model_validate_json(row['data']);samples=json.loads(row['samples'])
            result.append({'id':v.id,'version':v.version,'name':v.profile.name,'updated':v.updated,
                'nodes':len(for_profile(v.profile).nodes),'samples':len(samples),'needs_relearning':v.training_revision!=v.learned_revision})
        return result

    def create(self,profile=None,samples=None):
        profile=(profile or VoiceProfile()).model_copy(deep=True)
        profile.graph=for_profile(profile).model_dump()
        profile.library_id='';profile.library_version=0
        samples=[s.model_copy(deep=True) for s in (samples or [])]
        for i,s in enumerate(samples):s.id='S'+str(i+1);s.role='voice'
        validate_samples(samples)
        # Training is separate. A new voice with samples but no learned representation is stale.
        v=SavedVoice(profile=profile,training_revision=1 if samples else 0,
                     learned_revision=1 if samples and profile.graph.get('nodes') else 0)
        with self.store.lock,self.store.connect() as c:
            c.execute('INSERT INTO voices VALUES(?,?,?,?)',(v.id,0,v.model_dump_json(),json.dumps([s.model_dump() for s in samples],ensure_ascii=False)))
        return v

    def save(self,v,expected,samples=None):
        v=SavedVoice.model_validate(v.model_dump())
        v.profile.graph=for_profile(v.profile).model_dump()
        v.version=expected+1;v.updated=now()
        if samples is not None:validate_samples(samples)
        with self.store.lock,self.store.connect() as c:
            if samples is None:
                changed=c.execute('UPDATE voices SET version=?,data=? WHERE id=? AND version=?',(v.version,v.model_dump_json(),v.id,expected))
            else:
                changed=c.execute('UPDATE voices SET version=?,data=?,samples=? WHERE id=? AND version=?',(v.version,v.model_dump_json(),json.dumps([s.model_dump() for s in samples],ensure_ascii=False),v.id,expected))
            if changed.rowcount!=1:raise Conflict('This voice changed. Refresh before saving; existing work was not overwritten.')
        return v

    def delete(self,vid,version):
        with self.store.lock,self.store.connect() as c:
            changed=c.execute('DELETE FROM voices WHERE id=? AND version=?',(vid,version))
            if changed.rowcount!=1:raise Conflict('This voice changed or was removed. Refresh first.')

    def apply(self,project,voice):
        profile=voice.profile.model_copy(deep=True)
        profile.graph=for_profile(profile).model_dump()
        if not profile.graph['nodes']:raise ValueError('Learn or define this voice graph first.')
        profile.library_id=voice.id;profile.library_version=voice.version
        profile.sample_ids=[];profile.sample_hash='';profile.enabled=True
        project.voice_profile=profile
        return project
