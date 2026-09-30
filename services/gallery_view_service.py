from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from comfyreview.application import RankedImage, RankingQuery, RankingService
from services.context_filters import (
    GalleryContext,
    build_dropdown_lists,
    extract_character_from_subdir,
    normalize_model,
)
from services.file_urls import png_path_to_url
from services.playground_label_service import PromptLabelService


@dataclass(frozen=True)
class RankedCard:
    image_uid: str
    img_url: str
    json_path: str
    png_path: str
    model_branch: str
    checkpoint: str
    avg: float
    runs: int
    sampler: str
    scheduler: str
    steps: Any
    cfg: Any
    denoise: Any
    combo_key: str
    subdir: str
    character_name: str
    scene_name: str
    outfit_name: str
    pose_name: str
    expression_name: str
    modifiers: list[str]
    light_name: str
    assigned_set_key: str


def _card_from_ranked_image(
    image: RankedImage,
    prompt_labels: PromptLabelService,
) -> RankedCard:
    labels = prompt_labels.resolve(
        image.positive_prompt,
        include_lighting=True,
    )
    return RankedCard(
        image_uid=image.image_uid,
        img_url=png_path_to_url(str(image.png_path)),
        json_path=str(image.json_path or ""),
        png_path=str(image.png_path),
        model_branch=image.model_branch,
        checkpoint=image.checkpoint,
        avg=image.average_rating,
        runs=image.rating_count,
        sampler=str(image.sampler or ""),
        scheduler=str(image.scheduler or ""),
        steps=image.steps,
        cfg=image.cfg,
        denoise=image.denoise,
        combo_key=image.combo_key,
        subdir=image.subdir,
        character_name=extract_character_from_subdir(image.subdir),
        scene_name=labels.scene_name,
        outfit_name=labels.outfit_name,
        pose_name=labels.pose_name,
        expression_name=labels.expression_name,
        modifiers=list(labels.modifiers),
        light_name=labels.light_name,
        assigned_set_key=str(image.assigned_set_key or "unsorted"),
    )


def build_top_pictures_page(
    *,
    ranking_service: RankingService,
    prompt_labels: PromptLabelService,
    context: GalleryContext,
    min_runs: int,
    limit: int,
) -> dict[str, Any]:
    """Build canonical view data for the Top/Worst gallery page."""
    inventory = ranking_service.list_images(
        RankingQuery(minimum_ratings=0, limit=1_000_000)
    )
    model_list, subdir_list, character_options = build_dropdown_lists(
        inventory
    )
    model = normalize_model(context.model)
    ranked = ranking_service.list_images(
        RankingQuery(
            model=model,
            subdir=context.subdir,
            set_key=context.set_key,
            mode=context.mode,
            minimum_ratings=min_runs,
            limit=limit,
        )
    )
    cards = [_card_from_ranked_image(image, prompt_labels) for image in ranked]
    return {
        "cards": cards,
        "model": model,
        "subdir": context.subdir,
        "model_list": model_list,
        "subdir_list": subdir_list,
        "mode": context.mode,
        "character_options": character_options,
        "set_key": context.set_key,
    }


def build_arena_side(
    image: RankedImage,
    prompt_labels: PromptLabelService,
) -> dict[str, Any]:
    """Build one template side from a canonical ranked image."""
    card = _card_from_ranked_image(image, prompt_labels)
    return {
        **asdict(card),
        "view": {
            "sampler": card.sampler,
            "scheduler": card.scheduler,
            "steps": card.steps,
            "cfg": card.cfg,
            "denoise": card.denoise,
        },
    }
