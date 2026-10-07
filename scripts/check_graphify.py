"""Check the real external Graphify action in an isolated synthetic project.

Default: deterministic inference, real public Graphify process. --live-codex
requires an explicitly selected, already signed-in official Codex profile.
No credentials are read/exported by this script; only Codex accesses its own
profile. No installed project database or saved GraphPaper settings are opened.
"""
from __future__ import annotations
import argparse
import json
import platform
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from graphpaper.server import create_app
from graphpaper.providers import Clients
from graphpaper.models import Settings
from graphpaper.graphify_runtime import check_runtime
from graphpaper.codex import close_all
from tests.graphify_fixtures import FixtureClients,fixture_settings,add_sources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable',type=Path,help='Use the Graphify worker bundled in this compiled GraphPaper.exe')
    parser.add_argument('--live-codex',action='store_true')
    parser.add_argument('--codex-profile-root',type=Path,help='Directory containing the official codex-account profile; used only for authentication')
    parser.add_argument('--codex-executable',type=Path)
    parser.add_argument('--model',default='')
    parser.add_argument('--effort',default='low')
    parser.add_argument('--out',type=Path,default=ROOT/'test-results/graphify-action.json')
    args=parser.parse_args()
    if args.live_codex and (not args.codex_profile_root or not args.codex_executable):
        parser.error('Live mode needs explicit official account and executable locations.')
    report={'platform':platform.system(),'python':platform.python_version(),'packaged_graphify_worker':bool(args.executable),
        'real_graphify_process':True,'live_codex':args.live_codex,'synthetic_project':True,'ok':False}
    patches=[]
    if args.executable:
        command=[str(args.executable.resolve()),'--graphify-worker']
        patches.append(patch('graphpaper.graphify_runtime.worker_command',lambda:command))
    for context in patches:context.start()
    try:
        runtime=check_runtime()
        assert runtime['available'],runtime
        report['graphify_version']=runtime['version']
        with tempfile.TemporaryDirectory(prefix='GraphPaper-isolated-extraction-') as folder:
            app=create_app(Path(folder))
            settings=fixture_settings()
            if args.live_codex:
                settings=Settings(provider='codex',model=args.model,extraction_model=args.model,
                    extraction_reasoning_effort=args.effort,graph_engine='graphify',allow_cloud=True,
                    codex_executable=str(args.codex_executable.resolve()),max_calls=5,max_output_tokens=8000,
                    request_timeout_seconds=300,graphify_timeout_seconds=600)
                class AccountLocation:
                    path=args.codex_profile_root.resolve()/'credentials.dpapi'
                    def get(self,name):return ''
                app.state.runner.clients_factory=lambda s,v,j:Clients(s,AccountLocation(),j)
            else:
                FixtureClients.seen=[]
                app.state.runner.clients_factory=FixtureClients
            app.state.store.set_settings(settings.model_dump())
            try:
                with TestClient(app) as client:
                    client.get('/');client.headers['X-GraphPaper']='1'
                    p=client.post('/api/projects',json={'title':'Synthetic external Graphify acceptance test'}).json()
                    add_sources(client,p['id'])
                    response=client.post('/api/projects/'+p['id']+'/jobs',json={'action':'graph'})
                    assert response.status_code==200,response.text
                    jid=response.json()['id'];deadline=time.monotonic()+660;last=''
                    while time.monotonic()<deadline:
                        job=client.get('/api/jobs/'+jid).json()
                        message=job['messages'][-1]['text'] if job['messages'] else job['state']
                        if message!=last:print(message,flush=True);last=message
                        if job['state'] not in {'queued','running'}:break
                        time.sleep(.3)
                    else:
                        client.post('/api/jobs/'+jid+'/cancel')
                        raise RuntimeError('Isolated test exceeded its deadline')
                    report['job_state']=job['state'];report['usage']=job['usage']
                    if job['state']!='completed':raise RuntimeError(job['error'])
                    p=client.get('/api/projects/'+p['id']).json();graph=p['graph']
                    assert graph['coverage']['engine']=='external_graphify'
                    assert graph['nodes'] and graph['edges']
                    assert graph['coverage']['sources']==2 and len(p['sources'])==3
                    assert graph['coverage']['model_requests']==p['usage']['calls']
                    assert app.state.store.settings()==settings.model_dump()
                    report.update({'nodes':len(graph['nodes']),'edges':len(graph['edges']),'coverage':graph['coverage'],
                        'source_links':sorted({sid for n in graph['nodes'] for sid in n['source_ids']}),
                        'voice_source_excluded':True,'no_extra_native_pass':True,'settings_preserved':True,'ok':True})
            finally:
                for job in app.state.runner.jobs.values():job.cancel.set()
                app.state.runner.pool.shutdown(wait=True,cancel_futures=True)
                close_all()
    except Exception as exc:
        report['error']=str(exc)
        raise
    finally:
        for context in reversed(patches):context.stop()
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
