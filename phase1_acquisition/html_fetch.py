"""HTML fetch helpers: optional Splash, default httpx/requests fallback (#11)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional


SPLASH_SCRIPTS_DIR = Path(__file__).resolve().parent / "splash_scripts"


def splash_enabled() -> bool:
    """True when SPLASH_URL is set (Scrapy-Splash / splash server)."""
    return bool(os.environ.get("SPLASH_URL", "").strip())


def splash_script_path(name: str) -> Path:
    return SPLASH_SCRIPTS_DIR / name


def fetch_html(url: str, *, timeout: float = 30.0, lua_script: Optional[str] = None) -> Dict[str, Any]:
    """Fetch HTML for *url*.

    - If ``SPLASH_URL`` is set, POST to Splash ``/execute`` (or ``/render.html``).
    - Otherwise use plain HTTP (httpx if installed, else requests). CI and
      default clone-and-run use this fallback — no Docker/Splash required.
    """
    if splash_enabled():
        return _fetch_via_splash(url, timeout=timeout, lua_script=lua_script)
    return _fetch_via_http(url, timeout=timeout)


def _fetch_via_http(url: str, *, timeout: float) -> Dict[str, Any]:
    try:
        import httpx

        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        return {
            "url": str(resp.url),
            "status_code": resp.status_code,
            "html": resp.text,
            "backend": "httpx",
            "splash": False,
        }
    except ImportError:
        import requests

        resp = requests.get(url, timeout=timeout)
        return {
            "url": resp.url,
            "status_code": resp.status_code,
            "html": resp.text,
            "backend": "requests",
            "splash": False,
        }


def _fetch_via_splash(
    url: str, *, timeout: float, lua_script: Optional[str]
) -> Dict[str, Any]:
    import requests

    splash_base = os.environ["SPLASH_URL"].rstrip("/")
    if lua_script:
        script_path = splash_script_path(lua_script)
        lua = script_path.read_text(encoding="utf-8")
        endpoint = f"{splash_base}/execute"
        resp = requests.post(
            endpoint,
            json={"lua_source": lua, "url": url, "timeout": timeout},
            timeout=timeout + 5,
        )
        payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"html": resp.text}
        html = payload.get("html", resp.text)
    else:
        endpoint = f"{splash_base}/render.html"
        resp = requests.get(endpoint, params={"url": url, "timeout": int(timeout)}, timeout=timeout + 5)
        html = resp.text
    return {
        "url": url,
        "status_code": resp.status_code,
        "html": html,
        "backend": "splash",
        "splash": True,
        "lua_script": lua_script,
    }
