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
  await expect(page.getByText("Beobachtete vollständige Setups")).toBeVisible();
  await expect(page.locator(".analytics-render-setup").first()).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(1180);

  await page.getByRole("button", { name: "Checkpoint" }).click();
  const checkpointCard = page.locator(".analytics-parameter-card").first();
  await expect(checkpointCard).toBeVisible();
  await checkpointCard.locator("[data-playground-intent='parameter']").click();
  await expect(page).toHaveURL(/\/playground\/generator\?/);
  await expect(page.getByText("Kein Entwurf")).toBeVisible();
  expect(errors).toEqual([]);
});
