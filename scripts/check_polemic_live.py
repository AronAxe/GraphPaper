"""Opt-in real Codex editorial acceptance test with original synthetic documents.

Uses an explicitly selected existing official Codex sign-in, but does not open
or modify installed project databases/settings. No API billing fallback.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from graphpaper.models import Settings
from graphpaper.providers import Clients
from graphpaper.pipeline import Job,make_angles,make_outline,write_draft
from graphpaper.storage import Store
from graphpaper.codex import close_all
from tests.polemic_fixtures import project


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile-root',required=True,type=Path)
    parser.add_argument('--codex',required=True,type=Path)
    parser.add_argument('--model',required=True)
    parser.add_argument('--effort',default='low')
    parser.add_argument('--angles-only',action='store_true')
    parser.add_argument('--resume-angles',type=Path)
    parser.add_argument('--reuse-outline',action='store_true')
    parser.add_argument('--opposite',action='store_true')
    parser.add_argument('--out',type=Path,default=ROOT/'test-results/polemic-live.json')
    args=parser.parse_args()
    class AccountLocation:
        path=args.profile_root.resolve()/'credentials.dpapi'
        def get(self,name):return ''
    settings=Settings(provider='codex',codex_executable=str(args.codex.resolve()),model=args.model,
        reasoning_effort=args.effort,extraction_reasoning_effort=args.effort,editor_reasoning_effort=args.effort,
        allow_cloud=True,jev_provider='off',refine=False,max_calls=12,max_candidates=8,max_output_tokens=6000,request_timeout_seconds=300)
    report={'live_codex':True,'live_jev':False,'synthetic_material':True,'opposite_position':args.opposite,'model':args.model,'effort':args.effort,'ok':False}
    p=project(opposite=args.opposite);job=Job(p.id,'editorial-live');clients=Clients(settings,AccountLocation(),job)
    import graphpaper.providers as providers
    original_parse=providers.parse_json
    def observed_parse(text):
        try:return original_parse(text)
        except Exception:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.with_suffix('.invalid-response.txt').write_text(text,encoding='utf-8')
            raise
    providers.parse_json=observed_parse
    try:
        print('GENERATING ARGUMENT-LED ANGLES WITH AUTHOR VOICE',flush=True)
        if args.resume_angles:
            from graphpaper.models import Angle
            p.angles=[Angle.model_validate(a) for a in json.loads(args.resume_angles.read_text(encoding='utf-8'))['angles']]
            report['angles_reused_from_prior_live_call']=True
        else:
            make_angles(p,clients,job)
        report['angles']=[a.model_dump() for a in p.angles]
        report['thesis']=p.brief.thesis
        for angle in p.angles:print(json.dumps({'title':angle.title,'thesis':angle.thesis,'hook':angle.hook},ensure_ascii=False),flush=True)
        assert p.angles
        if not args.angles_only:
            p.selected_angle=p.angles[0].id
            print('OUTLINING THE SELECTED ARGUMENT',flush=True)
            if args.reuse_outline and args.resume_angles:
                from graphpaper.models import Section
                p.outline=[Section.model_validate(s) for s in json.loads(args.resume_angles.read_text(encoding='utf-8'))['outline']]
                report['outline_reused_from_prior_live_call']=True
            else:
                make_outline(p,clients,job)
            # The fixture is short; cap this acceptance run at three authored sections.
            p.outline=p.outline[:3]
            for section in p.outline:section.target_words=250
            with tempfile.TemporaryDirectory(prefix='GraphPaper-polemic-live-') as temp:
                store=Store(Path(temp));store.create(p)
                print('DRAFTING AND REVIEWING THE ARGUMENT',flush=True)
                write_draft(p,clients,store,job)
            report.update({'outline':[s.model_dump() for s in p.outline],'draft':p.draft,'review':p.review.model_dump()})
            print(p.draft,flush=True)
            print('AUTHORIAL_REVIEW',json.dumps(p.review.authorial_assessment),flush=True)
        report['ok']=True
    except Exception as exc:
        report['error']=str(exc)
        raise
    finally:
        report['usage']=job.usage
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        providers.parse_json=original_parse
        close_all()
        print('REPORT',str(args.out),json.dumps(job.usage),flush=True)

if __name__=='__main__':main()
