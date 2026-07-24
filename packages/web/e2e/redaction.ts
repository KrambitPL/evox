import type { Locator, Page } from "@playwright/test";

/**
 * Failure artefacts must not expose credentials or free-text feedback. The cockpit
 * must mark those fields with these stable accessible labels.
 */
export async function captureRedactedFailure(page: Page, name: string): Promise<void> {
  const masks: Locator[] = [
    page.getByLabel(/access token|api key|secret/i),
    page.getByLabel(/feedback/i),
  ];

  await page.screenshot({
    path: `test-results/${name}.png`,
    fullPage: true,
    mask: masks,
    maskColor: "#000000",
  });
}
