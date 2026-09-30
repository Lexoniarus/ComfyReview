"""Behavior-test ownership for every concrete public Python-core callable."""

FUNCTION_TEST_MANIFEST: dict[str, str] = {
    "comfyreview.application.analytics:AnalyticsService.best_images_for_combos": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_normalizes_canonical_queries"
    ),
    "comfyreview.application.analytics:AnalyticsService.best_images_for_parameter": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_normalizes_canonical_queries"
    ),
    "comfyreview.application.analytics:AnalyticsService.latest_review_sequence": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_handles_empty_and_observed_queries"
    ),
    "comfyreview.application.analytics:AnalyticsService.observed_combinations": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_handles_empty_and_observed_queries"
    ),
    "comfyreview.application.analytics:AnalyticsService.prompt_token_statistics": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_normalizes_canonical_queries"
    ),
    "comfyreview.application.analytics:AnalyticsService.token_statistics_for": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_normalizes_selected_tokens_and_matches"
    ),
    "comfyreview.application.analytics:AnalyticsService.best_prompt_match": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_normalizes_selected_tokens_and_matches"
    ),
    "comfyreview.application.playground:PlaygroundService.prepare_draft": (
        "tests/test_playground_application.py::"
        "test_playground_service_prepares_draft_without_generation_submission"
    ),
    "comfyreview.application.playground_generation:PlaygroundGenerationPolicy.build_request": (
        "tests/test_playground_generation.py::"
        "test_playground_generation_policy_builds_reproducible_request"
    ),
    "comfyreview.application.playground_generation:PlaygroundSubmissionService.submit": (
        "tests/test_playground_generation.py::"
        "test_playground_submission_service_uses_real_generation_port"
    ),
    "comfyreview.application.generation:GenerationService.submit": (
        "tests/test_generation_service.py::"
        "test_generation_service_submits_without_open_external_transaction"
    ),
    "comfyreview.application.generation:GenerationService.wait": (
        "tests/test_generation_service.py::"
        "test_generation_service_wait_maps_external_state"
    ),
    "comfyreview.application.generation_outputs:GenerationOutputCollector.collect": (
        "tests/test_generation_outputs.py::"
        "test_output_collector_maps_expected_nodes_and_actual_batch_indexes"
    ),
    "comfyreview.application.generation_outputs:generation_output_identity": (
        "tests/test_generation_outputs.py::"
        "test_generation_output_identity_does_not_depend_on_path"
    ),
    "comfyreview.application.playground:PromptRenderer.render": (
        "tests/test_playground_application.py::"
        "test_prompt_renderer_keeps_revision_snapshot_and_draft_override_separate"
    ),
    "comfyreview.application.playground:PromptSelectionPolicy.select": (
        "tests/test_playground_application.py::"
        "test_prompt_selection_policy_selects_reproducible_compatible_revisions"
    ),
    "comfyreview.application.prompt_catalog:PromptCatalogService.add_revision": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_catalog_service_appends_immutable_revision"
    ),
    "comfyreview.application.prompt_catalog:PromptCatalogService.create_component": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_catalog_service_creates_normalized_component"
    ),
    "comfyreview.application.prompt_catalog:PromptCatalogService.list_components": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_catalog_service_archives_restores_and_lists"
    ),
    "comfyreview.application.prompt_catalog:PromptCatalogService.get_component": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_catalog_service_updates_metadata_and_revision_atomically"
    ),
    "comfyreview.application.prompt_catalog:PromptCatalogService.set_archived": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_catalog_service_archives_restores_and_lists"
    ),
    "comfyreview.application.prompt_catalog:PromptCatalogService.update_metadata": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_catalog_service_updates_only_mutable_metadata"
    ),
    "comfyreview.application.prompt_catalog:PromptCatalogService.update_component": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_catalog_service_updates_metadata_and_revision_atomically"
    ),
    "comfyreview.application.prompt_catalog:prompt_revision_identity": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_revision_identity_is_content_and_component_stable"
    ),
    "comfyreview.application.prompt_catalog:prompt_component_key": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_component_key_is_readable_and_identity_scoped"
    ),
    "comfyreview.application.prompt_catalog:imported_prompt_component_uid": (
        "tests/test_prompt_catalog.py::"
        "test_imported_prompt_component_identity_is_stable_and_source_scoped"
    ),
    "comfyreview.application.arena:ArenaService.next_pair": (
        "tests/test_canonical_ranking_arena.py::"
        "test_arena_service_selects_forward_then_reverse_pair"
    ),
    "comfyreview.application.arena:ArenaService.record_decision": (
        "tests/test_canonical_ranking_arena.py::"
        "test_arena_service_records_clamped_target_ratings"
    ),
    "comfyreview.application.curation:CurationService.assign": (
        "tests/test_canonical_curation.py::"
        "test_curation_service_assigns_by_stable_image_identity"
    ),
    "comfyreview.application.ranking:RankingService.list_images": (
        "tests/test_canonical_ranking_arena.py::"
        "test_ranking_service_filters_and_sorts_canonical_images"
    ),
    "comfyreview.application.reviews:OutputImageReference.from_client_uid": (
        "tests/test_review_service.py::"
        "test_output_reference_accepts_canonical_uid"
    ),
    "comfyreview.application.reviews:ReviewService.submit": (
        "tests/test_review_service.py::"
        "test_review_service_submits_rating_in_order"
    ),
    "comfyreview.application.workflow_compilation:WorkflowCompiler.compile": (
        "tests/test_workflow_compiler.py::"
        "test_workflow_compiler_uses_only_explicit_roles_and_preserves_blueprint"
    ),
    "comfyreview.application.workflow_defaults:WorkflowDefaultsService.load": (
        "tests/test_workflow_defaults.py::"
        "test_workflow_defaults_service_reads_explicit_roles"
    ),
    "comfyreview.domain.prompts:parse_prompt_atoms": (
        "tests/test_prompt_atoms.py::"
        "test_parse_prompt_atoms_separates_text_and_explicit_weight"
    ),
    "comfyreview.settings:load_settings": (
        "tests/test_settings.py::"
        "test_environment_overrides_env_file_without_mutating_process"
    ),
    "quality.architecture:collect_architecture_violations": (
        "tests/test_architecture.py::"
        "test_repository_architecture_does_not_worsen"
    ),
    "quality.callable_manifest:discover_public_callables": (
        "tests/test_function_test_manifest.py::"
        "test_discovers_public_core_callables"
    ),
    "quality.callable_manifest:validate_manifest": (
        "tests/test_function_test_manifest.py::"
        "test_reports_invalid_manifest_entries"
    ),
    "comfyreview.observability:JsonLogFormatter.format": (
        "tests/test_observability.py::test_json_formatter_uses_approved_fields"
    ),
    "comfyreview.observability:configure_logging": (
        "tests/test_observability.py::test_configure_logging_is_idempotent"
    ),
    "comfyreview.observability:get_trace_id": (
        "tests/test_observability.py::test_request_context_is_isolated"
    ),
    "comfyreview.observability:normalize_request_id": (
        "tests/test_observability.py::test_normalizes_request_ids"
    ),
}
