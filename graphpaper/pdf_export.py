"""Local, paginated PDF export for ordinary manuscripts."""

from html import escape
from io import BytesIO
import os
from pathlib import Path
import re
from threading import Lock

import reportlab
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from .references import reference_label, web_link

_FONT_LOCK = Lock()
_FONT = "GraphPaperManuscript"


def register_fonts():
    with _FONT_LOCK:
        if _FONT in pdfmetrics.getRegisteredFontNames():
            return
        font_directory = Path(reportlab.__file__).parent / "fonts"
        files = ["Vera.ttf", "VeraBd.ttf", "VeraIt.ttf", "VeraBI.ttf"]
        if os.name == "nt":
            windows_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
            arial = ["arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"]
            if all((windows_fonts / name).is_file() for name in arial):
                font_directory, files = windows_fonts, arial
        for suffix, filename in zip(("", "Bold", "Italic", "BoldItalic"), files):
            pdfmetrics.registerFont(TTFont(_FONT + suffix, str(font_directory / filename)))
        pdfmetrics.registerFontFamily(
            _FONT, normal=_FONT, bold=_FONT + "Bold", italic=_FONT + "Italic",
            boldItalic=_FONT + "BoldItalic",
        )


def pdf_text(text):
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    glyphs = pdfmetrics.getFont(_FONT).face.charToGlyph
    unsupported = next((char for char in text if char not in "\t\r\n" and not glyphs.get(ord(char))), None)
    if unsupported is not None:
        raise ValueError(f"The PDF font cannot display U+{ord(unsupported):04X}. Export to Word to preserve this text.")
    return escape(text).replace("\n", "<br/>")


def pdf_bytes(title, parts, sources):
    register_fonts()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=24*mm, rightMargin=24*mm,
        topMargin=23*mm, bottomMargin=23*mm, title=title, author="",
    )
    body = ParagraphStyle("Body", fontName=_FONT, fontSize=11, leading=16, spaceAfter=9)
    headings = {
        level: ParagraphStyle(f"Heading{level}", parent=body, fontName=_FONT + "Bold",
                              fontSize=size, leading=size + 5, spaceBefore=11,
                              keepWithNext=True, textColor=HexColor("#243E38"))
        for level, size in ((1, 23), (2, 16), (3, 12))
    }
    separator = ParagraphStyle("Separator", parent=body, alignment=1)
    reference = ParagraphStyle("Reference", parent=body, fontSize=10, leading=15)
    story = []
    for part, text in parts:
        if part == "break":
            story.append(Paragraph("* * *", separator))
        else:
            markup = pdf_text(text)
            markup = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", markup)
            markup = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", markup)
            story.append(Paragraph(markup, headings.get(part, body)))
    if sources:
        story.append(Paragraph("References", headings[2]))
        for number, source in enumerate(sources, 1):
            label = pdf_text(f"[{number}] {reference_label(source)}")
            if url := web_link(source.url):
                link = pdf_text(url)
                label += f'<br/><link href="{link}" color="#235D4B">{link}</link>'
            story.append(Paragraph(label, reference))
    if not story:
        story.append(Paragraph(pdf_text(title), headings[1]))
    document.build(story)
    return buffer.getvalue()
