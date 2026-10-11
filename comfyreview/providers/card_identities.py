"""Opaque identities for confirmed POC Cards."""

from __future__ import annotations

from uuid import uuid4


class UuidCardIdentitySource:
    """Create stable UUID-based Card identities."""

    def new_card_id(self) -> str:
        """Return one new opaque Card identity."""
        return f"card-{uuid4()}"
