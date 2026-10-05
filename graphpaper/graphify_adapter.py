"""Optional real Graphify CLI bridge; user-selected executable, no shell commands."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .graph import import_graph
from .models import Project
from .providers import Clients, ProviderError


def run_graphify(project: Project, clients: Clients, job):
    if clients.settings.provider == "codex":
        raise ValueError("Use Native extraction or import a Graphify JSON graph with Codex sign-in. The optional external Graphify process requires its own API credentials.")
    executable = clients.settings.graphify_executable or shutil.which("graphify")
    if not executable or not Path(executable).is_file():
        raise ValueError("Graphify is not installed or its executable was not found. Select Native in Connections, import graph.json, or install graphifyy and choose its executable.")
    if clients.settings.provider == "anthropic":
        backend = "claude"
        envkey, basekey, modelkey = "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL"
    else:
        backend = "openai"
        envkey, basekey, modelkey = "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"
    clients.check(clients.settings.base_url)
    if not clients.llm_key() and not clients.settings.base_url.startswith(("http://localhost", "http://127.0.0.1")):
        raise ProviderError("Configure a writing API key before running Graphify.")
    with tempfile.TemporaryDirectory(prefix="graphpaper-") as folder:
        root = Path(folder)
        for s in project.sources:
            if s.enabled and s.role != "voice":
                (root / (s.id + ".md")).write_text(s.title + "\n\n" + s.text, encoding="utf-8")
        env = os.environ.copy()
        env.update({envkey: clients.llm_key() or "local", basekey: clients.settings.base_url,
                    modelkey: clients.settings.extraction_model or clients.settings.model,
                    "GRAPHIFY_NO_AUTO_REFRESH": "1", "PYTHONIOENCODING": "utf-8"})
        args = [str(executable), "extract", str(root), "--backend", backend, "--mode", "deep", "--no-viz", "--no-cluster", "--token-budget", "4000", "--max-concurrency", "2"]
        job.note("Running Graphify. Its own API usage is not metered by GraphPaper; check your provider billing.")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        with (root / "process.log").open("w", encoding="utf-8") as log:
            proc = subprocess.Popen(args, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
            started = time.monotonic()
            try:
                while proc.poll() is None:
                    job.check()
                    if time.monotonic() - started > 1200:
                        raise ValueError("Graphify exceeded its 20-minute timeout.")
                    time.sleep(0.25)
                if proc.returncode:
                    raise ValueError("Graphify failed. Native extraction remains available; no old graph was replaced.")
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
        candidates = [root / "graphify-out/graph.json", root / "graph.json"]
        graphpath = next((p for p in candidates if p.exists()), None)
        if not graphpath:
            raise ValueError("Graphify finished without graph.json. Check the installed version; select Native or import a graph manually.")
        if graphpath.stat().st_size > 20_000_000:
            raise ValueError("Graphify output exceeds 20 MB.")
        graph = import_graph(json.loads(graphpath.read_text(encoding="utf-8")))
        graph.engine = "Graphify CLI + GraphPaper evidence extraction"
        return graph
