"""Read-only runtime configuration and provider diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.comfyui import ComfyUiCapabilities, ComfyUiError


class RuntimeCapabilityProvider(Protocol):
    """Expose only the provider operation required by runtime diagnostics."""

    def discover_capabilities(self) -> ComfyUiCapabilities:
        """Return technical capabilities from the configured provider."""
        ...


class RuntimeCapabilityCache(Protocol):
    """Store the last usable provider capability snapshot."""

    def load(self) -> Mapping[str, object]:
        """Return cached technical capability values."""
        ...

    def save(self, capabilities: Mapping[str, object]) -> None:
        """Persist one technical capability snapshot."""
        ...


@dataclass(frozen=True, slots=True)
class RuntimeConfigurationSnapshot:
    """Expose safe runtime configuration without writable environment access."""

    comfyui_base_url: str
    output_root: str
    workflows_directory: str
    canonical_database_path: str
    schema_version: int
    runtime_mode: str
    environment_variables: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuntimeDiagnostics:
    """Describe configuration and the latest bounded ComfyUI check."""

    configuration: RuntimeConfigurationSnapshot
    connected: bool
    node_classes: tuple[str, ...]
    checkpoints: tuple[str, ...]
    samplers: tuple[str, ...]
    schedulers: tuple[str, ...]
    loras: tuple[str, ...]
    message: str
    upscale_models: tuple[str, ...] = ()


class RuntimeDiagnosticsService:
    """Read a safe configuration snapshot and technical provider status."""

    def __init__(
        self,
        configuration: RuntimeConfigurationSnapshot,
        comfyui: RuntimeCapabilityProvider,
        cache: RuntimeCapabilityCache | None = None,
    ) -> None:
        self._configuration = configuration
        self._comfyui = comfyui
        self._cache = cache

    def inspect(self) -> RuntimeDiagnostics:
        """Perform one bounded provider capability check."""
        try:
            capabilities = self._comfyui.discover_capabilities()
        except ComfyUiError as error:
            return self._cached(message=type(error).__name__)
        self._save(capabilities)
        return RuntimeDiagnostics(
            configuration=self._configuration,
            connected=True,
            node_classes=capabilities.node_classes,
            checkpoints=capabilities.checkpoints,
            samplers=capabilities.samplers,
            schedulers=capabilities.schedulers,
            loras=capabilities.loras,
            upscale_models=capabilities.upscale_models,
            message="connected",
        )

    def snapshot(self) -> RuntimeDiagnostics:
        """Return configuration immediately without an external provider call."""
        return self._cached(message="not_checked")

    def _cached(self, *, message: str) -> RuntimeDiagnostics:
        raw = self._cache.load() if self._cache is not None else {}
        cached = any(raw.get(name) for name in self._capability_names())
        return RuntimeDiagnostics(
            configuration=self._configuration,
            connected=False,
            node_classes=self._strings(raw.get("node_classes")),
            checkpoints=self._strings(raw.get("checkpoints")),
            samplers=self._strings(raw.get("samplers")),
            schedulers=self._strings(raw.get("schedulers")),
            loras=self._strings(raw.get("loras")),
            upscale_models=self._strings(raw.get("upscale_models")),
            message="cached"
            if cached and message == "not_checked"
            else message,
        )

    def _save(self, capabilities: ComfyUiCapabilities) -> None:
        if self._cache is None:
            return
        try:
            self._cache.save(
                {
                    name: list(getattr(capabilities, name))
                    for name in self._capability_names()
                }
            )
        except OSError:
            return

    @staticmethod
    def _capability_names() -> tuple[str, ...]:
        return (
            "node_classes",
            "checkpoints",
            "samplers",
            "schedulers",
            "loras",
            "upscale_models",
        )

    @staticmethod
    def _strings(value: object) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)):
            return ()
        return tuple(text for item in value if (text := str(item).strip()))
