"""HTTP contracts for canonical workspace settings and profiles."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from comfyreview.application import (
    ContentClassificationError,
    ContentLevel,
    GenerationLoraSelection,
    GenerationProfile,
    LoraDefinition,
    LoraReclassificationImpact,
    LoraRevision,
    RuntimeConfigurationSnapshot,
    RuntimeDiagnostics,
    WorkspacePreferences,
    WorkspaceSettingsValidationError,
)
from routers.api_v2.settings import router


def _lora_revision(level: ContentLevel, number: int) -> LoraRevision:
    return LoraRevision(
        f"revision-{number}",
        number,
        1000,
        1000,
        level,
        f"hash-{number}",
    )


class _Preferences:
    def __init__(self, value: WorkspacePreferences) -> None:
        self.value = value
        self.error: Exception | None = None

    def get(self) -> WorkspacePreferences:
        return self.value

    def update(
        self, preferences: WorkspacePreferences
    ) -> WorkspacePreferences:
        if self.error is not None:
            raise self.error
        self.value = preferences
        return preferences

    def set_default_profile(self, profile_uid: str) -> WorkspacePreferences:
        if self.error is not None:
            raise self.error
        self.value = replace(
            self.value,
            default_generation_profile_uid=profile_uid,
        )
        return self.value


class _Profiles:
    def __init__(self, value: GenerationProfile) -> None:
        self.value = value
        self.error: Exception | None = None

    def list_profiles(self) -> tuple[GenerationProfile, ...]:
        return (self.value,)

    def create(self, profile: GenerationProfile) -> GenerationProfile:
        return self._write(replace(profile, profile_uid="created-profile"))

    def update(self, profile: GenerationProfile) -> GenerationProfile:
        return self._write(profile)

    def set_archived(
        self, profile_uid: str, archived: bool
    ) -> GenerationProfile:
        return self._write(replace(self.value, archived=archived))

    def _write(self, profile: GenerationProfile) -> GenerationProfile:
        if self.error is not None:
            raise self.error
        self.value = profile
        return profile


class _Diagnostics:
    def snapshot(self) -> RuntimeDiagnostics:
        diagnostics = self.inspect()
        return replace(
            diagnostics,
            connected=False,
            node_classes=(),
            checkpoints=(),
            samplers=(),
            schedulers=(),
            loras=(),
            message="not_checked",
        )

    def inspect(self) -> RuntimeDiagnostics:
        return RuntimeDiagnostics(
            configuration=RuntimeConfigurationSnapshot(
                comfyui_base_url="http://127.0.0.1:8188",
                output_root="C:/output",
                workflows_directory="C:/workflows",
                canonical_database_path="C:/canonical.sqlite3",
                schema_version=9,
                runtime_mode="canonical",
                environment_variables=("COMFYUI_BASE_URL",),
            ),
            connected=True,
            node_classes=("CheckpointLoaderSimple",),
            checkpoints=("model.safetensors",),
            samplers=("euler",),
            schedulers=("normal",),
            loras=("style.safetensors",),
            upscale_models=("example-upscaler.pth",),
            message="connected",
        )


class _LoraCatalog:
    def __init__(self) -> None:
        self.definition = LoraDefinition(
            "lora-style",
            "style.safetensors",
            ContentLevel.SEXY,
            2,
            latest_revision=_lora_revision(ContentLevel.SEXY, 2),
        )
        self.error: Exception | None = None

    def list_definitions(self) -> tuple[LoraDefinition, ...]:
        return (self.definition,)

    def classify(
        self, provider_name: str, content_level: ContentLevel
    ) -> LoraDefinition:
        if self.error is not None:
            raise self.error
        self.definition = LoraDefinition(
            "lora-style",
            provider_name,
            content_level,
            3,
            latest_revision=_lora_revision(content_level, 3),
        )
        return self.definition

    def preview(self, lora_uid: str) -> LoraReclassificationImpact:
        if self.error is not None:
            raise self.error
        return LoraReclassificationImpact(lora_uid, 3, 4, 5, 1)

    def reclassify(
        self, lora_uid: str, expected_revision: int
    ) -> LoraReclassificationImpact:
        if self.error is not None:
            raise self.error
        return LoraReclassificationImpact(lora_uid, expected_revision, 4, 5, 1)


def test_settings_api_reads_and_updates_canonical_preferences() -> None:
    client, container = _client()

    response = client.get("/settings")
    updated = client.put(
        "/settings/preferences",
        json={
            "density": "compact",
            "motion": "reduced",
            "analytics_page_size": 48,
            "review_prioritize_unrated": False,
            "default_curation_set_key": "favorites",
            "curation_set_order": ["favorites", "archive"],
            "enabled_content_levels": ["sexy"],
        },
    )

    assert response.status_code == 200
    assert response.json()["runtime"]["configuration"]["schema_version"] == 9
    assert response.json()["runtime"]["message"] == "not_checked"
    assert response.json()["lora_definitions"][0]["lora_uid"] == ("lora-style")
    assert "generation_profiles" not in response.json()
    assert (
        "default_generation_profile_uid" not in response.json()["preferences"]
    )
    assert updated.status_code == 200
    assert updated.json()["density"] == "compact"
    assert (
        container.workspace_preferences.value.review_prioritize_unrated
        is False
    )
    assert container.workspace_preferences.value.enabled_content_levels == (
        ContentLevel.SEXY,
    )


def test_settings_api_removes_profiles_and_reports_capabilities() -> None:
    client, _ = _client()
    payload = _profile_payload()

    listed = client.get("/settings/generation-profiles")
    created = client.post("/settings/generation-profiles", json=payload)
    updated = client.put(
        "/settings/generation-profiles/created-profile",
        json={**payload, "name": "Updated"},
    )
    archived = client.patch(
        "/settings/generation-profiles/created-profile/archive",
        json={"archived": True},
    )
    selected = client.put(
        "/settings/generation-profiles/created-profile/default"
    )
    checked = client.post("/settings/comfyui/check")
    capabilities = client.get("/generation-capabilities")

    assert listed.status_code == 404
    assert created.status_code == 404
    assert updated.status_code == 404
    assert archived.status_code == 404
    assert selected.status_code == 404
    assert checked.json()["connected"] is True
    assert capabilities.json()["loras"] == ["style.safetensors"]
    assert capabilities.json()["upscale_models"] == ["example-upscaler.pth"]


def test_settings_api_classifies_loras_and_reclassifies_history() -> None:
    client, _container = _client()

    classified = client.post(
        "/settings/loras/classify",
        json={
            "provider_name": "style.safetensors",
            "content_level": "nude",
        },
    )
    preview = client.get("/settings/loras/lora-style/reclassification-impact")
    applied = client.post(
        "/settings/loras/lora-style/reclassify",
        json={"expected_revision": 3},
    )

    assert classified.status_code == 200
    assert classified.json()["latest_revision"]["content_level"] == "nude"
    assert preview.json()["image_count"] == 5
    assert preview.json()["manual_override_count"] == 1
    assert applied.json()["revision"] == 3


def test_settings_api_maps_lora_policy_errors() -> None:
    client, container = _client()
    container.lora_catalog.error = ContentClassificationError("invalid")

    classified = client.post(
        "/settings/loras/classify",
        json={
            "provider_name": "style.safetensors",
            "content_level": "nude",
        },
    )
    preview = client.get("/settings/loras/missing/reclassification-impact")
    applied = client.post(
        "/settings/loras/lora-style/reclassify",
        json={"expected_revision": 2},
    )

    assert classified.status_code == 400
    assert preview.status_code == 404
    assert applied.status_code == 409


def test_settings_api_maps_preference_validation() -> None:
    client, container = _client()
    container.workspace_preferences.error = WorkspaceSettingsValidationError(
        "invalid settings"
    )
    invalid_preferences = client.put(
        "/settings/preferences",
        json={
            "density": "compact",
            "motion": "system",
            "analytics_page_size": 24,
            "review_prioritize_unrated": True,
            "curation_set_order": [],
        },
    )
    assert invalid_preferences.status_code == 400
    assert invalid_preferences.json()["error"]["code"] == (
        "invalid_preferences"
    )


def _client() -> tuple[TestClient, SimpleNamespace]:
    container = SimpleNamespace(
        settings=SimpleNamespace(curation_set_keys=("favorites", "archive")),
        workspace_preferences=_Preferences(WorkspacePreferences()),
        generation_profiles=_Profiles(_profile()),
        runtime_diagnostics=_Diagnostics(),
        lora_catalog=_LoraCatalog(),
    )
    application = FastAPI()
    application.state.container = container
    application.include_router(router)
    return TestClient(application), container


def _profile() -> GenerationProfile:
    return GenerationProfile(
        profile_uid="profile-a",
        name="Editorial",
        blueprint_uid="default-character",
        blueprint_version=2,
        checkpoint="model.safetensors",
        sampler="euler",
        scheduler="normal",
        seed_mode="random",
        fixed_seed=None,
        steps_min=24,
        steps_max=36,
        cfg_min_milli=4500,
        cfg_max_milli=7000,
        denoise_milli=1000,
        batch_size=1,
        image_width=768,
        image_height=1152,
        loras=(
            GenerationLoraSelection(
                name="style.safetensors",
                model_strength_milli=800,
                clip_strength_milli=600,
                position=0,
            ),
        ),
    )


def _profile_payload() -> dict[str, object]:
    return {
        "name": "Editorial",
        "blueprint_uid": "default-character",
        "blueprint_version": 2,
        "checkpoint": "model.safetensors",
        "sampler": "euler",
        "scheduler": "normal",
        "seed_mode": "random",
        "fixed_seed": None,
        "steps_min": 24,
        "steps_max": 36,
        "cfg_min": 4.5,
        "cfg_max": 7,
        "denoise": 1,
        "batch_size": 1,
        "image_width": 768,
        "image_height": 1152,
        "output_tier": "full_hd_1080",
        "loras": [
            {
                "name": "style.safetensors",
                "model_strength": 0.8,
                "clip_strength": 0.6,
            }
        ],
    }
