"""Structure-aware chunking: each document type is split along its own seams.

Sizes are counted in words. 300 words is roughly 400 tokens for this prose, and
45 words of overlap is roughly 60 tokens.
"""

import re
from dataclasses import dataclass

from app.rag.loaders import Document

CHUNK_WORDS = 300
OVERLAP_WORDS = 45

_WELL_SECTION = re.compile(r"^\d+\. [A-Z][A-Za-z ]+$")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    id: str  # "<source>#<ref>", the citation handle
    text: str  # what is embedded and shown to the LLM
    source: str
    doc_type: str
    section: str


def split_long(text: str, size: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    """Pack whole sentences into windows of `size` words, repeating the last
    `overlap` words' worth of sentences at the start of the next window."""
    if len(text.split()) <= size:
        return [text]
    windows: list[str] = []
    current: list[str] = []
    for sentence in _SENTENCE_END.split(text):
        if current and sum(len(s.split()) for s in current) + len(sentence.split()) > size:
            windows.append(" ".join(current))
            tail: list[str] = []
            for s in reversed(current):
                if sum(len(t.split()) for t in tail) + len(s.split()) > overlap:
                    break
                tail.insert(0, s)
            current = tail
        current.append(sentence)
    windows.append(" ".join(current))
    return windows


def _unwrap(lines: list[str]) -> str:
    """Join hard-wrapped lines (PDF extraction) back into paragraphs."""
    paragraphs = re.split(r"\n\s*\n", "\n".join(lines).strip())
    return "\n\n".join(" ".join(p.split()) for p in paragraphs if p.strip())


def chunk_well_report(doc: Document) -> list[Chunk]:
    """One chunk for the header fields, then one per numbered section. Every
    chunk repeats the well ID so it can be understood, and matched, on its own."""
    sections: list[tuple[str, list[str]]] = [("Header", [])]
    for line in doc.text.splitlines():
        if _WELL_SECTION.match(line):
            sections.append((line.split(". ", 1)[1], []))
        else:
            sections[-1][1].append(line)
    # Header fields are one per line and never wrap, so they are kept as lines.
    header = "\n".join(line for line in sections[0][1] if line)
    well_id = (re.search(r"Well ID: (\S+)", header) or [None, doc.source])[1]
    chunks, n = [], 0
    for name, lines in sections:
        body = header if name == "Header" else _unwrap(lines)
        for part in split_long(body):
            prefix = f"Well completion report {well_id} - {name}"
            chunks.append(Chunk(f"{doc.source}#{n:02d}", f"{prefix}\n{part}", doc.source, doc.doc_type, name))
            n += 1
    return chunks


def chunk_manual(doc: Document) -> list[Chunk]:
    """Split on markdown headings; a subsection becomes one chunk unless it is
    longer than CHUNK_WORDS, in which case it is windowed with overlap."""
    title, section, subsection = "Manual", "", ""
    blocks: list[tuple[str, list[str]]] = []
    for line in doc.text.splitlines():
        if line.startswith("### "):
            subsection = line[4:].strip()
            blocks.append((f"{section} > {subsection}", []))
        elif line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("# "):
            title = line[2:].strip()
        elif blocks:
            blocks[-1][1].append(line)
    chunks, n = [], 0
    for path, lines in blocks:
        body = "\n".join(lines).strip()
        # Tables are kept whole: a fault-code row is useless without its header.
        parts = [body] if "|---" in body else split_long(_unwrap(lines))
        for part in parts:
            chunks.append(Chunk(f"{doc.source}#{n:02d}", f"{title} > {path}\n{part}", doc.source, doc.doc_type, path))
            n += 1
    return chunks


def chunk_maintenance_log(doc: Document) -> list[Chunk]:
    """One entry per chunk, no overlap: entries are short and self-contained."""
    chunks = []
    for e in doc.entries:
        meta = [f"Maintenance log {e['log_id']}"]
        if e.get("equipment_id"):
            meta.append(f"equipment {e['equipment_id']}")
        if e.get("fault_code"):
            meta.append(f"fault {e['fault_code']}")
        meta.append(f"logged {e['timestamp'][:10]}")
        chunks.append(
            Chunk(f"{doc.source}#{e['log_id']}", f"{' | '.join(meta)}\n{e['log_text']}", doc.source, doc.doc_type, e["log_id"])
        )
    return chunks


_CHUNKERS = {
    "well_report": chunk_well_report,
    "manual": chunk_manual,
    "maintenance_log": chunk_maintenance_log,
}


def chunk_documents(docs: list[Document]) -> list[Chunk]:
    return [chunk for doc in docs for chunk in _CHUNKERS[doc.doc_type](doc)]
