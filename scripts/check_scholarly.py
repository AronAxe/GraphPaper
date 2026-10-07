"""Opt-in live metadata smoke test. Uses a public query, no model calls or saved keys."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from graphpaper.science_models import ResearchPlan
from graphpaper.scholarly import ScholarlyClient,NAMES


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',default=str(ROOT/'test-results/scholarly-live.json'))
    args=parser.parse_args()
    plan=ResearchPlan(question='working memory',per_database=2)
    client=ScholarlyClient()
    checks=[]
    for db in NAMES:
        print('LIVE METADATA',db,flush=True)
        try:
            records,log=client.search(db,'working memory',plan)
            checks.append({'database':db,'ok':True,'retrieved':len(records),'total_hits':log['total_hits'],
                'query':log['query'],'capped':log['truncated'],'identifiers':[{'doi':r.metadata.doi,'pmid':r.metadata.pmid,'arxiv':r.metadata.arxiv_id} for r in records],
                'scopes':[r.metadata.content_scope for r in records]})
        except Exception as exc:
            checks.append({'database':db,'ok':False,'error':type(exc).__name__+': '+str(exc)[:400]})
        print(json.dumps(checks[-1],ensure_ascii=False),flush=True)
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'live_metadata':True,'live_models':False,'api_keys_used':False,'checks':checks}
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('REPORT',out,flush=True)
    # Provider throttling is recorded, not conflated with a failing local parser.
    if not any(c['ok'] and c.get('retrieved') for c in checks):raise SystemExit(1)

if __name__=='__main__':main()
