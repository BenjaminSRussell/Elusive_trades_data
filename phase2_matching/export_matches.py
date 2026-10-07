"""Export nested match JSON under data/processed/ to a flat Parquet table (#9)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Optional


COLUMNS = ("part", "vendor", "score", "url", "fetched_at")


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dig_url(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("url", "product_url", "link", "href"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        data = payload.get("data")
        if isinstance(data, dict):
            return _dig_url(data)
    return ""


def _dig_score(payload: Any) -> Optional[float]:
    if isinstance(payload, dict):
        for key in ("score", "match_score", "confidence", "similarity"):
            if key in payload:
                scored = _as_float(payload.get(key))
                if scored is not None:
                    return scored
        data = payload.get("data")
        if isinstance(data, dict):
            return _dig_score(data)
    return None


def match_record_to_rows(record: dict) -> List[dict]:
    """Flatten one match_results_*.json document into columnar rows."""
    part = str(record.get("part_number") or record.get("part") or "").strip()
    fetched_at = str(record.get("timestamp") or record.get("fetched_at") or "")
    rows: List[dict] = []
    for match in record.get("matches") or []:
        if not isinstance(match, dict):
            continue
        vendor = str(match.get("api") or match.get("vendor") or "").strip()
        payload = match.get("data") if isinstance(match.get("data"), dict) else match
        rows.append(
            {
                "part": part,
                "vendor": vendor,
                "score": _dig_score(payload),
                "url": _dig_url(payload),
                "fetched_at": fetched_at or str(payload.get("fetched_at") or ""),
            }
        )
    return rows


def iter_match_json_files(processed_dir: Path) -> Iterable[Path]:
    if not processed_dir.exists():
        return []
    return sorted(processed_dir.rglob("match_results_*.json"))


def collect_rows(processed_dir: Path) -> List[dict]:
    rows: List[dict] = []
    for path in iter_match_json_files(processed_dir):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            rows.extend(match_record_to_rows(data))
    return rows


def write_parquet(rows: List[dict], out: Path) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit(
            "pyarrow required for parquet export: pip install pyarrow"
        ) from exc
    # Normalize null scores to float column
    normalized = []
    for row in rows:
        normalized.append(
            {
                "part": row.get("part") or "",
                "vendor": row.get("vendor") or "",
                "score": row.get("score"),
                "url": row.get("url") or "",
                "fetched_at": row.get("fetched_at") or "",
            }
        )
    table = pa.Table.from_pylist(normalized)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)


def export_matches(processed_dir: Path, out: Path) -> int:
    rows = collect_rows(processed_dir)
    write_parquet(rows, out)
    return len(rows)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="export_matches",
        description="Export cross-vendor match results to Parquet (#9)",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory with nested match_results_*.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/matches.parquet"),
        help="Output Parquet path",
    )
    args = parser.parse_args(argv)
    n = export_matches(args.processed_dir, args.out)
    print(f"wrote {n} rows → {args.out}")
    print("columns:", ", ".join(COLUMNS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
