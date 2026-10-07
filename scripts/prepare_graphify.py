"""Verify/install-time assets of the public pinned runtime for Windows releases.

No credential or user-project access. pip installs requirements-graphify.txt;
this script verifies that distribution and prepares tokenizer cache/licences.
"""
from __future__ import annotations
import hashlib
import base64
import importlib.metadata as md
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from graphpaper.graphify_worker import probe, PINNED_VERSION


def main():
    result=probe()
    if not result['available']: raise SystemExit(result['error'])
    verified={}
    for name in ['graphifyy','openai','tiktoken']:
        distribution=md.distribution(name)
        count=0
        for entry in distribution.files or []:
            if not entry.hash or entry.hash.mode != 'sha256': continue
            path=distribution.locate_file(entry)
            if not path.is_file(): raise SystemExit('Missing installed dependency file: '+str(entry))
            value=base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).decode().rstrip('=')
            if value != entry.hash.value: raise SystemExit('Installed dependency differs from its distribution RECORD: '+str(entry))
            count+=1
        if not count: raise SystemExit('Dependency has no verifiable distribution records: '+name)
        verified[name]=count
    result['distribution_record_files_verified']=verified
    vendor=ROOT/'vendor';vendor.mkdir(exist_ok=True)
    cache=vendor/'tiktoken';cache.mkdir(exist_ok=True)
    os.environ['TIKTOKEN_CACHE_DIR']=str(cache)
    import tiktoken
    assert tiktoken.get_encoding('cl100k_base').encode('GraphPaper public Graphify runtime')
    licenses=vendor/'graphify-licenses';licenses.mkdir(exist_ok=True)
    distributions=[]
    for distribution in sorted(md.distributions(),key=lambda d:d.metadata['Name'].lower()):
        name=distribution.metadata['Name']
        # Include installed dependency licence files; no private home paths,
        # installed account state, font files or executable provenance tokens.
        records=[]
        for file in distribution.files or []:
            lower=str(file).lower()
            if '.dist-info/' not in lower or not any(part in lower.split('/')[-1] for part in ('license','notice','copying')):
                continue
            path=distribution.locate_file(file)
            if not path.is_file() or path.stat().st_size>2_000_000: continue
            data=path.read_bytes()
            try: data.decode('utf-8')
            except UnicodeDecodeError: continue
            out=licenses/name/Path(str(file)).name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
            records.append({'file':out.relative_to(vendor).as_posix(),'sha256':hashlib.sha256(data).hexdigest()})
        distributions.append({'name':name,'version':distribution.version,'licenses':records})
    if not any(d['name'].lower()=='graphifyy' and d['licenses'] for d in distributions):
        raise SystemExit('Graphify licence was not found; do not publish a licence-incomplete package.')
    result.update({'source':'https://pypi.org/project/graphifyy/'+PINNED_VERSION+'/',
        'upstream':'https://github.com/Graphify-Labs/graphify','patched_upstream':False,
        'tokenizer_cache':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(cache.iterdir()) if p.is_file()],
        'distributions':distributions})
    (vendor/'graphify-runtime.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Public Graphify runtime verified:',PINNED_VERSION,'with tokenizer cache and licences.',flush=True)

if __name__=='__main__': main()
