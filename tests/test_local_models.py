"""Behavior checks for normalized local-model contracts."""

from __future__ import annotations

import pytest

from comfyreview.application.local_models import (
    LocalModelConnectionError,
    LocalModelDescriptor,
    LocalModelError,
    LocalModelInstance,
    LocalModelLifecycleError,
    LocalModelProtocolError,
    LocalModelTimeoutError,
    LocalModelUnavailableError,
)


def test_local_model_descriptor_preserves_instance_identity() -> None:
    instance = LocalModelInstance("vision-model", "instance-1")
    loaded = LocalModelDescriptor("vision-model", (instance,))
    unloaded = LocalModelDescriptor("text-model")

    assert instance.model_id == "vision-model"
    assert instance.instance_id == "instance-1"
    assert loaded.model_id == instance.model_id
    assert loaded.loaded_instances == (instance,)
    assert unloaded.loaded_instances == ()


@pytest.mark.parametrize(
    "failure_type",
    (
        LocalModelConnectionError,
        LocalModelTimeoutError,
        LocalModelUnavailableError,
        LocalModelProtocolError,
        LocalModelLifecycleError,
    ),
)
def test_local_model_failures_share_normalized_base(
    failure_type: type[LocalModelError],
) -> None:
    error = failure_type("test failure")

    assert isinstance(error, LocalModelError)
    assert isinstance(error, RuntimeError)
    assert str(error) == "test failure"
