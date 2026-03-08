from pathlib import Path
import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return float(value)


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default.resolve()
    return Path(value).expanduser().resolve()


BASE_DIR = Path(__file__).resolve().parent

# =============================
# App
# =============================
APP_HOST = os.getenv("COMFYREVIEW_HOST", "127.0.0.1")
APP_PORT = _env_int("COMFYREVIEW_PORT", 8000)

# =============================
# Paths
# =============================
OUTPUT_ROOT = _env_path("COMFYREVIEW_OUTPUT_ROOT", BASE_DIR / "output")
TRASH_ROOT = OUTPUT_ROOT / "_trash"

DATA_DIR = _env_path("COMFYREVIEW_DATA_DIR", BASE_DIR / "data")
TEMPLATES_DIR = BASE_DIR / "templates"

# Create local runtime dirs so startup does not fail on fresh clones.
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
TRASH_ROOT.mkdir(parents=True, exist_ok=True)

# =============================
# vNext constants
# =============================
# runs means "number of real ratings" (rating IS NOT NULL, deleted=0)
POOL_LIMIT = _env_int("COMFYREVIEW_POOL_LIMIT", 128)
MIN_RUNS = _env_int("COMFYREVIEW_MIN_RUNS", 3)

# MV Worker
MV_DEBOUNCE_SECONDS = _env_int("COMFYREVIEW_MV_DEBOUNCE_SECONDS", 20)

# =============================
# vNext: LoRA curation
# =============================
CURATION_DB_PATH = _env_path("COMFYREVIEW_CURATION_DB", DATA_DIR / "curation.sqlite3")

# Export root for LoRA dataset copies.
# This folder is inside OUTPUT_ROOT, but the scanner is expected to ignore it.
LORA_EXPORT_ROOT = _env_path("COMFYREVIEW_LORA_EXPORT_ROOT", OUTPUT_ROOT / "_lora_export")
LORA_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)

# Allowed curation set keys (single label)
CURATION_SET_KEYS = [
    "character_face",
    "character_body",
    "scene",
    "outfit",
    "pose",
    "expression",
]

# =============================
# Databases
# =============================
MV_QUEUE_DB_PATH = _env_path("COMFYREVIEW_MV_QUEUE_DB", DATA_DIR / "mv_jobs.sqlite3")

DB_PATH = _env_path("COMFYREVIEW_RATINGS_DB", BASE_DIR / "ratings.sqlite3")
PROMPT_DB_PATH = _env_path("COMFYREVIEW_PROMPT_TOKENS_DB", BASE_DIR / "prompt_tokens.sqlite3")
ARENA_DB_PATH = _env_path("COMFYREVIEW_ARENA_DB", BASE_DIR / "arena.sqlite3")

PLAYGROUND_DB_PATH = _env_path("COMFYREVIEW_PLAYGROUND_DB", DATA_DIR / "playground.sqlite3")
COMBO_PROMPTS_DB_PATH = _env_path("COMFYREVIEW_COMBO_DB", DATA_DIR / "combo_prompts.sqlite3")
IMAGES_DB_PATH = _env_path("COMFYREVIEW_IMAGES_DB", DATA_DIR / "images.sqlite3")
PROMPT_RATINGS_DB_PATH = _env_path("COMFYREVIEW_PROMPT_RATINGS_DB", DATA_DIR / "prompt_ratings.sqlite3")
PROMPT_TOKENS_DB_PATH = PROMPT_DB_PATH

DEFAULT_MAX_TRIES = _env_int("COMFYREVIEW_DEFAULT_MAX_TRIES", 50)
DEFAULT_UNRATED_ONLY = _env_bool("COMFYREVIEW_DEFAULT_UNRATED_ONLY", False)
SOFT_DELETE_TO_TRASH = _env_bool("COMFYREVIEW_SOFT_DELETE_TO_TRASH", False)

# =============================
# Playground
# =============================
# Master switch for the Playground Rules Engine
PLAYGROUND_RULES_ENABLED = _env_bool("COMFYREVIEW_PLAYGROUND_RULES_ENABLED", False)

# =============================
# ComfyUI Bridge
# =============================
COMFYUI_BASE_URL = os.getenv("COMFYREVIEW_COMFYUI_BASE_URL", "http://127.0.0.1:8188")

WORKFLOWS_DIR = _env_path("COMFYREVIEW_WORKFLOWS_DIR", DATA_DIR / "workflows")
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_WORKFLOW_PATH = _env_path(
    "COMFYREVIEW_DEFAULT_WORKFLOW",
    WORKFLOWS_DIR / "_default_character.json",
)

COMFYUI_CHECKPOINTS_DIR = _env_path(
    "COMFYREVIEW_CHECKPOINTS_DIR",
    BASE_DIR / "comfyui_checkpoints",
)
COMFYUI_CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

# =============================
# SSL / HTTPS
# =============================
SSL_ENABLED = _env_bool("COMFYREVIEW_SSL_ENABLED", False)
SSL_CERTFILE = _env_path("COMFYREVIEW_SSL_CERTFILE", BASE_DIR / "certs" / "server.pem")
SSL_KEYFILE = _env_path("COMFYREVIEW_SSL_KEYFILE", BASE_DIR / "certs" / "server-key.pem")