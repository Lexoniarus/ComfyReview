"""Lazy composition owner for the complete Card-candidate POC runtime."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from comfyreview.application.card_battler_candidate_group_catalog import (
    CardCandidateGroupCatalogService,
)
from comfyreview.application.card_battler_candidate_group_service import (
    InitialCardCandidateGroupService,
)
from comfyreview.application.card_battler_candidate_image_service import (
    CardCandidateImageService,
)
from comfyreview.application.card_battler_candidate_images import (
    CardCandidateGenerationPolicy,
)
from comfyreview.application.card_battler_candidate_processing import (
    CardCandidateCompositionCoordinator,
    CardCandidateGroupLifecycleProcessor,
    CardCandidateGroupWorker,
    DevelopmentCardCandidateGroupProcessor,
    InitialCardCandidateGroupProcessor,
)
from comfyreview.application.card_battler_card_catalog import (
    CardPoolCatalogService,
)
from comfyreview.application.card_battler_card_pool import (
    CardCandidateAcceptanceService,
    DevelopmentCardCandidateAcceptancePolicy,
    InitialCardCandidateAcceptancePolicy,
)
from comfyreview.application.card_battler_common import CommonCardMaterializer
from comfyreview.application.card_battler_deck import (
    CardDeckPolicy,
    CardDeckService,
)
from comfyreview.application.card_battler_development import DevelopmentPlanner
from comfyreview.application.card_battler_development_addition import (
    CompatibleTraitAdditionPolicy,
)
from comfyreview.application.card_battler_development_groups import (
    CardDevelopmentCandidateComposer,
    CardDevelopmentCandidateGroupService,
)
from comfyreview.application.card_battler_development_improvement import (
    ExistingTraitImprovementPolicy,
)
from comfyreview.application.card_battler_development_service import (
    CardDevelopmentService,
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
from comfyreview.providers.card_candidate_group_identities import (
    SecureCardCandidateGroupSeedSource,
    UuidCardCandidateGroupIdentitySource,
)
from comfyreview.providers.card_identities import UuidCardIdentitySource
from comfyreview.providers.card_reference_images import (
    CanonicalCardCandidateReferenceImageProvider,
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
from comfyreview.repositories.sqlite.card_battler_candidate_groups import (
    SqliteCardCandidateGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_card_pool import (
    SqliteCardPoolRepository,
)
from comfyreview.repositories.sqlite.card_battler_deck import (
    SqliteCardDeckRepository,
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
from comfyreview.repositories.sqlite.card_battler_visual_model import (
    SqliteCardVisualModelRepository,
)
from comfyreview.settings import Settings


@dataclass(frozen=True, slots=True)
class CardFactoryPrototypeServices:
    """Expose Application services required by Card HTTP adapters."""

    initial_groups: InitialCardCandidateGroupService
    groups: CardCandidateGroupCatalogService
    acceptance: CardCandidateAcceptanceService
    development_groups: CardDevelopmentCandidateGroupService
    cards: CardPoolCatalogService
    deck: CardDeckService
    outputs: SqliteCardGenerationOutputRepository
    worker: CardCandidateGroupWorker


class CardFactoryPrototypeRuntime:
    """Build and own the Card-candidate service graph once per process."""

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

    def start(self) -> None:
        """Start the one owned Candidate worker after application startup."""
        self.get().worker.start()

    def stop(self) -> bool:
        """Stop the Candidate worker if the service graph was initialized."""
        with self._lock:
            services = self._services
        return True if services is None else services.worker.stop()

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
        local_models = LocalModelRuntime(
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
            runtime=local_models,
            inference=inference,
            vision_model_id=settings.lm_studio_vision_model,
        )
        presentation = CardPresentationRealizer(
            runtime=local_models,
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
        groups = SqliteCardCandidateGroupRepository(database_path)
        cards = SqliteCardPoolRepository(database_path)
        identities = UuidCardCandidateGroupIdentitySource()
        seeds = SecureCardCandidateGroupSeedSource()
        source_images = CanonicalCardSourceImageProvider(self._image_resolver)
        initial_groups = InitialCardCandidateGroupService(
            image_contexts=self._image_contexts,
            source_images=source_images,
            eligibility=CardSourceEligibilityPolicy(),
            groups=groups,
            identities=identities,
            seeds=seeds,
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
        candidate_images = CardCandidateImageService(
            groups=groups,
            reference_images=CanonicalCardCandidateReferenceImageProvider(
                source_images,
                card_outputs,
            ),
            stager=ComfyUiCardReferenceImageStager(
                UrlLibMultipartUploadTransport(settings.comfyui_base_url)
            ),
            policy=CardCandidateGenerationPolicy(
                checkpoint=settings.card_evolution_checkpoint
            ),
            generations=generation_service,
            outputs=card_outputs,
        )
        development_groups = CardDevelopmentCandidateGroupService(
            cards=cards,
            groups=groups,
            identities=identities,
            seeds=seeds,
        )
        composition = CardCandidateCompositionCoordinator(
            initial=InitialCardCandidateGroupProcessor(
                groups=groups,
                source_images=source_images,
                analyzer=analyzer,
                factory=factory,
            ),
            development=DevelopmentCardCandidateGroupProcessor(
                groups=groups,
                cards=cards,
                composer=CardDevelopmentCandidateComposer(
                    development=development_service,
                    visual_projector=projector,
                    presentation_realizer=presentation,
                ),
            ),
        )
        worker = CardCandidateGroupWorker(
            CardCandidateGroupLifecycleProcessor(
                composition=composition,
                groups=groups,
                images=candidate_images,
            )
        )
        return CardFactoryPrototypeServices(
            initial_groups=initial_groups,
            groups=CardCandidateGroupCatalogService(
                groups=groups,
                initial_groups=initial_groups,
            ),
            acceptance=CardCandidateAcceptanceService(
                groups=groups,
                cards=cards,
                identities=UuidCardIdentitySource(),
                policy=InitialCardCandidateAcceptancePolicy(),
                development_policy=DevelopmentCardCandidateAcceptancePolicy(),
            ),
            development_groups=development_groups,
            cards=CardPoolCatalogService(cards),
            deck=CardDeckService(
                decks=SqliteCardDeckRepository(database_path),
                cards=cards,
                policy=CardDeckPolicy(),
            ),
            outputs=card_outputs,
            worker=worker,
        )
