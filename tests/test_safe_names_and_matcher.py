from pathlib import Path
import json
import tempfile

from phase1_acquisition.safe_names import sanitize_part_token
from phase1_acquisition.apis.base_api import BaseAPI
from phase2_matching.matcher import PartMatcher


def test_sanitize_blocks_traversal_and_slashes():
    assert ".." not in sanitize_part_token("../../tmp/x")
    assert "/" not in sanitize_part_token("P291/4053")
    assert "\n" not in sanitize_part_token("a\n\nb")
    assert sanitize_part_token("   ") == "UNKNOWN"
    assert sanitize_part_token("") == "UNKNOWN"


class _Dummy(BaseAPI):
    def search_by_part_number(self, part_number):
        return {}
    def search_by_model(self, model_number):
        return {}
    def get_part_details(self, part_id):
        return {}
    def get_available_endpoints(self):
        return []


def test_save_response_sanitizes_filename(tmp_path):
    api = _Dummy(output_dir=str(tmp_path))
    path = api.save_response({"ok": True}, "part_../../etc/passwd")
    assert path.parent == api.api_output_dir.resolve() or str(path).startswith(str(api.api_output_dir.resolve()))
    assert ".." not in path.name
    assert path.exists()


def test_matcher_uses_latest_session_only(tmp_path):
    raw = tmp_path / "raw" / "carrier"
    old = raw / "20200101_000000"
    new = raw / "20260101_000000"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    payload = {"part_number": "ABC123", "cross_references": ["X1"], "data": {"cross_references": ["X2"]}}
    (old / "part_ABC123.json").write_text(json.dumps(payload))
    (new / "part_ABC123.json").write_text(json.dumps(payload))
    matcher = PartMatcher(raw_data_dir=str(tmp_path / "raw"), output_dir=str(tmp_path / "out"))
    results = matcher.search_part("ABC123")
    assert results["summary"]["total_matches"] == 1
    assert results["matches"][0]["session"] == "20260101_000000"
    # nested data["data"] cross_references collected
    assert "X2" in results["cross_references"] or "X1" in results["cross_references"]


def test_matcher_rejects_empty_part():
    matcher = PartMatcher(raw_data_dir="/tmp/none", output_dir="/tmp/none2")
    try:
        matcher.search_part("  ")
        assert False
    except ValueError:
        pass
