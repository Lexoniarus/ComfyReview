"""Behavior tests for the provider-independent card crafting lifecycle."""

from dataclasses import FrozenInstanceError, replace
from typing import cast

import pytest

from comfyreview.domain.card_battler import (
    CardImprint,
    CardRulesProvenance,
    CardStats,
    MaterializedMechanic,
    MaterializedTrait,
    StructuredCardSpec,
)
from comfyreview.domain.card_battler.crafting import (
    CandidateSlot,
    CardCraftingError,
    CardCraftingSession,
    CardIdentity,
    CardRevisionIdentity,
    ConfirmedCardRevision,
    CraftingSessionIdentity,
    CraftingStage,
)


def _spec(
    image_uid: str = "source-1",
    semantic_revision: str = "semantic-1",
    level: int = 1,
) -> StructuredCardSpec:
    imprint = CardImprint(
        world_style="urban",
        card_class="ranger",
        combat_role="precision",
        trait_lineage="marking",
        source_image_uid=image_uid,
        semantic_revision=semantic_revision,
        ruleset_key="prototype",
        ruleset_version=2,
        mapping_policy_key="semantic_imprint_mapping",
        mapping_policy_version=2,
        rng_policy_key="deterministic_rng",
        rng_policy_version=2,
        rng_algorithm="sha256-counter-v1",
        explicit_seed=42,
    )
    provenance = CardRulesProvenance(
        ruleset_key="prototype",
        ruleset_version=2,
        mapping_policy_key="semantic_imprint_mapping",
        mapping_policy_version=2,
        rng_policy_key="deterministic_rng",
        rng_policy_version=2,
        rng_algorithm="sha256-counter-v1",
        balance_policy_key="prototype_balance",
        balance_policy_version=2,
        explicit_seed=42,
        materialization_algorithm_revision="common-card-materialization-v1",
        rule_renderer_revision="canonical-rule-renderer-v1",
    )
    trait = MaterializedTrait(
        lineage_key="marking",
        mechanic=MaterializedMechanic(
            key="mark",
            trigger_key="on_attack",
            usage_limits=(),
            condition_groups=(),
            branches=(),
            costs=(),
            parameters=(),
        ),
        canonical_rule_text="Markierung",
    )
    return StructuredCardSpec(
        imprint=imprint,
        rarity_key="common",
        level=level,
        tier_ordinal=level,
        stats=CardStats(1_600, 1_400, 3_000, "balanced"),
        traits=(trait,),
        provenance=provenance,
    )


def _selected(
    *,
    base: ConfirmedCardRevision | None = None,
) -> CardCraftingSession:
    if base is None:
        state = CardCraftingSession.begin(
            session_identity=CraftingSessionIdentity("session-1"),
            card_identity=CardIdentity("card-1"),
            source_image_uid="source-1",
        )
    else:
        state = CardCraftingSession.begin_development(
            session_identity=CraftingSessionIdentity("session-2"),
            source_image_uid="source-1",
            base_revision=base,
        )
    return (
        state.record_analysis("semantic-1")
        .approve_analysis()
        .attach_draft(_spec(level=2 if base is not None else 1))
        .prepare_round()
        .record_candidates(
            ("generated-1", "generated-2", "generated-3", "generated-4")
        )
        .select_candidate(2)
    )


def test_crafting_lifecycle_requires_explicit_approval_and_confirmation() -> (
    None
):
    state = CardCraftingSession.begin(
        session_identity=CraftingSessionIdentity("attempt-1"),
        card_identity=CardIdentity("card-1"),
        source_image_uid="source-1",
    )
    assert state.stage is CraftingStage.SOURCE_SELECTED
    assert state.confirmed_revision is None
    analysis = state.record_analysis("semantic-1")
    assert analysis.stage is CraftingStage.ANALYSIS_AVAILABLE
    approved = analysis.approve_analysis()
    assert approved.stage is CraftingStage.ANALYSIS_APPROVED
    draft = approved.attach_draft(_spec())
    assert draft.stage is CraftingStage.DRAFT_AVAILABLE
    selected = (
        draft.prepare_round()
        .record_candidates(("a", "b", "c", "d"))
        .select_candidate(3)
    )
    assert selected.stage is CraftingStage.CANDIDATE_SELECTED
    assert selected.confirmed_revision is None
    ready = selected.mark_ready()
    assert ready.stage is CraftingStage.READY_FOR_CONFIRMATION
    assert ready.confirmed_revision is None
    confirmed = ready.confirm(CardRevisionIdentity("revision-1"))
    assert confirmed.stage is CraftingStage.CONFIRMED
    assert confirmed.confirmed_revision is not None
    assert confirmed.confirmed_revision.image_uid == "c"
    assert confirmed.confirmed_revision.card_identity == CardIdentity("card-1")
    assert confirmed.base_revision is None
    assert ready.confirmed_revision is None


def test_invalid_order_and_unapproved_or_mismatched_drafts_fail() -> None:
    initial = CardCraftingSession.begin(
        session_identity=CraftingSessionIdentity("session-1"),
        card_identity=CardIdentity("card-1"),
        source_image_uid="source-1",
    )
    with pytest.raises(CardCraftingError):
        initial.approve_analysis()
    with pytest.raises(CardCraftingError):
        initial.attach_draft(_spec())
    with pytest.raises(CardCraftingError):
        initial.prepare_round()
    analyzed = initial.record_analysis("semantic-1")
    with pytest.raises(CardCraftingError):
        analyzed.attach_draft(_spec())
    approved = analyzed.approve_analysis()
    with pytest.raises(CardCraftingError):
        approved.attach_draft(_spec(image_uid="wrong"))
    with pytest.raises(CardCraftingError):
        approved.attach_draft(_spec(semantic_revision="wrong"))
    corrupted = replace(
        _spec(),
        provenance=replace(_spec().provenance, ruleset_version=3),
    )
    with pytest.raises(CardCraftingError):
        approved.attach_draft(corrupted)
    with pytest.raises(CardCraftingError):
        approved.attach_draft(cast(StructuredCardSpec, None))
    with pytest.raises(CardCraftingError):
        initial.record_analysis("  ")


def test_round_has_exactly_four_ordered_slots_and_unique_images() -> None:
    prepared = (
        CardCraftingSession.begin(
            session_identity=CraftingSessionIdentity("session-1"),
            card_identity=CardIdentity("card-1"),
            source_image_uid="source-1",
        )
        .record_analysis("semantic-1")
        .approve_analysis()
        .attach_draft(_spec())
        .prepare_round()
    )
    assert tuple(slot.number for slot in prepared.slots) == (1, 2, 3, 4)
    assert all(slot.image_uid is None for slot in prepared.slots)
    with pytest.raises(CardCraftingError):
        prepared.select_candidate(1)
    with pytest.raises(CardCraftingError):
        prepared.record_candidates(
            cast(tuple[str, str, str, str], ("a", "b", "c"))
        )
    with pytest.raises(CardCraftingError):
        prepared.record_candidates(("a", "b", "c", "a"))
    with pytest.raises(CardCraftingError):
        prepared.record_candidates(("a", "b", "c", " "))
    with pytest.raises(CardCraftingError):
        CandidateSlot(5)
    with pytest.raises(CardCraftingError):
        CandidateSlot(1, "")
    generated = prepared.record_candidates(("a", "b", "c", "d"))
    assert generated.record_candidates(("a", "b", "c", "d")) is generated
    with pytest.raises(CardCraftingError):
        generated.record_candidates(("a", "b", "c", "e"))
    with pytest.raises(CardCraftingError):
        generated.select_candidate(0)
    with pytest.raises(CardCraftingError):
        generated.select_candidate(True)
    with pytest.raises(CardCraftingError):
        replace(prepared, slots=(CandidateSlot(1),))


def test_reject_all_never_confirms_and_allows_a_new_round() -> None:
    generated = _selected()
    with pytest.raises(CardCraftingError):
        generated.reject_all()
    source = (
        CardCraftingSession.begin(
            session_identity=CraftingSessionIdentity("session-1"),
            card_identity=CardIdentity("card-1"),
            source_image_uid="source-1",
        )
        .record_analysis("semantic-1")
        .approve_analysis()
        .attach_draft(_spec())
        .prepare_round()
        .record_candidates(("a", "b", "c", "d"))
    )
    rejected = source.reject_all()
    assert rejected.stage is CraftingStage.ROUND_REJECTED
    assert rejected.reject_all() is rejected
    assert rejected.confirmed_revision is None
    assert rejected.base_revision is None
    with pytest.raises(CardCraftingError):
        rejected.confirm(CardRevisionIdentity("revision-1"))
    again = rejected.prepare_round()
    assert again.round_number == 2
    assert len(again.slots) == 4
    assert all(slot.image_uid is None for slot in again.slots)
    assert again.card_identity == source.card_identity


def test_repeated_decisions_do_not_duplicate_confirmation() -> None:
    selected = _selected()
    assert selected.select_candidate(2) is selected
    with pytest.raises(CardCraftingError):
        selected.select_candidate(1)
    ready = selected.mark_ready()
    assert ready.mark_ready() is ready
    revision_id = CardRevisionIdentity("revision-1")
    confirmed = ready.confirm(revision_id)
    assert confirmed.confirm(revision_id) is confirmed
    with pytest.raises(CardCraftingError):
        confirmed.confirm(CardRevisionIdentity("revision-2"))
    with pytest.raises(CardCraftingError):
        confirmed.reject_all()
    with pytest.raises(CardCraftingError):
        ready.mark_ready().prepare_round()


def test_development_preserves_identity_and_confirmed_base_revision() -> None:
    old = _selected().mark_ready().confirm(CardRevisionIdentity("revision-1"))
    base = old.confirmed_revision
    assert base is not None
    working = _selected(base=base)
    assert working.card_identity is base.card_identity
    assert working.session_identity != old.session_identity
    assert working.base_revision is base
    assert working.draft is not base.spec
    assert working.draft is not None and working.draft.level == 2
    assert working.confirmed_revision is None
    with pytest.raises(CardCraftingError):
        working.mark_ready().confirm(base.revision_identity)
    with pytest.raises(CardCraftingError):
        working.reject_all()
    # Only a fresh explicit confirmation advances the card revision.
    developed = working.mark_ready().confirm(
        CardRevisionIdentity("revision-2")
    )
    assert developed.confirmed_revision is not None
    assert developed.confirmed_revision.card_identity is base.card_identity
    assert (
        developed.confirmed_revision.previous_revision_identity
        == base.revision_identity
    )
    assert old.confirmed_revision is base
    assert base.spec.level == 1
    assert developed.confirmed_revision.spec.level == 2


def test_rejected_development_does_not_mutate_confirmed_card() -> None:
    base = (
        _selected()
        .mark_ready()
        .confirm(CardRevisionIdentity("revision-1"))
        .confirmed_revision
    )
    assert base is not None
    development = CardCraftingSession.begin_development(
        session_identity=CraftingSessionIdentity("session-2"),
        source_image_uid="source-1",
        base_revision=base,
    )
    generated = (
        development.record_analysis("semantic-1")
        .approve_analysis()
        .attach_draft(_spec(level=2))
        .prepare_round()
        .record_candidates(("e", "f", "g", "h"))
    )
    rejected = generated.reject_all()
    assert rejected.base_revision is base
    assert rejected.confirmed_revision is None
    assert base.spec.level == 1
    assert base.image_uid == "generated-2"
    with pytest.raises(CardCraftingError):
        replace(development, card_identity=CardIdentity("other"))


def test_snapshots_and_identity_types_are_immutable_and_validated() -> None:
    state = _selected()
    with pytest.raises(FrozenInstanceError):
        state.stage = CraftingStage.CONFIRMED  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        state.slots[0].image_uid = "altered"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        state.card_identity.value = "altered"  # type: ignore[misc]
    assert state.draft is not None
    with pytest.raises(FrozenInstanceError):
        state.draft.level = 10  # type: ignore[misc]
    with pytest.raises(CardCraftingError):
        CraftingSessionIdentity("")
    with pytest.raises(CardCraftingError):
        CardIdentity(" ")
    with pytest.raises(CardCraftingError):
        CardRevisionIdentity("")
    with pytest.raises(CardCraftingError):
        replace(
            state,
            session_identity=cast(
                CraftingSessionIdentity, CardIdentity("wrong")
            ),
        )
    with pytest.raises(CardCraftingError):
        replace(state, stage=cast(CraftingStage, "invalid"))
    with pytest.raises(CardCraftingError):
        replace(state, selected_slot=None)
    with pytest.raises(CardCraftingError):
        replace(state, round_number=0)
    with pytest.raises(CardCraftingError):
        replace(state, round_number=-1)
    with pytest.raises(CardCraftingError):
        replace(state, round_number=cast(int, True))
    with pytest.raises(CardCraftingError):
        replace(state, slots=(CandidateSlot(1),) * 4)
    with pytest.raises(CardCraftingError):
        replace(state, slots=cast(tuple[CandidateSlot, ...], []))
    with pytest.raises(CardCraftingError):
        replace(state, slots=cast(tuple[CandidateSlot, ...], ("wrong",)))
    with pytest.raises(CardCraftingError):
        replace(state, selected_slot=cast(int, True))
    with pytest.raises(CardCraftingError):
        replace(state, base_revision=cast(ConfirmedCardRevision, "wrong"))
    with pytest.raises(CardCraftingError):
        replace(
            state.mark_ready().confirm(CardRevisionIdentity("rev")),
            confirmed_revision=cast(ConfirmedCardRevision, "wrong"),
        )


def test_confirmed_revision_must_match_its_card_and_selection() -> None:
    confirmed = (
        _selected().mark_ready().confirm(CardRevisionIdentity("revision-1"))
    )
    base = confirmed.confirmed_revision
    assert base is not None
    with pytest.raises(CardCraftingError):
        replace(confirmed, confirmed_revision=replace(base, image_uid="wrong"))
    with pytest.raises(CardCraftingError):
        replace(confirmed, confirmed_revision=None)
    with pytest.raises(CardCraftingError):
        replace(confirmed, stage=CraftingStage.CANDIDATES_AVAILABLE)
    with pytest.raises(CardCraftingError):
        ConfirmedCardRevision(
            CardIdentity("c"), CardRevisionIdentity("r"), _spec(), " "
        )
    with pytest.raises(CardCraftingError):
        replace(
            base,
            revision_identity=cast(
                CardRevisionIdentity, CardIdentity("wrong")
            ),
        )
    with pytest.raises(CardCraftingError):
        replace(
            confirmed,
            base_revision=replace(base, card_identity=CardIdentity("other")),
        )


def test_invalid_snapshot_combinations_and_revision_lineage_fail() -> None:
    selected = _selected()
    with pytest.raises(CardCraftingError):
        replace(selected, semantic_revision=None)
    with pytest.raises(CardCraftingError):
        replace(selected, draft=None)
    with pytest.raises(CardCraftingError):
        replace(selected, stage=CraftingStage.SOURCE_SELECTED)
    with pytest.raises(CardCraftingError):
        replace(
            selected,
            slots=(CandidateSlot(1, "a"),) * 4,
        )
    with pytest.raises(CardCraftingError):
        replace(
            selected,
            slots=(
                CandidateSlot(1),
                CandidateSlot(2),
                CandidateSlot(3),
                CandidateSlot(4),
            ),
        )
    with pytest.raises(CardCraftingError):
        replace(selected, selected_slot=7)
    with pytest.raises(CardCraftingError):
        replace(
            selected,
            slots=tuple(CandidateSlot(i, "duplicated") for i in range(1, 5)),
        )
    initial = CardCraftingSession.begin(
        session_identity=CraftingSessionIdentity("session-x"),
        card_identity=CardIdentity("card-x"),
        source_image_uid="source-1",
    )
    with pytest.raises(CardCraftingError):
        replace(initial, slots=(CandidateSlot(1),))
    with pytest.raises(CardCraftingError):
        replace(initial, source_image_uid=cast(str, None))
    with pytest.raises(CardCraftingError):
        ConfirmedCardRevision(
            CardIdentity("card-x"),
            CardRevisionIdentity("r"),
            _spec(),
            "image",
            CardRevisionIdentity("r"),
        )
    with pytest.raises(CardCraftingError):
        ConfirmedCardRevision(
            CardIdentity("card-x"),
            CardRevisionIdentity("r"),
            _spec(),
            "image",
            cast(CardRevisionIdentity, "not-typed"),
        )


def test_development_and_confirmation_require_typed_input() -> None:
    with pytest.raises(CardCraftingError):
        CardCraftingSession.begin_development(
            session_identity=CraftingSessionIdentity("session-new"),
            source_image_uid="source-1",
            base_revision=cast(ConfirmedCardRevision, None),
        )
    with pytest.raises(CardCraftingError):
        ConfirmedCardRevision(
            CardIdentity("card-1"),
            CardRevisionIdentity("rev-1"),
            cast(StructuredCardSpec, None),
            "image-1",
        )
