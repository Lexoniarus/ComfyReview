"""Bounded multipart upload provider for ComfyUI input images."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol, cast
from uuid import uuid4

from comfyreview.application.card_battler_evolution_images import (
    StagedCardReferenceImage,
)
from comfyreview.application.card_battler_semantics import CardSourceImage
from comfyreview.application.comfyui import (
    ComfyUiConnectionError,
    ComfyUiProtocolError,
    ComfyUiRejectionError,
    ComfyUiTimeoutError,
)

_CARD_INPUT_SUBFOLDER = "comfyreview/card-battler"


@dataclass(frozen=True, slots=True)
class MultipartUploadResponse:
    """Carry one decoded ComfyUI multipart response."""

    status_code: int
    payload: object


class MultipartUploadTransport(Protocol):
    """Upload one bounded file without exposing HTTP to application code."""

    def upload(
        self,
        path: str,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        fields: dict[str, str],
        timeout_seconds: float,
    ) -> MultipartUploadResponse:
        """Return one decoded response or a normalized technical failure."""
        ...


class UrlLibMultipartUploadTransport:
    """Own multipart encoding and bounded urllib communication."""

    def __init__(self, base_url: str) -> None:
        normalized = str(base_url or "").strip().rstrip("/")
        if not normalized:
            raise ValueError("base_url is required")
        self._base_url = normalized

    def upload(
        self,
        path: str,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        fields: dict[str, str],
        timeout_seconds: float,
    ) -> MultipartUploadResponse:
        """POST one multipart image and normalize transport failures."""
        boundary = f"comfyreview-{uuid4().hex}"
        body = self._body(
            boundary,
            filename=filename,
            content_type=content_type,
            content=content,
            fields=fields,
        )
        request = urllib.request.Request(
            self._base_url + "/" + path.lstrip("/"),
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=max(float(timeout_seconds), 0.0),
            ) as response:
                return MultipartUploadResponse(
                    int(response.status),
                    self._decode(response.read()),
                )
        except urllib.error.HTTPError as error:
            return MultipartUploadResponse(
                int(error.code),
                self._decode(error.read()),
            )
        except TimeoutError as error:
            raise ComfyUiTimeoutError("ComfyUI upload timed out") from error
        except (urllib.error.URLError, OSError) as error:
            raise ComfyUiConnectionError(
                "Could not connect to ComfyUI upload endpoint"
            ) from error

    @staticmethod
    def _body(
        boundary: str,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        fields: dict[str, str],
    ) -> bytes:
        marker = boundary.encode("ascii")
        parts: list[bytes] = []
        for name, value in sorted(fields.items()):
            parts.extend(
                (
                    b"--" + marker + b"\r\n",
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                    value.encode("utf-8") + b"\r\n",
                )
            )
        parts.extend(
            (
                b"--" + marker + b"\r\n",
                (
                    'Content-Disposition: form-data; name="image"; '
                    f'filename="{filename}"\r\n'
                ).encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode("ascii"),
                content + b"\r\n",
                b"--" + marker + b"--\r\n",
            )
        )
        return b"".join(parts)

    @staticmethod
    def _decode(raw: bytes) -> object:
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ComfyUiProtocolError(
                "ComfyUI upload returned invalid JSON"
            ) from error


class ComfyUiCardReferenceImageStager:
    """Stage Card image bytes in the reserved ComfyUI input subfolder."""

    def __init__(
        self,
        transport: MultipartUploadTransport,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._transport = transport
        self._timeout_seconds = max(float(timeout_seconds), 0.0)

    def stage(self, image: CardSourceImage) -> StagedCardReferenceImage:
        """Upload one PNG under a content-addressed stable input name."""
        if image.mime_type != "image/png":
            raise ValueError("Card evolution currently requires PNG input")
        filename = f"{image.content_hash}.png"
        response = self._transport.upload(
            "/upload/image",
            filename=filename,
            content_type=image.mime_type,
            content=image.content,
            fields={
                "overwrite": "true",
                "subfolder": _CARD_INPUT_SUBFOLDER,
                "type": "input",
            },
            timeout_seconds=self._timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise ComfyUiRejectionError(
                f"ComfyUI upload rejected with HTTP {response.status_code}"
            )
        if not isinstance(response.payload, dict):
            raise ComfyUiProtocolError("ComfyUI upload response is invalid")
        payload = cast(dict[str, object], response.payload)
        name = str(payload.get("name") or "").strip()
        subfolder = (
            str(payload.get("subfolder") or "").strip().replace("\\", "/")
        )
        storage_type = str(payload.get("type") or "").strip()
        if (
            name != filename
            or subfolder != _CARD_INPUT_SUBFOLDER
            or storage_type != "input"
        ):
            raise ComfyUiProtocolError(
                "ComfyUI upload response does not match staged Card input"
            )
        return StagedCardReferenceImage(
            f"{subfolder}/{name}",
            image.content_hash,
        )
