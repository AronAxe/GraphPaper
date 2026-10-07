from __future__ import annotations

import hashlib
import itertools
import re
from collections import defaultdict, deque

import networkx as nx

from .models import Edge, Evidence, Graph, Node, Project, Source, now


def node_id(label: str, kind: str) -> str:
    norm = re.sub(r"\s+", " ", label.casefold().strip())
    return "n_" + hashlib.sha256((kind + ":" + norm).encode()).hexdigest()[:14]


def evidence(items: list, source: Source, offset=0, chunk_end=None) -> list[Evidence]:
    out = []
    for item in items[:20]:
        quote = str(item.get("quote", ""))[:3000] if isinstance(item, dict) else str(item)[:3000]
        if not quote.strip():
            continue
        pos = source.text.find(quote, offset, chunk_end)
        out.append(Evidence(source_id=source.id, quote=quote, start=pos, end=pos + len(quote) if pos >= 0 else -1, verified=pos >= 0))
    return out


def normalize_extraction(raw: dict, source: Source, offset=0, chunk_end=None) -> Graph:
    nodes, edges, mapping = {}, [], {}
    for n in raw.get("nodes", [])[:160]:
        if not isinstance(n, dict) or not str(n.get("label", "")).strip():
            continue
        label = str(n["label"])[:200]
        kind = str(n.get("kind", "concept"))[:40].lower()
        ident = node_id(label, kind)
        ev = evidence(n.get("evidence", []), source, offset, chunk_end)
        status = "canon" if source.role == "canon" and any(e.verified for e in ev) else "sourced" if any(e.verified for e in ev) else "inferred"
        nodes[ident] = Node(id=ident, label=label, kind=kind, description=str(n.get("description", ""))[:4000], evidence=ev, status=status)
        mapping[str(n.get("id", label))] = ident
        mapping[label] = ident
    for e in raw.get("edges", [])[:320]:
        if not isinstance(e, dict):
            continue
        a, b = mapping.get(str(e.get("source"))), mapping.get(str(e.get("target")))
        if not a or not b or a == b:
            continue
        ev = evidence(e.get("evidence", []), source, offset, chunk_end)
        status = "canon" if source.role == "canon" and any(v.verified for v in ev) else "sourced" if any(v.verified for v in ev) else "inferred"
        relation = str(e.get("relation", "related_to")).lower().replace(" ", "_")[:80]
        edges.append(Edge(source=a, target=b, relation=relation, description=str(e.get("description", ""))[:2000], evidence=ev, status=status))
    return Graph(nodes=list(nodes.values()), edges=edges, engine="GraphPaper evidence extraction")


def merge_graphs(graphs: list[Graph]) -> Graph:
    nodes, edges = {}, {}
    def merge_evidence(a, b):
        return list({(e.source_id, e.quote): e for e in a + b}.values())
    for g in graphs:
        for n in g.nodes:
            if n.id in nodes:
                previous = nodes[n.id]
                previous.evidence = merge_evidence(previous.evidence, n.evidence)
                if n.status in {"sourced", "canon"}:
                    previous.status = n.status
                if n.description not in previous.description:
                    previous.description = (previous.description + "\n" + n.description)[:4000]
            else:
                nodes[n.id] = n.model_copy(deep=True)
        for e in g.edges:
            key = (e.source, e.target, e.relation)
            if key in edges:
                edges[key].evidence = merge_evidence(edges[key].evidence, e.evidence)
                if e.status in {"sourced", "canon"}:
                    edges[key].status = e.status
            else:
                e = e.model_copy(deep=True)
                e.id = "e_" + hashlib.sha256("|".join(key).encode()).hexdigest()[:14]
                edges[key] = e
    result = Graph(nodes=list(nodes.values()), edges=list(edges.values()), built=now(), engine="GraphPaper evidence extraction")
    annotate(result)
    return result


def annotate(graph: Graph):
    g = nx.Graph()
    g.add_nodes_from(n.id for n in graph.nodes)
    g.add_edges_from((e.source, e.target) for e in graph.edges if e.source in g and e.target in g)
    if g.number_of_edges():
        groups = nx.community.greedy_modularity_communities(g)
    else:
        groups = [{n} for n in g]
    mapping = {n: i for i, group in enumerate(groups) for n in group}
    for n in graph.nodes:
        n.community = mapping.get(n.id, 0)


def import_graph(raw: dict) -> Graph:
    """Graphify / NetworkX node-link interoperability. Imported edges are not evidence."""
    if not isinstance(raw, dict) or not isinstance(raw.get("nodes"), list):
        raise ValueError("Expected a Graphify/NetworkX JSON object with a nodes array.")
    raw_edges = raw.get("edges", raw.get("links", []))
    if not isinstance(raw_edges, list) or len(raw["nodes"]) > 5000 or len(raw_edges) > 20000:
        raise ValueError("Import limit: 5,000 nodes / 20,000 edges.")
    nodes, ids = [], set()
    for n in raw["nodes"]:
        if not isinstance(n, dict) or "id" not in n:
            raise ValueError("Each imported node needs an ID.")
        ident = str(n["id"])[:400]
        if ident in ids:
            raise ValueError("Duplicate graph node IDs.")
        ids.add(ident)
        nodes.append(Node(id=ident, label=str(n.get("label", n.get("name", ident)))[:200], kind=str(n.get("kind", n.get("type", "concept")))[:40], description=str(n.get("description", n.get("summary", "")))[:4000], status="imported"))
    edges, skipped = [], 0
    for e in raw_edges:
        if not isinstance(e, dict):
            raise ValueError("Each imported edge must be a JSON object.")
        a, b = str(e.get("source", "")), str(e.get("target", ""))
        if a not in ids or b not in ids or a == b:
            skipped += 1
            continue
        relation = str(e.get("relation", e.get("label", e.get("type", "related_to"))))[:80]
        edges.append(Edge(source=a, target=b, relation=relation, description=str(e.get("description", e.get("reason", "")))[:2000], status="imported"))
    g = Graph(nodes=nodes, edges=edges, engine="Graphify / node-link import", built=now(), warnings=["Imported relationships are hypotheses until checked against your uploaded sources. No imported confidence is treated as evidence."])
    if skipped:
        g.warnings.append(f"Skipped {skipped} dangling or self-referencing edges.")
    annotate(g)
    return g


def mine_motifs(project: Project, limit=60) -> list[dict]:
    """Bounded motif discovery; graph structure nominates, never proves, a thesis."""
    eligible_sources = {s.id for s in project.sources if s.enabled and s.role != "voice"}
    excluded = set(project.brief.excluded_nodes)
    nodes = {n.id: n for n in project.graph.nodes if n.id not in excluded}
    edges = [e for e in project.graph.edges if e.source in nodes and e.target in nodes]
    outgoing, incoming, undirected = defaultdict(list), defaultdict(list), defaultdict(set)
    for e in edges:
        outgoing[e.source].append(e)
        incoming[e.target].append(e)
        undirected[e.source].add(e.target)
        undirected[e.target].add(e.source)
    candidates, seen = [], set()
    def add(kind, ns, es):
        key = (kind, tuple(sorted(ns)))
        if key in seen or len(candidates) >= 1500:
            return
        seen.add(key)
        ns = list(dict.fromkeys(ns))
        es = list({e.id: e for e in es}.values())
        source_ids = sorted(({v.source_id for e in es for v in e.evidence if v.verified} | {v.source_id for n in ns for v in nodes[n].evidence if v.verified} | {sid for e in es for sid in e.source_ids} | {sid for n in ns for sid in nodes[n].source_ids}) & eligible_sources)
        pin = sum(n in project.brief.pinned_nodes for n in ns)
        tension = kind in {"contradiction", "conflict", "divergence", "cross-community bridge"}
        rank = pin * 5 + len(source_ids) * 2 + int(tension) * 2 + min(len(ns), 5)
        candidates.append({"id": "m_" + str(len(candidates) + 1), "motif": kind,
                           "nodes": [nodes[n].model_dump() for n in ns], "edges": [e.model_dump() for e in es],
                           "node_ids": ns, "edge_ids": [e.id for e in es], "source_ids": source_ids, "structural_rank": rank})
    for e in edges:
        kind = "contradiction" if any(x in e.relation for x in ["contradict", "challenge", "refut", "conflict", "oppose"]) else "relationship"
        if project.mode == "fiction" and kind == "contradiction":
            kind = "conflict"
        add(kind, [e.source, e.target], [e])
        if nodes[e.source].community != nodes[e.target].community:
            add("cross-community bridge", [e.source, e.target], [e])
    for ident in nodes:
        # Bound pair expansions for high-degree nodes.
        for a, b in itertools.islice(itertools.combinations(outgoing[ident], 2), 8):
            add("divergence", [ident, a.target, b.target], [a, b])
        for a, b in itertools.islice(itertools.combinations(incoming[ident], 2), 8):
            add("convergence", [a.source, b.source, ident], [a, b])
        for e1 in outgoing[ident][:8]:
            for e2 in outgoing[e1.target][:6]:
                if e2.target != ident:
                    add("character / consequence arc" if project.mode == "fiction" else "directed chain", [ident, e1.target, e2.target], [e1, e2])
    # Relevance prefilter from explicit direction, not a fabricated probability.
    terms = set(re.findall(r"\w{4,}", project.brief.direction.lower()))
    for c in candidates:
        text = " ".join(n["label"] + " " + n["description"] for n in c["nodes"]).lower()
        c["structural_rank"] += min(5, sum(t in text for t in terms))
    candidates.sort(key=lambda c: c["structural_rank"], reverse=True)
    # Round-robin motif families preserves diversity (not just highest-degree paths).
    buckets = defaultdict(deque)
    for c in candidates:
        buckets[c["motif"]].append(c)
    result = []
    while buckets and len(result) < limit:
        for k in list(buckets):
            result.append(buckets[k].popleft())
            if not buckets[k]:
                del buckets[k]
            if len(result) >= limit:
                break
    return result


def path_between(graph: Graph, a: str, b: str):
    g = nx.Graph()
    g.add_nodes_from(n.id for n in graph.nodes)
    g.add_edges_from((e.source, e.target) for e in graph.edges)
    try:
        return nx.shortest_path(g, a, b)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []
