"""HTTP contracts for complete Card groups, pool Cards, and the POC deck."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from comfyreview.application import ContentLevel
from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupConflictError,
    CardCandidateGroupStatus,
)
from comfyreview.application.card_battler_deck import CardDeckConflictError
from comfyreview.application.generation_outputs import GenerationOutput
from comfyreview.domain.card_battler import (
    POC_DECK_ID,
    CardDeck,
    CardDeckEntry,
)
from routers.api_v2.card_factory import router
from tests.test_card_candidate_acceptance import _ready_group
from tests.test_card_development_candidate_groups import _pool_card


class _InitialGroups:
    def __init__(self, group) -> None:
        self.group = group
        self.calls: list[object] = []

    def reserve(self, image_uid):
        self.calls.append(image_uid)
        return self.group


class _Groups:
    def __init__(self, group) -> None:
        self.group = group
        self.calls: list[object] = []

    def list_groups(self):
        return (self.group,)

    def get(self, group_id):
        self.calls.append(("get", group_id))
        return self.group

    def reject(self, group_id, *, expected_revision):
        self.calls.append(("reject", group_id, expected_revision))
        return replace(
            self.group,
            revision=expected_revision + 1,
            status=CardCandidateGroupStatus.REJECTED,
        )

    def retry_initial(self, group_id, *, expected_revision):
        self.calls.append(("retry", group_id, expected_revision))
        return self.group


class _Acceptance:
    def __init__(self, card) -> None:
        self.card = card
        self.calls: list[object] = []

    def accept(self, group_id, candidate_id, *, expected_revision):
        self.calls.append((group_id, candidate_id, expected_revision))
        return self.card


class _DevelopmentGroups:
    def __init__(self, group) -> None:
        self.group = group
        self.calls: list[object] = []

    def reserve(self, card_id, *, expected_revision):
        self.calls.append((card_id, expected_revision))
        return self.group


class _Cards:
    def __init__(self, card) -> None:
        self.card = card

    def list_cards(self):
        return (self.card,)

    def get(self, card_id):
        return self.card


class _Deck:
    def __init__(self, card_id: str) -> None:
        self.deck = CardDeck(POC_DECK_ID, 1, ())
        self.card_id = card_id
        self.calls: list[object] = []

    def get(self):
        return self.deck

    def add(self, card_id, *, expected_revision):
        self.calls.append(("add", card_id, expected_revision))
        self.deck = CardDeck(
            POC_DECK_ID,
            expected_revision + 1,
            (CardDeckEntry(card_id, 0),),
        )
        return self.deck

    def remove(self, card_id, *, expected_revision):
        self.calls.append(("remove", card_id, expected_revision))
        self.deck = CardDeck(POC_DECK_ID, expected_revision + 1, ())
        return self.deck

    def reorder(self, card_ids, *, expected_revision):
        self.calls.append(("reorder", card_ids, expected_revision))
        self.deck = CardDeck(
            POC_DECK_ID,
            expected_revision + 1,
            tuple(
                CardDeckEntry(card_id, position)
                for position, card_id in enumerate(card_ids)
            ),
        )
        return self.deck


class _Outputs:
    def __init__(self, path: Path) -> None:
        self.path = path

    def output_by_image_uid(self, image_uid):
        return GenerationOutput(
            image_uid,
            "primary",
            "save",
            0,
            self.path,
            "content-hash",
        )


class _Runtime:
    def __init__(self, services) -> None:
        self.services = services

    def get(self):
        return self.services


class _ImageContexts:
    def __init__(self) -> None:
        self.query = None

    def list_images(self, query):
        self.query = query
        return SimpleNamespace(
            entries=(SimpleNamespace(image_uid="image-1"),),
            total=1,
            offset=query.offset,
            limit=query.limit,
        )


class _ImageResponses:
    def summary(self, image):
        return {"image_uid": image.image_uid}

    def image_url(self, image_uid):
        return f"/files/{image_uid}.png"


class _FileUrls:
    def to_url(self, path: Path) -> str:
        return "/files/" + path.name


def _client(tmp_path: Path):
    group = _ready_group(tmp_path)
    card = _pool_card()
    services = SimpleNamespace(
        initial_groups=_InitialGroups(group),
        groups=_Groups(group),
        acceptance=_Acceptance(card),
        development_groups=_DevelopmentGroups(group),
        cards=_Cards(card),
        deck=_Deck(card.state.identity.card_id),
        outputs=_Outputs(tmp_path / "card.png"),
    )
    image_contexts = _ImageContexts()
    container = SimpleNamespace(
        card_factory_runtime=_Runtime(services),
        image_contexts=image_contexts,
        image_responses=_ImageResponses(),
        file_urls=_FileUrls(),
    )
    application = FastAPI()
    application.state.container = container
    application.include_router(router, prefix="/api/v2")
    return TestClient(application), container, services


def test_card_source_api_applies_server_side_standard_filter(
    tmp_path: Path,
) -> None:
    client, container, _ = _client(tmp_path)

    response = client.get("/api/v2/card-factory/sources?offset=0&limit=12")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"image_uid": "image-1", "image_url": "/files/image-1.png"}
    ]
    assert (
        container.image_contexts.query.filters.effective_content_level
        is ContentLevel.STANDARD
    )


def test_group_api_reserves_lists_reads_rejects_retries_and_accepts(
    tmp_path: Path,
) -> None:
    client, _, services = _client(tmp_path)
    group = services.groups.group
    candidate_id = group.candidates[0].candidate_id

    created = client.post(
        "/api/v2/card-factory/candidate-groups",
        json={"image_uid": "image-1"},
    )
    listed = client.get("/api/v2/card-factory/candidate-groups")
    loaded = client.get(
        f"/api/v2/card-factory/candidate-groups/{group.group_id}"
    )
    rejected = client.post(
        f"/api/v2/card-factory/candidate-groups/{group.group_id}/reject",
        json={"expected_revision": group.revision},
    )
    retried = client.post(
        f"/api/v2/card-factory/candidate-groups/{group.group_id}/retry",
        json={"expected_revision": group.revision},
    )
    accepted = client.post(
        f"/api/v2/card-factory/candidate-groups/{group.group_id}/"
        f"candidates/{candidate_id}/accept",
        json={"expected_revision": group.revision},
    )

    assert [
        created.status_code,
        listed.status_code,
        loaded.status_code,
        rejected.status_code,
        retried.status_code,
        accepted.status_code,
    ] == [202, 200, 200, 200, 202, 200]
    assert created.json()["candidates"][0]["artifacts"]["card"]["stats"]
    assert listed.json()["items"][0]["group_id"] == group.group_id
    assert loaded.json()["actions"] == {
        "can_accept": True,
        "can_reject": True,
        "can_retry": True,
    }
    assert accepted.json()["card_id"] == "card-1"
    assert services.initial_groups.calls == ["image-1"]
    assert services.acceptance.calls == [
        (group.group_id, candidate_id, group.revision)
    ]


def test_card_and_deck_api_expose_current_pool_and_revision_safe_commands(
    tmp_path: Path,
) -> None:
    client, _, services = _client(tmp_path)
    card_id = services.cards.card.state.identity.card_id
    group = services.groups.group

    cards = client.get("/api/v2/card-factory/cards")
    card = client.get(f"/api/v2/card-factory/cards/{card_id}")
    developed = client.post(
        f"/api/v2/card-factory/cards/{card_id}/development-groups",
        json={"expected_revision": 1},
    )
    deck = client.get("/api/v2/card-factory/deck")
    added = client.post(
        f"/api/v2/card-factory/deck/cards/{card_id}",
        json={"expected_revision": 1},
    )
    reordered = client.put(
        "/api/v2/card-factory/deck/order",
        json={"expected_revision": 2, "card_ids": [card_id]},
    )
    removed = client.request(
        "DELETE",
        f"/api/v2/card-factory/deck/cards/{card_id}",
        json={"expected_revision": 3},
    )

    assert [
        cards.status_code,
        card.status_code,
        developed.status_code,
        deck.status_code,
        added.status_code,
        reordered.status_code,
        removed.status_code,
    ] == [200, 200, 202, 200, 200, 200, 200]
    assert cards.json()["items"][0]["card_id"] == card_id
    assert card.json()["actions"] == {"can_develop": True}
    assert developed.json()["group_id"] == group.group_id
    assert deck.json()["deck"]["capacity"] == 40
    assert added.json()["entries"][0]["card_id"] == card_id
    assert reordered.json()["entries"][0]["position"] == 0
    assert removed.json()["entries"] == []
    assert services.development_groups.calls == [(card_id, 1)]
    assert services.deck.calls == [
        ("add", card_id, 1),
        ("reorder", (card_id,), 2),
        ("remove", card_id, 3),
    ]


def test_group_and_deck_conflicts_map_to_http_409(tmp_path: Path) -> None:
    client, _, services = _client(tmp_path)

    def reject(*_args, **_kwargs):
        raise CardCandidateGroupConflictError("stale group")

    def add(*_args, **_kwargs):
        raise CardDeckConflictError("stale deck")

    services.groups.reject = reject
    services.deck.add = add
    group = services.groups.group
    card_id = services.cards.card.state.identity.card_id

    group_response = client.post(
        f"/api/v2/card-factory/candidate-groups/{group.group_id}/reject",
        json={"expected_revision": group.revision},
    )
    deck_response = client.post(
        f"/api/v2/card-factory/deck/cards/{card_id}",
        json={"expected_revision": 1},
    )

    assert group_response.status_code == 409
    assert group_response.json()["error"]["code"] == (
        "card_candidate_group_conflict"
    )
    assert deck_response.status_code == 409
    assert deck_response.json()["error"]["code"] == "card_deck_conflict"


def test_legacy_session_endpoints_are_removed(tmp_path: Path) -> None:
    client, _, _ = _client(tmp_path)

    assert (
        client.post(
            "/api/v2/card-factory/sessions",
            json={"image_uid": "image-1"},
        ).status_code
        == 404
    )
