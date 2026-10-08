"""Canonical prompt-catalog V2 HTTP adapters."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from comfyreview.api import get_application_container
from comfyreview.application import (
    ContentClassificationError,
    ContentLevel,
    CreateLoraDefinitionCommand,
    CreatePromptComponentCommand,
    LoraDefinition,
    LoraRevision,
    PromptCatalogValidationError,
    PromptComponent,
    PromptRevision,
    UpdateLoraDefinitionCommand,
    UpdatePromptComponentCommand,
)
from comfyreview.application.prompt_kinds import PromptKind
from comfyreview.domain import PromptAtomUsage, prompt_atom_usage
from routers.api_v2.common import error_response

router = APIRouter()


class PromptAtomRequest(BaseModel):
    """Carry structured authored atom content."""

    text: str
    weight: float = 1.0


class PromptComponentWriteRequest(BaseModel):
    """Create or update catalog metadata and immutable prompt content."""

    kind: PromptKind
    name: str
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    positive_atoms: list[PromptAtomRequest] = Field(default_factory=list)
    negative_atoms: list[PromptAtomRequest] = Field(default_factory=list)
    content_level: ContentLevel


class PromptArchiveRequest(BaseModel):
    """Set reversible component archive state."""

    archived: bool


class LoraCatalogWriteRequest(BaseModel):
    """Create or revise one canonical LoRA catalog entry."""

    provider_name: str
    display_name: str
    content_level: ContentLevel
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    default_model_strength: float = 1.0
    default_clip_strength: float = 1.0
    positive_atoms: list[PromptAtomRequest] = Field(default_factory=list)
    negative_atoms: list[PromptAtomRequest] = Field(default_factory=list)
    expected_revision: int = 1


@router.get("/catalog/loras")
def catalog_loras(
    request: Request,
    include_archived: bool = Query(False),
) -> JSONResponse:
    """Return the canonical LoRA catalog with latest revisions."""
    container = get_application_container(request)
    definitions = container.lora_catalog.list_definitions()
    available = set(container.playground_discovery.discover().loras)
    return JSONResponse(
        {
            "loras": [
                {
                    **lora_response(item),
                    "available": item.provider_name in available,
                }
                for item in definitions
                if include_archived or not item.archived
            ]
        }
    )


@router.get("/catalog/loras/{lora_uid}")
def catalog_lora(request: Request, lora_uid: str) -> JSONResponse:
    """Return one stable LoRA catalog entry."""
    try:
        container = get_application_container(request)
        definition = container.lora_catalog.get_definition(lora_uid)
        available = set(container.playground_discovery.discover().loras)
        images = container.catalog_evidence.list_top_lora_images(lora_uid)
    except (KeyError, ContentClassificationError) as error:
        return lora_error(error)
    return JSONResponse(
        {
            **lora_response(definition),
            "available": definition.provider_name in available,
            "top_images": [
                {
                    "image_uid": image.image_uid,
                    "image_url": container.image_responses.image_url(
                        image.image_uid
                    ),
                    "average_rating": image.average_rating,
                    "rating_count": image.rating_count,
                }
                for image in images
            ],
        }
    )


@router.get("/catalog/loras/{lora_uid}/revisions")
def catalog_lora_revisions(request: Request, lora_uid: str) -> JSONResponse:
    """Return immutable LoRA trigger/default history."""
    try:
        revisions = get_application_container(
            request
        ).lora_catalog.list_revisions(lora_uid)
    except (KeyError, ContentClassificationError) as error:
        return lora_error(error)
    return JSONResponse(
        {"revisions": [lora_revision_response(item) for item in revisions]}
    )


@router.post("/catalog/loras")
def create_catalog_lora(
    request: Request, payload: LoraCatalogWriteRequest
) -> JSONResponse:
    """Create one stable LoRA definition with revision one."""
    try:
        definition = get_application_container(request).lora_catalog.create(
            CreateLoraDefinitionCommand(
                provider_name=payload.provider_name,
                display_name=payload.display_name,
                content_level=payload.content_level,
                tags=tuple(payload.tags),
                notes=payload.notes,
                default_model_strength_milli=round(
                    payload.default_model_strength * 1000
                ),
                default_clip_strength_milli=round(
                    payload.default_clip_strength * 1000
                ),
                positive_atoms=atom_usages(payload.positive_atoms),
                negative_atoms=atom_usages(payload.negative_atoms),
            )
        )
    except (ContentClassificationError, PromptCatalogValidationError) as error:
        return lora_error(error)
    return JSONResponse(lora_response(definition), status_code=201)


@router.put("/catalog/loras/{lora_uid}")
def update_catalog_lora(
    request: Request,
    lora_uid: str,
    payload: LoraCatalogWriteRequest,
) -> JSONResponse:
    """Update mutable metadata and append changed immutable defaults."""
    try:
        definition = get_application_container(request).lora_catalog.update(
            UpdateLoraDefinitionCommand(
                lora_uid=lora_uid,
                expected_revision=payload.expected_revision,
                provider_name=payload.provider_name,
                display_name=payload.display_name,
                content_level=payload.content_level,
                tags=tuple(payload.tags),
                notes=payload.notes,
                default_model_strength_milli=round(
                    payload.default_model_strength * 1000
                ),
                default_clip_strength_milli=round(
                    payload.default_clip_strength * 1000
                ),
                positive_atoms=atom_usages(payload.positive_atoms),
                negative_atoms=atom_usages(payload.negative_atoms),
            )
        )
    except (
        KeyError,
        ContentClassificationError,
        PromptCatalogValidationError,
    ) as error:
        return lora_error(error)
    return JSONResponse(lora_response(definition))


@router.patch("/catalog/loras/{lora_uid}")
def archive_catalog_lora(
    request: Request,
    lora_uid: str,
    payload: PromptArchiveRequest,
) -> JSONResponse:
    """Archive or restore one LoRA without deleting its revisions."""
    try:
        definition = get_application_container(
            request
        ).lora_catalog.set_archived(lora_uid, archived=payload.archived)
    except (KeyError, ContentClassificationError) as error:
        return lora_error(error)
    return JSONResponse(lora_response(definition))


@router.get("/catalog/components")
def catalog_components(
    request: Request,
    include_archived: bool = Query(False),
) -> JSONResponse:
    """Return canonical prompt components with their latest revisions."""
    components = get_application_container(
        request
    ).prompt_catalog_service.list_components(include_archived=include_archived)
    return JSONResponse(
        {"components": [component_response(item) for item in components]}
    )


@router.get("/catalog/components/{component_uid}")
def catalog_component(request: Request, component_uid: str) -> JSONResponse:
    """Return one canonical prompt component."""
    try:
        container = get_application_container(request)
        component = container.prompt_catalog_service.get_component(
            component_uid
        )
        images = container.catalog_evidence.list_top_images(component_uid)
    except (KeyError, PromptCatalogValidationError) as error:
        return catalog_error(error)
    return JSONResponse(
        {
            **component_response(component),
            "top_images": [
                {
                    "image_uid": image.image_uid,
                    "image_url": container.image_responses.image_url(
                        image.image_uid
                    ),
                    "average_rating": image.average_rating,
                    "rating_count": image.rating_count,
                }
                for image in images
            ],
        }
    )


@router.get("/catalog/components/{component_uid}/revisions")
def catalog_component_revisions(
    request: Request,
    component_uid: str,
) -> JSONResponse:
    """Return immutable revision history for one component."""
    try:
        revisions = get_application_container(
            request
        ).prompt_catalog_service.list_revisions(component_uid)
    except (KeyError, PromptCatalogValidationError) as error:
        return catalog_error(error)
    return JSONResponse(
        {"revisions": [revision_response(item) for item in revisions]}
    )


@router.post("/catalog/components")
def create_catalog_component(
    request: Request,
    payload: PromptComponentWriteRequest,
) -> JSONResponse:
    """Create one component and immutable revision one."""
    try:
        component = get_application_container(
            request
        ).prompt_catalog_service.create_component(
            CreatePromptComponentCommand(
                kind=payload.kind,
                component_key="",
                name=payload.name,
                tags=tuple(payload.tags),
                notes=payload.notes,
                positive_atoms=atom_usages(payload.positive_atoms),
                negative_atoms=atom_usages(payload.negative_atoms),
                content_level=payload.content_level,
            )
        )
    except PromptCatalogValidationError as error:
        return error_response(400, "invalid_catalog_component", str(error))
    return JSONResponse(component_response(component), status_code=201)


@router.put("/catalog/components/{component_uid}")
def update_catalog_component(
    request: Request,
    component_uid: str,
    payload: PromptComponentWriteRequest,
) -> JSONResponse:
    """Update metadata and append changed prompt content atomically."""
    try:
        current = get_application_container(
            request
        ).prompt_catalog_service.get_component(component_uid)
        if payload.kind != current.kind:
            raise PromptCatalogValidationError(
                "component kind cannot be changed"
            )
        component = get_application_container(
            request
        ).prompt_catalog_service.update_component(
            UpdatePromptComponentCommand(
                component_uid=component_uid,
                name=payload.name,
                tags=tuple(payload.tags),
                notes=payload.notes,
                positive_atoms=atom_usages(payload.positive_atoms),
                negative_atoms=atom_usages(payload.negative_atoms),
                content_level=payload.content_level,
            )
        )
    except (KeyError, PromptCatalogValidationError) as error:
        return catalog_error(error)
    return JSONResponse(component_response(component))


@router.patch("/catalog/components/{component_uid}")
def archive_catalog_component(
    request: Request,
    component_uid: str,
    payload: PromptArchiveRequest,
) -> JSONResponse:
    """Archive or restore one component without deleting revisions."""
    try:
        component = get_application_container(
            request
        ).prompt_catalog_service.set_archived(
            component_uid,
            archived=payload.archived,
        )
    except (KeyError, PromptCatalogValidationError) as error:
        return catalog_error(error)
    return JSONResponse(component_response(component))


def component_response(component: PromptComponent) -> dict[str, object]:
    """Map one canonical prompt component to its V2 response."""
    current = component.standard_revision
    candidate = component.latest_manual_variant
    return {
        "component_uid": component.component_uid,
        "kind": component.kind,
        "component_key": component.component_key,
        "name": component.name,
        "tags": component.tags,
        "content_level": component.content_level.value,
        "notes": component.notes,
        "archived": component.archived,
        "current_revision": component_revision_response(current),
        "latest_revision": component_revision_response(
            component.latest_revision
        ),
        "latest_manual_variant": (
            {
                "candidate_uid": candidate.candidate_uid,
                "source_revision_uid": candidate.source_revision_uid,
                "content_hash": candidate.content_hash,
                "positive_atoms": atom_response(candidate.positive_atoms),
                "negative_atoms": atom_response(candidate.negative_atoms),
            }
            if candidate is not None
            else None
        ),
    }


def revision_response(revision: PromptRevision) -> dict[str, object]:
    """Map one immutable prompt revision to its V2 response."""
    return {
        "revision_uid": revision.revision_uid,
        "revision_number": revision.revision_number,
        "positive_text": revision.positive_text,
        "negative_text": revision.negative_text,
        "content_hash": revision.content_hash,
        "positive_atoms": atom_response(revision.positive_atoms),
        "negative_atoms": atom_response(revision.negative_atoms),
    }


def component_revision_response(
    revision: PromptRevision,
) -> dict[str, object]:
    """Map the compact revision shape embedded in a component response."""
    payload = revision_response(revision)
    payload.pop("content_hash")
    return payload


def lora_response(definition: LoraDefinition) -> dict[str, object]:
    """Map one canonical LoRA definition to its public catalog shape."""
    latest = definition.latest_revision
    return {
        "lora_uid": definition.lora_uid,
        "provider_name": definition.provider_name,
        "display_name": definition.display_name or definition.provider_name,
        "tags": definition.tags,
        "notes": definition.notes,
        "revision": definition.revision,
        "archived": definition.archived,
        "latest_revision": (
            lora_revision_response(latest) if latest is not None else None
        ),
    }


def lora_revision_response(revision: LoraRevision) -> dict[str, object]:
    """Map immutable LoRA defaults and triggers to JSON-safe values."""
    return {
        "revision_uid": revision.revision_uid,
        "revision_number": revision.revision_number,
        "content_level": revision.content_level.value,
        "default_model_strength": (
            revision.default_model_strength_milli / 1000
        ),
        "default_clip_strength": revision.default_clip_strength_milli / 1000,
        "content_hash": revision.content_hash,
        "positive_atoms": atom_response(revision.positive_atoms),
        "negative_atoms": atom_response(revision.negative_atoms),
    }


def atom_usages(
    values: list[PromptAtomRequest],
) -> tuple[PromptAtomUsage, ...]:
    """Translate JSON atom values into validated domain usages."""
    try:
        return tuple(
            prompt_atom_usage(value.text, value.weight) for value in values
        )
    except ValueError as error:
        raise PromptCatalogValidationError(str(error)) from error


def atom_response(
    values: tuple[PromptAtomUsage, ...],
) -> list[dict[str, object]]:
    """Map ordered domain atom usages to JSON values."""
    return [{"text": item.text, "weight": item.weight} for item in values]


def catalog_error(error: Exception) -> JSONResponse:
    """Normalize catalog lookup and validation failures."""
    if isinstance(error, KeyError):
        message = error.args[0] if error.args else str(error)
        return error_response(404, "catalog_component_not_found", str(message))
    return error_response(400, "invalid_catalog_component", str(error))


def lora_error(error: Exception) -> JSONResponse:
    """Normalize LoRA catalog lookup and optimistic-write failures."""
    if isinstance(error, KeyError):
        message = error.args[0] if error.args else str(error)
        return error_response(404, "catalog_lora_not_found", str(message))
    return error_response(400, "invalid_catalog_lora", str(error))
