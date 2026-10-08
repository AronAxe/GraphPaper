import copy
import json
import httpx
import pytest
from graphpaper.jev_budget import plan,compact_state,wire_bytes,intern,MAX_BYTES
from graphpaper.providers import Clients,ProviderError
from graphpaper.models import Settings
from graphpaper.pipeline import Job
from graphpaper.secrets import Vault


def questions(n=4):
    return {f'c{i}_fit':{'type':'noul','instructions':f'Evaluate candidate candidate_{i} only.'} for i in range(n)}


def test_raw_voice_pieces_are_not_in_decisions():
    original={'author_voice':{'enabled':True,'instructions':'Use strong language. Keep the sarcasm.','samples':[{'excerpts':['PRIVATE_TRAINING_ARTICLE'*20000]}]},'brief':{'direction':'Preserve my forceful thesis'},'candidates':[{'id':'candidate_0','description':'An argument'}]}
    before=copy.deepcopy(original)
    batches=plan(original,questions(1),'jev-latest')
    assert 'PRIVATE_TRAINING_ARTICLE' not in json.dumps([b.state for b in batches])
    assert batches[0].state['author_voice']['graph']['nodes']
    assert 'strong language' in json.dumps(batches[0].state)
    assert original==before


def test_unicode_candidate_batches_keep_keys_ids_and_complete_text():
    candidates=[{'id':f'candidate_{i}','description':('猫'+str(i))*3500} for i in range(8)]
    qs=questions(8)
    batches=plan({'candidates':candidates,'editorial_contract':{'thesis':'A categorical moral judgment'}},qs,'jev-latest')
    assert len(batches)>1
    recovered={}
    for b in batches:
        assert wire_bytes({'model':'jev-latest','state':b.state,'questions':b.questions})<=MAX_BYTES
        for k in b.questions:
            index=int(k.split('_')[0][1:]);match=next(x for x in b.state['candidates'] if x['id']==f'candidate_{index}')
            assert match==candidates[index];recovered[k]=True
    assert set(recovered)==set(qs)


def test_question_count_and_serialized_envelope_are_bounded():
    qs={f'q{i}':{'type':'noul','instructions':'Read the same supplied material.'} for i in range(225)}
    batches=plan({'text':'material'},qs,'jev-latest')
    assert len(batches)==3
    assert sum(len(b.questions) for b in batches)==225
    assert all(len(b.questions)<=100 for b in batches)


def test_repeated_text_uses_lossless_references_not_excerpts():
    value='Do not remove the negation. '*3000
    original={'a':value,'b':value,'c':value}
    packed=intern(original)
    assert len(packed['texts'])==1
    assert packed['texts'][packed['state']['a']['text_ref']]==value
    assert original['a']==value


@pytest.mark.parametrize('route',['typesafe','openrouter'])
def test_actual_transport_combines_typed_answers_and_records_batch_cost(tmp_path,route):
    vault=Vault(tmp_path);vault.set(route,'synthetic-key',False);seen=[]
    def handler(request):
        data=json.loads(request.content);seen.append(data)
        assert len(request.content)<=MAX_BYTES
        return httpx.Response(200,json={'answers':{k:{'type':'noul','noul':.81} for k in data['questions']},'usage':{'input_tokens':10,'output_tokens':3,'cost':.0001}})
    job=Job('p','angles')
    c=Clients(Settings(model='fixture',allow_cloud=True,jev_provider=route,max_calls=20),vault,job,httpx.MockTransport(handler))
    state={'candidates':[{'id':f'candidate_{i}','description':str(i)*14000} for i in range(8)]}
    answers=c.decide(state,questions(8))
    assert len(answers)==8 and len(seen)>1
    assert job.usage['calls']==len(seen)
    assert all(r['request_bytes']<=MAX_BYTES for r in job.receipts)
    assert all(r['decision_batches']==len(seen) for r in job.receipts)
    assert job.usage['reported_cost']==pytest.approx(.0001*len(seen))


def test_indivisible_oversize_preserves_work_and_makes_no_request(tmp_path):
    vault=Vault(tmp_path);vault.set('typesafe','synthetic-key',False)
    called=[];job=Job('p','review')
    c=Clients(Settings(model='fixture',allow_cloud=True,jev_provider='typesafe'),vault,job,httpx.MockTransport(lambda r:called.append(r)))
    assert c.decide({'draft':'Unique manuscript '*10000},{'prefer_revision':{'type':'noul','instructions':'Compare the whole draft'}}) is None
    assert not called and job.usage['calls']==0
    assert 'unscored' in job.messages[-1]['text']


def test_budget_preflight_does_not_spend_a_partial_batch(tmp_path):
    vault=Vault(tmp_path);vault.set('typesafe','synthetic-key',False)
    job=Job('p','angles');job.usage['calls']=4
    c=Clients(Settings(model='x',allow_cloud=True,jev_provider='typesafe',max_calls=5),vault,job)
    assert c.decide({'candidates':[{'id':f'candidate_{i}','text':str(i)*30000} for i in range(4)]},questions()) is None
    assert job.usage['calls']==4


def test_off_remains_off_and_fabricated_answers_are_rejected(tmp_path):
    vault=Vault(tmp_path)
    assert Clients(Settings(jev_provider='off'),vault).decide('x',{}) is None
    vault.set('typesafe','x',False)
    c=Clients(Settings(allow_cloud=True,jev_provider='typesafe'),vault,transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'answers':{'q':{'type':'noul','noul':True}}})))
    with pytest.raises(ProviderError):c.decide('x',{'q':{'type':'noul','instructions':'Check'}})


def test_choice_vocabulary_and_missing_answer_are_not_relaxed(tmp_path):
    vault=Vault(tmp_path);vault.set('typesafe','x',False)
    c=Clients(Settings(allow_cloud=True,jev_provider='typesafe'),vault,transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'answers':{'q':{'type':'choice','choice':'invented'}}})))
    with pytest.raises(ProviderError):c.decide('x',{'q':{'type':'choice','instructions':'Choose','criteria':{'a':'A','b':'B'}}})
