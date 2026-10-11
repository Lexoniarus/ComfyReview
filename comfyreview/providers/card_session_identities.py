"""Opaque identities for Card Factory prototype sessions."""

from uuid import uuid4


class UuidCardSessionIdentitySource:
    """Create random UUID-based prototype Card identities."""

    def new_id(self) -> str:
        """Return one new opaque identity."""
        return f"card-session-{uuid4()}"
