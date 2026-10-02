"""Read-only runtime configuration and provider diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.comfyui import ComfyUiCapabilities, ComfyUiError


class RuntimeCapabilityProvider(Protocol):
    """Expose only the provider operation required by runtime diagnostics."""

    def discover_capabilities(self) -> ComfyUiCapabilities:
        """Return technical capabilities from the configured provider."""
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


class RuntimeDiagnosticsService:
    """Read a safe configuration snapshot and technical provider status."""

    def __init__(
        self,
        configuration: RuntimeConfigurationSnapshot,
        comfyui: RuntimeCapabilityProvider,
    ) -> None:
        self._configuration = configuration
        self._comfyui = comfyui

    def inspect(self) -> RuntimeDiagnostics:
        """Perform one bounded provider capability check."""
        try:
            capabilities = self._comfyui.discover_capabilities()
        except ComfyUiError as error:
            return RuntimeDiagnostics(
                configuration=self._configuration,
                connected=False,
                node_classes=(),
                checkpoints=(),
                samplers=(),
                schedulers=(),
                loras=(),
                message=type(error).__name__,
            )
        return RuntimeDiagnostics(
            configuration=self._configuration,
            connected=True,
            node_classes=capabilities.node_classes,
            checkpoints=capabilities.checkpoints,
            samplers=capabilities.samplers,
            schedulers=capabilities.schedulers,
            loras=capabilities.loras,
            message="connected",
        )
