from __future__ import annotations

from datetime import UTC, datetime


def utc_now_str() -> str:
    """Return current UTC time in the worker timestamp format."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def parse_utc_ts_to_epoch(ts: str) -> float | None:
    """Parse our UTC timestamp format into epoch seconds."""
    s = str(ts or "").strip()
    if not s:
        return None
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        return dt.timestamp()
    except Exception:
        return None
