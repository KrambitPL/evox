import { expect, test } from "@playwright/test";

test("@partial exposes truthful sponsor health and persists a mission", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("status", { name: /Pioneer/i })).toContainText(/healthy/i);
  await expect(page.getByRole("status", { name: /Senso/i })).toContainText(/healthy/i);
  await expect(page.getByRole("status", { name: /Actian/i })).toContainText(/unavailable/i);

  await page.getByLabel(/objective/i).fill("Resolve a configured EvoAgentX issue");
  await page.getByLabel(/success criteria/i).fill("Return a cited resolution or escalate");
  await page.getByLabel(/hard constraint/i).fill("Do not change immutable policy");
  await page.getByRole("button", { name: /create governed mission/i }).click();

  await expect(page.getByText(/Mission mission-/i)).toBeVisible();
});
