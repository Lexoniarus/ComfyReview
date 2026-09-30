"""Opaque identity provider for canonical prompt components."""

from uuid import uuid4


class UuidPromptIdentitySource:
    """Create UUID-backed prompt component identities."""

    def new_component_uid(self) -> str:
        """Return one opaque component UID."""
        return f"prompt-component-{uuid4()}"
