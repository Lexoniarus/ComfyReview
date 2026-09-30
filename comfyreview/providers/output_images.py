"""Canonical output-image provider backed by normalized persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from comfyreview.application import (
    CanonicalOutputImageRecord,
    CanonicalOutputImageSource,
    InvalidOutputPathError,
    OutputImageReadModel,
    OutputImageReference,
    OutputPair,
    OutputPairNotFoundError,
    ReviewImage,
)

_IGNORED_DIRECTORY_NAMES: Final = {"_lora_export", "_trash"}


class CanonicalOutputImageCatalog:
    """Expose filesystem-validated images from canonical persistence."""

    def __init__(
        self,
        *,
        output_root: Path,
        canonical_images: CanonicalOutputImageSource,
    ) -> None:
        self._output_root = Path(output_root).resolve()
        self._canonical_images = canonical_images

    def list_images(self) -> tuple[OutputImageReadModel, ...]:
        """Return live canonical images whose output files still exist."""
        images: list[OutputImageReadModel] = []

        for record in self._canonical_images.list_live_images():
            try:
                item = self._read_model(record)
            except (InvalidOutputPathError, OutputPairNotFoundError):
                continue
            images.append(item)

        images.sort(
            key=lambda item: (
                str(item.json_path or ""),
                str(item.png_path),
            )
        )
        return tuple(images)

    def resolve(self, reference: OutputImageReference) -> ReviewImage:
        """Resolve one stable canonical image identity."""
        record = self._canonical_images.get_live_image(reference.image_uid)
        if record is None:
            raise OutputPairNotFoundError(
                "Canonical output image no longer exists"
            )
        png_path, json_path = self._validated_paths(record)

        return ReviewImage(
            pair=OutputPair(png_path=png_path, json_path=json_path),
            model_branch=record.model_branch,
            checkpoint=record.checkpoint,
            combo_key=record.combo_key,
            steps=record.steps,
            cfg=record.cfg,
            sampler=record.sampler,
            scheduler=record.scheduler,
            denoise=record.denoise,
            loras_json=record.loras_json,
            positive_prompt=record.positive_prompt,
            negative_prompt=record.negative_prompt,
            image_uid=record.image_uid,
            generation_uid=record.generation_uid,
            output_node_id=record.output_node_id,
            output_index=record.output_index,
        )

    def _read_model(
        self,
        record: CanonicalOutputImageRecord,
    ) -> OutputImageReadModel:
        png_path, json_path = self._validated_paths(record)
        return OutputImageReadModel(
            png_path=png_path,
            json_path=json_path,
            subdir=self._subdir(png_path),
            model_branch=record.model_branch,
            checkpoint=record.checkpoint,
            combo_key=record.combo_key,
            meta=self._metadata(record),
            image_uid=record.image_uid,
            generation_uid=record.generation_uid,
            output_node_id=record.output_node_id,
            output_index=record.output_index,
            current_rating=record.current_rating,
            review_version=record.review_version,
            average_rating=record.average_rating,
            rating_count=record.rating_count,
            assigned_set_key=record.assigned_set_key,
            source=record.source,
        )

    def _validated_paths(
        self,
        record: CanonicalOutputImageRecord,
    ) -> tuple[Path, Path | None]:
        png_path = self._resolve_inside(record.png_path)
        if png_path.suffix.lower() != ".png" or self._is_ignored(png_path):
            raise InvalidOutputPathError("Invalid canonical PNG path")
        if not png_path.is_file():
            raise OutputPairNotFoundError("Canonical PNG no longer exists")

        json_path = None
        if record.json_path is not None:
            candidate = self._resolve_inside(record.json_path)
            if (
                candidate.suffix.lower() != ".json"
                or candidate.parent != png_path.parent
                or candidate.stem != png_path.stem
                or self._is_ignored(candidate)
            ):
                raise InvalidOutputPathError(
                    "Invalid canonical JSON provenance path"
                )
            json_path = candidate
        return png_path, json_path

    def _resolve_inside(self, path: Path) -> Path:
        candidate = path if path.is_absolute() else self._output_root / path
        try:
            resolved = candidate.resolve(strict=False)
            resolved.relative_to(self._output_root)
        except (OSError, ValueError) as exc:
            raise InvalidOutputPathError(
                "Output path is outside OUTPUT_ROOT"
            ) from exc
        return resolved

    @staticmethod
    def _is_ignored(path: Path) -> bool:
        return bool(
            _IGNORED_DIRECTORY_NAMES & {part.lower() for part in path.parts}
        )

    def _subdir(self, png_path: Path) -> str:
        relative_directory = png_path.parent.relative_to(self._output_root)
        parts = tuple(part for part in relative_directory.parts if part)
        if len(parts) >= 2 and parts[0].lower() == "playground":
            return f"playground/{parts[1]}"
        return relative_directory.as_posix()

    def _metadata(
        self,
        record: CanonicalOutputImageRecord,
    ) -> dict[str, Any]:
        metadata = self._json_object(record.raw_metadata_json)
        workflow = self._json_object(record.workflow_json)
        if workflow:
            metadata["comfy_prompt_graph"] = workflow

        metadata.update(
            {
                "checkpoint": record.checkpoint,
                "model_branch": record.model_branch,
                "combo_key": record.combo_key,
                "seed": record.seed,
                "steps": record.steps,
                "cfg": record.cfg,
                "sampler": record.sampler,
                "scheduler": record.scheduler,
                "denoise": record.denoise,
                "loras": self._json_list(record.loras_json),
                "pos_prompt": record.positive_prompt,
                "neg_prompt": record.negative_prompt,
                "image_uid": record.image_uid,
                "generation_uid": record.generation_uid,
                "generation_source": record.source,
                "ksampler": {
                    "seed": record.seed,
                    "steps": record.steps,
                    "cfg": record.cfg,
                    "sampler": record.sampler,
                    "scheduler": record.scheduler,
                    "denoise": record.denoise,
                },
            }
        )
        return metadata

    @staticmethod
    def _json_object(value: str | None) -> dict[str, Any]:
        if value is None or not value.strip():
            return {}
        try:
            payload = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _json_list(value: str) -> list[Any]:
        try:
            payload = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []
