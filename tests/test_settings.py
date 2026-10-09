"""Behavior tests for typed, side-effect-free settings."""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from comfyreview.settings import (
    load_legacy_migration_settings,
    load_settings,
)


def test_load_settings_uses_documented_defaults_without_writes(
    tmp_path: Path,
) -> None:
    settings = load_settings(base_directory=tmp_path, environ={})

    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 8000
    assert settings.output_root == (tmp_path / "output").resolve()
    assert settings.trash_root == settings.output_root / "_trash"
    assert settings.data_directory == (tmp_path / "data").resolve()
    expected_database = (tmp_path / "data" / "comfyreview.sqlite3").resolve()
    assert settings.canonical_database_path == expected_database
    assert settings.pool_limit == 128
    assert settings.default_unrated_only is False
    assert settings.soft_delete_to_trash is False
    assert settings.ssl_enabled is False
    assert settings.lm_studio_base_url == "http://127.0.0.1:1234"
    assert settings.lm_studio_vision_model == ""
    assert settings.lm_studio_text_model == ""
    assert settings.lm_studio_request_timeout_seconds == 120.0
    assert settings.lm_studio_lifecycle_timeout_seconds == 180.0
    assert not settings.output_root.exists()
    assert not settings.data_directory.exists()


def test_environment_overrides_env_file_without_mutating_process(
    tmp_path: Path,
) -> None:
    custom_output = tmp_path / "comfy output"
    custom_database = tmp_path / "runtime" / "canonical.sqlite3"
    env_file = tmp_path / "settings.env"
    env_file.write_text(
        "\n".join(
            (
                "# comment",
                "not-an-assignment",
                "=ignored",
                "COMFYREVIEW_HOST='env-file-host'",
                "COMFYREVIEW_PORT=9000",
                'COMFYREVIEW_COMFYUI_BASE_URL="http://example.test:8188"',
                "COMFYREVIEW_OUTPUT_ROOT=ignored-output",
                "COMFYREVIEW_DATA_DIR=",
                "COMFYREVIEW_DATABASE=ignored.sqlite3",
                "COMFYREVIEW_POOL_LIMIT=64",
                "COMFYREVIEW_DEFAULT_MAX_TRIES=12",
                "COMFYREVIEW_DEFAULT_UNRATED_ONLY=yes",
                "COMFYREVIEW_SOFT_DELETE_TO_TRASH=off",
                'COMFYREVIEW_LM_STUDIO_BASE_URL="http://file.test:1234"',
                "COMFYREVIEW_LM_STUDIO_VISION_MODEL=file-vision",
                "COMFYREVIEW_LM_STUDIO_TEXT_MODEL=file-text",
                "COMFYREVIEW_LM_STUDIO_REQUEST_TIMEOUT_SECONDS=90",
                "COMFYREVIEW_LM_STUDIO_LIFECYCLE_TIMEOUT_SECONDS=240",
                "COMFYREVIEW_SSL_ENABLED=true",
            )
        ),
        encoding="utf-8",
    )
    environment = {
        "COMFYREVIEW_PORT": "8123",
        "COMFYREVIEW_OUTPUT_ROOT": str(custom_output),
        "COMFYREVIEW_DATABASE": str(custom_database),
        "COMFYREVIEW_RATINGS_DB": "",
        "COMFYREVIEW_LM_STUDIO_BASE_URL": "http://127.0.0.1:5678",
        "COMFYREVIEW_LM_STUDIO_VISION_MODEL": "env-vision",
        "COMFYREVIEW_LM_STUDIO_REQUEST_TIMEOUT_SECONDS": "45.5",
    }
    process_environment = dict(os.environ)

    settings = load_settings(
        base_directory=tmp_path,
        environ=environment,
        env_file=env_file,
    )

    assert settings.app_host == "env-file-host"
    assert settings.app_port == 8123
    assert settings.comfyui_base_url == "http://example.test:8188"
    assert settings.lm_studio_base_url == "http://127.0.0.1:5678"
    assert settings.lm_studio_vision_model == "env-vision"
    assert settings.lm_studio_text_model == "file-text"
    assert settings.lm_studio_request_timeout_seconds == 45.5
    assert settings.lm_studio_lifecycle_timeout_seconds == 240.0
    assert settings.output_root == custom_output.resolve()
    assert settings.data_directory == (tmp_path / "data").resolve()
    assert settings.canonical_database_path == custom_database.resolve()
    assert settings.pool_limit == 64
    assert settings.default_max_tries == 12
    assert settings.default_unrated_only is True
    assert settings.soft_delete_to_trash is False
    assert settings.ssl_enabled is True
    assert dict(os.environ) == process_environment


def test_legacy_migration_settings_are_loaded_separately(
    tmp_path: Path,
) -> None:
    legacy = load_legacy_migration_settings(
        base_directory=tmp_path,
        environ={"COMFYREVIEW_RATINGS_DB": "archive/ratings.sqlite3"},
    )
    runtime = load_settings(base_directory=tmp_path, environ={})

    assert (
        legacy.ratings_database_path
        == Path("archive/ratings.sqlite3").resolve()
    )
    assert (
        legacy.playground_database_path
        == (tmp_path / "data" / "playground.sqlite3").resolve()
    )
    assert not hasattr(runtime, "ratings_database_path")


def test_default_environment_source_is_read_only(tmp_path: Path) -> None:
    before = dict(os.environ)

    settings = load_settings(
        base_directory=tmp_path,
        env_file=tmp_path / "missing.env",
    )

    assert settings.base_directory == tmp_path.resolve()
    assert dict(os.environ) == before


@pytest.mark.parametrize(
    "environment_name",
    (
        "COMFYREVIEW_LM_STUDIO_REQUEST_TIMEOUT_SECONDS",
        "COMFYREVIEW_LM_STUDIO_LIFECYCLE_TIMEOUT_SECONDS",
    ),
)
@pytest.mark.parametrize("invalid_value", ("0", "-1", "inf", "nan"))
def test_lm_studio_timeout_must_be_positive_and_finite(
    tmp_path: Path, environment_name: str, invalid_value: str
) -> None:
    with pytest.raises(ValueError, match=environment_name):
        load_settings(
            base_directory=tmp_path,
            environ={environment_name: invalid_value},
        )


def test_lm_studio_settings_do_not_connect_to_a_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbid_connect(_socket: socket.socket, _address: object) -> None:
        raise AssertionError("Settings loading must not access the network")

    monkeypatch.setattr(socket.socket, "connect", forbid_connect)
    settings = load_settings(
        base_directory=tmp_path,
        environ={"COMFYREVIEW_LM_STUDIO_VISION_MODEL": "local-vision"},
    )

    assert settings.lm_studio_vision_model == "local-vision"
