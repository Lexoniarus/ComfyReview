from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Hinweis: Tabellen sind klick-sortierbar (Header anklicken).

_TEMPLATES_DIR = Path(__file__).with_name("templates")

env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

INDEX_HTML = env.get_template("index.html")
STATS_HTML = env.get_template("stats.html")
RECO_HTML = env.get_template("recommendations.html")
PARAM_HTML = env.get_template("param_stats.html")
PROMPT_HTML = env.get_template("prompt_tokens.html")
ARENA_HTML = env.get_template("arena.html")
TOP_PICTURES_HTML = env.get_template("top_pictures.html")