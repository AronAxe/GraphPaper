"""Change the writing mode of an existing project without replacing its work."""
from fastapi import Request
from .editorial import contract, fingerprint, review_stamp, stale_angles
from .storage import Conflict

MODES={'nonfiction','fiction','science','polemic'}


def install(app,store,runner):
    @app.post('/api/projects/{pid}/writing-mode')
    async def change_mode(pid:str,request:Request):
        raw=await request.json()
        if not isinstance(raw,dict) or set(raw)-{'mode','version'}:
            raise ValueError('Choose a writing mode and the current project revision.')
        mode=raw.get('mode')
        if mode not in MODES:raise ValueError('Unknown writing mode.')
        with runner.lock,store.lock:
            if runner.active(pid):raise ValueError('Finish or cancel the active job before changing writing mode.')
            p=store.get(pid)
            if raw.get('version')!=p.version:raise Conflict('This project changed. Refresh before switching its writing mode.')
            if p.mode==mode:return p
            previous=p.mode
            p.mode=mode
            if mode=='polemic':
                p.brief.stance_policy='preserve'
                if p.brief.rhetorical_force==70:p.brief.rhetorical_force=85
                if p.brief.format in {'Long-form essay','APA scientific manuscript','Short story'}:
                    p.brief.format='Polemic / argumentative essay'
            # Keep source IDs, graph, angles, outline, manuscript, voice, revisions
            # and scientific/fiction context. Old stages are marked stale by hash,
            # not deleted or silently regenerated.
            p.research.acknowledgements={}
            p.research.confirmation_hash=''
            p.activity.append({'action':'writing-mode','from':previous,'to':mode})
            p.activity=p.activity[-100:]
            return store.save(p,p.version)

    @app.get('/api/projects/{pid}/editorial/status')
    def status(pid:str):
        p=store.get(pid)
        voice_enabled=p.voice_profile.enabled and p.voice_profile.strength>0
        return {'mode':p.mode,'version':p.version,'contract':contract(p),
                'voice_enabled':voice_enabled,'voice_samples':sum(s.enabled and s.role=='voice' for s in p.sources),
                'angles_stale':stale_angles(p),
                'outline_stale':bool(p.outline and p.outline_context_hash!=review_stamp(p)),
                'review_stale':bool(p.review.summary and p.review.context_hash!=review_stamp(p)),
                'instruction':'Changing mode or brief does not rewrite existing angles. Refresh angles from this graph to use the current thesis and voice; rebuilding the graph is unnecessary.'}
