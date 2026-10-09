"""Deterministic lease and ownership tests for local-model runtime."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from typing import cast

import pytest

from comfyreview.application.local_model_runtime import (
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
    """Do not contact LM Studio during construction."""
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
    assert provider.load_calls == []

    runtime.release(first)
    runtime.release(second)
    runtime.release(second)
    assert provider.unload_calls == []

    again = runtime.acquire("model")
    assert again.instance is instance
    assert provider.list_calls == 2
    runtime.release(again)
    assert provider.unload_calls == []


def test_multiple_existing_instances_use_stable_casefold_sorting() -> None:
    selected = LocalModelInstance("model", "a")
    provider = _FakeProvider(
        (
            LocalModelDescriptor(
                "model", (LocalModelInstance("model", "Z"), selected)
            ),
            LocalModelDescriptor("model", (LocalModelInstance("model", "A"),)),
            LocalModelDescriptor("other"),
        )
    )
    runtime = LocalModelRuntime(provider)

    lease = runtime.acquire("model")
    assert lease.instance.instance_id == "A"
    assert provider.load_calls == []
    runtime.release(lease)


def test_owned_model_reuses_instance_until_final_release() -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)

    first = runtime.acquire(" model ")
    second = runtime.acquire("model")
    assert first.instance is second.instance
    assert provider.list_calls == 1
    assert provider.load_calls == ["model"]

    runtime.release(first)
    assert provider.unload_calls == []
    runtime.release(first)
    assert provider.unload_calls == []
    runtime.release(second)
    runtime.release(second)
    assert provider.unload_calls == [first.instance]
    assert provider.unload_calls[0] is first.instance


def test_unknown_foreign_or_forged_leases_are_rejected() -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    foreign_runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    other = foreign_runtime.acquire("model")

    with pytest.raises(LocalModelLifecycleError, match="Unknown"):
        runtime.release(other)
    with pytest.raises(LocalModelLifecycleError, match="Unknown"):
        runtime.release(LocalModelLease(lease.instance, lease._issuer))
    with pytest.raises(LocalModelLifecycleError, match="Unknown"):
        runtime.release(cast(LocalModelLease, object()))
    assert provider.unload_calls == []

    runtime.release(lease)
    foreign_runtime.release(other)
    assert provider.unload_calls == [lease.instance, other.instance]


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
    runtime = LocalModelRuntime(provider)

    with pytest.raises(LocalModelUnavailableError, match="Model not found"):
        runtime.acquire("model")
    assert provider.load_calls == []


@pytest.mark.parametrize(
    "error_type",
    (
        LocalModelConnectionError,
        LocalModelTimeoutError,
        LocalModelProtocolError,
        LocalModelLifecycleError,
    ),
)
def test_discovery_errors_remain_normalized(
    error_type: type[Exception],
) -> None:
    provider = _available()

    def broken_list() -> tuple[LocalModelDescriptor, ...]:
        raise error_type("discovery failure")

    provider.on_list = broken_list
    runtime = LocalModelRuntime(provider)
    with pytest.raises(error_type, match="discovery failure"):
        runtime.acquire("model")
    assert provider.load_calls == []
    assert provider.unload_calls == []


@pytest.mark.parametrize(
    "error_type",
    (
        LocalModelConnectionError,
        LocalModelTimeoutError,
        LocalModelProtocolError,
        LocalModelLifecycleError,
        LocalModelUnavailableError,
    ),
)
def test_failed_load_is_not_owned_or_unloaded(
    error_type: type[Exception],
) -> None:
    provider = _available()

    def broken_load(model_id: str) -> LocalModelInstance:
        raise error_type("load failure")

    provider.on_load = broken_load
    runtime = LocalModelRuntime(provider)
    with pytest.raises(error_type, match="load failure"):
        runtime.acquire("model")
    assert provider.load_calls == ["model"]
    assert provider.unload_calls == []

    existing = LocalModelInstance("model", "external-after-failure")
    provider.models = (LocalModelDescriptor("model", (existing,)),)
    lease = runtime.acquire("model")
    assert lease.instance is existing
    runtime.release(lease)
    assert provider.unload_calls == []


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
    provider.on_load = lambda model_id: bad_instance
    runtime = LocalModelRuntime(provider)

    with pytest.raises(LocalModelProtocolError, match="invalid instance"):
        runtime.acquire("model")
    assert provider.unload_calls == []


def test_invalid_borrowed_instance_is_not_accepted() -> None:
    provider = _FakeProvider(
        (LocalModelDescriptor("model", (LocalModelInstance("other", "a"),)),)
    )
    runtime = LocalModelRuntime(provider)

    with pytest.raises(LocalModelProtocolError, match="invalid instance"):
        runtime.acquire("model")
    assert provider.load_calls == []


def test_failed_final_unload_is_recoverable_and_blocks_new_leases() -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    failed = True

    def unload(instance: LocalModelInstance) -> None:
        nonlocal failed
        if failed:
            failed = False
            raise LocalModelTimeoutError("unload failure")

    provider.on_unload = unload
    with pytest.raises(LocalModelTimeoutError, match="unload failure"):
        runtime.release(lease)
    with pytest.raises(LocalModelLifecycleError, match="Cleanup must"):
        runtime.acquire("model")
    assert provider.load_calls == ["model"]
    runtime.release(lease)
    runtime.release(lease)
    assert provider.unload_calls == [lease.instance, lease.instance]
    assert provider.unload_calls[0] is lease.instance


def test_retry_failed_unload_cannot_touch_unrelated_instances() -> None:
    first = LocalModelInstance("first", "first-id")
    second = LocalModelInstance("second", "second-id")
    provider = _FakeProvider(
        (LocalModelDescriptor("first"), LocalModelDescriptor("second"))
    )
    provider.on_load = (
        lambda model_id: first if model_id == "first" else second
    )
    runtime = LocalModelRuntime(provider)
    first_lease = runtime.acquire("first")
    second_lease = runtime.acquire("second")

    def unload(instance: LocalModelInstance) -> None:
        if instance == first and provider.unload_calls.count(first) == 1:
            raise LocalModelLifecycleError("failed first")

    provider.on_unload = unload
    with pytest.raises(LocalModelLifecycleError, match="failed first"):
        runtime.release(first_lease)
    runtime.release(second_lease)
    runtime.release(first_lease)
    assert provider.unload_calls == [first, second, first]


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
    runtime.release(lease_a)
    assert provider.unload_calls == []
    runtime.release(lease_b)
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
    runtime.release(fast_lease)
    runtime.release(slow_lease)


def test_parallel_releases_do_not_unload_before_final_lease() -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    leases = [runtime.acquire("model") for _ in range(3)]
    launch = Barrier(3)

    def release(lease: LocalModelLease) -> None:
        launch.wait(timeout=5)
        runtime.release(lease)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(release, leases[0])
        second = executor.submit(release, leases[1])
        launch.wait(timeout=5)
        first.result(timeout=5)
        second.result(timeout=5)

    assert provider.unload_calls == []
    runtime.release(leases[2])
    assert provider.unload_calls == [leases[2].instance]


def test_concurrent_final_release_only_unloads_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    entered = Event()
    allow = Event()
    second_waiting = Event()

    def unload(instance: LocalModelInstance) -> None:
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
        first.result(timeout=5)
        second.result(timeout=5)
    assert provider.unload_calls == [lease.instance]


def test_concurrent_waiter_sees_failed_unload_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    entered = Event()
    allow = Event()
    second_waiting = Event()

    def unload(instance: LocalModelInstance) -> None:
        entered.set()
        assert allow.wait(timeout=5)
        if len(provider.unload_calls) == 1:
            raise LocalModelTimeoutError("first attempt failed")

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
        with pytest.raises(LocalModelTimeoutError, match="first attempt"):
            first.result(timeout=5)
        with pytest.raises(LocalModelLifecycleError, match="Cleanup failed"):
            second.result(timeout=5)

    assert provider.unload_calls == [lease.instance]
    runtime.release(lease)
    assert provider.unload_calls == [lease.instance, lease.instance]


def test_parallel_acquisition_waiters_receive_failed_load_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    entered = Event()
    allow = Event()
    second_waiting = Event()

    def load(model_id: str) -> LocalModelInstance:
        entered.set()
        assert allow.wait(timeout=5)
        raise LocalModelConnectionError("load unavailable")

    provider.on_load = load
    original_wait = runtime._changed.wait

    def wait_for_load(timeout: float | None = None) -> bool:
        second_waiting.set()
        return original_wait(timeout)

    monkeypatch.setattr(runtime._changed, "wait", wait_for_load)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(runtime.acquire, "model")
        assert entered.wait(timeout=5)
        second = executor.submit(runtime.acquire, "model")
        try:
            assert second_waiting.wait(timeout=5)
        finally:
            allow.set()
        for result in (first, second):
            with pytest.raises(LocalModelConnectionError, match="unavailable"):
                result.result(timeout=5)

    assert provider.load_calls == ["model"]
    assert provider.unload_calls == []


def test_waiting_acquire_rejects_failed_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _available()
    runtime = LocalModelRuntime(provider)
    lease = runtime.acquire("model")
    entered = Event()
    allow = Event()
    waiting = Event()

    def unload(instance: LocalModelInstance) -> None:
        entered.set()
        assert allow.wait(timeout=5)
        raise LocalModelLifecycleError("cannot unload")

    provider.on_unload = unload
    original_wait = runtime._changed.wait

    def signal_wait(timeout: float | None = None) -> bool:
        waiting.set()
        return original_wait(timeout)

    monkeypatch.setattr(runtime._changed, "wait", signal_wait)
    with ThreadPoolExecutor(max_workers=2) as executor:
        releasing = executor.submit(runtime.release, lease)
        assert entered.wait(timeout=5)
        acquiring = executor.submit(runtime.acquire, "model")
        try:
            assert waiting.wait(timeout=5)
        finally:
            allow.set()
        with pytest.raises(LocalModelLifecycleError, match="cannot unload"):
            releasing.result(timeout=5)
        with pytest.raises(LocalModelLifecycleError, match="Cleanup failed"):
            acquiring.result(timeout=5)
    assert provider.load_calls == ["model"]


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
    runtime.release(lease)
    assert provider.unload_calls == [lease.instance]
