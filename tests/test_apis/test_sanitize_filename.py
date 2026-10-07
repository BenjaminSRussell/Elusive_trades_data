"""Tests for part-number filename sanitization (issues #15, #8)."""
import sys
from pathlib import Path
import tempfile
import json
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from phase1_acquisition.apis.base_api import sanitize_part_filename, BaseAPI


def test_rejects_empty_and_whitespace():
    for bad in ('', '   ', '\n\n', '\t'):
        with pytest.raises(ValueError):
            sanitize_part_filename(bad)


def test_blocks_path_escape():
    out = sanitize_part_filename('../../tmp/x')
    assert '..' not in out
    assert '/' not in out
    assert '\\' not in out


def test_slash_in_catalog_number():
    out = sanitize_part_filename('P291/4053')
    assert '/' not in out
    assert 'P291' in out and '4053' in out


def test_newlines_and_hash():
    out = sanitize_part_filename('Part#123\n\n')
    assert '\n' not in out
    assert '#' not in out


class _Dummy(BaseAPI):
    def search_by_part_number(self, part_number):
        return {}
    def search_by_model(self, model_number):
        return {}
    def get_part_details(self, part_id):
        return {}


def test_save_response_rejects_empty_part(tmp_path):
    api = _Dummy(output_dir=str(tmp_path))
    with pytest.raises(ValueError):
        api.save_response({'x': 1}, 'part_   ')


def test_save_response_no_escape(tmp_path):
    api = _Dummy(output_dir=str(tmp_path))
    path = api.save_response({'ok': True}, 'part_../../evil')
    assert path.exists()
    assert path.parent == api.api_output_dir.resolve() or str(path).startswith(str(api.api_output_dir.resolve()))
    assert '..' not in path.name
