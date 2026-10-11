import { expect, test } from "@playwright/test";
import { Buffer } from "node:buffer";

const pixel = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

test("Card Factory moves one complete candidate through pool, deck and development", async ({
  page,
}) => {
  const browserErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));

  let initialReservations = 0;
  let deckRevision = 1;
  let deckCardIds = [];
  let cardRevision = 1;
  let acceptedTitle = "Neonwache B";

  await page.route("**/files/e2e/**", (route) =>
    route.fulfill({ contentType: "image/png", body: pixel }),
  );
  await page.route("**/api/v2/card-factory/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();

    if (path.endsWith("/sources")) {
      await route.fulfill({
        json: {
          total: 1,
          offset: 0,
          limit: 24,
          items: [
            {
              image_uid: "image-e2e-01",
              image_url: "/files/e2e/source.png",
            },
          ],
        },
      });
      return;
    }
    if (path.endsWith("/candidate-groups") && method === "POST") {
      initialReservations += 1;
      await route.fulfill({ status: 202, json: group("initial") });
      return;
    }
    if (path.endsWith("/candidate-groups") && method === "GET") {
      await route.fulfill({ json: { items: [group("initial")] } });
      return;
    }
    if (path.endsWith("/candidate-groups/initial-group")) {
      await route.fulfill({ json: group("initial") });
      return;
    }
    if (path.endsWith("/candidate-groups/development-group")) {
      await route.fulfill({ json: group("development") });
      return;
    }
    if (path.endsWith("/accept") && method === "POST") {
      if (path.includes("development-group")) {
        cardRevision += 1;
        acceptedTitle = "Neonwache Ascended";
      }
      await route.fulfill({ json: poolCard() });
      return;
    }
    if (path.endsWith("/development-groups") && method === "POST") {
      await route.fulfill({ status: 202, json: group("development") });
      return;
    }
    if (path.endsWith("/deck") && method === "GET") {
      await route.fulfill({ json: deckPayload() });
      return;
    }
    if (path.includes("/deck/cards/card-e2e") && method === "POST") {
      deckCardIds = ["card-e2e"];
      deckRevision += 1;
      await route.fulfill({ json: deckProjection() });
      return;
    }
    await route.fulfill({ status: 404, json: { error: "unexpected route" } });
  });

  await page.goto("/card-factory");
  await expect(page.getByText("image-e2e-01")).toBeVisible();
  await page.getByRole("button", { name: /image-e2e-01/u }).click();

  await expect(page).toHaveURL(/\/card-candidate-groups$/u);
  await expect(page.getByText("Vier Karten bereit")).toBeVisible();
  await page.getByRole("link", { name: /Vier Karten bereit/u }).click();

  await expect(page).toHaveURL(/\/card-candidate-groups\/initial-group$/u);
  await expect(page.locator(".complete-card-candidate")).toHaveCount(4);
  await expect(
    page.getByText("Eine konzentrierte Figur bei Nacht."),
  ).toBeVisible();
  await expect(page.getByText("precision")).toBeVisible();
  await page
    .locator(".complete-card-candidate")
    .nth(1)
    .getByRole("button", { name: "Diese Karte wählen" })
    .click();

  await expect(page).toHaveURL(/\/card-deck$/u);
  await expect(
    page.getByRole("heading", { name: "Neonwache B" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Zum Deck" }).click();
  await expect(page.locator("[data-deck-capacity]")).toHaveText("1 / 40");

  await page
    .locator("[data-deck-list] .pool-card")
    .getByRole("button", { name: "Entwickeln" })
    .click();
  await expect(page).toHaveURL(/\/card-candidate-groups\/development-group$/u);
  await expect(
    page.getByRole("heading", { name: "Kartenentwicklung vergleichen" }),
  ).toBeVisible();
  await expect(page.locator(".complete-card-candidate")).toHaveCount(4);
  await expect(page.getByText("precision")).toBeVisible();
  await page
    .locator(".complete-card-candidate")
    .first()
    .getByRole("button", { name: "Diese Karte wählen" })
    .click();

  await expect(page).toHaveURL(/\/card-deck$/u);
  await expect(
    page
      .locator("[data-deck-list]")
      .getByRole("heading", { name: "Neonwache Ascended" }),
  ).toBeVisible();
  expect(initialReservations).toBe(1);
  expect(browserErrors).toEqual([]);

  function group(kind) {
    const development = kind === "development";
    const groupId = development ? "development-group" : "initial-group";
    return {
      group_id: groupId,
      revision: development ? 3 : 5,
      kind,
      status: "ready",
      source_card_id: development ? "card-e2e" : null,
      source_card_revision: development ? 1 : null,
      source: {
        image_uid: "image-e2e-01",
        content_hash: "source-hash",
        image_url: "/files/e2e/source.png",
      },
      reference: {
        image_uid: development ? "candidate-image-1" : "image-e2e-01",
        content_hash: development ? "candidate-hash-1" : "source-hash",
        image_url: development
          ? "/files/e2e/card-current.png"
          : "/files/e2e/source.png",
      },
      semantic_profile: semanticProfile(),
      imprint: imprint(),
      failure_category: null,
      actions: {
        can_accept: true,
        can_reject: true,
        can_retry: !development,
      },
      candidates: Array.from({ length: 4 }, (_, slot) =>
        candidate(groupId, slot, development),
      ),
    };
  }

  function candidate(groupId, slot, development) {
    return {
      candidate_id: `${groupId}-candidate-${slot}`,
      slot_index: slot,
      status: "completed",
      failure_category: null,
      image_uid: `${groupId}-image-${slot}`,
      image_url: `/files/e2e/${groupId}-${slot}.png`,
      can_accept: true,
      artifacts: {
        card: cardSpec(slot, development ? 2 : 1),
        presentation: {
          presentation: {
            card_title: development
              ? `Neonwache Ascended ${slot + 1}`
              : `Neonwache ${String.fromCharCode(65 + slot)}`,
            short_description: "Eine aufmerksame Kämpferin.",
            trait_display_names: ["Präzisionsimpuls"],
            flavor_text: "Sie wartet auf den richtigen Moment.",
          },
        },
        visual_recipe: { diagnostics: [] },
      },
    };
  }

  function poolCard() {
    return {
      card_id: "card-e2e",
      revision: cardRevision,
      identity: {
        card_id: "card-e2e",
        source_image_uid: "image-e2e-01",
      },
      card_spec: cardSpec(1, cardRevision),
      semantic_profile: semanticProfile(),
      presentation: {
        presentation: { card_title: acceptedTitle },
      },
      active_image: {
        image_uid: "candidate-image-1",
        content_hash: "candidate-hash-1",
        image_url: "/files/e2e/card-current.png",
        visual_tier: cardRevision,
      },
      actions: { can_develop: true },
    };
  }

  function deckPayload() {
    return { deck: deckProjection(), pool: [poolCard()] };
  }

  function deckProjection() {
    return {
      deck_id: "poc-deck",
      revision: deckRevision,
      capacity: 40,
      remaining_capacity: 40 - deckCardIds.length,
      entries: deckCardIds.map((cardId, position) => ({
        card_id: cardId,
        position,
        card: poolCard(),
      })),
    };
  }
});

function semanticProfile() {
  return {
    summary: "Eine konzentrierte Figur bei Nacht.",
    subjects: ["person"],
    actions: ["observing"],
    mood: ["calm"],
    environment: ["urban"],
    objects: ["neon"],
    signals: [{ concept_key: "focused", strength_milli: 900 }],
  };
}

function imprint() {
  return {
    world_style: "near_future",
    card_class: "striker",
    combat_role: "control",
    trait_lineage: "precision",
  };
}

function cardSpec(slot, tier) {
  return {
    rarity_key: tier === 1 ? "common" : "rare",
    level: tier,
    tier_ordinal: tier,
    stats: {
      attack: 150 + slot * 25,
      defense: 225 - slot * 25,
      stat_profile_key: "balanced",
    },
    traits: [
      {
        mechanic: { key: "marked_strike" },
        canonical_rule_text: "Markiere ein Ziel.",
      },
    ],
  };
}
