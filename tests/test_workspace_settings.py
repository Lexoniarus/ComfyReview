"""Behavior tests for typed workspace settings and generation profiles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pytest

from comfyreview.application import (
    ComfyUiCapabilities,
    ComfyUiConnectionError,
    RuntimeConfigurationSnapshot,
    RuntimeDiagnosticsService,
)
from comfyreview.application.workspace_settings import (
    ContentLevel,
    GenerationLoraSelection,
    GenerationProfile,
    GenerationProfileService,
    WorkspacePreferences,
    WorkspacePreferencesService,
    WorkspaceSettingsValidationError,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteGenerationProfileRepository,
    SqliteWorkspacePreferencesRepository,
)


class _Profiles:
    def __init__(self, profiles: tuple[GenerationProfile, ...] = ()) -> None:
        self.values = {profile.profile_uid: profile for profile in profiles}

    def list_profiles(self) -> tuple[GenerationProfile, ...]:
        return tuple(self.values.values())

    def get(self, profile_uid: str) -> GenerationProfile:
        return self.values[profile_uid]

    def save(self, profile: GenerationProfile) -> GenerationProfile:
        self.values[profile.profile_uid] = profile
        return profile

    def set_archived(
        self, profile_uid: str, archived: bool
    ) -> GenerationProfile:
        value = replace(self.values[profile_uid], archived=archived)
        self.values[profile_uid] = value
        return value


class _Preferences:
    def __init__(self, value: WorkspacePreferences) -> None:
        self.value = value

    def get(self) -> WorkspacePreferences:
        return self.value

    def save(self, preferences: WorkspacePreferences) -> WorkspacePreferences:
        self.value = preferences
        return preferences


class _Identities:
    def new_profile_uid(self) -> str:
        return "profile-created"


class _ComfyUi:
    def __init__(self, result: ComfyUiCapabilities | Exception) -> None:
        self.result = result

    def discover_capabilities(self) -> ComfyUiCapabilities:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class _UnexpectedComfyUi:
    def discover_capabilities(self) -> ComfyUiCapabilities:
        raise AssertionError("snapshot must not call ComfyUI")


class _CapabilityCache:
    def __init__(self, values: dict[str, object] | None = None) -> None:
        self.values = values or {}

    def load(self) -> dict[str, object]:
        return self.values

    def save(self, capabilities: Mapping[str, object]) -> None:
        self.values = dict(capabilities)


class _FailingCapabilityCache(_CapabilityCache):
    def save(self, capabilities: Mapping[str, object]) -> None:
        raise OSError("cache unavailable")


def _profile(
    *,
    profile_uid: str = "profile-one",
    name: str = "Editorial",
    blueprint_version: int = 2,
    seed_mode: str = "random",
    fixed_seed: int | None = None,
    steps_min: int = 24,
    steps_max: int = 36,
    cfg_min_milli: int = 4500,
    cfg_max_milli: int = 7000,
    denoise_milli: int = 1000,
    batch_size: int = 1,
    image_width: int = 1024,
    image_height: int = 1024,
    loras: tuple[GenerationLoraSelection, ...] = (
        GenerationLoraSelection("style.safetensors", 800, 600, 0),
    ),
    archived: bool = False,
    is_default: bool = False,
) -> GenerationProfile:
    return GenerationProfile(
        profile_uid=profile_uid,
        name=name,
        blueprint_uid="default-character",
        blueprint_version=blueprint_version,
        checkpoint="model.safetensors",
        sampler="euler",
        scheduler="normal",
        seed_mode=seed_mode,
        fixed_seed=fixed_seed,
        steps_min=steps_min,
        steps_max=steps_max,
        cfg_min_milli=cfg_min_milli,
        cfg_max_milli=cfg_max_milli,
        denoise_milli=denoise_milli,
        batch_size=batch_size,
        image_width=image_width,
        image_height=image_height,
        loras=loras,
        archived=archived,
        is_default=is_default,
    )


def test_generation_profile_service_preserves_ordered_lora_stack() -> None:
    repository = _Profiles()
    service = GenerationProfileService(repository, _Identities())
    source = _profile(
        profile_uid="browser-value",
        archived=True,
        is_default=True,
        loras=(
            GenerationLoraSelection("first.safetensors", 800, 700, 0),
            GenerationLoraSelection("second.safetensors", 600, 500, 1),
        ),
    )

    created = service.create(source)

    assert created.profile_uid == "profile-created"
    assert created.archived is False
    assert created.is_default is False
    assert [lora.name for lora in created.loras] == [
        "first.safetensors",
        "second.safetensors",
    ]
    assert service.list_profiles() == (created,)


def test_generation_profile_service_validates_ranges_and_lora_positions() -> (
    None
):
    service = GenerationProfileService(_Profiles(), _Identities())

    invalid_profiles = (
        _profile(name=""),
        _profile(blueprint_version=0),
        _profile(seed_mode="unknown"),
        _profile(steps_min=40, steps_max=20),
        _profile(cfg_min_milli=7000, cfg_max_milli=4000),
        _profile(seed_mode="fixed", fixed_seed=None),
        _profile(denoise_milli=1001),
        _profile(batch_size=0),
        _profile(image_width=1001),
        _profile(image_height=4104),
        _profile(loras=(GenerationLoraSelection("style", 1000, 1000, 1),)),
        _profile(loras=(GenerationLoraSelection("", 1000, 1000, 0),)),
        _profile(
            loras=(
                GenerationLoraSelection("style", 1000, 1000, 0),
                GenerationLoraSelection("style", 1000, 1000, 1),
            )
        ),
        _profile(loras=(GenerationLoraSelection("style", 10_001, 1000, 0),)),
        _profile(loras=(GenerationLoraSelection("style", 1000, -10_001, 0),)),
    )

    for profile in invalid_profiles:
        with pytest.raises(WorkspaceSettingsValidationError):
            service.create(profile)


def test_generation_profile_service_updates_and_protects_default_profile() -> (
    None
):
    existing = _profile(is_default=True)
    repository = _Profiles((existing,))
    service = GenerationProfileService(repository, _Identities())

    updated = service.update(replace(existing, name="Updated", archived=True))

    assert updated.name == "Updated"
    assert updated.archived is False
    assert updated.is_default is True
    with pytest.raises(
        WorkspaceSettingsValidationError,
        match="cannot be archived",
    ):
        service.set_archived(existing.profile_uid, True)

    non_default = _profile(profile_uid="other")
    repository.save(non_default)
    assert service.set_archived("other", True).archived is True


def test_workspace_preferences_service_validates_and_sets_default_profile() -> (
    None
):
    profile = _profile()
    profiles = _Profiles((profile,))
    repository = _Preferences(WorkspacePreferences())
    service = WorkspacePreferencesService(
        repository,
        profiles,
        curation_set_keys=("keep", "archive"),
    )

    saved = service.update(
        WorkspacePreferences(
            density="compact",
            motion="reduced",
            analytics_page_size=48,
            review_unrated_only=False,
            review_max_attempts=20,
            default_curation_set_key="keep",
            curation_set_order=("archive", "keep"),
            enabled_content_levels=(
                ContentLevel.STANDARD,
                ContentLevel.SEXY,
                ContentLevel.LEWD,
            ),
        )
    )
    selected = service.set_default_profile(profile.profile_uid)

    assert saved.density == "compact"
    assert saved.enabled_content_levels[-1] is ContentLevel.LEWD
    assert selected.default_generation_profile_uid == profile.profile_uid
    assert service.get() == selected

    profiles.save(replace(profile, archived=True))
    with pytest.raises(
        WorkspaceSettingsValidationError,
        match="archived profile",
    ):
        service.set_default_profile(profile.profile_uid)

    repository.value = WorkspacePreferences(
        default_generation_profile_uid=profile.profile_uid
    )
    with pytest.raises(
        WorkspaceSettingsValidationError,
        match="archived profile",
    ):
        service.get()


def test_workspace_preferences_service_rejects_unknown_or_duplicate_values() -> (
    None
):
    service = WorkspacePreferencesService(
        _Preferences(WorkspacePreferences()),
        _Profiles(),
        curation_set_keys=("keep",),
    )

    invalid_preferences = (
        WorkspacePreferences(density="wide"),
        WorkspacePreferences(motion="animated"),
        WorkspacePreferences(analytics_page_size=25),
        WorkspacePreferences(review_max_attempts=0),
        WorkspacePreferences(curation_set_order=("keep", "keep")),
        WorkspacePreferences(curation_set_order=("unknown",)),
        WorkspacePreferences(default_curation_set_key="unknown"),
        WorkspacePreferences(enabled_content_levels=(ContentLevel.SEXY,)),
        WorkspacePreferences(
            enabled_content_levels=(
                ContentLevel.STANDARD,
                ContentLevel.STANDARD,
            )
        ),
        WorkspacePreferences(
            enabled_content_levels=(
                ContentLevel.STANDARD,
                ContentLevel.LEWD,
                ContentLevel.SEXY,
            )
        ),
    )
    for preferences in invalid_preferences:
        with pytest.raises(WorkspaceSettingsValidationError):
            service.update(preferences)


def test_sqlite_settings_repositories_persist_profiles_and_preferences(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    profiles = SqliteGenerationProfileRepository(database_path)
    preferences = SqliteWorkspacePreferencesRepository(database_path)

    saved_profile = profiles.save(_profile())
    saved_preferences = preferences.save(
        WorkspacePreferences(
            density="compact",
            motion="reduced",
            analytics_page_size=12,
            default_generation_profile_uid=saved_profile.profile_uid,
            review_unrated_only=False,
            review_max_attempts=12,
            default_curation_set_key="keep",
            curation_set_order=("archive", "keep"),
            enabled_content_levels=(
                ContentLevel.STANDARD,
                ContentLevel.SEXY,
            ),
        )
    )

    assert saved_preferences.default_generation_profile_uid == "profile-one"
    assert saved_preferences.curation_set_order == ("archive", "keep")
    assert saved_preferences.enabled_content_levels == (
        ContentLevel.STANDARD,
        ContentLevel.SEXY,
    )
    assert profiles.get("profile-one").image_width == 1024
    assert profiles.get("profile-one").is_default is True
    archived = profiles.set_archived("profile-one", True)
    assert archived.archived is True
    assert profiles.list_profiles() == (archived,)


def test_sqlite_settings_repositories_reject_unknown_identities(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    profiles = SqliteGenerationProfileRepository(database_path)
    preferences = SqliteWorkspacePreferencesRepository(database_path)

    with pytest.raises(KeyError):
        profiles.get("missing")
    with pytest.raises(KeyError):
        profiles.set_archived("missing", True)
    with pytest.raises(KeyError):
        preferences.save(
            WorkspacePreferences(
                default_generation_profile_uid="missing",
            )
        )


def test_runtime_diagnostics_normalizes_connected_and_offline_states() -> None:
    configuration = RuntimeConfigurationSnapshot(
        comfyui_base_url="http://localhost:8188",
        output_root="output",
        workflows_directory="workflows",
        canonical_database_path="canonical.sqlite3",
        schema_version=9,
        runtime_mode="canonical",
        environment_variables=("COMFYREVIEW_DATABASE",),
    )
    connected = RuntimeDiagnosticsService(
        configuration,
        _ComfyUi(
            ComfyUiCapabilities(
                ("LoraLoader",),
                ("euler",),
                ("normal",),
                ("model.safetensors",),
                ("style.safetensors",),
            )
        ),
    ).inspect()
    offline = RuntimeDiagnosticsService(
        configuration,
        _ComfyUi(ComfyUiConnectionError("offline")),
    ).inspect()

    assert connected.connected is True
    assert connected.loras == ("style.safetensors",)
    assert offline.connected is False
    assert offline.message == "ComfyUiConnectionError"
    assert offline.configuration == configuration


def test_runtime_diagnostics_snapshot_avoids_provider_access() -> None:
    configuration = RuntimeConfigurationSnapshot(
        comfyui_base_url="http://127.0.0.1:8188",
        output_root="output",
        workflows_directory="workflows",
        canonical_database_path="canonical.sqlite3",
        schema_version=9,
        runtime_mode="canonical",
        environment_variables=("COMFYREVIEW_DATABASE",),
    )

    diagnostics = RuntimeDiagnosticsService(
        configuration,
        _UnexpectedComfyUi(),
    ).snapshot()

    assert diagnostics.configuration == configuration
    assert diagnostics.connected is False
    assert diagnostics.message == "not_checked"
    assert diagnostics.checkpoints == ()


def test_runtime_diagnostics_caches_capabilities_for_fast_snapshots() -> None:
    configuration = RuntimeConfigurationSnapshot(
        comfyui_base_url="http://127.0.0.1:8188",
        output_root="output",
        workflows_directory="workflows",
        canonical_database_path="canonical.sqlite3",
        schema_version=9,
        runtime_mode="canonical",
        environment_variables=("COMFYREVIEW_DATABASE",),
    )
    cache = _CapabilityCache()
    service = RuntimeDiagnosticsService(
        configuration,
        _ComfyUi(
            ComfyUiCapabilities(
                ("LoraLoader",),
                ("euler",),
                ("normal",),
                ("model.safetensors",),
                ("style.safetensors",),
            )
        ),
        cache,
    )

    assert service.inspect().connected is True
    snapshot = RuntimeDiagnosticsService(
        configuration,
        _UnexpectedComfyUi(),
        cache,
    ).snapshot()

    assert snapshot.connected is False
    assert snapshot.message == "cached"
    assert snapshot.checkpoints == ("model.safetensors",)
    assert snapshot.loras == ("style.safetensors",)
    assert (
        RuntimeDiagnosticsService(
            configuration,
            _ComfyUi(
                ComfyUiCapabilities((), (), (), (), ()),
            ),
            _FailingCapabilityCache(),
        )
        .inspect()
        .connected
        is True
    )
