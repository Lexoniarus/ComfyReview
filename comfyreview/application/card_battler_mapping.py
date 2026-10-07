"""Deterministic SemanticImageProfile to CardImprint mapping."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from comfyreview.application.card_battler_model import (
    CardBattlerMappingPolicy,
    CardBattlerModelRepository,
    CardBattlerRngPolicy,
    CompatibilityFact,
    FallbackCandidate,
    SemanticAffinity,
)


class CardImprintMappingError(RuntimeError):
    """Signal that a semantic profile cannot produce a legal CardImprint."""


@dataclass(frozen=True, slots=True)
class SemanticSignal:
    """One stable semantic concept observation in integer milli-space."""

    concept_key: str
    strength_milli: int

    def __post_init__(self) -> None:
        if not self.concept_key.strip():
            raise ValueError("semantic concept key must be non-empty")
        if not isinstance(self.strength_milli, int) or isinstance(
            self.strength_milli, bool
        ):
            raise ValueError("semantic strength must be an integer")
        if not 0 <= self.strength_milli <= 1000:
            raise ValueError("semantic strength must be between 0 and 1000")


@dataclass(frozen=True, slots=True)
class SemanticImageProfile:
    """Typed, game-mechanic-free input produced by the future Stage 1."""

    image_uid: str
    semantic_revision: str
    signals: tuple[SemanticSignal, ...]

    def __post_init__(self) -> None:
        if not self.image_uid.strip():
            raise ValueError("image_uid must be non-empty")
        if not self.semantic_revision.strip():
            raise ValueError("semantic_revision must be non-empty")
        object.__setattr__(self, "signals", tuple(self.signals))
        keys = [signal.concept_key for signal in self.signals]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate semantic concept keys are invalid")


@dataclass(frozen=True, slots=True)
class CardImprint:
    """Persistent four-axis Card DNA plus deterministic provenance."""

    world_style: str
    card_class: str
    combat_role: str
    trait_lineage: str
    source_image_uid: str
    semantic_revision: str
    ruleset_key: str
    ruleset_version: int
    mapping_policy_key: str
    mapping_policy_version: int
    rng_policy_key: str
    rng_policy_version: int
    rng_algorithm: str
    explicit_seed: int


@dataclass(frozen=True, slots=True)
class CandidateScore:
    """Inspectable score evidence for one selected or considered candidate."""

    entity_key: str
    semantic_component_milli: int
    compatibility_component_milli: int | None
    fallback_prior_milli: int
    final_score_milli: int
    fallback_admitted: bool


@dataclass(frozen=True, slots=True)
class MappingDecision:
    """Describe one deterministic dimension decision."""

    dimension: str
    selected_key: str
    counter: int
    candidates: tuple[CandidateScore, ...]


@dataclass(frozen=True, slots=True)
class CardImprintMappingResult:
    """Keep CardImprint identity clean while retaining mapping diagnostics."""

    imprint: CardImprint
    decisions: tuple[MappingDecision, ...]


class Sha256CounterV1:
    """Versioned deterministic integer-draw stream for Card-Imprint mapping."""

    algorithm = "sha256-counter-v1"

    def __init__(self, seed_material: tuple[str, ...]) -> None:
        payload = json.dumps(
            list(seed_material),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self._base_digest = hashlib.sha256(
            self.algorithm.encode("utf-8") + b"\0" + payload
        ).digest()

    @property
    def _base_digest_hex(self) -> str:
        """Return the frozen base digest for golden-vector diagnostics."""
        return self._base_digest.hex()

    def _digest_hex(self, counter: int) -> str:
        """Return the digest for one non-negative draw counter."""
        return self._digest(counter).hex()

    def _integer(self, counter: int) -> int:
        """Return the full digest interpreted as one non-negative integer."""
        return int.from_bytes(self._digest(counter), "big", signed=False)

    def _weighted_choice(
        self,
        candidates: tuple[tuple[str, int], ...],
        *,
        counter: int,
    ) -> str:
        """Choose from an already-stably-ordered integer-weighted pool."""
        if not candidates or any(weight <= 0 for _, weight in candidates):
            raise CardImprintMappingError(
                "weighted candidate pool must contain positive weights"
            )
        total = sum(weight for _, weight in candidates)
        ticket = self._integer(counter) % total
        cumulative = 0
        for key, weight in candidates[:-1]:
            cumulative += weight
            if ticket < cumulative:
                return key
        return candidates[-1][0]

    def _digest(self, counter: int) -> bytes:
        if counter < 0:
            raise ValueError("draw counter must be non-negative")
        return hashlib.sha256(
            self._base_digest + counter.to_bytes(8, "big", signed=False)
        ).digest()


class CardImprintMapper:
    """Authoritative deterministic Stage-2A semantic-to-card mapper."""

    _MAPPING_POLICY = ("semantic_imprint_mapping", 2)
    _RNG_POLICY = ("deterministic_rng", 2, Sha256CounterV1.algorithm)

    def __init__(self, repository: CardBattlerModelRepository) -> None:
        self._repository = repository

    def __call__(
        self,
        profile: SemanticImageProfile,
        *,
        explicit_seed: int,
    ) -> CardImprintMappingResult:
        """Map one semantic profile to a reproducible four-axis CardImprint."""
        if not isinstance(explicit_seed, int) or isinstance(
            explicit_seed, bool
        ):
            raise ValueError("explicit_seed must be an integer")
        ruleset = self._repository.resolve_ruleset()
        policy = self._repository.mapping_policy(ruleset)
        rng_policy = self._repository.rng_policy(ruleset)
        self._validate_policy_versions(policy, rng_policy)

        concepts = {
            item.key for item in self._repository.semantic_concepts(ruleset)
        }
        unknown = sorted(
            signal.concept_key
            for signal in profile.signals
            if signal.concept_key not in concepts
        )
        if unknown:
            raise CardImprintMappingError(
                "unknown semantic concept(s): " + ", ".join(unknown)
            )
        retained = tuple(
            sorted(
                (
                    signal
                    for signal in profile.signals
                    if signal.strength_milli >= policy.signal_min_milli
                ),
                key=lambda signal: signal.concept_key,
            )
        )
        stream = Sha256CounterV1(
            self._seed_material(
                rng_policy,
                profile,
                ruleset.key,
                ruleset.version,
                policy.key,
                policy.version,
                explicit_seed,
            )
        )

        world, world_decision = self._choose(
            dimension="world_style",
            counter=0,
            entity_keys=tuple(
                item.key for item in self._repository.world_styles(ruleset)
            ),
            affinities=self._repository.world_style_affinities(ruleset),
            fallback=self._repository.fallback_world_styles(policy, ruleset),
            compatibility=(),
            retained=retained,
            policy=policy,
            stream=stream,
        )
        card_class, class_decision = self._choose(
            dimension="card_class",
            counter=1,
            entity_keys=tuple(
                item.key for item in self._repository.card_classes(ruleset)
            ),
            affinities=self._repository.class_affinities(ruleset),
            fallback=self._repository.fallback_classes(policy, ruleset),
            compatibility=(
                self._compatibility_for_source(
                    self._repository.world_style_class_compatibility(ruleset),
                    world,
                ),
            ),
            retained=retained,
            policy=policy,
            stream=stream,
        )
        role, role_decision = self._choose(
            dimension="combat_role",
            counter=2,
            entity_keys=tuple(
                item.key for item in self._repository.combat_roles(ruleset)
            ),
            affinities=self._repository.role_affinities(ruleset),
            fallback=self._repository.fallback_roles(policy, ruleset),
            compatibility=(
                self._compatibility_for_source(
                    self._repository.class_role_compatibility(ruleset),
                    card_class,
                ),
            ),
            retained=retained,
            policy=policy,
            stream=stream,
        )
        lineage_compatibility = (
            self._compatibility_for_source(
                self._repository.class_lineage_compatibility(ruleset),
                card_class,
            ),
            self._compatibility_for_source(
                self._repository.role_lineage_compatibility(ruleset),
                role,
            ),
        )
        lineage, lineage_decision = self._choose(
            dimension="trait_lineage",
            counter=3,
            entity_keys=tuple(
                item.key for item in self._repository.trait_lineages(ruleset)
            ),
            affinities=self._repository.lineage_affinities(ruleset),
            fallback=self._repository.fallback_lineages(policy, ruleset),
            compatibility=lineage_compatibility,
            retained=retained,
            policy=policy,
            stream=stream,
        )

        imprint = CardImprint(
            world_style=world,
            card_class=card_class,
            combat_role=role,
            trait_lineage=lineage,
            source_image_uid=profile.image_uid,
            semantic_revision=profile.semantic_revision,
            ruleset_key=ruleset.key,
            ruleset_version=ruleset.version,
            mapping_policy_key=policy.key,
            mapping_policy_version=policy.version,
            rng_policy_key=rng_policy.key,
            rng_policy_version=rng_policy.version,
            rng_algorithm=rng_policy.algorithm,
            explicit_seed=explicit_seed,
        )
        return CardImprintMappingResult(
            imprint=imprint,
            decisions=(
                world_decision,
                class_decision,
                role_decision,
                lineage_decision,
            ),
        )

    @classmethod
    def _validate_policy_versions(
        cls,
        policy: CardBattlerMappingPolicy,
        rng_policy: CardBattlerRngPolicy,
    ) -> None:
        if (policy.key, policy.version) != cls._MAPPING_POLICY:
            raise CardImprintMappingError(
                f"unsupported mapping policy {policy.key}@{policy.version}"
            )
        if (
            rng_policy.key,
            rng_policy.version,
            rng_policy.algorithm,
        ) != cls._RNG_POLICY:
            raise CardImprintMappingError(
                "unsupported deterministic RNG policy "
                f"{rng_policy.key}@{rng_policy.version}:{rng_policy.algorithm}"
            )

    @staticmethod
    def _seed_material(
        policy: CardBattlerRngPolicy,
        profile: SemanticImageProfile,
        ruleset_key: str,
        ruleset_version: int,
        mapping_key: str,
        mapping_version: int,
        explicit_seed: int,
    ) -> tuple[str, ...]:
        available = {
            "image_uid": profile.image_uid,
            "semantic_revision": profile.semantic_revision,
            "ruleset_revision": f"{ruleset_key}@{ruleset_version}",
            "mapping_policy_revision": f"{mapping_key}@{mapping_version}",
            "explicit_seed": str(explicit_seed),
        }
        try:
            return tuple(available[name] for name in policy.seed_material)
        except KeyError as error:
            raise CardImprintMappingError(
                f"unsupported RNG seed material field: {error.args[0]}"
            ) from error

    def _choose(
        self,
        *,
        dimension: str,
        counter: int,
        entity_keys: tuple[str, ...],
        affinities: tuple[SemanticAffinity, ...],
        fallback: tuple[FallbackCandidate, ...],
        compatibility: tuple[tuple[CompatibilityFact, ...], ...],
        retained: tuple[SemanticSignal, ...],
        policy: CardBattlerMappingPolicy,
        stream: Sha256CounterV1,
    ) -> tuple[str, MappingDecision]:
        affinity_index = {
            (item.concept_key, item.entity_key): item.weight_milli
            for item in affinities
        }
        fallback_index = {
            item.entity_key: item.weight_milli for item in fallback
        }
        compatibility_indexes = tuple(
            {item.target_key: item for item in relation}
            for relation in compatibility
        )
        scored: dict[str, CandidateScore] = {}
        for key in entity_keys:
            compatibility_component = self._compatibility_component(
                key,
                compatibility_indexes,
                policy.compatibility_floor_milli,
            )
            if compatibility_indexes and compatibility_component is None:
                continue
            semantic_component = self._semantic_component(
                key, retained, affinity_index
            )
            fallback_prior = fallback_index.get(key, 0)
            final_score = self._final_score(
                semantic_component,
                compatibility_component,
                fallback_prior,
                policy,
            )
            if final_score >= policy.candidate_min_score_milli:
                scored[key] = CandidateScore(
                    entity_key=key,
                    semantic_component_milli=semantic_component,
                    compatibility_component_milli=compatibility_component,
                    fallback_prior_milli=fallback_prior,
                    final_score_milli=final_score,
                    fallback_admitted=False,
                )

        if (
            len(scored) < policy.minimum_candidate_count
            and policy.fallback_when_no_candidate
        ):
            active = set(entity_keys)
            for item in fallback:
                if item.entity_key in scored or item.entity_key not in active:
                    continue
                compatibility_component = self._compatibility_component(
                    item.entity_key,
                    compatibility_indexes,
                    policy.compatibility_floor_milli,
                )
                if compatibility_indexes and compatibility_component is None:
                    continue
                semantic_component = self._semantic_component(
                    item.entity_key, retained, affinity_index
                )
                final_score = self._final_score(
                    semantic_component,
                    compatibility_component,
                    item.weight_milli,
                    policy,
                )
                scored[item.entity_key] = CandidateScore(
                    entity_key=item.entity_key,
                    semantic_component_milli=semantic_component,
                    compatibility_component_milli=compatibility_component,
                    fallback_prior_milli=item.weight_milli,
                    final_score_milli=final_score,
                    fallback_admitted=True,
                )

        ordered = tuple(
            sorted(
                scored.values(),
                key=lambda item: (-item.final_score_milli, item.entity_key),
            )[: policy.top_pool_size]
        )
        if not ordered:
            raise CardImprintMappingError(
                f"no legal candidate for CardImprint dimension {dimension}"
            )
        if policy.use_seeded_weighted_selection:
            selected = stream._weighted_choice(
                tuple(
                    (item.entity_key, max(item.final_score_milli, 1))
                    for item in ordered
                ),
                counter=counter,
            )
        else:
            selected = ordered[0].entity_key
        return selected, MappingDecision(
            dimension=dimension,
            selected_key=selected,
            counter=counter,
            candidates=ordered,
        )

    @staticmethod
    def _semantic_component(
        entity_key: str,
        retained: tuple[SemanticSignal, ...],
        affinities: dict[tuple[str, str], int],
    ) -> int:
        denominator = sum(signal.strength_milli for signal in retained)
        if denominator == 0:
            return 0
        numerator = sum(
            signal.strength_milli
            * affinities.get((signal.concept_key, entity_key), 0)
            for signal in retained
        )
        return (numerator + denominator // 2) // denominator

    @staticmethod
    def _compatibility_component(
        entity_key: str,
        indexes: tuple[dict[str, CompatibilityFact], ...],
        floor: int,
    ) -> int | None:
        if not indexes:
            return None
        weights: list[int] = []
        for index in indexes:
            fact = index.get(entity_key)
            if fact is None or not fact.enabled or fact.weight_milli < floor:
                return None
            weights.append(fact.weight_milli)
        denominator = len(weights)
        return (sum(weights) + denominator // 2) // denominator

    @staticmethod
    def _final_score(
        semantic: int,
        compatibility: int | None,
        fallback_prior: int,
        policy: CardBattlerMappingPolicy,
    ) -> int:
        weighted_sum = (
            semantic * policy.semantic_affinity_weight
            + fallback_prior * policy.fallback_prior_weight
        )
        total_weight = (
            policy.semantic_affinity_weight + policy.fallback_prior_weight
        )
        if compatibility is not None:
            weighted_sum += compatibility * policy.compatibility_weight
            total_weight += policy.compatibility_weight
        return (weighted_sum + total_weight // 2) // total_weight

    @staticmethod
    def _compatibility_for_source(
        facts: tuple[CompatibilityFact, ...], source_key: str
    ) -> tuple[CompatibilityFact, ...]:
        return tuple(item for item in facts if item.source_key == source_key)
