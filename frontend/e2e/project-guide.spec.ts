import { expect, test } from "@playwright/test";
import { ASSISTANT_CONFIG } from "../src/lib/project-guide/config";

/**
 * End-to-end check of the project guide against the real Next.js route
 * handler. CI has no LLM key, so answers come from the extractive path; the
 * retrieval, citations, sources and UI states are all real.
 */
test.describe("project guide", () => {
  test("answers a suggested question with cited sources", async ({ page }) => {
    await page.goto("/");
    const launcher = page.getByRole("button", { name: new RegExp(ASSISTANT_CONFIG.launcherLabel) });
    await expect(launcher).toBeVisible({ timeout: 30_000 });
    await launcher.click();

    const dialog = page.getByRole("dialog", { name: ASSISTANT_CONFIG.title });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(ASSISTANT_CONFIG.greeting)).toBeVisible();

    await dialog.getByRole("button", { name: ASSISTANT_CONFIG.suggestions[0] }).click();
    const answer = dialog.locator(".rka-msg-assistant:not([role=status])").last();
    await expect(answer).toBeVisible({ timeout: 30_000 });
    await expect(answer.locator(".rka-cite").first()).toBeVisible();

    await answer.getByRole("button", { name: /Show \d+ sources?/ }).click();
    const firstSource = answer.locator(".rka-source-list a").first();
    await expect(firstSource).toHaveAttribute("href", /^https:\/\/(github\.com\/HuLaxx|portfolio\.hulax\.uk)/);

    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(launcher).toBeFocused();
  });

  test("declines an off-topic question instead of guessing", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: new RegExp(ASSISTANT_CONFIG.launcherLabel) }).click({ timeout: 30_000 });
    const dialog = page.getByRole("dialog", { name: ASSISTANT_CONFIG.title });
    await dialog.getByRole("textbox").fill("What's the weather in Paris tomorrow?");
    await dialog.getByRole("button", { name: "Send question" }).click();
    await expect(dialog.locator(".rka-msg-assistant").last()).toContainText("couldn't find that", { timeout: 30_000 });
  });

  test("API validates input and reports its index", async ({ request }) => {
    const health = await request.get("/api/project-guide");
    expect(health.ok()).toBeTruthy();
    const info = await health.json();
    expect(info.project).toBe(ASSISTANT_CONFIG.homeProject);
    expect(info.chunks).toBeGreaterThan(400);

    const empty = await request.post("/api/project-guide", { data: { question: "   " } });
    expect(empty.status()).toBe(400);

    const tooLong = await request.post("/api/project-guide", { data: { question: "x".repeat(601) } });
    expect(tooLong.status()).toBe(413);

    const res = await request.post("/api/project-guide", { data: { question: "What did Rahul do at Accenture?" } });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(["llm", "extractive"]).toContain(body.mode);
    expect(body.sources[0].project).toBe("profile");
    expect(body.answer).toMatch(/Accenture/);
  });
});
