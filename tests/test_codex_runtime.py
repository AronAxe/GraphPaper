"""Exercise the actual subprocess/JSON-RPC bridge with a local Codex test double."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock
import pytest
from graphpaper.codex import Codex
from graphpaper.pipeline import Job
from graphpaper.providers import ProviderError

FAKE = r'''
import json, os, pathlib, sys
home=pathlib.Path(os.environ['CODEX_HOME'])
if 'app-server' in sys.argv:
    for line in sys.stdin:
        d=json.loads(line)
        if 'id' not in d: continue
        method=d.get('method')
        if method=='account/read':
            result={'account':{'type':'chatgpt','email':'author@example.test','planType':'pro'} if (home/'signed-in.test').exists() else None}
        elif method=='account/login/start':
            (home/'signed-in.test').write_text('test session')
            result={'authUrl':'https://auth.openai.com/authorize?state=test','loginId':'test-login'}
        elif method=='account/logout':
            (home/'signed-in.test').unlink(missing_ok=True); result={}
        elif method=='model/list':
            result={'data':[{'id':'test-model','model':'test-model','displayName':'Test model'}]}
        else: result={}
        print(json.dumps({'id':d['id'],'result':result}),flush=True)
else:
    prompt=sys.stdin.read()
    (home/'exec-args.test').write_text(json.dumps(sys.argv))
    (home/'input.test').write_text(prompt)
    output=pathlib.Path(sys.argv[sys.argv.index('-o')+1])
    output.write_text('A complete piece of test prose.',encoding='utf-8')
    print(json.dumps({'type':'turn.completed','usage':{'input_tokens':42,'output_tokens':8}}))
'''


@pytest.fixture
def runtime(tmp_path,monkeypatch):
    script=tmp_path/'fake_codex.py';script.write_text(FAKE,encoding='utf-8')
    real=subprocess.Popen
    def launch(args,*a,**kw):
        if args[0]==str(script.resolve()):args=[sys.executable,str(script),*args[1:]]
        return real(args,*a,**kw)
    monkeypatch.setattr(subprocess,'Popen',launch)
    monkeypatch.setenv('OPENAI_API_KEY','do-not-inherit-this-key')
    monkeypatch.setattr('webbrowser.open',Mock(return_value=True))
    c=Codex(tmp_path,str(script))
    yield c
    c.close()


def test_browser_login_exec_usage_and_logout(runtime):
    assert not runtime.status()['signed_in']
    assert runtime.login()['started']
    assert runtime.status()['signed_in']
    assert runtime.models()[0]['id']=='test-model'
    job=Job('p','draft')
    assert runtime.complete('Write prose.','About the sea.','test-model',job)=='A complete piece of test prose.'
    assert job.usage['calls']==1 and job.usage['input_tokens']==42 and job.usage['output_tokens']==8
    assert job.usage['reported_cost']==0 and job.usage['unpriced_calls']==1
    args=json.loads((runtime.home/'exec-args.test').read_text())
    assert '--ephemeral' in args and 'read-only' in args and 'features.shell_tool=false' in args
    assert 'OPENAI_API_KEY' not in runtime.env
    assert runtime.home.name=='codex-account'
    runtime.logout()
    assert not runtime.status()['signed_in']


def test_codex_generation_refuses_unsigned_account(runtime):
    with pytest.raises(ProviderError,match='Sign in'):runtime.complete('system','data','')
    assert not (runtime.home/'exec-args.test').exists()
