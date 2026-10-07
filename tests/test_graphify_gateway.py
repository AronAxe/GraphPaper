"""The local extraction endpoint has a deliberately small request contract."""
from types import SimpleNamespace
import httpx
import pytest
from graphpaper.models import Settings
from graphpaper.graphify_gateway import Gateway,JobScope
from graphpaper.pipeline import Job
from graphpaper.secrets import Vault
from .graphify_fixtures import FixtureClients,fixture_settings


def parser():
    gateway=object.__new__(Gateway)
    gateway.model='graphpaper-extraction'
    gateway.clients=SimpleNamespace(settings=Settings())
    return gateway


def body():
    return {'model':'graphpaper-extraction','messages':[{'role':'system','content':'Extract a graph.'},{'role':'user','content':'Synthetic source text.'}],'stream':False}


@pytest.mark.parametrize('replacement',[{'model':'different-model'},{'stream':True},{'messages':[]},{'messages':[{'role':'user','content':'Text'}]},{'tools':[{'type':'function'}]},{'messages':[{'role':'system','content':'Text'},{'role':'user','content':[{'type':'image_url'}]}]}])
def test_only_the_fixed_text_extraction_contract_is_accepted(replacement):
    with pytest.raises(ValueError):parser().parse({**body(),**replacement})


def test_text_block_input_is_supported():
    value=body();value['messages'][1]['content']=[{'type':'text','text':'First text'},{'type':'text','text':'Second text'}]
    assert parser().parse(value)==('Extract a graph.','First text\nSecond text')


def test_job_auth_and_real_model_selection(tmp_path):
    FixtureClients.seen=[]
    job=Job('synthetic','graph');scope=JobScope(job,15)
    clients=FixtureClients(fixture_settings(),Vault(tmp_path),scope)
    with Gateway(clients,scope) as gateway:
        address=gateway.url+'/chat/completions'
        assert httpx.post(address,json=body()).status_code==401
        assert not FixtureClients.seen
        response=httpx.post(address,json=body(),headers={'Authorization':'Bearer '+gateway.token},timeout=10)
        assert response.status_code==200
        assert response.json()['usage']['total_tokens']==210
        assert gateway.completed==1 and job.usage['calls']==1
        assert gateway.receipts[0]['model']=='extract-fixture'
        assert gateway.receipts[0]['reasoning_effort']=='high'


def test_provider_failure_is_not_retried(tmp_path):
    class Failed(FixtureClients):behavior='error'
    job=Job('synthetic','graph');scope=JobScope(job,15)
    with Gateway(Failed(fixture_settings(),Vault(tmp_path),scope),scope) as gateway:
        for _ in range(2):
            response=httpx.post(gateway.url+'/chat/completions',json=body(),headers={'Authorization':'Bearer '+gateway.token},timeout=10)
            assert response.status_code==400
        assert job.usage['calls']==1
        assert gateway.error is not None
