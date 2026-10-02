"""Application contracts for workspace preferences and generation profiles."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol


class WorkspaceSettingsValidationError(ValueError):
    """Reject invalid workspace preferences or generation profiles."""


@dataclass(frozen=True, slots=True)
class GenerationLoraSelection:
    """Describe one ordered LoRA selection with independent strengths."""

    name: str
    model_strength_milli: int
    clip_strength_milli: int
    position: int


@dataclass(frozen=True, slots=True)
class GenerationProfile:
    """Describe reusable defaults for one canonical generation request."""

    profile_uid: str
    name: str
    blueprint_uid: str
    blueprint_version: int
    checkpoint: str
    sampler: str
    scheduler: str
    seed_mode: str
    fixed_seed: int | None
    steps_min: int
    steps_max: int
    cfg_min_milli: int
    cfg_max_milli: int
    denoise_milli: int
    batch_size: int
    loras: tuple[GenerationLoraSelection, ...] = ()
    archived: bool = False
    is_default: bool = False


@dataclass(frozen=True, slots=True)
class WorkspacePreferences:
    """Describe typed preferences that may be changed in the browser."""

    density: str = "comfortable"
    motion: str = "system"
    analytics_page_size: int = 24
    default_generation_profile_uid: str | None = None
    review_unrated_only: bool = True
    review_max_attempts: int = 50
    default_curation_set_key: str | None = None
    curation_set_order: tuple[str, ...] = ()


class PreferencesRepository(Protocol):
    """Persist the singleton workspace preference record."""

    def get(self) -> WorkspacePreferences:
        """Return current workspace preferences."""
        ...

    def save(self, preferences: WorkspacePreferences) -> WorkspacePreferences:
        """Persist and return validated workspace preferences."""
        ...


class GenerationProfileRepository(Protocol):
    """Persist reusable generation profiles and their ordered LoRAs."""

    def list_profiles(self) -> tuple[GenerationProfile, ...]:
        """Return every profile including archived historical profiles."""
        ...

    def get(self, profile_uid: str) -> GenerationProfile:
        """Return one profile by stable identity."""
        ...

    def save(self, profile: GenerationProfile) -> GenerationProfile:
        """Insert or update one profile without changing its identity."""
        ...

    def set_archived(
        self, profile_uid: str, archived: bool
    ) -> GenerationProfile:
        """Change only the profile lifecycle state."""
        ...


class GenerationProfileIdentitySource(Protocol):
    """Create opaque stable generation profile identities."""

    def new_profile_uid(self) -> str:
        """Return one globally unique profile identity."""
        ...


class WorkspacePreferencesService:
    """Validate and coordinate workspace preference changes."""

    def __init__(
        self,
        repository: PreferencesRepository,
        profiles: GenerationProfileRepository,
        *,
        curation_set_keys: tuple[str, ...],
    ) -> None:
        self._repository = repository
        self._profiles = profiles
        self._curation_set_keys = curation_set_keys

    def get(self) -> WorkspacePreferences:
        """Return the current validated preferences."""
        preferences = self._repository.get()
        self._validate(preferences)
        return preferences

    def update(
        self, preferences: WorkspacePreferences
    ) -> WorkspacePreferences:
        """Validate and persist one complete preference replacement."""
        self._validate(preferences)
        return self._repository.save(preferences)

    def set_default_profile(self, profile_uid: str) -> WorkspacePreferences:
        """Select one active profile as the workspace default."""
        profile = self._profiles.get(profile_uid)
        if profile.archived:
            raise WorkspaceSettingsValidationError(
                "archived profile cannot be the default"
            )
        current = self._repository.get()
        updated = replace(
            current,
            default_generation_profile_uid=profile.profile_uid,
        )
        self._validate(updated)
        return self._repository.save(updated)

    def _validate(self, preferences: WorkspacePreferences) -> None:
        if preferences.density not in {"comfortable", "compact"}:
            raise WorkspaceSettingsValidationError("invalid density")
        if preferences.motion not in {"system", "reduced"}:
            raise WorkspaceSettingsValidationError("invalid motion")
        if preferences.analytics_page_size not in {12, 24, 48}:
            raise WorkspaceSettingsValidationError(
                "invalid analytics page size"
            )
        if preferences.review_max_attempts < 1:
            raise WorkspaceSettingsValidationError(
                "review attempts must be positive"
            )
        if len(set(preferences.curation_set_order)) != len(
            preferences.curation_set_order
        ):
            raise WorkspaceSettingsValidationError(
                "curation set order contains duplicates"
            )
        allowed_sets = set(self._curation_set_keys)
        if not set(preferences.curation_set_order) <= allowed_sets:
            raise WorkspaceSettingsValidationError(
                "curation set order contains unknown keys"
            )
        if (
            preferences.default_curation_set_key is not None
            and preferences.default_curation_set_key not in allowed_sets
        ):
            raise WorkspaceSettingsValidationError(
                "default curation set is unknown"
            )
        if preferences.default_generation_profile_uid is not None:
            profile = self._profiles.get(
                preferences.default_generation_profile_uid
            )
            if profile.archived:
                raise WorkspaceSettingsValidationError(
                    "archived profile cannot be the default"
                )


class GenerationProfileService:
    """Validate profile settings and preserve ordered LoRA selections."""

    def __init__(
        self,
        repository: GenerationProfileRepository,
        identities: GenerationProfileIdentitySource,
    ) -> None:
        self._repository = repository
        self._identities = identities

    def list_profiles(self) -> tuple[GenerationProfile, ...]:
        """Return profiles with repository-defined deterministic ordering."""
        return self._repository.list_profiles()

    def create(self, profile: GenerationProfile) -> GenerationProfile:
        """Create a profile with a server-owned stable identity."""
        created = replace(
            profile,
            profile_uid=self._identities.new_profile_uid(),
            archived=False,
            is_default=False,
        )
        self._validate(created)
        return self._repository.save(created)

    def update(self, profile: GenerationProfile) -> GenerationProfile:
        """Update profile defaults while preserving its stable identity."""
        existing = self._repository.get(profile.profile_uid)
        updated = replace(
            profile,
            archived=existing.archived,
            is_default=existing.is_default,
        )
        self._validate(updated)
        return self._repository.save(updated)

    def set_archived(
        self, profile_uid: str, archived: bool
    ) -> GenerationProfile:
        """Archive or restore one non-default profile."""
        existing = self._repository.get(profile_uid)
        if archived and existing.is_default:
            raise WorkspaceSettingsValidationError(
                "default profile cannot be archived"
            )
        return self._repository.set_archived(profile_uid, archived)

    @staticmethod
    def _validate(profile: GenerationProfile) -> None:
        required_text = (
            profile.name,
            profile.blueprint_uid,
            profile.checkpoint,
            profile.sampler,
            profile.scheduler,
        )
        if any(not value.strip() for value in required_text):
            raise WorkspaceSettingsValidationError(
                "profile text values must not be empty"
            )
        if profile.blueprint_version < 1:
            raise WorkspaceSettingsValidationError(
                "blueprint version must be positive"
            )
        if profile.seed_mode not in {"fixed", "random"}:
            raise WorkspaceSettingsValidationError("invalid seed mode")
        if profile.seed_mode == "fixed" and profile.fixed_seed is None:
            raise WorkspaceSettingsValidationError(
                "fixed seed mode requires a seed"
            )
        if profile.steps_min < 1 or profile.steps_min > profile.steps_max:
            raise WorkspaceSettingsValidationError("invalid steps range")
        if profile.cfg_min_milli < 1 or (
            profile.cfg_min_milli > profile.cfg_max_milli
        ):
            raise WorkspaceSettingsValidationError("invalid CFG range")
        if not 0 <= profile.denoise_milli <= 1000:
            raise WorkspaceSettingsValidationError("invalid denoise")
        if profile.batch_size < 1:
            raise WorkspaceSettingsValidationError(
                "batch size must be positive"
            )
        expected_positions = tuple(range(len(profile.loras)))
        if (
            tuple(item.position for item in profile.loras)
            != expected_positions
        ):
            raise WorkspaceSettingsValidationError(
                "LoRA positions must be contiguous"
            )
        names = tuple(item.name.strip() for item in profile.loras)
        if any(not name for name in names) or len(set(names)) != len(names):
            raise WorkspaceSettingsValidationError(
                "LoRA names must be non-empty and unique"
            )
        for lora in profile.loras:
            if not -10_000 <= lora.model_strength_milli <= 10_000:
                raise WorkspaceSettingsValidationError(
                    "invalid LoRA model strength"
                )
            if not -10_000 <= lora.clip_strength_milli <= 10_000:
                raise WorkspaceSettingsValidationError(
                    "invalid LoRA CLIP strength"
                )
