"""Splash-optional HTML fetch uses HTTP fallback when SPLASH_URL unset (#11)."""
from __future__ import annotations

import os

from phase1_acquisition.html_fetch import fetch_html, splash_enabled


def test_splash_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SPLASH_URL", raising=False)
    assert splash_enabled() is False


def test_http_fallback_no_splash(monkeypatch):
    monkeypatch.delenv("SPLASH_URL", raising=False)

    class FakeResp:
        status_code = 200
        text = "<html>ok</html>"
        url = "https://example.com/part"

    def fake_get(url, timeout=None, follow_redirects=None):
        return FakeResp()

    try:
        import httpx

        monkeypatch.setattr(httpx, "get", fake_get)
    except ImportError:
        import requests

        monkeypatch.setattr(requests, "get", fake_get)

    result = fetch_html("https://example.com/part")
    assert result["splash"] is False
    assert result["status_code"] == 200
    assert "ok" in result["html"]
    assert result["backend"] in {"httpx", "requests"}
