"""Opaque identity provider for canonical prompt components."""

from uuid import uuid4


class UuidPromptIdentitySource:
    """Create UUID-backed prompt component identities."""

    def new_component_uid(self) -> str:
        """Return one opaque component UID."""
        return f"prompt-component-{uuid4()}"


class UuidGenerationIdentitySource:
    """Create opaque UUID-backed generation identities."""

    def new_generation_uid(self) -> str:
        """Return one canonical generation UID."""
        return f"generation-{uuid4()}"


class UuidGenerationProfileIdentitySource:
    """Create opaque UUID-backed generation profile identities."""

    def new_profile_uid(self) -> str:
        """Return one canonical generation profile UID."""
        return f"generation-profile-{uuid4()}"
