import { test, expect } from "@playwright/test";

// Demo flow: the login-form "Try the demo" button persists a demo token via
// loginDemo() AND navigates to /dashboard. This exercises P3.1 (auth entry point
// + demo fallback) and P3.2 (dashboard renders live data with demo fixtures when
// the backend is unreachable). Note: navbar "Try Demo" only sets a token (no nav),
// so we target the login-form button whose text is exactly "Try the demo".
test.describe("Demo flow", () => {
  test(
    "login Try the demo -> dashboard shows demo resumes + hides upload-first CTA",
    async ({ page }) => {
      await page.goto("/login");
      // Login-form button persists a token and pushes to /dashboard.
      await page.getByRole("button", { name: "Try the demo" }).click();

      await expect(page).toHaveURL(/\/dashboard/);
      await expect(page.getByRole("heading", { name: "My Resumes" })).toBeVisible();
      // Demo fixtures render as cards, each with a "Review" link.
      await expect(page.getByRole("link", { name: /review/i }).first()).toBeVisible();
      // Upload-first CTA hidden because demo resumes already exist.
      await expect(page.getByRole("heading", { name: /upload your first resume/i })).toBeHidden();
    },
  );

  test(
    "dashboard upload CTA navigates to /upload",
    async ({ page }) => {
      await page.goto("/login");
      // Login-form button persists a token and pushes to /dashboard.
      await page.getByRole("button", { name: "Try the demo" }).click();

      const uploadLink = page.getByRole("link", { name: /upload new/i });
      await expect(uploadLink).toBeVisible();
      await uploadLink.click();

      await expect(page).toHaveURL(/\/upload/);
      await expect(page.getByRole("heading", { name: "Upload your resume" })).toBeVisible();
    },
  );

  test(
    "upload posts to backend (unreachable) — no hang, button re-enables",
    async ({ page }) => {
      await page.goto("/login");
      // Login-form button persists a token and pushes to /dashboard.
      await page.getByRole("button", { name: "Try the demo" }).click();

      const uploadLink = page.getByRole("link", { name: /upload new/i });
      await expect(uploadLink).toBeVisible();
      await uploadLink.click();

      // The backend is unreachable, so the POST never gets a response. Waiting
      // on waitForResponse would hang; instead capture requests as they fire so
      // we can assert the live POST was sent without blocking on a reply.
      const uploadRequests = [];
      page.on("request", (req) => {
        if (req.url().includes("/api/v1/resume/upload") && req.method() === "POST") {
          uploadRequests.push(req);
        }
      });

      const analyzeBtn = page.getByRole("button", { name: /analyze resume/i });
      // No file selected -> disabled. Button is a native <button>, so this is the
      // real `disabled` attribute (not aria-disabled).
      await expect(analyzeBtn).toBeDisabled();

      // Select a file via the hidden <input type="file"> so submit() runs. The
      // mimeType must be a supported one or onFile rejects it as unsupported.
      const input = page.locator('input[type="file"]').first();
      await input.setInputFiles({ name: "sample.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 test") });

      // File selected -> button enables; click it to fire the real POST.
      await expect(analyzeBtn).toBeEnabled();

      // Clicking analyze fires the upload POST then rejects (backend unreachable);
      // the catch handler surfaces an error and re-enables the button.
      await analyzeBtn.click();

      // The upload POST was actually sent (proves the live path fires end-to-end).
      await expect.poll(() => uploadRequests.length, { timeout: 10_000 }).toBeGreaterThan(0);

      // Backend unreachable -> upload fails and an error message is shown.
      const errEl = page.locator('p.text-rose-400').first();
      await expect(errEl).toBeVisible();
      await expect(errEl).toHaveText(/.+/);

      // File still selected -> button re-enables after the failed attempt is caught.
      await expect(analyzeBtn).toBeEnabled();
    },
  );

  test(
    "logout clears demo token and returns to landing",
    async ({ page }) => {
      await page.goto("/login");
      // Login-form button persists a token and pushes to /dashboard.
      await page.getByRole("button", { name: "Try the demo" }).click();

      // Navbar shows logout when authenticated.
      await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
      await page.getByRole("button", { name: "Log out" }).click();

      // After logout the navbar should show Try Demo again (token cleared).
      await expect(page.getByRole("button", { name: "Try Demo" })).toBeVisible();
    },
  );
});
