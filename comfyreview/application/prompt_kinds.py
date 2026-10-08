"""Canonical ordered prompt-kind contract shared by application boundaries."""

from __future__ import annotations

from typing import Literal

PromptKind = Literal[
    "character",
    "scene",
    "atmosphere",
    "lighting",
    "outfit",
    "accessory",
    "pose",
    "expression",
    "framing",
    "camera_angle",
    "optical_effect",
]

PROMPT_KINDS: tuple[PromptKind, ...] = (
    "character",
    "scene",
    "atmosphere",
    "lighting",
    "outfit",
    "accessory",
    "pose",
    "expression",
    "framing",
    "camera_angle",
    "optical_effect",
)
OPTIONAL_PROMPT_KINDS: tuple[PromptKind, ...] = PROMPT_KINDS[1:]
REQUIRED_PROMPT_KINDS: tuple[PromptKind, ...] = ("character",)
