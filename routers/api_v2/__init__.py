"""Compose focused HTTP adapters for the ComfyReview V2 API."""

from fastapi import APIRouter

from routers.api_v2.arena import router as arena_router
from routers.api_v2.catalog import router as catalog_router
from routers.api_v2.curation import router as curation_router
from routers.api_v2.generations import router as generations_router
from routers.api_v2.images import router as images_router
from routers.api_v2.playground import router as playground_router
from routers.api_v2.review import router as review_router
from routers.api_v2.scopes import router as scopes_router

router = APIRouter(prefix="/api/v2")
router.include_router(scopes_router)
router.include_router(images_router)
router.include_router(review_router)
router.include_router(arena_router)
router.include_router(catalog_router)
router.include_router(playground_router)
router.include_router(generations_router)
router.include_router(curation_router)

__all__ = ["router"]
