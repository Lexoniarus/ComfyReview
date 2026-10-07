"""Behavior tests for canonical Playground Generator state."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from comfyreview.application import (
    GeneratorStateService,
    GeneratorStateSnapshot,
    GeneratorStateValidationError,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteGeneratorStateRepository,
)


def _payload() -> dict[str, object]:
    return {
        "selections": [
            {
                "kind": "character",
                "mode": "fixed",
                "component_uid": "character-a",
                "revision_uid": "revision-a",
            },
            {
                "kind": "scene",
                "mode": "random",
                "component_uid": None,
                "revision_uid": None,
            },
        ],
        "loras": [
            {
                "lora_uid": "lora-a",
                "revision_uid": "lora-revision-a",
                "model_strength": 0.8,
                "clip_strength": 0.65,
            }
        ],
        "checkpoint": "model.safetensors",
        "sampler": "euler",
        "scheduler": "normal",
        "seed_mode": "fixed",
        "seed": 37,
        "steps_min": 24,
        "steps_max": 32,
        "cfg_min": 6.5,
        "cfg_max": 7.25,
        "cfg_step": 0.25,
        "denoise": 0.9,
        "batch_runs": 2,
        "aspect_format": "2:3",
        "resolution_class": "1080",
    }


def _repository(tmp_path: Path) -> SqliteGeneratorStateRepository:
    database_path = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    with sqlite3.connect(database_path) as connection:
        component_id = connection.execute(
            """
            INSERT INTO prompt_components(
                component_uid, kind, component_key, name
            ) VALUES ('character-a', 'character', 'character_a', 'A')
            """
        ).lastrowid
        connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash
            ) VALUES ('revision-a', ?, 1, 'hero', '', 'prompt-hash')
            """,
            (component_id,),
        )
        definition_id = connection.execute(
            """
            INSERT INTO lora_definitions(
                lora_uid, provider_name, display_name, content_level
            ) VALUES ('lora-a', 'style.safetensors', 'Style', 'standard')
            """
        ).lastrowid
        connection.execute(
            """
            INSERT INTO lora_revisions(
                revision_uid, lora_definition_id, revision_number,
                default_model_strength_milli,
                default_clip_strength_milli, content_hash
            ) VALUES ('lora-revision-a', ?, 1, 1000, 1000, 'lora-hash')
            """,
            (definition_id,),
        )
        connection.commit()
    return SqliteGeneratorStateRepository(database_path)


def test_generator_state_round_trips_normalized_catalog_references(
    tmp_path: Path,
) -> None:
    service = GeneratorStateService(_repository(tmp_path))

    assert service.load() == {}
    saved = service.save(_payload())

    assert saved == _payload()
    assert service.load() == _payload()


def test_generator_state_rejects_unstable_ids_and_rolls_back(
    tmp_path: Path,
) -> None:
    service = GeneratorStateService(_repository(tmp_path))
    original = service.save(_payload())
    invalid = _payload()
    invalid["loras"] = [
        {
            "lora_uid": "lora-a",
            "revision_uid": "missing-revision",
            "model_strength": 0.5,
            "clip_strength": 0.5,
        }
    ]

    with pytest.raises(GeneratorStateValidationError, match="unknown LoRA"):
        service.save(invalid)

    assert service.load() == original


def test_generator_state_snapshot_validates_complete_fixed_references() -> (
    None
):
    payload = _payload()
    payload["selections"] = [
        {
            "kind": "character",
            "mode": "fixed",
            "component_uid": "character-a",
            "revision_uid": None,
        }
    ]

    with pytest.raises(GeneratorStateValidationError, match="stable"):
        GeneratorStateSnapshot.from_mapping(payload)


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (lambda value: value.update({"unknown": True}), "unknown"),
        (lambda value: value.pop("checkpoint"), "missing"),
        (lambda value: value.update({"selections": "bad"}), "selections"),
        (lambda value: value.update({"loras": "bad"}), "loras"),
        (lambda value: value.update({"selections": [1]}), "selection must"),
        (
            lambda value: value.update(
                {
                    "selections": [
                        {
                            "kind": "scene",
                            "mode": "off",
                            "component_uid": None,
                            "revision_uid": None,
                            "legacy": True,
                        }
                    ]
                }
            ),
            "selection unknown",
        ),
        (
            lambda value: value.update(
                {"selections": [{"kind": "scene", "mode": "off"}]}
            ),
            "selection missing",
        ),
        (
            lambda value: value.update(
                {
                    "selections": [
                        {
                            "kind": "unknown",
                            "mode": "off",
                            "component_uid": None,
                            "revision_uid": None,
                        }
                    ]
                }
            ),
            "unknown selection kind",
        ),
        (
            lambda value: value.update(
                {
                    "selections": [
                        {
                            "kind": "scene",
                            "mode": "off",
                            "component_uid": None,
                            "revision_uid": None,
                        },
                        {
                            "kind": "scene",
                            "mode": "random",
                            "component_uid": None,
                            "revision_uid": None,
                        },
                    ]
                }
            ),
            "duplicate selection kind",
        ),
        (
            lambda value: value.update(
                {
                    "selections": [
                        {
                            "kind": "scene",
                            "mode": "bad",
                            "component_uid": None,
                            "revision_uid": None,
                        }
                    ]
                }
            ),
            "unknown selection mode",
        ),
        (
            lambda value: value.update(
                {
                    "selections": [
                        {
                            "kind": "scene",
                            "mode": "off",
                            "component_uid": "scene-a",
                            "revision_uid": None,
                        }
                    ]
                }
            ),
            "cannot reference",
        ),
        (lambda value: value.update({"loras": [1]}), "LoRA must"),
        (
            lambda value: value.update(
                {
                    "loras": [
                        {
                            "lora_uid": "lora-a",
                            "revision_uid": "lora-revision-a",
                            "model_strength": 1,
                            "clip_strength": 1,
                            "legacy": True,
                        }
                    ]
                }
            ),
            "LoRA unknown",
        ),
        (
            lambda value: value.update(
                {
                    "loras": [
                        {
                            "lora_uid": "lora-a",
                            "revision_uid": "lora-revision-a",
                            "model_strength": 1,
                            "clip_strength": 1,
                        },
                        {
                            "lora_uid": "lora-a",
                            "revision_uid": "lora-revision-a",
                            "model_strength": 1,
                            "clip_strength": 1,
                        },
                    ]
                }
            ),
            "duplicate LoRA",
        ),
        (lambda value: value.update({"checkpoint": ""}), "checkpoint"),
        (lambda value: value.update({"seed_mode": "bad"}), "seed mode"),
        (lambda value: value.update({"seed": True}), "seed must"),
        (lambda value: value.update({"seed": object()}), "seed must"),
        (lambda value: value.update({"seed": "bad"}), "seed must"),
        (lambda value: value.update({"seed": 1.5}), "seed must"),
        (lambda value: value.update({"batch_runs": 0}), "batch_runs"),
        (lambda value: value.update({"cfg_min": True}), "cfg_min"),
        (lambda value: value.update({"cfg_min": "bad"}), "cfg_min"),
        (lambda value: value.update({"cfg_min": float("inf")}), "finite"),
        (lambda value: value.update({"cfg_step": 0}), "cfg_step"),
        (lambda value: value.update({"steps_max": 101}), "exceed 100"),
        (lambda value: value.update({"steps_min": 33}), "steps_min"),
        (lambda value: value.update({"cfg_max": 31}), "exceed 30"),
        (lambda value: value.update({"cfg_min": 8}), "cfg_min"),
        (lambda value: value.update({"denoise": 1.1}), "denoise"),
        (lambda value: value.update({"aspect_format": "bad"}), "aspect"),
        (
            lambda value: value.update({"resolution_class": "bad"}),
            "resolution",
        ),
    ),
)
def test_generator_state_snapshot_rejects_invalid_boundary_values(
    mutate: Callable[[dict[str, object]], object],
    message: str,
) -> None:
    payload = _payload()
    mutate(payload)

    with pytest.raises(GeneratorStateValidationError, match=message):
        GeneratorStateSnapshot.from_mapping(payload)
