from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config import OUTPUT_ROOT
from routers.stats_router import router as stats_router
from routers.index_router import router as index_router
from routers.top_router import router as top_router
from routers.arena_router import router as arena_router
from routers.stats_router import router as stats_router
from routers.playground_router import router as playground_router


app = FastAPI(title="Comfy Review")
app.mount("/files", StaticFiles(directory=str(OUTPUT_ROOT)), name="files")

app.include_router(index_router)
app.include_router(top_router)
app.include_router(arena_router)
app.include_router(stats_router)
app.include_router(playground_router)