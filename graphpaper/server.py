from __future__ import annotations
import json
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from . import __version__
from .demo import make_demo
from .export import export
from .graph import import_graph, path_between
from .ingest import MAX_BYTES, clean, digest, extract, fetch_url
from .models import Project, Source, Settings, Brief, Angle, Graph, Section, now, uid
from .pipeline import Runner
from .providers import Clients, ProviderError, endpoint
from .secrets import Vault
from .storage import Conflict, Store, data_directory


def asset_directory():
    candidate = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "ui"
    return candidate if candidate.is_dir() else Path(sys.prefix) / "share" / "graphpaper" / "ui"


def create_app(root=None):
    store = Store(Path(root) if root else data_directory())
    vault = Vault(store.root)
    token = secrets.token_urlsafe(32)
    settings = lambda: Settings.model_validate(store.settings())
    runner = Runner(store, vault, settings)
    app = FastAPI(title="GraphPaper", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store, app.state.vault, app.state.runner, app.state.token = store, vault, runner, token

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        if host not in {"127.0.0.1", "localhost", "testserver"}:
            return JSONResponse({"detail": "Loopback access only"}, status_code=403)
        if request.url.path.startswith("/api/"):
            origin = request.headers.get("origin")
            expected = f"{request.url.scheme}://{request.headers.get('host')}"
            if origin and origin != expected:
                return JSONResponse({"detail": "Cross-origin request refused"}, status_code=403)
            if request.headers.get("x-graphpaper") != "1" or request.cookies.get("gp_session") != token:
                return JSONResponse({"detail": "Open GraphPaper again to establish a local session."}, status_code=403)
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > 26 * 1024 * 1024:
                    return JSONResponse({"detail": "Request exceeds 26 MB"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid request length"}, status_code=400)
        res = await call_next(request)
        res.headers["X-Content-Type-Options"] = "nosniff"
        res.headers["Referrer-Policy"] = "no-referrer"
        res.headers["X-Frame-Options"] = "DENY"
        res.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        if request.url.path.startswith("/api/"):
            res.headers["Cache-Control"] = "no-store"
        return res

    @app.exception_handler(Conflict)
    async def conflict_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(KeyError)
    async def key_handler(request, exc):
        return JSONResponse({"detail": "Project or record not found"}, status_code=404)

    @app.exception_handler(ValueError)
    async def value_handler(request, exc):
        return JSONResponse({"detail": str(exc)[:1000]}, status_code=400)

    @app.exception_handler(ProviderError)
    async def provider_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=502)

    @app.get("/")
    def index():
        res = FileResponse(asset_directory() / "index.html")
        res.set_cookie("gp_session", token, httponly=True, samesite="strict")
        res.headers["Cache-Control"] = "no-store"
        return res

    @app.get("/health")
    def health():
        return {"ok": True, "version": __version__}

    def public_settings():
        s = settings()
        return s.model_dump() | {"keys": vault.flags(), "key_storage": vault.mode, "effective_jev": Clients(s, vault).jev_route(), "data_directory": str(store.root)}

    @app.get("/api/bootstrap")
    def bootstrap():
        return {"projects": store.list(), "settings": public_settings(), "version": __version__, "jobs": [j.public() for j in runner.jobs.values() if j.state in {"queued", "running"}]}

    @app.get("/api/settings")
    def get_settings():
        return public_settings()

    @app.put("/api/settings")
    async def put_settings(request: Request):
        if any(j.state in {"queued", "running"} for j in runner.jobs.values()):
            raise ValueError("Finish or cancel active AI jobs before changing connections. Their provider and key settings must remain consistent.")
        raw = await request.json()
        keys = raw.pop("api_keys", {})
        # Client-only flags never enter persistent settings.
        for k in ["keys", "key_storage", "effective_jev", "data_directory"]:
            raw.pop(k, None)
        value = Settings.model_validate(raw)
        endpoint(value.base_url)
        if not value.remember_keys:
            vault.forget_persistent()
        for key, v in keys.items():
            if v is not None:
                vault.set(key, str(v), value.remember_keys)
        store.set_settings(value.model_dump())
        return public_settings()

    @app.get("/api/graphify/status")
    async def graphify_status():
        from .graphify_runtime import check_runtime
        result = await run_in_threadpool(check_runtime, settings().graphify_executable)
        return {k:v for k,v in result.items() if k != "command"}

    @app.get("/api/models")
    async def get_models():
        return await run_in_threadpool(Clients(settings(), vault).discover_models)

    @app.post("/api/test-connection")
    async def test_connection(request: Request):
        kind = (await request.json()).get("kind", "writer")
        c = Clients(settings(), vault)
        if kind == "jev":
            result = await run_in_threadpool(c.decide, {"test": "A red apple"}, {"red": {"type": "noul", "instructions": "Is the described apple red?"}})
            if result is None:
                raise ValueError("JEV is off or no JEV-capable key is configured.")
            return {"ok": True, "message": "JEV returned a valid typed probability.", "result": result}
        result = await run_in_threadpool(c.complete, "Reply with the word Connected only.", "Connection test.", max_tokens=(settings().max_output_tokens if settings().reasoning_effort != "default" else 1000))
        return {"ok": True, "message": "Writing model responded.", "response": result[:200]}

    @app.post("/api/projects")
    async def create_project(request: Request):
        raw = await request.json()
        p = Project(title=raw.get("title", "Untitled project"), mode=raw.get("mode", "nonfiction"))
        if p.mode == "polemic":
            p.brief.format = "Polemic / argumentative essay"
            p.brief.stance_policy = "preserve"
            p.brief.rhetorical_force = 85
            p.brief.voice = "Incisive, witty and direct. Preserve the author's judgments and rhetorical energy."
        if p.mode == "science":
            p.brief.format = "APA scientific manuscript"
            p.brief.audience = "Scientific journal reviewers and researchers"
            p.brief.target_words = 4000
            p.brief.voice = "Precise academic prose; explain methods, effect sizes and limitations without inflated claims."
        if p.mode == "fiction":
            p.brief.format = "Short story"
            p.brief.avoid = "Expository monologues, generic imagery, unearned resolutions, continuity breaks."
        app.state.folders.path(p)
        return store.create(p)

    @app.post("/api/demo")
    async def demo(request: Request):
        mode = (await request.json()).get("mode", "nonfiction")
        p = make_demo(mode)
        store.create(p)
        store.snapshot(p, "Sample opening")
        return p

    @app.get("/api/projects/{pid}")
    def get_project(pid: str):
        return store.get(pid)

    @app.patch("/api/projects/{pid}")
    async def update_project(pid: str, request: Request):
        raw = await request.json()
        p = store.get(pid)
        version = raw.pop("version", None)
        if version != p.version:
            raise Conflict("A newer project version exists. Refresh; your unsaved editor text has been kept in this window.")
        allowed = {"title", "brief", "draft", "outline", "angles", "selected_angle", "feedback", "voice_profile", "auto_import"}
        if set(raw) - allowed:
            raise ValueError("Unsupported project field")
        if p.mode == 'science' and set(raw) & {'draft','brief','outline'}:
            p.research.acknowledgements = {}
            p.research.confirmation_hash = ''
        if "draft" in raw and p.draft != raw["draft"]:
            store.snapshot(p, "Before manual edit")
        new = Project.model_validate(p.model_dump() | raw)
        from .editorial import fingerprint as editorial_fingerprint, review_stamp
        if 'angles' in raw: new.angles_context_hash = editorial_fingerprint(new)
        if 'outline' in raw: new.outline_context_hash = review_stamp(new)
        if len(new.draft) > 1_000_000 or len(new.angles) > 100 or len(new.outline) > 40 or len(new.feedback) > 1000:
            raise ValueError("Project field exceeds size limits.")
        return store.save(new, version)

    @app.delete("/api/projects/{pid}")
    def delete_project(pid: str):
        if runner.active(pid):
            raise ValueError("Cancel the active job before deleting the project.")
        store.delete(pid)
        return {"ok": True}

    def add_source(pid, title, text, kind="text", role="evidence", url="", warnings=None, author="", published=""):
        if runner.active(pid):
            raise ValueError("Wait for the current job before changing sources.")
        p = store.get(pid)
        if len(p.sources) >= (600 if p.mode == "science" else 100):
            raise ValueError("Limit: 100 sources per project.")
        text = clean(text)
        fingerprint = digest(text)
        if any(s.digest == fingerprint and s.role == role for s in p.sources):
            raise ValueError("This text is already in the project.")
        n = max([int(s.id[1:]) for s in p.sources if re.fullmatch(r"S\d+", s.id)] + [0]) + 1
        p.sources.append(Source(id=f"S{n}", title=title[:300], text=text, kind=kind, role=role, url=url, warnings=warnings or [], digest=fingerprint, author=author[:300], published=published[:100]))
        if p.graph.nodes:
            p.graph.warnings = list(dict.fromkeys(p.graph.warnings + ["Sources changed after the last graph build. Rebuild before relying on coverage."]))
        p = store.save(p, p.version)
        app.state.folders.original(p, p.sources[-1])
        return p

    @app.post("/api/projects/{pid}/sources/text")
    async def source_text(pid: str, request: Request):
        raw = await request.json()
        return add_source(pid, str(raw.get("title", "Pasted source")), str(raw.get("text", "")), role=raw.get("role", "evidence"), url=str(raw.get("url", "")), author=str(raw.get("author", "")), published=str(raw.get("published", "")))

    @app.post("/api/projects/{pid}/sources/file")
    async def source_file(pid: str, file: UploadFile = File(...), role: str = Form("evidence")):
        data = await file.read(MAX_BYTES + 1)
        await file.close()
        title = Path(file.filename or "source.txt").name[:300]
        text, warnings = await run_in_threadpool(extract, data, title)
        p = add_source(pid, title, text, kind=Path(title).suffix.lstrip("."), role=role, warnings=warnings)
        app.state.folders.original(p, p.sources[-1], data, title)
        return p

    @app.post("/api/projects/{pid}/sources/url")
    async def source_url(pid: str, request: Request):
        raw = await request.json()
        try:
            title, text, url, warnings = await run_in_threadpool(fetch_url, str(raw.get("url", "")))
        except OSError as e:
            raise ValueError("Could not reach that source. Check the address, or paste the text / upload a saved copy.") from e
        return add_source(pid, title, text, "url", raw.get("role", "evidence"), url, warnings)

    @app.patch("/api/projects/{pid}/sources/{sid}")
    async def source_update(pid: str, sid: str, request: Request):
        if runner.active(pid):
            raise ValueError("Wait for the current job before changing sources.")
        raw = await request.json()
        if set(raw) - {"role", "enabled", "title", "author", "published"}:
            raise ValueError("Unsupported source property")
        p = store.get(pid)
        s = next((s for s in p.sources if s.id == sid), None)
        if not s:
            raise KeyError(sid)
        new = Source.model_validate(s.model_dump() | raw)
        p.sources[p.sources.index(s)] = new
        p.graph.warnings = list(dict.fromkeys(p.graph.warnings + ["Sources changed after the last graph build. Rebuild before relying on coverage."]))
        return store.save(p, p.version)

    @app.post("/api/projects/{pid}/graph/import")
    async def graph_import(pid: str, request: Request):
        if runner.active(pid):
            raise ValueError("Wait for the current job before importing a graph.")
        raw = await request.json()
        p = store.get(pid)
        p.graph = import_graph(raw)
        p.angles, p.selected_angle = [], ""
        return store.save(p, p.version)

    @app.get("/api/projects/{pid}/graph/path")
    def graph_path(pid: str, a: str, b: str):
        return {"path": path_between(store.get(pid).graph, a, b), "note": "Undirected conceptual path, not a causal proof."}

    @app.post("/api/projects/{pid}/jobs")
    async def start_job(pid: str, request: Request):
        raw = await request.json()
        return runner.start(pid, raw.get("action", ""), str(raw.get("instruction", ""))[:8000]).public()

    @app.get("/api/jobs/{jid}")
    def get_job(jid: str):
        if jid not in runner.jobs:
            raise KeyError(jid)
        return runner.jobs[jid].public()

    @app.post("/api/jobs/{jid}/cancel")
    def cancel_job(jid: str):
        if jid not in runner.jobs:
            raise KeyError(jid)
        runner.jobs[jid].cancel.set()
        return {"ok": True, "message": "Cancellation requested; an in-flight provider request may still complete and be billed."}

    @app.get("/api/projects/{pid}/revisions")
    def revisions(pid: str):
        return store.revisions(pid)

    @app.post("/api/projects/{pid}/revisions/{rid}/restore")
    def restore(pid: str, rid: str):
        if runner.active(pid):
            raise ValueError("Wait for the current job before restoring a version.")
        p = store.get(pid)
        r = next((r for r in store.revisions(pid) if r["id"] == rid), None)
        if not r:
            raise KeyError(rid)
        store.snapshot(p, "Before version restore")
        p.draft = r["draft"]
        return store.save(p, p.version)

    @app.get("/api/projects/{pid}/export/{kind}")
    def get_export(pid: str, kind: str):
        p = store.get(pid)
        data, media, ext = export(p, kind)
        stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", p.title).strip("-")[:80] or "GraphPaper"
        return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{stem}{ext}"'})

    @app.post("/api/import")
    async def import_project(request: Request):
        raw = await request.json()
        p = Project.model_validate(raw)
        # Imported projects carry text and metadata, never execution instructions or credentials.
        if len(p.sources) > (600 if p.mode == "science" else 100) or len(p.graph.nodes) > 5000 or len(p.graph.edges) > 20000 or len(p.draft) > 1_000_000:
            raise ValueError("Project exceeds import limits")
        if len({s.id for s in p.sources}) != len(p.sources):
            raise ValueError("Duplicate source IDs")
        if any(not re.fullmatch(r"S\d+", s.id) for s in p.sources):
            raise ValueError("Source IDs must use S1, S2, etc.")
        sources = {s.id: s for s in p.sources}
        for s in p.sources:
            s.digest = digest(s.text)
        ids = {n.id for n in p.graph.nodes}
        if len(ids) != len(p.graph.nodes) or any(e.source not in ids or e.target not in ids for e in p.graph.edges):
            raise ValueError("Graph has duplicate IDs or dangling relationships")
        for item in [*p.graph.nodes, *p.graph.edges]:
            for ev in item.evidence:
                s = sources.get(ev.source_id)
                pos = s.text.find(ev.quote) if s and ev.quote else -1
                ev.verified, ev.start, ev.end = pos >= 0, pos, pos + len(ev.quote) if pos >= 0 else -1
            if item.status in {"sourced", "canon"} and not any(ev.verified for ev in item.evidence):
                item.status = "inferred"
        p.id, p.version, p.created, p.updated = uid("p_"), 0, now(), now()
        p.title = (p.title + " · imported")[:200]
        return store.create(p)

    from .studio_routes import install
    install(app, store, vault, runner, settings)
    from .editorial_routes import install as install_editorial
    install_editorial(app,store,runner)
    from .science_routes import install as install_science
    install_science(app, store, vault, runner, settings)
    app.mount("/static", StaticFiles(directory=asset_directory()), name="static")
    return app
