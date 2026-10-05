"""Author voice, project inbox, prose editing and Codex UI endpoints."""
from __future__ import annotations
import hashlib
import os
import subprocess
import sys
from fastapi import Request
from starlette.concurrency import run_in_threadpool
from .models import Review
from .storage import Conflict
from .folders import ProjectFolders
from .polish import lint
from .voice import fingerprint, metrics, samples


def install(app, store, vault, runner, settings):
    folders = ProjectFolders(store,runner)
    app.state.folders = folders

    @app.get('/api/projects/{pid}/workspace')
    def workspace(pid: str):
        p = store.get(pid)
        return folders.info(p)

    @app.post('/api/projects/{pid}/workspace/scan')
    async def scan(pid: str, request: Request):
        raw = await request.json()
        return await run_in_threadpool(folders.scan,pid,bool(raw.get('force',False)))

    @app.post('/api/projects/{pid}/workspace/open')
    def open_folder(pid: str):
        folder = folders.path(store.get(pid))
        if sys.platform == 'win32':
            os.startfile(str(folder))
        elif sys.platform == 'darwin':
            subprocess.Popen(['open',str(folder)])
        elif os.getenv('DISPLAY'):
            subprocess.Popen(['xdg-open',str(folder)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            return {'opened':False,'path':str(folder)}
        return {'opened':True,'path':str(folder)}

    @app.get('/api/projects/{pid}/voice')
    def voice(pid: str):
        p = store.get(pid)
        return {'profile':p.voice_profile.model_dump(),'samples':[{'id':s.id,'title':s.title,'url':s.url,'metrics':metrics(s.text)} for s in samples(p)],
                'stale':bool(p.voice_profile.sample_hash and p.voice_profile.sample_hash!=fingerprint(p))}

    @app.post('/api/voice/discover')
    async def discover(request: Request):
        from .author_web import discover
        raw = await request.json()
        return await run_in_threadpool(discover,str(raw.get('url','')))

    @app.post('/api/projects/{pid}/craft/audit')
    def audit(pid: str):
        return lint(store.get(pid).draft)

    @app.post('/api/projects/{pid}/craft/accept')
    async def accept(pid: str, request: Request):
        raw = await request.json()
        with runner.lock, store.lock:
            if runner.active(pid):
                raise ValueError('Finish or cancel the current job first.')
            p = store.get(pid)
            if raw.get('version') != p.version:
                raise Conflict('The project changed. Refresh and compare the current draft before applying an edit.')
            candidate = p.polish
            if not candidate or candidate.original_hash != hashlib.sha256(p.draft.encode()).hexdigest():
                raise Conflict('The draft changed since this edit was proposed. Generate a fresh edit; nothing was overwritten.')
            if not candidate.review.get('meaning_preserved') and not raw.get('acknowledge_warnings',False):
                raise ValueError('The reviewer flagged meaning changes. Check the comparison and explicitly acknowledge those warnings before applying.')
            store.snapshot(p,'Before '+candidate.mode)
            p.draft = candidate.draft
            p.polish = None
            p.review = Review()
            p = store.save(p,p.version)
            store.snapshot(p,'Accepted prose edit')
            return p

    @app.post('/api/projects/{pid}/craft/discard')
    async def discard(pid: str, request: Request):
        raw = await request.json()
        with runner.lock, store.lock:
            p = store.get(pid)
            if runner.active(pid):
                raise ValueError('Finish or cancel the current job first.')
            if raw.get('version') != p.version:
                raise Conflict('The project changed. Refresh before discarding this candidate.')
            p.polish = None
            return store.save(p,p.version)

    def codex():
        from .codex import get_codex
        return get_codex(store.root,settings().codex_executable)

    @app.get('/api/codex/status')
    async def codex_status():
        from .providers import ProviderError
        try:
            return await run_in_threadpool(lambda:codex().status())
        except ProviderError as e:
            return {'installed':False,'signed_in':False,'error':str(e)}

    @app.post('/api/codex/login')
    async def codex_login():
        return await run_in_threadpool(lambda:codex().login())

    @app.post('/api/codex/logout')
    async def codex_logout():
        if any(j.state in {'queued','running'} for j in runner.jobs.values()):
            raise ValueError('Finish or cancel active jobs before signing out.')
        return await run_in_threadpool(lambda:codex().logout())
