# routers/playground/__init__.py
from fastapi import APIRouter

from .hub import router as hub_router
from .browse import router as browse_router
from .generator import router as generator_router
from .api import router as api_router

router = APIRouter()

router.include_router(hub_router)
router.include_router(browse_router)
router.include_router(generator_router)
router.include_router(api_router)
