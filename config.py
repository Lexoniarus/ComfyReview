from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

APP_HOST = "127.0.0.1"
APP_PORT = 8787

OUTPUT_ROOT = Path(r"C:\Users\Alexa\PycharmProjects\ComfyUI\output")
TRASH_ROOT = OUTPUT_ROOT / "_trash"

TEMPLATES_DIR = BASE_DIR / "templates"

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path("ratings.sqlite3")
PROMPT_DB_PATH = Path("prompt_tokens.sqlite3")
ARENA_DB_PATH = Path("arena.sqlite3")

PLAYGROUND_DB_PATH = DATA_DIR / "playground.sqlite3"

PROMPT_TOKENS_DB_PATH = PROMPT_DB_PATH

DEFAULT_UNRATED_ONLY = True
SOFT_DELETE_TO_TRASH = False

# ComfyUI Bridge
COMFYUI_BASE_URL = "http://127.0.0.1:8188"
WORKFLOWS_DIR = DATA_DIR / "workflows"
DEFAULT_WORKFLOW_PATH = BASE_DIR / "_default_character.json"
COMFYUI_CHECKPOINTS_DIR = Path(r"C:\Users\Alexa\PycharmProjects\ComfyUI\models\checkpoints")