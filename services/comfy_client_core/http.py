from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from .types import ComfyResponse


def build_url(base_url: str, path: str) -> str:
    base = str(base_url).rstrip("/")
    p = str(path or "")
    if not p.startswith("/"):
        p = "/" + p
    return base + p


def http_json(
    *,
    base_url: str,
    method: str,
    path: str,
    payload: Optional[dict] = None,
    timeout: int = 30,
) -> ComfyResponse:
    """HTTP JSON helper using urllib only.

    Semantik absichtlich minimal und kompatibel:
    - gibt auch bei JSON parse errors ein dict mit _raw zurueck
    - HTTPError liefert ok False mit status_code
    """

    url = build_url(base_url, path)
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, headers=headers, method=str(method).upper())

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace").strip()
            try:
                js: Dict[str, Any] = json.loads(raw) if raw else {}
            except Exception:
                js = {"_raw": raw}
            return ComfyResponse(ok=True, status_code=int(resp.status), response_json=js)

    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", errors="replace").strip()
        except Exception:
            pass

        try:
            js = json.loads(raw) if raw else {}
        except Exception:
            js = {"_raw": raw} if raw else {}

        return ComfyResponse(
            ok=False,
            status_code=int(getattr(e, "code", 0) or 0),
            response_json=js,
            error=str(e),
        )

    except Exception as e:
        return ComfyResponse(ok=False, status_code=0, response_json={}, error=str(e))
