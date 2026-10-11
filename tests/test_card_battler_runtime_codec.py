"""Round-trip tests for isolated Card-runtime structured values."""

from __future__ import annotations

from comfyreview.domain.card_battler import (
    CARD_DEVELOPMENT_ALGORITHM_REVISION,
    CardDevelopmentProvenance,
    CardDevelopmentResult,
    TraitDevelopmentAction,
)
from comfyreview.repositories.sqlite.card_battler_runtime_codec import (
    decode_development_result,
    encode_value,
)
from tests.test_card_battler_development_domain import _card_spec


def test_runtime_codec_round_trips_exact_development_action() -> None:
    card = _card_spec()
    provenance = CardDevelopmentProvenance(
        "prototype_development",
        1,
        CARD_DEVELOPMENT_ALGORITHM_REVISION,
    )
    result = CardDevelopmentResult(
        card=card,
        action=TraitDevelopmentAction(
            "improve_existing_trait",
            0,
            card.traits[0],
            card.traits[0],
        ),
        provenance=provenance,
    )

    assert decode_development_result(encode_value(result)) == result
