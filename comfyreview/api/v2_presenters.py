"""HTTP response mapping for canonical V2 image queries."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from comfyreview.application import ImageContext, ImageScope, ScopeFacet


class ImageFileRepository(Protocol):
    """Resolve stable image identities to current file attributes."""

    def get_png_path(self, image_uid: str) -> Path | None:
        """Return the current live PNG path when available."""
        ...


class FileUrlMapper(Protocol):
    """Map one validated output path to its mounted HTTP URL."""

    def to_url(self, png_path: str | Path) -> str:
        """Return the mounted output URL."""
        ...


class ImageResponseMapper:
    """Add presentation URLs to path-free application read models."""

    def __init__(
        self,
        *,
        files: ImageFileRepository,
        urls: FileUrlMapper,
    ) -> None:
        self._files = files
        self._urls = urls

    def context(self, image: ImageContext) -> dict[str, Any]:
        """Map a complete image context to snake-case JSON data."""
        return {
            **self.summary(image),
            "image_url": self.image_url(image.image_uid),
            "prompt_snapshot": {
                "positive": image.prompt_snapshot.positive,
                "negative": image.prompt_snapshot.negative,
                "draft_overridden": image.prompt_snapshot.draft_overridden,
            },
            "generation_settings": {
                "model": image.generation_settings.model,
                "checkpoint": image.generation_settings.checkpoint,
                "seed": image.generation_settings.seed,
                "steps": image.generation_settings.steps,
                "cfg": image.generation_settings.cfg,
                "sampler": image.generation_settings.sampler,
                "scheduler": image.generation_settings.scheduler,
                "denoise": image.generation_settings.denoise,
            },
            "workflow_provenance": {
                "blueprint_uid": image.workflow.blueprint_uid,
                "blueprint_version": image.workflow.blueprint_version,
                "graph_hash": image.workflow.graph_hash,
            },
            "output_role": image.output_role,
            "output_index": image.output_index,
            "geometry": self.geometry(image),
        }

    def image_url(self, image_uid: str) -> str:
        """Map one stable image identity to its current presentation URL."""
        path = self._files.get_png_path(image_uid)
        return self._urls.to_url(path) if path is not None else ""

    def summary(self, image: ImageContext) -> dict[str, Any]:
        """Map image-card fields without exposing prompt or local path data."""
        return {
            "image_uid": image.image_uid,
            "generation_uid": image.generation_uid,
            "classification": image.classification.value,
            "scopes": [self.scope(scope) for scope in image.scopes],
            "review_summary": {
                "current_rating": image.review.current_rating,
                "rating_count": image.review.rating_count,
                "average_rating": image.review.average_rating,
            },
            "curation": (
                {
                    "set_key": image.curation.set_key,
                    "assigned_at": image.curation.assigned_at,
                }
                if image.curation is not None
                else None
            ),
            "content_classification": {
                "inferred_level": image.content.inferred_level.value,
                "effective_level": image.content.effective_level.value,
                "override_level": (
                    image.content.override_level.value
                    if image.content.override_level is not None
                    else None
                ),
            },
            "geometry": self.geometry(image),
        }

    @staticmethod
    def geometry(image: ImageContext) -> dict[str, object] | None:
        """Map one optional rebuildable geometry projection."""
        geometry = image.geometry
        if geometry is None:
            return None
        return {
            "actual_width": geometry.actual_width,
            "actual_height": geometry.actual_height,
            "aspect_format": geometry.aspect_format.value,
            "resolution_class": geometry.resolution_class.value,
            "target_width": geometry.target_width,
            "target_height": geometry.target_height,
            "match": "exact" if geometry.exact else "approximate",
            "classifier_version": geometry.classifier_version,
        }

    @staticmethod
    def scope(scope: ImageScope) -> dict[str, Any]:
        """Map one application scope to JSON-safe values."""
        return {
            "kind": scope.kind.value,
            "component_uid": scope.component_uid,
            "revision_uid": scope.revision_uid,
            "name": scope.name,
            "position": scope.position,
        }

    @staticmethod
    def facet(facet: ScopeFacet) -> dict[str, Any]:
        """Map one canonical scope facet to JSON-safe values."""
        return {
            "kind": facet.kind.value,
            "component_uid": facet.component_uid,
            "revision_uid": facet.revision_uid,
            "name": facet.name,
            "archived": facet.archived,
            "count": facet.count,
        }
