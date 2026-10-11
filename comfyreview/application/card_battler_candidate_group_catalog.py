"""Application queries and terminal commands for Candidate groups."""

from __future__ import annotations

from comfyreview.application.card_battler_candidate_group_service import (
    InitialCardCandidateGroupService,
)
from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroup,
    CardCandidateGroupConflictError,
    CardCandidateGroupKind,
    CardCandidateGroupNotFoundError,
    CardCandidateGroupRepository,
)


class CardCandidateGroupCatalogService:
    """Read, reject, and explicitly retry complete Candidate groups."""

    def __init__(
        self,
        *,
        groups: CardCandidateGroupRepository,
        initial_groups: InitialCardCandidateGroupService,
    ) -> None:
        self._groups = groups
        self._initial_groups = initial_groups

    def list_groups(self) -> tuple[CardCandidateGroup, ...]:
        """Return all Candidate groups in repository-defined stable order."""
        return self._groups.list_groups()

    def get(self, group_id: str) -> CardCandidateGroup:
        """Return one Candidate group or a typed not-found failure."""
        group = self._groups.get(group_id)
        if group is None:
            raise CardCandidateGroupNotFoundError(group_id)
        return group

    def reject(
        self,
        group_id: str,
        *,
        expected_revision: int,
    ) -> CardCandidateGroup:
        """Reject one terminal comparison without changing any Card."""
        self.get(group_id)
        return self._groups.reject(
            group_id,
            expected_revision=expected_revision,
        )

    def retry_initial(
        self,
        group_id: str,
        *,
        expected_revision: int,
    ) -> CardCandidateGroup:
        """Reject an initial group and reserve a fully new analysis."""
        group = self.get(group_id)
        if group.kind is not CardCandidateGroupKind.INITIAL:
            raise CardCandidateGroupConflictError(
                "Only an initial Candidate group can restart analysis"
            )
        rejected = self._groups.reject(
            group_id,
            expected_revision=expected_revision,
        )
        return self._initial_groups.reserve(rejected.source_image_uid)
