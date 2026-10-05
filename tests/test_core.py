from __future__ import annotations
import io
import json
import zipfile
import socket
import pytest
from pydantic import ValidationError
from graphpaper.models import Project, Source, Settings, Node, Edge, Graph, Evidence
from graphpaper.storage import Store, Conflict
from graphpaper.ingest import clean, chunks, extract, html_text, resolve_public, digest
from graphpaper.graph import normalize_extraction, merge_graphs, import_graph, mine_motifs, path_between
from graphpaper.demo import make_demo
from graphpaper.export import export, simple_html
from graphpaper.pipeline import citation_audit, source_pack, Job
from graphpaper.providers import Cancelled


def test_sqlite_optimistic_save_and_restore(tmp_path):
    store=Store(tmp_path);p=store.create(Project())
    old=store.get(p.id);p.draft="First draft";store.save(p,0);store.snapshot(p,"first")
    with pytest.raises(Conflict):store.save(old,0)
    p.draft="Second draft";store.save(p,1)
    assert store.get(p.id).draft=="Second draft"
    assert store.revisions(p.id)[0]["draft"]=="First draft"
    assert store.get(p.id).version==2
    store.delete(p.id)
    assert not store.revisions(p.id)


def test_settings_and_cache(tmp_path):
    s=Store(tmp_path);s.set_settings({"model":"abc"});assert s.settings()["model"]=="abc"
    s.cache_put("test",{"x":1});assert s.cache_get("test")=={"x":1}
    assert s.cache_get("absent") is None


@pytest.mark.parametrize("length",[1,100,14000,14001,42000,99500])
def test_chunks_cover_every_character(length):
    text=("a b c\n\n"*((length+6)//7))[:length]
    parts=list(chunks(text));covered=set()
    for a,b,t in parts:
        assert t==text[a:b];covered.update(range(a,b))
    assert covered==set(range(length))
    assert all(a2>a1 for (a1,_,_),(a2,_,_) in zip(parts,parts[1:]))


def test_import_formats_and_html_safety():
    assert extract(b"Hello\r\nworld\x00", "hello.txt")[0]=="Hello\nworld"
    assert extract("café".encode("cp1252"),"x.txt")[1]
    title,text=html_text('<title>T</title><nav>junk</nav><article>Real text<script>bad()</script></article>')
    assert title=="T" and text=="Real text"
    assert "<script>" not in simple_html('<script>alert(1)</script>')
    with pytest.raises(ValueError):extract(b"abc","program.exe")
    with pytest.raises(ValueError):clean("  ")


def test_docx_roundtrip():
    p=Project(title="Essay",draft="# A title\n\nA **bold** paragraph.")
    data,_,_=export(p,"docx");text,warnings=extract(data,"essay.docx")
    assert "A title" in text and "bold" in text and warnings


def test_pdf_blank_rejected():
    from pypdf import PdfWriter
    writer=PdfWriter();writer.add_blank_page(width=200,height=200);b=io.BytesIO();writer.write(b)
    with pytest.raises(ValueError, match="image-only"):
        extract(b.getvalue(),"scan.pdf")


@pytest.mark.parametrize("url",["file:///etc/passwd","http://user:pass@example.org", "http://example.org:8080/x"])
def test_unsafe_urls_rejected_before_connect(url):
    with pytest.raises(ValueError):resolve_public(url)


@pytest.mark.parametrize("ip",["127.0.0.1","10.0.0.1","169.254.169.254","::1","192.168.1.2"])
def test_private_dns_rejected(monkeypatch,ip):
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**k:[(None,None,None,None,(ip,80))])
    with pytest.raises(ValueError,match="Private"):resolve_public("https://example.org/a")


def test_exact_quote_is_not_invented_evidence():
    source=Source(id="S1",title="Test",text="The cat is on the mat.")
    raw={"nodes":[{"id":"cat","label":"Cat","evidence":[{"quote":"The cat is on the mat."}]},{"id":"moon","label":"Moon","evidence":[{"quote":"The cat jumped over the Moon."}]}],"edges":[{"source":"cat","target":"moon","relation":"causes","evidence":[]},{"source":"cat","target":"missing"}]}
    g=normalize_extraction(raw,source,0,len(source.text))
    assert g.nodes[0].evidence[0].verified
    assert not g.nodes[1].evidence[0].verified
    assert g.nodes[1].status=="inferred"
    assert len(g.edges)==1
    assert g.edges[0].status=="inferred"


def test_quote_offsets_restricted_to_actual_chunk():
    source=Source(id="S1",title="Test",text="First passage.\n\nSecond passage.")
    raw={"nodes":[{"id":"x","label":"x","evidence":[{"quote":"First passage."}]}],"edges":[]}
    g=normalize_extraction(raw,source,16,len(source.text))
    assert not g.nodes[0].evidence[0].verified


def test_graph_import_formats_never_trust_provenance():
    for key in ["links","edges"]:
        g=import_graph({"nodes":[{"id":"a","label":"A","status":"sourced"},{"id":"b","label":"B"}],key:[{"source":"a","target":"b","label":"supports","confidence":1}]})
        assert len(g.edges)==1 and all(n.status=="imported" for n in g.nodes)
        assert not g.edges[0].evidence
        assert path_between(g,"a","b")==["a","b"]
        assert path_between(g,"a","none")==[]


def test_merging_deduplicates_nodes_and_edges():
    source=Source(id="S1",title="Test",text="a b")
    raw={"nodes":[{"id":"a","label":"A"},{"id":"b","label":"B"}],"edges":[{"source":"a","target":"b","relation":"enables"}]}
    g=normalize_extraction(raw,source,0,3);m=merge_graphs([g,g])
    assert len(m.nodes)==2 and len(m.edges)==1


def test_motifs_respect_exclusions_and_include_diversity():
    p=make_demo();cs=mine_motifs(p,30)
    assert len(cs)>3 and len({c["motif"] for c in cs})>1
    excluded=p.graph.nodes[0].id;p.brief.excluded_nodes=[excluded]
    assert all(excluded not in c["node_ids"] for c in mine_motifs(p,30))


def test_citation_roles_and_reference_integrity():
    p=Project(sources=[Source(id="S1",title="Fact",text="a",role="evidence"),Source(id="S2",title="Style",text="b",role="voice")])
    audit=citation_audit(p,"Claim. [S1] Bad. [S2] Unknown. [S99]")
    assert set(audit["unknown_or_ineligible_references"])=={"S2","S99"}
    assert citation_audit(p,"No reference.")["missing_all_citations"]
    p.mode="fiction";assert citation_audit(p,"Made-up scene.")["mode"]=="fiction"


def test_source_pack_budget_reports_coverage():
    p=make_demo();pack=source_pack(p,"light safety",500)
    assert pack["retrieved_passages"]<=pack["total_passages"]
    assert all(x["role"]!="voice" for x in pack["passages"])
    assert "not the whole corpus" in pack["note"]


@pytest.mark.parametrize("kind",["md","html","docx","json","graph"])
def test_exports_are_real_files(kind):
    p=make_demo();data,media,ext=export(p,kind)
    assert len(data)>100 and ext.startswith('.')
    if kind=="docx":assert zipfile.is_zipfile(io.BytesIO(data))
    if kind in {"json","graph"}:assert isinstance(json.loads(data),dict)
    if kind=="md":assert b"## Sources" in data
    if kind=="html":assert data.startswith(b'<!doctype html>')


def test_job_budget_and_cancellation():
    j=Job("p","graph");j.before_call("x",1)
    with pytest.raises(ValueError,match="budget"):j.before_call("x",1)
    j.cancel.set()
    with pytest.raises(Cancelled):j.check()


def test_nonfinite_settings_rejected():
    with pytest.raises(ValidationError):Settings(max_calls=float('nan'))
