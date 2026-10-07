import { expect, test } from "@playwright/test";

test("unsecured LAN-style origin prepares a server draft and submits it", async ({
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
  await page.getByLabel("Seed-Modus").selectOption("random");
  await stateSaved;
  await page.reload();
  await expect(page.getByLabel("Seed-Modus")).toHaveValue("random");
  await expect(page.getByLabel("Outfit: Modus")).toHaveValue("off");
  await expect(page.locator(".settings-lora-row")).toHaveCount(1);
  await expect(page.getByLabel("LoRA")).toHaveValue(
    "character-detail.safetensors",
  );
  await expect(page.getByLabel("Model")).toHaveValue("0.8");
  await expect(page.getByLabel("CLIP")).toHaveValue("0.65");
  await page.getByRole("button", { name: "Entwurf erstellen" }).click();

  await expect(page.locator("[data-draft-state]")).toHaveText(
    "Katalogrevisionen unverändert",
  );
  await expect(
    page.locator("[data-draft-preview] [data-atom-text]"),
  ).toHaveCount(5);
  const atomValues = await page
    .locator("[data-draft-preview] [data-atom-text]")
    .evaluateAll((elements) => elements.map((element) => element.value));
  expect(atomValues.filter((value) => value === "detail trigger")).toHaveLength(
    1,
  );
  expect(atomValues).toEqual(
    expect.arrayContaining(["bad anatomy", "low quality"]),
  );
  await expect(
    page.getByRole("button", { name: "An ComfyUI senden" }),
  ).toBeEnabled();
  await expect(page.getByLabel("Gemeinsamer Seed")).not.toHaveValue("");

  await page.getByRole("button", { name: "An ComfyUI senden" }).click();
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
