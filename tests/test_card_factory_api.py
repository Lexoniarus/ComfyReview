"""HTTP contracts for the revision-safe Card Factory prototype API."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from comfyreview.application import (
    CardFactorySessionSnapshot,
    CardSessionConflictError,
    CardSourceEligibilityError,
    ContentLevel,
    ImageContextNotFoundError,
    LocalModelConnectionError,
    LocalModelProtocolError,
)
from routers.api_v2.card_factory import router
from tests.test_card_battler_evolution import _session


class _Prototype:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def create(self, image_uid):
        self.calls.append(("create", image_uid))
        return CardFactorySessionSnapshot(_session(), ())

    def get(self, session_id):
        self.calls.append(("get", session_id))
        return CardFactorySessionSnapshot(_session(), ())

    def develop(self, session_id, *, expected_revision):
        self.calls.append(("develop", session_id, expected_revision))
        return CardFactorySessionSnapshot(_session(), ())

    def generate_candidates(self, session_id, *, expected_revision):
        self.calls.append(("generate", session_id, expected_revision))
        return CardFactorySessionSnapshot(_session(), ())

    def accept_candidate(self, session_id, candidate_id, *, expected_revision):
        self.calls.append(
            ("accept", session_id, candidate_id, expected_revision)
        )
        return CardFactorySessionSnapshot(_session(), ())


class _Runtime:
    def __init__(self, prototype) -> None:
        self.services = SimpleNamespace(
            prototype=prototype,
            outputs=SimpleNamespace(output_by_image_uid=lambda _uid: None),
        )

    def get(self):
        return self.services


class _ImageContexts:
    def __init__(self) -> None:
        self.query = None

    def list_images(self, query):
        self.query = query
        return SimpleNamespace(
            entries=(SimpleNamespace(image_uid="image-1"),),
            total=1,
            offset=query.offset,
            limit=query.limit,
        )


class _ImageResponses:
    def summary(self, image):
        return {"image_uid": image.image_uid}

    def image_url(self, image_uid):
        return f"/files/{image_uid}.png"


class _FileUrls:
    def to_url(self, path: Path) -> str:
        return "/files/" + path.name


def _client(prototype) -> tuple[TestClient, SimpleNamespace]:
    image_contexts = _ImageContexts()
    container = SimpleNamespace(
        card_factory_runtime=_Runtime(prototype),
        image_contexts=image_contexts,
        image_responses=_ImageResponses(),
        file_urls=_FileUrls(),
    )
    application = FastAPI()
    application.state.container = container
    application.include_router(router, prefix="/api/v2")
    return TestClient(application), container


def test_card_source_api_applies_server_side_standard_filter() -> None:
    client, container = _client(_Prototype())

    response = client.get("/api/v2/card-factory/sources?offset=0&limit=12")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"image_uid": "image-1", "image_url": "/files/image-1.png"}
    ]
    assert (
        container.image_contexts.query.filters.effective_content_level
        is ContentLevel.STANDARD
    )


def test_card_session_api_delegates_all_revision_safe_commands() -> None:
    prototype = _Prototype()
    client, _ = _client(prototype)

    created = client.post(
        "/api/v2/card-factory/sessions",
        json={"image_uid": "image-1"},
    )
    loaded = client.get("/api/v2/card-factory/sessions/session-1")
    developed = client.post(
        "/api/v2/card-factory/sessions/session-1/develop",
        json={"expected_revision": 1},
    )
    generated = client.post(
        "/api/v2/card-factory/sessions/session-1/candidates",
        json={"expected_revision": 2},
    )
    accepted = client.post(
        "/api/v2/card-factory/sessions/session-1/"
        "candidates/candidate-2/accept",
        json={"expected_revision": 3},
    )

    assert [
        created.status_code,
        loaded.status_code,
        developed.status_code,
        generated.status_code,
        accepted.status_code,
    ] == [201, 200, 200, 202, 200]
    assert created.json()["semantic_profile"]["image_uid"] == "image-1"
    assert created.json()["imprint"]["world_style"] == "near_future"
    assert created.json()["card_spec"]["stats"]["attack"] == 100
    assert created.json()["actions"] == {
        "can_generate": True,
        "can_develop": False,
    }
    assert prototype.calls == [
        ("create", "image-1"),
        ("get", "session-1"),
        ("develop", "session-1", 1),
        ("generate", "session-1", 2),
        ("accept", "session-1", "candidate-2", 3),
    ]


def test_card_session_api_maps_stale_mutation_to_conflict() -> None:
    class _ConflictPrototype(_Prototype):
        def develop(self, session_id, *, expected_revision):
            del session_id, expected_revision
            raise CardSessionConflictError("stale")

    client, _ = _client(_ConflictPrototype())

    response = client.post(
        "/api/v2/card-factory/sessions/session-1/develop",
        json={"expected_revision": 1},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "card_development_conflict"


@pytest.mark.parametrize(
    ("failure", "status_code", "code"),
    (
        (
            ImageContextNotFoundError("missing"),
            404,
            "card_source_not_found",
        ),
        (
            CardSourceEligibilityError("content_level"),
            422,
            "card_source_ineligible",
        ),
        (
            LocalModelConnectionError("offline"),
            503,
            "local_model_unavailable",
        ),
        (
            LocalModelProtocolError("invalid output"),
            502,
            "semantic_analysis_failed",
        ),
    ),
)
def test_card_create_api_normalizes_source_and_model_failures(
    failure: Exception,
    status_code: int,
    code: str,
) -> None:
    class _FailedPrototype(_Prototype):
        def create(self, image_uid):
            del image_uid
            raise failure

    client, _ = _client(_FailedPrototype())

    response = client.post(
        "/api/v2/card-factory/sessions",
        json={"image_uid": "image-1"},
    )

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code
