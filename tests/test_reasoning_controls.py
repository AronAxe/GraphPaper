import json
from unittest.mock import Mock,patch
import httpx
import pytest
from graphpaper.models import Settings
from graphpaper.reasoning import normalize_model,selected_effort,request_fields,validate_effort
from graphpaper.providers import Clients
from graphpaper.secrets import Vault
from graphpaper.pipeline import Job


def test_codex_catalog_preserves_extended_levels():
    raw={'model':'fixture-sol','displayName':'Fixture','isDefault':True,'defaultReasoningEffort':'medium','supportedReasoningEfforts':[{'reasoningEffort':'low'},{'reasoningEffort':'high'},{'reasoningEffort':'ultra'}]}
    result=normalize_model(raw,'codex')
    assert result['reasoning_levels']==['low','high','ultra']
    assert result['is_default'] and result['default_reasoning']=='medium'
    validate_effort('ultra',result,'codex')
    with pytest.raises(ValueError):validate_effort('max',result,'codex')


def test_unknown_codex_model_does_not_invent_support():
    assert normalize_model({'id':'x'},'codex')['reasoning_levels']==[]
    with pytest.raises(ValueError):validate_effort('high',None,'codex')


def test_anthropic_capabilities_not_universal_options():
    raw={'id':'claude-test','capabilities':{'effort':{'supported':True,'low':{'supported':True},'high':{'supported':True},'max':{'supported':False}},'thinking':{'types':{'adaptive':{'supported':True}}}}}
    model=normalize_model(raw,'anthropic')
    assert model['reasoning_levels']==['low','high']
    fields=request_fields(Settings(provider='anthropic',reasoning_effort='high'),'writer',model)
    assert fields=={'output_config':{'effort':'high'},'thinking':{'type':'adaptive'}}
    with pytest.raises(ValueError):request_fields(Settings(provider='anthropic',reasoning_effort='max'),'writer',model)


def test_nonreasoning_openrouter_model_rejects_override():
    model=normalize_model({'id':'plain','supported_parameters':['temperature','max_tokens']},'openrouter')
    assert model['reasoning_levels']==[]
    with pytest.raises(ValueError):request_fields(Settings(reasoning_effort='high'),'writer',model)
    assert request_fields(Settings(),'writer',model)=={}


@pytest.mark.parametrize('provider,expected',[('openrouter',{'reasoning':{'effort':'high'},'provider':{'require_parameters':True}}),('openai-compatible',{'reasoning_effort':'high'})])
def test_provider_native_fields(provider,expected):
    assert request_fields(Settings(provider=provider,reasoning_effort='high'),'writer')==expected


def test_independent_roles():
    settings=Settings(reasoning_effort='high',editor_reasoning_effort='medium',extraction_reasoning_effort='low')
    assert [selected_effort(settings,r) for r in ['writer','editor','extraction']]==['high','medium','low']


@pytest.mark.parametrize('budget,cap',[(4096,4000),(4096,4096)])
def test_budget_must_leave_output_room(budget,cap):
    with pytest.raises(ValueError):request_fields(Settings(reasoning_effort='budget',reasoning_budget_tokens=budget),'writer',{'id':'b','reasoning_levels':[],'supports_budget':True},cap)


def test_budget_request_shape():
    settings=Settings(provider='anthropic',reasoning_effort='budget',reasoning_budget_tokens=2048)
    assert request_fields(settings,'writer',{'id':'b','supports_budget':True},5000)=={'thinking':{'type':'enabled','budget_tokens':2048}}


def test_compatible_request_and_receipt_include_selected_effort(tmp_path):
    seen=[]
    def handler(req):
        if req.method=='GET':return httpx.Response(200,json={'data':[{'id':'test','reasoning_efforts':['low','high']}]})
        seen.append(json.loads(req.content))
        return httpx.Response(200,json={'model':'test','choices':[{'message':{'content':'Result'},'finish_reason':'stop'}],'usage':{'prompt_tokens':5,'completion_tokens':2}})
    vault=Vault(tmp_path);vault.set('llm','fixture-key',False)
    job=Job('p','test')
    c=Clients(Settings(provider='openai-compatible',model='test',base_url='https://example.org/v1',allow_cloud=True,reasoning_effort='high'),vault,job,httpx.MockTransport(handler))
    assert c.complete('System','User')=='Result'
    assert seen[0]['reasoning_effort']=='high'
    assert job.receipts[-1]['reasoning_effort']=='high'


def test_codex_exec_receives_exact_effort_and_no_shell(tmp_path):
    from graphpaper.codex import Codex
    codex=object.__new__(Codex)
    codex.exe='fixture-codex.exe';codex.env={}
    codex.status=lambda:{'signed_in':True}
    codex.models=lambda:[{'id':'test','is_default':True,'reasoning_levels':['low','ultra']}]
    captured=[]
    def popen(args,**kwargs):
        from pathlib import Path
        captured.append((args,kwargs));Path(args[args.index('-o')+1]).write_text('Answer',encoding='utf-8')
        proc=Mock();proc.communicate.return_value=('{"type":"turn.completed","usage":{"input_tokens":8,"output_tokens":2}}\n','');proc.returncode=0;proc.poll.return_value=0
        return proc
    with patch('graphpaper.codex.subprocess.Popen',popen):
        assert codex.complete('System','User','test',reasoning_effort='ultra')=='Answer'
    assert 'model_reasoning_effort="ultra"' in captured[0][0]
    assert not captured[0][1].get('shell',False)


def test_reasoning_persists_settings_without_credentials(client):
    settings=Settings(provider='codex',reasoning_effort='ultra',editor_reasoning_effort='high',extraction_reasoning_effort='low').model_dump()
    result=client.put('/api/settings',json=settings)
    assert result.status_code==200
    assert client.get('/api/settings').json()['reasoning_effort']=='ultra'
    assert client.put('/api/settings',json={**settings,'reasoning_effort':'bad\nparameter'}).status_code==400
