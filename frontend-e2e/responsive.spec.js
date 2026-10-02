import { expect, test } from "@playwright/test";

const VIEWPORTS = [
  { width: 3840, height: 2160 },
  { width: 1920, height: 1080 },
  { width: 1366, height: 1024 },
  { width: 1180, height: 820 },
];

for (const viewport of VIEWPORTS) {
  test(`core surfaces remain contained at ${viewport.width}x${viewport.height}`, async ({
    page,
  }) => {
    const errors = [];
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    page.on("pageerror", (error) => errors.push(error.message));
    await page.setViewportSize(viewport);

    await page.goto("/top_pictures?min_n=1");
    await expect(page.locator(".image-card").first()).toBeVisible();
    await expect(page.locator("[data-scope-kind-tab]")).toHaveCount(2);
    await expect(page.locator("[data-scope-uid]")).toHaveCount(1);
    await assertContained(page, viewport.width);

    await page.locator("[data-image-action='select']").first().click();
    await expect(page.getByText("Bild-UID", { exact: true })).toBeVisible();
    for (const heading of [
      "Prompt",
      "Generation",
      "Workflow",
      "Reviews",
      "Curation",
    ]) {
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    }

    await page.goto("/stats?min_n=1");
    await expect(
      page.locator(".analytics-composition-card").first(),
    ).toBeVisible();
    await assertContained(page, viewport.width);

    await page.goto("/playground/generator");
    await expect(
      page.getByRole("heading", { name: "Playground" }),
    ).toBeVisible();
    await expect(
      page.locator(".playground-combination-card").first(),
    ).toBeVisible();
    await assertContained(page, viewport.width);

    await page.goto("/settings");
    await expect(
      page.getByRole("heading", { name: "Allgemein" }),
    ).toBeVisible();
    await assertContained(page, viewport.width);
    expect(errors).toEqual([]);
  });
}

async function assertContained(page, expectedWidth) {
  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    content: document.documentElement.scrollWidth,
    offenders: [...document.querySelectorAll("body *")]
      .map((element) => {
        const rectangle = element.getBoundingClientRect();
        return {
          selector: `${element.tagName}.${String(element.className)}`,
          left: Math.round(rectangle.left),
          right: Math.round(rectangle.right),
          width: Math.round(rectangle.width),
        };
      })
      .filter(
        (element) => element.left < -1 || element.right > window.innerWidth + 1,
      )
      .slice(0, 10),
  }));
  expect(dimensions.viewport).toBe(expectedWidth);
  expect(
    dimensions.content,
    JSON.stringify(dimensions.offenders),
  ).toBeLessThanOrEqual(expectedWidth);
}
