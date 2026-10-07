"""Canonical coverage summary for the Analytics overview."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.render_guidance import RenderGuidanceService


@dataclass(frozen=True, slots=True)
class AnalyticsCoverageFacts:
    """Store non-derived visible counts read from canonical facts."""

    active_image_count: int
    rated_image_count: int
    prompt_linked_image_count: int
    legacy_image_count: int
    geometry_projected_count: int
    geometry_value_counts: tuple[tuple[str, str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class AnalyticsCoverage:
    """Combine canonical coverage with rebuildable render guidance."""

    active_image_count: int
    rated_image_count: int
    prompt_linked_image_count: int
    unlinked_prompt_image_count: int
    legacy_image_count: int
    geometry_projected_count: int
    missing_geometry_count: int
    observed_setup_count: int
    stable_setup_count: int
    modeled_value_counts: tuple[tuple[str, int], ...]
    geometry_value_counts: tuple[tuple[str, str, int], ...]
    model_version: str


class AnalyticsCoverageRepository(Protocol):
    """Read visible canonical coverage facts."""

    def load(self) -> AnalyticsCoverageFacts:
        """Return one immutable snapshot of coverage counts."""
        ...


class AnalyticsCoverageService:
    """Build the Analytics overview without parallel recommendation logic."""

    def __init__(
        self,
        *,
        repository: AnalyticsCoverageRepository,
        render_guidance: RenderGuidanceService,
    ) -> None:
        self._repository = repository
        self._render_guidance = render_guidance

    def load(self) -> AnalyticsCoverage:
        """Return canonical and derived coverage in one read model."""
        facts = self._repository.load()
        render = self._render_guidance.build(limit=0)
        return AnalyticsCoverage(
            active_image_count=facts.active_image_count,
            rated_image_count=facts.rated_image_count,
            prompt_linked_image_count=facts.prompt_linked_image_count,
            unlinked_prompt_image_count=max(
                0,
                facts.active_image_count - facts.prompt_linked_image_count,
            ),
            legacy_image_count=facts.legacy_image_count,
            geometry_projected_count=facts.geometry_projected_count,
            missing_geometry_count=max(
                0,
                facts.active_image_count - facts.geometry_projected_count,
            ),
            observed_setup_count=render.coverage.observed_setup_count,
            stable_setup_count=render.coverage.stable_setup_count,
            modeled_value_counts=tuple(
                (parameter.value, count)
                for parameter, count in render.coverage.modeled_value_counts
            ),
            geometry_value_counts=facts.geometry_value_counts,
            model_version=render.model_version,
        )
