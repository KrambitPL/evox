import { expect, test, type Locator } from "@playwright/test";

import { captureRedactedFailure } from "./redaction";

const healthChecks = ["Pioneer", "Senso", "Actian", "Band", "Guild.ai", "Replay.io"];

async function expectQueuedJobToComplete(
  status: Locator,
): Promise<void> {
  await expect(status).toBeVisible();
  await expect.poll(() => status.innerText(), { timeout: 60_000 }).toMatch(/succeeded|complete/i);
}

test.describe("owner journey", () => {
  test("supports the Define to Operate lifecycle with an explicit rollback", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: /define/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /system/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /trial/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /gate/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /operate/i })).toBeVisible();

    for (const integration of healthChecks) {
      await expect(page.getByRole("status", { name: new RegExp(integration, "i") })).toBeVisible();
    }

    await page.getByLabel(/objective/i).fill("Resolve the configured EvoAgentX issue");
    await page.getByLabel(/success criteria/i).fill("Return a cited resolution or escalate");
    await page.getByLabel(/hard constraint/i).fill("Do not change immutable policy");
    await page.getByRole("button", { name: /create mission/i }).click();
    await expect(page.getByRole("status", { name: /mission.*created/i })).toBeVisible();

    await page.getByRole("button", { name: /forge system/i }).click();
    await expectQueuedJobToComplete(page.getByRole("status", { name: /forge/i }));

    await page.getByRole("button", { name: /run trial/i }).click();
    await expectQueuedJobToComplete(page.getByRole("status", { name: /trial/i }));

    await page.getByRole("button", { name: /evaluate candidate/i }).click();
    await expectQueuedJobToComplete(page.getByRole("status", { name: /evaluation/i }));

    await page.getByRole("button", { name: /promote candidate/i }).click();
    await expectQueuedJobToComplete(page.getByRole("status", { name: /promotion/i }));

    await page.getByRole("button", { name: /rollback release/i }).click();
    await expectQueuedJobToComplete(page.getByRole("status", { name: /rollback/i }));

    await captureRedactedFailure(page, "owner-journey");
  });
});
