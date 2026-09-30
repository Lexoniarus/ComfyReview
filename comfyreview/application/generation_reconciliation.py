"""Application service for recovering ambiguous generation lifecycle state."""

from __future__ import annotations

import logging
from collections.abc import Callable

from comfyreview.application.comfyui import ComfyUiError, ComfyUiProvider
from comfyreview.application.generation import (
    GenerationMutationError,
    GenerationOutputCollection,
    GenerationReconciliationRequired,
    GenerationRecord,
    GenerationRepository,
    GenerationSubmission,
    GenerationValidationError,
)


class GenerationReconciliationService:
    """Resolve ambiguous generation state without resubmitting work."""

    def __init__(
        self,
        *,
        generations: GenerationRepository,
        comfyui: ComfyUiProvider,
        outputs: GenerationOutputCollection,
    ) -> None:
        self._generations = generations
        self._comfyui = comfyui
        self._outputs = outputs
        self._logger = logging.getLogger("comfyreview.generation")

    def reconcile(
        self,
        generation_uid: str,
        *,
        prompt_id: str | None = None,
    ) -> GenerationSubmission:
        """Reconcile one ambiguous generation against outputs and ComfyUI."""
        normalized_uid = self._required(generation_uid, "generation_uid")
        record = self._generations.get(normalized_uid)
        if record.status != "reconciliation_required":
            raise GenerationValidationError(
                "generation is not awaiting reconciliation"
            )
        record = self._assign_prompt_id(record, prompt_id)

        if self._outputs.outputs_complete(record.generation_uid):
            return self._complete_from_persisted_outputs(record)
        if record.prompt_id is None:
            self._logger.warning(
                "generation.reconciliation_manual_prompt_required",
                extra={"generation_id": record.generation_uid},
            )
            return self._submission(record)

        try:
            external = self._comfyui.get_status(record.prompt_id)
        except ComfyUiError as error:
            self._logger.warning(
                "generation.reconciliation_deferred",
                extra={
                    "generation_id": record.generation_uid,
                    "prompt_id": record.prompt_id,
                    "error_type": type(error).__name__,
                },
            )
            return self._submission(record)

        if external.failed:
            updated = self._transition(
                record,
                lambda: self._generations.mark_failed(
                    record.generation_uid,
                    external.message or "comfyui_failed",
                ),
                failure_reason="reconciliation_failed_state_write",
            )
        elif external.completed:
            updated = self._collect_and_complete(record)
        elif external.state == "running":
            updated = self._transition(
                record,
                lambda: self._generations.mark_running(record.generation_uid),
                failure_reason="reconciliation_running_state_write",
            )
        else:
            updated = self._transition(
                record,
                lambda: self._generations.mark_submitted(
                    record.generation_uid,
                    record.prompt_id or "",
                ),
                failure_reason="reconciliation_submitted_state_write",
            )
        self._logger.info(
            "generation.reconciled",
            extra={
                "generation_id": updated.generation_uid,
                "prompt_id": updated.prompt_id,
                "status": updated.status,
            },
        )
        return self._submission(updated)

    def _assign_prompt_id(
        self,
        record: GenerationRecord,
        prompt_id: str | None,
    ) -> GenerationRecord:
        normalized = str(prompt_id or "").strip()
        if not normalized:
            return record
        if record.prompt_id is not None and record.prompt_id != normalized:
            raise GenerationValidationError(
                "prompt_id conflicts with persisted external identity"
            )
        if record.prompt_id == normalized:
            return record
        try:
            return self._generations.mark_reconciliation_required(
                record.generation_uid,
                normalized,
                "operator_prompt_id_assigned",
            )
        except Exception as error:
            raise GenerationMutationError(
                "Could not persist the reconciliation prompt_id"
            ) from error

    def _complete_from_persisted_outputs(
        self,
        record: GenerationRecord,
    ) -> GenerationSubmission:
        updated = self._transition(
            record,
            lambda: self._generations.mark_completed(record.generation_uid),
            failure_reason="reconciliation_completed_state_write",
        )
        self._logger.info(
            "generation.reconciled_from_outputs",
            extra={
                "generation_id": updated.generation_uid,
                "prompt_id": updated.prompt_id,
                "status": updated.status,
            },
        )
        return self._submission(updated)

    def _collect_and_complete(
        self,
        record: GenerationRecord,
    ) -> GenerationRecord:
        assert record.prompt_id is not None
        try:
            self._outputs.collect(record.generation_uid, record.prompt_id)
            return self._generations.mark_completed(record.generation_uid)
        except Exception as error:
            self._keep_reconciliation(
                record,
                "reconciliation_output_confirmation_failed",
            )
            raise GenerationReconciliationRequired(
                "Generation outputs still require reconciliation"
            ) from error

    def _transition(
        self,
        record: GenerationRecord,
        operation: Callable[[], GenerationRecord],
        *,
        failure_reason: str,
    ) -> GenerationRecord:
        try:
            result = operation()
        except Exception as error:
            self._keep_reconciliation(record, failure_reason)
            raise GenerationMutationError(
                "Could not persist reconciled generation state"
            ) from error
        return result

    def _keep_reconciliation(
        self,
        record: GenerationRecord,
        reason: str,
    ) -> None:
        try:
            self._generations.mark_reconciliation_required(
                record.generation_uid,
                record.prompt_id,
                reason,
            )
        except Exception as error:
            raise GenerationMutationError(
                "Could not preserve reconciliation state"
            ) from error

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise GenerationValidationError(f"{field} is required")
        return normalized

    @staticmethod
    def _submission(record: GenerationRecord) -> GenerationSubmission:
        return GenerationSubmission(
            generation_uid=record.generation_uid,
            status=record.status,
            prompt_id=record.prompt_id,
        )
