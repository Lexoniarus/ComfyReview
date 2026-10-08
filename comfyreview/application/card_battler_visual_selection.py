"""Focused deterministic selection policies for visual prompt projection."""

from __future__ import annotations

from dataclasses import dataclass

from comfyreview.application.card_battler_model import CardBattlerModelInvalid
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.application.card_battler_visual_model import (
    PromptAtomExclusion,
    PromptGroupDefinition,
    VisualProgressionProfile,
    VisualProjectionPolicy,
    VisualPromptAtomDefinition,
    VisualPromptBinding,
    VisualPromptScope,
)
from comfyreview.application.card_battler_visuals import (
    VisualPromptAtom,
    VisualPromptAtomSource,
    VisualPromptDiagnostic,
)


@dataclass(frozen=True, slots=True)
class _ProjectedBinding:
    binding: VisualPromptBinding
    canonical_text: str
    weight_milli: int


@dataclass(frozen=True, slots=True)
class _MergedAtom:
    key: str
    canonical_text: str
    scope: VisualPromptScope
    weight_milli: int
    required: bool
    priority: int
    selection_weight_milli: int
    prompt_group_key: str | None
    sources: tuple[VisualPromptAtomSource, ...]

    def _public(self) -> VisualPromptAtom:
        return VisualPromptAtom(
            key=self.key,
            canonical_text=self.canonical_text,
            scope=self.scope,
            weight_milli=self.weight_milli,
            required=self.required,
            priority=self.priority,
            sources=self.sources,
        )


class _VisualPromptSelectionPolicy:
    """Resolve binding modes, groups, exclusions, and stable output order."""

    def __init__(
        self,
        policy: VisualProjectionPolicy,
        progression: VisualProgressionProfile,
        groups: tuple[PromptGroupDefinition, ...],
        exclusions: tuple[PromptAtomExclusion, ...],
        random: DomainSeparatedCardRandom,
    ) -> None:
        self._policy = policy
        self._progression = progression
        self._groups = {group.key: group for group in groups}
        self._exclusions = frozenset(
            frozenset((item.atom_a_key, item.atom_b_key))
            for item in exclusions
        )
        self._random = random

    def _select(
        self,
        definitions: tuple[VisualPromptAtomDefinition, ...],
        bindings: tuple[VisualPromptBinding, ...],
    ) -> tuple[
        tuple[VisualPromptAtom, ...], tuple[VisualPromptDiagnostic, ...]
    ]:
        definition_by_key = {item.key: item for item in definitions}
        projected = tuple(
            self._project(binding, definition_by_key) for binding in bindings
        )
        forbidden = frozenset(
            (item.binding.scope, item.binding.atom_key)
            for item in projected
            if item.binding.mode == "forbidden"
        )
        merged = self._merge(
            tuple(
                item for item in projected if item.binding.mode != "forbidden"
            )
        )
        diagnostics: list[VisualPromptDiagnostic] = []
        available: list[_MergedAtom] = []
        for atom in merged:
            identity = (atom.scope, atom.key)
            if identity in forbidden:
                if atom.required:
                    raise CardBattlerModelInvalid(
                        f"required visual atom {atom.key!r} is forbidden"
                    )
                diagnostics.append(
                    self._diagnostic(
                        "optional-atom-forbidden",
                        f"Optional atom {atom.key!r} was forbidden.",
                        atom,
                    )
                )
            elif atom.weight_milli <= 0:
                if atom.required:
                    raise CardBattlerModelInvalid(
                        f"required visual atom {atom.key!r} has zero intensity"
                    )
                diagnostics.append(
                    self._diagnostic(
                        "optional-atom-zero-intensity",
                        f"Optional atom {atom.key!r} has zero tier intensity.",
                        atom,
                    )
                )
            else:
                available.append(atom)
        selected, group_diagnostics = self._select_groups(tuple(available))
        diagnostics.extend(group_diagnostics)
        resolved, exclusion_diagnostics = self._resolve_exclusions(selected)
        diagnostics.extend(exclusion_diagnostics)
        ordered = self._stable_order(resolved)
        return tuple(item._public() for item in ordered), tuple(diagnostics)

    def _project(
        self,
        binding: VisualPromptBinding,
        definitions: dict[str, VisualPromptAtomDefinition],
    ) -> _ProjectedBinding:
        definition = definitions.get(binding.atom_key)
        if definition is None:
            raise CardBattlerModelInvalid(
                f"visual binding references unknown atom {binding.atom_key!r}"
            )
        intensity = self._intensity(binding.intensity_channel)
        weight = binding.weight_milli
        if self._policy.apply_intensity_channels:
            product = weight * intensity
            scale = self._policy.weight_scale
            weight = (product + scale // 2) // scale
        return _ProjectedBinding(binding, definition.canonical_text, weight)

    def _intensity(self, channel: str) -> int:
        normalized = channel.strip().casefold()
        intensities = {
            "world": self._progression.world_intensity_milli,
            "class": self._progression.class_intensity_milli,
            "role": self._progression.role_intensity_milli,
            "lineage": self._progression.lineage_intensity_milli,
            "mechanic": self._progression.mechanic_intensity_milli,
            "semantic": self._progression.semantic_preservation_milli,
            "semantic_preservation": (
                self._progression.semantic_preservation_milli
            ),
        }
        try:
            return intensities[normalized]
        except KeyError as error:
            raise CardBattlerModelInvalid(
                f"unknown visual intensity channel {channel!r}"
            ) from error

    def _merge(
        self, projected: tuple[_ProjectedBinding, ...]
    ) -> tuple[_MergedAtom, ...]:
        identities: list[tuple[VisualPromptScope, str]] = sorted(
            {(item.binding.scope, item.binding.atom_key) for item in projected}
        )
        merged: list[_MergedAtom] = []
        for scope, key in identities:
            matches = tuple(
                item
                for item in projected
                if item.binding.scope == scope and item.binding.atom_key == key
            )
            groups = {
                item.binding.prompt_group_key
                for item in matches
                if item.binding.prompt_group_key is not None
            }
            if len(groups) > 1:
                raise CardBattlerModelInvalid(
                    f"visual atom {key!r} belongs to multiple prompt groups"
                )
            sources = tuple(
                VisualPromptAtomSource(
                    item.binding.source_type,
                    item.binding.source_key,
                    item.binding.mode,
                    item.binding.weight_milli,
                    item.binding.priority,
                )
                for item in sorted(
                    matches,
                    key=lambda match: (
                        match.binding.source_type,
                        match.binding.source_key,
                        match.binding.mode,
                    ),
                )
            )
            merged.append(
                _MergedAtom(
                    key=key,
                    canonical_text=matches[0].canonical_text,
                    scope=scope,
                    weight_milli=max(item.weight_milli for item in matches),
                    required=any(
                        item.binding.mode == "required" for item in matches
                    ),
                    priority=min(item.binding.priority for item in matches),
                    selection_weight_milli=max(
                        item.binding.selection_weight_milli for item in matches
                    ),
                    prompt_group_key=next(iter(groups), None),
                    sources=sources,
                )
            )
        return tuple(merged)

    def _select_groups(
        self, atoms: tuple[_MergedAtom, ...]
    ) -> tuple[tuple[_MergedAtom, ...], tuple[VisualPromptDiagnostic, ...]]:
        selected = [item for item in atoms if item.prompt_group_key is None]
        diagnostics: list[VisualPromptDiagnostic] = []
        referenced_groups = {
            item.prompt_group_key
            for item in atoms
            if item.prompt_group_key is not None
        }
        unknown = referenced_groups - self._groups.keys()
        if unknown:
            raise CardBattlerModelInvalid(
                f"visual atoms reference unknown prompt groups {sorted(unknown)!r}"
            )
        for group_key in sorted(referenced_groups):
            group = self._groups[group_key]
            members = tuple(
                item for item in atoms if item.prompt_group_key == group_key
            )
            required = tuple(item for item in members if item.required)
            optional = tuple(item for item in members if not item.required)
            if len(required) > group.max_selected:
                raise CardBattlerModelInvalid(
                    f"required visual atoms exceed group {group_key!r} maximum"
                )
            chosen = list(required)
            remaining = list(optional)
            while len(chosen) < group.max_selected and remaining:
                choice = self._random.weighted_choice(
                    f"prompt:{group_key}:slot:{len(chosen)}",
                    tuple(
                        (
                            f"{item.scope}:{item.key}",
                            item.selection_weight_milli,
                        )
                        for item in remaining
                    ),
                )
                winner = next(
                    item
                    for item in remaining
                    if f"{item.scope}:{item.key}" == choice
                )
                chosen.append(winner)
                remaining.remove(winner)
            if len(chosen) < group.min_selected:
                raise CardBattlerModelInvalid(
                    f"visual prompt group {group_key!r} cannot reach its minimum"
                )
            selected.extend(chosen)
            diagnostics.extend(
                self._diagnostic(
                    "optional-atom-not-selected",
                    f"Optional atom {item.key!r} was not selected for group {group_key!r}.",
                    item,
                )
                for item in remaining
            )
        return tuple(selected), tuple(diagnostics)

    def _resolve_exclusions(
        self, atoms: tuple[_MergedAtom, ...]
    ) -> tuple[tuple[_MergedAtom, ...], tuple[VisualPromptDiagnostic, ...]]:
        selected = list(atoms)
        diagnostics: list[VisualPromptDiagnostic] = []
        while True:
            conflict = next(
                (
                    (left, right)
                    for index, left in enumerate(selected)
                    for right in selected[index + 1 :]
                    if frozenset((left.key, right.key)) in self._exclusions
                ),
                None,
            )
            if conflict is None:
                return tuple(selected), tuple(diagnostics)
            left, right = conflict
            if left.required and right.required:
                raise CardBattlerModelInvalid(
                    f"required visual atoms {left.key!r} and {right.key!r} exclude each other"
                )
            winner = min(
                (left, right),
                key=lambda item: (
                    not item.required,
                    item.priority,
                    item.key,
                    item.scope,
                ),
            )
            loser = right if winner is left else left
            selected.remove(loser)
            diagnostics.append(
                self._diagnostic(
                    "optional-atom-excluded",
                    f"Atom {loser.key!r} lost an exclusion to {winner.key!r}.",
                    loser,
                )
            )

    def _stable_order(
        self, atoms: tuple[_MergedAtom, ...]
    ) -> tuple[_MergedAtom, ...]:
        ordered = list(atoms)
        for field in reversed(self._policy.stable_order):
            if field == "priority_asc":
                ordered.sort(key=lambda item: item.priority)
            elif field == "source_type_asc":
                ordered.sort(
                    key=lambda item: min(
                        source.source_type for source in item.sources
                    )
                )
            elif field == "atom_key_asc":
                ordered.sort(key=lambda item: item.key)
            else:
                raise CardBattlerModelInvalid(
                    f"unsupported visual stable-order field {field!r}"
                )
        return tuple(ordered)

    @staticmethod
    def _diagnostic(
        code: str, message: str, atom: _MergedAtom
    ) -> VisualPromptDiagnostic:
        return VisualPromptDiagnostic(
            "info",
            code,
            message,
            (atom.key,),
            tuple(
                f"{source.source_type}:{source.source_key}"
                for source in atom.sources
            ),
        )
