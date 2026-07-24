import { expect, test } from "@playwright/test";

test("provides keyboard-operable semantic navigation through the owner states", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("banner")).toBeVisible();
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByRole("navigation", { name: /owner workflow/i })).toBeVisible();

  const workflow = page.getByRole("navigation", { name: /owner workflow/i });
  const steps = workflow.getByRole("link");
  await expect(steps).toHaveCount(5);

  await steps.first().focus();
  for (const expectedName of ["Define", "System", "Trial", "Gate", "Operate"]) {
    await expect(page.locator(":focus")).toHaveAccessibleName(expectedName);
    await page.keyboard.press("Tab");
  }
});

test("announces form validation errors without requiring pointer input", async ({ page }) => {
  await page.goto("/");

  const createMission = page.getByRole("button", { name: /create mission/i });
  await createMission.focus();
  await page.keyboard.press("Enter");

  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(/objective|required/i);
});
