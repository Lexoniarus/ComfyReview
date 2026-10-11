import { expect, test } from "@playwright/test";

test("Card Factory creates, evolves, accepts and develops one prototype session", async ({
  page,
}) => {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  let revision = 1;
  let tier = 1;
  let batch = 0;
  let activeKind = "source";
  let activeVisualTier = 0;
  let operationState = "idle";
  let activeImageUrl = "/files/e2e/image-01.png";
  let candidates = [];

  await page.route("**/api/v2/card-factory/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (path.endsWith("/sources")) {
      await route.fulfill({
        json: {
          total: 1,
          offset: 0,
          limit: 24,
          items: [
            {
              image_uid: "image-e2e-01",
              image_url: "/files/e2e/image-01.png",
            },
          ],
        },
      });
      return;
    }
    if (path.endsWith("/sessions") && request.method() === "POST") {
      await route.fulfill({ status: 201, json: snapshot() });
      return;
    }
    if (path.endsWith("/candidates") && request.method() === "POST") {
      revision += 1;
      batch += 1;
      operationState = "generating";
      candidates = Array.from({ length: 4 }, (_, slot) =>
        candidate(slot, "completed", batch),
      );
      await route.fulfill({ status: 202, json: snapshot() });
      return;
    }
    if (path.endsWith("/accept") && request.method() === "POST") {
      const accepted = candidates.find((item) =>
        path.includes(item.candidate_id),
      );
      revision += 1;
      activeKind = "candidate";
      activeVisualTier = tier;
      activeImageUrl = accepted.image_url;
      operationState = "idle";
      candidates = candidates.map((item) => ({
        ...item,
        status:
          item.candidate_id === accepted.candidate_id
            ? "accepted"
            : item.status,
        can_accept: false,
      }));
      await route.fulfill({ json: snapshot() });
      return;
    }
    if (path.endsWith("/develop") && request.method() === "POST") {
      revision += 1;
      tier += 1;
      operationState = "idle";
      candidates = [];
      await route.fulfill({ json: snapshot() });
      return;
    }
    await route.fulfill({ json: snapshot() });
  });

  await page.goto("/card-factory");
  await expect(page.getByText("image-e2e-01")).toBeVisible();
  await page.getByRole("button", { name: /image-e2e-01/ }).click();
  await expect(page).toHaveURL(/\/card-workshop\/session-e2e$/u);
  await expect(page.getByRole("heading", { name: "Neonwache" })).toBeVisible();

  await page.getByRole("button", { name: "Kandidaten erzeugen" }).click();
  await expect(page.locator(".card-candidate")).toHaveCount(4);
  await page.locator(".card-candidate").nth(1).getByRole("button").click();
  await expect(page.locator(".card-candidate").nth(1)).toHaveAttribute(
    "data-status",
    "accepted",
  );
  await expect(
    page.getByRole("button", { name: "Weiterentwickeln" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Weiterentwickeln" }).click();
  await expect(page.locator("#card-heading")).toHaveText("Rare L2");
  await page.getByRole("button", { name: "Kandidaten erzeugen" }).click();
  await expect(page.locator(".card-candidate")).toHaveCount(4);
  await expect(page.locator(".card-candidate").first()).toHaveAttribute(
    "data-status",
    "completed",
  );
  expect(errors).toEqual([]);

  function snapshot() {
    return {
      session_id: "session-e2e",
      revision,
      operation_state: operationState,
      source: {
        image_uid: "image-e2e-01",
        content_hash: "source-hash",
        image_url: "/files/e2e/image-01.png",
      },
      active_reference: {
        image_uid: activeKind === "source" ? "image-e2e-01" : "candidate-b",
        content_hash: `${activeKind}-hash`,
        kind: activeKind,
        visual_tier: activeVisualTier,
        image_url: activeImageUrl,
      },
      semantic_profile: {
        summary: "Eine konzentrierte Figur bei Nacht.",
        subjects: ["person"],
        actions: ["observing"],
        mood: ["calm"],
        environment: ["urban"],
        objects: ["neon"],
        signals: [{ concept_key: "focused", strength_milli: 900 }],
      },
      imprint: {
        world_style: "near_future",
        card_class: "striker",
        combat_role: "control",
        trait_lineage: "precision",
      },
      card_spec: {
        rarity_key: tier === 1 ? "common" : "rare",
        level: tier,
        tier_ordinal: tier,
        stats: {
          attack: 100 + tier * 50,
          defense: 250 - tier * 25,
          stat_profile_key: "balanced",
        },
        traits: [
          {
            mechanic: { key: "marked_strike" },
            canonical_rule_text: "Markiere ein Ziel.",
          },
        ],
      },
      visual_recipe: {
        positive_atoms: [
          {
            canonical_text: "focused neon lighting",
            weight_milli: 1100,
            required: true,
          },
        ],
        negative_atoms: [
          { canonical_text: "blur", weight_milli: 1000, required: false },
        ],
        diagnostics: [],
      },
      presentation: {
        card_title: "Neonwache",
        short_description: "Eine aufmerksame Kämpferin.",
        trait_display_names: ["Präzisionsimpuls"],
        flavor_text: "Sie wartet auf den richtigen Moment.",
      },
      presentation_status: "complete",
      actions: {
        can_generate: operationState === "idle",
        can_develop:
          operationState === "idle" &&
          activeKind === "candidate" &&
          activeVisualTier === tier,
      },
      candidates,
    };
  }
});

function candidate(slot, status, batch) {
  return {
    candidate_id: `candidate-${batch}-${slot}`,
    session_id: "session-e2e",
    session_revision: batch + 1,
    slot_index: slot,
    tier_ordinal: batch,
    recipe_revision: "visual-prompt-projection-v1",
    recipe_hash: `recipe-${batch}`,
    reference_image_uid: "image-e2e-01",
    reference_content_hash: "source-hash",
    status,
    generation_uid: `generation-${batch}-${slot}`,
    failure_category: null,
    output_image_uid: `candidate-image-${batch}-${slot}`,
    image_url: `/files/e2e/image-${String(slot + 2).padStart(2, "0")}.png`,
    can_accept: status === "completed",
  };
}
