import { expect, test } from "@playwright/test";

function collectConsoleErrors(page) {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

test("analytics renders a bounded page and loads the next page lazily", async ({
  page,
}) => {
  const errors = collectConsoleErrors(page);
  await page.goto("/stats?min_n=1");
  const cards = page.locator(".analytics-composition-card");
  await expect(cards.first()).toBeVisible();
  await expect(cards).toHaveCount(24);
  await expect(page.locator(".analytics-image-strip img")).toHaveCount(24);

  await page.locator("[data-analytics-sentinel]").scrollIntoViewIfNeeded();
  await expect(cards).toHaveCount(30);
  await expect(page.locator(".analytics-image-strip img")).toHaveCount(30);
  expect(errors).toEqual([]);
});

test("analytics cards remain contained and hand off without drafting", async ({
  page,
}) => {
  const errors = collectConsoleErrors(page);
  await page.setViewportSize({ width: 1180, height: 820 });
  await page.goto("/param_stats?min_n=1");
  await expect(
    page.getByRole("heading", { name: "Render-Analyse" }),
  ).toBeVisible();
  await expect(page.locator(".analytics-guidance-card").first()).toBeVisible();
  const cardWidths = await page
    .locator(".analytics-guidance-card")
    .evaluateAll((cards) =>
      cards.slice(0, 3).map((card) => card.getBoundingClientRect().width),
    );
  expect(cardWidths).toHaveLength(3);
  expect(new Set(cardWidths.map(Math.round)).size).toBe(1);
  expect(cardWidths[0]).toBeLessThan(400);
  expect(
    await page
      .locator(".analytics-guidance-card")
      .first()
      .evaluate((card) => card.scrollWidth - card.clientWidth),
  ).toBe(0);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(1180);

  const applicableSetup = page
    .locator(".analytics-guidance-card")
    .filter({ hasText: "NetaYume-e2e-1.safetensors" })
    .first();
  await applicableSetup
    .getByRole("button", { name: "Generierungseinstellungen übernehmen" })
    .click();
  await expect(page).toHaveURL(/\/playground\/generator$/);
  await expect(page.getByText("Kein Entwurf")).toBeVisible();

  await page.goto("/param_stats?min_n=1");
  await page.getByRole("button", { name: "Einzelwerte" }).click();
  await page.locator("[data-guidance-parameter='checkpoint']").click();
  const checkpointCard = page
    .locator(".analytics-guidance-card")
    .filter({ hasText: "NetaYume-e2e-1.safetensors" })
    .first();
  await expect(checkpointCard).toBeVisible();
  await checkpointCard.locator("[data-playground-intent='parameter']").click();
  await expect(page).toHaveURL(/\/playground\/generator$/);
  await expect(page.getByText("Kein Entwurf")).toBeVisible();
  expect(errors).toEqual([]);
});

test("analytics overview uses cyclic three-card rows on iPad", async ({
  page,
}) => {
  await page.setViewportSize({ width: 820, height: 1180 });
  await page.goto("/recommendations");
  await expect(
    page.locator(".analytics-overview-section").first(),
  ).toBeVisible();
  await expect(page.locator(".analytics-filters")).toBeHidden();
  const firstRail = page.locator(".analytics-card-rail").first();
  const cards = firstRail.locator(".analytics-overview-card");
  await expect(cards).toHaveCount(8);
  const widths = await cards.evaluateAll((items) =>
    items.slice(0, 3).map((item) => item.getBoundingClientRect().width),
  );
  expect(new Set(widths.map(Math.round)).size).toBe(1);
  await firstRail.getByRole("button", { name: "Vorherige Karten" }).click();
  await expect(firstRail.locator("[data-card-rail-track]")).toHaveAttribute(
    "data-card-rail-index",
    "7",
  );
});
