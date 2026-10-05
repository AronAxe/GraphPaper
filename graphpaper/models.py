from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


def uid(prefix: str = "") -> str:
    return prefix + uuid4().hex[:12]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Brief(Model):
    audience: str = "Curious, intelligent general readers"
    format: str = "Long-form essay"
    voice: str = "Clear, thoughtful, specific; wit without glibness. No formulaic AI phrasing."
    direction: str = ""
    target_words: int = Field(1800, ge=200, le=20000)
    originality: int = Field(65, ge=0, le=100)
    rigor: int = Field(85, ge=0, le=100)
    genre: str = "Literary speculative fiction"
    pov: str = "Close third person"
    tense: str = "Past"
    canon: str = ""
    avoid: str = "Invented quotations, unsupported certainty, repetitive summaries, generic introductions."
    pinned_nodes: list[str] = Field(default_factory=list)
    excluded_nodes: list[str] = Field(default_factory=list)


class Source(Model):
    id: str
    title: str = Field(max_length=300)
    text: str = Field(max_length=2_000_000)
    kind: str = "text"
    role: Literal["evidence", "canon", "inspiration", "voice"] = "evidence"
    url: str = ""
    author: str = ""
    published: str = ""
    added: str = Field(default_factory=now)
    enabled: bool = True
    warnings: list[str] = Field(default_factory=list)
    digest: str = ""


class Evidence(Model):
    source_id: str
    quote: str = Field(max_length=3000)
    start: int = -1
    end: int = -1
    verified: bool = False  # exact match only; does NOT establish truth


class Node(Model):
    id: str
    label: str = Field(max_length=200)
    kind: str = "concept"
    description: str = Field(default="", max_length=4000)
    evidence: list[Evidence] = Field(default_factory=list)
    status: Literal["sourced", "inferred", "canon", "proposed", "imported"] = "inferred"
    community: int = 0


class Edge(Model):
    id: str = Field(default_factory=lambda: uid("e_"))
    source: str
    target: str
    relation: str = "related_to"
    description: str = Field(default="", max_length=2000)
    evidence: list[Evidence] = Field(default_factory=list)
    status: Literal["sourced", "inferred", "canon", "proposed", "imported"] = "inferred"


class Graph(Model):
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    coverage: dict[str, Any] = Field(default_factory=dict)
    engine: str = ""
    built: str = ""
    warnings: list[str] = Field(default_factory=list)


class Angle(Model):
    id: str = Field(default_factory=lambda: uid("a_"))
    title: str
    thesis: str
    hook: str = ""
    why: str = ""
    motif: str = "custom"
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    counterargument: str = ""
    scores: dict[str, float] = Field(default_factory=dict)
    decision: str = "unscored"
    score_engine: str = "none"
    score: float | None = None


class Section(Model):
    id: str = Field(default_factory=lambda: uid("sec_"))
    title: str
    purpose: str
    beats: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    target_words: int = Field(400, ge=50, le=5000)


class Review(Model):
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    scores: dict[str, Any] = Field(default_factory=dict)
    citation_audit: dict[str, Any] = Field(default_factory=dict)
    verdict: str = "Not reviewed"
    draft_hash: str = ""


class Project(Model):
    id: str = Field(default_factory=lambda: uid("p_"))
    title: str = Field(default="Untitled project", min_length=1, max_length=200)
    mode: Literal["nonfiction", "fiction"] = "nonfiction"
    created: str = Field(default_factory=now)
    updated: str = Field(default_factory=now)
    version: int = 0
    brief: Brief = Field(default_factory=Brief)
    sources: list[Source] = Field(default_factory=list)
    graph: Graph = Field(default_factory=Graph)
    angles: list[Angle] = Field(default_factory=list)
    selected_angle: str = ""
    outline: list[Section] = Field(default_factory=list)
    draft: str = ""
    review: Review = Field(default_factory=Review)
    story_state: dict[str, Any] = Field(default_factory=dict)
    activity: list[dict[str, Any]] = Field(default_factory=list)
    feedback: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "reported_cost": 0.0, "unpriced_calls": 0})
    demo: bool = False


class Settings(Model):
    provider: Literal["openrouter", "openai-compatible", "anthropic"] = "openrouter"
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = ""
    editor_model: str = ""
    extraction_model: str = ""
    max_output_tokens: int = Field(7000, ge=1000, le=64000)
    context_chars: int = Field(90000, ge=16000, le=1500000)
    jev_provider: Literal["auto", "openrouter", "typesafe", "off"] = "auto"
    jev_model: str = "jev-latest"
    graph_engine: Literal["native", "graphify"] = "native"
    graphify_executable: str = ""
    max_calls: int = Field(80, ge=5, le=500)
    max_candidates: int = Field(30, ge=6, le=80)
    refine: bool = True
    allow_cloud: bool = False
    remember_keys: bool = True
    theme: Literal["dark", "light"] = "dark"
