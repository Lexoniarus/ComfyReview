from .arena_router import router as arena_router
from .index_router import router as index_router
from .stats_router import router as stats_router
from .top_router import router as top_router

__all__ = ["index_router", "top_router", "arena_router", "stats_router"]
