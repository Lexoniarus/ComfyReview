"""HTTP contracts for canonical V2 image reads and mutations."""

from __future__ import annotations

from dataclasses import replace
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
    GenerationSubmission,
    ImageClassification,
    ImageContext,
    ImageContextNotFoundError,
    ImagePage,
    ImageScope,
    PlaygroundDraft,
    PlaygroundSubmissionBatch,
    PlaygroundSubmissionFailure,
    PromptComponent,
    PromptRevision,
    PromptSelection,
    PromptSnapshot,
    RenderedPrompt,
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


def _prompt_component(
    uid: str = "character-a",
    kind: str = "character",
) -> PromptComponent:
    return PromptComponent(
        component_uid=uid,
        kind=kind,
        component_key=f"{uid}-key",
        name="Aiko" if kind == "character" else uid,
        tags=("anime",),
        notes="note",
        archived=False,
        latest_revision=PromptRevision(
            f"revision-{uid}", 1, f"positive {uid}", "negative", "hash"
        ),
    )


class _PromptCatalog:
    def __init__(self) -> None:
        self.component = _prompt_component()

    def list_components(self, *, include_archived=False):
        return (
            self.component,
            _prompt_component("scene-a", "scene"),
        )

    def get_component(self, component_uid):
        if component_uid == "missing":
            raise KeyError("missing")
        if component_uid == self.component.component_uid:
            return self.component
        return _prompt_component(component_uid)

    def list_revisions(self, component_uid):
        component = self.get_component(component_uid)
        return (component.latest_revision,)

    def create_component(self, command):
        self.component = _prompt_component("created", command.kind)
        return replace(
            self.component,
            name=command.name,
            tags=command.tags,
            notes=command.notes,
        )

    def update_component(self, command):
        self.component = replace(
            self.get_component(command.component_uid),
            name=command.name,
            tags=command.tags,
            notes=command.notes,
            latest_revision=PromptRevision(
                "revision-updated",
                2,
                command.positive_text,
                command.negative_text,
                "updated-hash",
            ),
        )
        return self.component

    def set_archived(self, component_uid, *, archived):
        self.component = replace(
            self.get_component(component_uid), archived=archived
        )
        return self.component


class _Playground:
    command = None
    confirm_command = None
    overrides = None

    def prepare_draft(self, command, *, overrides=None):
        self.command = command
        self.overrides = overrides
        return PlaygroundDraft(
            PromptSelection(
                (_prompt_component(), _prompt_component("scene-a", "scene"))
            ),
            RenderedPrompt(
                overrides.positive_text
                if overrides and overrides.positive_text is not None
                else "rendered positive",
                "rendered negative",
                "notes",
                ("revision-character-a", "revision-scene-a"),
                overrides is not None,
            ),
        )

    def confirm_draft(self, command):
        self.confirm_command = command
        if "missing" in command.component_uids:
            raise KeyError("missing")
        return PlaygroundDraft(
            PromptSelection(
                (_prompt_component(), _prompt_component("scene-a", "scene"))
            ),
            RenderedPrompt(
                command.positive_prompt,
                command.negative_prompt,
                "notes",
                ("revision-character-a", "revision-scene-a"),
                command.positive_prompt != "rendered positive",
            ),
        )


class _PlaygroundSubmission:
    draft = None
    fail = False

    def submit(self, drafts):
        self.draft = drafts[0]
        if self.fail:
            return PlaygroundSubmissionBatch(
                (), (PlaygroundSubmissionFailure("draft-1", "submit failed"),)
            )
        return PlaygroundSubmissionBatch(
            (GenerationSubmission("generation-1", "submitted", "prompt-1"),),
            (),
        )


class _GenerationQueries:
    def list_generations(self, *, status, offset, limit):
        if status == "invalid":
            from comfyreview.application import GenerationQueryValidationError

            raise GenerationQueryValidationError("unknown generation status")
        summary = _generation_summary()
        return SimpleNamespace(
            entries=(summary,), total=1, offset=offset, limit=limit
        )

    def get_generation(self, generation_uid):
        if generation_uid == "missing":
            from comfyreview.application import GenerationNotFoundError

            raise GenerationNotFoundError("missing")
        return SimpleNamespace(
            summary=_generation_summary(),
            positive_prompt="positive",
            negative_prompt="negative",
            revision_uids=("revision-character-a",),
            sampler_stages=(
                SimpleNamespace(
                    role="base_sampler",
                    node_id="12",
                    order=0,
                    seed=1,
                    steps=20,
                    cfg=7.0,
                    sampler="euler",
                    scheduler="normal",
                    denoise=1.0,
                ),
            ),
            outputs=(
                SimpleNamespace(
                    image_uid="image-1",
                    role="primary",
                    node_id="42",
                    output_index=0,
                    content_hash="hash",
                ),
            ),
        )


class _GenerationReconciliation:
    def __init__(self) -> None:
        self.arguments: tuple[str, str | None] | None = None

    def reconcile(self, generation_uid, *, prompt_id=None):
        self.arguments = (generation_uid, prompt_id)
        return GenerationSubmission(generation_uid, "running", prompt_id)


def _generation_summary():
    return SimpleNamespace(
        generation_uid="generation-1",
        status="completed",
        prompt_id="prompt-1",
        source="native_comfyui",
        model="anime",
        checkpoint="model.safetensors",
        blueprint_uid="default-character",
        blueprint_version=1,
        graph_hash="graph-hash",
        created_at="2026-01-01 00:00:00",
        submitted_at=None,
        started_at=None,
        completed_at="2026-01-01 00:01:00",
        output_count=1,
    )


class _PlaygroundDiscovery:
    def discover(self):
        return SimpleNamespace(
            checkpoints=["model.safetensors"],
            samplers=["euler"],
            schedulers=["normal"],
        )


class _WorkflowDefaults:
    def load(self, blueprint_uid, version):
        assert (blueprint_uid, version) == ("default-character", 1)
        return SimpleNamespace(
            checkpoint="model.safetensors",
            sampler=SimpleNamespace(
                steps=24,
                cfg=6.5,
                sampler="euler",
                scheduler="normal",
                denoise=1.0,
            ),
        )


class _AnalyticsPages:
    def __init__(self) -> None:
        self.call: tuple[str, dict[str, object]] | None = None

    def recommendations_context(self, **values):
        self.call = ("overview", values)
        return {
            "stable": [{"label": "stable"}],
            "avoid": [],
            "approx": {"rows": []},
            "model_list": ["anime"],
        }

    def prompt_tokens_context(self, **values):
        self.call = ("scopes", values)
        return {
            "rows": [
                {"token": "hero", "n": 4, "mean_score": 8.5, "lb05": 7.25}
            ],
            "model_list": ["anime"],
        }

    def parameter_context(self, **values):
        self.call = ("parameters", values)
        return {
            "stats": [{"key": "steps", "title": "Steps", "rows": []}],
            "best": [],
            "best_tested": [],
            "model_list": ["anime"],
        }

    def stats_context(self, **values):
        self.call = ("combinations", values)
        return {"rows": [{"combo_key": "a|b"}], "model_list": ["anime"]}


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


def test_v2_curation_sets_come_from_typed_application_settings() -> None:
    client, _container = _client()

    response = client.get("/api/v2/curation/sets")

    assert response.status_code == 200
    assert response.json() == {
        "set_keys": ["character_face", "outfit", "pose"]
    }


def test_v2_playground_reads_catalog_and_native_capabilities() -> None:
    client, _container = _client()

    catalog = client.get("/api/v2/catalog/components")
    capabilities = client.get("/api/v2/playground/capabilities")

    assert catalog.status_code == 200
    assert catalog.json()["components"][0]["component_uid"] == "character-a"
    assert catalog.json()["components"][0]["latest_revision"] == {
        "revision_uid": "revision-character-a",
        "revision_number": 1,
        "positive_text": "positive character-a",
        "negative_text": "negative",
    }
    assert capabilities.json() == {
        "checkpoints": ["model.safetensors"],
        "samplers": ["euler"],
        "schedulers": ["normal"],
        "defaults": {
            "checkpoint": "model.safetensors",
            "seed": 1,
            "steps": 24,
            "cfg": 6.5,
            "sampler": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
        },
    }


def test_v2_catalog_reads_revision_history_and_mutates_without_deleting() -> (
    None
):
    client, _container = _client()

    detail = client.get("/api/v2/catalog/components/character-a")
    revisions = client.get("/api/v2/catalog/components/character-a/revisions")
    created = client.post(
        "/api/v2/catalog/components",
        json={
            "kind": "scene",
            "name": "Rainy street",
            "tags": ["rain"],
            "notes": "note",
            "positive_text": "rainy street",
            "negative_text": "sun",
        },
    )
    updated = client.put(
        "/api/v2/catalog/components/created",
        json={
            "kind": "scene",
            "name": "Rainy street night",
            "tags": ["rain", "night"],
            "positive_text": "rainy street at night",
            "negative_text": "sun",
        },
    )
    archived = client.patch(
        "/api/v2/catalog/components/created", json={"archived": True}
    )

    assert detail.status_code == 200
    assert revisions.json()["revisions"][0]["revision_uid"] == (
        "revision-character-a"
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Rainy street"
    assert updated.json()["latest_revision"]["revision_number"] == 2
    assert archived.json()["archived"] is True


def test_v2_catalog_rejects_missing_components_and_kind_changes() -> None:
    client, _container = _client()
    payload = {
        "kind": "scene",
        "name": "Scene",
        "positive_text": "scene",
    }

    missing = client.get("/api/v2/catalog/components/missing")
    missing_revisions = client.get(
        "/api/v2/catalog/components/missing/revisions"
    )
    invalid_kind = client.put(
        "/api/v2/catalog/components/character-a", json=payload
    )

    assert missing.status_code == 404
    assert missing_revisions.status_code == 404
    assert invalid_kind.status_code == 400
    assert invalid_kind.json()["error"]["code"] == (
        "invalid_catalog_component"
    )


def test_v2_playground_draft_preserves_modes_and_overrides() -> None:
    client, container = _client()
    selections = [
        {"kind": "character", "mode": "fixed", "component_uid": "character-a"},
        {"kind": "scene", "mode": "fixed", "component_uid": "scene-a"},
        {"kind": "outfit", "mode": "random"},
        {"kind": "pose", "mode": "off"},
        {"kind": "expression", "mode": "random"},
        {"kind": "lighting", "mode": "off"},
        {"kind": "modifier", "mode": "random"},
    ]

    response = client.post(
        "/api/v2/playground/drafts",
        json={
            "selections": selections,
            "seed": 17,
            "positive_override": "draft positive",
        },
    )

    assert response.status_code == 200
    assert response.json()["positive_prompt"] == "draft positive"
    assert response.json()["revision_uids"] == [
        "revision-character-a",
        "revision-scene-a",
    ]
    assert container.playground_service.command.character_component_uid == (
        "character-a"
    )
    assert container.playground_service.command.disabled_kinds == (
        "pose",
        "lighting",
    )


def test_v2_playground_rejects_incomplete_or_disabled_character_intent() -> (
    None
):
    client, _container = _client()

    incomplete = client.post(
        "/api/v2/playground/drafts",
        json={"selections": [{"kind": "character", "mode": "random"}]},
    )
    selections = [
        {"kind": kind, "mode": "off"}
        for kind in (
            "character",
            "scene",
            "outfit",
            "pose",
            "expression",
            "lighting",
            "modifier",
        )
    ]
    disabled = client.post(
        "/api/v2/playground/drafts", json={"selections": selections}
    )

    assert incomplete.status_code == 400
    assert incomplete.json()["error"]["code"] == (
        "invalid_playground_selection"
    )
    assert disabled.status_code == 400


def test_v2_generation_submission_uses_reviewed_snapshot_and_stable_revisions() -> (
    None
):
    client, container = _client()
    payload = {
        "draft_uid": "draft-1",
        "component_uids": ["character-a", "scene-a"],
        "positive_prompt": "edited positive",
        "negative_prompt": "edited negative",
        "checkpoint": "model.safetensors",
        "sampler": {
            "seed": 42,
            "steps": 24,
            "cfg": 6.5,
            "sampler": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
        },
    }

    response = client.post("/api/v2/generations", json=payload)

    assert response.status_code == 202
    assert response.json() == {
        "generation_uid": "generation-1",
        "status": "submitted",
        "prompt_id": "prompt-1",
    }
    draft = container.playground_submission_service.draft
    assert draft.prompt.positive_text == "edited positive"
    assert draft.prompt.revision_uids == (
        "revision-character-a",
        "revision-scene-a",
    )
    assert draft.output_subdirectory == "playground/character-a-key"
    assert container.playground_service.confirm_command.component_uids == (
        "character-a",
        "scene-a",
    )


def test_v2_generation_submission_surfaces_validation_and_submit_failures() -> (
    None
):
    client, container = _client()
    payload = {
        "draft_uid": "draft-1",
        "component_uids": ["missing"],
        "positive_prompt": "positive",
        "negative_prompt": "negative",
        "checkpoint": "model.safetensors",
        "sampler": {
            "seed": 42,
            "steps": 24,
            "cfg": 6.5,
            "sampler": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
        },
    }

    invalid = client.post("/api/v2/generations", json=payload)
    payload["component_uids"] = ["character-a", "scene-a"]
    container.playground_submission_service.fail = True
    failed = client.post("/api/v2/generations", json=payload)

    graph_payload = dict(payload)
    graph_payload["workflow_graph"] = {"42": {"class_type": "SaveImage"}}
    graph = client.post("/api/v2/generations", json=graph_payload)

    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_generation"
    assert failed.status_code == 500
    assert failed.json()["error"]["code"] == "generation_failed"
    assert graph.status_code == 422


def test_v2_generation_reads_expose_lifecycle_outputs_and_urls() -> None:
    client, _container = _client()

    listing = client.get("/api/v2/generations", params={"status": "completed"})
    detail = client.get("/api/v2/generations/generation-1")
    missing = client.get("/api/v2/generations/missing")
    invalid = client.get("/api/v2/generations", params={"status": "invalid"})

    assert listing.status_code == 200
    assert listing.json()["items"][0]["status"] == "completed"
    assert detail.status_code == 200
    assert detail.json()["outputs"][0] == {
        "image_uid": "image-1",
        "role": "primary",
        "node_id": "42",
        "output_index": 0,
        "content_hash": "hash",
        "image_url": "/files/output/image-1.png",
    }
    assert missing.status_code == 404
    assert invalid.status_code == 400


def test_v2_generation_reconcile_uses_existing_lifecycle_service() -> None:
    client, container = _client()

    response = client.post(
        "/api/v2/generations/generation-1/reconcile",
        json={"prompt_id": "prompt-recovered"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert container.generation_reconciliation.arguments == (
        "generation-1",
        "prompt-recovered",
    )


def test_v2_analytics_endpoints_delegate_all_calculation_to_server_services() -> (
    None
):
    client, container = _client()

    overview = client.get(
        "/api/v2/analytics/overview", params={"model": "anime"}
    )
    scopes = client.get("/api/v2/analytics/scopes", params={"scope": "neg"})
    parameters = client.get("/api/v2/analytics/parameters")
    combinations = client.get(
        "/api/v2/analytics/combinations", params={"min_n": 2}
    )

    assert overview.json()["stable"] == [{"label": "stable"}]
    assert scopes.json()["rows"][0]["token"] == "hero"
    assert parameters.json()["stats"][0]["key"] == "steps"
    assert combinations.json()["rows"][0]["combo_key"] == "a|b"
    assert container.analytics_pages.call == (
        "combinations",
        {
            "model": "",
            "min_n": 2,
            "limit": 200,
            "success_threshold": 4,
            "delete_weight": 5,
        },
    )


def _client() -> tuple[TestClient, SimpleNamespace]:
    container = SimpleNamespace(
        settings=SimpleNamespace(
            minimum_runs=2,
            pool_limit=128,
            curation_set_keys=("character_face", "outfit", "pose"),
        ),
        image_contexts=_ImageContexts(),
        scope_facets=_Facets(),
        review_candidates=_Candidates(),
        image_responses=ImageResponseMapper(files=_Files(), urls=_Urls()),
        review_service=_Reviews(),
        curation_service=_Curation(),
        arena_service=_Arena(),
        prompt_catalog_service=_PromptCatalog(),
        playground_service=_Playground(),
        playground_submission_service=_PlaygroundSubmission(),
        generation_queries=_GenerationQueries(),
        generation_reconciliation=_GenerationReconciliation(),
        playground_discovery=_PlaygroundDiscovery(),
        workflow_defaults=_WorkflowDefaults(),
        analytics_pages=_AnalyticsPages(),
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
        prompt_evidence=None,
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
