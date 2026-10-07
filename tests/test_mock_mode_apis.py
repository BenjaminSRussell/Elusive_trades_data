"""Mock-mode acquisition must not invent unknown parts."""
import os
import tempfile
from pathlib import Path

from phase1_acquisition.apis.carrier_api import CarrierAPI
from phase1_acquisition.apis.ferguson_api import FergusonAPI
from phase1_acquisition.apis.goodman_api import GoodmanAPI
from phase1_acquisition.apis.johnstone_api import JohnstoneAPI


def test_nonexistent_not_found_all_vendors(monkeypatch):
    monkeypatch.setenv("ACQUISITION_MODE", "mock")
    with tempfile.TemporaryDirectory() as tmp:
        for cls, known in [
            (GoodmanAPI, "0131M00008P"),
            (CarrierAPI, "P291-4053RS"),
            (JohnstoneAPI, "C4405R"),
            (FergusonAPI, "CAP-405"),
        ]:
            api = cls(output_dir=tmp)
            missing = api.search_by_part_number("NONEXISTENT")
            assert missing["status"] == "not_found"
            assert missing["source"] == "mock"
            assert "fetched_at" in missing
            found = api.search_by_part_number(known)
            assert found["status"] == "found"
            assert found["source"] == "mock"
            assert "fetched_at" in found


def test_goodman_live_uses_session(monkeypatch):
    """Live mode performs an HTTP GET via requests.Session."""
    import requests

    monkeypatch.setenv("ACQUISITION_MODE", "live")

    class FakeResp:
        status_code = 404

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    called = {}

    def fake_get(self, url, params=None, timeout=None):
        called["url"] = url
        called["params"] = params
        called["timeout"] = timeout
        return FakeResp()

    monkeypatch.setattr(requests.Session, "get", fake_get)
    with tempfile.TemporaryDirectory() as tmp:
        api = GoodmanAPI(output_dir=tmp)
        result = api.search_by_part_number("ANY")
        assert called.get("url")
        assert result["status"] == "not_found"
        assert result["source"] == "live"
