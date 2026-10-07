"""Behavior tests for evidence-guided prompt component variants."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from comfyreview.application import (
    PromptCurrentStandard,
    PromptVariantGuidanceService,
    PromptVariantObservation,
    PromptVariantRecipe,
)
from comfyreview.domain import PromptAtomUsage
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqlitePromptVariantEvidenceRepository,
)


def _recipe(
    *weights: int, texts: tuple[str, ...] | None = None
) -> PromptVariantRecipe:
    names = texts or tuple(f"atom-{index}" for index in range(len(weights)))
    return PromptVariantRecipe(
        tuple(
            PromptAtomUsage(text, weight)
            for text, weight in zip(names, weights, strict=True)
        ),
        (),
    )


def _observation(
    image: str,
    recipe: PromptVariantRecipe,
    *,
    success: int = 1,
    failure: int = 0,
    rating: int = 8,
    rating_weight: int = 1,
    reviews: int = 1,
    revision_uid: str = "revision-a",
) -> PromptVariantObservation:
    return PromptVariantObservation(
        image_uid=image,
        recipe=recipe,
        success_weight=success,
        failure_weight=failure,
        rating_sum=rating * rating_weight,
        rating_weight=rating_weight,
        review_count=reviews,
        revision_uid=revision_uid,
    )


@dataclass
class _Repository:
    current: PromptCurrentStandard
    observations: tuple[PromptVariantObservation, ...]

    def get_current_standard(
        self, component_uid: str
    ) -> PromptCurrentStandard:
        assert component_uid == self.current.component_uid
        return self.current

    def list_observations(
        self, component_uid: str
    ) -> tuple[PromptVariantObservation, ...]:
        assert component_uid == self.current.component_uid
        return self.observations


def _guidance(
    current: PromptVariantRecipe,
    observations: tuple[PromptVariantObservation, ...],
    *,
    provisional: bool = False,
):
    return PromptVariantGuidanceService(
        _Repository(
            PromptCurrentStandard(
                component_uid="component-a",
                revision_uid="revision-current",
                recipe=current,
                provisional=provisional,
            ),
            observations,
        )
    ).build("component-a")


def test_guidance_requires_five_independent_images_not_repeated_reviews() -> (
    None
):
    recipe = _recipe(1000)
    four_images = tuple(
        _observation(f"image-{index}", recipe) for index in range(4)
    )
    repeated = _observation(
        "one-image",
        recipe,
        success=14,
        rating_weight=14,
        reviews=3,
    )

    four = _guidance(recipe, four_images)
    one = _guidance(recipe, (repeated,))
    five = _guidance(
        recipe, four_images + (_observation("image-five", recipe),)
    )

    assert four.best_observed is not None
    assert four.best_observed.score.sufficiently_observed is False
    assert one.best_observed is not None
    assert one.best_observed.score.image_count == 1
    assert one.best_observed.score.review_count == 3
    assert one.best_observed.score.sufficiently_observed is False
    assert five.best_observed is not None
    assert five.best_observed.score.sufficiently_observed is True


def test_guidance_keeps_delete_evidence_and_conservative_observed_order() -> (
    None
):
    clean = _recipe(900)
    deleted = _recipe(1100)
    observations = tuple(
        _observation(f"clean-{index}", clean) for index in range(5)
    ) + tuple(
        _observation(
            f"deleted-{index}",
            deleted,
            success=1,
            failure=5 if index == 0 else 0,
        )
        for index in range(5)
    )

    result = _guidance(clean, observations)

    assert result.best_observed is not None
    assert result.best_observed.recipe == clean
    assert result.best_observed.score.lower_bound is not None
    assert result.coverage.stable_variant_count == 2


def test_guidance_interpolates_only_between_supported_weight_anchors() -> None:
    current = _recipe(1000, texts=("eyes",))
    low = _recipe(900, texts=("eyes",))
    high = _recipe(1100, texts=("eyes",))
    observations = tuple(
        _observation(f"low-{index}", low, success=1, failure=1)
        for index in range(3)
    ) + tuple(
        _observation(f"high-{index}", high, success=1) for index in range(3)
    )

    result = _guidance(current, observations)

    optimized_atom = result.optimized.recipe.positive_atoms[0]
    assert optimized_atom.text == "eyes"
    assert 900 <= optimized_atom.weight_milli <= 1100
    assert optimized_atom.weight_milli % 50 == 0
    assert result.coverage.modeled_atom_count == 1
    assert result.next_test is not None
    assert result.next_test.recipe.key not in {
        current.key,
        result.optimized.recipe.key,
    }
    assert (
        900 <= result.next_test.recipe.positive_atoms[0].weight_milli <= 1100
    )


def test_guidance_does_not_model_an_unsupported_weight_or_change_structure() -> (
    None
):
    current = _recipe(1000, 1250, texts=("eyes", "hair"))
    unsupported = _recipe(1500, 1250, texts=("eyes", "hair"))
    observations = (
        _observation("image-a", unsupported),
        _observation("image-b", unsupported),
    )

    result = _guidance(current, observations)

    assert result.optimized.recipe == current
    assert result.next_test is None
    assert result.coverage.modeled_atom_count == 0


def test_guidance_normalizes_combined_effects_for_longer_atom_lists() -> None:
    current = _recipe(1000, 1000, texts=("eyes", "hair"))
    varied = (
        _recipe(900, 900, texts=("eyes", "hair")),
        _recipe(1100, 1100, texts=("eyes", "hair")),
    )
    observations = tuple(
        _observation(f"low-{index}", varied[0], success=1, failure=1)
        for index in range(3)
    ) + tuple(
        _observation(f"high-{index}", varied[1], success=1)
        for index in range(3)
    )

    result = _guidance(current, observations)

    assert result.optimized.recipe.structural_key == current.structural_key
    assert 0.0 <= result.optimized.score.expected_success_rate <= 1.0
    assert result.coverage.modeled_atom_count == 2


def test_guidance_breaks_observed_ties_deterministically() -> None:
    first = _recipe(900)
    second = _recipe(1100)
    observations = tuple(
        _observation(f"first-{index}", first) for index in range(5)
    ) + tuple(_observation(f"second-{index}", second) for index in range(5))

    one = _guidance(first, observations)
    two = _guidance(first, tuple(reversed(observations)))

    assert one.best_observed is not None
    assert two.best_observed is not None
    assert one.best_observed.recipe.key == two.best_observed.recipe.key


def test_sqlite_prompt_variant_repository_reads_repeated_and_delete_events(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    with sqlite3.connect(database_path) as connection:
        component_id = connection.execute(
            "INSERT INTO prompt_components(component_uid, kind, component_key, name) "
            "VALUES ('component-a', 'character', 'a', 'A') RETURNING id"
        ).fetchone()[0]
        revision_id = connection.execute(
            "INSERT INTO prompt_revisions(revision_uid, component_id, "
            "revision_number, positive_text, negative_text, content_hash) "
            "VALUES ('revision-a', ?, 1, 'eyes', '', 'hash-a') RETURNING id",
            (component_id,),
        ).fetchone()[0]
        atom_id = connection.execute(
            "INSERT INTO prompt_atoms(canonical_text) VALUES ('eyes') RETURNING id"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO prompt_revision_atom_usages("
            "revision_id, atom_id, scope, position, weight_milli) "
            "VALUES (?, ?, 'pos', 0, 1000)",
            (revision_id, atom_id),
        )
        for index in (1, 2):
            positive_id = connection.execute(
                "INSERT INTO prompts(scope, prompt_hash, text) "
                "VALUES ('pos', ?, 'eyes') RETURNING id",
                (f"positive-{index}",),
            ).fetchone()[0]
            negative_id = connection.execute(
                "INSERT INTO prompts(scope, prompt_hash, text) "
                "VALUES ('neg', ?, '') RETURNING id",
                (f"negative-{index}",),
            ).fetchone()[0]
            generation_id = connection.execute(
                "INSERT INTO generations(generation_uid, model_branch, checkpoint, "
                "combo_key, positive_prompt_id, negative_prompt_id) "
                "VALUES (?, 'anime', 'model', 'combo', ?, ?) RETURNING id",
                (f"generation-{index}", positive_id, negative_id),
            ).fetchone()[0]
            image_id = connection.execute(
                "INSERT INTO images(image_uid, generation_id, output_node_id, "
                "output_index, png_path, output_role, content_hash) "
                "VALUES (?, ?, 'save', 0, ?, 'primary', ?) RETURNING id",
                (
                    f"image-{index}",
                    generation_id,
                    f"image-{index}.png",
                    f"image-hash-{index}",
                ),
            ).fetchone()[0]
            group_id = connection.execute(
                "INSERT INTO generation_prompt_groups(group_uid, generation_id, "
                "component_id, source_revision_id, kind, position, content_hash) "
                "VALUES (?, ?, ?, ?, 'character', 0, 'hash-a') RETURNING id",
                (f"group-{index}", generation_id, component_id, revision_id),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO generation_prompt_group_atom_usages("
                "group_id, atom_id, scope, position, weight_milli) "
                "VALUES (?, ?, 'pos', 0, 1000)",
                (group_id, atom_id),
            )
            ratings = (8, 9) if index == 1 else (10,)
            for run, rating in enumerate(ratings, 1):
                sequence = index * 10 + run
                connection.execute(
                    "INSERT INTO review_events(event_uid, image_id, event_type, "
                    "rating, source, source_key, sequence) "
                    "VALUES (?, ?, 'rating', ?, 'test', ?, ?)",
                    (
                        f"rating-{index}-{run}",
                        image_id,
                        rating,
                        f"rating-{index}-{run}",
                        sequence,
                    ),
                )
            if index == 2:
                connection.execute(
                    "INSERT INTO review_events(event_uid, image_id, event_type, "
                    "rating, source, source_key, sequence) "
                    "VALUES ('delete-2', ?, 'delete', NULL, 'test', 'delete-2', 99)",
                    (image_id,),
                )

    repository = SqlitePromptVariantEvidenceRepository(database_path)

    current = repository.get_current_standard("component-a")
    observations = repository.list_observations("component-a")

    assert current.revision_uid == "revision-a"
    assert current.provisional is True
    assert current.recipe == _recipe(1000, texts=("eyes",))
    assert len(observations) == 2
    assert observations[0].review_count == 2
    assert observations[0].success_weight == 5
    assert observations[1].failure_weight == 4
