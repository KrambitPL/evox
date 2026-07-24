import { expect, test } from "@playwright/test";

test("keeps all workflow controls usable on a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");

  await expect(page.getByRole("navigation", { name: /owner workflow/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /create mission/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /rollback release/i })).toBeVisible();
});

test("fails closed when the designated real sponsor configuration is unavailable", async ({ page }) => {
  const unavailableBaseURL = process.env.EVOX_E2E_FAIL_CLOSED_BASE_URL;
  const unavailableSponsor = process.env.EVOX_E2E_UNAVAILABLE_SPONSOR;
  if (!unavailableBaseURL || !unavailableSponsor) {
    throw new Error(
      "EVOX_E2E_FAIL_CLOSED_BASE_URL and EVOX_E2E_UNAVAILABLE_SPONSOR are required for a real unavailable-sponsor environment.",
    );
  }

  await page.goto(new URL("/", unavailableBaseURL).toString());

  const sponsor = page.getByRole("status", { name: new RegExp(unavailableSponsor, "i") });
  await expect(sponsor).toBeVisible();
  await expect(sponsor).toContainText(/unavailable|not configured|failed/i);
  await expect(page.getByRole("button", { name: /create mission/i })).toBeDisabled();
  await expect(page.getByRole("alert")).toContainText(new RegExp(unavailableSponsor, "i"));
});
