import { test, expect } from "@playwright/test";

// Landing page: the entry point before any auth. Hero CTA and sign-in button are
// statically prerendered, so this runs without a backend.
test.describe("Landing", () => {
  test("shows hero, primary CTA and navbar Try Demo button", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("link", { name: "Upload your resume" })).toBeVisible();
    // Navbar button text is exactly "Try Demo".
    await expect(page.getByRole("button", { name: "Try Demo" })).toBeVisible();
  });

  test("hero CTA navigates to the upload flow", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Upload your resume" }).click();
    await expect(page).toHaveURL(/\/upload/);
    await expect(page.getByRole("heading", { name: "Upload your resume" })).toBeVisible();
  });

  test("login page links to signup and shows Keycloak entry point", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("link", { name: /create an account/i })).toHaveAttribute(
      "href",
      "/signup",
    );
    await expect(page.getByRole("button", { name: /continue with keycloak/i })).toBeVisible();
  });

  test("signup page shows a real email/password form", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.getByRole("heading", { name: /create your account/i })).toBeVisible();
    // Exact labels (there are two password inputs: Password + Confirm).
    await expect(page.getByLabel("Email")).toBeVisible();
    // Exact match — "Password" substring would also hit "Confirm password".
    await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Confirm password")).toBeVisible();
  });
});
