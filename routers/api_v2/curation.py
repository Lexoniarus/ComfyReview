"""Canonical image-curation V2 HTTP adapter."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from comfyreview.api import get_application_container
from comfyreview.application import (
    AssignCurationCommand,
    CurationMutationError,
    CurationValidationError,
    InvalidOutputPathError,
    OutputPairNotFoundError,
)
from routers.api_v2.common import error_response
from services.output_file_service import OutputMutationError

router = APIRouter()


class CurationRequest(BaseModel):
    """Accept one UID-only V2 curation mutation."""

    set_key: str


@router.put("/images/{image_uid}/curation")
def assign_curation(
    request: Request,
    image_uid: str,
    payload: CurationRequest,
) -> JSONResponse:
    """Assign one canonical image to a curation set."""
    container = get_application_container(request)
    try:
        result = container.curation_service.assign(
            AssignCurationCommand(image_uid=image_uid, set_key=payload.set_key)
        )
    except (CurationValidationError, InvalidOutputPathError) as error:
        return error_response(400, "invalid_curation", str(error))
    except OutputPairNotFoundError as error:
        return error_response(404, "image_not_found", str(error))
    except (CurationMutationError, OutputMutationError) as error:
        return error_response(500, "curation_failed", str(error))
    return JSONResponse(
        {"image_uid": result.image_uid, "set_key": result.set_key}
    )
