from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

APP_HOST = "0.0.0.0"
APP_PORT = 443

OUTPUT_ROOT = Path(r"C:\Users\Alexa\PycharmProjects\ComfyUI\output")
TRASH_ROOT = OUTPUT_ROOT / "_trash"

# =============================
# vNext constants
# =============================
# NOTE: runs means "number of real ratings" (rating IS NOT NULL, deleted=0)
POOL_LIMIT = 128
MIN_RUNS = 3

# MV Worker
# Debounce window for catchup jobs. The worker waits for a quiet period before
# running expensive rebuild logic. Each new rating "touches" the pending catchup
# job and restarts the countdown.
MV_DEBOUNCE_SECONDS = 20

TEMPLATES_DIR = BASE_DIR / "templates"

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# =============================
# vNext: LoRA curation
# =============================
CURATION_DB_PATH = DATA_DIR / "curation.sqlite3"

# vNext: export root for LoRA dataset copies.
# IMPORTANT: This folder is inside OUTPUT_ROOT, but the scanner ignores it.
LORA_EXPORT_ROOT = OUTPUT_ROOT / "_lora_export"

# vNext: allowed curation set keys (single label)
# Character is subdivided into face/body.
CURATION_SET_KEYS = [
    "character_face",
    "character_body",
    "scene",
    "outfit",
    "pose",
    "expression",
]

MV_QUEUE_DB_PATH = DATA_DIR / "mv_jobs.sqlite3"

DB_PATH = BASE_DIR / "ratings.sqlite3"
PROMPT_DB_PATH = BASE_DIR / "prompt_tokens.sqlite3"
ARENA_DB_PATH = BASE_DIR / "arena.sqlite3"

PLAYGROUND_DB_PATH = DATA_DIR / "playground.sqlite3"
COMBO_PROMPTS_DB_PATH = DATA_DIR / "combo_prompts.sqlite3"
IMAGES_DB_PATH = DATA_DIR / "images.sqlite3"
PROMPT_RATINGS_DB_PATH = DATA_DIR / "prompt_ratings.sqlite3"
PROMPT_TOKENS_DB_PATH = PROMPT_DB_PATH
DEFAULT_MAX_TRIES = 50
DEFAULT_UNRATED_ONLY = False
SOFT_DELETE_TO_TRASH = False

# Playground
# Master Switch fuer die Playground Rules Engine (GATES, EXCLUDES, REQUIRES, ...)
# True  -> Rules sind aktiv
# False -> Rules werden komplett uebersprungen (nur fuer Debug und Test)
PLAYGROUND_RULES_ENABLED = False

# ComfyUI Bridge
COMFYUI_BASE_URL = "http://127.0.0.1:8188"
WORKFLOWS_DIR = DATA_DIR / "workflows"
DEFAULT_WORKFLOW_PATH = WORKFLOWS_DIR / "_default_character.json"
COMFYUI_CHECKPOINTS_DIR = Path(r"C:\Users\Alexa\PycharmProjects\ComfyUI\models\checkpoints")

# SSL / HTTPS
SSL_ENABLED = True
SSL_CERTFILE = BASE_DIR / "certs" / "comfy.lan+1.pem"
SSL_KEYFILE = BASE_DIR / "certs" / "comfy.lan+1-key.pem"