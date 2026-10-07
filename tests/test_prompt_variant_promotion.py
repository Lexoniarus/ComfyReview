"""Behavior tests for evidence-based prompt standard promotion."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from comfyreview.__main__ import main
from comfyreview.application.prompt_catalog import (
    CreatePromptComponentCommand,
    PromptCatalogService,
    RevisePromptComponentCommand,
)
from comfyreview.application.prompt_variant_guidance import (
    PromptVariantCoverage,
    PromptVariantGuidance,
    PromptVariantRecipe,
    PromptVariantRecommendation,
    PromptVariantScore,
)
from comfyreview.application.prompt_variant_promotion import (
    PromptPromotionCoordinator,
    PromptPromotionDecision,
    PromptPromotionPolicy,
    PromptPromotionResult,
)
from comfyreview.domain import PromptAtomUsage
from comfyreview.repositories.sqlite.canonical_schema import (
    CanonicalSchemaManager,
)
from comfyreview.repositories.sqlite.prompt_catalog import (
    SqlitePromptCatalogRepository,
)
from comfyreview.repositories.sqlite.prompt_variant_promotion import (
    SqlitePromptPromotionRepository,
)


class _IdentitySource:
    def new_component_uid(self) -> str:
        return "prompt-component-aiko"


def _score(
    lower_bound: float,
    *,
    image_count: int = 5,
    sufficiently_observed: bool = True,
) -> PromptVariantScore:
    return PromptVariantScore(
        lower_bound=lower_bound,
        expected_success_rate=0.8,
        average_rating=8.0,
        image_count=image_count,
        review_count=image_count,
        standard_deviation=0.1,
        sufficiently_observed=sufficiently_observed,
    )


def _recommendation(
    recipe: PromptVariantRecipe,
    lower_bound: float,
    *,
    revision_uid: str | None = None,
) -> PromptVariantRecommendation:
    return PromptVariantRecommendation(
        recipe=recipe,
        score=_score(lower_bound),
        revision_uid=revision_uid,
    )


def _guidance(
    *,
    current: PromptVariantRecommendation,
    best: PromptVariantRecommendation | None,
    provisional: bool,
) -> PromptVariantGuidance:
    return PromptVariantGuidance(
        current_standard=current,
        current_provisional=provisional,
        best_observed=best,
        optimized=current,
        next_test=None,
        coverage=PromptVariantCoverage(5, 5, 1, 1, 0, 1),
    )


def test_promotion_policy_requires_stability_and_hysteresis() -> None:
    current_recipe = PromptVariantRecipe((PromptAtomUsage("aiko", 1000),), ())
    candidate_recipe = PromptVariantRecipe(
        (PromptAtomUsage("aiko", 1100),), ()
    )
    current = _recommendation(
        current_recipe, 0.50, revision_uid="revision-current"
    )
    policy = PromptPromotionPolicy()

    insufficient = PromptVariantRecommendation(
        recipe=candidate_recipe,
        score=_score(0.90, image_count=4, sufficiently_observed=False),
    )
    assert not policy.evaluate(
        "component",
        _guidance(current=current, best=insufficient, provisional=True),
    ).should_promote
    assert not policy.evaluate(
        "component",
        _guidance(
            current=current,
            best=_recommendation(candidate_recipe, 0.519),
            provisional=False,
        ),
    ).should_promote
    assert policy.evaluate(
        "component",
        _guidance(
            current=current,
            best=_recommendation(candidate_recipe, 0.52),
            provisional=False,
        ),
    ).should_promote
    assert policy.evaluate(
        "component",
        _guidance(
            current=current,
            best=_recommendation(current_recipe, 0.50),
            provisional=True,
        ),
    ).should_promote


class _Guidance:
    def __init__(self, by_component: dict[str, PromptVariantGuidance]) -> None:
        self.by_component = by_component

    def build(self, component_uid: str) -> PromptVariantGuidance:
        return self.by_component[component_uid]


class _Promotions:
    def __init__(self) -> None:
        self.promoted: list[str] = []

    def list_component_uids(self) -> tuple[str, ...]:
        return ("a", "b")

    def list_component_uids_for_image(self, image_uid: str) -> tuple[str, ...]:
        assert image_uid == "image-a"
        return ("b",)

    def promote(
        self,
        decision: PromptPromotionDecision,
        *,
        policy_version: str,
    ) -> PromptPromotionResult:
        assert policy_version == "prompt-guidance-v1"
        self.promoted.append(decision.component_uid)
        return PromptPromotionResult(
            component_uid=decision.component_uid,
            previous_revision_uid=decision.previous_revision_uid,
            revision_uid=f"revision-{decision.component_uid}",
            promotion_uid=f"promotion-{decision.component_uid}",
            created_revision=False,
            created_promotion=True,
        )


def test_promotion_coordinator_audits_and_reconciles_bounded_components() -> (
    None
):
    current_recipe = PromptVariantRecipe((PromptAtomUsage("aiko", 1000),), ())
    changed_recipe = PromptVariantRecipe((PromptAtomUsage("aiko", 1100),), ())
    current = _recommendation(
        current_recipe, 0.50, revision_uid="revision-current"
    )
    eligible = _guidance(
        current=current,
        best=_recommendation(changed_recipe, 0.60),
        provisional=False,
    )
    stable = _guidance(
        current=current,
        best=_recommendation(current_recipe, 0.60),
        provisional=False,
    )
    repository = _Promotions()
    coordinator = PromptPromotionCoordinator(
        guidance=_Guidance({"a": stable, "b": eligible}),  # type: ignore[arg-type]
        repository=repository,
    )

    audited = coordinator.audit()
    image_result = coordinator.reconcile_image("image-a")
    all_result = coordinator.reconcile_all()

    assert [item.should_promote for item in audited] == [False, True]
    assert image_result.evaluated == 1
    assert image_result.eligible == 1
    assert image_result.promoted == 1
    assert all_result.evaluated == 2
    assert all_result.eligible == 1
    assert repository.promoted == ["b", "b"]


def test_promotion_repository_creates_reuses_and_returns_to_revisions(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    catalog = PromptCatalogService(
        repository=SqlitePromptCatalogRepository(database_path),
        identities=_IdentitySource(),
    )
    created = catalog.create_component(
        CreatePromptComponentCommand(
            kind="character",
            component_key="aiko",
            name="Aiko",
            positive_atoms=(PromptAtomUsage("aiko", 1000),),
        )
    )
    repository = SqlitePromptPromotionRepository(database_path)
    first_recipe = PromptVariantRecipe(
        created.latest_revision.positive_atoms,
        created.latest_revision.negative_atoms,
    )
    stabilize = PromptPromotionDecision(
        component_uid=created.component_uid,
        should_promote=True,
        reason="provisional_standard_replaced",
        recommendation=_recommendation(
            first_recipe,
            0.60,
            revision_uid=created.latest_revision.revision_uid,
        ),
        previous_revision_uid=created.latest_revision.revision_uid,
    )
    stabilized = repository.promote(
        stabilize, policy_version="prompt-guidance-v1"
    )
    assert stabilized.created_revision is False
    assert stabilized.created_promotion is True
    assert (
        repository.promote(
            stabilize, policy_version="prompt-guidance-v1"
        ).created_promotion
        is False
    )

    changed_recipe = PromptVariantRecipe((PromptAtomUsage("aiko", 1150),), ())
    changed = repository.promote(
        PromptPromotionDecision(
            component_uid=created.component_uid,
            should_promote=True,
            reason="lower_bound_margin_reached",
            recommendation=_recommendation(changed_recipe, 0.70),
            previous_revision_uid=created.latest_revision.revision_uid,
        ),
        policy_version="prompt-guidance-v1",
    )
    assert changed.created_revision is True
    assert (
        catalog.get_component(created.component_uid).current_revision
        == (catalog.list_revisions(created.component_uid)[1])
    )

    newest = catalog.add_revision(
        RevisePromptComponentCommand(
            component_uid=created.component_uid,
            positive_atoms=(PromptAtomUsage("aiko detailed", 1000),),
            negative_atoms=(),
        )
    )
    returned = repository.promote(
        PromptPromotionDecision(
            component_uid=created.component_uid,
            should_promote=True,
            reason="lower_bound_margin_reached",
            recommendation=_recommendation(
                first_recipe,
                0.75,
                revision_uid=created.latest_revision.revision_uid,
            ),
            previous_revision_uid=changed.revision_uid,
        ),
        policy_version="prompt-guidance-v1",
    )
    component = catalog.get_component(created.component_uid)
    assert returned.created_revision is False
    assert component.current_revision == created.latest_revision
    assert component.latest_revision == newest
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_component_promotions"
        ).fetchone() == (4,)


def test_prompt_promotion_cli_audits_and_reconciles_explicit_database(
    tmp_path: Path,
    capsys,
) -> None:
    database_path = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()

    audit_code = main(
        ["prompt-promotions", "audit", "--database", str(database_path)]
    )
    audit = json.loads(capsys.readouterr().out)
    reconcile_code = main(
        [
            "prompt-promotions",
            "reconcile",
            "--database",
            str(database_path),
        ]
    )
    reconcile = json.loads(capsys.readouterr().out)

    assert audit_code == 0
    assert audit["evaluated"] == 0
    assert audit["decisions"] == []
    assert reconcile_code == 0
    assert reconcile["promoted"] == 0
