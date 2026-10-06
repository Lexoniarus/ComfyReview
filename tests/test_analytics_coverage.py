"""Behavior tests for the focused Analytics coverage read model."""

from dataclasses import dataclass

from comfyreview.application.analytics_coverage import (
    AnalyticsCoverageFacts,
    AnalyticsCoverageService,
)
from comfyreview.application.render_guidance import (
    GuidanceParameter,
    RenderGuidance,
    RenderGuidanceCoverage,
)


@dataclass
class _Repository:
    def load(self) -> AnalyticsCoverageFacts:
        return AnalyticsCoverageFacts(
            12,
            10,
            9,
            2,
            11,
            (("aspect_format", "1:1", 8),),
        )


class _Guidance:
    def build(self, *, limit: int = 24) -> RenderGuidance:
        assert limit == 0
        return RenderGuidance(
            None,
            None,
            None,
            None,
            None,
            None,
            (),
            (),
            (),
            RenderGuidanceCoverage(
                10,
                14,
                7,
                2,
                ((GuidanceParameter.SAMPLER, 3),),
            ),
        )


def test_analytics_coverage_reports_diagnostics_without_recommendations() -> (
    None
):
    coverage = AnalyticsCoverageService(
        repository=_Repository(),
        render_guidance=_Guidance(),  # type: ignore[arg-type]
    ).load()

    assert coverage.active_image_count == 12
    assert coverage.unlinked_prompt_image_count == 3
    assert coverage.missing_geometry_count == 1
    assert coverage.observed_setup_count == 7
    assert coverage.stable_setup_count == 2
    assert coverage.modeled_value_counts == (("sampler", 3),)
    assert coverage.geometry_value_counts == (("aspect_format", "1:1", 8),)
    assert coverage.model_version == "render-guidance-v1"
