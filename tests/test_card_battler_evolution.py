"""Behavior tests for persistent four-slot Card evolution."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from comfyreview.application import (
    CardActiveImageKind,
    CardCandidateStatus,
    CardEvolutionGenerationPolicy,
    CardEvolutionService,
    CardGenerationLifecycle,
    CardGenerationOutputQuery,
    CardPresentationResult,
    CardPresentationStatus,
    CardReferenceImageStager,
    CardSession,
    CardSessionOperationState,
    CardSessionReferenceImageProvider,
    CardSourceImage,
    CardSourceImageProvider,
    GenerationMutationError,
    GenerationOutput,
    GenerationSubmission,
    SemanticImageProfile,
    SemanticSignal,
    StagedCardReferenceImage,
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
        self.requests = []
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
        return GenerationSubmission(
            generation_uid,
            self.observed.get(generation_uid, "submitted"),
            "prompt",
        )


def _service(tmp_path: Path):
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
            _ReferenceImages(),
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
    assert sessions.get("session-1").revision == 2
    assert (
        sessions.get("session-1").operation_state
        is CardSessionOperationState.GENERATING
    )


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

    accepted = service.accept(candidate.candidate_id, expected_revision=2)

    assert accepted.revision == 3
    assert accepted.active_image_uid == "accepted-image"
    assert accepted.active_content_hash == output.content_hash
    assert accepted.active_image_kind is CardActiveImageKind.CANDIDATE
    assert accepted.active_visual_tier == 1
    assert accepted.semantic_profile == _session().semantic_profile
    assert accepted.imprint == _session().imprint
    assert accepted.card == _session().card


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
