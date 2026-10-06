"""Behavior tests for fixed generation and rebuildable image geometry."""

from __future__ import annotations

import sqlite3
import struct
from pathlib import Path
from typing import cast

import pytest

from comfyreview.application import (
    AspectFormat,
    GenerationGeometryPolicy,
    ImageGeometryProjection,
    ImageGeometryProjectionService,
    OutputTier,
    PlaygroundEvidenceCandidate,
    PlaygroundEvidenceQuery,
    PlaygroundEvidenceService,
    ResolutionClass,
)
from comfyreview.domain import PromptAtomUsage
from comfyreview.providers import PngHeaderDimensionReader
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteImageGeometryRepository,
    SqlitePlaygroundEvidenceRepository,
)


@pytest.mark.parametrize(
    ("aspect", "resolution", "expected"),
    [
        ("2:3", "720", (720, 1080)),
        ("2:3", "1080", (1080, 1620)),
        ("2:3", "2160", (2160, 3240)),
        ("3:2", "720", (1080, 720)),
        ("3:2", "1080", (1620, 1080)),
        ("3:2", "2160", (3240, 2160)),
        ("16:9", "720", (1280, 720)),
        ("16:9", "1080", (1920, 1080)),
        ("16:9", "2160", (3840, 2160)),
        ("9:16", "720", (720, 1280)),
        ("9:16", "1080", (1080, 1920)),
        ("9:16", "2160", (2160, 3840)),
        ("1:1", "720", (720, 720)),
        ("1:1", "1080", (1080, 1080)),
        ("1:1", "2160", (2160, 2160)),
    ],
)
def test_generation_geometry_resolves_all_matrix_cells(
    aspect: str,
    resolution: str,
    expected: tuple[int, int],
) -> None:
    geometry = GenerationGeometryPolicy().resolve(
        AspectFormat(aspect), ResolutionClass(resolution)
    )

    assert (geometry.output_width, geometry.output_height) == expected


def test_generation_geometry_rejects_values_outside_the_fixed_matrix() -> None:
    with pytest.raises(ValueError, match="unsupported generation geometry"):
        GenerationGeometryPolicy().resolve(
            cast(AspectFormat, "4:3"), ResolutionClass.HD_720
        )


def test_output_tier_maps_to_resolution_classes() -> None:
    assert (
        OutputTier.FULL_HD_1080.to_resolution_class()
        is ResolutionClass.FULL_HD_1080
    )
    assert (
        OutputTier.from_resolution_class(ResolutionClass.UHD_2160)
        is OutputTier.UHD_4K
    )


def test_geometry_classifier_handles_known_sizes_and_higher_tie() -> None:
    policy = GenerationGeometryPolicy()

    values = {
        (1024, 1024): ("1:1", "1080", False),
        (4096, 4096): ("1:1", "2160", False),
        (2160, 3240): ("2:3", "2160", True),
        (3840, 2160): ("16:9", "2160", True),
        (900, 900): ("1:1", "1080", False),
    }
    for dimensions, expected in values.items():
        projection = policy.classify("image", *dimensions)
        assert (
            projection.aspect_format.value,
            projection.resolution_class.value,
            projection.exact,
        ) == expected


def test_geometry_rebuild_scans_files_then_atomically_replaces_projection(
    tmp_path: Path,
) -> None:
    database = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database).upgrade()
    valid = tmp_path / "valid.png"
    invalid = tmp_path / "invalid.png"
    valid.write_bytes(_png_header(2160, 3240))
    invalid.write_bytes(b"broken")
    _insert_images(database, valid, invalid)
    service = ImageGeometryProjectionService(
        SqliteImageGeometryRepository(database), PngHeaderDimensionReader()
    )

    result = service.rebuild()

    assert result.projected == 1
    assert result.diagnostics[0].image_uid == "image-invalid"
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT actual_width, actual_height, aspect_format, "
            "resolution_class, is_exact FROM image_geometry_projection"
        ).fetchone()
    assert row == (2160, 3240, "2:3", "2160", 1)


def test_geometry_projection_projects_single_image(tmp_path: Path) -> None:
    database = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database).upgrade()
    image = tmp_path / "image.png"
    image.write_bytes(_png_header(1280, 720))
    _insert_images(database, image, tmp_path / "unused.png")
    service = ImageGeometryProjectionService(
        SqliteImageGeometryRepository(database), PngHeaderDimensionReader()
    )

    from comfyreview.application import ImageGeometrySource

    projection = service.project(ImageGeometrySource("image-valid", image))

    assert projection.aspect_format is AspectFormat.LANDSCAPE_16_9
    assert projection.resolution_class is ResolutionClass.HD_720


def test_png_reader_resolves_relative_paths_against_output_root(
    tmp_path: Path,
) -> None:
    image = tmp_path / "nested" / "image.png"
    image.parent.mkdir()
    image.write_bytes(_png_header(1920, 1080))

    dimensions = PngHeaderDimensionReader(tmp_path).read(
        Path("nested/image.png")
    )

    assert dimensions == (1920, 1080)


def test_geometry_projection_replace_rolls_back_atomically(
    tmp_path: Path,
) -> None:
    database = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database).upgrade()
    valid = tmp_path / "valid.png"
    invalid = tmp_path / "invalid.png"
    valid.write_bytes(_png_header(720, 1080))
    invalid.write_bytes(_png_header(720, 1080))
    _insert_images(database, valid, invalid)
    repository = SqliteImageGeometryRepository(database)
    original = GenerationGeometryPolicy().classify("image-valid", 720, 1080)
    repository.replace_all((original,))

    with pytest.raises(sqlite3.IntegrityError):
        repository.replace_all(
            (
                ImageGeometryProjection(
                    image_uid="image-invalid",
                    actual_width=-1,
                    actual_height=1080,
                    aspect_format=AspectFormat.PORTRAIT_2_3,
                    resolution_class=ResolutionClass.HD_720,
                    target_width=720,
                    target_height=1080,
                    exact=False,
                ),
            )
        )

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT image_id, actual_width FROM image_geometry_projection"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][1] == 720


def test_playground_evidence_ranks_prompt_and_sampler_independently() -> None:
    prompt_candidate = _evidence_candidate(
        "prompt-image",
        positive=(PromptAtomUsage("hero", 1010),),
        checkpoint="other",
    )
    sampler_candidate = _evidence_candidate(
        "sampler-image",
        positive=(PromptAtomUsage("different", 1000),),
    )
    repository = _EvidenceRepository((prompt_candidate, sampler_candidate))
    service = PlaygroundEvidenceService(repository)

    evidence = service.find(
        PlaygroundEvidenceQuery(
            positive_atoms=(PromptAtomUsage("hero", 1000),),
            negative_atoms=(),
            checkpoint="model",
            sampler="euler",
            scheduler="normal",
            steps=24,
            cfg=6.5,
            denoise=1.0,
            aspect_format=AspectFormat.PORTRAIT_2_3,
            resolution_class=ResolutionClass.UHD_2160,
        )
    )

    assert evidence.prompt_match is not None
    assert evidence.prompt_match.image_uid == "prompt-image"
    assert evidence.sampler_match is not None
    assert evidence.sampler_match.image_uid == "sampler-image"


def test_playground_evidence_returns_explicit_empty_matches() -> None:
    service = PlaygroundEvidenceService(_EvidenceRepository(()))

    evidence = service.find(
        PlaygroundEvidenceQuery(
            positive_atoms=(),
            negative_atoms=(),
            checkpoint="model",
            sampler="euler",
            scheduler="normal",
            steps=24,
            cfg=6.5,
            denoise=1.0,
            aspect_format=AspectFormat.SQUARE_1_1,
            resolution_class=ResolutionClass.FULL_HD_1080,
        )
    )

    assert evidence.prompt_match is None
    assert evidence.sampler_match is None


def test_playground_evidence_repository_uses_central_content_visibility(
    tmp_path: Path,
) -> None:
    database = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database).upgrade()
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(_png_header(720, 1080))
    second.write_bytes(_png_header(720, 1080))
    _insert_images(database, first, second)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE generations SET inferred_content_level = 'explicit' "
            "WHERE generation_uid = 'generation-2'"
        )
        connection.execute(
            "DELETE FROM workspace_content_levels WHERE singleton_id = 1"
        )
        connection.execute(
            "INSERT INTO workspace_content_levels(singleton_id, level, position) "
            "VALUES (1, 'standard', 0)"
        )

    candidates = SqlitePlaygroundEvidenceRepository(database).list_candidates()

    assert tuple(item.image_uid for item in candidates) == ("image-valid",)


def _png_header(width: int, height: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
    )


def _insert_images(database: Path, valid: Path, invalid: Path) -> None:
    with sqlite3.connect(database) as connection:
        positive = connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) VALUES "
            "('pos', 'geometry-pos', 'hero')"
        ).lastrowid
        negative = connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) VALUES "
            "('neg', 'geometry-neg', 'blur')"
        ).lastrowid
        for index, (uid, path) in enumerate(
            (("image-valid", valid), ("image-invalid", invalid)), start=1
        ):
            generation = connection.execute(
                "INSERT INTO generations("
                "generation_uid, model_branch, checkpoint, combo_key, "
                "positive_prompt_id, negative_prompt_id"
                ") VALUES (?, 'model', 'model', '', ?, ?)",
                (f"generation-{index}", positive, negative),
            ).lastrowid
            connection.execute(
                "INSERT INTO images("
                "image_uid, generation_id, output_node_id, output_index, "
                "output_role, png_path, content_hash"
                ") VALUES (?, ?, 'save', 0, 'primary', ?, ?)",
                (uid, generation, str(path), f"hash-{index}"),
            )


class _EvidenceRepository:
    def __init__(
        self, candidates: tuple[PlaygroundEvidenceCandidate, ...]
    ) -> None:
        self._candidates = candidates

    def list_candidates(self) -> tuple[PlaygroundEvidenceCandidate, ...]:
        return self._candidates


def _evidence_candidate(
    image_uid: str,
    *,
    positive: tuple[PromptAtomUsage, ...],
    checkpoint: str = "model",
) -> PlaygroundEvidenceCandidate:
    return PlaygroundEvidenceCandidate(
        image_uid=image_uid,
        positive_atoms=positive,
        negative_atoms=(),
        checkpoint=checkpoint,
        sampler="euler",
        scheduler="normal",
        steps=24,
        cfg=6.5,
        denoise=1.0,
        aspect_format=AspectFormat.PORTRAIT_2_3,
        resolution_class=ResolutionClass.UHD_2160,
        average_rating=8.0,
        rating_count=3,
    )
