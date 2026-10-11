"""Behavior tests for persistent four-slot Card evolution."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from comfyreview.application import (
    CardActiveImageKind,
    CardCandidateRepository,
    CardCandidateStatus,
    CardDevelopmentService,
    CardEvolutionCandidate,
    CardEvolutionGenerationPolicy,
    CardEvolutionService,
    CardFactory,
    CardFactoryPrototypeService,
    CardFactorySessionQueryService,
    CardFactorySessionService,
    CardFactorySessionSnapshot,
    CardGenerationLifecycle,
    CardGenerationOutputQuery,
    CardPresentationRealizer,
    CardPresentationResult,
    CardPresentationStatus,
    CardReferenceImageStager,
    CardSession,
    CardSessionConflictError,
    CardSessionOperationState,
    CardSessionReferenceImageProvider,
    CardSessionRepository,
    CardSourceEligibilityPolicy,
    CardSourceImage,
    CardSourceImageProvider,
    GenerationMutationError,
    GenerationOutput,
    GenerationRequest,
    GenerationSubmission,
    GenerationValidationError,
    ImageContextQueryService,
    SemanticImageProfile,
    SemanticSignal,
    StagedCardReferenceImage,
    VisualPromptProjector,
)
from comfyreview.application.card_battler_session_service import (
    CardSessionIdentitySource,
)
from comfyreview.application.card_battler_visuals import (
    VISUAL_PROMPT_PROJECTION_REVISION,
    VisualPromptAtom,
    VisualPromptAtomSource,
    VisualPromptProvenance,
    VisualPromptRecipe,
)
from comfyreview.domain.card_battler import (
    CANONICAL_RULE_RENDERER_REVISION,
    COMMON_CARD_MATERIALIZATION_REVISION,
    CardImprint,
    CardRulesProvenance,
    CardStats,
    MaterializedMechanic,
    MaterializedTrait,
    StructuredCardSpec,
)
from comfyreview.providers import (
    CanonicalCardSessionReferenceImageProvider,
    CardRuntimeOutputQuery,
)
from comfyreview.repositories.sqlite import (
    CardBattlerRuntimeSchemaManager,
    SqliteCardCandidateRepository,
    SqliteCardGenerationOutputRepository,
    SqliteCardSessionRepository,
)


def _source() -> CardSourceImage:
    content = b"\x89PNG\r\n\x1a\nevolution"
    return CardSourceImage(
        "image-1",
        "image/png",
        content,
        hashlib.sha256(content).hexdigest(),
    )


def _imprint() -> CardImprint:
    return CardImprint(
        "near_future",
        "observer",
        "control",
        "focus",
        "image-1",
        "semantic-1",
        "prototype",
        3,
        "mapping",
        1,
        "rng",
        1,
        "sha256-counter-v1",
        42,
    )


def _card() -> StructuredCardSpec:
    mechanic = MaterializedMechanic("observe", "passive", (), (), (), (), ())
    return StructuredCardSpec(
        _imprint(),
        "common",
        1,
        1,
        CardStats(100, 200, 300, "defensive"),
        (MaterializedTrait("focus", mechanic, "Beobachte das Ziel."),),
        CardRulesProvenance(
            "prototype",
            3,
            "mapping",
            1,
            "rng",
            1,
            "sha256-counter-v1",
            "balance",
            1,
            42,
            COMMON_CARD_MATERIALIZATION_REVISION,
            CANONICAL_RULE_RENDERER_REVISION,
        ),
    )


def _recipe() -> VisualPromptRecipe:
    positive_source = VisualPromptAtomSource(
        "semantic", "calm", "required", 1000, 1
    )
    negative_source = VisualPromptAtomSource(
        "semantic", "blur", "required", 1000, 1
    )
    return VisualPromptRecipe(
        1,
        (
            VisualPromptAtom(
                "calm",
                "calm focused subject",
                "positive",
                1100,
                True,
                1,
                (positive_source,),
            ),
        ),
        (
            VisualPromptAtom(
                "blur",
                "blurry details",
                "negative",
                1000,
                True,
                1,
                (negative_source,),
            ),
        ),
        (),
        VisualPromptProvenance(
            "prototype",
            3,
            "projection",
            1,
            42,
            "sha256-counter-v1",
            VISUAL_PROMPT_PROJECTION_REVISION,
        ),
    )


def _session() -> CardSession:
    source = _source()
    return CardSession(
        "session-1",
        1,
        source.image_uid,
        source.content_hash,
        SemanticImageProfile(
            "image-1",
            "semantic-1",
            (SemanticSignal("calm", 700),),
        ),
        _imprint(),
        _card(),
        _recipe(),
        CardPresentationResult(None, CardPresentationStatus.INFERENCE_FAILED),
        source.image_uid,
        source.content_hash,
        CardActiveImageKind.SOURCE,
        0,
        CardSessionOperationState.IDLE,
    )


class _ReferenceImages:
    def load(self, session):
        assert session.active_image_uid == "image-1"
        return _source()


class _Stager:
    def stage(self, image):
        assert image == _source()
        return StagedCardReferenceImage(
            f"comfyreview/card-battler/{image.content_hash}.png",
            image.content_hash,
        )


class _Generations:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.requests: list[GenerationRequest] = []
        self.observed: dict[str, str] = {}

    def submit(self, request):
        slot = len(self.requests)
        self.requests.append(request)
        if slot == 1:
            raise GenerationMutationError("partial failure")
        generation_uid = f"generation-{slot}"
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                """
                INSERT INTO card_generations(
                    generation_uid, status, prompt_id, prepared_request_json,
                    compiled_workflow_json, workflow_hash,
                    output_policy_json, output_bindings_json
                ) VALUES (?, 'submitted', ?, '{}', '{}', 'hash', '{}', '[]')
                """,
                (generation_uid, f"prompt-{slot}"),
            )
            connection.commit()
        finally:
            connection.close()
        return GenerationSubmission(
            generation_uid, "submitted", f"prompt-{slot}"
        )

    def observe(self, generation_uid):
        if self.observed.get(generation_uid) == "error":
            raise GenerationValidationError("observation failed")
        return GenerationSubmission(
            generation_uid,
            self.observed.get(generation_uid, "submitted"),
            "prompt",
        )


class _ProofGenerations:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.requests: list[GenerationRequest] = []
        self.observed: dict[str, str] = {}

    def submit(self, request):
        slot = len(self.requests)
        self.requests.append(request)
        generation_uid = f"proof-generation-{slot}"
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                """
                INSERT INTO card_generations(
                    generation_uid, status, prompt_id, prepared_request_json,
                    compiled_workflow_json, workflow_hash,
                    output_policy_json, output_bindings_json
                ) VALUES (?, 'submitted', ?, '{}', '{}', 'hash', '{}', '[]')
                """,
                (generation_uid, f"proof-prompt-{slot}"),
            )
            connection.commit()
        finally:
            connection.close()
        return GenerationSubmission(
            generation_uid,
            "submitted",
            f"proof-prompt-{slot}",
        )

    def observe(self, generation_uid):
        return GenerationSubmission(
            generation_uid,
            self.observed.get(generation_uid, "submitted"),
            "proof-prompt",
        )


class _RecordingStager:
    def __init__(self) -> None:
        self.images: list[CardSourceImage] = []

    def stage(self, image):
        self.images.append(image)
        return StagedCardReferenceImage(
            f"comfyreview/card-battler/{image.content_hash}.png",
            image.content_hash,
        )


def _service(tmp_path: Path, *, reference_images: object | None = None):
    runtime = tmp_path / "runtime.sqlite3"
    output_root = tmp_path / "output"
    CardBattlerRuntimeSchemaManager(runtime).prepare_startup()
    sessions = SqliteCardSessionRepository(runtime)
    sessions.create(_session())
    candidates = SqliteCardCandidateRepository(runtime)
    generations = _Generations(runtime)
    outputs = SqliteCardGenerationOutputRepository(runtime, output_root)
    service = CardEvolutionService(
        sessions=sessions,
        candidates=candidates,
        reference_images=cast(
            CardSessionReferenceImageProvider,
            _ReferenceImages()
            if reference_images is None
            else reference_images,
        ),
        stager=cast(CardReferenceImageStager, _Stager()),
        policy=CardEvolutionGenerationPolicy(checkpoint="card.safetensors"),
        generations=cast(CardGenerationLifecycle, generations),
        outputs=cast(CardGenerationOutputQuery, outputs),
    )
    return service, sessions, candidates, generations, outputs, output_root


def test_generation_policy_builds_four_stable_fresh_requests() -> None:
    policy = CardEvolutionGenerationPolicy(checkpoint="card.safetensors")

    first = policy.build_requests(_session(), staged_reference="reference.png")
    second = policy.build_requests(
        _session(), staged_reference="reference.png"
    )

    assert first == second
    assert len(first) == 4
    assert len({item.sampler_stages[0].seed for item in first}) == 4
    assert [item.combo_key for item in first] == [
        f"session-1:tier-1:candidate-{slot}" for slot in range(4)
    ]
    assert all(item.reference_image == "reference.png" for item in first)
    assert all(
        item.prompt.positive_text == "(calm focused subject:1.10)"
        for item in first
    )
    assert all(
        item.prompt.negative_text == "(blurry details:1.00)" for item in first
    )


def test_candidate_and_generation_policy_reject_incomplete_inputs() -> None:
    candidate = CardEvolutionCandidate(
        "candidate-1",
        "session-1",
        1,
        0,
        1,
        "projection-v1",
        "recipe-hash",
        "image-1",
        "content-hash",
        CardCandidateStatus.PENDING,
    )
    with pytest.raises(ValueError, match="slot"):
        replace(candidate, slot_index=4)
    with pytest.raises(ValueError, match="positive"):
        replace(candidate, session_revision=0)
    with pytest.raises(ValueError, match="provenance"):
        replace(candidate, recipe_hash="")
    with pytest.raises(ValueError, match="checkpoint"):
        CardEvolutionGenerationPolicy(checkpoint=" ")

    policy = CardEvolutionGenerationPolicy(checkpoint="card.safetensors")
    with pytest.raises(ValueError, match="staged reference"):
        policy.build_requests(_session(), staged_reference=" ")
    one_channel = replace(
        _session(),
        visual_recipe=replace(_recipe(), negative_atoms=()),
    )
    with pytest.raises(ValueError, match="both prompt channels"):
        policy.build_requests(one_channel, staged_reference="reference.png")


def test_evolution_service_returns_four_slots_with_partial_failures(
    tmp_path: Path,
) -> None:
    service, sessions, _, generations, _, _ = _service(tmp_path)

    candidates = service.generate_candidates("session-1", expected_revision=1)

    assert [item.slot_index for item in candidates] == [0, 1, 2, 3]
    assert [item.status for item in candidates] == [
        CardCandidateStatus.SUBMITTED,
        CardCandidateStatus.FAILED,
        CardCandidateStatus.SUBMITTED,
        CardCandidateStatus.SUBMITTED,
    ]
    assert len(generations.requests) == 4
    persisted = sessions.get("session-1")
    assert persisted is not None
    assert persisted.revision == 2
    assert persisted.operation_state is CardSessionOperationState.GENERATING


def test_evolution_service_rejects_conflicts_and_marks_staging_failure(
    tmp_path: Path,
) -> None:
    service, sessions, _, _, _, _ = _service(tmp_path / "guards")
    with pytest.raises(KeyError, match="Unknown"):
        service.generate_candidates("missing", expected_revision=1)
    with pytest.raises(CardSessionConflictError, match="stale"):
        service.generate_candidates("session-1", expected_revision=0)
    current = sessions.get("session-1")
    assert current is not None
    sessions.replace(
        replace(
            current,
            revision=2,
            operation_state=CardSessionOperationState.GENERATING,
        ),
        expected_revision=1,
    )
    with pytest.raises(CardSessionConflictError, match="progress"):
        service.generate_candidates("session-1", expected_revision=2)

    class _FailingReferenceImages:
        def load(self, session):
            del session
            raise ValueError("reference changed")

    failing, _, _, _, _, _ = _service(
        tmp_path / "staging",
        reference_images=_FailingReferenceImages(),
    )
    failed = failing.generate_candidates("session-1", expected_revision=1)
    assert [item.status for item in failed] == [CardCandidateStatus.FAILED] * 4


def test_evolution_synchronization_marks_observation_and_output_failures(
    tmp_path: Path,
) -> None:
    service, _, _, generations, _, _ = _service(tmp_path)
    service.generate_candidates("session-1", expected_revision=1)
    generations.observed = {
        "generation-0": "completed",
        "generation-2": "error",
    }

    synchronized = service.synchronize("session-1", session_revision=2)

    assert synchronized[0].failure_category == "primary_output_missing"
    assert synchronized[2].failure_category == "GenerationValidationError"


def test_evolution_service_synchronizes_completed_primary_outputs(
    tmp_path: Path,
) -> None:
    service, _, _, generations, outputs, output_root = _service(tmp_path)
    initial = service.generate_candidates("session-1", expected_revision=1)
    completed = initial[0]
    assert completed.generation_uid == "generation-0"
    path = output_root / "card-battler" / "candidate.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"candidate")
    output = GenerationOutput(
        "candidate-image-0",
        "primary",
        "save",
        0,
        path,
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    outputs.save_outputs("generation-0", (output,))
    generations.observed = {
        "generation-0": "completed",
        "generation-2": "failed",
    }

    synchronized = service.synchronize("session-1", session_revision=2)

    assert synchronized[0].status is CardCandidateStatus.COMPLETED
    assert synchronized[0].output_image_uid == "candidate-image-0"
    assert synchronized[2].status is CardCandidateStatus.FAILED
    assert synchronized[3].status is CardCandidateStatus.SUBMITTED


def test_candidate_repository_accepts_only_current_completed_slot(
    tmp_path: Path,
) -> None:
    service, _, _, generations, outputs, output_root = _service(tmp_path)
    candidates = service.generate_candidates("session-1", expected_revision=1)
    candidate = candidates[0]
    path = output_root / "card-battler" / "accepted.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"accepted")
    output = GenerationOutput(
        "accepted-image",
        "primary",
        "save",
        0,
        path,
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    outputs.save_outputs("generation-0", (output,))
    generations.observed["generation-0"] = "completed"
    service.synchronize("session-1", session_revision=2)

    accepted = service.accept(
        "session-1", candidate.candidate_id, expected_revision=2
    )

    assert accepted.revision == 3
    assert accepted.active_image_uid == "accepted-image"
    assert accepted.active_content_hash == output.content_hash
    assert accepted.active_image_kind is CardActiveImageKind.CANDIDATE
    assert accepted.active_visual_tier == 1
    assert accepted.semantic_profile == _session().semantic_profile
    assert accepted.imprint == _session().imprint
    assert accepted.card == _session().card


def test_two_generation_reference_chain_preserves_card_identity(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime.sqlite3"
    output_root = tmp_path / "output"
    CardBattlerRuntimeSchemaManager(runtime).prepare_startup()
    sessions = SqliteCardSessionRepository(runtime)
    original = sessions.create(_session())
    candidates = SqliteCardCandidateRepository(runtime)
    outputs = SqliteCardGenerationOutputRepository(runtime, output_root)
    generations = _ProofGenerations(runtime)
    stager = _RecordingStager()

    class _CanonicalSources:
        def load(self, image_uid):
            assert image_uid == original.source_image_uid
            return _source()

    reference_images = CanonicalCardSessionReferenceImageProvider(
        cast(CardSourceImageProvider, _CanonicalSources()),
        cast(CardRuntimeOutputQuery, outputs),
    )
    evolution = CardEvolutionService(
        sessions=cast(CardSessionRepository, sessions),
        candidates=cast(CardCandidateRepository, candidates),
        reference_images=reference_images,
        stager=cast(CardReferenceImageStager, stager),
        policy=CardEvolutionGenerationPolicy(checkpoint="card.safetensors"),
        generations=cast(CardGenerationLifecycle, generations),
        outputs=cast(CardGenerationOutputQuery, outputs),
    )

    first_batch = evolution.generate_candidates(
        original.session_id,
        expected_revision=1,
    )
    candidate_b = first_batch[1]
    assert candidate_b.generation_uid == "proof-generation-1"
    candidate_path = output_root / "card-battler" / "candidate-b.png"
    candidate_path.parent.mkdir(parents=True)
    candidate_path.write_bytes(b"accepted candidate B")
    candidate_hash = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    outputs.save_outputs(
        candidate_b.generation_uid,
        (
            GenerationOutput(
                "candidate-b-image",
                "primary",
                "save",
                0,
                candidate_path,
                candidate_hash,
            ),
        ),
    )
    generations.observed[candidate_b.generation_uid] = "completed"
    evolution.synchronize(original.session_id, session_revision=2)
    accepted = evolution.accept(
        original.session_id,
        candidate_b.candidate_id,
        expected_revision=2,
    )

    class _Development:
        def advance(self, card):
            assert card == original.card
            return SimpleNamespace(
                card=replace(
                    card,
                    rarity_key="uncommon",
                    level=2,
                    tier_ordinal=2,
                    stats=CardStats(200, 400, 600, "defensive"),
                )
            )

    class _Projector:
        def project(self, profile, card, *, explicit_seed):
            assert profile == original.semantic_profile
            assert card.tier_ordinal == 2
            assert explicit_seed == original.card.provenance.explicit_seed
            return replace(_recipe(), tier_ordinal=2)

    class _Presenter:
        def realize(self, profile, card, *, existing=None):
            assert profile == original.semantic_profile
            assert card.tier_ordinal == 2
            assert existing is None
            return original.presentation

    session_service = CardFactorySessionService(
        image_contexts=cast(ImageContextQueryService, object()),
        source_images=cast(CardSourceImageProvider, object()),
        eligibility=CardSourceEligibilityPolicy(),
        factory=cast(CardFactory, object()),
        sessions=cast(CardSessionRepository, sessions),
        identities=cast(CardSessionIdentitySource, object()),
        development=cast(CardDevelopmentService, _Development()),
        visual_projector=cast(VisualPromptProjector, _Projector()),
        presentation_realizer=cast(CardPresentationRealizer, _Presenter()),
    )
    developed = session_service.develop(
        original.session_id,
        expected_revision=accepted.revision,
    )
    second_batch = evolution.generate_candidates(
        original.session_id,
        expected_revision=developed.revision,
    )

    staged_candidate_name = f"comfyreview/card-battler/{candidate_hash}.png"
    assert len(first_batch) == len(second_batch) == 4
    assert len(generations.requests) == 8
    assert all(
        request.reference_image == staged_candidate_name
        for request in generations.requests[4:]
    )
    assert [image.image_uid for image in stager.images] == [
        original.source_image_uid,
        "candidate-b-image",
    ]
    assert stager.images[1].content == b"accepted candidate B"
    persisted = sessions.get(original.session_id)
    assert persisted is not None
    assert persisted.semantic_profile == original.semantic_profile
    assert persisted.imprint == original.imprint
    assert persisted.card.imprint == original.card.imprint
    assert persisted.card.tier_ordinal == 2
    assert persisted.active_image_uid == "candidate-b-image"
    assert persisted.active_content_hash == candidate_hash


def test_reference_provider_reads_accepted_card_output_without_canonical_lookup(
    tmp_path: Path,
) -> None:
    path = tmp_path / "candidate.png"
    path.write_bytes(b"accepted candidate")
    content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    output = GenerationOutput(
        "accepted-image",
        "primary",
        "save",
        0,
        path,
        content_hash,
    )

    class _CanonicalSources:
        def load(self, image_uid):
            raise AssertionError(image_uid)

    class _CardOutputs:
        def output_by_image_uid(self, image_uid):
            assert image_uid == "accepted-image"
            return output

    session = replace(
        _session(),
        active_image_uid="accepted-image",
        active_content_hash=content_hash,
        active_image_kind=CardActiveImageKind.CANDIDATE,
        active_visual_tier=1,
    )
    provider = CanonicalCardSessionReferenceImageProvider(
        cast(CardSourceImageProvider, _CanonicalSources()),
        cast(CardRuntimeOutputQuery, _CardOutputs()),
    )

    loaded = provider.load(session)

    assert loaded.image_uid == "accepted-image"
    assert loaded.content == b"accepted candidate"
    assert loaded.content_hash == content_hash


def test_reference_provider_rejects_changed_source_bytes() -> None:
    class _CanonicalSources:
        def load(self, image_uid):
            assert image_uid == "image-1"
            content = b"changed source"
            return CardSourceImage(
                "image-1",
                "image/png",
                content,
                hashlib.sha256(content).hexdigest(),
            )

    class _CardOutputs:
        def output_by_image_uid(self, image_uid):
            raise AssertionError(image_uid)

    provider = CanonicalCardSessionReferenceImageProvider(
        cast(CardSourceImageProvider, _CanonicalSources()),
        cast(CardRuntimeOutputQuery, _CardOutputs()),
    )

    with pytest.raises(ValueError, match="hash no longer matches"):
        provider.load(_session())


def test_session_query_synchronizes_generating_batch_before_projection() -> (
    None
):
    session = replace(
        _session(),
        revision=2,
        operation_state=CardSessionOperationState.GENERATING,
    )
    synchronized: list[tuple[str, int]] = []

    class _Sessions:
        def get(self, session_id):
            assert session_id == "session-1"
            return session

    class _Evolution:
        def synchronize(self, session_id, *, session_revision):
            synchronized.append((session_id, session_revision))
            return ()

    class _Candidates:
        def latest_for_session(self, session_id):
            assert session_id == "session-1"
            return ()

    result = CardFactorySessionQueryService(
        sessions=cast(CardFactorySessionService, _Sessions()),
        evolution=cast(CardEvolutionService, _Evolution()),
        candidates=cast(CardCandidateRepository, _Candidates()),
    ).get("session-1")

    assert result.session == session
    assert result.candidates == ()
    assert synchronized == [("session-1", 2)]


def test_prototype_service_delegates_revision_safe_use_cases() -> None:
    session = _session()
    events: list[tuple[object, ...]] = []

    class _Sessions:
        def create(self, image_uid):
            events.append(("create", image_uid))
            return session

        def get(self, session_id):
            events.append(("session-get", session_id))
            return session

        def develop(self, session_id, *, expected_revision):
            events.append(("develop", session_id, expected_revision))
            return replace(session, revision=expected_revision + 1)

    class _Queries:
        def get(self, session_id):
            events.append(("query-get", session_id))
            return CardFactorySessionSnapshot(session, ())

    class _Evolution:
        def generate_candidates(self, session_id, *, expected_revision):
            events.append(("generate", session_id, expected_revision))
            return ()

        def accept(self, session_id, candidate_id, *, expected_revision):
            events.append(
                ("accept", session_id, candidate_id, expected_revision)
            )
            return session

    service = CardFactoryPrototypeService(
        sessions=cast(CardFactorySessionService, _Sessions()),
        queries=cast(CardFactorySessionQueryService, _Queries()),
        evolution=cast(CardEvolutionService, _Evolution()),
    )

    assert service.create("image-1").session == session
    assert service.get("session-1").session == session
    assert (
        service.develop("session-1", expected_revision=1).session.revision == 2
    )
    assert (
        service.generate_candidates("session-1", expected_revision=1).session
        == session
    )
    assert (
        service.accept_candidate(
            "session-1", "candidate-1", expected_revision=2
        ).session
        == session
    )
    assert events == [
        ("create", "image-1"),
        ("query-get", "session-1"),
        ("develop", "session-1", 1),
        ("generate", "session-1", 1),
        ("session-get", "session-1"),
        ("accept", "session-1", "candidate-1", 2),
        ("query-get", "session-1"),
    ]
