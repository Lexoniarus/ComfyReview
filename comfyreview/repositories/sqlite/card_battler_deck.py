"""SQLite persistence for the one bounded POC Card deck."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.card_battler_deck import (
    CardDeckConflictError,
    CardDeckNotFoundError,
)
from comfyreview.domain.card_battler import CardDeck, CardDeckEntry
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteCardDeckRepository:
    """Persist ordered deck membership through one short CAS transaction."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def get(self, deck_id: str = "poc-deck") -> CardDeck | None:
        """Return the current deck and contiguous ordered membership."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                "SELECT deck_id, revision, capacity FROM card_decks "
                "WHERE deck_id = ?",
                (deck_id,),
            ).fetchone()
            if row is None:
                return None
            entries = connection.execute(
                """
                SELECT card_id, position FROM card_deck_entries
                WHERE deck_id = ? ORDER BY position
                """,
                (deck_id,),
            ).fetchall()
            return CardDeck(
                deck_id=str(row["deck_id"]),
                revision=int(row["revision"]),
                capacity=int(row["capacity"]),
                entries=tuple(
                    CardDeckEntry(str(item["card_id"]), int(item["position"]))
                    for item in entries
                ),
            )
        finally:
            connection.close()

    def replace_entries(
        self,
        deck_id: str,
        entries: tuple[CardDeckEntry, ...],
        *,
        expected_revision: int,
    ) -> CardDeck:
        """Atomically replace ordered membership by revision CAS."""
        CardDeck(deck_id, expected_revision, entries)
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE card_decks SET revision = revision + 1,
                    updated_at = datetime('now')
                WHERE deck_id = ? AND revision = ?
                """,
                (deck_id, expected_revision),
            )
            if updated.rowcount != 1:
                exists = connection.execute(
                    "SELECT 1 FROM card_decks WHERE deck_id = ?",
                    (deck_id,),
                ).fetchone()
                if exists is None:
                    raise CardDeckNotFoundError(deck_id)
                raise CardDeckConflictError("Deck revision is stale")
            connection.execute(
                "DELETE FROM card_deck_entries WHERE deck_id = ?",
                (deck_id,),
            )
            connection.executemany(
                """
                INSERT INTO card_deck_entries(deck_id, card_id, position)
                VALUES (?, ?, ?)
                """,
                (
                    (deck_id, entry.card_id, entry.position)
                    for entry in entries
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            connection.rollback()
            raise CardDeckConflictError(
                "Deck membership contains an unavailable or duplicate Card"
            ) from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        deck = self.get(deck_id)
        if deck is None:
            raise CardDeckNotFoundError(deck_id)
        return deck
