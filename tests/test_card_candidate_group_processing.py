"""Lifecycle tests for initial four-Card group composition."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupStatus,
    CardCandidateStatus,
)
from comfyreview.application.card_battler_candidate_processing import (
    InitialCardCandidateGroupProcessor,
)
from comfyreview.application.card_battler_factory import CardFactory
from comfyreview.application.card_battler_presentation import (
    CardPresentationResult,
    CardPresentationStatus,
)
from comfyreview.application.card_battler_semantics import (
    CardSourceImageProvider,
    SemanticImageAnalyzer,
)
from comfyreview.repositories.sqlite.card_battler_candidate_groups import (
    SqliteCardCandidateGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_runtime_schema import (
    CardBattlerRuntimeSchemaManager,
)
from tests.test_card_battler_factory import (
    _factory,
    _Mapper,
    _profile,
)
from tests.test_card_battler_factory import (
    _source as _changed_source,
)
from tests.test_card_candidate_group_reservation import _service, _SourceImages


def _repository(tmp_path: Path) -> SqliteCardCandidateGroupRepository:
    database = tmp_path / "card-runtime.sqlite3"
    CardBattlerRuntimeSchemaManager(database).prepare_startup()
    return SqliteCardCandidateGroupRepository(database)


def _processor(
    repository: SqliteCardCandidateGroupRepository,
    calls: list[str],
    *,
    source_images: CardSourceImageProvider | None = None,
) -> tuple[InitialCardCandidateGroupProcessor, _Mapper]:
    factory, mapper, _materializer = _factory(
        calls,
        CardPresentationResult(
            None,
            CardPresentationStatus.INFERENCE_FAILED,
        ),
    )
    sources = source_images or cast(CardSourceImageProvider, _SourceImages())

    class _Analyzer:
        def analyze(self, source):
            calls.append("analyze")
            assert source.image_uid == "image-1"
            return _profile()

    return (
        InitialCardCandidateGroupProcessor(
            groups=repository,
            source_images=sources,
            analyzer=cast(SemanticImageAnalyzer, _Analyzer()),
            factory=cast(CardFactory, factory),
        ),
        mapper,
    )


def test_processor_analyzes_and_maps_once_then_persists_four_cards(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    reserved = _service(repository)[0].reserve("image-1")
    calls: list[str] = []
    processor, mapper = _processor(repository, calls)

    assert processor.process_next() is True
    assert processor.process_next() is False

    persisted = repository.get(reserved.group_id)
    assert persisted is not None
    assert persisted.revision == 3
    assert persisted.status is CardCandidateGroupStatus.GENERATING
    assert persisted.semantic_profile == _profile()
    assert persisted.imprint is not None
    assert calls.count("analyze") == 1
    assert calls.count("map") == 1
    assert len(mapper.seeds) == 1
    assert len(persisted.candidates) == 4
    assert all(
        candidate.status is CardCandidateStatus.COMPOSING
        and candidate.artifacts is not None
        for candidate in persisted.candidates
    )
    assert tuple(
        candidate.materialization_seed for candidate in persisted.candidates
    ) == tuple(
        candidate.artifacts.materialization_seed
        for candidate in persisted.candidates
        if candidate.artifacts is not None
    )


def test_processor_persists_failure_without_retrying_mapping(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    reserved = _service(repository)[0].reserve("image-1")
    changed_source = _changed_source()

    class _ChangedSourceImages:
        def load(self, image_uid):
            return changed_source

    calls: list[str] = []
    processor, mapper = _processor(
        repository,
        calls,
        source_images=cast(CardSourceImageProvider, _ChangedSourceImages()),
    )

    assert processor.process_next() is True

    persisted = repository.get(reserved.group_id)
    assert persisted is not None
    assert persisted.status is CardCandidateGroupStatus.FAILED
    assert persisted.failure_category == "ValueError"
    assert all(
        candidate.status is CardCandidateStatus.FAILED
        for candidate in persisted.candidates
    )
    assert calls == []
    assert mapper.seeds == []


def test_restart_recovery_fails_claimed_composition_without_inference(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    reserved = _service(repository)[0].reserve("image-1")
    claimed = repository.claim_next_queued()
    assert claimed is not None
    calls: list[str] = []
    processor, mapper = _processor(repository, calls)

    assert processor.recover_interrupted() == 1
    assert processor.recover_interrupted() == 0

    persisted = repository.get(reserved.group_id)
    assert persisted is not None
    assert persisted.status is CardCandidateGroupStatus.FAILED
    assert persisted.failure_category == "interrupted_composition"
    assert calls == []
    assert mapper.seeds == []
