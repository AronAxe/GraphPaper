"""Fetch the official Windows Codex runtime, verify GitHub's asset digest, keep provenance."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request
import urllib.error
from urllib.parse import urlsplit
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def get(url):
    headers={'User-Agent':'GraphPaper-release-builder','Accept':'application/vnd.github+json'}
    if urlsplit(url).hostname=='api.github.com' and os.getenv('GITHUB_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    return urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=90)


def main():
    version=os.getenv('CODEX_RELEASE_TAG','rust-v0.160.1')
    api='https://api.github.com/repos/openai/codex/releases/'+('latest' if version=='latest' else 'tags/'+version)
    with get(api) as r:release=json.load(r)
    if release.get('prerelease') or release.get('draft'):
        raise ValueError('Only an official stable Codex release may be bundled.')
    assets=release['assets'];tag=release['tag_name']
    destination=ROOT/'vendor';destination.mkdir(exist_ok=True)
    provenance={'repository':'openai/codex','release':tag,'release_url':release['html_url'],'assets':[]}
    for stem,required in [('codex',True),('codex-command-runner',False),('codex-windows-sandbox-setup',False)]:
        matches=[a for a in assets if a['name'].startswith(stem+'-x86_64-pc-windows-msvc') and a['name'].endswith(('.tar.gz','.zip'))]
        if not matches:
            if required:raise ValueError('Official Windows x64 Codex archive not found.')
            continue
        asset=sorted(matches,key=lambda a:a['name'])[0]
        expected=asset.get('digest','')
        if not expected.startswith('sha256:'):
            raise ValueError('GitHub did not supply a SHA-256 digest for '+asset['name'])
        url=asset['browser_download_url']
        if not url.startswith('https://github.com/openai/codex/releases/download/'):
            raise ValueError('Unexpected release download URL.')
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/asset['name'];hasher=hashlib.sha256();size=0
            with get(url) as source,archive.open('wb') as out:
                while chunk:=source.read(1024*1024):
                    size+=len(chunk)
                    if size>300*1024*1024:raise ValueError('Runtime archive exceeds 300 MB.')
                    hasher.update(chunk);out.write(chunk)
            if hasher.hexdigest()!=expected.split(':',1)[1]:raise ValueError('Codex runtime checksum mismatch.')
            if archive.name.endswith('.zip'):
                with zipfile.ZipFile(archive) as z:
                    names=[n for n in z.namelist() if n.lower().endswith('.exe') and Path(n).name.startswith(stem)]
                    if not names:raise ValueError('Missing runtime executable.')
                    data=z.read(names[0])
            else:
                with tarfile.open(archive,'r:gz') as t:
                    members=[m for m in t.getmembers() if m.isfile() and m.name.lower().endswith('.exe') and Path(m.name).name.startswith(stem)]
                    if not members:raise ValueError('Missing runtime executable.')
                    with t.extractfile(members[0]) as source:data=source.read(400*1024*1024+1)
            if len(data)>400*1024*1024:raise ValueError('Expanded runtime exceeds limit.')
            (destination/(stem+'.exe')).write_bytes(data)
        provenance['assets'].append({'name':asset['name'],'download_url':url,'archive_sha256':expected.split(':',1)[1],
                                      'executable':stem+'.exe','executable_sha256':hashlib.sha256(data).hexdigest()})
    for filename in ['LICENSE','NOTICE']:
        try:
            with get(f'https://raw.githubusercontent.com/openai/codex/{tag}/{filename}') as r:text=r.read(100_000)
            (destination/(filename+'.Codex.txt')).write_bytes(text)
        except urllib.error.HTTPError as e:
            if filename=='LICENSE' or e.code!=404:raise
    (destination/'codex-release.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(provenance,indent=2))

if __name__=='__main__':main()
