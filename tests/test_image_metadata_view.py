"""Behavior tests for image metadata presentation mapping."""

from __future__ import annotations

from services.image_metadata_view import (
    LoraView,
    extract_prompts,
    extract_view,
    preset_text_from_view,
)


def _graph_metadata() -> dict[str, object]:
    return {
        "comfy_prompt_graph": {
            "1": {
                "class_type": "PrimitiveString",
                "inputs": {"value": "<Prompt Start> hero"},
            },
            "2": {
                "class_type": "PrimitiveString",
                "inputs": {"value": "sharp"},
            },
            "3": {
                "class_type": "StringConcatenate",
                "inputs": {
                    "string_a": ["1", 0],
                    "string_b": ["2", 0],
                    "delimiter": ", ",
                },
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": ["3", 0]},
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": "blur"},
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "seed": 12,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                },
            },
            "7": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "model.safetensors"},
            },
            "8": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": 1024, "height": 1024},
            },
            "9": {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": "style.safetensors",
                    "strength_model": "0.8",
                    "strength_clip": "invalid",
                },
            },
        }
    }


def test_extract_view_prefers_graph_values() -> None:
    view = extract_view(_graph_metadata())

    assert view == {
        "checkpoint": "model.safetensors",
        "resolution": "1024x1024",
        "seed": 12,
        "steps": 20,
        "cfg": 7.0,
        "sampler": "euler",
        "scheduler": "normal",
        "denoise": 1.0,
        "pos_prompt": "hero, sharp",
        "neg_prompt": "blur",
        "loras": [LoraView("style.safetensors", 0.8, None)],
    }


def test_extract_view_falls_back_to_normalized_metadata() -> None:
    view = extract_view(
        {
            "checkpoint": "fallback.safetensors",
            "width": 512,
            "height": 768,
            "seed": 1,
            "steps": 30,
            "cfg": 6.5,
            "sampler": "dpmpp",
            "scheduler": "karras",
            "denoise": 0.7,
            "pos_prompt": "You are an assistant designed to generate high quality anime images based on textual prompts. hero",
            "neg_prompt": "<Prompt Start> blur",
        }
    )

    assert view["checkpoint"] == "fallback.safetensors"
    assert view["resolution"] == "512x768"
    assert view["pos_prompt"] == "hero"
    assert view["neg_prompt"] == "blur"
    assert view["loras"] == []


def test_prompt_and_preset_views_preserve_ui_contracts() -> None:
    positive, negative, graph_hint = extract_prompts(_graph_metadata())
    fallback = extract_prompts(
        {"pos_prompt": "<Prompt Start> hero", "neg_prompt": "blur"}
    )

    assert (positive, negative) == ("hero, sharp", "blur")
    assert "comfy_prompt_graph" in graph_hint
    assert fallback == (
        "hero",
        "blur",
        "Prompts filled from stored meta keys.",
    )
    assert (
        preset_text_from_view(
            {"sampler": "euler", "scheduler": "normal", "steps": 20}
        )
        == "euler,normal,20"
    )
