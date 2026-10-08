"""One-time, exact-anchored source update; executed only on a GitHub-hosted runner."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def replace(name,old,new,count=1):
    p=ROOT/name;t=p.read_text(encoding='utf-8')
    if t.count(old)!=count:raise RuntimeError(f'{name}: expected {count} exact anchors, found {t.count(old)}: {old[:90]}')
    p.write_text(t.replace(old,new),encoding='utf-8',newline='\n')

replace('graphpaper/models.py','from pydantic import BaseModel, Field, ConfigDict','from pydantic import BaseModel, Field, ConfigDict, field_validator')
replace('graphpaper/models.py','class VoiceProfile(Model):','''class VoiceProfile(Model):
    graph: dict[str, Any] = Field(default_factory=dict)
    library_id: str = Field('', pattern=r'^(?:v_[a-f0-9]{12})?$')
    library_version: int = Field(0, ge=0)

    @field_validator('graph')
    @classmethod
    def validate_voice_graph(cls,value):
        if not value:return {}
        from .style_graph import StyleGraph
        return StyleGraph.model_validate(value).model_dump()
''')
p=ROOT/'graphpaper/providers.py';t=p.read_text(encoding='utf-8');a=t.index('    def decide(');b=t.index('    def discover_models(',a)
t=t[:a]+'''    def decide(self, state: dict | str, questions: dict) -> dict | None:
        from .jev_budget import dispatch
        return dispatch(self,state,questions)

'''+t[b:];p.write_text(t,encoding='utf-8',newline='\n')
replace('graphpaper/voice.py','per_source = max(200, budget // len(selected))','per_source = max(1, budget // len(selected))')
replace('graphpaper/voice.py',"    stale = bool(profile.sample_hash and profile.sample_hash != fingerprint(project))",'''    if profile.library_id:
        from .style_graph import for_profile
        return {'enabled':True,'name':profile.name,'influence_percent':profile.strength,
                'graph':for_profile(profile).model_dump(),'instructions':'','samples':[],
                'profile_needs_refresh':False,
                'rule':'Apply this saved voice graph as flexible style preferences, not factual evidence or a filter. The current brief and author instruction take precedence, including stronger vocabulary, profanity, ridicule and rhetorical force. Training articles are not needed again.'}
    stale = bool(profile.sample_hash and profile.sample_hash != fingerprint(project))''')
replace('graphpaper/voice.py',"    job.note('Voice profile ready. Edit it, adjust its influence, or switch it off.', 95)",'''    from .style_graph import for_profile,StyleGraph
    graph=raw.get('graph')
    if isinstance(graph,dict) and graph.get('nodes'):
        project.voice_profile.graph=StyleGraph.model_validate(graph).model_dump()
    else:
        project.voice_profile.graph=for_profile(project.voice_profile).model_dump()
    job.note('Voice graph ready. Save it to My voices to reuse across projects without retraining.', 95)''')
replace('graphpaper/voice.py',"'observations': ['Short, evidence-limited observations']","'observations': ['Short, evidence-limited observations'], 'graph': {'nodes':[{'id':'voice','label':'Named voice','kind':'voice','instruction':'Style identity, not factual claims','weight':1,'targets':['all']},{'id':'force','label':'Rhetorical force','kind':'style','instruction':'A compact observed writing habit, including power language when present. Current author requests override the preference.','weight':1,'targets':['claim']}], 'edges':[{'source':'voice','target':'force','relation':'expresses'}]}")
replace('graphpaper/voice.py','Do not quote or copy distinctive sample sentences.','Do not quote or copy distinctive sample sentences. Return a compact reusable graph of 8-20 style nodes and relationships. Preserve force, swearing, indignation and ridicule where present; do not install a vocabulary filter. Each instruction is at most 600 characters, and the current author brief overrides saved preferences.')
p=ROOT/'graphpaper/editorial.py';t=p.read_text(encoding='utf-8');a=t.index('    voice=voice_context(project,1800 if compact else 6500)');b=t.index('    selected=next(',a)
t=t[:a]+'''    if compact:
        from .style_graph import voice_decision
        profile=project.voice_profile
        if not profile.library_id and profile.sample_hash and profile.sample_hash!=voice_fingerprint(project):
            profile=profile.model_copy(update={'instructions':'','graph':{}})
        voice=voice_decision(profile)
    else:
        voice=voice_context(project,6500)
'''+t[b:];p.write_text(t,encoding='utf-8',newline='\n')
replace('graphpaper/editorial.py',"'policy_version':'authorial-intent-v1'","'policy_version':'authorial-intent-v2', 'voice_precedence':'The current author brief overrides saved voice habits. Power language is allowed; saved preferences do not cap force, vocabulary or profanity.'")
# Plain added voice samples do not invalidate an evidence graph.
replace('graphpaper/server.py','        if p.graph.nodes:\n            p.graph.warnings = list(dict.fromkeys(w for w in p.graph.warnings))','        if p.graph.nodes:\n            p.graph.warnings = list(dict.fromkeys(w for w in p.graph.warnings))',0) if False else None
replace('graphpaper/server.py','        if p.graph.nodes:\n            p.graph.warnings = list(dict.fromkeys(p.graph.warnings + ["Sources changed after the last graph build. Rebuild before relying on coverage."]))','        if p.graph.nodes and role != "voice":\n            p.graph.warnings = list(dict.fromkeys(p.graph.warnings + ["Sources changed after the last graph build. Rebuild before relying on coverage."]))')
replace('graphpaper/server.py','        p.sources[p.sources.index(s)] = new\n        p.graph.warnings = list(dict.fromkeys(p.graph.warnings + ["Sources changed after the last graph build. Rebuild before relying on coverage."]))','        p.sources[p.sources.index(s)] = new\n        if s.role != "voice" or new.role != "voice":\n            p.graph.warnings = list(dict.fromkeys(p.graph.warnings + ["Sources changed after the last graph build. Rebuild before relying on coverage."]))')
replace('graphpaper/server.py','    from .studio_routes import install\n    install(app, store, vault, runner, settings)','    from .studio_routes import install\n    install(app, store, vault, runner, settings)\n    from .voice_routes import install as install_voices\n    install_voices(app, store, vault, runner, settings)')
replace('ui/index.html','</head>','<link rel="stylesheet" href="/static/voices.css">\n<script src="/static/voices.js" defer></script>\n</head>')
replace('graphpaper/__init__.py','0.4.0','0.5.0')
replace('pyproject.toml','version = "0.4.0"','version = "0.5.0"')
replace('pyproject.toml','"ui/polemic.css"','"ui/polemic.css", "ui/voices.js", "ui/voices.css"')
p=ROOT/'ui/app.js';t=p.read_text(encoding='utf-8').replace('GraphPaper · 0.4.0','GraphPaper · 0.5.0');p.write_text(t,encoding='utf-8',newline='\n')
replace('scripts/build_release.ps1','docs/RELEASE-0.4.0.md','docs/RELEASE-0.5.0.md')
p=ROOT/'.github/workflows/quality.yml';t=p.read_text(encoding='utf-8');needle='      - run: python scripts/ui_polemic_smoke.py';assert needle in t;t=t.replace(needle,needle+'\n      - run: python scripts/ui_voices_smoke.py');p.write_text(t,encoding='utf-8',newline='\n')
p=ROOT/'.github/workflows/windows.yml';t=p.read_text(encoding='utf-8').replace('docs/RELEASE-0.4.0.md','docs/RELEASE-0.5.0.md');p.write_text(t,encoding='utf-8',newline='\n')
p=ROOT/'docs/wiki-pages.json';v=json.loads(p.read_text(encoding='utf-8'));v['docs_version']='0.5.0';v['pages'].append({'title':'Reusable-Voice-Graphs','source':'docs/VOICE-GRAPHS.md','section':'Studio guides'});p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
p=ROOT/'docs/README.md';t=p.read_text(encoding='utf-8').replace('GraphPaper 0.4.0','GraphPaper 0.5.0');t+='\n## Reusable voices and bounded JEV decisions\n\n[Save a voice graph once and reuse it across projects](VOICE-GRAPHS.md). Training pieces are separate from article evidence; current author instructions override saved preferences.\n';p.write_text(t,encoding='utf-8',newline='\n')
print('Applied exact source changes for reusable graph voices and bounded JEV decisions.')
