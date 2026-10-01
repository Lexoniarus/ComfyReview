"""HTTP contracts for canonical V2 image reads and mutations."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from comfyreview.api.v2_presenters import ImageResponseMapper
from comfyreview.application import (
    ArenaPair,
    ArenaResult,
    CurationResult,
    GenerationSettings,
    ImageClassification,
    ImageContext,
    ImageContextNotFoundError,
    ImagePage,
    ImageScope,
    PromptSnapshot,
    ReviewResult,
    ReviewSummary,
    ScopeFacet,
    ScopeKind,
    WorkflowProvenance,
)
from comfyreview.observability import RequestTracingMiddleware
from routers.api_v2_router import router


class _Files:
    def get_png_path(self, image_uid: str) -> Path | None:
        return Path("output") / f"{image_uid}.png"


class _Urls:
    def to_url(self, png_path: str | Path) -> str:
        return "/files/" + Path(png_path).as_posix()


class _ImageContexts:
    def __init__(self) -> None:
        self.query = None

    def list_images(self, query):
        self.query = query
        return ImagePage((_context(),), 1, query.offset, query.limit)

    def get_image(self, image_uid):
        if image_uid == "missing":
            raise ImageContextNotFoundError("unknown canonical image: missing")
        return _context(image_uid)


class _Facets:
    def __init__(self) -> None:
        self.filters = None

    def list_facets(self, filters):
        self.filters = filters
        return (
            ScopeFacet(
                ScopeKind.CHARACTER,
                "character-a",
                "revision-a",
                "Aiko",
                False,
                12,
            ),
        )


class _Candidates:
    def __init__(self) -> None:
        self.empty = False

    def next_candidate(self, filters):
        return None if self.empty else _context()


class _Reviews:
    command = None

    def submit(self, command):
        self.command = command
        return ReviewResult(1, 7, command.delete)


class _Curation:
    command = None

    def assign(self, command):
        self.command = command
        return CurationResult(
            command.image_uid, Path("image.png"), None, command.set_key
        )


class _Arena:
    command = None

    def next_pair(self, query):
        self.query = query
        return ArenaPair(_context("left"), _context("right"))

    def record_decision(self, command):
        self.command = command
        return ArenaResult("match-1", command.left_image_uid, 10, 4)


def test_v2_scope_and_ranking_reads_use_canonical_query_services() -> None:
    client, container = _client()

    facets = client.get(
        "/api/v2/scopes/facets",
        params=[("scope", "character-a"), ("scope", "character-b")],
    )
    rankings = client.get(
        "/api/v2/rankings",
        params={"mode": "worst", "classification": "classified", "limit": 10},
    )

    assert facets.status_code == 200
    assert facets.json()["facets"][0] == {
        "kind": "character",
        "component_uid": "character-a",
        "revision_uid": "revision-a",
        "name": "Aiko",
        "archived": False,
        "count": 12,
    }
    assert container.scope_facets.filters.scopes.component_uids == (
        "character-a",
        "character-b",
    )
    assert rankings.status_code == 200
    assert rankings.json()["mode"] == "worst"
    assert (
        rankings.json()["items"][0]["image_url"] == "/files/output/image-1.png"
    )
    assert "prompt_snapshot" not in rankings.json()["items"][0]
    assert container.image_contexts.query.filters.minimum_rating_count == 2


def test_v2_image_context_has_url_but_never_exposes_local_path() -> None:
    client, _container = _client()

    response = client.get("/api/v2/images/image-1")

    assert response.status_code == 200
    assert response.json()["image_url"] == "/files/output/image-1.png"
    assert response.json()["prompt_snapshot"]["positive"] == "positive"
    assert "png_path" not in response.text
    assert "json_path" not in response.text


def test_v2_errors_use_stable_envelope_and_request_trace() -> None:
    client, _container = _client()

    missing = client.get(
        "/api/v2/images/missing",
        headers={"X-Request-ID": "frontend-test"},
    )
    invalid = client.get("/api/v2/rankings", params={"mode": "newest"})
    invalid_classification = client.get(
        "/api/v2/scopes/facets", params={"classification": "legacy"}
    )

    assert missing.status_code == 404
    assert missing.json()["error"] == {
        "code": "image_not_found",
        "message": "unknown canonical image: missing",
        "trace_id": "frontend-test",
    }
    assert missing.headers["x-request-id"] == "frontend-test"
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_ranking_query"
    assert invalid_classification.status_code == 400


def test_v2_review_candidate_supports_empty_and_loaded_states() -> None:
    client, container = _client()

    loaded = client.get("/api/v2/review/candidate")
    container.review_candidates.empty = True
    empty = client.get("/api/v2/review/candidate")

    assert loaded.status_code == 200
    assert loaded.json()["image_uid"] == "image-1"
    assert empty.status_code == 204


def test_v2_arena_pair_uses_the_canonical_filtered_pool() -> None:
    client, container = _client()

    response = client.get(
        "/api/v2/arena/pair",
        params=[("scope", "character-a"), ("classification", "classified")],
    )

    assert response.status_code == 200
    assert response.json()["left"]["image_uid"] == "left"
    assert response.json()["right"]["image_uid"] == "right"
    assert container.arena_service.query.images.limit == 100
    assert (
        container.arena_service.query.images.filters.scopes.component_uids
        == ("character-a",)
    )


def test_v2_mutations_submit_only_stable_image_identities() -> None:
    client, container = _client()

    review = client.post(
        "/api/v2/reviews", json={"image_uid": "image-1", "rating": 9}
    )
    delete = client.post("/api/v2/images/image-2/delete")
    curation = client.put(
        "/api/v2/images/image-3/curation", json={"set_key": "favorite"}
    )
    arena = client.post(
        "/api/v2/arena/decisions",
        json={
            "left_image_uid": "image-1",
            "right_image_uid": "image-2",
            "winner_side": "left",
        },
    )

    assert review.status_code == 200
    assert container.review_service.command.image.image_uid == "image-2"
    assert container.review_service.command.delete is True
    assert delete.json()["deleted"] is True
    assert curation.status_code == 200
    assert container.curation_service.command.image_uid == "image-3"
    assert arena.status_code == 200
    assert container.arena_service.command.right_image_uid == "image-2"


def _client() -> tuple[TestClient, SimpleNamespace]:
    container = SimpleNamespace(
        settings=SimpleNamespace(minimum_runs=2, pool_limit=128),
        image_contexts=_ImageContexts(),
        scope_facets=_Facets(),
        review_candidates=_Candidates(),
        image_responses=ImageResponseMapper(files=_Files(), urls=_Urls()),
        review_service=_Reviews(),
        curation_service=_Curation(),
        arena_service=_Arena(),
    )
    application = FastAPI()
    application.state.container = container
    application.add_middleware(RequestTracingMiddleware)
    application.include_router(router)
    return TestClient(application), container


def _context(image_uid: str = "image-1") -> ImageContext:
    return ImageContext(
        image_uid=image_uid,
        generation_uid="generation-1",
        classification=ImageClassification.CLASSIFIED,
        scopes=(
            ImageScope(
                ScopeKind.CHARACTER, "character-a", "revision-a", "Aiko", 0
            ),
        ),
        prompt_snapshot=PromptSnapshot("positive", "negative", False),
        generation_settings=GenerationSettings(
            "anime", "checkpoint", 1, 20, 7.0, "euler", "normal", 1.0
        ),
        workflow=WorkflowProvenance("default-character", 1, "graph-hash"),
        output_role="primary",
        output_index=0,
        review=ReviewSummary(9, 2, 8.5),
        curation=None,
    )
