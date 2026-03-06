from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import (
    OUTPUT_ROOT,
    MV_QUEUE_DB_PATH,
    DB_PATH,
    PROMPT_TOKENS_DB_PATH,
    PROMPT_RATINGS_DB_PATH,
    COMBO_PROMPTS_DB_PATH,
    PLAYGROUND_DB_PATH,
    IMAGES_DB_PATH,
)

from routers.stats_router import router as stats_router
from routers.index_router import router as index_router
from routers.top_router import router as top_router
from routers.arena_router import router as arena_router
from routers.playground_router import router as playground_router

from services.mv_worker import start_worker_thread


app = FastAPI(title="Comfy Review")
app.mount("/files", StaticFiles(directory=str(OUTPUT_ROOT)), name="files")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(index_router)
app.include_router(top_router)
app.include_router(arena_router)
app.include_router(stats_router)
app.include_router(playground_router)


@app.on_event("startup")
def _startup_worker():
    # Start persistent MV worker (Queue + Catchup)
    start_worker_thread(
        queue_db_path=MV_QUEUE_DB_PATH,
        state_db_path=MV_QUEUE_DB_PATH,
        ratings_db_path=DB_PATH,
        prompt_tokens_db_path=PROMPT_TOKENS_DB_PATH,
        prompt_ratings_db_path=PROMPT_RATINGS_DB_PATH,
        combo_db_path=COMBO_PROMPTS_DB_PATH,
        playground_db_path=PLAYGROUND_DB_PATH,
        images_db_path=IMAGES_DB_PATH,
    )
