from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def edit(name,old,new):
    p=ROOT/name;t=p.read_text(encoding='utf-8')
    assert t.count(old)==1,(name,t.count(old),old[:90])
    p.write_text(t.replace(old,new),encoding='utf-8',newline='\n')
edit('graphpaper/jev_budget.py',"        current={}\n        for key,question in qs.items():","        current={}\n        threshold=MAX_BYTES if wire_bytes({'state':scoped})>TARGET_BYTES*0.75 else TARGET_BYTES\n        for key,question in qs.items():")
edit('graphpaper/jev_budget.py','size>TARGET_BYTES or len(proposed)>MAX_QUESTIONS','size>threshold or len(proposed)>MAX_QUESTIONS')
edit('graphpaper/pipeline.py',"'Structurally explored (JEV off)'","'Structurally explored (unscored)'")
edit('graphpaper/editorial.py',"'voice_sources':voice_fingerprint(project)","'voice_sources':('saved:'+project.voice_profile.library_id if project.voice_profile.library_id else voice_fingerprint(project))")
# Reuse the existing narrow native save bridge; do not expose filesystem APIs.
edit('graphpaper/desktop.py','"research-package", "submission"}:','"research-package", "submission", "voice"}:')
edit('graphpaper/desktop.py','''            p = self._store.get(project_id)
            data, _, ext = export(p, kind)
            stem = re.sub(r'[^\w\s.-]', '', p.title).strip()[:80] or "GraphPaper"''','''            if kind == 'voice':
                from .voice_library import VoiceLibrary
                import json
                v,_ = VoiceLibrary(self._store).get(project_id)
                profile=v.profile.model_copy(deep=True)
                profile.sample_ids=[];profile.sample_hash='';profile.library_id='';profile.library_version=0
                data=json.dumps({'format':'graphpaper-voice-1','profile':profile.model_dump()},ensure_ascii=False,indent=2).encode()
                ext='.json';title=v.profile.name
            else:
                p = self._store.get(project_id)
                data, _, ext = export(p, kind)
                title=p.title
            stem = re.sub(r'[^\w\s.-]', '', title).strip()[:80] or "GraphPaper"''')
edit('ui/voices.js',"async function voiceDownload(path,name){const r=await fetch", "async function voiceDownload(path,name){if(window.pywebview?.api?.save_export){const r=await window.pywebview.api.save_export(voicesUI.current.id,'voice');if(r.error)throw new Error(r.error);if(r.saved)toast('Voice graph exported.');return;}const r=await fetch")
p=ROOT/'scripts/native_smoke.py';t=p.read_text(encoding='utf-8')
a=t.index("    parser.add_argument('--polemic'");b=t.index('\n',a)
t=t[:b]+"\n    parser.add_argument('--voices',action='store_true',help='Exercise saved voice graphs without model calls')"+t[b:]
needle="            page.locator('[data-action=\"settings\"]').click();page.wait_for_selector('#s-provider')"
assert t.count(needle)==1
t=t.replace(needle,"            if args.voices:\n                from voice_ui_checks import exercise\n                report['voice_library']=exercise(page,check,out,native=True)\n                responsive(hwnd)\n"+needle)
p.write_text(t,encoding='utf-8',newline='\n')
p=ROOT/'README.md';t=p.read_text(encoding='utf-8');needle='## What makes it useful';assert needle in t
t=t.replace(needle,'**New: reusable voice graphs.** Save a voice once, select it in any project, and keep its training pieces separate. JEV receives compact graph context with automatic request sizing—not the article pile. [Voice graphs and author control](docs/VOICE-GRAPHS.md)\n\n'+needle,1);p.write_text(t,encoding='utf-8',newline='\n')
p=ROOT/'CHANGELOG.md';t=p.read_text(encoding='utf-8');t=t.replace('# Changelog','# Changelog\n\n## 0.5.0\n\n- Bound and automatically batch JEV requests by actual serialized UTF-8 size; remove voice-training prose from decision payloads.\n- Add named, reusable voice graphs with independent training, graph editing, import/export and explicit application across projects.\n- Compose namespaced style/evidence overlays without altering the research graph; current author instructions override saved style preferences.\n- Keep unrepresentable optional decisions honestly unscored instead of aborting completed writing.\n- Implement and validate the update using GitHub-hosted runners only.\n',1);p.write_text(t,encoding='utf-8',newline='\n')
print('Completed native voice export, graph-library checks and documentation links.')
