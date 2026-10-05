from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .models import Project, now, uid


class Conflict(Exception):
    pass


def data_directory() -> Path:
    override = os.getenv("GRAPHPAPER_DATA_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        return Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "GraphPaper"
    return Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "GraphPaper"


class Store:
    """Atomic SQLite writes plus optimistic revisions; no user text in filenames."""
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "studio.sqlite3"
        self.lock = threading.RLock()
        with self.connect() as c:
            c.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, version INTEGER, updated TEXT, data TEXT);
            CREATE TABLE IF NOT EXISTS revisions(id TEXT PRIMARY KEY, project_id TEXT, label TEXT, created TEXT, draft TEXT);
            CREATE INDEX IF NOT EXISTS revisions_project ON revisions(project_id,created);
            CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1), data TEXT);
            CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, data TEXT);
            """)

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def list(self) -> list[dict]:
        with self.connect() as c:
            rows = c.execute("SELECT data FROM projects ORDER BY updated DESC").fetchall()
        out = []
        for row in rows:
            p = json.loads(row[0])
            out.append({k: p[k] for k in ["id", "title", "mode", "updated", "version", "demo"]} | {
                "sources": len(p["sources"]), "words": len(p["draft"].split()),
                "nodes": len(p["graph"]["nodes"]),
            })
        return out

    def get(self, project_id: str) -> Project:
        with self.connect() as c:
            row = c.execute("SELECT data FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise KeyError("Project not found")
        return Project.model_validate_json(row[0])

    def create(self, project: Project) -> Project:
        with self.lock, self.connect() as c:
            c.execute("INSERT INTO projects VALUES(?,?,?,?)", (project.id, project.version, project.updated, project.model_dump_json()))
        return project

    def save(self, project: Project, expected: int) -> Project:
        with self.lock, self.connect() as c:
            previous_version = project.version
            project.version = expected + 1
            project.updated = now()
            result = c.execute("UPDATE projects SET version=?, updated=?, data=? WHERE id=? AND version=?",
                               (project.version, project.updated, project.model_dump_json(), project.id, expected))
            if not result.rowcount:
                project.version = previous_version
                raise Conflict("Project changed while this action ran. Refresh before saving; your newer work was not overwritten.")
        return project

    def delete(self, project_id: str):
        with self.lock, self.connect() as c:
            c.execute("DELETE FROM projects WHERE id=?", (project_id,))
            c.execute("DELETE FROM revisions WHERE project_id=?", (project_id,))

    def snapshot(self, project: Project, label: str):
        if not project.draft.strip():
            return
        with self.connect() as c:
            last = c.execute("SELECT draft FROM revisions WHERE project_id=? ORDER BY created DESC LIMIT 1", (project.id,)).fetchone()
            if last and last[0] == project.draft:
                return
            c.execute("INSERT INTO revisions VALUES(?,?,?,?,?)", (uid("r_"), project.id, label, now(), project.draft))

    def revisions(self, project_id: str):
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM revisions WHERE project_id=? ORDER BY created DESC", (project_id,))]

    def settings(self) -> dict:
        with self.connect() as c:
            r = c.execute("SELECT data FROM settings WHERE id=1").fetchone()
        return json.loads(r[0]) if r else {}

    def set_settings(self, settings: dict):
        with self.connect() as c:
            c.execute("INSERT OR REPLACE INTO settings VALUES(1,?)", (json.dumps(settings),))

    def cache_get(self, key: str):
        with self.connect() as c:
            r = c.execute("SELECT data FROM cache WHERE key=?", (key,)).fetchone()
        return json.loads(r[0]) if r else None

    def cache_put(self, key: str, value: Any):
        with self.connect() as c:
            c.execute("INSERT OR REPLACE INTO cache VALUES(?,?)", (key, json.dumps(value)))
