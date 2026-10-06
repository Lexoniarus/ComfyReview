"""Behavior tests for canonical ranking and Arena services."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import cast

import pytest

from comfyreview.application import (
    ArenaCompetitor,
    ArenaDecision,
    ArenaImageRotation,
    ArenaPair,
    ArenaPairingHistory,
    ArenaQuery,
    ArenaResult,
    ArenaService,
    ArenaValidationError,
    ImageContextQueryService,
    ImageQuery,
    RankedImage,
    RankingQuery,
    RankingService,
    RecordArenaDecisionCommand,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteArenaRepository,
    SqliteRankingRepository,
)


def _image(
    uid: str,
    *,
    average: float,
    count: int = 3,
    model: str = "model",
    subdir: str = "playground/Alice",
    set_key: str | None = None,
) -> RankedImage:
    return RankedImage(
        image_uid=uid,
        png_path=Path(f"C:/output/{uid}.png"),
        json_path=None,
        subdir=subdir,
        model_branch=model,
        checkpoint="checkpoint",
        combo_key="combo",
        positive_prompt="prompt",
        average_rating=average,
        rating_count=count,
        current_rating=round(average),
        sampler="euler",
        scheduler="normal",
        steps=20,
        cfg=7.0,
        denoise=1.0,
        assigned_set_key=set_key,
    )


class _RankingRepository:
    def __init__(self, images: tuple[RankedImage, ...]) -> None:
        self.images = images

    def list_ranked_images(self) -> tuple[RankedImage, ...]:
        return self.images


class _ArenaRepository:
    def __init__(
        self,
        *,
        directions: frozenset[tuple[str, str]] = frozenset(),
        rotations: tuple[ArenaImageRotation, ...] = (),
    ) -> None:
        self.directions = directions
        self.rotations = rotations
        self.saved: ArenaDecision | None = None

    def pairing_history(
        self,
        image_uids: tuple[str, ...],
    ) -> ArenaPairingHistory:
        assert image_uids
        return ArenaPairingHistory(self.directions, self.rotations)

    def get_competitors(
        self,
        left_image_uid: str,
        right_image_uid: str,
    ) -> tuple[ArenaCompetitor, ArenaCompetitor]:
        return (
            ArenaCompetitor(left_image_uid, 9.0),
            ArenaCompetitor(right_image_uid, 2.0),
        )

    def save_decision(self, decision: ArenaDecision) -> ArenaResult:
        self.saved = decision
        winner_uid = (
            decision.command.left_image_uid
            if decision.command.winner_side == "left"
            else decision.command.right_image_uid
        )
        return ArenaResult(
            match_uid="match",
            winner_image_uid=winner_uid,
            winner_rating=decision.winner_rating,
            loser_rating=decision.loser_rating,
        )


class _ImageContexts:
    def __init__(self, images: tuple[RankedImage, ...]) -> None:
        self.images = images

    def list_images(self, query):
        return type(
            "Page",
            (),
            {"entries": self.images, "query": query},
        )()


def _arena_service(
    repository: _ArenaRepository | SqliteArenaRepository,
    images: tuple[RankedImage, ...] = (),
) -> ArenaService:
    return ArenaService(
        images=cast(ImageContextQueryService, _ImageContexts(images)),
        repository=repository,
    )


def test_ranking_service_filters_and_sorts_canonical_images() -> None:
    service = RankingService(
        _RankingRepository(
            (
                _image("low", average=3.0, set_key="scene"),
                _image("high", average=9.0, count=5, set_key="scene"),
                _image("other-model", average=10.0, model="other"),
                _image("empty", average=10.0, subdir="playground/Empty"),
                _image("few", average=10.0, count=1, set_key="scene"),
            )
        )
    )

    ranked = service.list_images(
        RankingQuery(
            model="model",
            subdir=r"playground\Alice\scene",
            set_key="scene",
            mode="invalid",
            minimum_ratings=2,
            limit=2,
        )
    )

    assert [image.image_uid for image in ranked] == ["high", "low"]


def test_ranking_service_supports_worst_and_unsorted_filters() -> None:
    service = RankingService(
        _RankingRepository(
            (
                _image("rated-high", average=8.0),
                _image("rated-low", average=2.0, set_key="unsorted"),
                _image("curated", average=1.0, set_key="scene"),
                _image("empty", average=0.0, subdir="Empty"),
            )
        )
    )

    ranked = service.list_images(
        RankingQuery(
            set_key="unsorted",
            mode="worst",
            minimum_ratings=-1,
            limit=20,
        )
    )

    assert [image.image_uid for image in ranked] == [
        "rated-low",
        "rated-high",
    ]
    assert service.list_images(RankingQuery(limit=-1)) == ()


def test_arena_service_rotates_before_selecting_reverse_pair() -> None:
    images = (
        _image("a", average=9.0),
        _image("b", average=8.0),
        _image("c", average=7.0),
    )
    query = ImageQuery()
    forward = _arena_service(_ArenaRepository(), images).next_pair(
        ArenaQuery(query)
    )
    rotated = _arena_service(
        _ArenaRepository(
            directions=frozenset({("a", "b")}),
            rotations=(
                ArenaImageRotation("a", 1),
                ArenaImageRotation("b", 1),
                ArenaImageRotation("c", None),
            ),
        ),
        images,
    ).next_pair(ArenaQuery(query))
    complete = _arena_service(
        _ArenaRepository(
            directions=frozenset(
                (left.image_uid, right.image_uid)
                for left in images
                for right in images
                if left.image_uid != right.image_uid
            )
        ),
        images,
    ).next_pair(ArenaQuery(query))

    assert isinstance(forward, ArenaPair)
    assert (forward.left.image_uid, forward.right.image_uid) == ("a", "b")
    assert isinstance(rotated, ArenaPair)
    assert (rotated.left.image_uid, rotated.right.image_uid) == ("c", "a")
    assert complete is None


def test_arena_service_uses_reverse_after_the_pair_rotates_back() -> None:
    images = (
        _image("a", average=9.0),
        _image("b", average=8.0),
    )

    pair = _arena_service(
        _ArenaRepository(directions=frozenset({("a", "b")})),
        images,
    ).next_pair(ArenaQuery(ImageQuery()))

    assert isinstance(pair, ArenaPair)
    assert (pair.left.image_uid, pair.right.image_uid) == ("b", "a")


def test_arena_service_records_clamped_target_ratings() -> None:
    repository = _ArenaRepository()
    service = _arena_service(repository)

    result = service.record_decision(
        RecordArenaDecisionCommand("left", "right", "right")
    )

    assert result.winner_image_uid == "right"
    assert result.winner_rating == 10
    assert result.loser_rating == 1
    assert repository.saved is not None


@pytest.mark.parametrize(
    ("command", "message"),
    [
        (RecordArenaDecisionCommand("", "right", "left"), "distinct"),
        (RecordArenaDecisionCommand("same", "same", "left"), "distinct"),
        (RecordArenaDecisionCommand("left", "right", "draw"), "winner_side"),
    ],
)
def test_arena_service_rejects_invalid_commands(
    command: RecordArenaDecisionCommand,
    message: str,
) -> None:
    service = _arena_service(_ArenaRepository())

    with pytest.raises(ArenaValidationError, match=message):
        service.record_decision(command)


def _seed_canonical_database(database_path: Path, output_root: Path) -> None:
    CanonicalSchemaManager(database_path).prepare_startup()
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', 'pos', 'portrait')"
        )
        positive_id = int(
            connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        )
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', 'neg', '')"
        )
        negative_id = int(
            connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        )
        for index, (uid, rating) in enumerate((("left", 8), ("right", 4)), 1):
            cursor = connection.execute(
                """
                INSERT INTO generations(
                    generation_uid, model_branch, checkpoint, combo_key,
                    steps, cfg, sampler, scheduler, denoise, loras_json,
                    positive_prompt_id, negative_prompt_id
                )
                VALUES (?, 'model', 'checkpoint', 'combo', 20, 7.0,
                        'euler', 'normal', 1.0, '[]', ?, ?)
                """,
                (f"generation-{uid}", positive_id, negative_id),
            )
            generation_id = cursor.lastrowid
            assert generation_id is not None
            image_id = int(
                connection.execute(
                    """
                    INSERT INTO images(
                        image_uid, generation_id, output_node_id,
                        output_index, png_path, json_path
                    )
                    VALUES (?, ?, 'node', 0, ?, NULL)
                    RETURNING id
                    """,
                    (
                        uid,
                        generation_id,
                        str(
                            output_root / "playground" / "Alice" / f"{uid}.png"
                        ),
                    ),
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO review_events(
                    event_uid, image_id, event_type, rating, source,
                    source_key, sequence
                )
                VALUES (?, ?, 'rating', ?, 'test', ?, ?)
                """,
                (f"event-{uid}", image_id, rating, f"rating-{uid}", index),
            )
        connection.execute("UPDATE review_clock SET value = 2")
        connection.commit()
    finally:
        connection.close()


def test_sqlite_ranking_and_arena_use_canonical_facts_atomically(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    _seed_canonical_database(database_path, output_root)
    rankings = SqliteRankingRepository(
        database_path,
        output_root=output_root,
        allowed_set_keys=("scene",),
    )
    arena = SqliteArenaRepository(database_path)

    images = rankings.list_ranked_images()
    result = _arena_service(arena).record_decision(
        RecordArenaDecisionCommand("left", "right", "left")
    )

    assert [image.image_uid for image in images] == ["left", "right"]
    assert all(image.json_path is None for image in images)
    assert result.winner_image_uid == "left"
    history = arena.pairing_history(("left", "right"))
    assert history.played_directions == frozenset({("left", "right")})
    assert {item.image_uid for item in history.rotations} == {"left", "right"}
    with sqlite3.connect(database_path) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM arena_matches"
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM review_events"
            ).fetchone()[0]
            == 4
        )

    with pytest.raises(ArenaValidationError, match="already decided"):
        _arena_service(arena).record_decision(
            RecordArenaDecisionCommand("left", "right", "left")
        )
    with sqlite3.connect(database_path) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM arena_matches"
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM review_events"
            ).fetchone()[0]
            == 4
        )
