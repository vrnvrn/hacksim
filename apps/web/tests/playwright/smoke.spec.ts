import { test, expect } from "@playwright/test";

// End-to-end smoke. Starts on the hero, follows the example link to the
// live page, opens a ProjectDemoModal, switches to Code, switches to
// Verdict. Mock mode is on (set in playwright.config.ts), so this runs
// without the FastAPI orchestrator.
test("hero to demo modal tab switch", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /run your own hackathon/i }),
  ).toBeVisible();

  // Submit a prompt and verify the route lands on /sim/<id>.
  await page
    .getByPlaceholder(
      "an onchain agents hackathon with five sponsors and a $5k pool",
    )
    .fill("a tiny test hackathon");
  await page.getByRole("button", { name: "Spin up sim" }).click();
  await page.waitForURL(/\/sim\//);

  // Live page: prompt quote is the page header.
  await expect(page.getByText("a tiny test hackathon").first()).toBeVisible({
    timeout: 5000,
  }).catch(async () => {
    // The mock POST route returns the canonical sim id which is wired to the
    // canned prompt in snapshot.json. Fall back to that if our prompt was
    // overwritten.
    await expect(
      page.getByText(
        /onchain agents hackathon with five sponsors/i,
      ),
    ).toBeVisible();
  });

  // Find the first Submissions Try-it button and open the modal.
  const tryButton = page.getByRole("button", { name: /try .* in the demo modal/i }).first();
  await tryButton.click();

  await expect(page.getByRole("tab", { name: "Demo" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Code" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Verdict" })).toBeVisible();

  // Verify the iframe is sandboxed correctly.
  const iframeLocator = page.locator("iframe[title^='Demo of']").first();
  await expect(iframeLocator).toHaveAttribute("sandbox", "allow-scripts");

  // Switch tabs.
  await page.getByRole("tab", { name: "Code" }).click();
  await expect(page.getByRole("tab", { name: "Code" })).toHaveAttribute(
    "data-state",
    "active",
  );

  await page.getByRole("tab", { name: "Verdict" }).click();
  await expect(page.getByRole("tab", { name: "Verdict" })).toHaveAttribute(
    "data-state",
    "active",
  );

  // Close the modal via the close button.
  await page.getByLabel("Close demo modal").click();
});

test("showcase page renders winners and opens a modal", async ({ page }) => {
  await page.goto("/sim/sim_2026-04-28_a1b2c3/showcase");
  await expect(
    page.getByRole("heading", { name: "Showcase" }),
  ).toBeVisible();
  // Three winners across the three judged projects.
  await expect(page.getByText("1st").first()).toBeVisible();
  // Open the first winner's demo modal.
  await page.getByRole("button", { name: /try .* in the demo modal/i }).first().click();
  await expect(page.getByRole("tab", { name: "Demo" })).toBeVisible();
});
