"""Deterministic joint SemanticImageProfile to CardImprint mapping."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import product

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
class _DimensionCandidate:
    """One semantically or fallback-admissible axis, never RNG-selected."""

    key: str
    semantic_milli: int
    fallback_prior_milli: int
    fallback_admitted: bool


@dataclass(frozen=True, slots=True)
class ImprintCandidateScore:
    """Full candidate and inspectable integer-score evidence."""

    world_style: str
    card_class: str
    combat_role: str
    trait_lineage: str
    key: str
    semantic_component_milli: int
    compatibility_component_milli: int
    fallback_prior_milli: int
    final_score_milli: int
    fallback_dimensions: tuple[str, ...]
    axis_semantic_milli: tuple[int, int, int, int]
    compatibility_milli: tuple[int, int, int, int]
    axis_fallback_prior_milli: tuple[int, int, int, int]

@dataclass(frozen=True, slots=True)
class CardImprintMappingResult:
    """Selected full candidate, one draw counter, and the top pool."""

    imprint: CardImprint
    selected_candidate: ImprintCandidateScore
    selection_counter: int | None
    candidates: tuple[ImprintCandidateScore, ...]


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
    """Authoritative deterministic Stage-2A joint semantic-to-card mapper."""

    _MAPPING_POLICY = ("semantic_imprint_mapping", 2)
    _RNG_POLICY = ("deterministic_rng", 2, Sha256CounterV1.algorithm)
    _FINAL_DRAW_COUNTER = 0
    _DIMENSIONS = (
        "world_style",
        "card_class",
        "combat_role",
        "trait_lineage",
    )

    def __init__(self, repository: CardBattlerModelRepository) -> None:
        self._repository = repository

    def __call__(
        self,
        profile: SemanticImageProfile,
        *,
        explicit_seed: int,
    ) -> CardImprintMappingResult:
        """Score legal full imprints, then select once from the top pool."""
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

        dimension_pools = (
            self._dimension_pool(
                dimension="world_style",
                entity_keys=tuple(
                    item.key for item in self._repository.world_styles(ruleset)
                ),
                affinities=self._repository.world_style_affinities(ruleset),
                fallback=self._repository.fallback_world_styles(
                    policy, ruleset
                ),
                retained=retained,
                policy=policy,
            ),
            self._dimension_pool(
                dimension="card_class",
                entity_keys=tuple(
                    item.key for item in self._repository.card_classes(ruleset)
                ),
                affinities=self._repository.class_affinities(ruleset),
                fallback=self._repository.fallback_classes(policy, ruleset),
                retained=retained,
                policy=policy,
            ),
            self._dimension_pool(
                dimension="combat_role",
                entity_keys=tuple(
                    item.key for item in self._repository.combat_roles(ruleset)
                ),
                affinities=self._repository.role_affinities(ruleset),
                fallback=self._repository.fallback_roles(policy, ruleset),
                retained=retained,
                policy=policy,
            ),
            self._dimension_pool(
                dimension="trait_lineage",
                entity_keys=tuple(
                    item.key
                    for item in self._repository.trait_lineages(ruleset)
                ),
                affinities=self._repository.lineage_affinities(ruleset),
                fallback=self._repository.fallback_lineages(policy, ruleset),
                retained=retained,
                policy=policy,
            ),
        )
        compatibility_indexes = (
            self._compatibility_index(
                self._repository.world_style_class_compatibility(ruleset)
            ),
            self._compatibility_index(
                self._repository.class_role_compatibility(ruleset)
            ),
            self._compatibility_index(
                self._repository.class_lineage_compatibility(ruleset)
            ),
            self._compatibility_index(
                self._repository.role_lineage_compatibility(ruleset)
            ),
        )
        scored: list[ImprintCandidateScore] = []
        for axes in product(*dimension_pools):
            world, card_class, role, lineage = axes
            relations = (
                (world.key, card_class.key),
                (card_class.key, role.key),
                (card_class.key, lineage.key),
                (role.key, lineage.key),
            )
            compatible_weights: list[int] = []
            for index, pair in zip(compatibility_indexes, relations):
                fact = index.get(pair)
                if (
                    fact is None
                    or not fact.enabled
                    or fact.weight_milli < policy.compatibility_floor_milli
                ):
                    break
                compatible_weights.append(fact.weight_milli)
            if len(compatible_weights) != len(compatibility_indexes):
                continue

            semantics = (
                world.semantic_milli,
                card_class.semantic_milli,
                role.semantic_milli,
                lineage.semantic_milli,
            )
            priors = (
                world.fallback_prior_milli,
                card_class.fallback_prior_milli,
                role.fallback_prior_milli,
                lineage.fallback_prior_milli,
            )
            compatibility_weights = (
                compatible_weights[0],
                compatible_weights[1],
                compatible_weights[2],
                compatible_weights[3],
            )
            semantic_component = self._rounded_mean(semantics)
            compatibility_component = self._rounded_mean(
                compatibility_weights
            )
            fallback_prior_component = self._rounded_mean(priors)
            final_score = self._final_score(
                semantic_component,
                compatibility_component,
                fallback_prior_component,
                policy,
            )
            if final_score < policy.candidate_min_score_milli:
                continue
            scored.append(
                ImprintCandidateScore(
                    world_style=world.key,
                    card_class=card_class.key,
                    combat_role=role.key,
                    trait_lineage=lineage.key,
                    key="|".join(
                        (world.key, card_class.key, role.key, lineage.key)
                    ),
                    semantic_component_milli=semantic_component,
                    compatibility_component_milli=compatibility_component,
                    fallback_prior_milli=fallback_prior_component,
                    final_score_milli=final_score,
                    fallback_dimensions=tuple(
                        name
                        for name, item in zip(self._DIMENSIONS, axes)
                        if item.fallback_admitted
                    ),
                    axis_semantic_milli=semantics,
                    compatibility_milli=compatibility_weights,
                    axis_fallback_prior_milli=priors,
                )
            )

        ordered = sorted(
            scored, key=lambda item: (-item.final_score_milli, item.key)
        )
        candidates = tuple(ordered[: policy.top_pool_size])
        if not candidates:
            raise CardImprintMappingError(
                "no legal complete CardImprint candidate"
            )

        counter: int | None = None
        selected = candidates[0]
        if policy.use_seeded_weighted_selection:
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
            # Exactly one mapping draw, on the complete pool, at counter 0.
            counter = self._FINAL_DRAW_COUNTER
            selected_key = stream._weighted_choice(
                tuple(
                    (item.key, max(item.final_score_milli, 1))
                    for item in candidates
                ),
                counter=counter,
            )
            selected = next(
                item for item in candidates if item.key == selected_key
            )

        imprint = CardImprint(
            world_style=selected.world_style,
            card_class=selected.card_class,
            combat_role=selected.combat_role,
            trait_lineage=selected.trait_lineage,
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
            selected_candidate=selected,
            selection_counter=counter,
            candidates=candidates,
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

    def _dimension_pool(
        self,
        *,
        dimension: str,
        entity_keys: tuple[str, ...],
        affinities: tuple[SemanticAffinity, ...],
        fallback: tuple[FallbackCandidate, ...],
        retained: tuple[SemanticSignal, ...],
        policy: CardBattlerMappingPolicy,
    ) -> tuple[_DimensionCandidate, ...]:
        """Admit semantic evidence first, then configured fallback if needed.

        Compatibility never admits an unsupported axis; its four relations are
        evaluated only after these admissible pools are constructed.
        """
        affinity_index = {
            (item.concept_key, item.entity_key): item.weight_milli
            for item in affinities
        }
        fallback_index = {
            item.entity_key: item.weight_milli for item in fallback
        }
        scored: dict[str, _DimensionCandidate] = {}
        for key in sorted(set(entity_keys)):
            semantic_component = self._semantic_component(
                key, retained, affinity_index
            )
            if (
                semantic_component == 0
                or semantic_component < policy.candidate_min_score_milli
            ):
                continue
            scored[key] = _DimensionCandidate(
                key=key,
                semantic_milli=semantic_component,
                fallback_prior_milli=fallback_index.get(key, 0),
                fallback_admitted=False,
            )
        if (
            len(scored) < policy.minimum_candidate_count
            and policy.fallback_when_no_candidate
        ):
            for key in sorted(fallback_index):
                if key in scored or key not in entity_keys:
                    continue
                scored[key] = _DimensionCandidate(
                    key=key,
                    semantic_milli=self._semantic_component(
                        key, retained, affinity_index
                    ),
                    fallback_prior_milli=fallback_index[key],
                    fallback_admitted=True,
                )
        if not scored:
            raise CardImprintMappingError(
                "no admissible candidate for CardImprint dimension "
                f"{dimension}"
            )
        return tuple(scored[key] for key in sorted(scored))

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
    def _rounded_mean(values: tuple[int, ...]) -> int:
        return (sum(values) + len(values) // 2) // len(values)

    @staticmethod
    def _compatibility_index(
        facts: tuple[CompatibilityFact, ...],
    ) -> dict[tuple[str, str], CompatibilityFact]:
        return {(fact.source_key, fact.target_key): fact for fact in facts}

    @staticmethod
    def _final_score(
        semantic: int,
        compatibility: int,
        fallback_prior: int,
        policy: CardBattlerMappingPolicy,
    ) -> int:
        weighted_sum = (
            semantic * policy.semantic_affinity_weight
            + compatibility * policy.compatibility_weight
            + fallback_prior * policy.fallback_prior_weight
        )
        total_weight = (
            policy.semantic_affinity_weight
            + policy.compatibility_weight
            + policy.fallback_prior_weight
        )
        return (weighted_sum + total_weight // 2) // total_weight


# The existing application package re-exports these names.  They now refer to
# complete-imprint scores; there are no per-axis MappingDecision records.
CandidateScore = ImprintCandidateScore
MappingDecision = ImprintCandidateScore
