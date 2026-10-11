"""Behavior tests for canonical Card source bytes and Stage-1 semantics."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import cast

import pytest

from comfyreview.application import (
    CardBattlerModelRepository,
    CardBattlerRulesetRef,
    CardSourceImage,
    LocalModelInstance,
    LocalModelLifecycleError,
    LocalModelRuntime,
    LocalStructuredInferenceRequest,
    LocalStructuredInferenceResult,
    OutputImageReference,
    OutputPair,
    ReviewImage,
    SemanticConceptDefinition,
    SemanticImageAnalysisError,
    SemanticImageAnalyzer,
    SemanticImageProfile,
    SemanticSignal,
)
from comfyreview.providers import CanonicalCardSourceImageProvider


class _ModelRepository:
    ruleset = CardBattlerRulesetRef(
        "prototype", 3, "Prototype", "active", "", "visual", 1
    )

    def resolve_ruleset(self):
        return self.ruleset

    def semantic_concepts(self, ruleset):
        assert ruleset == self.ruleset
        return (
            SemanticConceptDefinition(
                "calm", "Calm", "mood", "Mood", "calm visible energy", ()
            ),
            SemanticConceptDefinition(
                "focused",
                "Focused",
                "mood",
                "Mood",
                "focused visible attention",
                (),
            ),
        )


class _LifecycleProvider:
    def __init__(self, *, fail_cleanup: bool = False) -> None:
        self.fail_cleanup = fail_cleanup
        self.unloaded: list[str] = []

    def list_models(self):
        from comfyreview.application import LocalModelDescriptor

        return (LocalModelDescriptor("vision", ()),)

    def load_model(self, model_id):
        return LocalModelInstance(model_id, "vision-instance")

    def unload_model(self, instance):
        if self.fail_cleanup:
            raise LocalModelLifecycleError("cleanup failed")
        self.unloaded.append(instance.instance_id)


class _StructuredInference:
    def __init__(self, document) -> None:
        self.document = document
        self.requests: list[LocalStructuredInferenceRequest] = []

    def infer_structured(self, request):
        self.requests.append(request)
        return LocalStructuredInferenceResult(
            requested_model_id="vision",
            reported_model_id="vision",
            document=self.document,
        )


def _source_image() -> CardSourceImage:
    content = b"\x89PNG\r\n\x1a\nsemantic-image"
    return CardSourceImage(
        "image-1",
        "image/png",
        content,
        hashlib.sha256(content).hexdigest(),
    )


def _document():
    return {
        "summary": "A focused person in a quiet room.",
        "subjects": ["person"],
        "actions": ["observing"],
        "mood": ["quiet"],
        "environment": ["interior"],
        "objects": ["screen"],
        "signals": [
            {"concept_key": "focused", "strength_milli": 900},
            {"concept_key": "calm", "strength_milli": 650},
        ],
    }


def _analyzer(document, *, fail_cleanup: bool = False):
    lifecycle = _LifecycleProvider(fail_cleanup=fail_cleanup)
    inference = _StructuredInference(document)
    analyzer = SemanticImageAnalyzer(
        model_repository=cast(CardBattlerModelRepository, _ModelRepository()),
        runtime=LocalModelRuntime(lifecycle),
        inference=inference,
        vision_model_id="vision",
    )
    return analyzer, lifecycle, inference


def test_semantic_analyzer_uses_controlled_vocabulary_and_stable_profile() -> (
    None
):
    analyzer, lifecycle, inference = _analyzer(_document())

    first = analyzer.analyze(_source_image())
    second = analyzer.analyze(_source_image())

    assert first == second
    assert first.signals == (
        SemanticSignal("calm", 650),
        SemanticSignal("focused", 900),
    )
    assert first.summary == "A focused person in a quiet room."
    assert first.subjects == ("person",)
    assert first.semantic_revision.startswith("semantic-")
    assert lifecycle.unloaded == ["vision-instance", "vision-instance"]
    request = inference.requests[0]
    assert request.inference.image_data_url is not None
    assert request.inference.image_data_url.startswith(
        "data:image/png;base64,"
    )
    schema = request.schema_document()
    signal_schema = schema["properties"]["signals"]["items"]
    assert signal_schema["properties"]["concept_key"]["enum"] == [
        "calm",
        "focused",
    ]
    assert "game classes" in str(request.inference.system_prompt)


def test_semantic_analyzer_rejects_unknown_or_duplicate_signals() -> None:
    unknown = _document()
    unknown["signals"] = [{"concept_key": "cyberpunk", "strength_milli": 700}]
    analyzer, _, _ = _analyzer(unknown)
    with pytest.raises(SemanticImageAnalysisError, match="signal is invalid"):
        analyzer.analyze(_source_image())

    duplicate = _document()
    duplicate["signals"] = [
        {"concept_key": "calm", "strength_milli": 600},
        {"concept_key": "calm", "strength_milli": 700},
    ]
    analyzer, _, _ = _analyzer(duplicate)
    with pytest.raises(SemanticImageAnalysisError, match="duplicate"):
        analyzer.analyze(_source_image())


def test_cleanup_failure_does_not_replace_successful_semantics() -> None:
    analyzer, _, _ = _analyzer(_document(), fail_cleanup=True)

    profile = analyzer.analyze(_source_image())

    assert profile.image_uid == "image-1"
    with pytest.raises(
        LocalModelLifecycleError, match="Cleanup must be retried"
    ):
        analyzer.analyze(_source_image())


def test_semantic_contract_remains_compatible_and_validates_fact_groups() -> (
    None
):
    legacy = SemanticImageProfile(
        "image", "revision", (SemanticSignal("calm", 500),)
    )
    assert legacy.summary == ""
    with pytest.raises(ValueError, match="subjects contains"):
        SemanticImageProfile(
            "image",
            "revision",
            (),
            subjects=("",),
        )
    with pytest.raises(ValueError, match="hash"):
        CardSourceImage("image", "image/png", b"png", "wrong")


class _Resolver:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.references: list[OutputImageReference] = []

    def resolve(self, reference: OutputImageReference) -> ReviewImage:
        self.references.append(reference)
        return ReviewImage(
            pair=OutputPair(self.path, None),
            model_branch="model",
            checkpoint="checkpoint",
            combo_key="combo",
            steps=None,
            cfg=None,
            sampler=None,
            scheduler=None,
            denoise=None,
            loras_json="[]",
            positive_prompt="",
            negative_prompt="",
            image_uid=reference.image_uid,
            generation_uid="generation",
        )


def test_source_provider_reuses_resolver_and_never_exposes_path(
    tmp_path: Path,
) -> None:
    path = tmp_path / "source.png"
    content = b"\x89PNG\r\n\x1a\nsource"
    path.write_bytes(content)
    resolver = _Resolver(path)

    source = CanonicalCardSourceImageProvider(resolver).load("image-source")

    assert resolver.references == [OutputImageReference("image-source")]
    assert source.image_uid == "image-source"
    assert source.content == content
    assert not hasattr(source, "path")


def test_source_provider_rejects_non_png_after_canonical_resolution(
    tmp_path: Path,
) -> None:
    path = tmp_path / "source.png"
    path.write_bytes(b"not-png")

    with pytest.raises(ValueError, match="not a PNG"):
        CanonicalCardSourceImageProvider(_Resolver(path)).load("image-source")
