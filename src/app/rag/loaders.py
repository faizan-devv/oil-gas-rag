"""Read the three document types from disk and lightly clean them."""

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

# Running header/footer lines that pypdf returns as ordinary text.
_PDF_FURNITURE = re.compile(r"^(.*\bCONFIDENTIAL\b.*|Page \d+ of \d+)$")
_DASHES = str.maketrans({"–": "-", "—": "-", "‐": "-", "‑": "-"})


@dataclass
class Document:
    source: str  # file name, used in citations
    doc_type: str  # well_report | manual | maintenance_log
    text: str = ""
    entries: list[dict] = field(default_factory=list)  # maintenance logs only


def clean(text: str) -> str:
    """Normalise unicode and whitespace; keep line structure for the chunkers."""
    text = unicodedata.normalize("NFKC", text).translate(_DASHES)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def read_pdf(path: Path) -> str:
    pages = [page.extract_text() or "" for page in PdfReader(path).pages]
    lines = [ln for page in pages for ln in page.splitlines() if not _PDF_FURNITURE.match(ln.strip())]
    return "\n".join(lines)


def load_documents(data_dir: Path) -> list[Document]:
    docs: list[Document] = []
    for path in sorted((data_dir / "well_reports").glob("*")):
        if path.suffix == ".pdf":
            docs.append(Document(path.name, "well_report", clean(read_pdf(path))))
        elif path.suffix == ".txt":
            docs.append(Document(path.name, "well_report", clean(path.read_text())))
    for path in sorted((data_dir / "manual").glob("*.md")):
        docs.append(Document(path.name, "manual", clean(path.read_text())))
    for path in sorted((data_dir / "maintenance_logs").glob("*.jsonl")):
        entries = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        for e in entries:
            e["log_text"] = clean(e["log_text"])
        docs.append(Document(path.name, "maintenance_log", entries=entries))
    return docs
