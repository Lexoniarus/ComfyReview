"""Lazy composition owner for the optional Card Factory prototype runtime."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from comfyreview.application.card_battler_common import CommonCardMaterializer
from comfyreview.application.card_battler_development import DevelopmentPlanner
from comfyreview.application.card_battler_development_addition import (
    CompatibleTraitAdditionPolicy,
)
from comfyreview.application.card_battler_development_improvement import (
    ExistingTraitImprovementPolicy,
)
from comfyreview.application.card_battler_development_service import (
    CardDevelopmentService,
)
from comfyreview.application.card_battler_evolution import (
    CardEvolutionGenerationPolicy,
    CardEvolutionService,
)
from comfyreview.application.card_battler_factory import CardFactory
from comfyreview.application.card_battler_mapping import CardImprintMapper
from comfyreview.application.card_battler_materialization import (
    CardStatMaterializer,
    StatProfileSelector,
)
from comfyreview.application.card_battler_presentation import (
    CardPresentationRealizer,
)
from comfyreview.application.card_battler_preview import (
    CardSourceEligibilityPolicy,
)
from comfyreview.application.card_battler_rules import (
    CanonicalRuleRenderer,
    MechanicMaterializer,
)
from comfyreview.application.card_battler_semantics import (
    SemanticImageAnalyzer,
)
from comfyreview.application.card_battler_session_service import (
    CardFactorySessionService,
)
from comfyreview.application.card_battler_trait_selection import (
    InitialTraitSelector,
)
from comfyreview.application.card_battler_visual_projection import (
    VisualPromptProjector,
)
from comfyreview.application.comfyui import ComfyUiProvider
from comfyreview.application.generation import GenerationService
from comfyreview.application.generation_outputs import (
    GenerationOutputCollector,
)
from comfyreview.application.image_queries import ImageContextQueryService
from comfyreview.application.local_model_runtime import LocalModelRuntime
from comfyreview.application.workflow_compilation import (
    WorkflowBlueprintRepository,
    WorkflowCompiler,
)
from comfyreview.providers.card_reference_images import (
    CanonicalCardSessionReferenceImageProvider,
)
from comfyreview.providers.card_session_identities import (
    UuidCardSessionIdentitySource,
)
from comfyreview.providers.card_source_images import (
    CanonicalCardImageResolver,
    CanonicalCardSourceImageProvider,
)
from comfyreview.providers.comfyui_uploads import (
    ComfyUiCardReferenceImageStager,
    UrlLibMultipartUploadTransport,
)
from comfyreview.providers.generation_outputs import (
    LocalGenerationOutputSource,
)
from comfyreview.providers.lm_studio import (
    NativeLmStudioProvider,
    UrlLibLmStudioJsonTransport,
)
from comfyreview.providers.lm_studio_structured_inference import (
    NativeLmStudioStructuredInferenceProvider,
)
from comfyreview.providers.prompt_identities import (
    UuidGenerationIdentitySource,
)
from comfyreview.repositories.sqlite.card_battler_candidates import (
    SqliteCardCandidateRepository,
)
from comfyreview.repositories.sqlite.card_battler_development_model import (
    SqliteCardDevelopmentModelRepository,
)
from comfyreview.repositories.sqlite.card_battler_generations import (
    SqliteCardGenerationOutputRepository,
    SqliteCardGenerationRepository,
)
from comfyreview.repositories.sqlite.card_battler_materialization_model import (
    SqliteCardMaterializationModelRepository,
)
from comfyreview.repositories.sqlite.card_battler_model import (
    SqliteCardBattlerModelRepository,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    SqliteCardBattlerModelResource,
)
from comfyreview.repositories.sqlite.card_battler_sessions import (
    SqliteCardSessionRepository,
)
from comfyreview.repositories.sqlite.card_battler_visual_model import (
    SqliteCardVisualModelRepository,
)
from comfyreview.settings import Settings


@dataclass(frozen=True, slots=True)
class CardFactoryPrototypeServices:
    """Expose the focused services required by Card API adapters."""

    sessions: CardFactorySessionService
    evolution: CardEvolutionService
    candidates: SqliteCardCandidateRepository


class CardFactoryPrototypeRuntime:
    """Build the optional Card service graph once on first Card use."""

    def __init__(
        self,
        *,
        settings: Settings,
        model_resource: SqliteCardBattlerModelResource,
        image_contexts: ImageContextQueryService,
        image_resolver: CanonicalCardImageResolver,
        comfyui: ComfyUiProvider,
        blueprints: WorkflowBlueprintRepository,
    ) -> None:
        self._settings = settings
        self._model_resource = model_resource
        self._image_contexts = image_contexts
        self._image_resolver = image_resolver
        self._comfyui = comfyui
        self._blueprints = blueprints
        self._lock = Lock()
        self._services: CardFactoryPrototypeServices | None = None

    def get(self) -> CardFactoryPrototypeServices:
        """Return the one lazily composed Card service graph."""
        with self._lock:
            if self._services is None:
                self._services = self._build()
            return self._services

    def _build(self) -> CardFactoryPrototypeServices:
        settings = self._settings
        model = SqliteCardBattlerModelRepository(self._model_resource)
        materialization = SqliteCardMaterializationModelRepository(
            self._model_resource
        )
        development = SqliteCardDevelopmentModelRepository(
            self._model_resource
        )
        visual = SqliteCardVisualModelRepository(self._model_resource)
        ruleset = model.resolve_ruleset()
        mechanics = MechanicMaterializer()
        rules = CanonicalRuleRenderer()
        stats = CardStatMaterializer()
        projector = VisualPromptProjector(visual, ruleset)

        transport = UrlLibLmStudioJsonTransport(
            settings.lm_studio_base_url,
            settings.lm_studio_api_token,
        )
        runtime = LocalModelRuntime(
            NativeLmStudioProvider(
                transport,
                list_timeout_seconds=settings.lm_studio_list_timeout_seconds,
                load_timeout_seconds=settings.lm_studio_load_timeout_seconds,
                unload_timeout_seconds=(
                    settings.lm_studio_unload_timeout_seconds
                ),
            )
        )
        inference = NativeLmStudioStructuredInferenceProvider(
            transport,
            inference_timeout_seconds=(
                settings.lm_studio_inference_timeout_seconds
            ),
        )
        analyzer = SemanticImageAnalyzer(
            model_repository=model,
            runtime=runtime,
            inference=inference,
            vision_model_id=settings.lm_studio_vision_model,
        )
        presentation = CardPresentationRealizer(
            runtime=runtime,
            inference=inference,
            text_model_id=settings.lm_studio_text_model,
        )
        materializer = CommonCardMaterializer(
            model,
            materialization,
            StatProfileSelector(),
            stats,
            InitialTraitSelector(),
            mechanics,
            rules,
        )
        factory = CardFactory(
            analyzer=analyzer,
            mapper=CardImprintMapper(model),
            materializer=materializer,
            visual_projector=projector,
            presentation_realizer=presentation,
        )
        development_service = CardDevelopmentService(
            model,
            materialization,
            DevelopmentPlanner(model, development),
            ExistingTraitImprovementPolicy(
                model,
                development,
                materialization,
                mechanics,
                rules,
            ),
            CompatibleTraitAdditionPolicy(
                model,
                development,
                materialization,
                mechanics,
                rules,
            ),
            stats,
        )

        database_path = settings.card_battler_runtime_database_path
        sessions = SqliteCardSessionRepository(database_path)
        session_service = CardFactorySessionService(
            image_contexts=self._image_contexts,
            source_images=CanonicalCardSourceImageProvider(
                self._image_resolver
            ),
            eligibility=CardSourceEligibilityPolicy(),
            factory=factory,
            sessions=sessions,
            identities=UuidCardSessionIdentitySource(),
            development=development_service,
            visual_projector=projector,
            presentation_realizer=presentation,
        )

        card_generations = SqliteCardGenerationRepository(database_path)
        card_outputs = SqliteCardGenerationOutputRepository(
            database_path,
            settings.output_root,
        )
        generation_service = GenerationService(
            blueprints=self._blueprints,
            compiler=WorkflowCompiler(),
            generations=card_generations,
            comfyui=self._comfyui,
            outputs=GenerationOutputCollector(
                comfyui=self._comfyui,
                source=LocalGenerationOutputSource(settings.output_root),
                repository=card_outputs,
            ),
            identities=UuidGenerationIdentitySource(),
        )
        candidates = SqliteCardCandidateRepository(database_path)
        evolution = CardEvolutionService(
            sessions=sessions,
            candidates=candidates,
            reference_images=CanonicalCardSessionReferenceImageProvider(
                CanonicalCardSourceImageProvider(self._image_resolver),
                card_outputs,
            ),
            stager=ComfyUiCardReferenceImageStager(
                UrlLibMultipartUploadTransport(settings.comfyui_base_url)
            ),
            policy=CardEvolutionGenerationPolicy(
                checkpoint=settings.card_evolution_checkpoint
            ),
            generations=generation_service,
            outputs=card_outputs,
        )
        return CardFactoryPrototypeServices(
            sessions=session_service,
            evolution=evolution,
            candidates=candidates,
        )
