import re
import sqlite3
from pathlib import Path

STOPWORDS = {"a", "an", "and", "are", "as", "at", "be", "can", "do", "does", "for", "from", "how", "i", "in", "is", "it", "many", "me", "of", "on", "our", "receive", "the", "their", "they", "to", "what", "when", "with", "you"}


def extract_pages(path: Path):
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(PdfReader(path).pages)]
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"\[Page (\d+)\]", text)
    if len(parts) == 1:
        return [(1, text)]
    return [(int(parts[i]), parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def retrieve_policy(path: Path, question: str, limit=3):
    pages = extract_pages(path)
    db = sqlite3.connect(":memory:")
    db.execute("CREATE VIRTUAL TABLE pages USING fts5(text, page UNINDEXED)")
    db.executemany("INSERT INTO pages(text,page) VALUES (?,?)", [(text, page) for page, text in pages])
    tokens = [word for word in re.findall(r"[a-zA-Z0-9]+", question.lower()) if word not in STOPWORDS]
    aliases = {"vacation": "PTO", "paid": "PTO", "full": "full", "leave": "leave"}
    tokens = list(dict.fromkeys(tokens + [aliases[token] for token in tokens if token in aliases]))
    query = " OR ".join('"' + word + '"' for word in tokens)
    hits = db.execute("SELECT text,page FROM pages WHERE pages MATCH ? ORDER BY bm25(pages) LIMIT ?", (query, limit)).fetchall() if query else []
    db.close()
    return [{"id": str(i + 1), "document": path.name, "page": int(page), "snippet": text, "synthetic": True} for i, (text, page) in enumerate(hits)]
