"""Behavior tests for shared Generator and Analytics render guidance."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pytest

from comfyreview.application.render_guidance import (
    GuidanceBasis,
    GuidanceParameter,
    GuidanceScope,
    RenderCapabilitySet,
    RenderEvidenceObservation,
    RenderGuidanceService,
    RenderSettings,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteRenderEvidenceRepository,
)


@dataclass
class _Repository:
    observations: tuple[RenderEvidenceObservation, ...]
    model: str = ""

    def list_observations(
        self, *, model: str = ""
    ) -> tuple[RenderEvidenceObservation, ...]:
        self.model = model
        return self.observations


def test_render_settings_and_capability_values_are_stable() -> None:
    settings = RenderSettings(
        "checkpoint-a", "sampler-a", "simple", 20, 6.5, 0.85
    )
    capabilities = RenderCapabilitySet(
        checkpoints=("checkpoint-a",),
        samplers=("sampler-a",),
        schedulers=("simple",),
    )

    assert settings.value(GuidanceParameter.CFG) == "6.5"
    assert settings.value(GuidanceParameter.DENOISE) == "0.85"
    assert settings.key == (
        "checkpoint=checkpoint-a|sampler=sampler-a|scheduler=simple|"
        "steps=20|cfg=6.5|denoise=0.85"
    )
    assert capabilities.supports(settings) is True
    assert (
        capabilities.supports(
            RenderSettings("missing", "sampler-a", "simple", 20, 6.5, 0.85)
        )
        is False
    )


def test_guidance_exposes_four_modes_with_independent_image_support() -> None:
    stable = RenderSettings("checkpoint-a", "sampler-a", "simple", 20, 6, 1)
    weak = RenderSettings("checkpoint-a", "sampler-b", "normal", 30, 8, 1)
    observations = tuple(
        [
            _observation(f"stable-{index}", stable, success=4, rating=9)
            for index in range(5)
        ]
        + [
            _observation(f"weak-{index}", weak, failure=3, rating=2)
            for index in range(5)
        ]
    )
    repository = _Repository(observations)

    result = RenderGuidanceService(repository).build(
        current=stable,
        capabilities=RenderCapabilitySet(
            checkpoints=("checkpoint-a",),
            samplers=("sampler-a", "sampler-b"),
            schedulers=("simple", "normal"),
        ),
        model=" model-a ",
        limit=8,
    )

    assert repository.model == "model-a"
    assert result.observed_setup is not None
    assert result.observed_setup.settings == stable
    assert result.observed_parameters is not None
    assert result.predicted_setup is not None
    assert result.predicted_parameters is not None
    assert result.current_observed is not None
    assert result.current_predicted is not None
    assert result.coverage.image_count == 10
    assert result.coverage.stable_setup_count == 2
    assert result.model_version == "render-guidance-v1"
    assert all(
        not item.evidence.jointly_observed for item in result.predicted_setups
    )


def test_guidance_keeps_unsupported_values_visible_but_not_applicable() -> (
    None
):
    retired = RenderSettings(
        "retired-checkpoint", "retired-sampler", "retired", 20, 6, 1
    )
    supported = RenderSettings(
        "active-checkpoint", "active-sampler", "active", 20, 6, 1
    )
    observations = tuple(
        [
            _observation(f"retired-{index}", retired, success=1, rating=8)
            for index in range(5)
        ]
        + [
            _observation(f"supported-{index}", supported, success=1, rating=9)
            for index in range(5)
        ]
    )

    result = RenderGuidanceService(_Repository(observations)).build(
        capabilities=RenderCapabilitySet(
            checkpoints=("active-checkpoint",),
            samplers=("active-sampler",),
            schedulers=("active",),
        )
    )

    assert result.observed_setup is not None
    assert result.observed_setup.settings == supported
    assert result.predicted_setup is None
    assert any(not item.applicable for item in result.observed_setups)
    assert any(not item.applicable for item in result.parameter_values)


def test_guidance_marks_sparse_values_insufficient_and_deterministic() -> None:
    settings = RenderSettings("checkpoint-a", "sampler-a", "simple", 20, 6, 1)
    observations = (
        _observation("image-a", settings, success=1, rating=10),
        _observation("image-b", settings, success=1, rating=10),
    )

    result = RenderGuidanceService(_Repository(observations)).build(limit=4)

    assert result.observed_setup is None
    assert result.predicted_setup is None
    assert result.predicted_parameters is None
    checkpoint = next(
        item
        for item in result.parameter_values
        if item.parameter is GuidanceParameter.CHECKPOINT
    )
    assert checkpoint.observed is not None
    assert checkpoint.observed.confidence.value == "insufficient"
    assert checkpoint.predicted is None


def test_guidance_covers_discovery_guards_and_high_confidence() -> None:
    supported = RenderSettings("checkpoint-a", "sampler-a", "simple", 20, 6, 1)
    observations = tuple(
        _observation(f"high-{index}", supported, success=1, rating=9)
        for index in range(30)
    )
    service = RenderGuidanceService(_Repository(observations))

    without_discovery = service.build(limit=0)
    with_high_confidence = service.build(limit=8)
    unknown_current = service.build(
        current=RenderSettings(
            "checkpoint-a", "missing-sampler", "simple", 20, 6, 1
        )
    )

    assert without_discovery.predicted_setups == ()
    assert with_high_confidence.observed_setups[
        0
    ].evidence.confidence.value == ("high")
    assert unknown_current.current_predicted is None

    unsupported = RenderSettings(
        "retired-checkpoint", "retired-sampler", "retired", 22, 7, 1
    )
    sparse = tuple(
        _observation(f"retired-{index}", unsupported, success=1, rating=8)
        for index in range(3)
    )
    blocked = RenderGuidanceService(_Repository(sparse)).build(
        capabilities=RenderCapabilitySet(
            checkpoints=("checkpoint-a",),
            samplers=("sampler-a",),
            schedulers=("simple",),
        )
    )

    assert blocked.predicted_setups == ()


def test_guidance_query_filters_server_side_and_validates_dimensions() -> None:
    first = RenderSettings("checkpoint-a", "sampler-a", "simple", 20, 6, 1)
    second = RenderSettings("checkpoint-a", "sampler-b", "normal", 30, 8, 1)
    observations = tuple(
        [
            _observation(f"first-{index}", first, success=2, rating=8)
            for index in range(5)
        ]
        + [
            _observation(f"second-{index}", second, failure=2, rating=3)
            for index in range(3)
        ]
    )
    service = RenderGuidanceService(_Repository(observations))

    page = service.query(
        basis=GuidanceBasis.OBSERVED,
        scope=GuidanceScope.SETUP,
        minimum_images=5,
        limit=1,
    )
    parameter_page = service.query(
        basis="predicted",
        scope="parameter",
        parameter="sampler",
        minimum_images=3,
    )

    assert page.total == 2
    assert page.filtered_total == 1
    assert len(page.entries) == 1
    assert parameter_page.parameter is GuidanceParameter.SAMPLER
    assert parameter_page.filtered_total == 2
    with pytest.raises(ValueError, match="requires"):
        service.query(basis="observed", scope="parameter")
    with pytest.raises(ValueError, match="does not accept"):
        service.query(basis="observed", scope="setup", parameter="sampler")
    with pytest.raises(ValueError):
        service.query(basis="unknown", scope="setup")


def test_sqlite_repository_aggregates_immutable_events_per_image(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "guidance.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path = tmp_path / "image.png"
    json_path = tmp_path / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")
    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO prompts(scope, prompt_hash, text) VALUES (?, ?, ?)",
            (("pos", "pos", "hero"), ("neg", "neg", "blur")),
        )
        connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key, seed,
                steps, cfg, sampler, scheduler, denoise, loras_json,
                positive_prompt_id, negative_prompt_id, source, status
            ) VALUES (
                'generation-1', 'anime', 'model.safetensors', 'combo', 1,
                24, 6.5, 'euler', 'normal', 1.0, '[]', 1, 2,
                'test', 'completed'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, json_path
            ) VALUES ('image-1', 1, 'save', 0, ?, ?)
            """,
            (str(png_path), str(json_path)),
        )
        connection.executemany(
            """
            INSERT INTO review_events(
                event_uid, image_id, event_type, rating, source,
                source_key, sequence
            ) VALUES (?, 1, 'rating', ?, 'test', ?, ?)
            """,
            (("event-1", 9, "one", 1), ("event-2", 3, "two", 2)),
        )
        connection.execute(
            """
            INSERT INTO review_events(
                event_uid, image_id, event_type, rating, source,
                source_key, sequence
            ) VALUES ('event-3', 1, 'delete', NULL, 'test', 'three', 3)
            """
        )

    observations = SqliteRenderEvidenceRepository(
        database_path
    ).list_observations(model="anime")

    assert len(observations) == 1
    assert observations[0].image_uid == "image-1"
    assert observations[0].review_count == 3
    assert observations[0].rating_weight == 5
    assert observations[0].failure_weight > 0
    assert observations[0].settings == RenderSettings(
        "model.safetensors", "euler", "normal", 24, 6.5, 1.0
    )


def _observation(
    image_uid: str,
    settings: RenderSettings,
    *,
    success: int = 0,
    failure: int = 0,
    rating: int | None = None,
) -> RenderEvidenceObservation:
    return RenderEvidenceObservation(
        image_uid=image_uid,
        settings=settings,
        success_weight=success,
        failure_weight=failure,
        rating_sum=float(rating or 0),
        rating_weight=1 if rating is not None else 0,
        review_count=1,
    )
