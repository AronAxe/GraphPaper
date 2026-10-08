from __future__ import annotations

import copy
import json
import math
import re
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from .graph import merge_graphs, mine_motifs, normalize_extraction
from .ingest import chunks, digest
from .models import Angle, Graph, Project, Review, Section, Source, now, uid
from .providers import Cancelled, Clients, ProviderError
from .storage import Store
from .support import audit_claims
from .editorial import FACTUAL_BOUNDARY, system as editorial_system, context as editorial_context, fingerprint as editorial_fingerprint, review_stamp

BOUNDARY = FACTUAL_BOUNDARY


@dataclass
class Job:
    project_id: str
    action: str
    id: str = field(default_factory=lambda: uid("j_"))
    state: str = "queued"
    progress: int = 0
    messages: list = field(default_factory=list)
    error: str = ""
    cancel: threading.Event = field(default_factory=threading.Event)
    usage: dict = field(default_factory=lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "reported_cost": 0.0, "unpriced_calls": 0})
    receipts: list = field(default_factory=list)
    created: str = field(default_factory=now)
    finished: str = ""

    def check(self):
        if self.cancel.is_set():
            raise Cancelled("Cancelled. Completed provider calls may still be billed.")

    def note(self, text, progress=None):
        self.check()
        self.messages.append({"time": now(), "text": text})
        self.messages = self.messages[-100:]
        if progress is not None:
            self.progress = progress

    def before_call(self, label, maximum):
        self.check()
        if self.usage["calls"] >= maximum:
            raise ValueError(f"This run reached the {maximum}-request budget. Increase the limit deliberately in Connections; your previous project state is intact.")
        self.usage["calls"] += 1
        # Each request remains unpriced until an actual provider cost is returned.
        self.usage["unpriced_calls"] += 1

    def record_usage(self, label, usage, model):
        inp = usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0
        out = usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0
        self.usage["input_tokens"] += int(inp)
        self.usage["output_tokens"] += int(out)
        cost = usage.get("cost")
        if isinstance(cost, (float, int)) and not isinstance(cost, bool) and math.isfinite(cost) and cost >= 0:
            self.usage["reported_cost"] += cost
            self.usage["unpriced_calls"] = max(0, self.usage["unpriced_calls"] - 1)
        else:
            cost = None
        self.receipts.append({"stage": label, "model": model, "input_tokens": inp, "output_tokens": out, "cost": cost})

    def public(self):
        return {k: getattr(self, k) for k in ["id", "project_id", "action", "state", "progress", "messages", "error", "usage", "receipts", "created", "finished"]}


def dumps(value):
    return json.dumps(value, ensure_ascii=False, indent=1)


def graph_fingerprint(p: Project, clients: Clients):
    return digest(dumps({"sources": [(s.id, s.digest, s.role, s.enabled) for s in p.sources], "mode": p.mode,
                         "model": clients.settings.extraction_model or clients.settings.model}))


def build_graph(p: Project, clients: Clients, store: Store, job: Job):
    sources = [s for s in p.sources if s.enabled and s.role != "voice"]
    if not sources:
        if p.mode == "fiction" and (p.brief.direction.strip() or p.brief.canon.strip()):
            text = p.brief.direction + "\n\n" + p.brief.canon
            s = Source(id="S" + str(max([int(s.id[1:]) for s in p.sources if re.fullmatch(r"S\d+", s.id)] + [0]) + 1), title="Creative brief", text=text, role="canon", digest=digest(text))
            p.sources.append(s)
            sources = [s]
        else:
            raise ValueError("Add a source first, or give your fiction project a premise in Direction.")
    parts = [(s, a, b, t) for s in sources for a, b, t in chunks(s.text)]
    if clients.settings.graph_engine != "graphify" and len(parts) > 350:
        raise ValueError(f"This library requires {len(parts)} extraction chunks. Split it into projects or import an existing graph.")
    graphs = []
    if clients.settings.graph_engine == "graphify":
        from .graphify_adapter import run_graphify
        result = run_graphify(p, clients, job)
        job.check()
        p.graph = result
        p.angles, p.selected_angle = [], ""
        job.note(f"External Graphify complete: {len(result.nodes)} nodes and {len(result.edges)} edges. No duplicate Native extraction pass.", 95)
        return
    for i, (source, a, b, text) in enumerate(parts):
        job.note(f"Reading {source.title} · passage {i + 1} of {len(parts)}", 5 + int(80 * i / len(parts)))
        cachekey = digest("extract-v1|" + source.id + "|" + source.digest + "|" + source.role + "|" + p.mode + "|" + (clients.settings.extraction_model or clients.settings.model) + "|" + clients.settings.base_url + "|" + str(a))
        cached = store.cache_get(cachekey)
        if cached:
            g = Graph.model_validate(cached)
        else:
            schema = {"nodes": [{"id": "local1", "label": "specific concept or claim", "kind": "claim|person|concept|event|character|place|theme|rule", "description": "attributed meaning, not just a keyword", "evidence": [{"quote": "verbatim substring from passage"}]}], "edges": [{"source": "local1", "target": "local2", "relation": "supports|challenges|causes|enables|contrasts_with|motivates|desires|conflicts_with|reveals|precedes|related_to", "description": "why this relationship is present", "evidence": [{"quote": "verbatim substring"}]}]}
            prompt = f"Extract a useful, selective {'story/continuity' if p.mode == 'fiction' else 'claim/evidence'} graph. Prefer 8–25 meaningful nodes, not a node for every word. Use shared canonical labels. Extract opposing claims too. Distinguish attribution from endorsement. For unsupported interpretations, leave evidence empty. Preserve names, causal order and negation. Do not infer causality from co-occurrence. Exact quotes must occur in this passage. Return this shape:\n{dumps(schema)}\n\nSOURCE ID: {source.id}\nROLE: {source.role}\nTITLE: {source.title}\nPASSAGE:\n{text}"
            raw = clients.complete(BOUNDARY, prompt, role="extraction", json_mode=True)
            if not isinstance(raw.get("nodes"), list) or not isinstance(raw.get("edges"), list):
                raise ProviderError("Extraction schema missing nodes or edges. Old graph preserved.")
            g = normalize_extraction(raw, source, a, b)
            if not g.nodes:
                raise ProviderError(f"No concepts were extracted from {source.title}. No partial graph was installed.")
            store.cache_put(cachekey, g.model_dump())
        graphs.append(g)
    g = merge_graphs(graphs)
    g.coverage = {"sources": len(sources), "chunks": len(parts), "processed_chunks": len(parts), "characters": sum(len(s.text) for s in sources), "fingerprint": graph_fingerprint(p, clients)}
    g.warnings = list(dict.fromkeys(w for s in sources for w in s.warnings))
    bad_quotes = sum(not ev.verified for n in g.nodes for ev in n.evidence) + sum(not ev.verified for e in g.edges for ev in e.evidence)
    if bad_quotes:
        g.warnings.append(f"{bad_quotes} extracted quote anchors did not exactly match the text. These are flagged, not accepted as evidence.")
    p.graph = g
    p.angles, p.selected_angle = [], ""
    job.note(f"Graph ready: {len(g.nodes)} concepts and {len(g.edges)} relationships. All {len(parts)} text passages processed.", 95)


def compact_motif(c):
    return {"id": c["id"], "motif": c["motif"], "nodes": [{"id": n["id"], "label": n["label"], "description": n["description"][:500]} for n in c["nodes"]], "edges": [{"relation": e["relation"], "description": e["description"][:350], "status": e["status"], "evidence": [{"source_id": v["source_id"], "quote": v["quote"][:400]} for v in e["evidence"] if v["verified"]][:3]} for e in c["edges"]], "source_ids": c["source_ids"], "source_context": c.get("source_context", [])}


def make_angles(p: Project, clients: Clients, job: Job):
    if not p.graph.nodes:
        raise ValueError("Build or import a graph first.")
    if any(w.startswith("Sources changed after") for w in p.graph.warnings):
        raise ValueError("Sources changed since this graph was built. Rebuild it before discovering angles; unchanged extraction chunks are cached.")
    author_context = editorial_context(p, include_selection=False)
    judge_context = editorial_context(p, compact=True, include_selection=False)
    candidates = mine_motifs(p, clients.settings.max_candidates)
    if not candidates:
        # Single-node graph can still seed an angle; never fake a path.
        for n in p.graph.nodes[:6]:
            if n.id not in p.brief.excluded_nodes:
                candidates.append({"id": "m_" + n.id, "motif": "single concept", "nodes": [n.model_dump()], "edges": [], "node_ids": [n.id], "edge_ids": [], "source_ids": sorted({e.source_id for e in n.evidence if e.verified}), "structural_rank": 0})
    if not candidates:
        raise ValueError("No concepts remain after exclusions.")
    if p.graph.coverage.get('engine') == 'external_graphify':
        # File provenance is a retrieval pointer, not verified entailment. Give
        # the evaluator bounded original passages rather than trusting a label.
        source_index = {s.id:s for s in p.sources if s.enabled and s.role != 'voice'}
        for c in candidates:
            c['source_ids'] = sorted(set(c['source_ids']) | {sid for n in c['nodes'] for sid in n.get('source_ids',[]) if sid in source_index})
            c['source_context'] = []
            for sid in c['source_ids'][:3]:
                source = source_index.get(sid)
                if source is None: continue
                positions = [source.text.lower().find(n['label'].lower()) for n in c['nodes'] if len(n['label']) > 2]
                found = [v for v in positions if v >= 0]
                start = max(0, min(found)-180) if found else 0
                c['source_context'].append({'source_id':sid,'role':source.role,'text':source.text[start:start+1000],
                    'scope':'Retrieved source excerpt, not proof that the proposed relationship follows.'})
    job.note(f"Discovered {len(candidates)} diverse paths and motifs.", 10)
    for offset in range(0, len(candidates), 4):
        batch = candidates[offset:offset + 4]
        state = {"mode": p.mode, "brief": p.brief.model_dump(), "candidates": [compact_motif(c) for c in batch], **judge_context}
        questions = {}
        for i, c in enumerate(batch):
            for key, question in {
                "valuable": "Could this candidate sustain a distinctive, compelling piece in the requested genre and author voice, rather than a neutralized substitute?",
                "grounded": "Are the empirical premises anchored to supplied evidence or canon? Do not demand experimental proof for a value judgment or mistake an explicit analogy for a claim of causal identity.",
                "fit": "Does this candidate serve the author's actual thesis and direction without replacing a judgment with an unresolved question or a more moderate position?",
                "spurious": "Does this candidate invent an empirical or causal connection? Assess facts separately from values; a bold moral judgment or explicitly rhetorical analogy is not a spurious factual claim merely because it is forceful.",
            }.items():
                questions[f"c{i}_{key}"] = {"type": "noul", "instructions": f"Evaluate candidate {c['id']} only. {question}"}
        answers = clients.decide(state, questions)
        for i, c in enumerate(batch):
            if answers:
                c["scores"] = {key: answers[f"c{i}_{key}"]["noul"] for key in ["valuable", "grounded", "fit", "spurious"]}
                sc = c["scores"]
                c["priority"] = sc["valuable"] * 0.4 + sc["fit"] * 0.3 + sc["grounded"] * 0.2 + (1 - sc["spurious"]) * 0.1
            else:
                c["priority"] = c["structural_rank"]
        job.note(f"{'JEV inspected' if answers else 'Structurally explored (unscored)'} {min(offset + 4, len(candidates))}/{len(candidates)} motifs.", 15 + int(45 * (offset + len(batch)) / len(candidates)))
    ranked = sorted(candidates, key=lambda x: x["priority"], reverse=True)
    selected = []
    counts = defaultdict(int)
    for c in ranked:
        if counts[c["motif"]] < 2:
            selected.append(c)
            counts[c["motif"]] += 1
        if len(selected) == 8:
            break
    prompt = {"task": "Propose up to six genuinely different article theses or story premises from these graph structures, following the editorial contract and supplied author voice. In Polemic or argument-led nonfiction, produce different sharp routes into the author's thesis, not six softened positions or open questions about whether the author may hold it. Write the actual thesis in a publishable voice, not a prospectus beginning The essay would ask or examine. In exploratory work, discover genuinely distinct interpretations without manufacturing balance. Fiction: give an agent a desire, obstacle, stakes, choice and earned change. A real factual limitation may appear in questions; it need not swallow the thesis. Every candidate must cite one of the supplied motif_ids.",
              "mode": p.mode, "brief": p.brief.model_dump(), "motifs": [compact_motif(c) for c in selected], **author_context,
              "output_schema": {"angles": [{"title": "Working title", "thesis": "Precise one-paragraph thesis or premise", "hook": "Potential opening", "why": "What is distinctive and why it matters", "motif_ids": ["m_1"], "counterargument": "Optional directly relevant challenge or dramatic counterforce; empty when none is material", "questions": ["A concrete research or continuity question"], "evaluation_questions": ["One yes/no editorial test specific to this candidate"]}]}}
    raw = clients.complete(editorial_system(p, 'angles'), dumps(prompt), json_mode=True)
    result = []
    index = {c["id"]: c for c in candidates}
    for a in raw.get("angles", [])[:6]:
        refs = [index[k] for k in a.get("motif_ids", []) if k in index]
        if not refs or not a.get("title") or not a.get("thesis"):
            continue
        angle = Angle(title=str(a["title"])[:300], thesis=str(a["thesis"])[:4000], hook=str(a.get("hook", ""))[:2000], why=str(a.get("why", ""))[:2500], counterargument=str(a.get("counterargument", ""))[:2500], questions=[str(q)[:500] for q in a.get("questions", [])[:8]], motif=" + ".join(dict.fromkeys(c["motif"] for c in refs)), node_ids=list(dict.fromkeys(n for c in refs for n in c["node_ids"])), edge_ids=list(dict.fromkeys(e for c in refs for e in c["edge_ids"])), source_ids=sorted({s for c in refs for s in c["source_ids"]}))
        state = {"brief": p.brief.model_dump(), "mode": p.mode, "angle": angle.model_dump(), "evidence": [compact_motif(c) for c in refs], **judge_context}
        qs = {"editorial_potential": {"type": "noul", "instructions": "Is this a coherent, compelling angle that fulfills this author's intended argument and voice, without compulsory balance or a generic restatement?"}, "evidence_fit": {"type": "noul", "instructions": "Do supplied sources support the actual factual premises? Preserve the distinction between those premises and the author's moral judgment, analogy or interpretation. Do not penalize a stance for lacking neutrality."}, "needs_research": {"type": "noul", "instructions": "Is essential evidence missing for a specific factual premise actually asserted here? Mere uncertainty about consciousness, an untestable value judgment or a remote objection to an argument not made does not alone require more research."}}
        for i, q in enumerate(a.get("evaluation_questions", [])[:2]):
            qs[f"tailored_{i}"] = {"type": "noul", "instructions": str(q)[:500]}
        qs['stance_fidelity'] = {'type':'noul',"instructions":"Does this angle preserve the stated author position and requested purpose, instead of reopening it as a neutral inquiry or substituting a compromise? For exploratory work, does it genuinely explore the question?"}
        qs['voice_fidelity'] = {'type':'noul','instructions':'Does this angle match the supplied voice, rhetorical habits and requested force, rather than generic committee prose?'}
        scores = clients.decide(state, qs)
        if scores:
            angle.scores = {k: v["noul"] for k, v in scores.items()}
            angle.score = round(100 * (0.45 * angle.scores["editorial_potential"] + 0.25 * angle.scores["stance_fidelity"] + 0.15 * angle.scores["voice_fidelity"] + 0.15 * angle.scores["evidence_fit"]), 1)
            angle.score_engine = "JEV editorial estimate (not a truth probability)"
            angle.decision = "Research first" if angle.scores["needs_research"] > 0.65 else "Ready to develop"
        result.append(angle)
    if not result:
        raise ProviderError("No valid, graph-grounded angles returned. Your previous angles are unchanged.")
    if clients.jev_route() != "off":
        result.sort(key=lambda a: a.score or 0, reverse=True)
    p.angles = result
    p.angles_context_hash = editorial_fingerprint(p)
    p.selected_angle = ""  # human selects; do not silently force highest-scored opinion
    job.note(f"{len(result)} angles ready. Choose one, edit its thesis, or write your own.", 95)


def selected_angle(p: Project):
    a = next((a for a in p.angles if a.id == p.selected_angle), None)
    if not a:
        raise ValueError("Choose an angle first, or add a custom angle.")
    return a


def source_pack(p: Project, query: str, limit=38000, ids=None):
    """Diverse, bounded relevant passages with stable source labels. Explicit coverage."""
    sources = [s for s in p.sources if s.enabled and s.role != "voice"]
    terms = set(re.findall(r"\w{4,}", query.casefold()))
    selected_nodes = set(p.brief.pinned_nodes)
    if p.selected_angle:
        selected_nodes.update(next((a.node_ids for a in p.angles if a.id == p.selected_angle), []))
    anchored = defaultdict(list)
    for n in p.graph.nodes:
        if n.id in selected_nodes:
            for e in n.evidence:
                if e.verified:
                    anchored[e.source_id].append(e.quote)
    items = []
    for s in sources:
        for a, b, text in chunks(s.text, 5500, 200):
            rank = sum(min(text.casefold().count(t), 5) for t in terms) + (6 if ids and s.id in ids else 0)
            rank += 10 * sum(q in text for q in anchored[s.id])
            items.append({"source_id": s.id, "title": s.title, "role": s.role, "start": a, "end": b, "text": text, "rank": rank, "url": s.url, "published": s.published})
    items.sort(key=lambda x: x["rank"], reverse=True)
    chosen, size, seen = [], 0, set()
    # One passage per source first, then ranked remainder; source count may exceed budget.
    first = []
    for item in items:
        if item["source_id"] not in seen:
            first.append(item)
            seen.add(item["source_id"])
    order = first + [i for i in items if i not in first]
    for item in order:
        n = len(dumps(item))
        if size + n <= limit:
            chosen.append({k: v for k, v in item.items() if k != "rank"})
            size += n
    return {"passages": chosen, "retrieved_passages": len(chosen), "total_passages": len(items), "note": "Selected source passages, not the whole corpus. Do not cite content not supplied here."}


def voice_notes(p: Project):
    from .voice import voice_context
    return voice_context(p)


def make_outline(p: Project, clients: Clients, job: Job):
    a = selected_angle(p)
    job.note("Designing the argument / dramatic progression before writing prose.", 20)
    pack = source_pack(p, a.thesis, min(38000, clients.settings.context_chars // 2), a.source_ids)
    schema = {"sections": [{"title": "Section title or scene label", "purpose": "What changes for the reader here", "beats": ["Specific beat, mechanism or evidence to develop"], "source_ids": ["S1"], "target_words": 400}]}
    raw = clients.complete(editorial_system(p, 'outline'), dumps({"task": "Build an editable outline. Nonfiction and Polemic: each section advances the author's selected thesis in a distinct way. Address an objection only when it materially bears on that thesis; no mandatory opposing-view or compromise section. No obligatory generic introduction or summary. Fiction: scene-driven desire, tension, consequential choices, subtext, sensory specifics, a satisfying but not necessarily resolved ending. Respect canon. Use 3–12 sections/scenes, approximately 500–1500 words each for longer pieces. Allocate target words to match the brief. Flag missing evidence within beats; never manufacture it.", "mode": p.mode, "brief": p.brief.model_dump(), "angle": a.model_dump(), "sources": pack, "schema": schema, **editorial_context(p)}), json_mode=True)
    valid = {s.id for s in p.sources if s.enabled and s.role != "voice"}
    outline = []
    for item in raw.get("sections", [])[:20]:
        item["source_ids"] = [str(s) for s in item.get("source_ids", []) if s in valid]
        outline.append(Section.model_validate(item))
    if not outline:
        raise ProviderError("The model returned no outline sections.")
    if len(outline) * 50 > p.brief.target_words or len(outline) * 5000 < p.brief.target_words:
        raise ProviderError("The proposed section count cannot accommodate the target length. Adjust target words or regenerate the outline.")
    total = sum(s.target_words for s in outline)
    for s in outline:
        s.target_words = min(5000, max(50, round(s.target_words / total * p.brief.target_words)))
    delta = p.brief.target_words - sum(s.target_words for s in outline)
    while delta:
        for s in outline:
            step = 1 if delta > 0 else -1
            if 50 <= s.target_words + step <= 5000:
                s.target_words += step
                delta -= step
            if not delta:
                break
    p.outline = outline
    p.outline_context_hash = review_stamp(p)
    job.note("Outline ready. Reorder or edit the sections before drafting.", 95)


def citation_audit(p: Project, text: str):
    if p.mode == "fiction":
        return {"mode": "fiction", "note": "Fiction is checked against canon by the editor; narrative claims are not forced to carry citations."}
    allowed = {s.id for s in p.sources if s.enabled and s.role == "evidence"}
    refs = set(re.findall(r"\[(S\d+)\]", text))
    used = sorted(refs & allowed)
    return {"valid_references": used, "unknown_or_ineligible_references": sorted(refs - allowed), "missing_all_citations": not refs and bool(allowed), "note": "Deterministic reference integrity only. Valid IDs do not prove that the source supports the claim. Read the editorial issues and source excerpts."}


def review_draft(p: Project, clients: Clients, job: Job, text=None) -> Review:
    text = p.draft if text is None else text
    if not text.strip():
        raise ValueError("Write or generate a draft first.")
    job.note("Editorial review: structure, specificity, evidence / continuity and voice.", 80)
    pack = source_pack(p, text[:5000], min(30000, clients.settings.context_chars // 3))
    review_schema = {"summary": "Short honest editorial assessment", "strengths": ["specific strength"], "issues": [{"severity": "critical|major|minor", "category": "evidence|logic|continuity|voice|structure|craft|authorial_drift|irrelevant_caveat", "excerpt": "exact draft excerpt", "problem": "specific problem", "suggestion": "concrete repair", "source_ids": ["S1"]}], "suggestions": ["useful revision instruction"], "verdict": "Ready for author review / Needs revision / Needs evidence", "claims": [{"claim": "One load-bearing factual claim from the draft", "support": "supported|partial|unsupported|inference|opinion|unknown", "quotes": [{"source_id": "S1", "quote": "verbatim supporting passage supplied here"}]}]}
    review_schema['authorial_assessment'] = {'intent_preserved': True, 'stance_preserved': True, 'voice_preserved': True,
        'summary': 'Specific observations about fidelity to the supplied authorial contract; no ideological moderation score.'}
    raw = clients.complete(editorial_system(p, 'review'), dumps({"task": "Act as a rigorous but not formulaic developmental editor. Identify consequential flaws, not busywork. For nonfiction check attribution, inference, invented numbers, quotations, cited-source support and fidelity to the author's actual argument. Flag irrelevant caveats and softened conclusions; do not penalize forceful moral judgments or require an opposing view merely for balance. Any unavailable evidence is unknown, not a pass. For fiction check character desire, agency, causality, canon/timeline, stakes, repetitive beats, emotional precision, prose and ending. Quote the actual draft for issues. Do not rate your own certainty numerically. Do not rewrite yet. Nonfiction and Polemic: audit up to 12 load-bearing factual claims with exact source quotes. A moral evaluation, rhetorical analogy or explicitly signalled inference is not an empirical result; do not require a paper proving the author is entitled to hold it. Do not label a claim supported unless the supplied quote actually entails it; distinguish opinion and inference. Fiction: return an empty claims array.", "mode": p.mode, "brief": p.brief.model_dump(), "draft": text, "sources": pack, "schema": review_schema, **editorial_context(p)}), role="editor", json_mode=True)
    review = Review(summary=str(raw.get("summary", "")), strengths=[str(x) for x in raw.get("strengths", [])[:10]], issues=[x for x in raw.get("issues", [])[:30] if isinstance(x, dict)], suggestions=[str(x) for x in raw.get("suggestions", [])[:10]], verdict=str(raw.get("verdict", "Needs author review")), citation_audit=citation_audit(p, text), draft_hash=digest(text))
    review.context_hash = review_stamp(p)
    assessment = raw.get('authorial_assessment')
    if isinstance(assessment, dict):
        review.authorial_assessment = {k:v for k,v in assessment.items() if k in {'intent_preserved','stance_preserved','voice_preserved','summary'} and (type(v)==bool or (k=='summary' and isinstance(v,str)))}
    if p.mode != "fiction":
        review.citation_audit.update(audit_claims(p, raw.get("claims", [])))
        for claim in review.citation_audit["sampled_claims"]:
            if claim["editor_judgment"] in {"unverified", "unsupported"}:
                review.issues.append({"severity": "major", "category": "evidence", "problem": "Source support has not been established for: " + claim["claim"], "suggestion": "Verify the original source, attribute the statement more carefully, or remove it."})
    # State-specific JEV questions steer the next action, not just a generic score.
    findings = {"mode": p.mode, "brief": p.brief.model_dump(), "editorial_findings": raw, "citation_audit": review.citation_audit, **editorial_context(p,compact=True)}
    questions = {"action": {"type": "choice", "instructions": "Given these editorial findings and the authorial contract, which action is most appropriate? Do not mistake a value judgment for missing empirical evidence. Authorial drift calls for restoring the intended argument, not moderating it. Real unsupported factual premises still need correction.", "criteria": {"research": "A specifically identified, essential factual premise or canon detail is missing. Not merely moral disagreement, forceful language or a hypothetical objection.", "revise": "Known fixable issues require a prose/structure/logic revision.", "author_review": "The draft is ready for human editorial review, not automatic publication."}}, "material_issue": {"type": "noul", "instructions": "Do the findings identify a consequential factual, logical, canon or narrative flaw?"}}
    decisions = clients.decide(findings, questions)
    if decisions:
        review.scores = decisions
        review.verdict = {"research": "Research / canon clarification needed", "revise": "Revision recommended", "author_review": "Ready for author review"}[decisions["action"]["choice"]]
    audit = review.citation_audit
    if audit.get("unknown_or_ineligible_references") or audit.get("missing_all_citations"):
        review.verdict = "Citation repair required"
    return review


def revise(p: Project, clients: Clients, job: Job, store: Store, instruction="", automatic=False):
    if not p.draft.strip():
        raise ValueError("There is no draft to revise.")
    original = p.draft
    review = review_draft(p, clients, job) if not p.review.summary or p.review.draft_hash != digest(p.draft) or p.review.context_hash != review_stamp(p) else p.review
    pack = source_pack(p, (instruction or review.summary) + original[:4000], min(28000, clients.settings.context_chars // 3))
    job.note("Revising the draft without changing its intended thesis or fictional canon.", 87)
    revised = clients.complete(editorial_system(p, 'revise'), dumps({"task": "Revise this complete piece. Preserve its best lines, nuance, voice, factual limits and intentional ending. Fix material issues rather than flattening style. Do not add unsupported claims. Return the complete revised Markdown only, not a critique or preface. Source citations remain [S1] format. Fiction has no inline scholarly citations.", "mode": p.mode, "brief": p.brief.model_dump(), "author_instruction": instruction, "review": review.model_dump(), "draft": original, "sources": pack, **editorial_context(p)}), role="editor")
    # Invalid references cannot be accepted through an automated revision gate.
    audit = citation_audit(p, revised)
    candidate_project = p.model_copy(deep=True)
    candidate_project.draft = revised
    store.snapshot(candidate_project, "AI revision candidate")
    if automatic:
        comparisons = []
        if len(original) + len(revised) < 40000:
            comparisons = clients.decide({"mode": p.mode, "brief": p.brief.model_dump(), "original": original, "candidate": revised, "known_issues": review.model_dump(), **editorial_context(p,compact=True)}, {"prefer_revision": {"type": "noul", "instructions": "Does the candidate materially improve the known issues while preserving the author's thesis, stance, rhetorical force, wit, meaningful empirical qualifiers and fictional canon? A more moderate, balanced or polite version is not automatically better. Reject a candidate that turns the intended argument into an unresolved inquiry unless the author requested that change."}})
        accepted = bool(comparisons and comparisons["prefer_revision"]["noul"] >= 0.6)
        accepted = accepted and not audit.get("unknown_or_ineligible_references") and not audit.get("missing_all_citations")
        if not accepted:
            p.review = review
            job.note("Kept the original: the automatic acceptance gate did not confirm a better revision. Candidate saved in Versions.")
            return
    p.draft = revised
    p.review = review_draft(p, clients, job)


def write_draft(p: Project, clients: Clients, store: Store, job: Job):
    a = selected_angle(p)
    if not p.outline:
        raise ValueError("Create and approve an outline before drafting.")
    from .argument_draft import use_whole_draft, write_whole_argument
    if use_whole_draft(p):
        return write_whole_argument(p, clients, store, job)
    draft_sections = []
    ledger = {}
    for i, section in enumerate(p.outline):
        job.note(f"Writing {i + 1}/{len(p.outline)} · {section.title}", 10 + int(60 * i / len(p.outline)))
        pack = source_pack(p, a.thesis + "\n" + section.purpose + "\n" + " ".join(section.beats), min(38000, clients.settings.context_chars // 2), section.source_ids)
        prompt = {"task": "Write only this section/scene, approximately its target_words. No title/heading, preamble, references list or summary of the whole piece. Nonfiction and Polemic: cite material factual claims using exactly [S1] etc, only evidence-role sources supplied here; preserve attribution and specific empirical limits without attaching generic uncertainty to moral judgments. Do not cite inspiration or fictional canon as real-world evidence. Missing evidence must be avoided or explicitly attributed as unresolved. Do not turn the separate counterargument metadata into a compulsory paragraph. Preserve rhetorical force and answer only objections that actually matter here. Fiction: show consequential scenes, specific actions, subtext, varied rhythm; no citations and no mechanical explanation of the theme. Preserve canon; do not resolve later scenes prematurely. Avoid repeating the previous section or announcing the next one.", "mode": p.mode, "brief": p.brief.model_dump(), "angle": a.model_dump(), "whole_outline": [s.model_dump() for s in p.outline], "current_section": section.model_dump(), "previous_prose_for_continuity": "\n\n".join(draft_sections)[-9000:], "story_ledger": ledger, "source_passages": pack, **editorial_context(p)}
        text = clients.complete(editorial_system(p, 'draft'), dumps(prompt))
        draft_sections.append(("## " + section.title + "\n\n" if p.mode != "fiction" else "") + text)
        # Recoverable checkpoints never replace the current editor document.
        checkpoint = p.model_copy(deep=True)
        checkpoint.draft = "# " + a.title + "\n\n" + ("\n\n" if p.mode != "fiction" else "\n\n* * *\n\n").join(draft_sections)
        store.snapshot(checkpoint, f"Draft checkpoint {i + 1}/{len(p.outline)}")
        if p.mode == "fiction":
            ledger = clients.complete(editorial_system(p, 'draft'), dumps({"task": "Update a compact continuity ledger from this newly written scene. Record only what the text establishes; do not invent events, retcon canon or write the next scene. Preserve prior facts unless this scene explicitly changes them. Limit to 5,000 characters total. Return JSON with characters (name, location, wants, knowledge), chronology, objects, unresolved_threads, resolved_threads, and canon_conflicts (specific conflicts with author canon, if any).", "author_canon": p.brief.canon, "previous_ledger": ledger, "new_scene": text}), role="extraction", json_mode=True)
            if len(dumps(ledger)) > 10000:
                raise ProviderError("Continuity ledger exceeded its size limit. Draft checkpoint saved; choose a more instruction-following extraction model.")
    p.story_state = ledger
    p.draft = "# " + a.title + "\n\n" + ("\n\n" if p.mode != "fiction" else "\n\n* * *\n\n").join(draft_sections)
    p.review = review_draft(p, clients, job)
    store.snapshot(p, "Complete first draft")
    if clients.settings.refine and p.review.scores.get("action", {}).get("choice") == "revise":
        revise(p, clients, job, store, automatic=True)
    job.note("Draft ready for your review. Sources and all saved versions remain available.", 98)


class Runner:
    def __init__(self, store, vault, settings_factory):
        self.store, self.vault, self.settings_factory = store, vault, settings_factory
        self.jobs: dict[str, Job] = {}
        self.lock = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="graphpaper")
        self.clients_factory = Clients

    def active(self, project_id):
        return next((j for j in self.jobs.values() if j.project_id == project_id and j.state in {"queued", "running"}), None)

    def start(self, project_id, action, instruction=""):
        if action not in {"graph", "angles", "outline", "draft", "review", "revise", "voice", "humanize", "deslop", "both", "science-plan", "science-search", "science-fulltext", "science-appraise", "science-outline", "science-draft", "science-review"}:
            raise ValueError("Unknown action")
        with self.lock:
            if self.active(project_id):
                raise ValueError("This project already has an active job. Wait or cancel it before starting another.")
            p = self.store.get(project_id)
            settings = self.settings_factory()
            job = Job(project_id, action)
            self.jobs[job.id] = job
            # Keep completed status history bounded; project activity remains in SQLite.
            for old in list(self.jobs.values())[:-150]:
                if old.state not in {"queued", "running"}:
                    self.jobs.pop(old.id, None)
            self.pool.submit(self._run, job, p, settings, instruction)
            return job

    def _run(self, job, p, settings, instruction):
        base = p.version
        job.state = "running"
        clients = self.clients_factory(settings, self.vault, job)
        try:
            self.store.snapshot(p, "Before " + job.action)
            if job.action.startswith('science-') or (p.mode == 'science' and job.action in {'outline','draft','review'}):
                if p.mode != 'science': raise ValueError('Create a Science project for scholarly research.')
                from . import science
                task = job.action.removeprefix('science-')
                if task == 'plan': science.plan_search(p, clients, job)
                else:
                    tasks = {'search':science.search_literature,'fulltext':science.fetch_fulltexts,'appraise':science.appraise,
                             'outline':science.outline_science,'draft':science.draft_science,'review':science.review_science}
                    tasks[task](p, clients, self.store, job)
            elif job.action == "voice":
                from .voice import learn_voice
                learn_voice(p, clients, job)
            elif job.action in {"humanize", "deslop", "both"}:
                from .polish import polish_draft
                polish_draft(p, clients, job, job.action, instruction)
            elif job.action == "graph":
                build_graph(p, clients, self.store, job)
            elif job.action == "angles":
                make_angles(p, clients, job)
            elif job.action == "outline":
                make_outline(p, clients, job)
            elif job.action == "draft":
                write_draft(p, clients, self.store, job)
            elif job.action == "review":
                p.review = review_draft(p, clients, job)
            elif job.action == "revise":
                revise(p, clients, job, self.store, instruction)
            job.check()
            self._add_accounting(p, job, state="completed")
            self.store.save(p, base)
            self.store.snapshot(p, "After " + job.action)
            job.progress, job.state = 100, "completed"
        except Cancelled:
            job.state, job.error = "cancelled", "Cancelled. Completed/ongoing provider calls may still be billed; draft checkpoints are in Versions."
            self._save_failed_accounting(job)
        except Exception as e:
            job.state = "failed"
            job.error = str(e) if isinstance(e, (ValueError, ProviderError)) or type(e).__name__ == "Conflict" else f"{type(e).__name__}: this operation failed without replacing your work. Check settings or use a smaller project."
            self._save_failed_accounting(job)
        finally:
            job.finished = now()

    def _add_accounting(self, p, job, state=None):
        if any(a.get("job_id") == job.id for a in p.activity):
            return
        for key, value in job.usage.items():
            p.usage[key] = p.usage.get(key, 0) + value
        p.activity.append({"time": now(), "action": job.action, "usage": copy.deepcopy(job.usage), "state": state or job.state, "job_id": job.id, "receipts": copy.deepcopy(job.receipts)})
        p.activity = p.activity[-100:]

    def _save_failed_accounting(self, job):
        # Accounting never overwrites a concurrent manuscript update.
        for _ in range(3):
            try:
                p = self.store.get(job.project_id)
                version = p.version
                self._add_accounting(p, job)
                self.store.save(p, version)
                return
            except Exception:
                continue
