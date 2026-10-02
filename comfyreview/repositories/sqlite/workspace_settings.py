"""SQLite repositories for canonical workspace settings."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.workspace_settings import (
    GenerationLoraSelection,
    GenerationProfile,
    WorkspacePreferences,
)
from comfyreview.repositories.sqlite.connection import connect_existing


class SqliteWorkspacePreferencesRepository:
    """Persist the singleton typed workspace preferences."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def get(self) -> WorkspacePreferences:
        """Return current preferences and their ordered curation sets."""
        with connect_existing(self._database_path, rows=True) as connection:
            row = connection.execute(
                """
                SELECT preference.density,
                       preference.motion,
                       preference.analytics_page_size,
                       profile.profile_uid AS default_profile_uid,
                       preference.review_unrated_only,
                       preference.review_max_attempts,
                       preference.default_curation_set_key
                FROM workspace_preferences AS preference
                LEFT JOIN generation_profiles AS profile
                  ON profile.id = preference.default_generation_profile_id
                WHERE preference.singleton_id = 1
                """
            ).fetchone()
            if row is None:
                raise RuntimeError("workspace preferences are missing")
            order = tuple(
                str(item[0])
                for item in connection.execute(
                    """
                    SELECT set_key
                    FROM workspace_curation_set_order
                    WHERE singleton_id = 1
                    ORDER BY position
                    """
                ).fetchall()
            )
            return WorkspacePreferences(
                density=str(row["density"]),
                motion=str(row["motion"]),
                analytics_page_size=int(row["analytics_page_size"]),
                default_generation_profile_uid=(
                    str(row["default_profile_uid"])
                    if row["default_profile_uid"] is not None
                    else None
                ),
                review_unrated_only=bool(row["review_unrated_only"]),
                review_max_attempts=int(row["review_max_attempts"]),
                default_curation_set_key=(
                    str(row["default_curation_set_key"])
                    if row["default_curation_set_key"] is not None
                    else None
                ),
                curation_set_order=order,
            )

    def save(self, preferences: WorkspacePreferences) -> WorkspacePreferences:
        """Replace preferences and ordered set keys in one transaction."""
        with connect_existing(self._database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            profile_id = self._profile_id(
                connection,
                preferences.default_generation_profile_uid,
            )
            connection.execute(
                """
                UPDATE workspace_preferences
                SET density = ?,
                    motion = ?,
                    analytics_page_size = ?,
                    default_generation_profile_id = ?,
                    review_unrated_only = ?,
                    review_max_attempts = ?,
                    default_curation_set_key = ?,
                    updated_at = datetime('now')
                WHERE singleton_id = 1
                """,
                (
                    preferences.density,
                    preferences.motion,
                    preferences.analytics_page_size,
                    profile_id,
                    int(preferences.review_unrated_only),
                    preferences.review_max_attempts,
                    preferences.default_curation_set_key,
                ),
            )
            connection.execute(
                "DELETE FROM workspace_curation_set_order "
                "WHERE singleton_id = 1"
            )
            connection.executemany(
                """
                INSERT INTO workspace_curation_set_order(
                    singleton_id, set_key, position
                ) VALUES (1, ?, ?)
                """,
                tuple(
                    (set_key, position)
                    for position, set_key in enumerate(
                        preferences.curation_set_order
                    )
                ),
            )
            connection.commit()
        return self.get()

    @staticmethod
    def _profile_id(
        connection: sqlite3.Connection,
        profile_uid: str | None,
    ) -> int | None:
        if profile_uid is None:
            return None
        row = connection.execute(
            "SELECT id FROM generation_profiles WHERE profile_uid = ?",
            (profile_uid,),
        ).fetchone()
        if row is None:
            raise KeyError(profile_uid)
        return int(row[0])


class SqliteGenerationProfileRepository:
    """Persist profiles and replace each ordered LoRA stack atomically."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def list_profiles(self) -> tuple[GenerationProfile, ...]:
        """Return every profile with stable presentation ordering."""
        with connect_existing(self._database_path, rows=True) as connection:
            rows = connection.execute(
                self._select_sql()
                + " ORDER BY (profile.archived_at IS NOT NULL), "
                "lower(profile.name), profile.profile_uid"
            ).fetchall()
            return tuple(self._profile(connection, row) for row in rows)

    def get(self, profile_uid: str) -> GenerationProfile:
        """Return one profile and its complete ordered LoRA stack."""
        with connect_existing(self._database_path, rows=True) as connection:
            row = connection.execute(
                self._select_sql() + " WHERE profile.profile_uid = ?",
                (profile_uid,),
            ).fetchone()
            if row is None:
                raise KeyError(profile_uid)
            return self._profile(connection, row)

    def save(self, profile: GenerationProfile) -> GenerationProfile:
        """Upsert one profile and replace its LoRA stack transactionally."""
        with connect_existing(self._database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO generation_profiles(
                    profile_uid, name, blueprint_uid, blueprint_version,
                    checkpoint, sampler, scheduler, seed_mode, fixed_seed,
                    steps_min, steps_max, cfg_min_milli, cfg_max_milli,
                    denoise_milli, batch_size, archived_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_uid) DO UPDATE SET
                    name = excluded.name,
                    blueprint_uid = excluded.blueprint_uid,
                    blueprint_version = excluded.blueprint_version,
                    checkpoint = excluded.checkpoint,
                    sampler = excluded.sampler,
                    scheduler = excluded.scheduler,
                    seed_mode = excluded.seed_mode,
                    fixed_seed = excluded.fixed_seed,
                    steps_min = excluded.steps_min,
                    steps_max = excluded.steps_max,
                    cfg_min_milli = excluded.cfg_min_milli,
                    cfg_max_milli = excluded.cfg_max_milli,
                    denoise_milli = excluded.denoise_milli,
                    batch_size = excluded.batch_size,
                    archived_at = excluded.archived_at,
                    updated_at = datetime('now')
                """,
                (
                    profile.profile_uid,
                    profile.name,
                    profile.blueprint_uid,
                    profile.blueprint_version,
                    profile.checkpoint,
                    profile.sampler,
                    profile.scheduler,
                    profile.seed_mode,
                    profile.fixed_seed,
                    profile.steps_min,
                    profile.steps_max,
                    profile.cfg_min_milli,
                    profile.cfg_max_milli,
                    profile.denoise_milli,
                    profile.batch_size,
                    "1970-01-01 00:00:00" if profile.archived else None,
                ),
            )
            profile_id = int(
                connection.execute(
                    "SELECT id FROM generation_profiles WHERE profile_uid = ?",
                    (profile.profile_uid,),
                ).fetchone()[0]
            )
            connection.execute(
                "DELETE FROM generation_profile_loras WHERE profile_id = ?",
                (profile_id,),
            )
            connection.executemany(
                """
                INSERT INTO generation_profile_loras(
                    profile_id, position, lora_name,
                    model_strength_milli, clip_strength_milli
                ) VALUES (?, ?, ?, ?, ?)
                """,
                tuple(
                    (
                        profile_id,
                        lora.position,
                        lora.name,
                        lora.model_strength_milli,
                        lora.clip_strength_milli,
                    )
                    for lora in profile.loras
                ),
            )
            connection.commit()
        return self.get(profile.profile_uid)

    def set_archived(
        self, profile_uid: str, archived: bool
    ) -> GenerationProfile:
        """Change only one profile lifecycle state."""
        with connect_existing(self._database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE generation_profiles
                SET archived_at = CASE WHEN ? THEN datetime('now') ELSE NULL END,
                    updated_at = datetime('now')
                WHERE profile_uid = ?
                """,
                (int(archived), profile_uid),
            )
            if cursor.rowcount != 1:
                raise KeyError(profile_uid)
            connection.commit()
        return self.get(profile_uid)

    @staticmethod
    def _select_sql() -> str:
        return """
            SELECT profile.*,
                   CASE WHEN preference.default_generation_profile_id = profile.id
                        THEN 1 ELSE 0 END AS is_default
            FROM generation_profiles AS profile
            LEFT JOIN workspace_preferences AS preference
              ON preference.singleton_id = 1
        """

    @staticmethod
    def _profile(
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> GenerationProfile:
        loras = tuple(
            GenerationLoraSelection(
                name=str(item["lora_name"]),
                model_strength_milli=int(item["model_strength_milli"]),
                clip_strength_milli=int(item["clip_strength_milli"]),
                position=int(item["position"]),
            )
            for item in connection.execute(
                """
                SELECT position, lora_name,
                       model_strength_milli, clip_strength_milli
                FROM generation_profile_loras
                WHERE profile_id = ?
                ORDER BY position
                """,
                (int(row["id"]),),
            ).fetchall()
        )
        return GenerationProfile(
            profile_uid=str(row["profile_uid"]),
            name=str(row["name"]),
            blueprint_uid=str(row["blueprint_uid"]),
            blueprint_version=int(row["blueprint_version"]),
            checkpoint=str(row["checkpoint"]),
            sampler=str(row["sampler"]),
            scheduler=str(row["scheduler"]),
            seed_mode=str(row["seed_mode"]),
            fixed_seed=(
                int(row["fixed_seed"])
                if row["fixed_seed"] is not None
                else None
            ),
            steps_min=int(row["steps_min"]),
            steps_max=int(row["steps_max"]),
            cfg_min_milli=int(row["cfg_min_milli"]),
            cfg_max_milli=int(row["cfg_max_milli"]),
            denoise_milli=int(row["denoise_milli"]),
            batch_size=int(row["batch_size"]),
            loras=loras,
            archived=row["archived_at"] is not None,
            is_default=bool(row["is_default"]),
        )
