"""Versioned global prompt policies applied outside the selectable catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.workspace_settings import ContentLevel
from comfyreview.domain import PromptAtomUsage


@dataclass(frozen=True, slots=True)
class GlobalPromptPolicyRevision:
    """Describe one immutable quality or content-policy revision."""

    policy_uid: str
    policy_key: str
    policy_type: str
    revision_number: int
    name: str
    content_level: ContentLevel | None
    positive_atoms: tuple[PromptAtomUsage, ...] = ()
    negative_atoms: tuple[PromptAtomUsage, ...] = ()


@dataclass(frozen=True, slots=True)
class AppliedGlobalPromptPolicies:
    """Return rendered atoms and exact policy revision identities."""

    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]
    policy_uids: tuple[str, ...]


class GlobalPromptPolicyRepository(Protocol):
    """Read active immutable policy revisions for workspace content levels."""

    def list_active(
        self,
        enabled_content_levels: tuple[ContentLevel, ...],
    ) -> tuple[GlobalPromptPolicyRevision, ...]: ...


class GlobalPromptPolicyApplicator:
    """Append global atoms while preserving component-owned duplicates."""

    def apply(
        self,
        positive_atoms: tuple[PromptAtomUsage, ...],
        negative_atoms: tuple[PromptAtomUsage, ...],
        policies: tuple[GlobalPromptPolicyRevision, ...],
    ) -> AppliedGlobalPromptPolicies:
        """Apply policies in order with canonical, scope-local deduplication."""
        return AppliedGlobalPromptPolicies(
            positive_atoms=self._append_unique(
                positive_atoms,
                tuple(
                    atom
                    for policy in policies
                    for atom in policy.positive_atoms
                ),
            ),
            negative_atoms=self._append_unique(
                negative_atoms,
                tuple(
                    atom
                    for policy in policies
                    for atom in policy.negative_atoms
                ),
            ),
            policy_uids=tuple(policy.policy_uid for policy in policies),
        )

    @classmethod
    def _append_unique(
        cls,
        component_atoms: tuple[PromptAtomUsage, ...],
        global_atoms: tuple[PromptAtomUsage, ...],
    ) -> tuple[PromptAtomUsage, ...]:
        seen = {cls._canonical_text(atom.text) for atom in component_atoms}
        result = list(component_atoms)
        for atom in global_atoms:
            key = cls._canonical_text(atom.text)
            if key in seen:
                continue
            seen.add(key)
            result.append(atom)
        return tuple(result)

    @staticmethod
    def _canonical_text(value: str) -> str:
        return " ".join(str(value).casefold().split())
