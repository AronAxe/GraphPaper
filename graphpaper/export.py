from __future__ import annotations
import html
import io
import re

from .models import Project
from .references import evidence_references, numbered_text, reference_label, web_link


def referenced_sources(p: Project):
    return evidence_references(p, p.draft)


def markdown(p: Project):
    text = p.draft
    sources = referenced_sources(p) if p.mode in {"nonfiction", "polemic"} else []
    if sources:
        text += "\n\n---\n\n## Sources\n\n"
        for s in sources:
            text += f"[{s.id}] {reference_label(s)}" + (f"\n{s.url}" if s.url else "") + "\n\n"
    return text


def simple_html(text):
    """Small safe Markdown subset, never allows raw HTML or remote assets."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        t = html.escape(block)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
        if re.match(r"^#{1,3} ", block):
            n = len(block) - len(block.lstrip("#"))
            out.append(f"<h{n}>{t[n+1:]}</h{n}>")
        elif block.strip() in {"---", "* * *"}:
            out.append("<hr>")
        else:
            out.append("<p>" + t.replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def manuscript_parts(draft):
    """Yield the supported headings, scene breaks, and body paragraphs."""
    for block in re.split(r"\n\s*\n", draft.strip()):
        if not block:
            continue
        if block.strip() in {"---", "* * *"}:
            yield "break", ""
            continue
        heading = re.match(r"^(#{1,3}) ([^\n]+)(?:\n|$)", block)
        if heading:
            yield len(heading[1]), heading[2]
            block = block[heading.end():]
        if block:
            yield "body", block


def add_word_link(paragraph, url):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.opc.constants import RELATIONSHIP_TYPE

    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), paragraph.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True))
    run = paragraph.add_run(url, style="Hyperlink" if "Hyperlink" in paragraph.part.styles else None)
    run.underline = True
    link.append(run._element)
    paragraph._p.append(link)


def export(p: Project, kind: str):
    if p.mode == 'science' and kind not in {'json','graph'}:
        from .science_export import export_science
        return export_science(p,kind)
    if kind == "json":
        return p.model_dump_json(indent=2).encode(), "application/json", ".graphpaper.json"
    if kind == "graph":
        return p.graph.model_dump_json(indent=2).encode(), "application/json", ".graph.json"
    if kind == "md":
        return markdown(p).encode(), "text/markdown; charset=utf-8", ".md"
    sources = referenced_sources(p) if p.mode in {"nonfiction", "polemic"} else []
    draft = numbered_text(p.draft, sources) if p.mode in {"nonfiction", "polemic"} else p.draft
    if kind == "html":
        body = simple_html(draft)
        if sources:
            body += "<hr><h2>References</h2>"
            for number, source in enumerate(sources, 1):
                body += f"<p>[{number}] {html.escape(reference_label(source))}"
                if url := web_link(source.url):
                    escaped = html.escape(url, quote=True)
                    body += f'<br><a href="{escaped}">{escaped}</a>'
                body += "</p>"
        text = '<!doctype html><html lang="en"><meta charset="utf-8"><title>' + html.escape(p.title) + '</title><style>body{max-width:740px;margin:64px auto;padding:0 28px;font:18px/1.75 Georgia,serif;color:#26282b}h1{font-size:2.3em;line-height:1.16}h2{margin-top:2em}p{overflow-wrap:anywhere}hr{border:0;border-top:1px solid #ddd;margin:2em 0}@media print{body{margin:0;max-width:none;font-size:11pt}h1,h2,h3{break-after:avoid}p{orphans:3;widows:3}@page{size:A4;margin:24mm}}</style><body>' + body + '</body></html>'
        return text.encode(), "text/html; charset=utf-8", ".html"
    if kind == "pdf":
        from .pdf_export import pdf_bytes
        return pdf_bytes(p.title, manuscript_parts(draft), sources), "application/pdf", ".pdf"
    if kind == "docx":
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        doc = Document()
        sec = doc.sections[0]
        sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
        sec.top_margin = sec.bottom_margin = Inches(0.9)
        sec.left_margin = sec.right_margin = Inches(0.95)
        style = doc.styles["Normal"]
        style.font.name, style.font.size = "Calibri", Pt(11)
        style.paragraph_format.space_after = Pt(8)
        style.paragraph_format.line_spacing = 1.18
        doc.core_properties.title, doc.core_properties.author = p.title, ""
        for part, block in manuscript_parts(draft):
            if isinstance(part, int):
                para = doc.add_heading(block, part)
                for r in para.runs:
                    r.font.color.rgb = RGBColor.from_string("243E38")
            elif part == "break":
                doc.add_paragraph("* * *")
            else:
                para = doc.add_paragraph()
                for token in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", block):
                    run = para.add_run(token.strip("*") if token.startswith("*") else token)
                    run.bold = token.startswith("**")
                    run.italic = token.startswith("*") and not run.bold
        if sources:
            doc.add_heading("References", 2)
            for number, source in enumerate(sources, 1):
                paragraph = doc.add_paragraph(f"[{number}] {reference_label(source)}")
                if url := web_link(source.url):
                    paragraph.add_run().add_break()
                    add_word_link(paragraph, url)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"
    raise ValueError("Unknown export format")
