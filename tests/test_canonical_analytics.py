"""Behavior and SQLite tests for canonical analytics queries."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from comfyreview.application import (
    AnalyticsImage,
    AnalyticsReportService,
    AnalyticsService,
    CalculatedRenderRecommendation,
    CollectionPage,
    CompositionAnalyticsService,
    CompositionStatistic,
    ObservedPromptCombination,
    PromptMatchPreview,
    PromptTokenStatistic,
    RenderAnalyticsService,
    RenderParameter,
    RenderSamplerStage,
    RenderSetupStatistic,
    ScopeKind,
    ScopeStatistic,
    normalize_page,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteAnalyticsReportRepository,
    SqliteAnalyticsRepository,
    SqliteCompositionAnalyticsRepository,
    SqliteRenderAnalyticsRepository,
)


class _AnalyticsRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def list_prompt_token_statistics(self, **values):
        self.calls.append(("tokens", values))
        return (PromptTokenStatistic("hero", 2, 8.0, 7.0),)

    def list_best_images_for_combos(self, combo_keys, **values):
        self.calls.append(("combos", (combo_keys, values)))
        return {combo_keys[0]: ()}

    def list_selected_prompt_token_statistics(self, tokens, **values):
        self.calls.append(("selected-tokens", (tokens, values)))
        return (PromptTokenStatistic(tokens[0], 2, 8.0, 7.0),)

    def find_best_prompt_match(self, tokens, **values):
        self.calls.append(("prompt-match", (tokens, values)))
        return PromptMatchPreview(
            Path("image.json"),
            Path("image.png"),
            2,
            8.0,
            3,
        )

    def list_best_images_for_parameter(self, parameter, values, **options):
        self.calls.append(("parameter", (parameter, values, options)))
        return {values[0]: ()}

    def list_observed_combinations(self, **values):
        self.calls.append(("observed", values))
        return ()

    def latest_review_sequence(self):
        self.calls.append(("frontier", None))
        return 9


class _AnalyticsReportRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def combo_statistics(self, **values):
        self.calls.append(("combos", values))
        return [{"combo_key": "character:1|scene:2"}]

    def scope_statistics(self, **values):
        self.calls.append(("scopes", values))
        return CollectionPage(
            (
                ScopeStatistic(
                    ScopeKind.CHARACTER,
                    "character-a",
                    "Aiko",
                    False,
                    2,
                    4,
                    8.5,
                ),
            ),
            1,
            values["offset"],
            values["limit"],
        )

    def composition_statistics(self, **values):
        self.calls.append(("compositions", values))
        return CollectionPage(
            (
                CompositionStatistic(
                    "composition-a",
                    ("Aiko", "Rooftop"),
                    2,
                    4,
                    8.5,
                ),
            ),
            1,
            values["offset"],
            values["limit"],
        )

    def recommendations(self, **values):
        self.calls.append(("recommendations", values))
        return {"stable": [], "avoid": [], "approx": {}}

    def parameter_statistics(self, **values):
        self.calls.append(("parameters", values))
        return [{"feat": "steps", "value": 20}]

    def calculated_best_cases(self, **values):
        self.calls.append(("best-cases", values))
        return [{"checkpoint": "model.safetensors"}]

    def list_models(self):
        self.calls.append(("models", None))
        return ("sdxl",)


class _RenderAnalyticsRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.setup = RenderSetupStatistic(
            "setup",
            "model.safetensors",
            (RenderSamplerStage("base", 20, 7.0, "euler", "normal", 1.0),),
            1,
            2,
            8.0,
            0.75,
            0.5,
        )

    def list_calculated_recommendations(self, **values):
        self.calls.append(("recommendations", values))
        return (
            CalculatedRenderRecommendation(
                "model.safetensors",
                "euler",
                "normal",
                20,
                7.0,
                1.0,
                0.7,
                0.6,
            ),
        )

    def list_observed_setups(self, **values):
        self.calls.append(("setups", values))
        return CollectionPage(
            (self.setup,), 1, values["offset"], values["limit"]
        )

    def list_parameter_values(self, parameter, **values):
        self.calls.append(("values", (parameter, values)))
        return CollectionPage((), 0, values["offset"], values["limit"])


class _CompositionAnalyticsRepository:
    def __init__(self, setup: RenderSetupStatistic) -> None:
        self.setup = setup
        self.calls: list[tuple[str, object]] = []

    def list_prompt_combinations(self, **values):
        self.calls.append(("prompts", values))
        return CollectionPage(
            (
                CompositionStatistic(
                    "composition-a", ("Aiko", "Rooftop"), 1, 2, 8.0
                ),
            ),
            1,
            values["offset"],
            values["limit"],
        )

    def list_render_setups(self, composition_uid, **values):
        self.calls.append(("setups", (composition_uid, values)))
        return (self.setup,)


def test_analytics_service_normalizes_canonical_queries() -> None:
    repository = _AnalyticsRepository()
    service = AnalyticsService(repository)

    tokens = service.prompt_token_statistics(
        model_branch=" model ",
        scope="invalid",
        minimum_samples=-1,
        limit=-2,
    )
    combos = service.best_images_for_combos(
        (" combo ", "combo", ""),
        model_branch=" model ",
        limit_per_combo=-1,
    )
    parameters = service.best_images_for_parameter(
        "checkpoint",
        (" model.safetensors ", ""),
        limit_per_value=2,
    )

    assert tokens[0].token == "hero"
    assert combos == {"combo": ()}
    assert parameters == {"model.safetensors": ()}
    assert repository.calls[:3] == [
        (
            "tokens",
            {
                "model_branch": "model",
                "scope": "pos",
                "minimum_samples": 0,
                "limit": 0,
            },
        ),
        (
            "combos",
            (
                ("combo",),
                {"model_branch": "model", "limit_per_combo": 0},
            ),
        ),
        (
            "parameter",
            (
                "checkpoint",
                ("model.safetensors",),
                {"model_branch": "", "limit_per_value": 2},
            ),
        ),
    ]


def test_analytics_service_handles_empty_and_observed_queries() -> None:
    repository = _AnalyticsRepository()
    service = AnalyticsService(repository)

    assert service.best_images_for_combos(()) == {}
    assert service.best_images_for_parameter("steps", ()) == {}
    assert service.observed_combinations(combo_size=2, limit=-1) == ()
    assert service.latest_review_sequence() == 9
    assert service.token_statistics_for(()) == {}
    assert service.best_prompt_match(()) is None
    with pytest.raises(ValueError, match="combo_size must be 2 or 3"):
        service.observed_combinations(combo_size=4)


def test_analytics_service_normalizes_selected_tokens_and_matches() -> None:
    repository = _AnalyticsRepository()
    service = AnalyticsService(repository)

    statistics = service.token_statistics_for(
        (" hero ", "hero", "missing", ""),
        model_branch=" sdxl ",
        scope="invalid",
    )
    match = service.best_prompt_match(
        (" hero ", "hero"),
        model_branch=" sdxl ",
        scope="invalid",
        minimum_hits=0,
        minimum_ratings=-1,
        candidate_limit=0,
    )

    assert statistics["hero"].sample_count == 2
    assert statistics["missing"] == PromptTokenStatistic(
        "missing", 0, 0.0, 0.0
    )
    assert match is not None and match.token_hits == 2
    assert repository.calls[-2:] == [
        (
            "selected-tokens",
            (("hero", "missing"), {"model_branch": "sdxl", "scope": "pos"}),
        ),
        (
            "prompt-match",
            (
                ("hero",),
                {
                    "model_branch": "sdxl",
                    "scope": "pos",
                    "minimum_hits": 1,
                    "minimum_ratings": 0,
                    "candidate_limit": 1,
                },
            ),
        ),
    ]


def test_analytics_report_service_normalizes_queries() -> None:
    repository = _AnalyticsReportRepository()
    service = AnalyticsReportService(repository)

    assert (
        service.combo_statistics(
            model=" sdxl ",
            minimum_samples=-1,
            limit=-2,
            success_threshold=4,
            delete_weight=5,
        )[0]["combo_key"]
        == "character:1|scene:2"
    )
    assert (
        service.scope_statistics(model=" sdxl ", minimum_samples=-1, limit=-2)
        .entries[0]
        .component_uid
        == "character-a"
    )
    assert (
        service.composition_statistics(
            model=" sdxl ", minimum_samples=-1, limit=-2
        )
        .entries[0]
        .composition_uid
        == "composition-a"
    )
    assert (
        service.recommendations(
            model=" sdxl ",
            minimum_samples=-1,
            limit=-2,
            success_threshold=4,
            delete_weight=5,
            minimum_lower_bound=0.5,
            approximate_minimum_samples=-3,
            approximate_limit=-4,
        )["stable"]
        == []
    )
    assert (
        service.parameter_statistics(
            model=" sdxl ",
            minimum_samples=-1,
            success_threshold=4,
            delete_weight=5,
        )[0]["feat"]
        == "steps"
    )
    assert (
        service.calculated_best_cases(
            model=" sdxl ",
            minimum_samples=-1,
            success_threshold=4,
            delete_weight=5,
            limit=-2,
        )[0]["checkpoint"]
        == "model.safetensors"
    )
    assert service.list_models() == ("sdxl",)
    assert repository.calls == [
        (
            "combos",
            {
                "model": "sdxl",
                "min_n": 0,
                "limit": 0,
                "success_threshold": 4,
                "delete_weight": 5,
            },
        ),
        (
            "scopes",
            {
                "model": "sdxl",
                "min_n": 0,
                "kind": ScopeKind.CHARACTER,
                "offset": 0,
                "limit": 1,
            },
        ),
        (
            "compositions",
            {"model": "sdxl", "min_n": 0, "offset": 0, "limit": 1},
        ),
        (
            "recommendations",
            {
                "model": "sdxl",
                "min_n": 0,
                "limit": 0,
                "success_threshold": 4,
                "delete_weight": 5,
                "min_lb": 0.5,
                "approx_min_n": 0,
                "approx_limit": 0,
            },
        ),
        (
            "parameters",
            {
                "model": "sdxl",
                "min_n": 0,
                "success_threshold": 4,
                "delete_weight": 5,
            },
        ),
        (
            "best-cases",
            {
                "model": "sdxl",
                "min_n": 0,
                "success_threshold": 4,
                "delete_weight": 5,
                "limit": 0,
            },
        ),
        ("models", None),
    ]


def test_focused_analytics_services_normalize_queries() -> None:
    render_repository = _RenderAnalyticsRepository()
    render_service = RenderAnalyticsService(render_repository)
    summary = render_service.summary(
        model=" sdxl ",
        minimum_samples=-1,
        success_threshold=4,
        delete_weight=-2,
        limit=-3,
    )
    values = render_service.parameter_values(
        "steps",
        model=" sdxl ",
        minimum_samples=-1,
        limit=-2,
    )

    assert summary.observed_setups.entries == (render_repository.setup,)
    assert summary.recommendations[0].checkpoint == "model.safetensors"
    assert values.entries == ()
    assert render_repository.calls == [
        (
            "recommendations",
            {
                "model": "sdxl",
                "minimum_samples": 0,
                "success_threshold": 4,
                "delete_weight": 0,
                "limit": 0,
            },
        ),
        (
            "setups",
            {
                "model": "sdxl",
                "minimum_samples": 0,
                "success_threshold": 4,
                "delete_weight": 0,
                "offset": 0,
                "limit": 1,
            },
        ),
        (
            "values",
            (
                RenderParameter.STEPS,
                {
                    "model": "sdxl",
                    "minimum_samples": 0,
                    "success_threshold": 4,
                    "delete_weight": 5,
                    "offset": 0,
                    "limit": 1,
                },
            ),
        ),
    ]
    with pytest.raises(ValueError, match="unsupported render parameter"):
        render_service.parameter_values("seed")

    composition_repository = _CompositionAnalyticsRepository(
        render_repository.setup
    )
    composition_service = CompositionAnalyticsService(composition_repository)
    combinations = composition_service.prompt_combinations(
        model=" sdxl ", minimum_samples=-1, limit=-1
    )
    setups = composition_service.render_setups(
        " composition-a ",
        model=" sdxl ",
        minimum_samples=-1,
        delete_weight=-1,
        limit=-1,
    )

    assert combinations.entries[0].composition_uid == "composition-a"
    assert setups == (render_repository.setup,)
    assert composition_repository.calls == [
        (
            "prompts",
            {
                "model": "sdxl",
                "minimum_samples": 0,
                "offset": 0,
                "limit": 1,
            },
        ),
        (
            "setups",
            (
                "composition-a",
                {
                    "model": "sdxl",
                    "minimum_samples": 0,
                    "success_threshold": 4,
                    "delete_weight": 0,
                    "limit": 0,
                },
            ),
        ),
    ]
    with pytest.raises(ValueError, match="composition_uid is required"):
        composition_service.render_setups(" ")


def test_analytics_paging_is_bounded_and_scope_kind_is_explicit() -> None:
    assert normalize_page(-10, 100) == (0, 48)
    assert normalize_page(4, 0) == (4, 1)

    repository = _AnalyticsReportRepository()
    service = AnalyticsReportService(repository)
    page = service.scope_statistics(
        model="",
        minimum_samples=0,
        kind="scene",
        offset=5,
        limit=100,
    )

    assert page.total == 1
    assert repository.calls == [
        (
            "scopes",
            {
                "model": "",
                "min_n": 0,
                "kind": ScopeKind.SCENE,
                "offset": 5,
                "limit": 48,
            },
        )
    ]
    with pytest.raises(ValueError, match="unsupported scope kind"):
        service.scope_statistics(model="", minimum_samples=0, kind="unknown")


def _insert_analytics_fixture(database_path: Path, tmp_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO prompt_atoms(canonical_text) VALUES (?)",
            (("hero",), ("blur",)),
        )
        connection.executemany(
            "INSERT INTO prompts(scope, prompt_hash, text) VALUES (?, ?, ?)",
            (("pos", "pos", "hero"), ("neg", "neg", "blur")),
        )
        connection.executemany(
            """
            INSERT INTO prompt_memberships(
                prompt_id, atom_id, position, weight_milli, raw_text
            ) VALUES (?, ?, 0, 1000, ?)
            """,
            ((1, 1, "hero"), (2, 2, "blur")),
        )
        revision_ids: list[int] = []
        for source_key, kind, name in (
            ("1", "character", "Alice"),
            ("2", "scene", "Rooftop"),
            ("3", "outfit", "Red Coat"),
        ):
            cursor = connection.execute(
                """
                INSERT INTO prompt_components(
                    component_uid, kind, component_key, name, tags, notes
                ) VALUES (?, ?, ?, ?, '[]', '')
                """,
                (f"component-{source_key}", kind, f"key-{source_key}", name),
            )
            connection.execute(
                """
                INSERT INTO legacy_prompt_component_sources(
                    component_id, source, source_key
                ) VALUES (?, 'legacy_playground', ?)
                """,
                (cursor.lastrowid, source_key),
            )
            revision = connection.execute(
                """
                INSERT INTO prompt_revisions(
                    revision_uid, component_id, revision_number,
                    positive_text, negative_text, content_hash
                ) VALUES (?, ?, 1, ?, '', ?)
                """,
                (
                    f"revision-{source_key}",
                    cursor.lastrowid,
                    name,
                    f"hash-{source_key}",
                ),
            )
            revision_id = revision.lastrowid
            assert revision_id is not None
            revision_ids.append(revision_id)
        composition = connection.execute(
            "INSERT INTO prompt_compositions(composition_uid) "
            "VALUES ('composition-1')"
        )
        composition_id = composition.lastrowid
        assert composition_id is not None
        connection.executemany(
            """
            INSERT INTO prompt_composition_revisions(
                composition_id, revision_id, slot, position
            ) VALUES (?, ?, ?, ?)
            """,
            (
                (
                    composition_id,
                    revision_id,
                    f"slot-{position}",
                    position,
                )
                for position, revision_id in enumerate(revision_ids)
            ),
        )
        combo_key = "character:1|scene:2|outfit:3"
        connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                seed, steps, cfg, sampler, scheduler, denoise, loras_json,
                positive_prompt_id, negative_prompt_id, source, status,
                prompt_composition_id
            ) VALUES (
                'generation-1', 'sdxl', 'model.safetensors', ?,
                1, 20, 7.0, 'euler', 'normal', 1.0, '[]',
                1, 2, 'test', 'completed', ?
            )
            """,
            (combo_key, composition_id),
        )
        connection.execute(
            """
            INSERT INTO generation_sampler_stages(
                generation_id, node_id, stage_order, role, seed, steps,
                cfg, sampler, scheduler, denoise, source
            ) VALUES (
                1, 'sampler', 0, 'base_sampler', 1, 20,
                7.0, 'euler', 'normal', 1.0, 'test'
            )
            """
        )
        png_path = tmp_path / "image.png"
        png_path.write_bytes(b"png")
        json_path = tmp_path / "image.json"
        json_path.write_text("{}", encoding="utf-8")
        connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, json_path
            ) VALUES ('image-1', 1, 'save', 0, ?, ?)
            """,
            (str(png_path), str(json_path)),
        )
        connection.execute(
            """
            INSERT INTO review_events(
                event_uid, image_id, event_type, rating, source,
                source_key, sequence
            ) VALUES ('event-1', 1, 'rating', 8, 'test', '1', 1)
            """
        )
        connection.execute("UPDATE review_clock SET value = 1")


def test_analytics_fixture_keeps_render_setup_outside_combo_key(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _insert_analytics_fixture(database_path, tmp_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE generations SET combo_key = 'not-a-render-contract'"
        )
        row = connection.execute(
            """
            SELECT
                generation.checkpoint,
                stage.role,
                stage.steps,
                stage.cfg,
                stage.sampler,
                stage.scheduler,
                stage.denoise
            FROM generations AS generation
            JOIN generation_sampler_stages AS stage
                ON stage.generation_id = generation.id
            """
        ).fetchone()

    assert row == (
        "model.safetensors",
        "base_sampler",
        20,
        7.0,
        "euler",
        "normal",
        1.0,
    )


def test_sqlite_analytics_reads_canonical_views_without_projection_databases(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _insert_analytics_fixture(database_path, tmp_path)
    repository = SqliteAnalyticsRepository(database_path)
    combo_key = "character:1|scene:2|outfit:3"

    token_stats = repository.list_prompt_token_statistics(
        model_branch="sdxl",
        scope="pos",
        minimum_samples=1,
        limit=10,
    )
    combo_images = repository.list_best_images_for_combos(
        (combo_key,),
        model_branch="sdxl",
        limit_per_combo=3,
    )
    parameter_images = repository.list_best_images_for_parameter(
        "steps",
        ("20",),
        model_branch="",
        limit_per_value=3,
    )
    observed = repository.list_observed_combinations(combo_size=3, limit=8)
    selected = repository.list_selected_prompt_token_statistics(
        ("hero", "missing"),
        model_branch="sdxl",
        scope="pos",
    )
    match = repository.find_best_prompt_match(
        ("hero",),
        model_branch="sdxl",
        scope="pos",
        minimum_hits=1,
        minimum_ratings=1,
        candidate_limit=10,
    )

    assert token_stats == (PromptTokenStatistic("hero", 1, 8.0, 8.0),)
    assert selected == (PromptTokenStatistic("hero", 1, 8.0, 8.0),)
    assert match == PromptMatchPreview(
        json_path=tmp_path / "image.json",
        png_path=tmp_path / "image.png",
        token_hits=1,
        average_rating=8.0,
        rating_count=1,
    )
    assert combo_images[combo_key][0].average_rating == 8.0
    assert parameter_images["20"][0].rating_count == 1
    assert observed == (
        ObservedPromptCombination(
            combo_key="component-1|component-2|component-3",
            combo_size=3,
            component_uids=("component-1", "component-2", "component-3"),
            component_names=("Alice", "Rooftop", "Red Coat"),
            label="Alice + Rooftop + Red Coat",
            average_rating=8.0,
            image_count=1,
            total_rating_count=1,
            best_images=(
                AnalyticsImage(
                    png_path=tmp_path / "image.png",
                    json_path=tmp_path / "image.json",
                    average_rating=8.0,
                    rating_count=1,
                    image_uid="image-1",
                ),
            ),
        ),
    )
    assert repository.latest_review_sequence() == 1
    with pytest.raises(ValueError, match="Unsupported analytics parameter"):
        repository.list_best_images_for_parameter(
            "unknown",
            ("value",),
            model_branch="",
            limit_per_value=1,
        )


def test_sqlite_analytics_apply_workspace_content_visibility(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _insert_analytics_fixture(database_path, tmp_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE prompt_components SET tags = ? "
            "WHERE component_uid = 'component-3'",
            ('["nsfw_level_nude"]',),
        )
        connection.commit()

    analytics = SqliteAnalyticsRepository(database_path)
    reports = SqliteAnalyticsReportRepository(database_path)

    assert analytics.list_observed_combinations(combo_size=3, limit=8) == ()
    assert (
        analytics.list_best_images_for_parameter(
            "steps",
            ("20",),
            model_branch="",
            limit_per_value=3,
        )
        == {}
    )
    assert (
        reports.scope_statistics(
            model="",
            min_n=0,
            kind=ScopeKind.OUTFIT,
            limit=24,
        ).entries
        == ()
    )
    assert (
        reports.parameter_statistics(
            model="",
            min_n=0,
            success_threshold=4,
            delete_weight=0,
        )
        == []
    )


def test_sqlite_analytics_reports_query_canonical_compatibility_views(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _insert_analytics_fixture(database_path, tmp_path)
    repository = SqliteAnalyticsReportRepository(database_path)

    combo_rows = repository.combo_statistics(
        model="sdxl",
        min_n=1,
        limit=10,
        success_threshold=4,
        delete_weight=5,
    )
    recommendations = repository.recommendations(
        model="sdxl",
        min_n=1,
        limit=10,
        success_threshold=4,
        delete_weight=5,
        min_lb=-1.0,
        approx_min_n=1,
        approx_limit=10,
    )
    parameters = repository.parameter_statistics(
        model="sdxl",
        min_n=1,
        success_threshold=4,
        delete_weight=5,
    )
    best_cases = repository.calculated_best_cases(
        model="sdxl",
        min_n=1,
        success_threshold=4,
        delete_weight=5,
        limit=10,
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE generations SET combo_key = 'deliberately-wrong'"
        )
    scopes = repository.scope_statistics(model="sdxl", min_n=1, limit=10)
    scene_page = repository.scope_statistics(
        model="sdxl",
        min_n=1,
        kind=ScopeKind.SCENE,
        offset=0,
        limit=1,
    )
    compositions = repository.composition_statistics(
        model="sdxl", min_n=1, limit=10
    )

    assert combo_rows[0]["combo_key"] == ("character:1|scene:2|outfit:3")
    assert recommendations["stable"][0]["avg_rating"] == 8.0
    assert {row["feat"] for row in parameters} == {
        "checkpoint",
        "steps",
        "cfg",
        "sampler",
        "scheduler",
    }
    assert best_cases[0]["checkpoint"] == "model.safetensors"
    assert scopes.entries == (
        ScopeStatistic(
            ScopeKind.CHARACTER,
            "component-1",
            "Alice",
            False,
            1,
            1,
            8.0,
            (
                AnalyticsImage(
                    tmp_path / "image.png",
                    tmp_path / "image.json",
                    8.0,
                    1,
                    "image-1",
                ),
            ),
        ),
        ScopeStatistic(
            ScopeKind.OUTFIT,
            "component-3",
            "Red Coat",
            False,
            1,
            1,
            8.0,
            (
                AnalyticsImage(
                    tmp_path / "image.png",
                    tmp_path / "image.json",
                    8.0,
                    1,
                    "image-1",
                ),
            ),
        ),
        ScopeStatistic(
            ScopeKind.SCENE,
            "component-2",
            "Rooftop",
            False,
            1,
            1,
            8.0,
            (
                AnalyticsImage(
                    tmp_path / "image.png",
                    tmp_path / "image.json",
                    8.0,
                    1,
                    "image-1",
                ),
            ),
        ),
    )
    assert scopes.total == 3
    assert scene_page.total == 1
    assert scene_page.entries[0].component_uid == "component-2"
    assert compositions.entries == (
        CompositionStatistic(
            "composition-1",
            ("Alice", "Rooftop", "Red Coat"),
            1,
            1,
            8.0,
            (
                AnalyticsImage(
                    tmp_path / "image.png",
                    tmp_path / "image.json",
                    8.0,
                    1,
                    "image-1",
                ),
            ),
        ),
    )
    assert repository.list_models() == ("sdxl",)


def test_focused_sqlite_analytics_uses_normalized_render_facts(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _insert_analytics_fixture(database_path, tmp_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE generations SET combo_key = 'not-a-render-contract'"
        )

    render_repository = SqliteRenderAnalyticsRepository(database_path)
    recommendations = render_repository.list_calculated_recommendations(
        model="sdxl",
        minimum_samples=1,
        success_threshold=4,
        delete_weight=5,
        limit=10,
    )
    setups = render_repository.list_observed_setups(
        model="sdxl",
        minimum_samples=1,
        success_threshold=4,
        delete_weight=5,
        limit=10,
    )
    values = render_repository.list_parameter_values(
        RenderParameter.STEPS,
        model="sdxl",
        minimum_samples=1,
        success_threshold=4,
        delete_weight=5,
        limit=10,
    )
    composition_repository = SqliteCompositionAnalyticsRepository(
        database_path
    )
    combinations = composition_repository.list_prompt_combinations(
        model="sdxl", minimum_samples=1, limit=10
    )
    composition_setups = composition_repository.list_render_setups(
        "composition-1",
        model="sdxl",
        minimum_samples=1,
        success_threshold=4,
        delete_weight=5,
        limit=10,
    )

    assert recommendations[0].checkpoint == "model.safetensors"
    assert setups.entries[0].checkpoint == "model.safetensors"
    assert setups.entries[0].stages == (
        RenderSamplerStage("base_sampler", 20, 7.0, "euler", "normal", 1.0),
    )
    assert setups.entries[0].image_count == 1
    assert setups.entries[0].rating_count == 1
    assert setups.entries[0].best_images[0].png_path == tmp_path / "image.png"
    assert values.entries[0].parameter is RenderParameter.STEPS
    assert values.entries[0].value == "20"
    assert combinations.entries[0].composition_uid == "composition-1"
    assert composition_setups == setups.entries
