"""Synthetic provider responses. Graphify itself is the actual public dependency."""
from __future__ import annotations
import threading
import time
from graphpaper.models import Settings
from graphpaper.providers import Clients,ProviderError


class FixtureClients(Clients):
    seen=[]
    entered=threading.Event()
    behavior='ok'
    def __init__(self,settings,vault,job=None,transport=None):
        super().__init__(settings,vault,job,transport)
    def check(self,url):
        if self.job:self.job.check()
        return super().check(url)
    def complete(self,system,user,*,role='writer',json_mode=False,max_tokens=None):
        assert role=='extraction' and json_mode
        self.job.before_call('fixture',self.settings.max_calls)
        type(self).seen.append({'role':role,'model':self.settings.extraction_model or self.settings.model,
            'effort':self.settings.extraction_reasoning_effort,'system':system,'user':user,'max_tokens':max_tokens})
        type(self).entered.set()
        if self.behavior=='slow':
            while True:self.job.check();time.sleep(.03)
        if self.behavior=='error':raise ProviderError('Synthetic provider failure')
        if self.behavior=='malformed':return {'nodes':'not an array','edges':[]}
        value={'nodes':[
            {'id':'eva','label':'Eva','file_type':'document','source_file':'source-0001.md','description':'Eva maintains the Observatory.'},
            {'id':'observatory','label':'Observatory','file_type':'document','source_file':'source-0001.md','description':'An observation site.'},
            {'id':'funding','label':'Research grant','file_type':'document','source_file':'source-0002.md','description':'Funds the Observatory.'}],
            'edges':[{'source':'eva','target':'observatory','relation':'maintains','confidence':'EXTRACTED','source_file':'source-0001.md','reason':'Eva maintains the Observatory.'},
                {'source':'funding','target':'observatory','relation':'funds','confidence':'EXTRACTED','source_file':'source-0002.md','reason':'A research grant funds the Observatory.'}]}
        self.job.record_usage('fixture',{'input_tokens':120,'output_tokens':90,'cost':0.0},self.settings.extraction_model or self.settings.model)
        return value


def fixture_settings(**kwargs):
    return Settings(provider='openai-compatible',base_url='http://127.0.0.1:1/v1',model='writer-fixture',extraction_model='extract-fixture',
        extraction_reasoning_effort='high',graph_engine='graphify',max_calls=5,**kwargs)


def add_sources(client,pid):
    for title,text,role in [
        ('Operations','Eva maintains the Observatory. The Observatory records variable stars.','evidence'),
        ('Funding','A research grant funds the Observatory. The grant requires public summaries.','evidence'),
        ('Private voice','This voice sample must not be sent to external graph extraction.','voice')]:
        response=client.post('/api/projects/'+pid+'/sources/text',json={'title':title,'text':text,'role':role})
        assert response.status_code==200,response.text
