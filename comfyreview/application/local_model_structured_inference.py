"""Typed contracts for independently validated local structured inference."""

from __future__ import annotations

import json
import re
from dataclasses import InitVar, dataclass, field
from typing import Protocol, TypeAlias, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from comfyreview.application.local_model_inference import (
    LocalInferenceRequest,
    LocalInferenceUsage,
)
from comfyreview.application.local_models import LocalModelProtocolError

JsonValue: TypeAlias = (
    None
    | bool
    | int
    | float
    | str
    | list["JsonValue"]
    | dict[str, "JsonValue"]
)
_MAX_SCHEMA_BYTES = 64 * 1024
_SCHEMA_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


class LocalModelStructuredOutputError(LocalModelProtocolError):
    """Report a JSON response that fails its independently checked schema."""


def _check_json_keys(value: object) -> None:
    """Ensure no JSON object keys are silently coerced into strings."""
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("json_schema keys must be strings")
            _check_json_keys(item)
    elif isinstance(value, list):
        for item in value:
            _check_json_keys(item)
    elif value is not None and type(value) not in (
        bool,
        int,
        float,
        str,
    ):
        raise ValueError("JSON values must use JSON data types")


def _check_schema_references(document: object) -> None:
    """Reject references that would require remote or dynamic resolution."""
    if not isinstance(document, dict):
        return
    for key in ("$dynamicRef", "$recursiveRef"):
        if key in document:
            raise ValueError("json_schema has an unsupported reference")
    if "$ref" in document:
        ref = document["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#"):
            raise ValueError("json_schema has an unsupported reference")
    schema_maps = (
        "$defs",
        "definitions",
        "dependentSchemas",
        "patternProperties",
        "properties",
    )
    schema_arrays = ("allOf", "anyOf", "oneOf", "prefixItems")
    schema_singles = (
        "additionalProperties",
        "contains",
        "contentSchema",
        "else",
        "if",
        "items",
        "not",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
    )
    for key in schema_maps:
        children = document.get(key)
        if isinstance(children, dict):
            for child in children.values():
                _check_schema_references(child)
    for key in schema_arrays:
        children = document.get(key)
        if isinstance(children, list):
            for child in children:
                _check_schema_references(child)
    for key in schema_singles:
        _check_schema_references(document.get(key))


@dataclass(frozen=True, slots=True)
class LocalStructuredInferenceRequest:
    """Bind a validated JSON Schema to a bounded inference request."""

    inference: LocalInferenceRequest
    schema_name: str
    json_schema: InitVar[dict[str, object]] = field(repr=False)
    _schema_json: str = field(init=False, repr=False)

    def __post_init__(self, json_schema: dict[str, object]) -> None:
        if not isinstance(self.inference, LocalInferenceRequest):
            raise TypeError("inference must be LocalInferenceRequest")
        if (
            not isinstance(self.schema_name, str)
            or _SCHEMA_NAME.fullmatch(self.schema_name) is None
        ):
            raise ValueError("schema_name must be a short ASCII identifier")
        if not isinstance(json_schema, dict):
            raise ValueError("json_schema must be a JSON object")
        try:
            _check_json_keys(json_schema)
            _check_schema_references(json_schema)
            serialized = json.dumps(
                json_schema,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError, RecursionError) as error:
            raise ValueError("json_schema must contain valid JSON") from error
        if len(serialized.encode("utf-8")) > _MAX_SCHEMA_BYTES:
            raise ValueError("json_schema exceeds the size limit")
        document = cast(dict[str, object], json.loads(serialized))
        dialect = document.get("$schema")
        if dialect is not None and dialect not in (
            "https://json-schema.org/draft/2020-12/schema",
            "https://json-schema.org/draft/2020-12/schema#",
        ):
            raise ValueError("json_schema must use Draft 2020-12")
        try:
            Draft202012Validator.check_schema(document)
        except SchemaError as error:
            raise ValueError(
                "json_schema is not a valid Draft 2020-12 schema"
            ) from error
        object.__setattr__(self, "_schema_json", serialized)

    def schema_document(self) -> dict[str, object]:
        """Return a fresh transport-ready schema, never caller-owned data."""
        return cast(dict[str, object], json.loads(self._schema_json))


@dataclass(frozen=True, slots=True)
class LocalStructuredInferenceResult:
    """Expose checked JSON without asserting unavailable instance identity."""

    requested_model_id: str
    reported_model_id: str | None
    document: InitVar[JsonValue] = field(repr=False)
    usage: LocalInferenceUsage | None = None
    model_instance_id: None = field(default=None, init=False)
    _document_json: str = field(init=False, repr=False)

    def __post_init__(self, document: JsonValue) -> None:
        if (
            not isinstance(self.requested_model_id, str)
            or not self.requested_model_id
            or self.requested_model_id != self.requested_model_id.strip()
        ):
            raise ValueError("requested_model_id must be an exact identifier")
        if self.reported_model_id is not None and (
            not isinstance(self.reported_model_id, str)
            or not self.reported_model_id
            or self.reported_model_id != self.reported_model_id.strip()
        ):
            raise ValueError("reported_model_id must be an exact identifier")
        if self.usage is not None and not isinstance(
            self.usage, LocalInferenceUsage
        ):
            raise ValueError("usage must be validated token counters")
        try:
            _check_json_keys(document)
            serialized = json.dumps(document, allow_nan=False)
        except (ValueError, TypeError, RecursionError) as error:
            raise ValueError("document must be valid JSON") from error
        object.__setattr__(self, "_document_json", serialized)

    @property
    def value(self) -> JsonValue:
        """Return a defensive copy of the validated JSON value."""
        return cast(JsonValue, json.loads(self._document_json))


class LocalStructuredInferenceProvider(Protocol):
    """Accept schema-constrained local inference without owning models."""

    def infer_structured(
        self, request: LocalStructuredInferenceRequest
    ) -> LocalStructuredInferenceResult:
        """Return independently validated structured data."""
        ...
