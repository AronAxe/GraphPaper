"""GUI-facing voice library, isolated training jobs and explicit project application."""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import Request,UploadFile,File
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from .models import Source,VoiceProfile,Project,now
from .voice_library import VoiceLibrary
from .style_graph import StyleGraph,for_profile,overlay
from .ingest import clean,digest,extract,fetch_url,MAX_BYTES
from .storage import Conflict


def install(app,store,vault,runner,settings):
    library=VoiceLibrary(store);app.state.voices=library
    def active(vid):
        return any(j.project_id==vid and j.state in {'queued','running'} for j in runner.jobs.values())
    def get_editable(vid,version=None):
        if active(vid):raise ValueError('Finish or cancel this voice-learning job before editing it.')
        v,s=library.get(vid)
        if version is not None and v.version!=version:raise Conflict('The voice changed. Refresh before saving.')
        return v,s
    def public(v,s):
        return {**v.model_dump(),'graph':for_profile(v.profile).model_dump(),
            'samples':[{'id':x.id,'title':x.title,'words':len(x.text.split()),'url':x.url} for x in s],
            'needs_relearning':v.training_revision!=v.learned_revision}
    def add_training(vid,title,text,kind='text',url='',warnings=None):
        with runner.lock,store.lock:
            v,s=get_editable(vid);text=clean(text)
            if any(x.digest==digest(text) for x in s):raise ValueError('This writing sample is already in the voice library.')
            number=max([int(x.id[1:]) for x in s]+[0])+1
            s.append(Source(id='S'+str(number),title=title[:300],text=text,role='voice',kind=kind,url=url,warnings=warnings or [],digest=digest(text)))
            v.training_revision+=1
            return public(library.save(v,v.version,s),s)

    @app.get('/api/voices')
    def list_voices():return library.list()

    @app.post('/api/voices')
    async def create_voice(request:Request):
        raw=await request.json()
        if set(raw)-{'name','instructions','graph','project_id','version'}:raise ValueError('Unsupported voice property.')
        with runner.lock,store.lock:
            if raw.get('project_id'):
                p=store.get(raw['project_id'])
                if runner.active(p.id):raise ValueError('Finish the active project job first.')
                if p.version!=raw.get('version'):raise Conflict('The project changed. Refresh before saving its voice.')
                profile=p.voice_profile.model_copy(deep=True)
                samples=[s for s in p.sources if s.role=='voice' and s.enabled]
            else:profile=VoiceProfile();samples=[]
            if 'name' in raw:profile.name=raw['name']
            if 'instructions' in raw:profile.instructions=raw['instructions'];profile.graph={}
            if 'graph' in raw:profile.graph=StyleGraph.model_validate(raw['graph']).model_dump()
            profile=VoiceProfile.model_validate(profile.model_dump())
            v=library.create(profile,samples)
            return public(v,library.get(v.id)[1])

    @app.post('/api/voices/import')
    async def import_voice(request:Request):
        raw=await request.json()
        if raw.get('format')!='graphpaper-voice-1':raise ValueError('Choose a GraphPaper voice graph export.')
        profile=VoiceProfile.model_validate(raw.get('profile',{}))
        profile.graph=StyleGraph.model_validate(profile.graph).model_dump()
        v=library.create(profile)
        return public(v,[])

    @app.get('/api/voices/{vid}')
    def read_voice(vid:str):return public(*library.get(vid))

    @app.patch('/api/voices/{vid}')
    async def edit_voice(vid:str,request:Request):
        raw=await request.json()
        if set(raw)-{'version','name','instructions','graph','strength'}:raise ValueError('Unsupported saved-voice property.')
        with runner.lock,store.lock:
            v,s=get_editable(vid,raw.get('version',-1))
            for key in ('name','strength'):
                if key in raw:setattr(v.profile,key,raw[key])
            if 'instructions' in raw and raw['instructions']!=v.profile.instructions:
                v.profile.instructions=raw['instructions'];v.profile.graph={}
            if 'graph' in raw:
                g=StyleGraph.model_validate(raw['graph']);g.source_hash=''
                v.profile.graph=g.model_dump()
            v.profile=VoiceProfile.model_validate(v.profile.model_dump())
            return public(library.save(v,v.version),s)

    @app.delete('/api/voices/{vid}')
    async def delete_voice(vid:str,request:Request):
        raw=await request.json()
        with runner.lock,store.lock:
            v,_=get_editable(vid,raw.get('version',-1));library.delete(vid,v.version)
        return {'deleted':True,'note':'Applied project copies remain available.'}

    @app.get('/api/voices/{vid}/export')
    def export_voice(vid:str):
        v,_=library.get(vid)
        profile=v.profile.model_copy(deep=True);profile.sample_ids=[];profile.sample_hash='';profile.library_id='';profile.library_version=0
        content=json.dumps({'format':'graphpaper-voice-1','profile':profile.model_dump()},ensure_ascii=False,indent=2)
        return Response(content,media_type='application/json',headers={'Content-Disposition':'attachment; filename="voice-graph.json"'})

    @app.post('/api/voices/{vid}/samples/text')
    async def sample_text(vid:str,request:Request):
        raw=await request.json();return add_training(vid,str(raw.get('title','Writing sample')),str(raw.get('text','')))

    @app.post('/api/voices/{vid}/samples/file')
    async def sample_file(vid:str,file:UploadFile=File(...)):
        data=await file.read(MAX_BYTES+1);await file.close()
        title=Path(file.filename or 'sample.txt').name
        text,warnings=await run_in_threadpool(extract,data,title)
        return add_training(vid,title,text,'file',warnings=warnings)

    @app.post('/api/voices/{vid}/samples/url')
    async def sample_url(vid:str,request:Request):
        raw=await request.json()
        title,text,url,warnings=await run_in_threadpool(fetch_url,str(raw.get('url','')))
        return add_training(vid,title,text,'url',url,warnings)

    @app.get('/api/voices/{vid}/samples/{sid}')
    def sample_read(vid:str,sid:str):
        _,samples=library.get(vid);s=next((x for x in samples if x.id==sid),None)
        if s is None:raise KeyError('Training sample not found.')
        return {'id':s.id,'title':s.title,'text':s.text}

    @app.delete('/api/voices/{vid}/samples/{sid}')
    async def sample_delete(vid:str,sid:str,request:Request):
        raw=await request.json()
        with runner.lock,store.lock:
            v,s=get_editable(vid,raw.get('version',-1))
            rest=[x for x in s if x.id!=sid]
            if len(rest)==len(s):raise KeyError('Training sample not found.')
            v.training_revision+=1
            return public(library.save(v,v.version,rest),rest)

    def learn_job(job,v,s,configuration):
        from .voice import learn_voice
        from .providers import Cancelled,ProviderError
        job.state='running';original_version=v.version
        try:
            temporary=Project(title='Voice learning',sources=s,voice_profile=v.profile.model_copy(deep=True))
            clients=runner.clients_factory(configuration,vault,job)
            learn_voice(temporary,clients,job);job.check()
            v.profile=temporary.voice_profile;v.profile.graph=for_profile(v.profile).model_dump()
            v.learned_revision=v.training_revision
            for key,value in job.usage.items():v.usage[key]=v.usage.get(key,0)+value
            library.save(v,original_version)
            job.state='completed';job.progress=100
        except Cancelled:job.state='cancelled';job.error='Voice learning cancelled. The previous saved voice is unchanged.'
        except Exception as e:
            job.state='failed';job.error=str(e) if isinstance(e,(ValueError,ProviderError,Conflict)) else 'Voice learning failed. The previous saved voice is unchanged.'
        finally:job.finished=now()

    @app.post('/api/voices/{vid}/learn')
    async def learn(vid:str,request:Request):
        from .pipeline import Job
        raw=await request.json()
        with runner.lock,store.lock:
            v,s=get_editable(vid,raw.get('version',-1))
            if not s:raise ValueError('Add writing samples to this voice first.')
            job=Job(vid,'voice-library');runner.jobs[job.id]=job
            runner.pool.submit(learn_job,job,v,s,settings())
            return job.public()

    @app.post('/api/projects/{pid}/voice/apply')
    async def apply(pid:str,request:Request):
        raw=await request.json()
        with runner.lock,store.lock:
            if runner.active(pid):raise ValueError('Finish the current project job before applying a voice.')
            p=store.get(pid)
            if p.version!=raw.get('version'):raise Conflict('The project changed. Refresh before applying this voice.')
            v,_=library.get(raw.get('voice_id',''))
            library.apply(p,v)
            return store.save(p,p.version)

    @app.get('/api/projects/{pid}/voice/overlay')
    def get_overlay(pid:str):return overlay(store.get(pid))
