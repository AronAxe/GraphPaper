"""Actual public Graphify CLI extraction, using GraphPaper's configured inference.

Graphify builds the graph in a child process. A job-scoped loopback gateway
supplies text completions, including official Codex/ChatGPT OAuth completions.
No private Graphify fork or API-key fallback is required.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time

from .graph import import_graph
from .models import Evidence, now
from .providers import ProviderError, Cancelled
from .graphify_gateway import Gateway, JobScope
from .graphify_process import OwnedProcess
from .graphify_runtime import check_runtime, isolated_environment
from .graphify_worker import PINNED_VERSION

MAX_GRAPH_BYTES=20_000_000


def validate_graph(raw):
    """Fail closed on malformed/dangling graphs; never drop broken rows silently."""
    if not isinstance(raw,dict) or not isinstance(raw.get('nodes'),list):
        raise ValueError('Graphify output must contain a nodes array.')
    edges=raw.get('edges',raw.get('links'))
    if not isinstance(edges,list): raise ValueError('Graphify output must contain edges or links.')
    if not raw['nodes']: raise ValueError('Graphify returned an empty graph; the previous graph was preserved.')
    if len(raw['nodes'])>5000 or len(edges)>20000: raise ValueError('Graphify output exceeds the graph size limits.')
    ids=set()
    for node in raw['nodes']:
        if not isinstance(node,dict) or not isinstance(node.get('id'),(str,int)) or isinstance(node['id'],bool):
            raise ValueError('Graphify returned an invalid node ID.')
        ident=str(node['id'])
        if not ident or len(ident)>400 or ident in ids: raise ValueError('Graphify node IDs must be unique and nonempty.')
        label=node.get('label',node.get('name',ident))
        if not isinstance(label,str) or not label.strip(): raise ValueError('Graphify returned an empty/nontext node label.')
        ids.add(ident)
    for edge in edges:
        if not isinstance(edge,dict) or not isinstance(edge.get('source'),(str,int)) or not isinstance(edge.get('target'),(str,int)):
            raise ValueError('Graphify returned an invalid edge.')
        if str(edge['source']) not in ids or str(edge['target']) not in ids:
            raise ValueError('Graphify returned a dangling edge; no partial graph was installed.')
    return raw


def load_graph(path: Path, workspace: Path):
    if not path.is_file(): raise ValueError('Graphify finished without graph.json; the previous graph was preserved.')
    if path.is_symlink() or workspace.resolve() not in path.resolve().parents:
        raise ValueError('Graphify output escaped its isolated workspace.')
    if path.stat().st_size>MAX_GRAPH_BYTES: raise ValueError('Graphify output exceeds 20 MB.')
    with path.open('rb') as stream: data=stream.read(MAX_GRAPH_BYTES+1)
    if len(data)>MAX_GRAPH_BYTES: raise ValueError('Graphify output exceeds 20 MB.')
    def invalid(_): raise ValueError('Graphify output contains a non-finite number.')
    try: raw=json.loads(data.decode('utf-8-sig'),parse_constant=invalid)
    except (UnicodeError,json.JSONDecodeError,RecursionError) as exc:
        raise ValueError('Graphify returned malformed graph JSON; the previous graph was preserved.') from exc
    return validate_graph(raw)


def source_refs(item, files, input_root):
    values=[]
    if isinstance(item.get('source_file'),str): values.append(item['source_file'])
    if isinstance(item.get('source_files'),list): values += [s for s in item['source_files'] if isinstance(s,str)]
    result=[]
    for value in values:
        try:
            p=Path(value.replace('\\','/'))
            resolved=(input_root/p).resolve() if not p.is_absolute() else p.resolve()
            if resolved.parent==input_root.resolve() and resolved.name in files:
                result.append(files[resolved.name].id)
        except (ValueError,OSError): pass
    return list(dict.fromkeys(result))


def attach_provenance(graph,raw,files,input_root):
    sources={s.id:s for s in files.values()}
    def apply(target,item,extra_ids=()):
        target.source_ids=list(dict.fromkeys(source_refs(item,files,input_root)+list(extra_ids)))
        # File attribution alone is not a quote or evidence of entailment.
        candidates=item.get('evidence',[])
        if isinstance(candidates,str): candidates=[{'quote':candidates}]
        if not isinstance(candidates,list): candidates=[]
        if isinstance(item.get('quote'),str): candidates=[*candidates,{'quote':item['quote']}]
        for candidate in candidates[:10]:
            quote=candidate.get('quote','') if isinstance(candidate,dict) else ''
            if not isinstance(quote,str) or not quote.strip() or len(quote)>3000: continue
            for sid in target.source_ids:
                s=sources[sid];pos=s.text.find(quote)
                if pos>=0:
                    target.evidence.append(Evidence(source_id=sid,quote=quote,start=pos,end=pos+len(quote),verified=True))
                    break
        # Graphify's EXTRACTED/INFERRED labels remain external interpretations;
        # even exact attribution does not establish the truth of an edge.
        target.status='imported'
    nodes={n.id:n for n in graph.nodes}
    for item in raw['nodes']: apply(nodes[str(item['id'])],item)
    edge_lookup={}
    for e in graph.edges: edge_lookup.setdefault((e.source,e.target),[]).append(e)
    for item in raw.get('edges',raw.get('links',[])):
        a,b=str(item['source']),str(item['target'])
        if a==b: continue
        match=edge_lookup.get((a,b),[])
        if match:
            target=match.pop(0)
            apply(target,item,[*nodes[a].source_ids,*nodes[b].source_ids])


def run_graphify(project,clients,job):
    # Consent is checked against the actual selected provider, not a stale API
    # base URL when the user has selected Codex OAuth.
    if clients.settings.provider=='codex': clients.check('https://chatgpt.com')
    else: clients.check(clients.settings.base_url)
    runtime=check_runtime(clients.settings.graphify_executable)
    if not runtime['available']: raise ValueError(runtime['error'])
    sources=[s for s in project.sources if s.enabled and s.role!='voice']
    if not sources: raise ValueError('No enabled non-voice sources are available for Graphify.')
    if sum(len(s.text.encode('utf-8')) for s in sources)>64_000_000:
        raise ValueError('Graphify input exceeds the 64 MB text limit. Split the project; no sources were truncated.')
    scope=JobScope(job,clients.settings.graphify_timeout_seconds)
    routed=copy.copy(clients);routed.job=scope
    # Validate selected effort through the real provider's existing model route.
    # Native completions will check again immediately before a billed request.
    if clients.settings.provider=='codex':
        from .codex import get_codex
        from .reasoning import validate_effort
        codex=get_codex(clients.vault.path.parent,clients.settings.codex_executable)
        if not codex.status()['signed_in']: raise ProviderError('Sign in with ChatGPT before running external Graphify with Codex.')
        model=clients.settings.extraction_model or clients.settings.model
        catalog=codex.models()
        info=next((m for m in catalog if m['id']==model),None) if model else next((m for m in catalog if m.get('is_default')),None)
        if model and info is None: raise ProviderError('The extraction model was not found in the Codex catalog. Refresh models in Connections.')
        validate_effort(clients.settings.extraction_reasoning_effort,info,'codex')
    with tempfile.TemporaryDirectory(prefix='graphpaper-graphify-') as temp:
        root=Path(temp);input_root=root/'input';input_root.mkdir();output=root/'output'
        files={}
        for i,s in enumerate(sources,1):
            filename=f'source-{i:04d}.md';files[filename]=s
            (input_root/filename).write_text(f'# {s.title}\n\nSource ID: {s.id}\nRole: {s.role}\n\n{s.text}\n',encoding='utf-8',newline='\n')
        with Gateway(routed,scope) as gateway:
            env=isolated_environment(root/'home')
            env.update({'OPENAI_API_KEY':gateway.token,'OPENAI_BASE_URL':gateway.url,'OPENAI_MODEL':gateway.model,
                'GRAPHIFY_OPENAI_MODEL':gateway.model,'GRAPHIFY_OUT':str(output),
                'GRAPHIFY_MAX_OUTPUT_TOKENS':str(clients.settings.max_output_tokens),
                'GRAPHIFY_API_TIMEOUT':str(clients.settings.request_timeout_seconds+10)})
            args=[*runtime['command'],'extract',str(input_root),'--backend','openai','--model',gateway.model,
                '--mode','deep','--no-viz','--no-cluster','--out',str(output),
                '--token-budget',str(clients.settings.graphify_chunk_tokens),'--max-concurrency','1','--max-workers','1',
                '--api-timeout',str(clients.settings.request_timeout_seconds+10)]
            scope.note(f'Running public Graphify {PINNED_VERSION} through {clients.settings.provider}; using the extraction model and reasoning setting. Requests count toward this job budget.',5)
            # External stdout is not an authority or a place to return secrets.
            # It is consumed and discarded to avoid blocking or unbounded logs.
            with OwnedProcess(args,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) as proc:
                while proc.poll() is None:
                    scope.check()
                    if gateway.error: raise gateway.error
                    time.sleep(.1)
                scope.check()
                if gateway.error: raise gateway.error
                if proc.returncode:
                    raise ValueError('Graphify failed before producing a complete graph. Verify the pinned runtime and selected model; no old graph was replaced and no Native fallback ran.')
            if not gateway.completed: raise ValueError('Graphify made no successful model requests. The empty/unverified extraction was not installed.')
            raw=load_graph(output/'graph.json',root)
            graph=import_graph(raw)
            attach_provenance(graph,raw,files,input_root)
            graph.engine=f'Graphify {PINNED_VERSION} via {clients.settings.provider}'
            graph.built=now()
            graph.coverage={'engine':'external_graphify','runtime_version':runtime['version'],'runtime_selection':runtime['selection'],
                'sources':len(sources),'characters':sum(len(s.text) for s in sources),
                'source_ids':[s.id for s in sources],
                'model':clients.settings.extraction_model or clients.settings.model or 'provider default',
                'reasoning_effort':clients.settings.extraction_reasoning_effort,
                'model_requests':gateway.completed,'requests':list(gateway.receipts),
                'scope':'Enabled source text exported in full; Graphify controls chunking and extraction. No extra Native extraction pass was run.'}
            graph.warnings=['Graphify relationships are externally generated interpretations. Source-file links and exact quotation matches establish attribution, not truth.']
            graph.warnings.extend(dict.fromkeys(w for source in sources for w in source.warnings))
            graph.warnings.extend(dict.fromkeys(w for s in sources for w in s.warnings))
            if raw.get('hyperedges'):
                graph.coverage['hyperedge_count']=len(raw['hyperedges'])
                graph.warnings.append('This view displays pairwise edges. Graphify hyperedges are not displayed as independent hyperedge objects.')
            return graph
