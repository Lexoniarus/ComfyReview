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
  await page.getByRole("button", { name: "Entwurf erstellen" }).click();

  await expect(page.locator("[data-draft-state]")).toHaveText(
    "Katalogrevisionen unverändert",
  );
  await expect(
    page.locator("[data-draft-preview] [data-atom-text]"),
  ).toHaveCount(3);
  await expect(
    page.getByRole("button", { name: "An ComfyUI senden" }),
  ).toBeEnabled();
  await expect(page.getByLabel("Gemeinsamer Seed")).not.toHaveValue("");

  await page.getByRole("button", { name: "An ComfyUI senden" }).click();
  await expect(page.locator("[data-generation-result]")).toContainText(
    "submitted",
  );
});
