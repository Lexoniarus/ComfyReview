import { expect, test } from "@playwright/test";

test("unsecured LAN-style origin prepares, reviews and submits variant batches", async ({
  page,
}) => {
  await page.goto("http://comfyreview.test:8015/playground/generator");
  expect(await page.evaluate(() => window.isSecureContext)).toBe(false);
  await expect(
    page.getByRole("option", { name: "Basic Underwear Set" }),
  ).toHaveCount(0);

  const promptReference = page.locator(".prompt-reference-image").first();
  await expect(promptReference).toBeVisible();
  await promptReference.click();
  await expect(page.locator("[data-image-viewer]")).toHaveAttribute("open", "");
  await page.getByRole("button", { name: "Bildansicht schließen" }).click();

  await page.locator(".playground-guidance > summary").click();
  await expect(
    page.getByRole("button", { name: "Gesamtsetup übernehmen" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Gesamtsetup übernehmen" }).click();
  await page.getByRole("radio", { name: "Einzelwerte" }).check();
  await expect(
    page.locator("[data-guidance-action='parameter']").first(),
  ).toBeEnabled();
  await page.locator("[data-guidance-action='parameter']").first().click();
  await page.getByRole("radio", { name: "Rechnerisch" }).check();
  await page.getByRole("radio", { name: "Gesamtsetup" }).check();
  await expect(
    page.getByRole("button", { name: "Gesamtsetup übernehmen" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Gesamtsetup übernehmen" }).click();
  await page.getByRole("radio", { name: "Einzelwerte" }).check();
  await expect(
    page.locator("[data-guidance-action='parameter']").first(),
  ).toBeEnabled();
  await page.locator("[data-guidance-action='parameter']").first().click();

  for (const label of [
    "Outfit: Modus",
    "Pose: Modus",
    "Ausdruck: Modus",
    "Licht: Modus",
    "Modifier: Modus",
  ]) {
    await page.getByLabel(label).selectOption("off");
  }
  await page.getByRole("button", { name: "LoRA hinzufügen" }).click();
  await expect(page.locator(".settings-lora-row")).toHaveCount(1);
  await expect(page.getByLabel("LoRA")).toHaveValue(
    "character-detail.safetensors",
  );
  await page.getByLabel("Model").fill("0.8");
  await page.getByLabel("CLIP").fill("0.65");
  const stateSaved = page.waitForResponse(
    (response) =>
      response.request().method() === "PUT" &&
      response.url().endsWith("/api/v2/playground/generator-state") &&
      response.ok(),
  );
  await page.locator(".sampler-variation > summary").click();
  await page.getByLabel("Seed variieren").selectOption("random");
  await stateSaved;
  const variantCountSaved = page.waitForResponse(
    (response) =>
      response.request().method() === "PUT" &&
      response.url().endsWith("/api/v2/playground/generator-state") &&
      response.ok(),
  );
  await page.getByLabel("Anzahl Varianten").fill("4");
  await page.getByLabel("Anzahl Varianten").dispatchEvent("change");
  await variantCountSaved;
  await page.reload();
  await page.locator(".sampler-variation > summary").click();
  await expect(page.getByLabel("Seed variieren")).toHaveValue("random");
  await expect(page.getByLabel("Anzahl Varianten")).toHaveValue("4");
  await expect(page.getByLabel("Outfit: Modus")).toHaveValue("off");
  await expect(page.locator(".settings-lora-row")).toHaveCount(1);
  await expect(page.getByLabel("LoRA")).toHaveValue(
    "character-detail.safetensors",
  );
  await expect(page.getByLabel("Model")).toHaveValue("0.8");
  await expect(page.getByLabel("CLIP")).toHaveValue("0.65");
  await page.getByRole("button", { name: "Varianten vorbereiten" }).click();

  await expect(page.locator("[data-variant-state]")).toHaveText(
    "Katalogrevisionen unverändert",
  );
  await expect(page.locator(".variant-card")).toHaveCount(4);
  expect(
    await page.locator("[data-variant-inspector] [data-atom-text]").count(),
  ).toBeGreaterThan(0);
  const atomValues = await page
    .locator("[data-variant-inspector] [data-atom-text]")
    .evaluateAll((elements) => elements.map((element) => element.value));
  expect(atomValues.filter((value) => value === "detail trigger")).toHaveLength(
    1,
  );
  expect(atomValues).toEqual(
    expect.arrayContaining(["bad anatomy", "low quality"]),
  );
  await expect(
    page.getByRole("button", { name: "Auswahl generieren" }),
  ).toBeEnabled();
  await expect(page.getByLabel("Bild-Seed")).not.toHaveValue("");

  await page.getByRole("tab", { name: /Setup/ }).click();
  await page.getByLabel("Denoise").fill("0.9");
  await page.getByLabel("Denoise").dispatchEvent("change");
  await page.getByRole("tab", { name: /Varianten/ }).click();
  await expect(page.getByText("Das Setup wurde geändert")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Auswahl generieren" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Varianten aktualisieren" }).click();
  await expect(
    page.getByRole("button", { name: "Auswahl generieren" }),
  ).toBeEnabled();

  const generationRequest = page.waitForRequest(
    (request) =>
      request.method() === "POST" &&
      request.url().endsWith("/api/v2/generations/batch"),
  );
  await page.getByRole("button", { name: "Auswahl generieren" }).click();
  const submittedPayload = (await generationRequest).postDataJSON();
  expect(submittedPayload.variants).toHaveLength(4);
  expect(submittedPayload.variants[0].component_uids).toBeUndefined();
  expect(submittedPayload.variants[0].sampler.batch_runs).toBe(1);
  expect(submittedPayload.variants[0].prompt_selections).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        kind: "character",
        component_uid: expect.any(String),
        revision_uid: expect.any(String),
      }),
    ]),
  );
  await expect(page.locator("[data-generation-result]")).toContainText(
    "submitted",
  );
  const submission = await page.evaluate(async () =>
    fetch("/_e2e/submissions").then((response) => response.json()),
  );
  expect(submission.loras).toEqual([
    ["character-detail.safetensors", 800, 650],
  ]);
  const loraNode = submission.prompt.prompt["cr:lora:000"];
  expect(loraNode.inputs.lora_name).toBe("character-detail.safetensors");
  expect(loraNode.inputs.strength_model).toBe(0.8);
  expect(loraNode.inputs.strength_clip).toBe(0.65);
  expect(
    JSON.stringify(submission.prompt.prompt).match(/detail trigger/g),
  ).toHaveLength(1);
});
