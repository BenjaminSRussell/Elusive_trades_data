"""FTS helpers used by GUI (#5) — no Tk required."""
from __future__ import annotations

import tempfile
from pathlib import Path

from phase3_index.parts_index import PartsIndex


def test_fts_search_subsecond():
    import time
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "parts.sqlite"
        idx = PartsIndex(db)
        idx.ingest_parts(
            "manual.pdf",
            [{"part_number": "0131M00008P", "description": "Cap", "page_ref": 12}],
        )
        t0 = time.perf_counter()
        hits = idx.search("0131M00008P")
        assert (time.perf_counter() - t0) < 1.0
        assert hits and hits[0]["page_ref"] == 12
        idx.close()
