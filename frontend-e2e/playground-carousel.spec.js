import { expect, test } from "@playwright/test";

test("playground evidence carousels loop with arrows and bounded images", async ({
  page,
}) => {
  await page.route("**/api/v2/playground/top-combinations", async (route) => {
    const response = await route.fetch();
    const payload = await response.json();
    const combinations = payload.characters[0].two_additional_factors;
    combinations[0].best_images = combinations
      .slice(0, 3)
      .map((combination) => combination.best_images[0]);
    await route.fulfill({ response, json: payload });
  });
  await page.goto("/playground");
  await expect(
    page.getByRole("heading", {
      name: "Top-Kombinationen mit 2 Zusatzfaktoren",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Top-Kombinationen mit 3 Zusatzfaktoren",
    }),
  ).toBeVisible();
  const group = page.locator(".playground-character-row").first();
  const track = group.locator("[data-carousel-track]");
  const cards = track.locator(".playground-combination-card");

  await expect(cards.first()).toBeVisible();
  expect(await cards.count()).toBeGreaterThan(1);
  expect(await cards.first().locator("img").count()).toBe(1);
  const imageCounts = await cards.evaluateAll((items) =>
    items.map((item) => Number(item.dataset.imageCount || 0)),
  );
  expect(imageCounts.every((count) => count >= 1 && count <= 3)).toBe(true);
  expect(Math.max(...imageCounts)).toBeGreaterThan(1);
  await expect(track).toHaveAttribute("data-carousel-index", "0");
  const coverSources = await page
    .locator(".playground-combination-card img")
    .evaluateAll((images) => images.map((image) => image.getAttribute("src")));
  expect(new Set(coverSources).size).toBe(coverSources.length);
  expect(
    await track.evaluate((element) => getComputedStyle(element).scrollbarWidth),
  ).toBe("none");

  const multiImageCard = track
    .locator(
      ".playground-combination-card[data-image-count='2'], " +
        ".playground-combination-card[data-image-count='3']",
    )
    .first();
  const evidenceImage = multiImageCard.locator("img");
  const initialSource = await evidenceImage.getAttribute("src");
  await multiImageCard.getByRole("button", { name: "Nächstes Bild" }).click();
  await expect(evidenceImage).not.toHaveAttribute("src", initialSource || "");

  await group.getByRole("button", { name: "Vorherige Kombinationen" }).click();
  await expect(track).toHaveAttribute(
    "data-carousel-index",
    String((await cards.count()) - 1),
  );
  await expect
    .poll(() => track.evaluate((element) => element.scrollLeft))
    .toBeGreaterThan(0);

  await group.getByRole("button", { name: "Nächste Kombinationen" }).click();
  await expect(track).toHaveAttribute("data-carousel-index", "0");
  await expect
    .poll(() => track.evaluate((element) => element.scrollLeft))
    .toBe(0);
});
