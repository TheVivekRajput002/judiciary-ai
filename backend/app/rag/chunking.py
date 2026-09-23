"""Structure-aware chunking for legal documents.

Strategy:
- Respect section/paragraph boundaries where detectable.
- Fall back to sentence-boundary splitting when structure isn't clear.
- Target ~400 tokens per chunk with 80-token overlap.
"""
from __future__ import annotations
import re
from dataclasses import dataclass


CHUNK_SIZE = 800      # target tokens (~3200 chars - full legal sections)
CHUNK_OVERLAP = 120
CHARS_PER_TOKEN = 4


@dataclass
class RawChunk:
    content: str
    page_number: int | None
    section: str | None
    paragraph: str | None
    chunk_index: int


# ---------------------------------------------------------------------------
# Section-heading detection patterns common in Indian judgments
# ---------------------------------------------------------------------------
_SECTION_PATTERNS = [
    re.compile(r"^(?:JUDGMENT|ORDER|FACTS|ISSUES?|HELD|CONCLUSION|BACKGROUND|ANALYSIS|REASONING)\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\d+\.\s+[A-Z]", re.MULTILINE),               # "1. Facts"
    re.compile(r"^[IVX]+\.\s+[A-Z]", re.MULTILINE),            # "IV. Analysis"
    re.compile(r"^(?:Section|Clause|Article|Para)\s+\d+", re.IGNORECASE | re.MULTILINE),
]


def _split_by_structure(text: str) -> list[tuple[str, str | None]]:
    """Split text on detected section headings.

    Returns list of (section_text, section_name).
    """
    # Find all heading positions
    positions: list[tuple[int, str]] = []
    for pat in _SECTION_PATTERNS:
        for m in pat.finditer(text):
            positions.append((m.start(), m.group(0).strip()))

    if not positions:
        return [(text, None)]

    positions.sort(key=lambda x: x[0])
    sections: list[tuple[str, str | None]] = []
    for i, (pos, heading) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        sections.append((text[pos:end], heading))
    # Prepend any text before the first heading
    if positions[0][0] > 0:
        sections.insert(0, (text[:positions[0][0]], None))
    return sections


def _split_into_chunks(text: str, page: int | None, section: str | None) -> list[tuple[str, int | None, str | None]]:
    """Split a block of text into overlap-aware chunks of ~CHUNK_SIZE tokens."""
    max_chars = CHUNK_SIZE * CHARS_PER_TOKEN
    overlap_chars = CHUNK_OVERLAP * CHARS_PER_TOKEN

    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    chunks: list[tuple[str, int | None, str | None]] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append((current, page, section))
            # Start new chunk with overlap
            overlap_text = current[-overlap_chars:] if overlap_chars < len(current) else current
            current = (overlap_text + " " + sentence).strip()

    if current:
        chunks.append((current, page, section))

    return chunks


def chunk_document(pages: list[tuple[str, int]]) -> list[RawChunk]:
    """Main entry point.

    Args:
        pages: list of (page_text, page_number) tuples extracted from the document.

    Returns:
        Ordered list of RawChunk objects ready for embedding.
    """
    raw_chunks: list[RawChunk] = []
    idx = 0

    for page_text, page_num in pages:
        sections = _split_by_structure(page_text)
        for section_text, section_name in sections:
            for content, pg, sec in _split_into_chunks(section_text, page_num, section_name):
                if content.strip():
                    raw_chunks.append(
                        RawChunk(
                            content=content.strip(),
                            page_number=pg,
                            section=sec,
                            paragraph=None,
                            chunk_index=idx,
                        )
                    )
                    idx += 1

    return raw_chunks
