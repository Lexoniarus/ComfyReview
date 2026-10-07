"""Deterministic example evidence for reviewed Playground drafts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.generation_geometry import (
    AspectFormat,
    ResolutionClass,
)
from comfyreview.domain import PromptAtomUsage


@dataclass(frozen=True, slots=True)
class PlaygroundEvidenceQuery:
    """Carry the current prompt, sampler and geometry comparison values."""

    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]
    checkpoint: str
    sampler: str
    scheduler: str
    steps: int
    cfg: float
    denoise: float
    aspect_format: AspectFormat
    resolution_class: ResolutionClass


@dataclass(frozen=True, slots=True)
class PlaygroundEvidenceCandidate:
    """Expose one visible historical image to pure scoring policy."""

    image_uid: str
    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]
    checkpoint: str
    sampler: str
    scheduler: str
    steps: int | None
    cfg: float | None
    denoise: float | None
    aspect_format: AspectFormat | None
    resolution_class: ResolutionClass | None
    average_rating: float | None
    rating_count: int


@dataclass(frozen=True, slots=True)
class PlaygroundEvidenceMatch:
    """Summarize the selected stable image and review evidence."""

    image_uid: str
    average_rating: float | None
    rating_count: int


@dataclass(frozen=True, slots=True)
class PlaygroundEvidence:
    """Return independently selected prompt and sampler examples."""

    prompt_match: PlaygroundEvidenceMatch | None
    sampler_match: PlaygroundEvidenceMatch | None
    prompt_matches: tuple[PlaygroundEvidenceMatch, ...] = ()
    sampler_matches: tuple[PlaygroundEvidenceMatch, ...] = ()


class PlaygroundEvidenceRepository(Protocol):
    """Read only images allowed by the central visibility policy."""

    def list_candidates(self) -> tuple[PlaygroundEvidenceCandidate, ...]: ...


class PlaygroundEvidenceService:
    """Rank visible evidence with deterministic product semantics."""

    def __init__(self, repository: PlaygroundEvidenceRepository) -> None:
        self._repository = repository

    def find(self, query: PlaygroundEvidenceQuery) -> PlaygroundEvidence:
        """Return the best prompt and sampler candidates independently."""
        candidates = self._repository.list_candidates()
        prompt = self._prompt_matches(query, candidates)
        sampler = self._sampler_matches(query, candidates)
        return PlaygroundEvidence(
            prompt_match=self._match(prompt[0]) if prompt else None,
            sampler_match=self._match(sampler[0]) if sampler else None,
            prompt_matches=self._matches(prompt),
            sampler_matches=self._matches(sampler),
        )

    @classmethod
    def _prompt_matches(
        cls,
        query: PlaygroundEvidenceQuery,
        candidates: tuple[PlaygroundEvidenceCandidate, ...],
    ) -> tuple[PlaygroundEvidenceCandidate, ...]:
        scored = [
            (cls._prompt_score(query, candidate), candidate)
            for candidate in candidates
        ]
        matching = [item for item in scored if item[0][2] > 0]
        matching.sort(key=lambda item: item[0], reverse=True)
        return tuple(item[1] for item in matching[:8])

    @classmethod
    def _sampler_matches(
        cls,
        query: PlaygroundEvidenceQuery,
        candidates: tuple[PlaygroundEvidenceCandidate, ...],
    ) -> tuple[PlaygroundEvidenceCandidate, ...]:
        ordered = sorted(
            candidates,
            key=lambda candidate: cls._sampler_score(query, candidate),
            reverse=True,
        )
        return tuple(ordered[:8])

    @classmethod
    def _prompt_score(
        cls,
        query: PlaygroundEvidenceQuery,
        candidate: PlaygroundEvidenceCandidate,
    ) -> tuple[int, int, int, int, float, int, str]:
        query_atoms = cls._atoms_by_scope(
            query.positive_atoms, query.negative_atoms
        )
        candidate_atoms = cls._atoms_by_scope(
            candidate.positive_atoms, candidate.negative_atoms
        )
        shared = set(query_atoms) & set(candidate_atoms)
        weight_distance = sum(
            abs(query_atoms[key] - candidate_atoms[key]) for key in shared
        )
        return (
            int(candidate.aspect_format == query.aspect_format),
            int(candidate.resolution_class == query.resolution_class),
            len(shared),
            -weight_distance,
            candidate.average_rating
            if candidate.average_rating is not None
            else -1.0,
            candidate.rating_count,
            candidate.image_uid,
        )

    @staticmethod
    def _sampler_score(
        query: PlaygroundEvidenceQuery,
        candidate: PlaygroundEvidenceCandidate,
    ) -> tuple[int, int, int, int, int, float, float, int, str]:
        numeric_distance = (
            abs(query.steps - (candidate.steps or 0))
            + abs(query.cfg - (candidate.cfg or 0.0))
            + abs(query.denoise - (candidate.denoise or 0.0))
        )
        return (
            int(candidate.aspect_format == query.aspect_format),
            int(candidate.resolution_class == query.resolution_class),
            int(candidate.checkpoint == query.checkpoint),
            int(candidate.sampler == query.sampler),
            int(candidate.scheduler == query.scheduler),
            -numeric_distance,
            candidate.average_rating
            if candidate.average_rating is not None
            else -1.0,
            candidate.rating_count,
            candidate.image_uid,
        )

    @staticmethod
    def _atoms_by_scope(
        positive: tuple[PromptAtomUsage, ...],
        negative: tuple[PromptAtomUsage, ...],
    ) -> dict[tuple[str, str], int]:
        return {
            **{
                ("pos", item.text.casefold()): item.weight_milli
                for item in positive
            },
            **{
                ("neg", item.text.casefold()): item.weight_milli
                for item in negative
            },
        }

    @staticmethod
    def _match(
        candidate: PlaygroundEvidenceCandidate,
    ) -> PlaygroundEvidenceMatch:
        return PlaygroundEvidenceMatch(
            image_uid=candidate.image_uid,
            average_rating=candidate.average_rating,
            rating_count=candidate.rating_count,
        )

    @staticmethod
    def _matches(
        candidates: tuple[PlaygroundEvidenceCandidate, ...],
    ) -> tuple[PlaygroundEvidenceMatch, ...]:
        return tuple(
            PlaygroundEvidenceMatch(
                image_uid=item.image_uid,
                average_rating=item.average_rating,
                rating_count=item.rating_count,
            )
            for item in candidates
        )
