from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys
from unittest.mock import Mock
import pytest
from graphpaper.models import Project, Source, Settings, VoiceProfile, PolishCandidate
from graphpaper.voice import metrics, fingerprint, sample_pack, voice_context, learn_voice
from graphpaper.polish import lint, mask, unmask, polish_draft
from graphpaper.author_web import extract_links
from graphpaper.pipeline import Job
from graphpaper.providers import ProviderError
from graphpaper.folders import safe_name
from .conftest import ScriptedClients


def sample_project():
    p=Project()
    p.sources=[Source(id='S1',title='My voice',role='voice',text='I write about things I can explain. Some sentences are short. Others take the time they need, because the point deserves a little more room. '*6)]
    return p


def test_old_project_migrates_with_new_defaults():
    p=Project.model_validate({'title':'Existing project'})
    assert p.auto_import and p.voice_profile.strength==75 and p.polish is None


def test_metrics_and_balanced_voice_samples():
    p=sample_project();p.sources[0].text='START '+('middle words '*5000)+' END'
    pack=sample_pack(p,300)
    assert pack[0]['excerpts'][0].startswith('START')
    assert pack[0]['excerpts'][-1].endswith(' END')
    assert sum(map(len,pack[0]['excerpts']))<=300
    assert metrics('One. Two words. Three short words?')['mean_sentence_words']==2


def test_voice_excludes_evidence_and_disabled_samples():
    p=sample_project()
    p.sources += [Source(id='S2',title='Facts',text='Not my voice.'),Source(id='S3',title='Disabled',text='Also not selected.',role='voice',enabled=False)]
    assert len(sample_pack(p))==1
    p.voice_profile.enabled=False
    assert voice_context(p)=={'enabled':False}


def test_voice_profile_staleness_and_off_switch():
    p=sample_project();p.voice_profile.instructions='Learned voice';p.voice_profile.sample_hash=fingerprint(p)
    assert voice_context(p)['instructions']=='Learned voice'
    p.sources[0].text+=' Changed.'
    assert voice_context(p)['profile_needs_refresh'] and not voice_context(p)['instructions']
    p.voice_profile.strength=0
    assert not voice_context(p)['enabled']


def test_learn_voice_persists_real_profile():
    c=Mock();c.settings=Settings();c.complete.return_value={'name':'Direct and dry','instructions':'Vary sentence length. Use exact verbs. Keep humor dry and occasional.','observations':['Sample-limited observations.']}
    p=sample_project();learn_voice(p,c,Job(p.id,'voice'))
    assert p.voice_profile.name=='Direct and dry' and p.voice_profile.sample_ids==['S1']
    assert p.voice_profile.sample_hash==fingerprint(p)
    assert 'factual beliefs or biography' in c.complete.call_args.args[1]


def test_learning_requires_enough_words():
    with pytest.raises(ValueError):learn_voice(Project(),Mock(),Job('p','voice'))
    p=sample_project();p.sources[0].text='Tiny sample.'
    with pytest.raises(ValueError,match='80'):learn_voice(p,Mock(),Job(p.id,'voice'))


@pytest.mark.parametrize('text',['A 12.5% change [S1].', '“Keep these exact words.”', 'Use `foo(x)` at https://example.org/test.', '```py\nx=2\n```', '> A quoted block.\n> Second line.', '[Readable label](https://example.org)'])
def test_protected_spans_roundtrip(text):
    encoded,spans=mask(text)
    assert unmask(encoded,spans)==text
    if spans:
        with pytest.raises(ValueError):unmask(encoded+next(iter(spans)),spans)
        with pytest.raises(ValueError):unmask(encoded.replace(next(iter(spans)),''),spans)


def test_lint_does_not_treat_quotation_as_authors_filler():
    report=lint('It is important to note that this works.\n\n“Let that sink in.”\n\n```\nLet that sink in.\n```')
    assert any(f['rule']=='filler' for f in report['findings'])
    assert not any(f['rule']=='empty-closer' for f in report['findings'])
    assert 'not AI-authorship detection' in report['note']


class EditClient:
    def complete(self,system,user,**kw):
        raw=json.loads(user)
        if kw.get('json_mode'):
            return {'meaning_preserved':True,'summary':'Filler removed.','warnings':[],'improvements':['More direct opening.']}
        return raw['draft'].replace('It is important to note that ','')


@pytest.mark.parametrize('mode',['humanize','deslop','both'])
def test_polish_is_reversible_proposal_with_protected_facts(mode):
    p=sample_project();p.draft='It is important to note that the count was 12.5% in “the test” [S1].'
    old=p.draft;polish_draft(p,EditClient(),Job(p.id,mode),mode)
    assert p.draft==old
    assert p.polish.draft=='the count was 12.5% in “the test” [S1].'
    assert p.polish.original_hash==hashlib.sha256(old.encode()).hexdigest()
    assert p.polish.before['count']>p.polish.after['count']


def test_polish_rejects_invented_number():
    class Invent(EditClient):
        def complete(self,system,user,**kw):
            answer=super().complete(system,user,**kw)
            return answer+' 9999' if isinstance(answer,str) else answer
    p=sample_project();p.draft='It is important to note that this is the complete original statement.'
    with pytest.raises(ProviderError,match='protected'):polish_draft(p,Invent(),Job(p.id,'humanize'),'humanize')
    assert p.polish is None


def test_accept_reject_and_stale_edit(client,app):
    p=Project(draft='Original text.')
    p.polish=PolishCandidate(mode='deslop',original_hash=hashlib.sha256(p.draft.encode()).hexdigest(),draft='Proposed text.',review={'meaning_preserved':True})
    app.state.store.create(p);base='/api/projects/'+p.id
    accepted=client.post(base+'/craft/accept',json={'version':0})
    assert accepted.status_code==200 and accepted.json()['draft']=='Proposed text.'
    assert any(v['draft']=='Original text.' for v in app.state.store.revisions(p.id))
    p=app.state.store.get(p.id);p.polish=PolishCandidate(mode='deslop',original_hash='obsolete',draft='Stale.');app.state.store.save(p,p.version)
    assert client.post(base+'/craft/accept',json={'version':p.version}).status_code==409
    assert app.state.store.get(p.id).draft=='Proposed text.'
    assert client.post(base+'/craft/discard',json={'version':p.version}).json()['polish'] is None


def test_fidelity_warning_needs_explicit_author_approval(client,app):
    p=Project(draft='Original text.');p.polish=PolishCandidate(mode='humanize',original_hash=hashlib.sha256(p.draft.encode()).hexdigest(),draft='Different.',review={'meaning_preserved':False})
    app.state.store.create(p);url='/api/projects/'+p.id+'/craft/accept'
    assert client.post(url,json={'version':0}).status_code==400
    assert client.post(url,json={'version':0,'acknowledge_warnings':True}).status_code==200


def test_project_folders_are_separate_and_automatically_role_mapped(client,app):
    p=client.post('/api/projects',json={'title':'One'}).json();q=client.post('/api/projects',json={'title':'Two'}).json()
    first=client.get('/api/projects/'+p['id']+'/workspace').json();second=client.get('/api/projects/'+q['id']+'/workspace').json()
    assert first['path']!=second['path']
    inbox=Path(first['inbox']);(inbox/'Voice'/'my-essay.md').write_text('My own sample text.',encoding='utf-8')
    (inbox/'Evidence'/'paper.txt').write_text('Factual material.',encoding='utf-8')
    result=client.post('/api/projects/'+p['id']+'/workspace/scan',json={'force':True}).json()
    assert result['changed'] and {s['role'] for s in result['project']['sources']}=={'voice','evidence'}
    assert not app.state.store.get(q['id']).sources
    assert app.state.store.get(p['id']).usage['calls']==0
    assert not client.post('/api/projects/'+p['id']+'/workspace/scan',json={'force':True}).json()['changed']


def test_inbox_requires_stable_file_then_updates_without_duplication(client):
    p=client.post('/api/projects',json={'title':'Inbox'}).json();base='/api/projects/'+p['id']
    info=client.get(base+'/workspace').json();file=Path(info['inbox'])/'new.txt';file.write_text('First content.',encoding='utf-8')
    assert not client.post(base+'/workspace/scan',json={}).json()['changed']
    r=client.post(base+'/workspace/scan',json={}).json();assert r['changed'];sid=r['project']['sources'][0]['id']
    file.write_text('Changed content in the same document.',encoding='utf-8')
    r=client.post(base+'/workspace/scan',json={'force':True}).json();assert len(r['project']['sources'])==1
    assert r['project']['sources'][0]['id']==sid
    file.unlink();r=client.post(base+'/workspace/scan',json={'force':True}).json()
    assert len(r['project']['sources'])==1 and r['events'][0]['status']=='retained'


def test_upload_retains_original_and_same_text_can_be_voice(client):
    p=client.post('/api/projects',json={'title':'Uploads'}).json();base='/api/projects/'+p['id']
    assert client.post(base+'/sources/file',files={'file':('notes.md',b'Same text.','text/markdown')},data={'role':'evidence'}).status_code==200
    r=client.post(base+'/sources/file',files={'file':('notes.md',b'Same text.','text/markdown')},data={'role':'voice'})
    assert r.status_code==200 and len(r.json()['sources'])==2
    folder=Path(client.get(base+'/workspace').json()['path'])/'Originals'
    assert len(list(folder.glob('*.md')))==2


def test_inbox_symlink_does_not_import_outside_project(client,tmp_path):
    p=client.post('/api/projects',json={'title':'Links'}).json();base='/api/projects/'+p['id']
    info=client.get(base+'/workspace').json();outside=tmp_path/'outside.txt';outside.write_text('Not project material.')
    try:(Path(info['inbox'])/'link.txt').symlink_to(outside)
    except (OSError,NotImplementedError):pytest.skip('Symlinks unavailable for this Windows account')
    result=client.post(base+'/workspace/scan',json={'force':True}).json()
    assert not result['project']['sources']


@pytest.mark.parametrize('name',['CON','NUL.txt','../../secret','A:B*?<>|.txt'])
def test_safe_windows_original_names(name):
    result=safe_name(name)
    assert '/' not in result and ':' not in result and not result.startswith('..')
    assert result.split('.')[0].upper() not in {'CON','NUL'}


def test_author_link_discovery_stays_on_site_and_excludes_login():
    html='<title>My essays</title><a href="/first">My first full essay</a><a href="https://evil.example/x">Elsewhere article</a><a href="/login">Please sign in</a><a href="/second#part">A second essay</a><a href="/first">Duplicate article</a>'
    links=extract_links(html,'https://writer.example/blog')
    assert {x['url'] for x in links}=={'https://writer.example/blog','https://writer.example/first','https://writer.example/second'}


def test_codex_setting_and_auth_url_allowlist():
    from graphpaper.codex import safe_login_url
    assert Settings(provider='codex').provider=='codex'
    assert safe_login_url('https://auth.openai.com/authorize?state=abc')
    assert safe_login_url('https://chatgpt.com/oauth')
    assert not safe_login_url('https://auth.openai.com.evil.test/')
    assert not safe_login_url('http://auth.openai.com/')
    assert not safe_login_url('https://evil@auth.openai.com/')


def test_codex_provider_uses_bridge_not_api_transport(tmp_path,monkeypatch):
    from graphpaper.providers import Clients
    from graphpaper.secrets import Vault
    bridge=Mock();bridge.complete.return_value='{"ok":true}'
    monkeypatch.setattr('graphpaper.codex.get_codex',lambda *a:bridge)
    c=Clients(Settings(provider='codex',allow_cloud=True,model=''),Vault(tmp_path))
    c.post=Mock(side_effect=AssertionError('Must not call API'))
    assert c.complete('instructions','data',json_mode=True)=={'ok':True}
    c.post.assert_not_called()
    assert 'JSON' in bridge.complete.call_args.args[0]


def test_codex_still_requires_explicit_cloud_consent(tmp_path,monkeypatch):
    from graphpaper.providers import Clients
    from graphpaper.secrets import Vault
    bridge=Mock();monkeypatch.setattr('graphpaper.codex.get_codex',lambda *a:bridge)
    c=Clients(Settings(provider='codex',allow_cloud=False),Vault(tmp_path))
    with pytest.raises(ProviderError):c.complete('system','private text')
    bridge.complete.assert_not_called()
