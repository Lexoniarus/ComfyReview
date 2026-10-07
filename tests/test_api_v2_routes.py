"""HTTP contracts for canonical V2 image reads and mutations."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from comfyreview.api.v2_presenters import ImageResponseMapper
from comfyreview.application import (
    ArenaPair,
    ArenaResult,
    CatalogEvidenceImage,
    ContentClassificationError,
    ContentLevel,
    CurationResult,
    EvidenceScore,
    GenerationSettings,
    GenerationSubmission,
    GeneratorPromptSelection,
    GuidanceBasis,
    GuidanceConfidence,
    GuidanceParameter,
    GuidanceScope,
    ImageClassification,
    ImageContentClassification,
    ImageContext,
    ImageContextNotFoundError,
    ImageGeneratorHandoffValidationError,
    ImagePage,
    ImageScope,
    LoraDefinition,
    ManualPromptSelection,
    PlaygroundDraft,
    PlaygroundEvidence,
    PlaygroundEvidenceMatch,
    PlaygroundGenerationSweepPolicy,
    PlaygroundSubmissionBatch,
    PlaygroundSubmissionFailure,
    PromptComponent,
    PromptRenderer,
    PromptRevision,
    PromptSelection,
    PromptSelectionError,
    PromptSnapshot,
    RenderedPrompt,
    RenderGuidance,
    RenderGuidanceCoverage,
    RenderGuidancePage,
    RenderRecommendation,
    RenderSettings,
    ReviewResult,
    ReviewSummary,
    ScopeFacet,
    ScopeKind,
    SelectedPromptComponent,
    WorkflowProvenance,
)
from comfyreview.domain import (
    prompt_atom_usages_from_text,
    render_prompt_atom_usages,
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


class _ReviewHistory:
    def list_for_image(self, image_uid):
        if image_uid == "missing":
            from comfyreview.application import ReviewHistoryNotFoundError

            raise ReviewHistoryNotFoundError(
                "unknown canonical image: missing"
            )
        return (
            SimpleNamespace(
                event_uid="event-1",
                event_type="rating",
                rating=9,
                sequence=7,
                reviewed_at="2026-01-01 00:00:00",
            ),
        )


class _Curation:
    command = None

    def assign(self, command):
        self.command = command
        return CurationResult(
            command.image_uid, Path("image.png"), None, command.set_key
        )


class _ImageContentLevels:
    def set_level(self, image_uid, content_level):
        if image_uid == "missing":
            raise ContentClassificationError("unknown image")
        inferred = ContentLevel.SEXY
        return ImageContentClassification(
            inferred_level=inferred,
            effective_level=content_level or inferred,
            override_level=content_level,
        )


class _ImageGeneratorHandoffs:
    def get(self, image_uid):
        if image_uid == "missing":
            raise ImageContextNotFoundError("missing")
        if image_uid == "inconsistent":
            raise ImageGeneratorHandoffValidationError(
                "duplicate prompt scope kind: scene"
            )
        return SimpleNamespace(
            image_uid=image_uid,
            generation_uid="generation-1",
            prompt_setup=SimpleNamespace(
                source_image_uid=image_uid,
                availability="grouped",
                selections=(
                    GeneratorPromptSelection(
                        ScopeKind.CHARACTER, "character-a", "revision-a", 0
                    ),
                    GeneratorPromptSelection(
                        ScopeKind.SCENE, "scene-a", "revision-b", 1
                    ),
                    GeneratorPromptSelection(
                        ScopeKind.OUTFIT, "outfit-a", "revision-c", 2
                    ),
                    GeneratorPromptSelection(
                        ScopeKind.MODIFIER, "modifier-a", "revision-d", 3
                    ),
                ),
                component_uids=(
                    "character-a",
                    "scene-a",
                    "outfit-a",
                    "modifier-a",
                ),
                revision_uids=(
                    "revision-a",
                    "revision-b",
                    "revision-c",
                    "revision-d",
                ),
                positive_atoms=prompt_atom_usages_from_text("hero"),
                negative_atoms=prompt_atom_usages_from_text("blur"),
                draft_overridden=False,
                loras=(),
                issues=(),
            ),
            render_setup=SimpleNamespace(
                applicable=True,
                checkpoint="model.safetensors",
                sampler_stages=(
                    SimpleNamespace(
                        role="base_sampler",
                        order=0,
                        seed=17,
                        steps=24,
                        cfg=6.5,
                        sampler="euler",
                        scheduler="normal",
                        denoise=1.0,
                    ),
                ),
                seed=17,
                aspect_format="1:1",
                resolution_class="1080",
                actual_width=1080,
                actual_height=1080,
                target_width=1080,
                target_height=1080,
                geometry_match="exact",
                issues=(),
            ),
        )


class _LoraCatalog:
    def list_definitions(self):
        return (
            LoraDefinition(
                "lora-style",
                "style.safetensors",
                ContentLevel.LEWD,
                1,
            ),
        )


class _LoraDrafts:
    def resolve(self, selections):
        return tuple(
            SimpleNamespace(
                selection=replace(selection, name="style.safetensors"),
                display_name="Style",
                revision=SimpleNamespace(
                    revision_uid="lora-revision-style",
                    positive_atoms=prompt_atom_usages_from_text(
                        "style trigger"
                    ),
                    negative_atoms=(),
                ),
            )
            for selection in selections
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
            f"revision-{uid}",
            1,
            f"positive {uid}",
            "negative",
            "hash",
            prompt_atom_usages_from_text(f"positive {uid}"),
            prompt_atom_usages_from_text("negative"),
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
                render_prompt_atom_usages(command.positive_atoms),
                render_prompt_atom_usages(command.negative_atoms),
                "updated-hash",
                command.positive_atoms,
                command.negative_atoms,
            ),
        )
        return self.component

    def set_archived(self, component_uid, *, archived):
        self.component = replace(
            self.get_component(component_uid), archived=archived
        )
        return self.component


class _CatalogEvidence:
    def list_top_images(self, component_uid, *, limit=3):
        assert component_uid != "missing"
        assert limit == 3
        return (
            CatalogEvidenceImage("evidence-1", 9.25, 4),
            CatalogEvidenceImage("evidence-2", None, 0),
        )

    def list_top_lora_images(self, lora_uid, *, limit=3):
        assert lora_uid == "lora-style"
        assert limit == 3
        return (CatalogEvidenceImage("evidence-1", 9.25, 4),)


class _PlaygroundEvidence:
    query = None

    def find(self, query):
        self.query = query
        return PlaygroundEvidence(
            PlaygroundEvidenceMatch("image-prompt", 9.0, 4),
            PlaygroundEvidenceMatch("image-sampler", 8.0, 3),
        )


class _Playground:
    command = None
    confirm_command = None
    overrides = None

    def list_available_components(self):
        return (_prompt_component(),)

    def prepare_draft(self, command, *, overrides=None):
        self.command = command
        self.overrides = overrides
        character = _prompt_component()
        scene = _prompt_component("scene-a", "scene")
        character_revision = character.latest_revision
        character_revision_uid = getattr(
            command,
            "character_revision_uid",
            None,
        )
        if character_revision_uid is not None:
            character_revision = replace(
                character_revision,
                revision_uid=character_revision_uid,
            )
        scene_revision = scene.latest_revision
        manual_selections = getattr(command, "manual_selections", ())
        if manual_selections:
            requested_revision_uid = manual_selections[0].revision_uid
            if requested_revision_uid is not None:
                scene_revision = replace(
                    scene_revision,
                    revision_uid=requested_revision_uid,
                )
        selected = (
            SelectedPromptComponent(character, character_revision),
            SelectedPromptComponent(scene, scene_revision),
        )
        return PlaygroundDraft(
            PromptSelection(selected),
            RenderedPrompt(
                render_prompt_atom_usages(overrides.positive_atoms)
                if overrides and overrides.positive_atoms is not None
                else "rendered positive",
                "rendered negative",
                "notes",
                tuple(item.revision.revision_uid for item in selected),
                overrides is not None,
                overrides.positive_atoms
                if overrides and overrides.positive_atoms is not None
                else prompt_atom_usages_from_text("rendered positive"),
                prompt_atom_usages_from_text("rendered negative"),
            ),
        )

    def prepare_revision_draft(self, revision_uids):
        self.revision_uids = revision_uids
        return self.prepare_draft(SimpleNamespace(), overrides=None)

    def prepare_composition_draft(self, composition_uid):
        self.composition_uid = composition_uid
        return self.prepare_draft(SimpleNamespace(), overrides=None)

    def resolve_composition_selection(self, composition_uid):
        self.composition_uid = composition_uid
        character = _prompt_component()
        scene = _prompt_component("scene-a", "scene")
        selection = PromptSelection(
            (
                SelectedPromptComponent(
                    character,
                    replace(
                        character.latest_revision,
                        revision_uid="character-historical",
                    ),
                ),
                SelectedPromptComponent(
                    scene,
                    replace(
                        scene.latest_revision,
                        revision_uid="scene-historical",
                    ),
                ),
            ),
        )
        self.composition_selection = selection
        return selection

    def confirm_draft(self, command):
        self.confirm_command = command
        if "missing" in command.component_uids:
            raise KeyError("missing")
        components = (
            _prompt_component(),
            _prompt_component("scene-a", "scene"),
        )
        return PlaygroundDraft(
            PromptSelection(
                tuple(
                    SelectedPromptComponent(
                        component,
                        component.latest_revision,
                    )
                    for component in components
                )
            ),
            RenderedPrompt(
                render_prompt_atom_usages(command.positive_atoms),
                render_prompt_atom_usages(command.negative_atoms),
                "notes",
                ("revision-character-a", "revision-scene-a"),
                render_prompt_atom_usages(command.positive_atoms)
                != "rendered positive",
                command.positive_atoms,
                command.negative_atoms,
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
        failure_reason=None,
    )


class _PlaygroundDiscovery:
    def discover(self):
        return SimpleNamespace(
            checkpoints=["model.safetensors"],
            samplers=["euler"],
            schedulers=["normal"],
            loras=["style.safetensors"],
            upscale_models=["example-upscaler.pth"],
        )


class _WorkflowDefaults:
    def load(self, blueprint_uid, version):
        assert (blueprint_uid, version) == ("default-character", 4)
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

    def scope_context(self, **values):
        self.call = ("scopes", values)
        return {
            "rows": [
                {
                    "kind": "character",
                    "component_uid": "character-a",
                    "name": "Aiko",
                    "archived": False,
                    "image_count": 2,
                    "rating_count": 4,
                    "average_rating": 8.5,
                }
            ],
            "model_list": ["anime"],
        }

    def parameter_summary_context(self, **values):
        self.call = ("parameter-summary", values)
        return {
            "view": "summary",
            "recommendations": [{"checkpoint": "model.safetensors"}],
            "observed_setups": [{"setup_key": "setup-a"}],
            "model_list": ["anime"],
        }

    def parameter_values_context(self, parameter, **values):
        if parameter not in {
            "checkpoint",
            "steps",
            "cfg",
            "sampler",
            "scheduler",
        }:
            raise ValueError("unsupported render parameter")
        self.call = ("parameter-values", {"parameter": parameter, **values})
        return {
            "view": "values",
            "parameter": parameter,
            "rows": [{"value": "20"}],
            "model_list": ["anime"],
        }

    def composition_context(self, **values):
        self.call = ("combinations", values)
        return {
            "rows": [
                {
                    "composition_uid": "composition-a",
                    "component_names": ["Aiko", "Rooftop"],
                }
            ],
            "model_list": ["anime"],
        }

    def render_setups_context(self, **values):
        self.call = ("render-setups", values)
        return {
            "view": "render",
            "rows": [{"setup_key": "setup-a"}],
            "model_list": ["anime"],
        }

    def composition_render_setups_context(self, composition_uid, **values):
        self.call = (
            "composition-render-setups",
            {"composition_uid": composition_uid, **values},
        )
        return {
            "composition_uid": composition_uid,
            "rows": [{"setup_key": "setup-a"}],
        }

    def playground_combinations_context(self, **values):
        self.call = ("playground-combinations", values)
        return {
            "characters": [
                {
                    "character_uid": "character-a",
                    "character_name": "Aiko",
                    "two_component": [
                        {
                            "combo_key": "character-a|scene-a",
                            "component_uids": ["character-a", "scene-a"],
                            "component_names": ["Aiko", "Rooftop"],
                            "label": "Aiko + Rooftop",
                            "average_rating": 8.5,
                            "image_count": 2,
                            "rating_count": 4,
                            "best_images": [
                                {"url": "/files/output/image-1.png"}
                            ],
                        }
                    ],
                    "three_component": [],
                }
            ]
        }


class _AnalyticsCoverage:
    def load(self):
        return SimpleNamespace(
            active_image_count=12,
            rated_image_count=10,
            prompt_linked_image_count=9,
            unlinked_prompt_image_count=3,
            legacy_image_count=2,
            geometry_projected_count=11,
            missing_geometry_count=1,
            observed_setup_count=7,
            stable_setup_count=2,
            modeled_value_counts=(("sampler", 3),),
            geometry_value_counts=(("aspect_format", "1:1", 12),),
            model_version="render-guidance-v1",
        )


class _RenderGuidance:
    def __init__(self) -> None:
        settings = RenderSettings(
            "model.safetensors", "euler", "normal", 24, 6.5, 1.0
        )
        score = EvidenceScore(
            GuidanceBasis.OBSERVED,
            0.8,
            0.8,
            0.6,
            8.0,
            6,
            8,
            GuidanceConfidence.LOW,
            True,
            True,
            1.0,
        )
        self.recommendation = RenderRecommendation(settings, score, True)
        self.coverage = RenderGuidanceCoverage(
            6, 8, 1, 1, ((GuidanceParameter.SAMPLER, 1),)
        )

    def build(self, **_values):
        return RenderGuidance(
            self.recommendation,
            None,
            self.recommendation,
            self.recommendation,
            None,
            None,
            (),
            (self.recommendation,),
            (),
            self.coverage,
        )

    def query(self, **values):
        if values.get("parameter") == "seed":
            raise ValueError("unsupported render parameter")
        return RenderGuidancePage(
            GuidanceBasis.OBSERVED,
            GuidanceScope.SETUP,
            None,
            (self.recommendation,),
            1,
            1,
            1,
            0,
            24,
            self.coverage,
        )


class _PlaygroundRenderGuidance:
    def __init__(self, guidance: _RenderGuidance) -> None:
        self.guidance = guidance

    def build(self, _settings):
        return self.guidance.build()


class _PlaygroundGeneratorSettings:
    def __init__(self) -> None:
        self.settings = {
            "selections": [],
            "loras": [],
            "checkpoint": "model.safetensors",
            "sampler": "euler",
            "scheduler": "normal",
            "seed_mode": "fixed",
            "seed": 17,
            "steps_min": 24,
            "steps_max": 24,
            "cfg_min": 6.5,
            "cfg_max": 6.5,
            "cfg_step": 0.1,
            "denoise": 1.0,
            "batch_runs": 1,
            "aspect_format": "1:1",
            "resolution_class": "1080",
        }

    def load(self):
        return dict(self.settings)

    def save(self, settings):
        self.settings = dict(settings)
        return dict(self.settings)


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
    assert container.image_contexts.query.filters.minimum_rating_count == 1


def test_v2_image_context_has_url_but_never_exposes_local_path() -> None:
    client, _container = _client()

    response = client.get("/api/v2/images/image-1")

    assert response.status_code == 200
    assert response.json()["image_url"] == "/files/output/image-1.png"
    assert response.json()["prompt_snapshot"]["positive"] == "positive"
    assert "png_path" not in response.text
    assert "json_path" not in response.text


def test_v2_image_generator_handoff_exposes_visible_prompt_components() -> (
    None
):
    client, _container = _client()

    response = client.get("/api/v2/images/image-1/generator-handoff")

    assert response.status_code == 200
    assert response.json()["prompt_setup"]["component_uids"] == [
        "character-a",
        "scene-a",
        "outfit-a",
        "modifier-a",
    ]
    assert response.json()["prompt_setup"]["revision_uids"] == [
        "revision-a",
        "revision-b",
        "revision-c",
        "revision-d",
    ]
    assert response.json()["prompt_setup"]["selections"] == [
        {
            "kind": "character",
            "component_uid": "character-a",
            "revision_uid": "revision-a",
            "position": 0,
        },
        {
            "kind": "scene",
            "component_uid": "scene-a",
            "revision_uid": "revision-b",
            "position": 1,
        },
        {
            "kind": "outfit",
            "component_uid": "outfit-a",
            "revision_uid": "revision-c",
            "position": 2,
        },
        {
            "kind": "modifier",
            "component_uid": "modifier-a",
            "revision_uid": "revision-d",
            "position": 3,
        },
    ]


def test_v2_image_generator_handoff_reports_inconsistent_scopes() -> None:
    client, _container = _client()

    response = client.get("/api/v2/images/inconsistent/generator-handoff")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "inconsistent_generator_handoff"
    assert error["message"] == "duplicate prompt scope kind: scene"


def test_v2_image_content_level_supports_override_and_inherit() -> None:
    client, _container = _client()

    overridden = client.put(
        "/api/v2/images/image-1/content-level",
        json={"content_level": "nude"},
    )
    inherited = client.put(
        "/api/v2/images/image-1/content-level",
        json={"content_level": None},
    )
    missing = client.put(
        "/api/v2/images/missing/content-level",
        json={"content_level": "explicit"},
    )

    assert overridden.json() == {
        "inferred_level": "sexy",
        "effective_level": "nude",
        "override_level": "nude",
    }
    assert inherited.json()["effective_level"] == "sexy"
    assert inherited.json()["override_level"] is None
    assert missing.status_code == 404


def test_v2_review_history_exposes_append_only_events() -> None:
    client, _container = _client()

    response = client.get("/api/v2/images/image-1/reviews")
    missing = client.get("/api/v2/images/missing/reviews")

    assert response.status_code == 200
    assert response.json() == {
        "image_uid": "image-1",
        "events": [
            {
                "event_uid": "event-1",
                "event_type": "rating",
                "rating": 9,
                "sequence": 7,
                "reviewed_at": "2026-01-01 00:00:00",
            }
        ],
    }
    assert missing.status_code == 404


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
    playground_catalog = client.get("/api/v2/playground/components")
    capabilities = client.get("/api/v2/playground/capabilities")
    loras = client.get("/api/v2/catalog/loras")

    assert catalog.status_code == 200
    assert catalog.json()["components"][0]["component_uid"] == "character-a"
    assert catalog.json()["components"][0]["latest_revision"] == {
        "revision_uid": "revision-character-a",
        "revision_number": 1,
        "positive_text": "positive character-a",
        "negative_text": "negative",
        "positive_atoms": [{"text": "positive character-a", "weight": 1.0}],
        "negative_atoms": [{"text": "negative", "weight": 1.0}],
    }
    assert playground_catalog.status_code == 200
    assert loras.json()["loras"][0]["available"] is True
    assert playground_catalog.json()["components"][0]["component_uid"] == (
        "character-a"
    )
    assert capabilities.json() == {
        "checkpoints": ["model.safetensors"],
        "samplers": ["euler"],
        "schedulers": ["normal"],
        "loras": ["style.safetensors"],
        "lora_definitions": [
            {
                "lora_uid": "lora-style",
                "provider_name": "style.safetensors",
                "display_name": "style.safetensors",
                "tags": [],
                "notes": "",
                "content_level": "lewd",
                "revision": 1,
                "archived": False,
                "latest_revision": None,
                "available": True,
            }
        ],
        "upscale_models": ["example-upscaler.pth"],
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
    combinations = client.get("/api/v2/playground/top-combinations")
    assert combinations.status_code == 200
    assert combinations.json()["characters"][0]["two_component"][0][
        "component_uids"
    ] == [
        "character-a",
        "scene-a",
    ]


def test_v2_playground_projects_exact_composition_prompt_selections() -> None:
    client, container = _client()

    response = client.get(
        "/api/v2/playground/compositions/composition-a/prompt-selections"
    )

    assert response.status_code == 200
    assert response.json() == {
        "selections": [
            {
                "kind": "character",
                "component_uid": "character-a",
                "revision_uid": "character-historical",
            },
            {
                "kind": "scene",
                "component_uid": "scene-a",
                "revision_uid": "scene-historical",
            },
        ]
    }
    assert container.playground_service.composition_uid == "composition-a"
    assert tuple(
        selected.revision.revision_uid
        for selected in container.playground_service.composition_selection.components
    ) == ("character-historical", "scene-historical")


def test_v2_playground_composition_handoff_surfaces_selection_rejection() -> (
    None
):
    client, container = _client()

    for message in (
        "composition contains an inactive prompt component",
        "prompt selection contains a disabled content level",
    ):

        def reject_composition(
            composition_uid: str,
            expected_message: str = message,
        ) -> PromptSelection:
            assert composition_uid == "composition-rejected"
            raise PromptSelectionError(expected_message)

        container.playground_service.resolve_composition_selection = (
            reject_composition
        )
        response = client.get(
            "/api/v2/playground/compositions/composition-rejected/prompt-selections"
        )

        assert response.status_code == 400
        assert response.json()["error"]["message"] == message


def test_v2_playground_generator_state_round_trips_strict_payload() -> None:
    client, container = _client()

    current = client.get("/api/v2/playground/generator-state")
    selections = [
        {
            "kind": "character",
            "mode": "fixed",
            "component_uid": "character-a",
            "revision_uid": "revision-character-old",
        }
    ]
    changed = {
        **current.json(),
        "selections": selections,
        "steps_min": 28,
        "steps_max": 32,
    }
    saved = client.put(
        "/api/v2/playground/generator-state",
        json=changed,
    )
    restored = client.get("/api/v2/playground/generator-state")
    invalid = client.put(
        "/api/v2/playground/generator-state",
        json={**changed, "unknown": True},
    )

    assert current.status_code == 200
    assert saved.status_code == 200
    assert saved.json()["steps_min"] == 28
    assert saved.json()["selections"] == selections
    assert restored.json()["selections"] == selections
    assert container.playground_generator_settings.settings == changed
    assert invalid.status_code == 422


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
            "content_level": "standard",
            "tags": ["rain"],
            "notes": "note",
            "positive_atoms": [{"text": "rainy street", "weight": 1.0}],
            "negative_atoms": [{"text": "sun", "weight": 1.0}],
        },
    )
    updated = client.put(
        "/api/v2/catalog/components/created",
        json={
            "kind": "scene",
            "name": "Rainy street night",
            "content_level": "standard",
            "tags": ["rain", "night"],
            "positive_atoms": [
                {"text": "rainy street at night", "weight": 1.0}
            ],
            "negative_atoms": [{"text": "sun", "weight": 1.0}],
        },
    )
    archived = client.patch(
        "/api/v2/catalog/components/created", json={"archived": True}
    )

    assert detail.status_code == 200
    assert detail.json()["top_images"] == [
        {
            "image_uid": "evidence-1",
            "image_url": "/files/output/evidence-1.png",
            "average_rating": 9.25,
            "rating_count": 4,
        },
        {
            "image_uid": "evidence-2",
            "image_url": "/files/output/evidence-2.png",
            "average_rating": None,
            "rating_count": 0,
        },
    ]
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
        "content_level": "standard",
        "positive_atoms": [{"text": "scene", "weight": 1.0}],
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
        {
            "kind": "character",
            "mode": "fixed",
            "component_uid": "character-a",
            "revision_uid": "revision-character-old",
        },
        {
            "kind": "scene",
            "mode": "fixed",
            "component_uid": "scene-a",
            "revision_uid": "revision-scene-old",
        },
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
            "generation": _draft_generation(seed=17),
            "positive_atoms": [{"text": "draft positive", "weight": 1.0}],
        },
    )

    assert response.status_code == 200
    assert response.json()["draft_uid"].startswith("draft-")
    assert response.json()["seed"] == 17
    assert response.json()["positive_prompt"] == "draft positive"
    assert response.json()["revision_uids"] == [
        "revision-character-old",
        "revision-scene-old",
    ]
    assert (
        response.json()["components"][0]["latest_revision"]["revision_uid"]
        == "revision-character-a"
    )
    assert response.json()["groups"][0]["revision_uid"] == (
        "revision-character-old"
    )
    assert response.json()["groups"][1]["revision_uid"] == (
        "revision-scene-old"
    )
    assert response.json()["groups"][1]["positive_atoms"] == [
        {"text": "positive scene-a", "weight": 1.0}
    ]
    assert container.playground_service.command.character_component_uid == (
        "character-a"
    )
    assert (
        container.playground_service.command.character_revision_uid
        == "revision-character-old"
    )
    assert container.playground_service.command.manual_selections[0] == (
        ManualPromptSelection("scene", "scene-a", "revision-scene-old")
    )
    assert container.playground_service.command.disabled_kinds == (
        "pose",
        "lighting",
    )
    for selection_index in (2, 3):
        invalid_revision_mode = [dict(selection) for selection in selections]
        invalid_revision_mode[selection_index]["revision_uid"] = (
            "revision-not-fixed"
        )
        rejected = client.post(
            "/api/v2/playground/drafts",
            json={
                "selections": invalid_revision_mode,
                "generation": _draft_generation(seed=17),
            },
        )
        assert rejected.status_code == 400
        assert rejected.json()["error"]["code"] == (
            "invalid_playground_selection"
        )

    preview = client.post(
        "/api/v2/playground/render-preview",
        json={
            "positive_atoms": [
                {"text": "cyan eyes", "weight": 1.2},
                {"text": "silver hair", "weight": 1.0},
            ],
            "negative_atoms": [{"text": "blur", "weight": 1.0}],
        },
    )
    assert preview.json() == {
        "positive_prompt": "(cyan eyes:1.2), silver hair",
        "negative_prompt": "blur",
    }

    randomized = client.post(
        "/api/v2/playground/drafts",
        json={
            "selections": selections,
            "generation": _draft_generation(seed=None),
        },
    )
    concrete_seed = randomized.json()["seed"]
    assert isinstance(concrete_seed, int)
    assert container.playground_service.command.seed == concrete_seed

    evidence = client.post(
        "/api/v2/playground/evidence",
        json={
            **_draft_generation(),
            "positive_atoms": [{"text": "hero", "weight": 1.01}],
            "negative_atoms": [{"text": "blur", "weight": 1.0}],
        },
    )
    assert evidence.json()["prompt_match"]["image_uid"] == "image-prompt"
    assert evidence.json()["sampler_match"]["image_uid"] == "image-sampler"
    assert (
        container.playground_evidence.query.positive_atoms[0].weight_milli
        == 1010
    )


def test_v2_playground_draft_appends_selected_lora_triggers() -> None:
    client, _container = _client()

    response = client.post(
        "/api/v2/playground/drafts",
        json={
            "selections": [
                {
                    "kind": kind,
                    "mode": "fixed" if kind == "character" else "off",
                    **(
                        {"component_uid": "character-a"}
                        if kind == "character"
                        else {}
                    ),
                }
                for kind in (
                    "character",
                    "scene",
                    "outfit",
                    "pose",
                    "expression",
                    "lighting",
                    "modifier",
                )
            ],
            "generation": _draft_generation(),
            "loras": [
                {
                    "lora_uid": "lora-style",
                    "revision_uid": "lora-revision-style",
                    "model_strength": 0.8,
                    "clip_strength": 0.7,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["positive_prompt"]
        == "rendered positive, style trigger"
    )
    assert response.json()["positive_atoms"][-1] == {
        "text": "style trigger",
        "weight": 1.0,
    }
    assert response.json()["groups"][-1]["kind"] == "lora"
    assert response.json()["groups"][-1]["positive_atoms"] == [
        {"text": "style trigger", "weight": 1.0}
    ]


def test_v2_playground_rejects_incomplete_or_disabled_character_intent() -> (
    None
):
    client, _container = _client()

    incomplete = client.post(
        "/api/v2/playground/drafts",
        json={
            "selections": [{"kind": "character", "mode": "random"}],
            "generation": _draft_generation(),
        },
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
        "/api/v2/playground/drafts",
        json={"selections": selections, "generation": _draft_generation()},
    )

    assert incomplete.status_code == 400
    assert incomplete.json()["error"]["code"] == (
        "invalid_playground_selection"
    )
    assert disabled.status_code == 400


def test_v2_playground_accepts_exact_revision_and_composition_handoffs() -> (
    None
):
    client, container = _client()

    revisions = client.post(
        "/api/v2/playground/drafts",
        json={
            "revision_uids": ["revision-character-a", "revision-scene-a"],
            "generation": _draft_generation(),
        },
    )
    composition = client.post(
        "/api/v2/playground/drafts",
        json={
            "composition_uid": "composition-a",
            "generation": _draft_generation(),
        },
    )
    mixed = client.post(
        "/api/v2/playground/drafts",
        json={
            "composition_uid": "composition-a",
            "revision_uids": ["revision-character-a"],
            "generation": _draft_generation(),
        },
    )

    assert revisions.status_code == 200
    assert container.playground_service.revision_uids == (
        "revision-character-a",
        "revision-scene-a",
    )
    assert composition.status_code == 200
    assert container.playground_service.composition_uid == "composition-a"
    assert mixed.status_code == 400


def test_v2_generation_submission_uses_reviewed_snapshot_and_stable_revisions() -> (
    None
):
    client, container = _client()
    payload = {
        "draft_uid": "draft-1",
        "component_uids": ["character-a", "scene-a"],
        "positive_atoms": [{"text": "edited positive", "weight": 1.0}],
        "negative_atoms": [{"text": "edited negative", "weight": 1.0}],
        "checkpoint": "model.safetensors",
        "aspect_format": "2:3",
        "resolution_class": "1080",
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
        "submissions": [
            {
                "generation_uid": "generation-1",
                "status": "submitted",
                "prompt_id": "prompt-1",
            }
        ],
    }
    draft = container.playground_submission_service.draft
    assert draft.prompt.positive_text == "edited positive"
    assert draft.prompt.revision_uids == (
        "revision-character-a",
        "revision-scene-a",
    )
    assert draft.output_subdirectory == "playground/character-a-key"
    assert draft.aspect_format.value == "2:3"
    assert draft.resolution_class.value == "1080"
    assert draft.blueprint_version == 4
    assert container.playground_service.confirm_command.component_uids == (
        "character-a",
        "scene-a",
    )


def test_v2_generation_submission_surfaces_validation_and_submit_failures() -> (
    None
):
    client, container = _client()
    payload: dict[str, Any] = {
        "draft_uid": "draft-1",
        "component_uids": ["missing"],
        "positive_atoms": [{"text": "positive", "weight": 1.0}],
        "negative_atoms": [{"text": "negative", "weight": 1.0}],
        "checkpoint": "model.safetensors",
        "aspect_format": "2:3",
        "resolution_class": "1080",
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
    bad_sweep = {
        **payload,
        "sampler": {**payload["sampler"], "steps_max": 20},
    }
    invalid_sweep = client.post("/api/v2/generations", json=bad_sweep)
    container.playground_submission_service.fail = True
    failed = client.post("/api/v2/generations", json=payload)

    graph_payload = dict(payload)
    graph_payload["workflow_graph"] = {"42": {"class_type": "SaveImage"}}
    graph = client.post("/api/v2/generations", json=graph_payload)

    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_generation"
    assert invalid_sweep.status_code == 400
    assert failed.status_code == 500
    assert failed.json()["error"]["code"] == "generation_failed"
    assert graph.status_code == 422


def _draft_generation(seed: int | None = 17) -> dict[str, object]:
    return {
        "checkpoint": "model.safetensors",
        "sampler": "euler",
        "scheduler": "normal",
        "seed": seed,
        "randomize_seed": seed is None,
        "steps": 24,
        "cfg": 6.5,
        "denoise": 1.0,
        "aspect_format": "2:3",
        "resolution_class": "1080",
    }


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
    scopes = client.get("/api/v2/analytics/scopes")
    render = client.get("/api/v2/analytics/render")
    combinations = client.get(
        "/api/v2/analytics/combinations", params={"min_n": 2}
    )
    composition_setups = client.get(
        "/api/v2/analytics/combinations/composition-a/render-setups"
    )
    invalid_parameter = client.get(
        "/api/v2/analytics/render",
        params={"scope": "parameter", "parameter": "seed"},
    )
    retired_parameters = client.get("/api/v2/analytics/parameters")

    assert overview.json()["observed_setup_count"] == 7
    assert scopes.json()["rows"][0]["component_uid"] == "character-a"
    assert render.json()["items"][0]["settings"]["checkpoint"] == (
        "model.safetensors"
    )
    assert combinations.json()["rows"][0]["composition_uid"] == (
        "composition-a"
    )
    assert composition_setups.json()["composition_uid"] == "composition-a"
    assert invalid_parameter.status_code == 400
    assert retired_parameters.status_code == 404
    assert container.analytics_pages.call == (
        "composition-render-setups",
        {
            "composition_uid": "composition-a",
            "model": "",
            "min_n": 1,
            "limit": 20,
        },
    )


def _client() -> tuple[TestClient, SimpleNamespace]:
    render_guidance = _RenderGuidance()
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
        review_history=_ReviewHistory(),
        curation_service=_Curation(),
        image_content_levels=_ImageContentLevels(),
        image_generator_handoffs=_ImageGeneratorHandoffs(),
        arena_service=_Arena(),
        prompt_catalog_service=_PromptCatalog(),
        catalog_evidence=_CatalogEvidence(),
        playground_evidence=_PlaygroundEvidence(),
        prompt_renderer=PromptRenderer(),
        playground_service=_Playground(),
        playground_submission_service=_PlaygroundSubmission(),
        playground_generation_sweeps=PlaygroundGenerationSweepPolicy(),
        generation_queries=_GenerationQueries(),
        generation_reconciliation=_GenerationReconciliation(),
        playground_discovery=_PlaygroundDiscovery(),
        workflow_defaults=_WorkflowDefaults(),
        lora_catalog=_LoraCatalog(),
        lora_drafts=_LoraDrafts(),
        analytics_pages=_AnalyticsPages(),
        analytics_coverage=_AnalyticsCoverage(),
        render_guidance=render_guidance,
        playground_render_guidance=_PlaygroundRenderGuidance(render_guidance),
        playground_generator_settings=_PlaygroundGeneratorSettings(),
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
