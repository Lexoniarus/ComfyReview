"""Candidate-specific generation planning for complete Card groups."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidate,
    CardCandidateGroup,
)
from comfyreview.application.card_battler_generation_prompt import (
    CardEvolutionComfyUiPromptRenderer,
    CardEvolutionPromptAdapter,
)
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.application.card_battler_visuals import VisualPromptRecipe
from comfyreview.application.generation import (
    GenerationCanvas,
    GenerationOutputPolicy,
    GenerationPromptSnapshot,
    GenerationRequest,
    GenerationSamplerSettings,
)

CARD_CANDIDATE_GENERATION_POLICY_REVISION = "card-candidate-generation-v1"


@dataclass(frozen=True, slots=True)
class CardCandidateGenerationPlan:
    """Bind one exact candidate and Recipe to a prepared generation request."""

    candidate_id: str
    recipe_hash: str
    generation_policy_revision: str
    request: GenerationRequest


class CardCandidateGenerationPolicy:
    """Build one fresh img2img request from one candidate Recipe only."""

    def __init__(self, *, checkpoint: str) -> None:
        if not checkpoint.strip():
            raise ValueError("Card candidate checkpoint is required")
        self._checkpoint = checkpoint

    def build(
        self,
        group: CardCandidateGroup,
        candidate: CardCandidate,
        *,
        staged_reference: str,
    ) -> CardCandidateGenerationPlan:
        """Build one deterministic candidate-specific generation plan."""
        if candidate.group_id != group.group_id:
            raise ValueError("Candidate belongs to another group")
        if candidate.group_revision != group.revision:
            raise ValueError("Candidate group revision is stale")
        if candidate.artifacts is None:
            raise ValueError("Candidate artifacts are not composed")
        if not staged_reference.strip():
            raise ValueError("staged reference image is required")
        recipe = candidate.artifacts.visual_recipe
        handoff = CardEvolutionPromptAdapter.adapt(recipe)
        rendered = CardEvolutionComfyUiPromptRenderer.render(handoff)
        if not rendered.positive_prompt or not rendered.negative_prompt:
            raise ValueError(
                "Card candidate recipe requires both prompt channels"
            )
        recipe_hash = self._recipe_hash(recipe)
        tier = candidate.artifacts.card.tier_ordinal
        random = DomainSeparatedCardRandom(
            (
                CARD_CANDIDATE_GENERATION_POLICY_REVISION,
                group.group_id,
                str(group.group_seed),
                str(candidate.materialization_seed),
                str(tier),
                recipe_hash,
                group.reference_content_hash,
            )
        )
        request = GenerationRequest(
            prompt=GenerationPromptSnapshot(
                rendered.positive_prompt,
                rendered.negative_prompt,
                (),
            ),
            blueprint_uid="card-evolution",
            blueprint_version=1,
            model_branch="card-evolution",
            combo_key=f"{group.group_id}:tier-{tier}:candidate-{candidate.slot_index}",
            checkpoint=self._checkpoint,
            sampler_stages=(
                GenerationSamplerSettings(
                    role="base_sampler",
                    seed=random.integer(
                        f"evolution:{tier}:candidate:{candidate.slot_index}",
                        modulo=2**63 - 1,
                    ),
                    steps=32,
                    cfg=6.0,
                    sampler="sa_solver",
                    scheduler="simple",
                    denoise=0.55,
                ),
            ),
            output_policy=GenerationOutputPolicy(
                "card-battler",
                f"{group.group_id}-t{tier}-c{candidate.slot_index}",
                ("primary",),
            ),
            reference_image=staged_reference,
            canvas=GenerationCanvas(1024, 1024),
        )
        return CardCandidateGenerationPlan(
            candidate.candidate_id,
            recipe_hash,
            CARD_CANDIDATE_GENERATION_POLICY_REVISION,
            request,
        )

    @staticmethod
    def _recipe_hash(recipe: VisualPromptRecipe) -> str:
        payload = json.dumps(
            asdict(recipe),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
