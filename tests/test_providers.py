from __future__ import annotations
import json
import httpx
import pytest
from graphpaper.models import Settings
from graphpaper.secrets import Vault
from graphpaper.providers import Clients, ProviderError, parse_json, endpoint
from graphpaper.pipeline import Job


def test_json_parser_strict():
    assert parse_json('```json\n{"a":1}\n```')=={'a':1}
    for text in ['not json','[]','{"x":NaN}','{"x":Infinity}']:
        with pytest.raises(ProviderError):parse_json(text)


def test_endpoint_policy():
    assert endpoint('https://example.org/v1/')=='https://example.org/v1'
    assert endpoint('http://127.0.0.1:11434/v1')
    for x in ['http://example.org','https://key:secret@example.org','file:///x','https://example.org?api_key=x']:
        with pytest.raises(ValueError):endpoint(x)


@pytest.mark.parametrize('route',['openrouter','typesafe'])
def test_real_jev_protocol_shape_with_mock_transport(tmp_path,route):
    seen=[];v=Vault(tmp_path);v.set(route,'unit-test-key',False)
    def handler(req):
        data=json.loads(req.content);seen.append((str(req.url),data,req.headers.get('Authorization')))
        return httpx.Response(200,json={'answers':{'good':{'type':'noul','noul':.9}},'usage':{'input_tokens':10,'output_tokens':3,'cost':.0002}})
    j=Job('test','angles');c=Clients(Settings(model='test',allow_cloud=True,jev_provider=route),v,j,transport=httpx.MockTransport(handler))
    ans=c.decide({'candidate':'A'}, {'good':{'type':'noul','instructions':'Is this coherent?'}})
    assert ans['good']['noul']==.9
    assert seen[0][0]==('https://openrouter.ai/api/alpha/decisions' if route=='openrouter' else 'https://api.typesafe.ai/v1/systemone')
    assert seen[0][1]['model']==('~typesafe/jev-latest' if route=='openrouter' else 'jev-latest')
    assert seen[0][2]=='Bearer unit-test-key'
    assert j.usage['calls']==1 and j.usage['unpriced_calls']==0


def test_jev_auto_precedence_and_generic_openrouter_key(tmp_path):
    v=Vault(tmp_path);s=Settings(model='test');c=Clients(s,v)
    assert c.jev_route()=='off'
    v.set('typesafe','x',False);assert c.jev_route()=='typesafe'
    v.set('openrouter','y',False);assert c.jev_route()=='openrouter'
    v.set('openrouter','',False);v.set('llm','generic',False)
    assert c.llm_key()=='generic' and c.jev_route()=='openrouter'


@pytest.mark.parametrize('value',[True,-.1,1.1,None,'0.5'])
def test_jev_invalid_noul_rejected(tmp_path,value):
    v=Vault(tmp_path);v.set('typesafe','x',False)
    c=Clients(Settings(model='test',allow_cloud=True,jev_provider='typesafe'),v,transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'answers':{'q':{'type':'noul','noul':value}}})))
    with pytest.raises(ProviderError):c.decide('state',{'q':{'type':'noul','instructions':'Check'}})


def test_no_consent_no_network(tmp_path):
    called=[];v=Vault(tmp_path);v.set('openrouter','x',False)
    c=Clients(Settings(model='test'),v,transport=httpx.MockTransport(lambda r:called.append(r)))
    with pytest.raises(ProviderError,match='Nothing has been sent'):c.complete('System','User')
    assert not called


@pytest.mark.parametrize('provider,base,path,tokenfield',[('openrouter','https://openrouter.ai/api/v1','/api/v1/chat/completions','max_tokens'),('openai-compatible','https://api.openai.com/v1','/v1/chat/completions','max_completion_tokens'),('anthropic','https://api.anthropic.com','/v1/messages','max_tokens'),('anthropic','https://api.anthropic.com/v1','/v1/messages','max_tokens')])
def test_completion_url_and_tokens(tmp_path,provider,base,path,tokenfield):
    v=Vault(tmp_path);v.set('llm','x',False);v.set('openrouter','x',False);seen=[]
    def handler(req):
        seen.append(req)
        return httpx.Response(200,json={'content':[{'type':'text','text':'Connected'}],'choices':[{'message':{'content':'Connected'},'finish_reason':'stop'}]})
    c=Clients(Settings(model='test',provider=provider,base_url=base,allow_cloud=True),v,transport=httpx.MockTransport(handler))
    assert c.complete('a','b')=='Connected'
    assert seen[0].url.path==path
    assert tokenfield in json.loads(seen[0].content)


def test_truncated_result_never_applied(tmp_path):
    v=Vault(tmp_path);v.set('openrouter','x',False)
    c=Clients(Settings(model='test',allow_cloud=True),v,transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[{'message':{'content':'Partial text'},'finish_reason':'length'}]})))
    with pytest.raises(ProviderError,match='truncated'):c.complete('a','b')


def test_error_body_not_exposed_and_timeout_not_retried(tmp_path):
    v=Vault(tmp_path);v.set('openrouter','x',False)
    c=Clients(Settings(model='test',allow_cloud=True),v,transport=httpx.MockTransport(lambda r:httpx.Response(401,text='SECRET-MUST-NOT-LEAK')))
    with pytest.raises(ProviderError) as e:c.complete('a','b')
    assert 'SECRET' not in str(e.value)
    calls=[]
    def handler(req):calls.append(req);raise httpx.ReadTimeout('timeout')
    c.transport=httpx.MockTransport(handler)
    with pytest.raises(ProviderError):c.complete('a','b')
    assert len(calls)==1


def test_actual_cost_not_fabricated():
    j=Job('test','draft');j.before_call('test',5);j.record_usage('test',{'input_tokens':1,'output_tokens':2},'test')
    assert j.usage['reported_cost']==0 and j.usage['unpriced_calls']==1
    j.before_call('test',5);j.record_usage('test',{'cost':float('nan')},'test')
    assert j.usage['reported_cost']==0 and j.usage['unpriced_calls']==2
