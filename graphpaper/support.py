"""Conservative source-anchor audit of a reviewer's sampled factual claims."""
from __future__ import annotations
from .models import Project


def audit_claims(project: Project, claims: list) -> dict:
    """A matching quote is not proof of entailment. Keep that distinction explicit."""
    sources = {s.id: s for s in project.sources if s.enabled and s.role == "evidence"}
    rows = []
    for claim in claims[:12]:
        if not isinstance(claim, dict):
            continue
        quotes = []
        for q in claim.get("quotes", [])[:6]:
            if not isinstance(q, dict):
                continue
            sid, quote = str(q.get("source_id", "")), str(q.get("quote", ""))[:3000]
            s = sources.get(sid)
            pos = s.text.find(quote) if s and quote.strip() else -1
            quotes.append({"source_id": sid, "quote": quote, "exact_match": pos >= 0, "start": pos, "end": pos + len(quote) if pos >= 0 else -1})
        support = str(claim.get("support", "unknown"))
        if support not in {"supported", "partial", "unsupported", "inference", "opinion", "unknown"}:
            support = "unknown"
        if support == "supported" and (not quotes or not all(q["exact_match"] for q in quotes)):
            support = "unverified"
        rows.append({"claim": str(claim.get("claim", ""))[:1500], "editor_judgment": support, "quotes": quotes})
    return {"sampled_claims": rows, "scope": "At most 12 load-bearing claims selected by the editor, not exhaustive fact-checking. Exact matches verify attribution; support/entailment is a model judgment, not a deterministic proof."}
