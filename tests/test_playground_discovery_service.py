"""Tests for native ComfyUI capability discovery in Playground."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from comfyreview.application import (
    ComfyUiCapabilities,
    ComfyUiConnectionError,
    ComfyUiProvider,
)
from comfyreview.repositories.filesystem import JsonComfyUiCapabilityCache
from services.playground_discovery_service import PlaygroundDiscoveryService


class _Provider:
    def __init__(self, result: ComfyUiCapabilities | Exception) -> None:
        self.result = result

    def discover_capabilities(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _service(
    provider: _Provider, cache_path: Path
) -> PlaygroundDiscoveryService:
    return PlaygroundDiscoveryService(
        cast(ComfyUiProvider, provider),
        JsonComfyUiCapabilityCache(cache_path),
    )


def test_playground_discovery_uses_native_capabilities_and_refreshes_cache(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "capabilities.json"
    service = _service(
        _Provider(
            ComfyUiCapabilities(
                ("SaveImage",),
                ("euler",),
                ("normal",),
                ("model.safetensors",),
                ("style.safetensors",),
            )
        ),
        cache_path,
    )

    result = service.discover()

    assert result.checkpoints == ["model.safetensors"]
    assert result.samplers == ["euler"]
    assert result.loras == ["style.safetensors"]
    assert cache_path.is_file()


def test_playground_discovery_falls_back_to_clean_cached_lists(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "capabilities.json"
    cache_path.write_text(
        '{"checkpoints":[" model ",""],"samplers":["euler"],'
        '"schedulers":"invalid"}',
        encoding="utf-8",
    )
    offline = _service(
        _Provider(ComfyUiConnectionError("offline")),
        cache_path,
    )
    empty = _service(
        _Provider(ComfyUiCapabilities((), (), (), (), ())),
        cache_path,
    )

    assert offline.discover().checkpoints == ["model"]
    assert offline.discover().schedulers == []
    assert empty.discover().samplers == ["euler"]


def test_playground_discovery_ignores_cache_write_failure(
    tmp_path: Path,
) -> None:
    del tmp_path

    class _ReadOnlyCache:
        def load(self):
            return {}

        def save(self, capabilities):
            del capabilities
            raise OSError("readonly")

    service = PlaygroundDiscoveryService(
        cast(
            ComfyUiProvider,
            _Provider(ComfyUiCapabilities((), ("euler",), (), (), ())),
        ),
        _ReadOnlyCache(),
    )

    assert service.discover().samplers == ["euler"]
