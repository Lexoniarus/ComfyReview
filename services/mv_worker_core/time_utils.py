from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def utc_now_str() -> str:
    """Return current UTC time in the worker timestamp format."""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def parse_utc_ts_to_epoch(ts: str) -> Optional[float]:
    """Parse our UTC timestamp format into epoch seconds."""
    s = str(ts or "").strip()
    if not s:
        return None
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None
