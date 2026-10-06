import { expect, test } from "@playwright/test";

const VIEWPORTS = [
  { width: 3840, height: 2160 },
  { width: 1920, height: 1080 },
  { width: 1366, height: 1024 },
  { width: 1180, height: 820 },
  { width: 820, height: 1180 },
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
    await expect(page.locator("[data-scope-kind-tab]")).toHaveCount(3);
    await expect(page.locator("[data-scope-uid]")).toHaveCount(1);
    await assertContained(page, viewport.width);
    if ([820, 1180].includes(viewport.width)) {
      await assertThreeColumns(page, ".image-card");
      await assertNaturalImage(page, ".image-card img");
    }

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
    if ([820, 1180].includes(viewport.width)) {
      await assertThreeColumns(page, ".analytics-composition-card");
      await assertNaturalImage(page, ".analytics-composition-card img");
    }

    await page.goto("/playground");
    await expect(
      page.getByRole("heading", { name: "Playground" }),
    ).toBeVisible();
    await expect(
      page.locator(".playground-combination-card").first(),
    ).toBeVisible();
    await assertContained(page, viewport.width);
    if ([820, 1180].includes(viewport.width)) {
      await assertThreeVisibleCarouselCards(page);
      await assertNaturalImage(page, ".playground-combination-card img");
    }

    await page.goto("/playground/generator");
    await expect(page.locator("[data-generation-controls]")).toBeVisible();
    await assertContained(page, viewport.width);

    await page.goto("/settings");
    await expect(
      page.getByRole("heading", { name: "Allgemein" }),
    ).toBeVisible();
    await assertContained(page, viewport.width);
    expect(errors).toEqual([]);
  });
}

test("Top/Worst inspector closes and scrolls as an iPad drawer", async ({
  page,
}) => {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1180, height: 820 });
  await page.goto("/top_pictures?min_n=1");

  const shell = page.locator("[data-v2-surface='top-worst']");
  const firstImage = page.locator("[data-image-action='select']").first();
  const inspector = page.locator("[data-image-inspector]");
  await firstImage.click();
  await expect(shell).toHaveClass(/is-inspector-open/);
  await expect(
    page.getByRole("button", { name: "Bilddetails schließen" }),
  ).toBeVisible();
  await inspector.getByText("Bild-UID", { exact: true }).click();
  await expect(shell).toHaveClass(/is-inspector-open/);

  const scrollState = await inspector.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
    return {
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
      scrollTop: element.scrollTop,
      overflowY: getComputedStyle(element).overflowY,
      overscrollBehavior: getComputedStyle(element).overscrollBehavior,
    };
  });
  expect(scrollState.scrollHeight).toBeGreaterThan(scrollState.clientHeight);
  expect(scrollState.scrollTop).toBeGreaterThan(0);
  expect(scrollState.overflowY).toBe("auto");
  expect(scrollState.overscrollBehavior).toBe("contain");

  await firstImage.click();
  await expect(shell).not.toHaveClass(/is-inspector-open/);
  await firstImage.click();
  await expect(shell).toHaveClass(/is-inspector-open/);
  await page.getByRole("heading", { name: "Top / Worst" }).click();
  await expect(shell).not.toHaveClass(/is-inspector-open/);

  await firstImage.click();
  await page.getByRole("button", { name: "Bilddetails schließen" }).click();
  await expect(shell).not.toHaveClass(/is-inspector-open/);
  expect(errors).toEqual([]);
});

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

async function assertThreeColumns(page, selector) {
  const columns = await page.locator(selector).evaluateAll((elements) => {
    const cards = elements.slice(0, 6).map((element) => {
      const rectangle = element.getBoundingClientRect();
      return { y: Math.round(rectangle.y), width: Math.round(rectangle.width) };
    });
    return {
      count: cards.filter((card) => card.y === cards[0]?.y).length,
      widths: [...new Set(cards.map((card) => card.width))],
    };
  });
  expect(columns.count).toBe(3);
  expect(columns.widths).toHaveLength(1);
}

async function assertThreeVisibleCarouselCards(page) {
  const result = await page
    .locator(".playground-combination-grid")
    .first()
    .evaluate((track) => {
      const trackRectangle = track.getBoundingClientRect();
      const visible = [
        ...track.querySelectorAll(".playground-combination-card"),
      ].filter((card) => {
        const rectangle = card.getBoundingClientRect();
        return (
          rectangle.left >= trackRectangle.left - 1 &&
          rectangle.right <= trackRectangle.right + 1
        );
      });
      return {
        count: visible.length,
        widths: [
          ...new Set(visible.map((card) => card.getBoundingClientRect().width)),
        ],
      };
    });
  expect(result.count).toBe(3);
  expect(result.widths).toHaveLength(1);
}

async function assertNaturalImage(page, selector) {
  const image = await page
    .locator(selector)
    .first()
    .evaluate((element) => {
      const rectangle = element.getBoundingClientRect();
      return {
        naturalRatio: element.naturalWidth / element.naturalHeight,
        renderedRatio: rectangle.width / rectangle.height,
        objectFit: getComputedStyle(element).objectFit,
      };
    });
  expect(image.objectFit).toBe("contain");
  expect(Math.abs(image.naturalRatio - image.renderedRatio)).toBeLessThan(0.01);
}
