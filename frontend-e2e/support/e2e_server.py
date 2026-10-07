"""Run a disposable canonical-v8 application for browser acceptance tests."""

from __future__ import annotations

import atexit
import base64
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from comfyreview.bootstrap import (  # noqa: E402
    build_application_container,
    create_app,
)
from comfyreview.repositories.sqlite import (  # noqa: E402
    CanonicalSchemaManager,
)
from comfyreview.settings import load_settings  # noqa: E402

PORT = 8015
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUB"
    "AScY42YAAAAASUVORK5CYII="
)


class BrowserTestRuntime:
    """Own one temporary canonical database and its output files."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="comfyreview-e2e-"))
        self.data_directory = self.root / "data"
        self.output_root = self.root / "output"
        self.database_path = self.data_directory / "canonical.sqlite3"
        self.submitted_prompts: list[dict[str, Any]] = []

    def create_application(self) -> FastAPI:
        """Build and seed one isolated application with fake ComfyUI routes."""
        self.data_directory.mkdir(parents=True)
        self.output_root.mkdir(parents=True)
        CanonicalSchemaManager(self.database_path).prepare_startup()
        self._seed_database()
        settings = load_settings(
            base_directory=ROOT,
            env_file=self.root / "missing.env",
            environ={
                "COMFYREVIEW_DATABASE": str(self.database_path),
                "COMFYREVIEW_DATA_DIR": str(self.data_directory),
                "COMFYREVIEW_OUTPUT_ROOT": str(self.output_root),
                "COMFYREVIEW_WORKFLOWS_DIR": str(ROOT / "data" / "workflows"),
                "COMFYREVIEW_COMFYUI_BASE_URL": (
                    f"http://127.0.0.1:{PORT}/_fake_comfyui"
                ),
                "COMFYREVIEW_PORT": str(PORT),
                "COMFYREVIEW_SOFT_DELETE_TO_TRASH": "true",
            },
        )
        application = create_app(build_application_container(settings))
        self._add_test_routes(application)
        return application

    def cleanup(self) -> None:
        """Remove every disposable browser-test artifact."""
        shutil.rmtree(self.root, ignore_errors=True)

    def _seed_database(self) -> None:
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            negative_prompt_id = self._insert_prompt(
                connection, "neg", "bad anatomy, low quality"
            )
            character_revision_id = self._insert_component(
                connection,
                kind="character",
                component_uid="component-character-aiko",
                name="Aiko",
                positive_text="aiko",
            )
            self._insert_lora(connection)
            self._insert_component(
                connection,
                kind="outfit",
                component_uid="component-outfit-underwear",
                name="Basic Underwear Set",
                positive_text="underwear",
                content_level="sexy",
            )
            sequence = 0
            for index in range(30):
                sequence = self._insert_generation(
                    connection,
                    index=index,
                    character_revision_id=character_revision_id,
                    negative_prompt_id=negative_prompt_id,
                    first_sequence=sequence,
                )
            connection.commit()
        finally:
            connection.close()

    def _insert_generation(
        self,
        connection: sqlite3.Connection,
        *,
        index: int,
        character_revision_id: int,
        negative_prompt_id: int,
        first_sequence: int,
    ) -> int:
        scene_name = f"Testszene {index + 1:02d}"
        scene_revision_id = self._insert_component(
            connection,
            kind="scene",
            component_uid=f"component-scene-{index + 1:02d}",
            name=scene_name,
            positive_text=f"test scene {index + 1:02d}",
        )
        composition_uid = f"composition-e2e-{index + 1:02d}"
        composition_id = self._last_row_id(
            connection.execute(
                "INSERT INTO prompt_compositions(composition_uid) VALUES (?)",
                (composition_uid,),
            )
        )
        connection.executemany(
            """
            INSERT INTO prompt_composition_revisions(
                composition_id, revision_id, slot, position
            ) VALUES (?, ?, ?, ?)
            """,
            (
                (composition_id, character_revision_id, "character", 0),
                (composition_id, scene_revision_id, "scene", 1),
            ),
        )
        positive_prompt_id = self._insert_prompt(
            connection, "pos", f"aiko, test scene {index + 1:02d}"
        )
        setup_index = index // 10
        checkpoint = f"NetaYume-e2e-{setup_index + 1}.safetensors"
        steps = 24 + (setup_index * 4)
        cfg = 5.0 + setup_index
        sampler = ("euler", "dpmpp_2m", "sa_solver")[setup_index]
        generation_id = self._last_row_id(
            connection.execute(
                """
                INSERT INTO generations(
                    generation_uid, model_branch, checkpoint, combo_key,
                    seed, steps, cfg, sampler, scheduler, denoise,
                    loras_json, positive_prompt_id, negative_prompt_id,
                    source, raw_metadata_json, workflow_json, workflow_hash,
                    status, prompt_composition_id
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    f"generation-e2e-{index + 1:02d}",
                    "NetaYume",
                    checkpoint,
                    composition_uid,
                    1000 + index,
                    steps,
                    cfg,
                    sampler,
                    "simple",
                    1.0,
                    "[]",
                    positive_prompt_id,
                    negative_prompt_id,
                    "browser_test",
                    "{}",
                    "{}",
                    self._digest(f"workflow-{index}"),
                    "completed",
                    composition_id,
                ),
            )
        )
        image_uid = f"image-e2e-{index + 1:02d}"
        relative_path = Path("e2e") / f"image-{index + 1:02d}.png"
        image_path = self.output_root / relative_path
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(_PNG)
        image_id = self._last_row_id(
            connection.execute(
                """
                INSERT INTO images(
                    image_uid, generation_id, output_node_id, output_index,
                    png_path, output_role, content_hash
                ) VALUES (?, ?, '33', 0, ?, 'primary', ?)
                """,
                (
                    image_uid,
                    generation_id,
                    relative_path.as_posix(),
                    self._digest(_PNG),
                ),
            )
        )
        connection.execute(
            """
            INSERT INTO generation_sampler_stages(
                generation_id, node_id, stage_order, role, seed, steps, cfg,
                sampler, scheduler, denoise
            ) VALUES (?, '3', 0, 'base_sampler', ?, ?, ?, ?, 'simple', 1.0)
            """,
            (generation_id, 1000 + index, steps, cfg, sampler),
        )
        sequence = first_sequence
        for rating_index in range(8):
            sequence += 1
            connection.execute(
                """
                INSERT INTO review_events(
                    event_uid, image_id, event_type, rating, source,
                    source_key, sequence
                ) VALUES (?, ?, 'rating', ?, 'browser_test', ?, ?)
                """,
                (
                    f"review-e2e-{index + 1:02d}-{rating_index + 1}",
                    image_id,
                    6 + ((index + rating_index) % 5),
                    f"image-{index + 1:02d}-rating-{rating_index + 1}",
                    sequence,
                ),
            )
        return sequence

    @staticmethod
    def _insert_component(
        connection: sqlite3.Connection,
        *,
        kind: str,
        component_uid: str,
        name: str,
        positive_text: str,
        content_level: str = "standard",
    ) -> int:
        negative_text = "bad anatomy" if kind == "character" else ""
        component_id = BrowserTestRuntime._last_row_id(
            connection.execute(
                """
                INSERT INTO prompt_components(
                    kind, component_key, name, component_uid, tags
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    kind,
                    component_uid,
                    name,
                    component_uid,
                    json.dumps([f"content_level_{content_level}"]),
                ),
            )
        )
        content_hash = BrowserTestRuntime._digest(positive_text)
        revision_id = BrowserTestRuntime._last_row_id(
            connection.execute(
                """
                INSERT INTO prompt_revisions(
                    revision_uid, component_id, revision_number,
                    positive_text, negative_text, content_hash
                ) VALUES (?, ?, 1, ?, ?, ?)
                """,
                (
                    f"revision-{component_uid}",
                    component_id,
                    positive_text,
                    negative_text,
                    content_hash,
                ),
            )
        )
        atom_id = BrowserTestRuntime._insert_atom(connection, positive_text)
        connection.execute(
            """
            INSERT INTO prompt_revision_atom_usages(
                revision_id, atom_id, scope, position, weight_milli
            ) VALUES (?, ?, 'pos', 0, 1000)
            """,
            (revision_id, atom_id),
        )
        if negative_text:
            negative_atom_id = BrowserTestRuntime._insert_atom(
                connection, negative_text
            )
            connection.execute(
                """
                INSERT INTO prompt_revision_atom_usages(
                    revision_id, atom_id, scope, position, weight_milli
                ) VALUES (?, ?, 'neg', 0, 1000)
                """,
                (revision_id, negative_atom_id),
            )
        return revision_id

    @staticmethod
    def _insert_lora(connection: sqlite3.Connection) -> None:
        definition_id = BrowserTestRuntime._last_row_id(
            connection.execute(
                """
                INSERT INTO lora_definitions(
                    lora_uid, provider_name, display_name, content_level
                ) VALUES (
                    'lora-e2e-detail', 'character-detail.safetensors',
                    'Character Detail', 'standard'
                )
                """
            )
        )
        content_hash = BrowserTestRuntime._digest(
            "\0".join(("1000", "1000", "", ""))
        )
        revision_id = BrowserTestRuntime._last_row_id(
            connection.execute(
                """
            INSERT INTO lora_revisions(
                revision_uid, lora_definition_id, revision_number,
                default_model_strength_milli,
                default_clip_strength_milli, content_hash
            ) VALUES (
                'lora-revision-e2e-detail', ?, 1, 1000, 1000, ?
            )
            """,
                (definition_id, content_hash),
            )
        )
        atom_id = BrowserTestRuntime._insert_atom(connection, "detail trigger")
        connection.execute(
            """
            INSERT INTO lora_revision_atom_usages(
                revision_id, atom_id, scope, position, weight_milli
            ) VALUES (?, ?, 'pos', 0, 1000)
            """,
            (revision_id, atom_id),
        )

    @staticmethod
    def _insert_prompt(
        connection: sqlite3.Connection, scope: str, text: str
    ) -> int:
        prompt_id = BrowserTestRuntime._last_row_id(
            connection.execute(
                "INSERT INTO prompts(scope, prompt_hash, text) VALUES (?, ?, ?)",
                (scope, BrowserTestRuntime._digest(text), text),
            )
        )
        for position, raw_text in enumerate(text.split(", ")):
            atom_id = BrowserTestRuntime._insert_atom(connection, raw_text)
            connection.execute(
                """
                INSERT INTO prompt_memberships(
                    prompt_id, atom_id, position, weight_milli, raw_text
                ) VALUES (?, ?, ?, 1000, ?)
                """,
                (prompt_id, atom_id, position, raw_text),
            )
        return prompt_id

    @staticmethod
    def _insert_atom(connection: sqlite3.Connection, text: str) -> int:
        connection.execute(
            "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
            (text,),
        )
        row = connection.execute(
            "SELECT id FROM prompt_atoms WHERE canonical_text = ?", (text,)
        ).fetchone()
        if row is None:
            raise RuntimeError("prompt atom insert did not return an id")
        return int(row[0])

    @staticmethod
    def _digest(value: str | bytes) -> str:
        payload = value.encode("utf-8") if isinstance(value, str) else value
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _last_row_id(cursor: sqlite3.Cursor) -> int:
        value = cursor.lastrowid
        if value is None:
            raise RuntimeError("SQLite insert did not return a row id")
        return int(value)

    def _add_test_routes(self, application: FastAPI) -> None:
        @application.get("/_e2e/health")
        def health() -> dict[str, str]:
            return {"status": "ok"}

        @application.get("/_fake_comfyui/object_info")
        def object_info() -> dict[str, Any]:
            return {
                "KSampler": {
                    "input": {
                        "required": {
                            "sampler_name": [
                                ["euler", "dpmpp_2m", "sa_solver"]
                            ],
                            "scheduler": [["normal", "simple", "karras"]],
                        }
                    }
                },
                "CheckpointLoaderSimple": {
                    "input": {
                        "required": {
                            "ckpt_name": [["NetaYume-e2e-1.safetensors"]]
                        }
                    }
                },
                "LoraLoader": {
                    "input": {
                        "required": {
                            "lora_name": [
                                [
                                    "character-detail.safetensors",
                                    "cinematic-light.safetensors",
                                ]
                            ]
                        }
                    }
                },
                "UpscaleModelLoader": {
                    "input": {
                        "required": {"model_name": [["4x-AnimeSharp.pth"]]}
                    }
                },
                "ImageUpscaleWithModel": {},
                "ImageSharpen": {},
                "ImageScale": {},
                "SaveImage": {},
                "PrimitiveString": {},
                "PrimitiveStringMultiline": {},
                "StringConcatenate": {},
                "CLIPTextEncode": {},
                "VAEDecode": {},
                "EmptySD3LatentImage": {},
            }

        @application.post("/_fake_comfyui/prompt")
        def submit_prompt(payload: dict[str, Any]) -> dict[str, str]:
            self.submitted_prompts.append(payload)
            return {"prompt_id": "e2e-prompt-1"}

        @application.get("/_e2e/submissions")
        def submissions() -> dict[str, Any]:
            with sqlite3.connect(self.database_path) as connection:
                loras = connection.execute(
                    """
                    SELECT lora_name, model_strength_milli,
                           clip_strength_milli
                    FROM generation_loras
                    WHERE generation_id = (
                        SELECT MAX(id) FROM generations
                    )
                    ORDER BY position
                    """
                ).fetchall()
            return {
                "prompt": self.submitted_prompts[-1]
                if self.submitted_prompts
                else None,
                "loras": [list(item) for item in loras],
            }


runtime = BrowserTestRuntime()
atexit.register(runtime.cleanup)
app = runtime.create_application()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
