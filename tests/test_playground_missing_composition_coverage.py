"""Coverage for missing persisted Playground compositions."""

import pytest

from comfyreview.application import PromptSelectionError
from tests.test_playground_application import (
    _catalog,
    _CatalogService,
    _service,
)


def test_playground_service_rejects_unknown_composition() -> None:
    service = _service(_CatalogService(_catalog()))

    for prepare in (
        service.resolve_composition_selection,
        service.prepare_composition_draft,
    ):
        with pytest.raises(PromptSelectionError, match="character revision"):
            prepare("composition-missing")
