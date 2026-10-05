"""Uploaded rule documents (law / feng shui / other) as md, txt or pdf."""
from pathlib import Path
import os

ROOT = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[2] / "data")) / "knowledge"
CATEGORIES = ("law", "fengshui", "other")
ALLOWED = {".md", ".txt", ".pdf"}


def _safe(category, name):
    if category not in CATEGORIES:
        raise ValueError("bad category")
    return ROOT / category / Path(name).name


def save(category, filename, data: bytes):
    if Path(filename).suffix.lower() not in ALLOWED:
        raise ValueError("only .md, .txt, .pdf")
    p = _safe(category, filename)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p.name


def delete(category, name):
    _safe(category, name).unlink(missing_ok=True)


def list_files():
    return [{"category": c, "name": f.name, "bytes": f.stat().st_size}
            for c in CATEGORIES if (ROOT / c).exists() for f in sorted((ROOT / c).iterdir()) if f.is_file()]


def read(category, name, max_chars=12000):
    p = _safe(category, name)
    if not p.exists():
        return {"error": "not found"}
    if p.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        text = "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    else:
        text = p.read_text(encoding="utf-8", errors="replace")
    return {"name": p.name, "truncated": len(text) > max_chars, "text": text[:max_chars]}
