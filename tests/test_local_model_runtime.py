"""Deterministic lease and ownership tests for local-model runtime."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from typing import cast

import pytest

from comfyreview.application.local_model_runtime import (
    LocalModelCleanupFailure,
    LocalModelLease,
    LocalModelRuntime,
    _Phase,
)
from comfyreview.application.local_models import (
    LocalModelConnectionError,
    LocalModelDescriptor,
    LocalModelInstance,
    LocalModelLifecycleError,
    LocalModelProtocolError,
    LocalModelTimeoutError,
    LocalModelUnavailableError,
)

_ModelList = tuple[LocalModelDescriptor, ...]


class _FakeProvider:
    def __init__(self, models: _ModelList) -> None:
        self.models = models
        self.list_calls = 0
        self.load_calls: list[str] = []
        self.unload_calls: list[LocalModelInstance] = []
        self.on_list: Callable[[], _ModelList] | None = None
        self.on_load: Callable[[str], LocalModelInstance] | None = None
        self.on_unload: Callable[[LocalModelInstance], None] | None = None

    def list_models(self) -> _ModelList:
        self.list_calls += 1
        if self.on_list is not None:
            return self.on_list()
        return self.models

    def load_model(self, model_id: str) -> LocalModelInstance:
        self.load_calls.append(model_id)
        if self.on_load is not None:
            return self.on_load(model_id)
        return LocalModelInstance(model_id, "created-1")

    def unload_model(self, instance: LocalModelInstance) -> None:
        self.unload_calls.append(instance)
        if self.on_unload is not None:
            self.on_unload(instance)


def _available(model_id: str = "model") -> _FakeProvider:
    return _FakeProvider((LocalModelDescriptor(model_id),))


def test_runtime_constructor_is_passive() -> None:
    provider = _available()

    runtime = LocalModelRuntime(provider)

    assert isinstance(runtime, LocalModelRuntime)
    assert provider.list_calls == 0
    assert provider.load_calls == []
    assert provider.unload_calls == []


def test_loaded_model_is_borrowed_and_never_unloaded() -> None:
    instance = LocalModelInstance("model", "already-loaded")
    provider = _FakeProvider((LocalModelDescriptor("model", (instance,)),))
    runtime = LocalModelRuntime(provider)

    first = runtime.acquire("model")
    second = runtime.acquire("model")
    assert first is not second
    assert first.instance is instance
    assert second.instance is instance
    assert provider.list_calls == 1

    assert runtime.release(first) is None
    assert runtime.release(second) is None
    assert runtime.release(second) is None
    assert provider.unload_calls == []

    again = runtime.acquire("model")
    assert provider.list_calls == 2
    assert runtime.release(again) is None
    assert provider.unload_calls == []


def test_multiple_existing_instances_use_stable_casefold_sorting() -> None:
    provider = _FakeProvider(
        (
            LocalModelDescriptor(
                "model",
                (
                    LocalModelInstance("model", "Z"),
                    LocalModelInstance("model", "a"),
                ),
            ),
            LocalModelDescriptor("model", (LocalModelInstance("model", "A"),)),
            LocalModelDescriptor("other"),
        )
    )
    runtime = LocalModelRuntime(provider)

    lease = runtime.acquire("model")

    assert lease.instance.instance_id == "A"
    assert provider.load_calls == []
    assert runtime.release(lease) is None


def test_owned_model_reuses_instance_until_final_release() -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)

    first = runtime.acquire(" model ")
    second = runtime.acquire("model")

    assert first.instance is second.instance
    assert provider.list_calls == 1
    assert provider.load_calls == ["model"]
    assert runtime.release(first) is None
    assert runtime.release(first) is None
    assert provider.unload_calls == []
    assert runtime.release(second) is None
    assert runtime.release(second) is None
    assert provider.unload_calls == [first.instance]


def test_unknown_foreign_or_forged_leases_are_programming_errors() -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    foreign_runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    other = foreign_runtime.acquire("model")

    with pytest.raises(ValueError, match="Unknown"):
        runtime.release(other)
    with pytest.raises(ValueError, match="Unknown"):
        runtime.release(LocalModelLease(lease.instance, lease._issuer))
    with pytest.raises(ValueError, match="Unknown"):
        runtime.release(cast(LocalModelLease, object()))

    assert runtime.release(lease) is None
    assert foreign_runtime.release(other) is None


@pytest.mark.parametrize("invalid", (None, "", "  ", 123))
def test_invalid_model_id_is_rejected_without_provider_calls(
    invalid: object,
) -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)

    with pytest.raises(ValueError, match="model_id"):
        runtime.acquire(cast(str, invalid))
    assert provider.list_calls == 0


def test_missing_model_is_rejected_without_loading() -> None:
    provider = _available("other")

    with pytest.raises(LocalModelUnavailableError, match="Model not found"):
        LocalModelRuntime(provider).acquire("model")
    assert provider.load_calls == []


def test_discovery_and_load_errors_remain_normalized() -> None:
    discovery_provider = _available()
    discovery_provider.on_list = lambda: (_ for _ in ()).throw(
        LocalModelConnectionError("discovery failure")
    )
    with pytest.raises(LocalModelConnectionError, match="discovery failure"):
        LocalModelRuntime(discovery_provider).acquire("model")

    load_provider = _available()
    load_provider.on_load = lambda _model_id: (_ for _ in ()).throw(
        LocalModelTimeoutError("load failure")
    )
    with pytest.raises(LocalModelTimeoutError, match="load failure"):
        LocalModelRuntime(load_provider).acquire("model")
    assert load_provider.unload_calls == []


@pytest.mark.parametrize(
    "bad_instance",
    (
        LocalModelInstance("other", "unexpected"),
        LocalModelInstance("model", ""),
        LocalModelInstance("model", "  "),
        cast(LocalModelInstance, object()),
    ),
)
def test_invalid_load_response_never_establishes_ownership(
    bad_instance: LocalModelInstance,
) -> None:
    provider = _available()
    provider.on_load = lambda _model_id: bad_instance

    with pytest.raises(LocalModelProtocolError, match="invalid instance"):
        LocalModelRuntime(provider).acquire("model")
    assert provider.unload_calls == []


def test_invalid_borrowed_instance_is_not_accepted() -> None:
    provider = _FakeProvider(
        (LocalModelDescriptor("model", (LocalModelInstance("other", "a"),)),)
    )

    with pytest.raises(LocalModelProtocolError, match="invalid instance"):
        LocalModelRuntime(provider).acquire("model")
    assert provider.load_calls == []


def test_failed_final_unload_is_recoverable_and_blocks_new_leases() -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    fail = True

    def unload(_instance: LocalModelInstance) -> None:
        nonlocal fail
        if fail:
            fail = False
            raise LocalModelTimeoutError("unload failure")

    provider.on_unload = unload
    failure = runtime.release(lease)

    assert failure is not None
    assert failure == LocalModelCleanupFailure(lease.instance, failure.error)
    assert isinstance(failure.error, LocalModelTimeoutError)
    assert str(failure.error) == "unload failure"
    with pytest.raises(LocalModelLifecycleError, match="Cleanup must"):
        runtime.acquire("model")
    assert runtime.release(lease) is None
    assert runtime.release(lease) is None
    assert provider.unload_calls == [lease.instance, lease.instance]


def test_waiting_release_retries_unexpected_cleanup_bug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    entered = Event()
    allow = Event()
    second_waiting = Event()

    def unload(_instance: LocalModelInstance) -> None:
        if len(provider.unload_calls) == 1:
            entered.set()
            assert allow.wait(timeout=5)
            raise RuntimeError("provider bug")

    provider.on_unload = unload
    original_wait = runtime._changed.wait

    def wait_for_unload(timeout: float | None = None) -> bool:
        second_waiting.set()
        return original_wait(timeout)

    monkeypatch.setattr(runtime._changed, "wait", wait_for_unload)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(runtime.release, lease)
        assert entered.wait(timeout=5)
        second = executor.submit(runtime.release, lease)
        try:
            assert second_waiting.wait(timeout=5)
        finally:
            allow.set()
        with pytest.raises(RuntimeError, match="provider bug"):
            first.result(timeout=5)
        assert second.result(timeout=5) is None

    assert provider.unload_calls == [lease.instance, lease.instance]


def test_parallel_acquires_load_one_instance_only() -> None:
    provider = _available()
    entered = Event()
    proceed = Event()
    launch = Barrier(3)

    def load(model_id: str) -> LocalModelInstance:
        entered.set()
        assert proceed.wait(timeout=5)
        return LocalModelInstance(model_id, "created-in-parallel")

    provider.on_load = load
    runtime = LocalModelRuntime(provider)

    def acquire() -> LocalModelLease:
        launch.wait(timeout=5)
        return runtime.acquire("model")

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(acquire)
        second = executor.submit(acquire)
        launch.wait(timeout=5)
        try:
            assert entered.wait(timeout=5)
        finally:
            proceed.set()
        lease_a = first.result(timeout=5)
        lease_b = second.result(timeout=5)

    assert lease_a.instance is lease_b.instance
    assert provider.load_calls == ["model"]
    assert runtime.release(lease_a) is None
    assert runtime.release(lease_b) is None
    assert provider.unload_calls == [lease_a.instance]


def test_slow_load_for_one_model_does_not_block_another() -> None:
    provider = _FakeProvider(
        (LocalModelDescriptor("slow"), LocalModelDescriptor("fast"))
    )
    slow_entered = Event()
    allow_slow = Event()

    def load(model_id: str) -> LocalModelInstance:
        if model_id == "slow":
            slow_entered.set()
            assert allow_slow.wait(timeout=5)
        return LocalModelInstance(model_id, f"{model_id}-id")

    provider.on_load = load
    runtime = LocalModelRuntime(provider)
    with ThreadPoolExecutor(max_workers=2) as executor:
        slow = executor.submit(runtime.acquire, "slow")
        assert slow_entered.wait(timeout=5)
        try:
            fast_lease = executor.submit(runtime.acquire, "fast").result(
                timeout=5
            )
        finally:
            allow_slow.set()
        slow_lease = slow.result(timeout=5)

    assert provider.load_calls == ["slow", "fast"]
    assert runtime.release(fast_lease) is None
    assert runtime.release(slow_lease) is None


def test_concurrent_final_release_only_unloads_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    entered = Event()
    allow = Event()
    second_waiting = Event()

    def unload(_instance: LocalModelInstance) -> None:
        entered.set()
        assert allow.wait(timeout=5)

    provider.on_unload = unload
    original_wait = runtime._changed.wait

    def wait_for_unload(timeout: float | None = None) -> bool:
        second_waiting.set()
        return original_wait(timeout)

    monkeypatch.setattr(runtime._changed, "wait", wait_for_unload)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(runtime.release, lease)
        assert entered.wait(timeout=5)
        second = executor.submit(runtime.release, lease)
        try:
            assert second_waiting.wait(timeout=5)
        finally:
            allow.set()
        assert first.result(timeout=5) is None
        assert second.result(timeout=5) is None

    assert provider.unload_calls == [lease.instance]


def test_concurrent_waiter_observes_cleanup_failure() -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    entered = Event()
    allow = Event()

    def unload(_instance: LocalModelInstance) -> None:
        entered.set()
        assert allow.wait(timeout=5)
        raise LocalModelTimeoutError("cleanup failed")

    provider.on_unload = unload
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(runtime.release, lease)
        assert entered.wait(timeout=5)
        second = executor.submit(runtime.release, lease)
        allow.set()
        first_failure = first.result(timeout=5)
        second_failure = second.result(timeout=5)

    assert first_failure is second_failure
    provider.on_unload = None
    assert runtime.release(lease) is None


def test_parallel_acquisition_waiters_receive_failed_load_without_retry() -> (
    None
):
    provider = _available()
    runtime = LocalModelRuntime(provider)
    entered = Event()
    allow = Event()

    def load(_model_id: str) -> LocalModelInstance:
        entered.set()
        assert allow.wait(timeout=5)
        raise LocalModelConnectionError("load unavailable")

    provider.on_load = load
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(runtime.acquire, "model")
        assert entered.wait(timeout=5)
        second = executor.submit(runtime.acquire, "model")
        allow.set()
        for result in (first, second):
            with pytest.raises(LocalModelConnectionError, match="unavailable"):
                result.result(timeout=5)

    assert provider.load_calls == ["model"]


def test_waiting_acquire_rejects_failed_cleanup() -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    entered = Event()
    allow = Event()

    def unload(_instance: LocalModelInstance) -> None:
        entered.set()
        assert allow.wait(timeout=5)
        raise LocalModelTimeoutError("cannot unload")

    provider.on_unload = unload
    with ThreadPoolExecutor(max_workers=2) as executor:
        releasing = executor.submit(runtime.release, lease)
        assert entered.wait(timeout=5)
        acquiring = executor.submit(runtime.acquire, "model")
        allow.set()
        assert isinstance(
            releasing.result(timeout=5), LocalModelCleanupFailure
        )
        with pytest.raises(LocalModelLifecycleError, match="Cleanup failed"):
            acquiring.result(timeout=5)


def test_corrupt_active_lifecycle_is_rejected_before_unload() -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    entry = runtime._models["model"]
    entry.phase = _Phase.LOADING

    with pytest.raises(LocalModelLifecycleError, match="Invalid release"):
        runtime.release(lease)
    assert provider.unload_calls == []

    entry.phase = _Phase.READY
    assert runtime.release(lease) is None
