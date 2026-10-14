"""Author-facing decisions, preferences and evaluation data. No background inference."""
from fastapi import Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from pydantic import Field
from .models import Model
from .storage import Conflict
from . import s1_learning


class Feedback(Model):
    version:int=Field(ge=0)
    angle_id:str=Field(min_length=1,max_length=200)
    label:int=Field(ge=0,le=1)
    correction:str=Field('',max_length=2000)


def install(app,store,runner,settings):
    s1_learning.initialize(store)

    @app.get('/api/projects/{pid}/system-one')
    def status(pid:str):
        p=store.get(pid)
        return {'state':p.system_one,'feedback':s1_learning.history(store,p),
                'preference_model':s1_learning.model(store,p),'scope':s1_learning.scope(p),
                'settings':{k:v for k,v in settings().model_dump().items() if k.startswith('system_one_')},
                'note':'Recorded judgments may predate edits. Current instructions override learned preferences. No model call is made by viewing this desk.'}

    @app.post('/api/projects/{pid}/system-one/feedback')
    async def feedback(pid:str,request:Request):
        raw=Feedback.model_validate(await request.json())
        with runner.lock,store.lock:
            if runner.active(pid):raise ValueError('Wait for the active job before rating its results.')
            p=store.get(pid)
            if p.version!=raw.version:raise Conflict('The angle changed. Refresh before rating it.')
            a=next((a for a in p.angles if a.id==raw.angle_id),None)
            if a is None:raise KeyError(raw.angle_id)
            return s1_learning.add_feedback(store,p,a.id,raw.label,a.scores,raw.correction)

    @app.delete('/api/projects/{pid}/system-one/feedback/{fid}')
    def remove(pid:str,fid:str):
        p=store.get(pid)
        with store.lock:s1_learning.remove_feedback(store,p,fid)
        return {'ok':True}

    @app.post('/api/projects/{pid}/system-one/train')
    async def train(pid:str):
        p=store.get(pid)
        def work():
            with store.lock:return s1_learning.train(store,p)
        return await run_in_threadpool(work)

    @app.post('/api/projects/{pid}/system-one/reset-model')
    def reset(pid:str):
        with store.lock:s1_learning.reset_model(store,store.get(pid))
        return {'ok':True}
