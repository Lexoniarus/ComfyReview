"""Typed, side-effect-free application configuration loading."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_CURATION_SET_KEYS = (
    "character_face",
    "character_body",
    "scene",
    "outfit",
    "pose",
    "expression",
)


@dataclass(frozen=True)
class Settings:
    """Contain environment-derived settings required by the live runtime."""

    base_directory: Path
    app_host: str
    app_port: int
    output_root: Path
    trash_root: Path
    data_directory: Path
    canonical_database_path: Path
    templates_directory: Path
    pool_limit: int
    minimum_runs: int
    lora_export_root: Path
    curation_set_keys: tuple[str, ...]
    default_max_tries: int
    default_unrated_only: bool
    soft_delete_to_trash: bool
    comfyui_base_url: str
    workflows_directory: Path
    comfyui_checkpoints_directory: Path
    ssl_enabled: bool
    ssl_certificate_path: Path
    ssl_key_path: Path


@dataclass(frozen=True)
class LegacyMigrationSettings:
    """Contain database paths used only by explicit legacy maintenance."""

    data_directory: Path
    ratings_database_path: Path
    prompt_tokens_database_path: Path
    arena_database_path: Path
    curation_database_path: Path
    playground_database_path: Path
    combo_prompts_database_path: Path
    images_database_path: Path
    prompt_ratings_database_path: Path
    worker_queue_database_path: Path


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {'"', "'"}
        ):
            value = value[1:-1]
        values[name] = value
    return values


def _integer(values: Mapping[str, str], name: str, default: int) -> int:
    value = values.get(name)
    return default if value is None or not value.strip() else int(value)


def _boolean(values: Mapping[str, str], name: str, default: bool) -> bool:
    value = values.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _path(values: Mapping[str, str], name: str, default: Path) -> Path:
    value = values.get(name)
    if value is None or not value.strip():
        return default.resolve()
    return Path(value).expanduser().resolve()


def _base_path(base_directory: Path | None) -> Path:
    """Resolve the configuration base without changing process state."""
    if base_directory is not None:
        return Path(base_directory).resolve()
    return Path(__file__).resolve().parents[1]


def _configuration_values(
    *,
    base: Path,
    environ: Mapping[str, str] | None,
    env_file: Path | None,
) -> dict[str, str]:
    """Merge defaults-file values with the selected environment mapping."""
    file_path = Path(env_file) if env_file is not None else base / ".env"
    values = _read_env_file(file_path)
    values.update(dict(os.environ if environ is None else environ))
    return values


def load_settings(
    *,
    base_directory: Path | None = None,
    environ: Mapping[str, str] | None = None,
    env_file: Path | None = None,
) -> Settings:
    """Load typed settings without mutating process environment or files."""
    base = _base_path(base_directory)
    values = _configuration_values(
        base=base,
        environ=environ,
        env_file=env_file,
    )

    output_root = _path(values, "COMFYREVIEW_OUTPUT_ROOT", base / "output")
    data_directory = _path(values, "COMFYREVIEW_DATA_DIR", base / "data")
    canonical_database_path = _path(
        values,
        "COMFYREVIEW_DATABASE",
        data_directory / "comfyreview.sqlite3",
    )
    workflows_directory = _path(
        values,
        "COMFYREVIEW_WORKFLOWS_DIR",
        data_directory / "workflows",
    )
    return Settings(
        base_directory=base,
        app_host=values.get("COMFYREVIEW_HOST", "127.0.0.1"),
        app_port=_integer(values, "COMFYREVIEW_PORT", 8000),
        output_root=output_root,
        trash_root=output_root / "_trash",
        data_directory=data_directory,
        canonical_database_path=canonical_database_path,
        templates_directory=base / "templates",
        pool_limit=_integer(values, "COMFYREVIEW_POOL_LIMIT", 128),
        minimum_runs=_integer(values, "COMFYREVIEW_MIN_RUNS", 3),
        lora_export_root=_path(
            values,
            "COMFYREVIEW_LORA_EXPORT_ROOT",
            output_root / "_lora_export",
        ),
        curation_set_keys=_CURATION_SET_KEYS,
        default_max_tries=_integer(
            values,
            "COMFYREVIEW_DEFAULT_MAX_TRIES",
            50,
        ),
        default_unrated_only=_boolean(
            values,
            "COMFYREVIEW_DEFAULT_UNRATED_ONLY",
            False,
        ),
        soft_delete_to_trash=_boolean(
            values,
            "COMFYREVIEW_SOFT_DELETE_TO_TRASH",
            False,
        ),
        comfyui_base_url=values.get(
            "COMFYREVIEW_COMFYUI_BASE_URL",
            "http://127.0.0.1:8188",
        ),
        workflows_directory=workflows_directory,
        comfyui_checkpoints_directory=_path(
            values,
            "COMFYREVIEW_CHECKPOINTS_DIR",
            base / "comfyui_checkpoints",
        ),
        ssl_enabled=_boolean(values, "COMFYREVIEW_SSL_ENABLED", False),
        ssl_certificate_path=_path(
            values,
            "COMFYREVIEW_SSL_CERTFILE",
            base / "certs" / "server.pem",
        ),
        ssl_key_path=_path(
            values,
            "COMFYREVIEW_SSL_KEYFILE",
            base / "certs" / "server-key.pem",
        ),
    )


def load_legacy_migration_settings(
    *,
    base_directory: Path | None = None,
    environ: Mapping[str, str] | None = None,
    env_file: Path | None = None,
) -> LegacyMigrationSettings:
    """Load paths used exclusively by explicit legacy maintenance commands."""
    base = _base_path(base_directory)
    values = _configuration_values(
        base=base,
        environ=environ,
        env_file=env_file,
    )
    data_directory = _path(values, "COMFYREVIEW_DATA_DIR", base / "data")
    return LegacyMigrationSettings(
        data_directory=data_directory,
        ratings_database_path=_path(
            values,
            "COMFYREVIEW_RATINGS_DB",
            base / "ratings.sqlite3",
        ),
        prompt_tokens_database_path=_path(
            values,
            "COMFYREVIEW_PROMPT_TOKENS_DB",
            base / "prompt_tokens.sqlite3",
        ),
        arena_database_path=_path(
            values,
            "COMFYREVIEW_ARENA_DB",
            base / "arena.sqlite3",
        ),
        curation_database_path=_path(
            values,
            "COMFYREVIEW_CURATION_DB",
            data_directory / "curation.sqlite3",
        ),
        playground_database_path=_path(
            values,
            "COMFYREVIEW_PLAYGROUND_DB",
            data_directory / "playground.sqlite3",
        ),
        combo_prompts_database_path=_path(
            values,
            "COMFYREVIEW_COMBO_DB",
            data_directory / "combo_prompts.sqlite3",
        ),
        images_database_path=_path(
            values,
            "COMFYREVIEW_IMAGES_DB",
            data_directory / "images.sqlite3",
        ),
        prompt_ratings_database_path=_path(
            values,
            "COMFYREVIEW_PROMPT_RATINGS_DB",
            data_directory / "prompt_ratings.sqlite3",
        ),
        worker_queue_database_path=_path(
            values,
            "COMFYREVIEW_MV_QUEUE_DB",
            data_directory / "mv_jobs.sqlite3",
        ),
    )
