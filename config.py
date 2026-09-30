"""Compatibility exports backed by typed ComfyReview settings."""

from comfyreview.settings import Settings, load_settings

SETTINGS: Settings = load_settings()

APP_HOST = SETTINGS.app_host
APP_PORT = SETTINGS.app_port
OUTPUT_ROOT = SETTINGS.output_root
POOL_LIMIT = SETTINGS.pool_limit
MIN_RUNS = SETTINGS.minimum_runs
CURATION_SET_KEYS = list(SETTINGS.curation_set_keys)
DEFAULT_MAX_TRIES = SETTINGS.default_max_tries
DEFAULT_UNRATED_ONLY = SETTINGS.default_unrated_only
SOFT_DELETE_TO_TRASH = SETTINGS.soft_delete_to_trash
SSL_ENABLED = SETTINGS.ssl_enabled
SSL_CERTFILE = SETTINGS.ssl_certificate_path
SSL_KEYFILE = SETTINGS.ssl_key_path
