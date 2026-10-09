"""Reference-counted ownership of concrete local-model instances."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from threading import Condition, Lock
from weakref import WeakSet

from comfyreview.application.local_models import (
    LocalModelInstance,
    LocalModelLifecycleError,
    LocalModelProtocolError,
    LocalModelProvider,
    LocalModelUnavailableError,
)


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class LocalModelLease:
    """Identify one caller's lease, issued by exactly one runtime."""

    instance: LocalModelInstance
    _issuer: object = field(repr=False)


class _Phase(Enum):
    LOADING = auto()
    READY = auto()
    UNLOADING = auto()
    FAILED_LOAD = auto()
    FAILED_UNLOAD = auto()


@dataclass(slots=True)
class _TrackedModel:
    phase: _Phase = _Phase.LOADING
    instance: LocalModelInstance | None = None
    owned: bool = False
    references: int = 0
    failure: Exception | None = None


class LocalModelRuntime:
    """Borrow existing models and unload only confirmed owned instances."""

    def __init__(self, provider: LocalModelProvider) -> None:
        self._provider = provider
        self._issuer = object()
        self._changed = Condition(Lock())
        self._models: dict[str, _TrackedModel] = {}
        self._active: dict[LocalModelLease, str] = {}
        self._issued: WeakSet[LocalModelLease] = WeakSet()

    def acquire(self, model_id: str) -> LocalModelLease:
        """Return a distinct lease for the requested exact model ID."""
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id is required")
        normalized = model_id.strip()

        with self._changed:
            while True:
                entry = self._models.get(normalized)
                if entry is None:
                    entry = _TrackedModel()
                    self._models[normalized] = entry
                    break
                if entry.phase is _Phase.READY:
                    return self._issue_lease(normalized, entry)
                if entry.phase is _Phase.FAILED_UNLOAD:
                    raise LocalModelLifecycleError(
                        "Cleanup must be retried before acquiring "
                        f"{normalized}"
                    )
                self._changed.wait()
                if entry.phase is _Phase.FAILED_LOAD:
                    assert entry.failure is not None
                    raise entry.failure
                if entry.phase is _Phase.FAILED_UNLOAD:
                    raise LocalModelLifecycleError(
                        f"Cleanup failed for {normalized}; retry release"
                    )

        try:
            instance, owned = self._discover_or_load(normalized)
        except Exception as error:
            # Publish the same failure to concurrent callers; do not retry it.
            with self._changed:
                entry.phase = _Phase.FAILED_LOAD
                entry.failure = error
                del self._models[normalized]
                self._changed.notify_all()
            raise

        with self._changed:
            entry.instance = instance
            entry.owned = owned
            entry.phase = _Phase.READY
            lease = self._issue_lease(normalized, entry)
            self._changed.notify_all()
            return lease

    def release(self, lease: LocalModelLease) -> None:
        """Release one known lease; retry failed final owned cleanup."""
        with self._changed:
            if (
                not isinstance(lease, LocalModelLease)
                or lease._issuer is not self._issuer
                or lease not in self._issued
            ):
                raise LocalModelLifecycleError(
                    "Unknown or foreign model lease"
                )

            while True:
                model_id = self._active.get(lease)
                if model_id is None:
                    return
                entry = self._models[model_id]
                if entry.phase is _Phase.UNLOADING:
                    self._changed.wait()
                    if entry.phase is _Phase.FAILED_UNLOAD:
                        raise LocalModelLifecycleError(
                            f"Cleanup failed for {model_id}; retry release"
                        )
                    continue
                if entry.phase is _Phase.READY:
                    if entry.references > 1:
                        entry.references -= 1
                        del self._active[lease]
                        return
                    if not entry.owned:
                        entry.references = 0
                        del self._active[lease]
                        del self._models[model_id]
                        self._changed.notify_all()
                        return
                elif entry.phase is not _Phase.FAILED_UNLOAD:
                    raise LocalModelLifecycleError(
                        f"Invalid release lifecycle for {model_id}"
                    )

                entry.phase = _Phase.UNLOADING
                instance = entry.instance
                assert instance is not None
                break

        unloaded = False
        try:
            self._provider.unload_model(instance)
            unloaded = True
        finally:
            with self._changed:
                if unloaded:
                    entry.references = 0
                    del self._active[lease]
                    del self._models[model_id]
                else:
                    entry.phase = _Phase.FAILED_UNLOAD
                self._changed.notify_all()

    def _issue_lease(
        self, model_id: str, entry: _TrackedModel
    ) -> LocalModelLease:
        assert entry.instance is not None
        lease = LocalModelLease(entry.instance, self._issuer)
        entry.references += 1
        self._issued.add(lease)
        self._active[lease] = model_id
        return lease

    def _discover_or_load(
        self, model_id: str
    ) -> tuple[LocalModelInstance, bool]:
        descriptors = self._provider.list_models()
        matching = tuple(
            model for model in descriptors if model.model_id == model_id
        )
        if not matching:
            raise LocalModelUnavailableError(f"Model not found: {model_id}")

        loaded = tuple(
            instance
            for model in matching
            for instance in model.loaded_instances
        )
        if loaded:
            for instance in loaded:
                self._validate_instance(model_id, instance)
            selected = min(
                loaded,
                key=lambda value: (
                    value.instance_id.casefold(),
                    value.instance_id,
                ),
            )
            return selected, False

        instance = self._provider.load_model(model_id)
        self._validate_instance(model_id, instance)
        return instance, True

    @staticmethod
    def _validate_instance(
        model_id: str, instance: LocalModelInstance
    ) -> None:
        if (
            not isinstance(instance, LocalModelInstance)
            or instance.model_id != model_id
            or not isinstance(instance.instance_id, str)
            or not instance.instance_id.strip()
        ):
            raise LocalModelProtocolError(
                f"Provider returned an invalid instance for {model_id}"
            )
