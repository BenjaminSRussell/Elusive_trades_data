"""SQLite FTS5 parts index — documents, pages, parts (#4)."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    title TEXT,
    indexed_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_num INTEGER NOT NULL,
    text TEXT,
    UNIQUE(document_id, page_num)
);
CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_id INTEGER REFERENCES pages(id) ON DELETE SET NULL,
    part_number TEXT NOT NULL,
    part_number_norm TEXT NOT NULL,
    description TEXT,
    page_ref INTEGER
);
CREATE VIRTUAL TABLE IF NOT EXISTS parts_fts USING fts5(
    part_number,
    part_number_norm,
    description,
    content='parts',
    content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS parts_ai AFTER INSERT ON parts BEGIN
  INSERT INTO parts_fts(rowid, part_number, part_number_norm, description)
  VALUES (new.id, new.part_number, new.part_number_norm, new.description);
END;
CREATE TRIGGER IF NOT EXISTS parts_ad AFTER DELETE ON parts BEGIN
  INSERT INTO parts_fts(parts_fts, rowid, part_number, part_number_norm, description)
  VALUES ('delete', old.id, old.part_number, old.part_number_norm, old.description);
END;
"""


def normalize_part(part_number: str) -> str:
    return re.sub(r"[\s\-]", "", str(part_number or "")).upper()


class PartsIndex:
    def __init__(self, db_path: str | Path = "data/parts_index.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def upsert_document(self, path: str, title: str | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO documents(path, title) VALUES (?, ?) "
            "ON CONFLICT(path) DO UPDATE SET title=excluded.title "
            "RETURNING id",
            (path, title or Path(path).name),
        )
        row = cur.fetchone()
        if row is None:
            row = self.conn.execute(
                "SELECT id FROM documents WHERE path = ?", (path,)
            ).fetchone()
        self.conn.commit()
        return int(row[0])

    def add_page(self, document_id: int, page_num: int, text: str = "") -> int:
        self.conn.execute(
            "INSERT INTO pages(document_id, page_num, text) VALUES (?, ?, ?) "
            "ON CONFLICT(document_id, page_num) DO UPDATE SET text=excluded.text",
            (document_id, page_num, text),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM pages WHERE document_id=? AND page_num=?",
            (document_id, page_num),
        ).fetchone()
        return int(row[0])

    def add_part(
        self,
        document_id: int,
        part_number: str,
        *,
        description: str = "",
        page_ref: int | None = None,
        page_id: int | None = None,
    ) -> int:
        norm = normalize_part(part_number)
        cur = self.conn.execute(
            "INSERT INTO parts(document_id, page_id, part_number, part_number_norm, description, page_ref) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, page_id, part_number, norm, description, page_ref),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """FTS5 search; also matches normalized part numbers without dashes/spaces."""
        q = (query or "").strip()
        if not q:
            return []
        norm = normalize_part(q)
        # Prefer exact norm match, then FTS
        rows = self.conn.execute(
            "SELECT p.part_number, p.description, p.page_ref, d.path AS document, p.part_number_norm "
            "FROM parts p JOIN documents d ON d.id = p.document_id "
            "WHERE p.part_number_norm = ? LIMIT ?",
            (norm, limit),
        ).fetchall()
        if rows:
            return [dict(r) for r in rows]
        # FTS: escape quotes
        safe = q.replace('"', '""')
        try:
            rows = self.conn.execute(
                "SELECT p.part_number, p.description, p.page_ref, d.path AS document, p.part_number_norm "
                "FROM parts_fts f "
                "JOIN parts p ON p.id = f.rowid "
                "JOIN documents d ON d.id = p.document_id "
                "WHERE parts_fts MATCH ? LIMIT ?",
                (f'"{safe}" OR "{norm}"', limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        return [dict(r) for r in rows]

    def ingest_parts(
        self,
        document_path: str,
        parts: Sequence[Dict[str, Any]],
        title: str | None = None,
    ) -> int:
        """Ingest a list of {part_number, description?, page_ref?} dicts."""
        doc_id = self.upsert_document(document_path, title=title)
        n = 0
        for item in parts:
            pn = item.get("part_number") or item.get("part")
            if not pn:
                continue
            page_ref = item.get("page_ref") or item.get("page")
            page_id = None
            if page_ref is not None:
                page_id = self.add_page(doc_id, int(page_ref), text=item.get("page_text") or "")
            self.add_part(
                doc_id,
                str(pn),
                description=str(item.get("description") or ""),
                page_ref=int(page_ref) if page_ref is not None else None,
                page_id=page_id,
            )
            n += 1
        return n


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(prog="parts_index")
    sub = p.add_subparsers(dest="cmd", required=True)
    ing = sub.add_parser("ingest", help="Ingest parts JSON into FTS index")
    ing.add_argument("--db", type=Path, default=Path("data/parts_index.sqlite"))
    ing.add_argument("--document", required=True, help="Source PDF / document path label")
    ing.add_argument("--parts-json", type=Path, required=True, help="JSON list of parts")
    sch = sub.add_parser("search", help="Search FTS index")
    sch.add_argument("--db", type=Path, default=Path("data/parts_index.sqlite"))
    sch.add_argument("query")
    sch.add_argument("--limit", type=int, default=20)
    args = p.parse_args(argv)
    idx = PartsIndex(args.db)
    try:
        if args.cmd == "ingest":
            data = json.loads(args.parts_json.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data = data.get("parts") or data.get("items") or []
            n = idx.ingest_parts(args.document, data)
            print(f"ingested {n} parts → {args.db}")
        else:
            for row in idx.search(args.query, limit=args.limit):
                print(f"{row['part_number']}\tpage={row.get('page_ref')}\t{row.get('description','')}\t{row['document']}")
    finally:
        idx.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
