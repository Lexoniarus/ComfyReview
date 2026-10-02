import { expect, test } from "@playwright/test";

test("settings persist preferences and an ordered LoRA generation profile", async ({
  page,
}) => {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Allgemein" })).toBeVisible();
  await page.getByLabel("Analytics-Seitengröße").selectOption("12");
  await page.getByRole("button", { name: "Speichern" }).click();
  await expect(page.locator(".settings-status")).toContainText("Gespeichert");

  await page.getByRole("button", { name: "ComfyUI" }).click();
  await page.getByRole("button", { name: "Verbindung testen" }).click();
  await expect(page.locator(".settings-status")).toContainText("Verbunden");
  await expect(page.getByText("character-detail.safetensors")).toBeVisible();

  await page.getByRole("button", { name: "Generierungsprofile" }).click();
  await page.getByLabel("Name").fill("E2E Profil");
  await page.getByRole("button", { name: "LoRA hinzufügen" }).click();
  await page.getByRole("button", { name: "LoRA hinzufügen" }).click();
  await page
    .locator(".settings-lora-row")
    .nth(1)
    .getByRole("button", { name: "↑" })
    .click();
  await page
    .locator(".settings-form")
    .getByRole("button", { name: "Speichern" })
    .click();
  await expect(page.locator(".settings-status")).toContainText("Gespeichert");

  await page.reload();
  await page.getByRole("button", { name: "Generierungsprofile" }).click();
  await page.getByRole("button", { name: "E2E Profil" }).click();
  const loraNames = await page
    .locator(".settings-lora-row select")
    .evaluateAll((elements) => elements.map((element) => element.value));
  expect(loraNames).toEqual([
    "cinematic-light.safetensors",
    "character-detail.safetensors",
  ]);
  expect(errors).toEqual([]);
});
