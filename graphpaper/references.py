"""Resolve the source markers kept in Article and Polemic drafts."""

import re
from urllib.parse import urlsplit

GROUP = re.compile(r"(?<!\\)\[(S[0-9]+(?:[ \t]*[,;][ \t]*S[0-9]+)*)\](?!\()")
INLINE = re.compile(r"`[^`\n]+`|" + GROUP.pattern)
SOURCE_ID = re.compile(r"S[0-9]+")


def citation_ids(text):
    """Unique source IDs in order of first appearance, including unresolved IDs."""
    return list(dict.fromkeys(
        source_id
        for group in INLINE.finditer(text) if group[1] is not None
        for source_id in SOURCE_ID.findall(group[1])
    ))


def evidence_references(project, text):
    eligible = {source.id: source for source in project.sources
                if source.enabled and source.role == "evidence"}
    return [eligible[source_id] for source_id in citation_ids(text) if source_id in eligible]


def numbered_text(text, sources):
    numbers = {source.id: str(index) for index, source in enumerate(sources, 1)}
    return INLINE.sub(
        lambda group: "[" + ", ".join(numbers.get(source_id, source_id)
                                       for source_id in SOURCE_ID.findall(group[1])) + "]"
        if group[1] is not None else group[0],
        text,
    )


def reference_label(source):
    return (source.title
            + (f" — {source.author}" if source.author else "")
            + (f" ({source.published})" if source.published else ""))


def web_link(url):
    """Only public-web schemes may become clickable in exported files."""
    if re.fullmatch(r'https?://[^\s<>"\\]+', url, re.I):
        try:
            if urlsplit(url).hostname:
                return url
        except ValueError:
            pass
    return ""
