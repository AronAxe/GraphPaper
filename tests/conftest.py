from __future__ import annotations
import json
import pytest
from fastapi.testclient import TestClient
from graphpaper.server import create_app
from graphpaper.models import Settings
from graphpaper.providers import Clients


@pytest.fixture
def app(tmp_path, monkeypatch):
    for k in ["OPENAI_API_KEY", "OPENROUTER_API_KEY", "TYPESAFE_API_KEY", "ANTHROPIC_API_KEY", "TAVILY_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    value = create_app(tmp_path)
    yield value
    for job in value.state.runner.jobs.values():
        job.cancel.set()
    value.state.runner.pool.shutdown(wait=True, cancel_futures=True)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        c.get("/")
        c.headers["X-GraphPaper"] = "1"
        yield c


class ScriptedClients:
    """Deterministic test double. Never presented as a real model output/quality test."""
    def __init__(self, settings=None, vault=None, job=None):
        self.settings = settings or Settings(model="test/model", allow_cloud=True, max_candidates=6, refine=False)
        self.job = job
        self.calls = []

    def jev_route(self):
        return "off" if self.settings.jev_provider == "off" else "openrouter"

    def _record(self, stage):
        if self.job:
            self.job.before_call(stage, self.settings.max_calls)
            self.job.record_usage(stage, {"input_tokens": 100, "output_tokens": 50, "cost": .001}, "deterministic-test-double")

    def decide(self, state, questions):
        if self.jev_route() == "off":
            return None
        self._record("JEV")
        self.calls.append(("decide", state, questions))
        answers={}
        negative=('spurious','needs_research','added_allegation','irrelevant_caveat','meaning_drift','lost_reasoning','canon_conflict','knowledge_conflict','motivation_conflict','repetitive','material_issue','contradiction','overclaim')
        for k,q in questions.items():
            if q['type']=='noul':answers[k]={'type':'noul','noul':.1 if any(t in k for t in negative) else .85}
            elif q['type']=='choice':
                chosen='author_review' if 'author_review' in q['criteria'] else 'uncertain' if 'uncertain' in q['criteria'] else next(iter(q['criteria']))
                answers[k]={'type':'choice','choice':chosen,'probabilities':{v:float(v==chosen) for v in q['criteria']},'confidence':1}
            else:
                keys=list(map(str,range(len(q['criteria']))))
                answers[k]={'type':'score','score':len(keys)-1,'legend':dict(zip(keys,q['criteria'])),'probabilities':{v:float(v==keys[-1]) for v in keys},'confidence':1}
        return answers

    def complete(self, system, user, *, role="writer", json_mode=False, max_tokens=None):
        self._record(role)
        self.calls.append(("complete", system, user))
        if "Extract a useful" in user:
            passage = user.split("PASSAGE:\n",1)[1]
            quote = passage[:min(120,len(passage))]
            return {"nodes": [{"id":"a","label":"Shared public space","kind":"concept","description":"The shared setting","evidence":[{"quote":quote}]}, {"id":"b","label":"Individual choice","kind":"claim","description":"The choice at stake","evidence":[{"quote":quote}]}, {"id":"c","label":"Unintended consequence","kind":"event","description":"A consequence","evidence":[]}], "edges":[{"source":"a","target":"b","relation":"supports","description":"A potential connection","evidence":[{"quote":quote}]},{"source":"b","target":"c","relation":"challenges","evidence":[]}]}
        data = json.loads(user)
        task = data["task"]
        if task.startswith("Propose up to six"):
            return {"angles":[{"title":"A test direction","thesis":"Individual choices can reshape a shared place.","hook":"An opening.","why":"A relationship to investigate.","motif_ids":[data["motifs"][0]["id"]],"counterargument":"There may be competing causes.","questions":["What evidence is missing?"],"evaluation_questions":["Is the competing explanation addressed?"]}]}
        if task.startswith("Build an editable outline"):
            return {"sections":[{"title":name,"purpose":"Advance a distinct part.","beats":["A specific beat"],"source_ids":["S1"],"target_words":600} for name in ["The place","The choice","The consequence"]]}
        if task.startswith("Write the complete argumentative essay"):
            return "# A test argument\n\nA specific fact supports the case. [S1] The conclusion is a judgment, not an invented experiment."
        if task.startswith("Write only this section"):
            return "Mira shut the drawer and left the key on the sill. She had not yet chosen whom to disappoint." if data["mode"]=="fiction" else "The notes describe a choice about shared space. [S1] That observation motivates a question, not a universal conclusion."
        if task.startswith("Update a compact continuity ledger"):
            return {"characters":[{"name":"Mira","location":"archive","knowledge":"The key is on the sill"}],"chronology":["Mira closed the drawer"],"objects":["key"],"unresolved_threads":["The choice"],"resolved_threads":[],"canon_conflicts":[]}
        if task.startswith("Revise this complete piece"):
            return data["draft"] + ("\n\nShe did not turn back." if data["mode"]=="fiction" else "\n\nThe distinction remains important. [S1]")
        # Full-draft critic (both modes).
        if json_mode:
            return {"summary":"Test review: the draft is coherent.","strengths":["Distinct sections"],"issues":[],"suggestions":["Human review remains necessary."],"claims":[]}
        raise AssertionError(f"Unexpected task: {task[:100]}")
