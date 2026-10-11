"""Opaque identities and entropy for Card candidate groups."""

from __future__ import annotations

import secrets
from uuid import uuid4


class UuidCardCandidateGroupIdentitySource:
    """Create one UUID group identity and deterministic child identities."""

    def new_group_id(self) -> str:
        """Return one new opaque candidate-group identity."""
        return f"card-group-{uuid4()}"

    def candidate_id(self, group_id: str, slot_index: int) -> str:
        """Derive one stable slot identity inside the group."""
        if not group_id.strip() or not 0 <= slot_index < 4:
            raise ValueError("Candidate identity inputs are invalid")
        return f"{group_id}-candidate-{slot_index}"


class SecureCardCandidateGroupSeedSource:
    """Create non-predictable seeds that remain replayable once persisted."""

    def new_seed(self) -> int:
        """Return one SQLite-compatible nonnegative seed."""
        return secrets.randbelow(2**63 - 1)
