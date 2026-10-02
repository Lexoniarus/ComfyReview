import { expect, test } from "@playwright/test";

test("playground evidence carousels loop with arrows and bounded images", async ({
  page,
}) => {
  await page.goto("/playground/generator");
  const group = page.locator(".playground-combination-group").first();
  const track = group.locator("[data-carousel-track]");
  const cards = track.locator(".playground-combination-card");

  await expect(cards.first()).toBeVisible();
  expect(await cards.count()).toBeGreaterThan(1);
  expect(await cards.first().locator("img").count()).toBeLessThanOrEqual(3);
  await expect(track).toHaveAttribute("data-carousel-index", "0");
  expect(
    await track.evaluate((element) => getComputedStyle(element).scrollbarWidth),
  ).toBe("none");

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
