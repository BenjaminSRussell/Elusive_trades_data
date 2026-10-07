"""FTS5 parts index tests (#4)."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from phase3_index.parts_index import PartsIndex, normalize_part


def test_normalize_part():
    assert normalize_part("0131-M00 008P") == "0131M00008P"


def test_ingest_and_search_under_100ms():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "parts.sqlite"
        idx = PartsIndex(db)
        parts = [
            {"part_number": "0131M00008P", "description": "Capacitor 40+5", "page_ref": 12},
            {"part_number": "P291-4053RS", "description": "Carrier cross", "page_ref": 15},
            {"part_number": "C4405R", "description": "Johnstone", "page_ref": 3},
        ]
        n = idx.ingest_parts("sample.pdf", parts, title="Sample PDF")
        assert n == 3
        t0 = time.perf_counter()
        hits = idx.search("0131-M00008P")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 100, elapsed_ms
        assert len(hits) >= 1
        assert hits[0]["part_number"] == "0131M00008P"
        assert hits[0]["page_ref"] == 12
        # FTS description
        hits2 = idx.search("Capacitor")
        assert any("0131" in h["part_number"] for h in hits2)
        idx.close()
