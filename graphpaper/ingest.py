from __future__ import annotations

import hashlib
import http.client
import io
import ipaddress
import re
import socket
import ssl
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

MAX_BYTES = 20 * 1024 * 1024
MAX_TEXT = 2_000_000


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def clean(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    if len(text) > MAX_TEXT:
        raise ValueError("Extracted text exceeds 2 million characters. Split this source into smaller files.")
    if not text.strip():
        raise ValueError("No readable text found. Scanned PDFs need OCR before import; GraphPaper does not silently guess their contents.")
    return text.strip()


def html_text(raw: str) -> tuple[str, str]:
    soup = BeautifulSoup(raw, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else "Web source"
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "svg", "form", "iframe"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body or soup
    return title, clean(main.get_text("\n", strip=True))


def extract(data: bytes, filename: str) -> tuple[str, list[str]]:
    if len(data) > MAX_BYTES:
        raise ValueError("Maximum upload size is 20 MB per file.")
    ext = Path(filename).suffix.lower()
    warnings = []
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("This PDF is encrypted. Import an unlocked copy.")
        if len(reader.pages) > 1000:
            raise ValueError("PDF exceeds 1,000 pages. Import selected chapters.")
        pages, empty = [], []
        count = 0
        for i, page in enumerate(reader.pages, 1):
            t = page.extract_text() or ""
            count += len(t)
            if count > MAX_TEXT:
                raise ValueError("PDF contains too much text for a single source. Split it into chapters.")
            if not t.strip():
                empty.append(i)
            pages.append(f"[Page {i}]\n{t}")
        if len(empty) == len(pages):
            raise ValueError("This is an image-only PDF. Run OCR before importing it.")
        if empty:
            warnings.append(f"No text on pages {', '.join(map(str, empty[:25]))}. Image content was not read.")
        warnings.append("PDF text extracted; figures, scanned text and complex table layouts require manual review.")
        text = "\n\n".join(pages)
    elif ext == ".docx":
        from docx import Document
        from docx.table import Table
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist()) > 80 * 1024 * 1024:
                raise ValueError("Expanded DOCX is too large.")
        doc = Document(io.BytesIO(data))
        chunks = []
        for item in doc.iter_inner_content():
            if isinstance(item, Table):
                chunks.append("\n".join(" | ".join(c.text for c in r.cells) for r in item.rows))
            else:
                chunks.append(item.text)
        text = "\n\n".join(chunks)
        warnings.append("Paragraphs and tables imported; images, comments and tracked-change history are not included.")
    elif ext in {".html", ".htm"}:
        _, text = html_text(data.decode("utf-8-sig", errors="replace"))
    elif ext in {".txt", ".md", ".markdown", ".csv"}:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("cp1252")
            warnings.append("Decoded as Windows-1252. Check special characters in the source viewer.")
    else:
        raise ValueError("Supported sources: PDF, DOCX, TXT, Markdown, CSV and HTML. Use Import graph for JSON.")
    return clean(text), warnings


def chunks(text: str, size: int = 14000, overlap: int = 500):
    """Character offsets retained; cover every character, never silently truncate."""
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind("\n\n", start + size // 2, end)
            if boundary > start:
                end = boundary + 2
        yield start, end, text[start:end]
        if end == len(text):
            break
        start = max(start + 1, end - overlap)


def resolve_public(url: str):
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("Use a public HTTP or HTTPS URL, without credentials.")
    host = p.hostname.encode("idna").decode("ascii")
    port = p.port or (443 if p.scheme == "https" else 80)
    if port not in {80, 443}:
        raise ValueError("Source URLs must use standard HTTP/HTTPS ports.")
    addresses = sorted({i[4][0] for i in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise ValueError("Private, loopback, link-local and reserved network addresses cannot be imported.")
    return p, host, port, addresses[0]


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, ip, port):
        super().__init__(host, port, timeout=25, context=ssl.create_default_context())
        self.ip = ip

    def connect(self):
        self.sock = socket.create_connection((self.ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def fetch_url(url: str) -> tuple[str, str, str, list[str]]:
    """DNS pinned after validation; redirects revalidated; no cookies, JS, or proxy."""
    for _ in range(5):
        p, host, port, ip = resolve_public(url)
        conn = PinnedHTTPS(host, ip, port) if p.scheme == "https" else http.client.HTTPConnection(ip, port, timeout=25)
        try:
            path = p.path or "/"
            if p.query:
                path += "?" + p.query
            conn.request("GET", path, headers={"Host": host, "User-Agent": "GraphPaper/0.1 source-reader", "Accept-Encoding": "identity"})
            res = conn.getresponse()
            if res.status in {301, 302, 303, 307, 308}:
                target = res.getheader("Location")
                if not target:
                    raise ValueError("Redirect has no destination.")
                url = urljoin(url, target)
                continue
            if res.status != 200:
                raise ValueError(f"Source returned HTTP {res.status}. Paste the text or upload a saved copy instead.")
            if res.getheader("Content-Encoding", "identity") not in {"", "identity"}:
                raise ValueError("Source sent compressed content despite requesting uncompressed data. Upload a saved copy.")
            content_type = res.getheader("Content-Type", "").split(";")[0].lower()
            data = res.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("Web source exceeds 20 MB.")
            if content_type == "application/pdf" or data.startswith(b"%PDF"):
                text, warnings = extract(data, "source.pdf")
                return Path(p.path).name or "Web PDF", text, url, warnings
            if content_type not in {"text/html", "application/xhtml+xml", "text/plain", "text/markdown", ""}:
                raise ValueError("URL did not return an article or PDF.")
            raw = data.decode("utf-8-sig", errors="replace")
            if content_type in {"text/plain", "text/markdown"}:
                return Path(p.path).name or host, clean(raw), url, []
            title, text = html_text(raw)
            return title, text, url, ["Web text only. Check the imported text for paywalls, missing sections or navigation."]
        finally:
            conn.close()
    raise ValueError("Too many source redirects.")
