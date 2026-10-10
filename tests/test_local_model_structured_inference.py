"""Contract tests for bounded schema-constrained inference values."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from comfyreview.application.local_model_inference import (
    LocalInferenceRequest,
    LocalInferenceUsage,
)
from comfyreview.application.local_model_structured_inference import (
    JsonValue,
    LocalModelStructuredOutputError,
    LocalStructuredInferenceRequest,
    LocalStructuredInferenceResult,
)
from comfyreview.application.local_models import LocalModelProtocolError

_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"facts": {"type": "array", "items": {"type": "string"}}},
    "required": ["facts"],
    "additionalProperties": False,
}


def _inference() -> LocalInferenceRequest:
    return LocalInferenceRequest("local/model", "Extract facts", 64)


def test_request_snapshots_schema_and_hides_its_contents() -> None:
    schema: dict[str, object] = {"type": "object", "properties": {}}
    request = LocalStructuredInferenceRequest(
        _inference(), "extract_facts", schema
    )
    schema["type"] = "array"
    first = request.schema_document()
    first["type"] = "string"
    assert request.schema_document() == {
        "type": "object",
        "properties": {},
    }
    assert "properties" not in repr(request)
    assert "Extract facts" not in repr(request)
    with pytest.raises(FrozenInstanceError):
        setattr(request, str("schema_name"), "different")


def test_schema_accepts_nested_local_references() -> None:
    schema: dict[str, object] = {
        "$defs": {"item": {"type": "string"}},
        "type": "array",
        "items": {"$ref": "#/$defs/item"},
    }
    request = LocalStructuredInferenceRequest(_inference(), "items", schema)
    assert request.schema_document() == schema


@pytest.mark.parametrize("bad", (None, 7, "query", object()))
def test_requires_typed_local_inference_request(bad: object) -> None:
    with pytest.raises(TypeError, match="inference"):
        LocalStructuredInferenceRequest(
            cast(LocalInferenceRequest, bad), "response", _SCHEMA
        )


@pytest.mark.parametrize(
    "bad", ("", " ", "no spaces", "with/slash", "ä", "x" * 65, 7)
)
def test_requires_safe_schema_name(bad: object) -> None:
    with pytest.raises(ValueError, match="schema_name"):
        LocalStructuredInferenceRequest(_inference(), cast(str, bad), _SCHEMA)


@pytest.mark.parametrize("bad", (None, True, [], 5, "{}"))
def test_requires_schema_document_object(bad: object) -> None:
    with pytest.raises(ValueError, match="json_schema"):
        LocalStructuredInferenceRequest(_inference(), "response", cast(dict[str, object], bad))


@pytest.mark.parametrize(
    "bad",
    (
        {"type": "missing"},
        {"type": "object", "required": "no"},
        {"type": 42},
    ),
)
def test_invalid_draft_schema_rejected(bad: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="Draft 2020-12"):
        LocalStructuredInferenceRequest(_inference(), "response", bad)


@pytest.mark.parametrize(
    "bad",
    (
        {"$ref": "https://example.com/schema"},
        {"$ref": 9},
        {"$dynamicRef": "#x"},
        {"$recursiveRef": "#"},
        {"anyOf": [{"$ref": "file:///etc/passwd"}]},
    ),
)
def test_external_or_dynamic_schema_refs_rejected(
    bad: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="json_schema"):
        LocalStructuredInferenceRequest(_inference(), "response", bad)


def test_declared_schema_dialect_must_match_validator() -> None:
    schema: dict[str, object] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
    }
    LocalStructuredInferenceRequest(_inference(), "response", schema)
    with pytest.raises(ValueError, match="Draft 2020-12"):
        LocalStructuredInferenceRequest(
            _inference(),
            "response",
            {"$schema": "http://json-schema.org/draft-07/schema#"},
        )


def test_non_string_schema_keys_rejected() -> None:
    invalid = cast(dict[str, object], {5: {"type": "string"}})
    with pytest.raises(ValueError, match="json_schema"):
        LocalStructuredInferenceRequest(_inference(), "response", invalid)


@pytest.mark.parametrize(
    "bad", ({"const": object()}, {"const": float("nan")}, {"enum": (1, 2)})
)
def test_non_json_schema_values_rejected(bad: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="json_schema"):
        LocalStructuredInferenceRequest(_inference(), "response", bad)


def test_circular_schema_rejected() -> None:
    invalid: dict[str, object] = {}
    invalid["cycle"] = invalid
    with pytest.raises(ValueError, match="json_schema"):
        LocalStructuredInferenceRequest(_inference(), "response", invalid)


def test_oversized_schema_rejected() -> None:
    with pytest.raises(ValueError, match="size limit"):
        LocalStructuredInferenceRequest(
            _inference(), "response", {"description": "x" * 65536}
        )


def test_result_is_typed_immutable_and_defensive() -> None:
    result = LocalStructuredInferenceResult(
        requested_model_id="local/model",
        reported_model_id=None,
        document={"facts": ["truth"]},
        usage=LocalInferenceUsage(20, 8, 0),
    )
    first = cast(dict[str, object], result.value)
    cast(list[str], first["facts"]).append("tampered")
    assert result.value == {"facts": ["truth"]}
    assert result.model_instance_id is None
    assert result.usage == LocalInferenceUsage(20, 8, 0)
    assert "truth" not in repr(result)
    with pytest.raises(FrozenInstanceError):
        setattr(result, str("reported_model_id"), "other")
    assert issubclass(LocalModelStructuredOutputError, LocalModelProtocolError)


@pytest.mark.parametrize("bad", ("", " ", " space ", 5))
def test_result_rejects_invalid_requested_model(bad: object) -> None:
    with pytest.raises(ValueError, match="requested_model_id"):
        LocalStructuredInferenceResult(cast(str, bad), None, document={})


@pytest.mark.parametrize("bad", ("", " ", " space ", 5))
def test_result_rejects_invalid_reported_model(bad: object) -> None:
    with pytest.raises(ValueError, match="reported_model_id"):
        LocalStructuredInferenceResult(
            "local/model", cast(str, bad), document={}
        )


def test_result_rejects_unvalidated_usage() -> None:
    with pytest.raises(ValueError, match="usage"):
        LocalStructuredInferenceResult(
            "local/model",
            None,
            document={},
            usage=cast(LocalInferenceUsage, 2),
        )


@pytest.mark.parametrize(
    "bad", (object(), float("inf"), (1, 2), {1: "bad key"})
)
def test_result_rejects_invalid_json_values(bad: object) -> None:
    with pytest.raises(ValueError, match="document"):
        LocalStructuredInferenceResult(
            "local/model", None, document=cast(JsonValue, bad)
        )
