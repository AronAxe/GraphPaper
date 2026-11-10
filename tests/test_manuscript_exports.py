from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfReader
from graphpaper.polish import mask


@pytest.mark.parametrize("mode", ["nonfiction", "polemic"])
def test_article_export_keeps_citation_order_and_metadata(client, mode):
    project = client.post("/api/projects", json={"title": "An essay", "mode": mode}).json()
    path = "/api/projects/" + project["id"]
    sources = [
        {"title": "Later source", "text": "The second source."},
        {"title": "Café study", "text": "The first source.", "author": "Éva Example",
         "published": "2024", "url": "https://example.org/research?x=1&y=2"},
        {"title": "Private voice sample", "text": "A voice sample.", "role": "voice"},
    ]
    for source in sources:
        response = client.post(path + "/sources/text", json=source)
        assert response.status_code == 200
        project = response.json()
    draft = "# Essay title\n\nA claim [S2, S1]. Again [S2]. Check [S3] and [S99]."
    assert client.patch(path, json={"version": project["version"], "draft": draft}).status_code == 200

    pdf = client.get(path + "/export/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.headers["content-disposition"].endswith('.pdf"')
    pdf_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    word = client.get(path + "/export/docx")
    assert word.status_code == 200
    word_text = "\n".join(paragraph.text for paragraph in Document(BytesIO(word.content)).paragraphs)
    for text in (pdf_text, word_text):
        assert "A claim [1, 2]. Again [1]." in text
        assert "References" in text
        assert text.index("[1] Café study") < text.index("[2] Later source")
        assert "Éva Example" in text and "2024" in text
        assert "https://example.org/research?x=1&y=2" in text
        assert "Private voice sample" not in text
        assert "Check [S3] and [S99]." in text
    assert client.get(path).json()["draft"] == draft


def test_pdf_reports_unavailable_glyph_instead_of_omitting_it(client):
    project = client.post("/api/projects", json={"title": "Unsupported glyph"}).json()
    path = "/api/projects/" + project["id"]
    draft = "A personal name with a supplementary character \U00020000."
    assert client.patch(path, json={"version": project["version"], "draft": draft}).status_code == 200
    response = client.get(path + "/export/pdf")
    assert response.status_code == 400
    assert "U+20000" in response.json()["detail"]
    assert client.get(path + "/export/docx").status_code == 200


def test_polishing_protects_grouped_citations_as_one_span():
    _, protected = mask("A claim [S2, S1].")
    assert list(protected.values()) == ["[S2, S1]"]
