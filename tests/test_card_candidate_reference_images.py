"""Provider tests for Candidate-group reference-image resolution."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from comfyreview.application.card_battler_semantics import (
    CardSourceImage,
    CardSourceImageProvider,
)
from comfyreview.application.generation_outputs import GenerationOutput
from comfyreview.providers.card_reference_images import (
    CanonicalCardCandidateReferenceImageProvider,
    CardRuntimeOutputQuery,
)
from tests.test_card_candidate_group_reservation import _Groups, _service


class _CanonicalSources:
    def __init__(self, image: CardSourceImage) -> None:
        self.image = image
        self.calls: list[str] = []

    def load(self, image_uid: str) -> CardSourceImage:
        self.calls.append(image_uid)
        return self.image


class _CardOutputs:
    def __init__(self, output: GenerationOutput | None) -> None:
        self.output = output
        self.calls: list[str] = []

    def output_by_image_uid(self, image_uid: str) -> GenerationOutput | None:
        self.calls.append(image_uid)
        return self.output


def _group():
    groups = _Groups()
    return _service(groups)[0].reserve("image-1")


def test_candidate_reference_provider_uses_canonical_source_for_initial_group() -> (
    None
):
    group = _group()
    content = b"canonical source"
    source = CardSourceImage(
        group.source_image_uid,
        "image/png",
        content,
        hashlib.sha256(content).hexdigest(),
    )
    group = replace(
        group,
        source_content_hash=source.content_hash,
        reference_content_hash=source.content_hash,
    )
    canonical = _CanonicalSources(source)
    outputs = _CardOutputs(None)
    provider = CanonicalCardCandidateReferenceImageProvider(
        cast(CardSourceImageProvider, canonical),
        cast(CardRuntimeOutputQuery, outputs),
    )

    assert provider.load(group) == source
    assert canonical.calls == [group.source_image_uid]
    assert outputs.calls == []


def test_candidate_reference_provider_uses_runtime_output_for_development(
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
    group = replace(
        _group(),
        reference_image_uid=output.image_uid,
        reference_content_hash=content_hash,
    )
    unused_content = b"unused"
    canonical = _CanonicalSources(
        CardSourceImage(
            "image-1",
            "image/png",
            unused_content,
            hashlib.sha256(unused_content).hexdigest(),
        )
    )
    outputs = _CardOutputs(output)
    provider = CanonicalCardCandidateReferenceImageProvider(
        cast(CardSourceImageProvider, canonical),
        cast(CardRuntimeOutputQuery, outputs),
    )

    loaded = provider.load(group)

    assert loaded.image_uid == "accepted-image"
    assert loaded.content == b"accepted candidate"
    assert loaded.content_hash == content_hash
    assert canonical.calls == []
    assert outputs.calls == ["accepted-image"]

    changed = replace(group, reference_content_hash="changed")
    with pytest.raises(ValueError, match="hash no longer matches"):
        provider.load(changed)
