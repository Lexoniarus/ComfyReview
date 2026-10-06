import { expect, test } from "@playwright/test";

test("settings persist preferences and expose LoRA catalog status without profiles", async ({
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
  await expect(page.getByText("example-upscaler.pth")).toBeVisible();

  await page.getByRole("button", { name: "Inhaltsstufen" }).click();
  await expect(
    page.getByRole("heading", { name: "LoRA-Status" }),
  ).toBeVisible();
  await expect(page.getByText("character-detail.safetensors")).toBeVisible();
  await expect(page.getByText("cinematic-light.safetensors")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "LoRA-Katalog öffnen" }),
  ).toHaveAttribute("href", "/catalog");
  await expect(
    page.getByRole("button", { name: "Stufe speichern" }),
  ).toHaveCount(0);

  await expect(
    page.getByRole("button", { name: "Generierungsprofile" }),
  ).toHaveCount(0);

  await page.reload();
  await expect(page.getByLabel("Analytics-Seitengröße")).toHaveValue("12");
  await page.getByRole("button", { name: "Inhaltsstufen" }).click();
  await expect(
    page.locator(".settings-lora-row", {
      hasText: "cinematic-light.safetensors",
    }),
  ).toContainText("Nicht eingestuft");
  expect(errors).toEqual([]);
});
