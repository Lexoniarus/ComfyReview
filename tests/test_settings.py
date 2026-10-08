"""Behavior tests for typed, side-effect-free settings."""

from __future__ import annotations

import os
from pathlib import Path

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
