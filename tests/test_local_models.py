"""Behavior checks for normalized local-model contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

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

    assert loaded.model_id == instance.model_id
    assert loaded.loaded_instances == (instance,)
    assert unloaded.loaded_instances == ()
    with pytest.raises(FrozenInstanceError):
        setattr(instance, "instance_id", "different-instance")
    with pytest.raises(FrozenInstanceError):
        setattr(loaded, "loaded_instances", ())


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
