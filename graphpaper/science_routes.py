"""Project-scoped scientific workspace routes; no implicit search or model spending."""
from __future__ import annotations
from fastapi import Request
from .science_models import ResearchPlan, ScholarlyMeta
from .science import record_source, mark_changed, readiness, research_fingerprint
from .ingest import digest
from .storage import Conflict
from .apa import markdown, citation_map


def install(app,store,vault,runner,settings):
    def project(pid,version=None):
        if runner.active(pid):raise ValueError('Finish or cancel the active project job before changing the research workspace.')
        p=store.get(pid)
        if p.mode!='science':raise ValueError('This workspace belongs to a Science project.')
        if version is not None and version!=p.version:raise Conflict('The research project changed. Refresh before saving.')
        return p

    @app.put('/api/projects/{pid}/research/plan')
    async def plan(pid:str,request:Request):
        raw=await request.json()
        with runner.lock,store.lock:
            p=project(pid,raw.get('version',-1))
            p.research.plan=ResearchPlan.model_validate(raw.get('plan',{}))
            if 'abstract' in raw:p.research.abstract=str(raw['abstract'])[:12000]
            if 'keywords' in raw:p.research.keywords=[str(x)[:100] for x in raw['keywords'][:12]]
            p.brief.direction=p.research.plan.question
            mark_changed(p)
            return store.save(p,p.version)

    @app.post('/api/projects/{pid}/research/screen')
    async def screen(pid:str,request:Request):
        raw=await request.json()
        with runner.lock,store.lock:
            p=project(pid,raw.get('version',-1))
            ids=set(raw.get('ids',[]));decision=raw.get('decision')
            if not ids or len(ids)>600 or decision not in {'include','exclude','unscreened'}:raise ValueError('Select papers and a valid screening decision.')
            if not ids<={r.id for r in p.research.records}:raise ValueError('Unknown paper ID.')
            reason=str(raw.get('reason',''))[:3000]
            if decision=='exclude' and not reason.strip():raise ValueError('Record an exclusion reason for the search audit.')
            for r in p.research.records:
                if r.id not in ids:continue
                if decision=='include' and r.metadata.retracted:raise ValueError('This paper is flagged retracted. Do not include it as supporting evidence.')
                r.decision=decision;r.reason=reason
                if decision=='include':record_source(p,r)
            active_ids={r.source_id for r in p.research.records if r.decision=='include'}
            inactive={r.source_id for r in p.research.records if r.id in ids and r.decision!='include'}-active_ids
            for s in p.sources:
                if s.id in inactive:s.enabled=False
            mark_changed(p)
            if p.graph.nodes:p.graph.warnings=list(dict.fromkeys(p.graph.warnings+['Sources changed after research screening. Rebuild the graph.']))
            return store.save(p,p.version)

    @app.patch('/api/projects/{pid}/research/records/{rid}')
    async def update_record(pid:str,rid:str,request:Request):
        raw=await request.json()
        with runner.lock,store.lock:
            p=project(pid,raw.get('version',-1));r=next((r for r in p.research.records if r.id==rid),None)
            if not r:raise ValueError('Paper not found.')
            if 'metadata' in raw:
                candidate=ScholarlyMeta.model_validate(raw['metadata'])
                candidate.retracted = candidate.retracted or r.metadata.retracted
                candidate.content_scope=r.metadata.content_scope
                candidate.metadata_sources=list(dict.fromkeys(r.metadata.metadata_sources+['author-corrected']))
                candidate.retrieved_at=r.metadata.retrieved_at
                r.metadata=candidate
                if r.source_id:
                    s=next((s for s in p.sources if s.id==r.source_id),None)
                    if s:s.scholarly=candidate.model_copy(deep=True)
            if 'reason' in raw:r.reason=str(raw['reason'])[:3000]
            if 'appraisal_note' in raw:r.appraisal['author_note']=str(raw['appraisal_note'])[:6000]
            mark_changed(p);return store.save(p,p.version)

    @app.post('/api/projects/{pid}/research/records/{rid}/attach')
    async def attach(pid:str,rid:str,request:Request):
        raw=await request.json()
        with runner.lock,store.lock:
            p=project(pid,raw.get('version',-1));r=next((r for r in p.research.records if r.id==rid),None)
            source=next((s for s in p.sources if s.id==raw.get('source_id') and s.role=='evidence'),None)
            if not r or not source:raise ValueError('Select a paper and an existing evidence-role source.')
            if any(other.id != rid and other.source_id == source.id for other in p.research.records):raise ValueError('That source is already linked to a different paper. Upload the correct paper as a separate source.')
            if not raw.get('confirm_identity'):raise ValueError('Confirm that the uploaded text is this exact paper.')
            old_id=r.source_id;r.source_id=source.id;r.metadata.content_scope='full_text' if raw.get('full_text') else 'user_supplied'
            source.scholarly=r.metadata.model_copy(deep=True);source.enabled=r.decision=='include'
            r.appraisal={};r.appraisal_source_hash='';r.fulltext_error=''
            for s in p.sources:
                if s.id==old_id and old_id!=source.id and not any(o.source_id==old_id and o.decision=='include' for o in p.research.records):s.enabled=False
            mark_changed(p);return store.save(p,p.version)

    @app.get('/api/projects/{pid}/research/readiness')
    def get_readiness(pid:str):
        p=store.get(pid)
        if p.mode!='science':raise ValueError('Not a Science project.')
        return readiness(p)

    @app.post('/api/projects/{pid}/research/confirm')
    async def confirm(pid:str,request:Request):
        raw=await request.json()
        with runner.lock,store.lock:
            p=project(pid,raw.get('version',-1));allowed=readiness(p)['author_checks']
            checks=raw.get('checks',{})
            if set(checks)-set(allowed) or any(type(v)!=bool for v in checks.values()):raise ValueError('Invalid author confirmations.')
            p.research.acknowledgements=checks
            p.research.confirmation_hash=digest(research_fingerprint(p)+p.draft+p.research.abstract)
            return store.save(p,p.version)

    @app.get('/api/projects/{pid}/research/preview')
    def preview(pid:str):
        p=store.get(pid)
        return {'markdown':markdown(p),'citations':citation_map(p)}
