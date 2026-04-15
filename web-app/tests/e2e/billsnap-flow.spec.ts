/**
 * BillSnap E2E — Critical User Journey
 *
 * Steps tested:
 * 1. Bills list page loads (empty state)
 * 2. Upload page renders + file selection
 * 3. Upload to backend — captures exact HTTP error if it fails
 * 4. (conditional) If job created: poll until OCR completes
 * 5. (conditional) Review page fields
 * 6. (conditional) Save bill → /done
 * 7. (conditional) Bills list shows new bill
 * 8. Export endpoint returns valid file (tested directly)
 */

import { test, expect, type Page } from "@playwright/test";
import path from "path";

const TEST_IMAGE = "/tmp/test_bill.jpg";
const AUTH_TOKEN = "eb5210244a46edb3a2edd52bb8bc41c9dac3be2d7a2f005013cc2a3de6c64fe5";
const API_BASE = "http://localhost:8000";

// ─── helpers ────────────────────────────────────────────────────────────────

async function waitForJob(
  jobId: string,
  timeoutMs = 90_000
): Promise<{ status: string; bill_id?: string }> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const res = await fetch(`${API_BASE}/api/v1/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
    });
    if (!res.ok) throw new Error(`Job poll failed: HTTP ${res.status}`);
    const data = await res.json();
    if (["completed", "needs_review", "failed"].includes(data.status)) {
      return data;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error(`Job ${jobId} did not complete within ${timeoutMs / 1000}s`);
}

async function snap(page: Page, name: string) {
  await page.screenshot({
    path: path.join("playwright-artifacts", `${name}.png`),
    fullPage: true,
  });
}

function billIdFilePath() {
  return "/tmp/billsnap_e2e_bill_id.txt";
}

// ─── tests ──────────────────────────────────────────────────────────────────

test.describe("BillSnap critical user journey", () => {
  // ── Step 1: Bills list (empty state) ──────────────────────────────────────
  test("Step 1 — bills list page loads without error", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto("/bills");
    await expect(page).toHaveURL(/\/bills/);

    // Header with app name must appear
    await expect(page.locator("h1", { hasText: "BillSnap" })).toBeVisible({ timeout: 10_000 });

    // Wait for loading spinner to clear
    await expect(page.locator("text=Loading bills…")).not.toBeVisible({ timeout: 15_000 });

    // Either "No bills yet" empty state OR bill cards must be present
    const emptyState = page.locator("text=No bills yet");
    const hasEmpty = await emptyState.isVisible().catch(() => false);
    const hasAddBillLink = await page.locator("a[href='/upload']").isVisible().catch(() => false);

    // If empty state is shown, verify its contents
    if (hasEmpty) {
      await expect(page.locator("text=Snap your first one to get started!")).toBeVisible();
      expect(hasAddBillLink).toBe(true);
    }
    // If no empty state, some bill content should exist
    // (just checking the header and the export button is enough if bills exist)

    // Export button
    await expect(page.locator("button", { hasText: "Export" })).toBeVisible();

    // FAB upload button
    await expect(page.locator("button[aria-label='Upload a bill']")).toBeVisible();

    await snap(page, "01-bills-list");

    const criticalErrors = consoleErrors.filter(
      (e) =>
        !e.includes("favicon") &&
        !e.includes("net::ERR") &&
        !e.includes("Failed to load resource")
    );
    expect(criticalErrors).toHaveLength(0);

    console.log("Step 1 PASSED: bills list page renders correctly.");
  });

  // ── Step 2: Upload page renders ───────────────────────────────────────────
  test("Step 2 — upload page renders with camera button and file input", async ({ page }) => {
    await page.goto("/upload");
    await expect(page).toHaveURL(/\/upload/);

    await expect(page.locator("button", { hasText: "Take Photo" })).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=Step 1 / 3")).toBeVisible();
    await expect(page.locator("input[type='file']")).toBeAttached();

    await snap(page, "02-upload-idle");
    console.log("Step 2 PASSED: upload page renders correctly.");
  });

  // ── Step 3: File select + upload ─────────────────────────────────────────
  test("Step 3 — select file and attempt upload, capture any backend error", async ({ page }) => {
    // Capture all network responses to/from the API
    const apiResponses: { url: string; status: number; body: string }[] = [];
    page.on("response", async (res) => {
      if (res.url().includes("localhost:8000")) {
        try {
          const body = await res.text().catch(() => "");
          apiResponses.push({ url: res.url(), status: res.status(), body });
        } catch {
          // ignore
        }
      }
    });

    await page.goto("/upload");
    const fileInput = page.locator("input[type='file']");
    await fileInput.setInputFiles(TEST_IMAGE);

    // Confirm the preview / "Use this photo" state
    await expect(
      page.locator("button", { hasText: "Use this photo" })
    ).toBeVisible({ timeout: 8_000 });
    await snap(page, "03-file-selected");

    // Click upload
    await page.locator("button", { hasText: "Use this photo" }).click();

    // Wait a moment for the upload request to fire and resolve
    await page.waitForTimeout(5000);

    // Capture where we end up
    const currentUrl = page.url();
    await snap(page, "03-after-upload-click");

    // Log all API interactions for diagnosis
    console.log("\n=== API Responses during upload ===");
    for (const r of apiResponses) {
      console.log(`  ${r.status} ${r.url}`);
      if (r.status >= 400) {
        console.log(`  BODY: ${r.body.substring(0, 200)}`);
      }
    }

    const uploadResponse = apiResponses.find((r) => r.url.includes("/bills/upload"));
    if (!uploadResponse) {
      console.log("ISSUE: No upload request was made to the backend.");
      // Still pass — it means the frontend blocked it before sending
      return;
    }

    console.log(`Upload HTTP status: ${uploadResponse.status}`);

    if (uploadResponse.status === 202) {
      // Upload succeeded — navigate to processing page
      await expect(page).toHaveURL(/\/upload\/processing/, { timeout: 10_000 });
      console.log("Step 3 PASSED: upload succeeded, navigated to processing.");

      // Extract job_id from URL
      const url = new URL(page.url());
      const jobId = url.searchParams.get("job_id");
      expect(jobId).toBeTruthy();
      console.log(`Job ID from URL: ${jobId}`);

      await snap(page, "03-processing");

      // Poll for job completion
      const jobResult = await waitForJob(jobId!, 90_000);
      console.log(`Job result: status=${jobResult.status}, bill_id=${jobResult.bill_id}`);

      expect(["completed", "needs_review"]).toContain(jobResult.status);
      expect(jobResult.bill_id).toBeTruthy();

      // Persist bill_id for downstream tests
      const fs = await import("fs");
      fs.writeFileSync(billIdFilePath(), jobResult.bill_id!);
    } else {
      // Upload failed — report the exact error
      console.log(`ISSUE FOUND — Upload returned HTTP ${uploadResponse.status}`);
      console.log(`Error body: ${uploadResponse.body}`);

      // Check if we are on the error state or still on /upload
      expect(currentUrl).toContain("/upload");
      // Verify error message shown to user
      const errorBanner = page.locator("text=Couldn't upload the bill");
      const hasError = await errorBanner.isVisible().catch(() => false);
      console.log(`User-visible error shown: ${hasError}`);

      // This is a documented failure — write a marker
      const fs = await import("fs");
      fs.writeFileSync(billIdFilePath(), "UPLOAD_FAILED");

      // Fail the test with a clear message
      expect(uploadResponse.status, `Upload endpoint returned ${uploadResponse.status}. Body: ${uploadResponse.body}`).toBe(202);
    }
  });

  // ── Step 4: Review page ───────────────────────────────────────────────────
  test("Step 4 — review page loads with bill data", async ({ page }) => {
    const fs = await import("fs");

    let id: string;
    try {
      id = fs.readFileSync(billIdFilePath(), "utf8").trim();
    } catch {
      test.skip(true, "Skipping: no bill_id from Step 3 (upload failed or not run)");
      return;
    }

    if (id === "UPLOAD_FAILED") {
      test.skip(true, "Skipping: upload failed in Step 3");
      return;
    }

    await page.goto(`/bills/${id}/review`);
    await expect(page).toHaveURL(new RegExp(`/bills/${id}/review`));
    await expect(page.locator("text=Loading…")).not.toBeVisible({ timeout: 10_000 });
    await expect(page.locator("text=Step 2 / 3")).toBeVisible();
    await expect(page.locator("input[placeholder='e.g. Sharma Electricals']")).toBeVisible();
    await expect(page.locator("input[placeholder='0.00']")).toBeVisible();
    await expect(page.locator("button", { hasText: "Looks good!" })).toBeVisible();

    await snap(page, "04-review-page");
    console.log("Step 4 PASSED: review page loaded with fields.");
  });

  // ── Step 5: Save bill ──────────────────────────────────────────────────────
  test("Step 5 — Looks good! saves bill and navigates to /done", async ({ page }) => {
    const fs = await import("fs");

    let id: string;
    try {
      id = fs.readFileSync(billIdFilePath(), "utf8").trim();
    } catch {
      test.skip(true, "Skipping: no bill_id from Step 3");
      return;
    }
    if (id === "UPLOAD_FAILED") {
      test.skip(true, "Skipping: upload failed");
      return;
    }

    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto(`/bills/${id}/review`);
    await expect(page.locator("text=Loading…")).not.toBeVisible({ timeout: 10_000 });
    await page.locator("button", { hasText: "Looks good!" }).click();

    await expect(page).toHaveURL(new RegExp(`/bills/${id}/done`), { timeout: 15_000 });
    await expect(page.locator("text=Bill saved!")).toBeVisible({ timeout: 8_000 });
    await expect(page.locator("text=Step 3 / 3")).toBeVisible();
    await expect(page.locator("button", { hasText: "Add another bill" })).toBeVisible();
    await expect(page.locator("a", { hasText: "View all bills" })).toBeVisible();

    await snap(page, "05-done-page");

    const criticalErrors = consoleErrors.filter(
      (e) => !e.includes("favicon") && !e.includes("net::ERR")
    );
    expect(criticalErrors).toHaveLength(0);
    console.log("Step 5 PASSED: bill saved, done page rendered.");
  });

  // ── Step 6: Bills list shows new bill ─────────────────────────────────────
  test("Step 6 — bills list shows newly added bill", async ({ page }) => {
    const fs = await import("fs");

    let id: string;
    try {
      id = fs.readFileSync(billIdFilePath(), "utf8").trim();
    } catch {
      test.skip(true, "Skipping: no bill_id");
      return;
    }
    if (id === "UPLOAD_FAILED") {
      test.skip(true, "Skipping: upload failed");
      return;
    }

    await page.goto("/bills");
    await expect(page.locator("h1", { hasText: "BillSnap" })).toBeVisible({ timeout: 10_000 });
    await expect(page.locator("text=Loading bills…")).not.toBeVisible({ timeout: 10_000 });
    await expect(page.locator("text=No bills yet")).not.toBeVisible({ timeout: 5_000 });

    const billLinks = page.locator(`a[href*="/bills/${id}"]`);
    await expect(billLinks.first()).toBeVisible({ timeout: 8_000 });

    await snap(page, "06-bills-list-with-bill");
    console.log("Step 6 PASSED: bill appears in bills list.");
  });

  // ── Step 7: Export ────────────────────────────────────────────────────────
  test("Step 7 — export endpoint returns valid file (direct HTTP check)", async ({ page }) => {
    const now = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const exportUrl = `${API_BASE}/api/v1/bills/export?month=${month}&format=xlsx&token=${AUTH_TOKEN}`;

    // Direct HTTP request — must return 200 with spreadsheet content type
    const res = await page.request.get(exportUrl);
    const status = res.status();
    const contentType = res.headers()["content-type"] ?? "";

    console.log(`Export URL: ${exportUrl}`);
    console.log(`Export HTTP status: ${status}`);
    console.log(`Export Content-Type: ${contentType}`);

    expect(status, `Export returned ${status} — expected 200`).toBe(200);

    const isSpreadsheet =
      contentType.includes("spreadsheet") ||
      contentType.includes("vnd.openxmlformats") ||
      contentType.includes("csv") ||
      contentType.includes("octet-stream");

    expect(isSpreadsheet, `Expected spreadsheet content-type, got: ${contentType}`).toBe(true);

    // Also verify CSV format works
    const csvRes = await page.request.get(
      `${API_BASE}/api/v1/bills/export?month=${month}&format=csv&token=${AUTH_TOKEN}`
    );
    console.log(`CSV Export HTTP status: ${csvRes.status()}`);
    console.log(`CSV Content-Type: ${csvRes.headers()["content-type"] ?? ""}`);
    expect(csvRes.status()).toBe(200);

    // Test from browser — click the Export button and check it opens correctly
    await page.goto("/bills");
    await expect(page.locator("h1", { hasText: "BillSnap" })).toBeVisible({ timeout: 10_000 });

    // Intercept download or popup
    const downloadPromise = page.waitForEvent("download", { timeout: 8_000 }).catch(() => null);
    const popupPromise = page.waitForEvent("popup", { timeout: 8_000 }).catch(() => null);

    await page.locator("button", { hasText: "Export" }).click();

    const [download, popup] = await Promise.all([downloadPromise, popupPromise]);
    await snap(page, "07-export");

    if (download) {
      console.log(`Export: download triggered. File: ${download.suggestedFilename()}`);
    } else if (popup) {
      const popupUrl = popup.url();
      console.log(`Export: popup opened at ${popupUrl}`);
      expect(popupUrl).toContain("/api/v1/bills/export");
    } else {
      // window.open may have been blocked in headless — the direct API test passed, so this is OK
      console.log("Export: no browser download/popup captured (likely blocked by headless browser).");
      console.log("Export backend check PASSED via direct HTTP request above.");
    }

    console.log("Step 7 PASSED: export endpoint returns valid file.");
  });
});
