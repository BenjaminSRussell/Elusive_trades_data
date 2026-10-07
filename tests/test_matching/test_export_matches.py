"""Tests for Parquet export of cross-vendor matches (#9)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pytest

from phase2_matching.export_matches import (
    COLUMNS,
    collect_rows,
    export_matches,
    match_record_to_rows,
)


class TestExportMatches(unittest.TestCase):
    def test_match_record_to_rows_flattens(self):
        record = {
            "part_number": "0131M00008P",
            "timestamp": "2024-01-01T12:00:00",
            "matches": [
                {
                    "api": "goodman",
                    "data": {
                        "data": {
                            "url": "https://vendor.example/p/0131M00008P",
                            "score": 0.91,
                        }
                    },
                },
                {"api": "carrier", "data": {"url": "https://c.example/x", "confidence": 0.5}},
            ],
        }
        rows = match_record_to_rows(record)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["part"], "0131M00008P")
        self.assertEqual(rows[0]["vendor"], "goodman")
        self.assertEqual(rows[0]["score"], 0.91)
        self.assertEqual(rows[0]["url"], "https://vendor.example/p/0131M00008P")
        self.assertEqual(rows[0]["fetched_at"], "2024-01-01T12:00:00")
        self.assertEqual(rows[1]["vendor"], "carrier")
        self.assertEqual(rows[1]["score"], 0.5)

    def test_collect_and_export_parquet(self):
        pyarrow = pytest.importorskip("pyarrow")
        import pyarrow.parquet as pq

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            part_dir = root / "0131M00008P"
            part_dir.mkdir()
            (part_dir / "match_results_20240101_120000.json").write_text(
                json.dumps(
                    {
                        "part_number": "0131M00008P",
                        "timestamp": "2024-01-01T12:00:00",
                        "matches": [
                            {
                                "api": "goodman",
                                "data": {
                                    "data": {
                                        "url": "https://ex/p",
                                        "score": 0.8,
                                    }
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            rows = collect_rows(root)
            self.assertEqual(len(rows), 1)
            out = root / "matches.parquet"
            n = export_matches(root, out)
            self.assertEqual(n, 1)
            self.assertTrue(out.exists())
            table = pq.read_table(out)
            self.assertEqual(table.num_rows, 1)
            self.assertEqual(list(table.column_names), list(COLUMNS))
            self.assertEqual(table.column("part")[0].as_py(), "0131M00008P")
            self.assertEqual(table.column("vendor")[0].as_py(), "goodman")


if __name__ == "__main__":
    unittest.main()
