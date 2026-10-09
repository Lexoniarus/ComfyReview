"""Application contracts for local-model discovery and lifecycle control."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LocalModelError(RuntimeError):
    """Base class for normalized local-model boundary failures."""


class LocalModelConnectionError(LocalModelError):
    """Report that the local model server cannot be reached."""


class LocalModelTimeoutError(LocalModelError):
    """Report that a bounded operation exceeded its deadline."""


class LocalModelUnavailableError(LocalModelError):
    """Report that a requested model is not available."""


class LocalModelProtocolError(LocalModelError):
    """Report a provider response that cannot be normalized."""


class LocalModelLifecycleError(LocalModelError):
    """Report a defined failure to load or unload a model instance."""


@dataclass(frozen=True, slots=True)
class LocalModelInstance:
    """Identify one concrete loaded instance of a local model."""

    model_id: str
    instance_id: str


@dataclass(frozen=True, slots=True)
class LocalModelDescriptor:
    """Describe one available model and its already loaded instances."""

    model_id: str
    loaded_instances: tuple[LocalModelInstance, ...] = ()


class LocalModelProvider(Protocol):
    """Expose normalized local-model discovery and lifecycle operations."""

    def list_models(self) -> tuple[LocalModelDescriptor, ...]:
        """List models together with their currently loaded instances."""
        ...

    def load_model(self, model_id: str) -> LocalModelInstance:
        """Load one model and identify its concrete instance."""
        ...

    def unload_model(self, instance: LocalModelInstance) -> None:
        """Unload one specific loaded instance."""
        ...
