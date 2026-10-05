"""One-time integration of v0.2.0. Exact anchors fail closed on upstream drift."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def change(path, old, new):
    p=ROOT/path
    text=p.read_text(encoding='utf-8')
    if new in text:
        return
    if old not in text:
        raise RuntimeError('Integration anchor missing: '+path+' '+old[:90])
    if text.count(old)!=1:
        raise RuntimeError('Ambiguous integration anchor: '+path+' '+old[:90])
    p.write_text(text.replace(old,new,1),encoding='utf-8')

change('graphpaper/models.py','class Project(Model):', '''class VoiceProfile(Model):
    enabled: bool = True
    strength: int = Field(75, ge=0, le=100)
    name: str = Field('My writing voice', max_length=160)
    instructions: str = Field('', max_length=12000)
    sample_ids: list[str] = Field(default_factory=list)
    sample_hash: str = ''
    learned_at: str = ''
    metrics: dict[str, Any] = Field(default_factory=dict)
    observations: list[str] = Field(default_factory=list)


class PolishCandidate(Model):
    mode: str
    original_hash: str
    draft: str = Field(max_length=1_000_000)
    created: str = ''
    review: dict[str, Any] = Field(default_factory=dict)
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    protected_spans: int = 0
    diff: list[str] = Field(default_factory=list)


class Project(Model):''')
change('graphpaper/models.py','    demo: bool = False\n','    demo: bool = False\n    voice_profile: VoiceProfile = Field(default_factory=VoiceProfile)\n    polish: PolishCandidate | None = None\n    auto_import: bool = True\n')
change('graphpaper/models.py','Literal["openrouter", "openai-compatible", "anthropic"]','Literal["openrouter", "openai-compatible", "anthropic", "codex"]')
change('graphpaper/models.py','    editor_model: str = ""','    codex_executable: str = ""\n    editor_model: str = ""')
change('graphpaper/providers.py','        if not model.strip():','        if not model.strip() and s.provider != "codex":')
change('graphpaper/providers.py','        if s.provider == "anthropic":\n            data = self.post(','''        if s.provider == "codex":
            from .codex import get_codex
            self.check('https://chatgpt.com')
            text = get_codex(self.vault.path.parent, s.codex_executable).complete(system, user, model, self.job, s.max_calls)
            return parse_json(text) if json_mode else text
        if s.provider == "anthropic":
            data = self.post(''')
change('graphpaper/providers.py','    def discover_models(self):\n','''    def discover_models(self):
        if self.settings.provider == 'codex':
            from .codex import get_codex
            return get_codex(self.vault.path.parent, self.settings.codex_executable).models()
''')
change('graphpaper/pipeline.py','def voice_notes(p: Project):\n    return [{"title": s.title, "sample": s.text[:3500], "note": "Style reference only. Do not copy wording or treat as factual evidence."} for s in p.sources if s.enabled and s.role == "voice"][:3]', '''def voice_notes(p: Project):
    from .voice import voice_context
    return voice_context(p)''')
change('graphpaper/pipeline.py','"review": review.model_dump(), "draft": original, "sources": pack}', '"review": review.model_dump(), "draft": original, "sources": pack, "author_voice": voice_notes(p)}')
change('graphpaper/pipeline.py','{"graph", "angles", "outline", "draft", "review", "revise"}', '{"graph", "angles", "outline", "draft", "review", "revise", "voice", "humanize", "deslop", "both"}')
change('graphpaper/pipeline.py','            if job.action == "graph":\n', '''            if job.action == "voice":
                from .voice import learn_voice
                learn_voice(p, clients, job)
            elif job.action in {"humanize", "deslop", "both"}:
                from .polish import polish_draft
                polish_draft(p, clients, job, job.action, instruction)
            elif job.action == "graph":
''')
change('graphpaper/server.py','        allowed = {"title", "brief", "draft", "outline", "angles", "selected_angle", "feedback"}', '        allowed = {"title", "brief", "draft", "outline", "angles", "selected_angle", "feedback", "voice_profile", "auto_import"}')
change('graphpaper/server.py','    app.mount("/static", StaticFiles(directory=asset_directory()), name="static")', '''    from .studio_routes import install
    install(app, store, vault, runner, settings)
    app.mount("/static", StaticFiles(directory=asset_directory()), name="static")''')
change('graphpaper/server.py','        return store.create(p)\n\n    @app.post("/api/demo")', '''        app.state.folders.path(p)
        return store.create(p)

    @app.post("/api/demo")''')
change('graphpaper/server.py','        return store.save(p, p.version)\n\n    @app.post("/api/projects/{pid}/sources/text")', '''        p = store.save(p, p.version)
        app.state.folders.original(p, p.sources[-1])
        return p

    @app.post("/api/projects/{pid}/sources/text")''')
old='        return add_source(pid, title, text, kind=Path(title).suffix.lstrip("."), role=role, warnings=warnings)'
change('graphpaper/server.py',old,'''        p = add_source(pid, title, text, kind=Path(title).suffix.lstrip("."), role=role, warnings=warnings)
        app.state.folders.original(p, p.sources[-1], data, title)
        return p''')
change('graphpaper/graphify_adapter.py','    executable = clients.settings.graphify_executable or shutil.which("graphify")', '''    if clients.settings.provider == "codex":
        raise ValueError("Use Native extraction or import a Graphify JSON graph with Codex sign-in. The optional external Graphify process requires its own API credentials.")
    executable = clients.settings.graphify_executable or shutil.which("graphify")''')
change('ui/index.html','<script src="/static/app.js" defer></script>','<script src="/static/app.js" defer></script>\n<script src="/static/studio.js" defer></script>')
change('ui/index.html','<link rel="stylesheet" href="/static/styles.css">','<link rel="stylesheet" href="/static/styles.css"><link rel="stylesheet" href="/static/studio.css">')
change('ui/app.js',"if(!state.settings.model){toast('Choose a writing model in Connections first.');", "if(!state.settings.model&&state.settings.provider!=='codex'){toast('Choose a writing model in Connections first.');")
change('ui/app.js',"GraphPaper · 0.1.0", "GraphPaper · 0.2.0")
change('ui/app.js',"draft:'write',review:'write',revise:'write'", "draft:'write',review:'write',revise:'write',humanize:'write',deslop:'write',both:'write',voice:'sources'")
change('graphpaper/__init__.py','__version__ = "0.1.0"','__version__ = "0.2.0"')
change('pyproject.toml','version = "0.1.0"','version = "0.2.0"')
change('pyproject.toml','"ui/graphpaper.ico"]','"ui/graphpaper.ico", "ui/studio.js", "ui/studio.css"]')
print('GraphPaper v0.2.0 integrations applied.')
change('graphpaper/server.py','if any(s.digest == fingerprint for s in p.sources):','if any(s.digest == fingerprint and s.role == role for s in p.sources):')

ignore=ROOT/'.gitignore'
if '\nvendor/\n' not in ignore.read_text():
    ignore.write_text(ignore.read_text()+'\nvendor/\n')
readme=ROOT/'README.md'
intro='''## GraphPaper 0.2.0

[**Download the Windows release**](https://github.com/AronAxe/GraphPaper/releases/latest) · [What is new](docs/UPDATE-0.2.md)

Your own writing voice from uploads or article URLs; a project Inbox with automatic local imports; reversible humanizer/deslopping passes; and **Codex / ChatGPT browser sign-in instead of a writing API key**. The Windows package includes Python and the official Codex runtime. Existing API providers and the optional JEV connection remain available.

'''
text=readme.read_text(encoding='utf-8')
if '## GraphPaper 0.2.0' not in text:
    text=text.replace('## Open the studio on Windows',intro+'## Open the source edition on Windows',1)
    readme.write_text(text,encoding='utf-8')
changelog=ROOT/'CHANGELOG.md'
text=changelog.read_text(encoding='utf-8')
if '## 0.2.0' not in text:
    text=text.replace('# Changelog','# Changelog\n\n## 0.2.0 — 2026-10-05\n\n- Learn and edit an author voice from uploaded writing or selected article URLs.\n- Separate project folders, stable-file automatic Inbox imports, role subfolders and original uploads.\n- Local prose inspection, humanizer/deslopping proposals, protected factual spans and explicit accept/reject with version history.\n- Official Codex browser OAuth and subscription-based writing, with an isolated account directory and bundled Windows runtime.\n- Dedicated new workflow, API, subprocess and browser tests; versioned Windows release packaging with SHA-256 provenance.\n',1)
    changelog.write_text(text,encoding='utf-8')
