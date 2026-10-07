import { expect, test } from "@playwright/test";

const VIEWPORTS = [
  { width: 3840, height: 2160 },
  { width: 1920, height: 1080 },
  { width: 1080, height: 810 },
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
    await expect(page.locator("[data-scope-kind-tab]")).toHaveCount(4);
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

test("Playground uses desktop inspector, laptop drawer and tablet tabs", async ({
  page,
}) => {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  for (const viewport of [
    { width: 1920, height: 1080, mode: "desktop" },
    { width: 1180, height: 820, mode: "drawer" },
    { width: 1080, height: 810, mode: "tabs" },
    { width: 820, height: 1180, mode: "tabs" },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/playground/generator");
    for (const label of [
      "Outfit: Modus",
      "Pose: Modus",
      "Ausdruck: Modus",
      "Licht: Modus",
      "Modifier: Modus",
    ]) {
      await page.getByLabel(label).selectOption("off");
    }
    await page.getByLabel("Anzahl Varianten").fill("4");
    await page.getByRole("button", { name: "Varianten vorbereiten" }).click();
    await expect(page.locator(".variant-card")).toHaveCount(4);
    await assertContained(page, viewport.width);

    const board = page.locator("[data-variant-region='board']");
    const inspector = page.locator("[data-variant-region='inspector']");
    const viewSwitcher = page.locator(".variant-view-switcher");
    if (viewport.mode === "desktop") {
      await expect(board).toBeVisible();
      await expect(inspector).toBeVisible();
      await expect(viewSwitcher).toBeHidden();
    } else {
      await expect(board).toBeVisible();
      await expect(inspector).toBeHidden();
      await page
        .getByRole("button", { name: "Prüfen & bearbeiten" })
        .nth(1)
        .click();
      await expect(inspector).toBeVisible();
      if (viewport.mode === "drawer") {
        await expect(viewSwitcher).toBeHidden();
        await page
          .getByRole("button", { name: "Inspector schließen" })
          .first()
          .click();
        await expect(inspector).toBeHidden();
        await expect(board).toBeVisible();
      } else {
        await expect(viewSwitcher).toBeVisible();
        await expect(board).toBeHidden();
        await page.getByRole("tab", { name: "Karten" }).click();
        await expect(board).toBeVisible();
        await expect(inspector).toBeHidden();
      }
    }

    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await assertActionBarDoesNotCoverContent(page);
    await assertContained(page, viewport.width);
  }
  expect(errors).toEqual([]);
});

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
  await page.getByRole("button", { name: "Bereiche", exact: true }).click();
  await expect(shell).toHaveClass(/is-scope-open/);
  await page.getByRole("button", { name: "Bereiche schließen" }).click();
  await expect(shell).not.toHaveClass(/is-scope-open/);
  await page.getByRole("button", { name: "Bereiche", exact: true }).click();
  await page.mouse.click(700, 180);
  await expect(shell).not.toHaveClass(/is-scope-open/);

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

test("historical image handoff restores archived scopes and LoRA", async ({
  page,
}) => {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1180, height: 820 });
  await page.goto("/top_pictures?min_n=1");

  const card = page.locator(".image-card").filter({
    has: page.locator(
      '[data-image-action="select"][data-image-uid="image-e2e-01"]',
    ),
  });
  await expect(card).toContainText("LoRA · character-detail.safetensors");
  await card.getByRole("button", { name: "Im Generator verwenden" }).click();
  await card.getByRole("button", { name: "Prompt & LoRAs übernehmen" }).click();

  await expect(page).toHaveURL(/\/playground\/generator$/);
  const sceneRow = page.locator('.prompt-mode-row[data-kind="scene"]');
  await expect(sceneRow.locator("select").first()).toHaveValue("fixed");
  await expect(sceneRow.locator("select").nth(1)).toHaveValue(
    "component-scene-01",
  );
  await expect(sceneRow).toContainText("Testszene 01 · Archiv");
  await expect(sceneRow.locator("select").nth(2)).toHaveValue("historical");
  await expect(sceneRow.locator("select").nth(2)).toContainText(
    "Historisch · R1",
  );
  await expect(sceneRow.locator("[data-atom-text]").first()).toHaveValue(
    "test scene 01",
  );
  for (const kind of ["outfit", "pose"]) {
    await expect(
      page.locator(`.prompt-mode-row[data-kind="${kind}"] select`).first(),
    ).toHaveValue("fixed");
  }
  for (const kind of ["expression", "lighting", "modifier"]) {
    await expect(
      page.locator(`.prompt-mode-row[data-kind="${kind}"] select`).first(),
    ).toHaveValue("off");
  }
  await expect(page.locator(".prompt-lora-layer")).toContainText(
    "Character Detail",
  );
  await page.getByLabel("Anzahl Varianten").fill("1");
  await page.getByLabel("Anzahl Varianten").dispatchEvent("change");
  await page.getByRole("button", { name: "Varianten vorbereiten" }).click();
  await expect(page.locator(".variant-card")).toHaveCount(1);
  const generationRequest = page.waitForRequest(
    (request) =>
      request.method() === "POST" &&
      request.url().endsWith("/api/v2/generations/batch"),
  );
  await page.getByRole("button", { name: "Auswahl generieren" }).click();
  const submittedPayload = (await generationRequest).postDataJSON();
  expect(submittedPayload.variants).toHaveLength(1);
  for (const submittedVariant of submittedPayload.variants) {
    expect(submittedVariant.source_image_uid).toBe("image-e2e-01");
    expect(submittedVariant.prompt_groups).toEqual([]);
    expect(submittedVariant.prompt_selections).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          kind: "scene",
          revision_uid: "revision-component-scene-01",
        }),
      ]),
    );
    expect(
      submittedVariant.positive_atoms.filter(
        (atom) => atom.text === "detail trigger",
      ),
    ).toHaveLength(1);
  }
  await expect(page.locator("[data-generation-result]")).toContainText(
    "submitted",
  );
  await expect(page.locator("[data-generation-result]")).not.toContainText(
    "Fehler:",
  );
  const submission = await page.evaluate(async () =>
    fetch("/_e2e/submissions").then((response) => response.json()),
  );
  expect(submission.loras).toEqual([
    ["character-detail.safetensors", 800, 600],
  ]);
  const loraNode = submission.prompt.prompt["cr:lora:000"];
  expect(loraNode.inputs.lora_name).toBe("character-detail.safetensors");
  expect(loraNode.inputs.strength_model).toBe(0.8);
  expect(loraNode.inputs.strength_clip).toBe(0.6);
  expect(
    JSON.stringify(submission.prompt.prompt).match(/detail trigger/g),
  ).toHaveLength(1);
  expect(JSON.stringify(submission.prompt.prompt)).toContain("test scene 01");
  expect(JSON.stringify(submission.prompt.prompt)).not.toContain(
    "current test scene 01",
  );
  expect(errors).toEqual([]);
});

test("content settings allow excluding Standard but never every level", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1180, height: 820 });
  await page.goto("/settings");
  await page.getByRole("button", { name: "Inhaltsstufen" }).click();
  const standard = page.getByLabel("Standard", { exact: true });
  const sexy = page.getByLabel("Sexy", { exact: true });
  await expect(standard).toBeChecked();
  await expect(standard).toBeDisabled();
  await sexy.check();
  await expect(standard).toBeEnabled();
  await standard.uncheck();
  await expect(sexy).toBeDisabled();
  await page.getByRole("button", { name: "Speichern" }).click();
  await expect(page.locator("[data-settings-status]")).toHaveText(
    "Gespeichert.",
  );

  await standard.check();
  await sexy.uncheck();
  await page.getByRole("button", { name: "Speichern" }).click();
  await expect(page.locator("[data-settings-status]")).toHaveText(
    "Gespeichert.",
  );
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

async function assertActionBarDoesNotCoverContent(page) {
  const layout = await page.evaluate(() => {
    const actionBar = document.querySelector(".playground-variant-actions");
    const visibleRegion = [
      ...document.querySelectorAll("[data-variant-region]"),
    ]
      .filter((element) => {
        const style = getComputedStyle(element);
        return style.display !== "none" && style.visibility !== "hidden";
      })
      .at(-1);
    if (
      !(actionBar instanceof HTMLElement) ||
      !(visibleRegion instanceof HTMLElement)
    )
      return null;
    const actionRectangle = actionBar.getBoundingClientRect();
    const regionRectangle = visibleRegion.getBoundingClientRect();
    return {
      actionTop: Math.round(actionRectangle.top),
      regionBottom: Math.round(regionRectangle.bottom),
    };
  });
  expect(layout).not.toBeNull();
  expect(layout.regionBottom).toBeLessThanOrEqual(layout.actionTop);
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
