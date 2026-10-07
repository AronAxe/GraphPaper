"""Launch the unmodified, public Graphify CLI in its own process.

Packaged entry: GraphPaper.exe --graphify-worker ...
Source entry: python <this file> ...
This is not a second implementation of graph extraction or a private fork.
"""
from __future__ import annotations
import importlib.metadata
import json
import os
from pathlib import Path
import sys

PINNED_VERSION = '0.9.80'


def probe() -> dict:
    # Do not import graphify.llm for a probe: its tokenizer can initialize a
    # download. Availability checks must not spend tokens or fetch model data.
    required = ['graphifyy','openai','tiktoken','networkx','numpy','rapidfuzz','tree-sitter']
    versions={}; missing=[]
    for name in required:
        try: versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: missing.append(name)
    valid = not missing and versions.get('graphifyy') == PINNED_VERSION
    return {'available':valid,'package':'graphifyy','version':versions.get('graphifyy',''),
            'required_version':PINNED_VERSION,'dependencies':versions,'missing':missing,
            'distribution':'public PyPI, unmodified Graphify CLI',
            'error': '' if valid else 'Install the pinned graphifyy[openai] dependency, or use the complete Windows release.'}


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if sys.stdout is None: sys.stdout=open(os.devnull,'w',encoding='utf-8')
    if sys.stderr is None: sys.stderr=open(os.devnull,'w',encoding='utf-8')
    if args==['--graphpaper-probe']:
        result=probe()
        report=os.environ.get('GRAPHPAPER_GRAPHIFY_PROBE_FILE')
        if report: Path(report).write_text(json.dumps(result),encoding='utf-8')
        print(json.dumps(result),flush=True)
        return 0 if result['available'] else 2
    if not args or args[0]!='extract':
        raise SystemExit('The GraphPaper worker exposes Graphify extraction only; use a separate Graphify installation for other CLI actions.')
    status=probe()
    if not status['available']:
        print(json.dumps(status),file=sys.stderr); return 2
    # The worker only accepts an adapter-created loopback gateway. No provider
    # credentials are forwarded to this process.
    from urllib.parse import urlsplit
    base=urlsplit(os.environ.get('OPENAI_BASE_URL',''))
    if base.scheme!='http' or base.hostname!='127.0.0.1' or not base.port or base.path!='/v1' or not os.environ.get('OPENAI_API_KEY','').startswith('gp-graphify-'):
        raise SystemExit('Graphify worker requires its temporary GraphPaper gateway.')
    # Let the publicly released CLI parse its own documented flags and build its
    # own graph. sys.argv is necessary because upstream dispatch uses it.
    sys.argv=['graphify',*args]
    from graphify.__main__ import main as upstream_main
    value=upstream_main()
    return value if isinstance(value,int) else 0


if __name__=='__main__':
    raise SystemExit(main())
