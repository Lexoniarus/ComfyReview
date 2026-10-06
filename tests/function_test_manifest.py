"""Behavior-test ownership for every concrete public Python-core callable."""

FUNCTION_TEST_MANIFEST: dict[str, str] = {
    "comfyreview.application.lora_effects:LoraGraphEffectPolicy.effects": (
        "tests/test_content_classification.py::"
        "test_lora_graph_effect_policy_ignores_disconnected_and_zero_branches"
    ),
    "comfyreview.application.lora_effects:LoraGraphEffectPolicy.active_branches": (
        "tests/test_default_workflow_blueprint.py::"
        "test_default_blueprint_v4_wires_ordered_loras_through_model_and_clip"
    ),
    "comfyreview.application.lora_effects:CompiledLoraGraphPolicy.validate": (
        "tests/test_default_workflow_blueprint.py::"
        "test_default_blueprint_v4_wires_ordered_loras_through_model_and_clip"
    ),
    "comfyreview.application.image_generator_handoff:ImageGeneratorHandoffService.get": (
        "tests/test_image_generator_handoff.py::"
        "test_image_handoff_preserves_ordered_typed_prompt_selections"
    ),
    "comfyreview.application.render_guidance:RenderSettings.value": (
        "tests/test_render_guidance.py::"
        "test_render_settings_and_capability_values_are_stable"
    ),
    "comfyreview.application.render_guidance:RenderSettings.key": (
        "tests/test_render_guidance.py::"
        "test_render_settings_and_capability_values_are_stable"
    ),
    "comfyreview.application.render_guidance:RenderCapabilitySet.supports": (
        "tests/test_render_guidance.py::"
        "test_render_settings_and_capability_values_are_stable"
    ),
    "comfyreview.application.analytics_coverage:AnalyticsCoverageService.load": (
        "tests/test_analytics_coverage.py::"
        "test_analytics_coverage_reports_diagnostics_without_recommendations"
    ),
    "comfyreview.application.render_guidance:RenderGuidanceService.build": (
        "tests/test_render_guidance.py::"
        "test_guidance_exposes_four_modes_with_independent_image_support"
    ),
    "comfyreview.application.render_guidance:RenderGuidanceService.query": (
        "tests/test_render_guidance.py::"
        "test_guidance_query_filters_server_side_and_validates_dimensions"
    ),
    "comfyreview.application.generation_geometry:OutputTier.from_resolution_class": (
        "tests/test_image_geometry.py::"
        "test_output_tier_maps_to_resolution_classes"
    ),
    "comfyreview.application.generation_geometry:OutputTier.to_resolution_class": (
        "tests/test_image_geometry.py::"
        "test_output_tier_maps_to_resolution_classes"
    ),
    "comfyreview.application.generation_geometry:GenerationGeometryPolicy.resolve": (
        "tests/test_content_classification.py::"
        "test_generation_geometry_policy_resolves_matrix_and_classifies"
    ),
    "comfyreview.application.generation_geometry:GenerationGeometryPolicy.classify": (
        "tests/test_content_classification.py::"
        "test_generation_geometry_policy_resolves_matrix_and_classifies"
    ),
    "comfyreview.application.image_geometry:ImageGeometryProjectionService.project": (
        "tests/test_image_geometry.py::"
        "test_geometry_projection_projects_single_image"
    ),
    "comfyreview.application.image_geometry:ImageGeometryProjectionService.rebuild": (
        "tests/test_image_geometry.py::"
        "test_geometry_rebuild_scans_files_then_atomically_replaces_projection"
    ),
    "comfyreview.application.playground_evidence:PlaygroundEvidenceService.find": (
        "tests/test_image_geometry.py::"
        "test_playground_evidence_ranks_prompt_and_sampler_independently"
    ),
    "comfyreview.application.content_classification:infer_content_level": (
        "tests/test_content_classification.py::"
        "test_content_level_inference_uses_strictest_prompt_or_lora"
    ),
    "comfyreview.application.content_classification:PromptContentLevelPolicy.read": (
        "tests/test_content_classification.py::"
        "test_prompt_content_level_policy_prefers_canonical_and_writes_one_marker"
    ),
    "comfyreview.application.content_classification:PromptContentLevelPolicy.write": (
        "tests/test_content_classification.py::"
        "test_prompt_content_level_policy_prefers_canonical_and_writes_one_marker"
    ),
    "comfyreview.application.content_classification:LoraCatalogService.list_definitions": (
        "tests/test_content_classification.py::"
        "test_lora_catalog_and_selection_policy_require_typed_resolution"
    ),
    "comfyreview.application.content_classification:LoraCatalogService.get_definition": (
        "tests/test_content_classification.py::"
        "test_sqlite_lora_catalog_revisions_defaults_triggers_and_archive"
    ),
    "comfyreview.application.content_classification:LoraCatalogService.list_revisions": (
        "tests/test_content_classification.py::"
        "test_sqlite_lora_catalog_revisions_defaults_triggers_and_archive"
    ),
    "comfyreview.application.content_classification:LoraCatalogService.create": (
        "tests/test_content_classification.py::"
        "test_sqlite_lora_catalog_revisions_defaults_triggers_and_archive"
    ),
    "comfyreview.application.content_classification:LoraCatalogService.update": (
        "tests/test_content_classification.py::"
        "test_sqlite_lora_catalog_revisions_defaults_triggers_and_archive"
    ),
    "comfyreview.application.content_classification:LoraCatalogService.set_archived": (
        "tests/test_content_classification.py::"
        "test_sqlite_lora_catalog_revisions_defaults_triggers_and_archive"
    ),
    "comfyreview.application.content_classification:LoraDraftSelectionService.resolve": (
        "tests/test_content_classification.py::"
        "test_lora_draft_selection_uses_exact_revision_and_content_policy"
    ),
    "comfyreview.application.content_classification:LoraCatalogService.classify": (
        "tests/test_content_classification.py::"
        "test_lora_catalog_and_selection_policy_require_typed_resolution"
    ),
    "comfyreview.application.content_classification:LoraCatalogService.resolve": (
        "tests/test_content_classification.py::"
        "test_lora_catalog_and_selection_policy_require_typed_resolution"
    ),
    "comfyreview.application.content_classification:LoraCatalogService.preview": (
        "tests/test_content_classification.py::"
        "test_lora_catalog_and_selection_policy_require_typed_resolution"
    ),
    "comfyreview.application.content_classification:LoraCatalogService.reclassify": (
        "tests/test_content_classification.py::"
        "test_lora_catalog_and_selection_policy_require_typed_resolution"
    ),
    "comfyreview.application.content_classification:LoraSelectionContentPolicy.apply": (
        "tests/test_content_classification.py::"
        "test_lora_catalog_and_selection_policy_require_typed_resolution"
    ),
    "comfyreview.application.content_classification:ImageContentLevelService.set_level": (
        "tests/test_content_classification.py::"
        "test_image_content_level_service_supports_override_and_inherit"
    ),
    "comfyreview.application.catalog_evidence:CatalogEvidenceService.list_top_images": (
        "tests/test_catalog_evidence.py::"
        "test_catalog_evidence_service_validates_bounded_queries"
    ),
    "comfyreview.application.catalog_evidence:CatalogEvidenceService.list_top_lora_images": (
        "tests/test_catalog_evidence.py::"
        "test_catalog_evidence_service_validates_bounded_queries"
    ),
    "comfyreview.application.pagination:normalize_page": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_paging_is_bounded_and_scope_kind_is_explicit"
    ),
    "comfyreview.application.generation_queries:GenerationQueryService.list_generations": (
        "tests/test_generation_queries.py::"
        "test_generation_query_service_reads_persisted_lifecycle_state"
    ),
    "comfyreview.application.generation_queries:GenerationQueryService.get_generation": (
        "tests/test_generation_queries.py::"
        "test_generation_query_service_reads_persisted_lifecycle_state"
    ),
    "comfyreview.application.image_queries:DraftOverridePolicy.apply": (
        "tests/test_image_query_contracts.py::"
        "test_draft_override_policy_uses_canonical_renderer_semantics"
    ),
    "comfyreview.application.image_queries:ImageContextQueryService.list_images": (
        "tests/test_image_query_contracts.py::"
        "test_image_query_service_delegates_normalized_canonical_filter"
    ),
    "comfyreview.application.image_queries:ImageContextQueryService.get_image": (
        "tests/test_image_query_contracts.py::"
        "test_image_context_service_gets_by_uid_and_reports_missing_images"
    ),
    "comfyreview.application.image_queries:ScopeFacetService.list_facets": (
        "tests/test_image_query_contracts.py::"
        "test_scope_facet_service_keeps_repository_side_counting"
    ),
    "comfyreview.application.image_queries:ReviewCandidateService.next_candidate": (
        "tests/test_image_query_contracts.py::"
        "test_review_candidate_service_returns_unclassified_without_inference"
    ),
    "comfyreview.application.analytics:AnalyticsReportService.combo_statistics": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_report_service_normalizes_queries"
    ),
    "comfyreview.application.analytics:AnalyticsReportService.scope_statistics": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_report_service_normalizes_queries"
    ),
    "comfyreview.application.analytics:AnalyticsReportService.composition_statistics": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_report_service_normalizes_queries"
    ),
    "comfyreview.application.analytics:AnalyticsReportService.recommendations": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_report_service_normalizes_queries"
    ),
    "comfyreview.application.analytics:AnalyticsReportService.parameter_statistics": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_report_service_normalizes_queries"
    ),
    "comfyreview.application.analytics:AnalyticsReportService.calculated_best_cases": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_report_service_normalizes_queries"
    ),
    "comfyreview.application.analytics:AnalyticsReportService.list_models": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_report_service_normalizes_queries"
    ),
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
    "comfyreview.application.analytics:AnalyticsService.observed_combinations_by_character": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_handles_empty_and_observed_queries"
    ),
    "comfyreview.application.analytics:AnalyticsService.prompt_token_statistics": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_normalizes_canonical_queries"
    ),
    "comfyreview.application.reviews:ReviewHistoryService.list_for_image": (
        "tests/test_review_service.py::"
        "test_review_history_service_validates_identity_and_reports_missing"
    ),
    "comfyreview.application.analytics:AnalyticsService.token_statistics_for": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_normalizes_selected_tokens_and_matches"
    ),
    "comfyreview.application.analytics:AnalyticsService.best_prompt_match": (
        "tests/test_canonical_analytics.py::"
        "test_analytics_service_normalizes_selected_tokens_and_matches"
    ),
    "comfyreview.application.render_analytics:RenderAnalyticsService.summary": (
        "tests/test_canonical_analytics.py::"
        "test_focused_analytics_services_normalize_queries"
    ),
    "comfyreview.application.render_analytics:RenderAnalyticsService.parameter_values": (
        "tests/test_canonical_analytics.py::"
        "test_focused_analytics_services_normalize_queries"
    ),
    "comfyreview.application.composition_analytics:CompositionAnalyticsService.prompt_combinations": (
        "tests/test_canonical_analytics.py::"
        "test_focused_analytics_services_normalize_queries"
    ),
    "comfyreview.application.composition_analytics:CompositionAnalyticsService.render_setups": (
        "tests/test_canonical_analytics.py::"
        "test_focused_analytics_services_normalize_queries"
    ),
    "comfyreview.application.playground:PlaygroundService.prepare_draft": (
        "tests/test_playground_application.py::"
        "test_playground_sqlite_fixed_revision_is_exact_without_changing_latest"
    ),
    "comfyreview.application.playground:PlaygroundService.prepare_image_snapshot": (
        "tests/test_playground_application.py::"
        "test_playground_service_uses_authoritative_image_snapshot"
    ),
    "comfyreview.application.playground:PlaygroundService.list_available_components": (
        "tests/test_playground_application.py::"
        "test_playground_content_policy_filters_explicit_levels"
    ),
    "comfyreview.application.playground:PromptContentPolicy.filter": (
        "tests/test_playground_application.py::"
        "test_playground_content_policy_filters_explicit_levels"
    ),
    "comfyreview.application.playground:PlaygroundService.prepare_revision_draft": (
        "tests/test_playground_application.py::"
        "test_playground_service_restores_exact_revisions_and_compositions"
    ),
    "comfyreview.application.playground:PlaygroundService.prepare_composition_draft": (
        "tests/test_playground_application.py::"
        "test_playground_service_restores_exact_revisions_and_compositions"
    ),
    "comfyreview.application.playground:PlaygroundService.resolve_composition_prompt_selections": (
        "tests/test_playground_application.py::"
        "test_playground_service_resolves_ordered_exact_composition_selections"
    ),
    "comfyreview.application.playground:PlaygroundService.confirm_draft": (
        "tests/test_playground_application.py::"
        "test_playground_service_revalidates_confirmed_draft_and_derives_revisions"
    ),
    "comfyreview.application.playground_generation:PlaygroundGenerationPolicy.build_request": (
        "tests/test_playground_generation.py::"
        "test_playground_generation_policy_builds_reproducible_request"
    ),
    "comfyreview.application.playground_generation:PlaygroundGenerationSweepPolicy.expand": (
        "tests/test_playground_generation.py::"
        "test_generation_sweep_expands_ranges_and_random_seeds_deterministically"
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
    "comfyreview.application.generation:GenerationService.observe": (
        "tests/test_generation_service.py::"
        "test_generation_service_observes_without_resubmitting"
    ),
    "comfyreview.application.generation_lifecycle:GenerationLifecycleCoordinator.run_once": (
        "tests/test_generation_lifecycle.py::"
        "test_lifecycle_coordinator_recovers_local_interrupted_states"
    ),
    "comfyreview.application.generation_lifecycle:GenerationLifecycleWorker.start": (
        "tests/test_generation_lifecycle.py::"
        "test_lifecycle_worker_owns_one_thread_and_stops_cleanly"
    ),
    "comfyreview.application.generation_lifecycle:GenerationLifecycleWorker.stop": (
        "tests/test_generation_lifecycle.py::"
        "test_lifecycle_worker_owns_one_thread_and_stops_cleanly"
    ),
    "comfyreview.application.generation_reconciliation:GenerationReconciliationService.reconcile": (
        "tests/test_generation_reconciliation.py::"
        "test_reconciliation_completes_from_already_persisted_outputs"
    ),
    "comfyreview.application.generation_outputs:GenerationOutputCollector.collect": (
        "tests/test_generation_outputs.py::"
        "test_output_collector_maps_expected_nodes_and_actual_batch_indexes"
    ),
    "comfyreview.application.generation_outputs:GenerationOutputCollector.collect_descriptors": (
        "tests/test_generation_outputs.py::"
        "test_output_collector_maps_expected_nodes_and_actual_batch_indexes"
    ),
    "comfyreview.application.generation_outputs:GenerationOutputRecoveryService.recover": (
        "tests/test_generation_outputs.py::"
        "test_output_recovery_uses_canonical_collector_mapping"
    ),
    "comfyreview.application.generation_outputs:GenerationOutputCollector.outputs_complete": (
        "tests/test_generation_outputs.py::"
        "test_output_collector_reports_prior_atomic_collection"
    ),
    "comfyreview.application.generation_outputs:generation_output_identity": (
        "tests/test_generation_outputs.py::"
        "test_generation_output_identity_does_not_depend_on_path"
    ),
    "comfyreview.application.playground:PromptRenderer.render": (
        "tests/test_playground_application.py::"
        "test_prompt_renderer_keeps_revision_snapshot_and_draft_override_separate"
    ),
    "comfyreview.application.playground:PromptRenderer.render_blocks": (
        "tests/test_playground_application.py::"
        "test_prompt_renderer_keeps_revision_snapshot_and_draft_override_separate"
    ),
    "comfyreview.application.playground:PromptRenderer.render_atoms": (
        "tests/test_prompt_atoms.py::"
        "test_structured_prompt_usages_validate_and_render_deterministically"
    ),
    "comfyreview.application.playground:PromptSelectionPolicy.select": (
        "tests/test_playground_application.py::"
        "test_prompt_selection_policy_selects_reproducible_compatible_revisions"
    ),
    "comfyreview.application.playground:PromptSelectionPolicy.confirm": (
        "tests/test_playground_application.py::"
        "test_prompt_selection_policy_confirms_exact_components_in_domain_order"
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
    "comfyreview.application.prompt_catalog:PromptCatalogService.list_revisions": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_catalog_service_archives_restores_and_lists"
    ),
    "comfyreview.application.prompt_catalog:PromptCatalogService.list_components_for_revisions": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_catalog_service_archives_restores_and_lists"
    ),
    "comfyreview.application.prompt_catalog:PromptCatalogService.list_composition_components": (
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
    "comfyreview.application.prompt_catalog:prompt_composition_identity": (
        "tests/test_prompt_catalog.py::"
        "test_prompt_composition_identity_uses_slots_positions_and_revisions"
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
        "test_arena_service_rotates_before_selecting_reverse_pair"
    ),
    "comfyreview.application.arena:FairArenaPairingPolicy.select": (
        "tests/test_canonical_ranking_arena.py::"
        "test_arena_service_rotates_before_selecting_reverse_pair"
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
    "comfyreview.application.workspace_settings:GenerationProfileService.create": (
        "tests/test_workspace_settings.py::"
        "test_generation_profile_service_preserves_ordered_lora_stack"
    ),
    "comfyreview.application.workspace_settings:GenerationProfileService.list_profiles": (
        "tests/test_workspace_settings.py::"
        "test_generation_profile_service_preserves_ordered_lora_stack"
    ),
    "comfyreview.application.workspace_settings:GenerationProfileService.set_archived": (
        "tests/test_workspace_settings.py::"
        "test_generation_profile_service_updates_and_protects_default_profile"
    ),
    "comfyreview.application.workspace_settings:GenerationProfileService.update": (
        "tests/test_workspace_settings.py::"
        "test_generation_profile_service_updates_and_protects_default_profile"
    ),
    "comfyreview.application.workspace_settings:WorkspacePreferencesService.get": (
        "tests/test_workspace_settings.py::"
        "test_workspace_preferences_service_validates_and_ignores_dormant_profile"
    ),
    "comfyreview.application.workspace_settings:WorkspacePreferencesService.update": (
        "tests/test_workspace_settings.py::"
        "test_workspace_preferences_service_validates_and_ignores_dormant_profile"
    ),
    "comfyreview.application.runtime_diagnostics:RuntimeDiagnosticsService.inspect": (
        "tests/test_workspace_settings.py::"
        "test_runtime_diagnostics_normalizes_connected_and_offline_states"
    ),
    "comfyreview.application.runtime_diagnostics:RuntimeDiagnosticsService.snapshot": (
        "tests/test_workspace_settings.py::"
        "test_runtime_diagnostics_caches_capabilities_for_fast_snapshots"
    ),
    "comfyreview.domain.prompts:parse_prompt_atoms": (
        "tests/test_prompt_atoms.py::"
        "test_parse_prompt_atoms_separates_text_and_explicit_weight"
    ),
    "comfyreview.domain.prompts:PromptAtomUsage.weight": (
        "tests/test_prompt_atoms.py::"
        "test_structured_prompt_usages_validate_and_render_deterministically"
    ),
    "comfyreview.domain.prompts:prompt_atom_usage": (
        "tests/test_prompt_atoms.py::"
        "test_structured_prompt_usages_validate_and_render_deterministically"
    ),
    "comfyreview.domain.prompts:prompt_atom_usages_from_text": (
        "tests/test_prompt_atoms.py::"
        "test_structured_prompt_usages_validate_and_render_deterministically"
    ),
    "comfyreview.domain.prompts:render_prompt_atom_usages": (
        "tests/test_prompt_atoms.py::"
        "test_structured_prompt_usages_validate_and_render_deterministically"
    ),
    "comfyreview.settings:load_settings": (
        "tests/test_settings.py::"
        "test_environment_overrides_env_file_without_mutating_process"
    ),
    "comfyreview.settings:load_legacy_migration_settings": (
        "tests/test_settings.py::"
        "test_legacy_migration_settings_are_loaded_separately"
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
