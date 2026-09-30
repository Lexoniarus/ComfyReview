"""Compatibility exports backed by typed ComfyReview settings."""

from comfyreview.settings import Settings, load_settings

SETTINGS: Settings = load_settings()

APP_HOST = SETTINGS.app_host
APP_PORT = SETTINGS.app_port
OUTPUT_ROOT = SETTINGS.output_root
TRASH_ROOT = SETTINGS.trash_root
DATA_DIR = SETTINGS.data_directory
CANONICAL_DB_PATH = SETTINGS.canonical_database_path
TEMPLATES_DIR = SETTINGS.templates_directory
POOL_LIMIT = SETTINGS.pool_limit
MIN_RUNS = SETTINGS.minimum_runs
MV_DEBOUNCE_SECONDS = SETTINGS.worker_debounce_seconds
WORKER_SHUTDOWN_TIMEOUT_SECONDS = SETTINGS.worker_shutdown_timeout_seconds
CURATION_DB_PATH = SETTINGS.curation_database_path
LORA_EXPORT_ROOT = SETTINGS.lora_export_root
CURATION_SET_KEYS = list(SETTINGS.curation_set_keys)
MV_QUEUE_DB_PATH = SETTINGS.worker_queue_database_path
DB_PATH = SETTINGS.canonical_database_path
PROMPT_DB_PATH = SETTINGS.canonical_database_path
PROMPT_TOKENS_DB_PATH = SETTINGS.canonical_database_path
ARENA_DB_PATH = SETTINGS.arena_database_path
PLAYGROUND_DB_PATH = SETTINGS.playground_database_path
COMBO_PROMPTS_DB_PATH = SETTINGS.combo_prompts_database_path
IMAGES_DB_PATH = SETTINGS.images_database_path
PROMPT_RATINGS_DB_PATH = SETTINGS.prompt_ratings_database_path
DEFAULT_MAX_TRIES = SETTINGS.default_max_tries
DEFAULT_UNRATED_ONLY = SETTINGS.default_unrated_only
SOFT_DELETE_TO_TRASH = SETTINGS.soft_delete_to_trash
COMFYUI_BASE_URL = SETTINGS.comfyui_base_url
WORKFLOWS_DIR = SETTINGS.workflows_directory
COMFYUI_CHECKPOINTS_DIR = SETTINGS.comfyui_checkpoints_directory
SSL_ENABLED = SETTINGS.ssl_enabled
SSL_CERTFILE = SETTINGS.ssl_certificate_path
SSL_KEYFILE = SETTINGS.ssl_key_path
