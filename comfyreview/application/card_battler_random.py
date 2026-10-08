"""Domain-separated deterministic randomness for Card Battler materialization."""

from __future__ import annotations

import hashlib
import json


class DomainSeparatedCardRandom:
    """Derive independent counter-zero draws from stable seed material."""

    algorithm = "sha256-counter-v1"

    def __init__(self, seed_material: tuple[str, ...]) -> None:
        if not seed_material or any(not item for item in seed_material):
            raise ValueError(
                "random seed material must contain non-empty text"
            )
        self._seed_material = tuple(seed_material)

    def integer(self, domain: str, *, modulo: int) -> int:
        """Return one bounded integer derived only from the named domain."""
        if modulo <= 0:
            raise ValueError("random modulo must be positive")
        return self._integer(domain) % modulo

    def weighted_choice(
        self,
        domain: str,
        candidates: tuple[tuple[str, int], ...],
    ) -> str:
        """Choose deterministically from a key-stabilized weighted pool."""
        ordered = tuple(sorted(candidates, key=lambda item: item[0]))
        keys = tuple(key for key, _weight in ordered)
        if not ordered or len(keys) != len(set(keys)):
            raise ValueError("weighted candidates require unique stable keys")
        if any(not key or weight <= 0 for key, weight in ordered):
            raise ValueError("weighted candidates require positive weights")
        ticket = self.integer(
            domain,
            modulo=sum(weight for _key, weight in ordered),
        )
        cumulative = 0
        for key, weight in ordered[:-1]:
            cumulative += weight
            if ticket < cumulative:
                return key
        return ordered[-1][0]

    def _integer(self, domain: str) -> int:
        if not domain.strip():
            raise ValueError("random domain must be non-empty")
        payload = json.dumps(
            [*self._seed_material, domain],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        base_digest = hashlib.sha256(
            self.algorithm.encode("utf-8") + b"\0" + payload
        ).digest()
        digest = hashlib.sha256(base_digest + (0).to_bytes(8, "big")).digest()
        return int.from_bytes(digest, "big", signed=False)
