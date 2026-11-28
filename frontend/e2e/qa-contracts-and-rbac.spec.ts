import { test, expect, type Browser } from "@playwright/test";

const accounts: Record<string, { email: string; password: string }> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = `http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;
const api = `http://127.0.0.1:${process.env.KLTN_E2E_API_PORT || "8001"}/api/v1`;

const VALID_PDF = Buffer.from(
  "%PDF-1.3\n%âãÏÓ\n1 0 obj\n<<\n/Producer (pypdf)\n>>\nendobj\n" +
  "2 0 obj\n<<\n/Type /Pages\n/Count 1\n/Kids [ 4 0 R ]\n>>\nendobj\n" +
  "3 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n" +
  "4 0 obj\n<<\n/Type /Page\n/Resources <<\n>>\n/MediaBox [ 0.0 0.0 612 792 ]\n/Parent 2 0 R\n>>\nendobj\n" +
  "xref\n0 5\n0000000000 65535 f \n0000000015 00000 n \n0000000054 00000 n \n0000000113 00000 n \n0000000162 00000 n \n" +
  "trailer\n<<\n/Size 5\n/Root 3 0 R\n/Info 1 0 R\n>>\nstartxref\n256\n%%EOF\n"
);

async function login(browser: Browser, key: string) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto(web + "/");
  await page.getByLabel("Email", { exact: true }).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(accounts[key].password);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Tổng quan", exact: true })).toBeVisible();
  return { context, page, pageErrors };
}

test("RBAC route/API 403, tự đề xuất 0-byte, drawer 409 If-Match, focus Escape và 429/401", async ({ browser }) => {
  test.setTimeout(120000);
  const sv = await login(browser, "sv1");
  const admin = await login(browser, "admin");
  const gv = await login(browser, "gv");
  const secondarySv = await login(browser, "auditSv1");

  try {
    // 1. Direct URL & Backend API 403 RBAC Guards
    for (const restricted of ["/administration", "/rounds", "/positions", "/roster", "/reports"]) {
      await sv.page.goto(web + restricted);
      await expect(sv.page).toHaveURL(new RegExp(`${web.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/$`));
    }
    const svContext = await (await sv.page.request.get(api + "/me/context")).json();
    expect((await sv.page.request.get(api + "/admin/users/directory")).status()).toBe(403);
    expect((await sv.page.request.get(api + "/admin/rounds")).status()).toBe(403);
    expect((await sv.page.request.post(api + "/admin/rounds", {
      headers: { "X-CSRF-Token": svContext.csrf_token },
      data: {
        academic_year_code: "2026-2027",
        year_starts_on: "2026-09-01",
        year_ends_on: "2027-06-30",
        code: "UNAUTHORIZED-R1",
        round_type: "MAIN",
        opens_at: "2026-10-01T00:00:00Z",
        closes_at: "2026-11-01T00:00:00Z",
        basis_ref: "Unauthorized RBAC check",
      },
    })).status()).toBe(403);

    for (const workflowOnly of ["/theses", "/registrations", "/withdrawals", "/changes"]) {
      await admin.page.goto(web + workflowOnly);
      await expect(admin.page).toHaveURL(new RegExp(`${web.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/$`));
    }

    // 2. Student self-proposal 0-byte rejection + valid PDF upload forwarding (real backend + ClamAV)
    await sv.page.goto(web + "/topics");
    const proposeBtn = sv.page.getByRole("button", { name: "Tự đề xuất đề tài", exact: true });
    await expect(proposeBtn).toBeEnabled();
    await proposeBtn.click();

    const createDialog = sv.page.getByRole("dialog", { name: "Tự đề xuất và lập đăng ký" });
    await expect(createDialog).toBeVisible();
    const roundSelect = createDialog.locator("#topic-round");
    if (await roundSelect.evaluate((el) => el.tagName === "SELECT")) {
      await roundSelect.selectOption({ index: 1 });
    }
    await createDialog.locator("#topic-title").fill("Đề xuất tự động QA kiểm tra minh chứng 0 byte");
    await createDialog.locator("#topic-description").fill("Phạm vi nghiên cứu kiểm thử hợp đồng tải tệp minh chứng khi tự đề xuất đề tài.");
    const lecturerSelect = createDialog.locator("#topic-lecturer");
    await expect(lecturerSelect.locator("option")).not.toHaveCount(1);
    const firstValidOption = await lecturerSelect.locator('option[value]:not([value=""]):not([disabled])').first().getAttribute("value");
    expect(firstValidOption).toBeTruthy();
    await lecturerSelect.selectOption(firstValidOption!);
    await createDialog.getByRole("checkbox").check();

    // 0-byte PDF must be rejected client-side before submit
    await createDialog.locator("#registration-evidence-file").setInputFiles({
      name: "empty.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.alloc(0),
    });
    await expect(createDialog.getByRole("alert")).toContainText("0 byte");
    await expect(createDialog.getByRole("button", { name: "Lập đăng ký của tôi", exact: true })).toBeDisabled();

    // Valid PDF clears error and forwards to /registrations with saved evidence
    await createDialog.locator("#registration-evidence-file").setInputFiles({
      name: "minh-chung-de-xuat.pdf",
      mimeType: "application/pdf",
      buffer: VALID_PDF,
    });
    await expect(createDialog.getByRole("alert")).toHaveCount(0);
    await expect(createDialog.getByRole("button", { name: "Lập đăng ký của tôi", exact: true })).toBeEnabled();
    await createDialog.getByRole("button", { name: "Lập đăng ký của tôi", exact: true }).click();

    await expect(sv.page).toHaveURL(/\/registrations$/);
    await expect(sv.page.getByText("Đã lập đăng ký và lưu minh chứng của bạn.", { exact: true })).toBeVisible();
    await expect(sv.page.getByText(/minh-chung-de-xuat\.pdf/).first()).toBeVisible();

    // 3. Topic Side Drawer real 409 optimistic concurrency (If-Match auto-refresh) & Escape filter preservation
    const gvContext = await (await gv.page.request.get(api + "/me/context")).json();
    const openRounds = await (await gv.page.request.get(api + "/rounds/open")).json();
    const token = `QA409-${Date.now()}`;
    const createRes = await gv.page.request.post(api + "/topics", {
      headers: { "X-CSRF-Token": gvContext.csrf_token },
      data: {
        round_id: openRounds[0].id,
        title: `Đề tài kiểm thử 409 ${token}`,
        description: "Mô tả ban đầu trước khi có cập nhật đồng thời",
        max_students: 2,
        requirements: [],
      },
    });
    expect(createRes.status()).toBe(201);
    const createdTopic = await createRes.json();

    await gv.page.goto(web + "/topics");
    await gv.page.getByRole("button", { name: "Đề tài của tôi", exact: true }).click();
    const searchInput = gv.page.getByLabel("Tìm đề tài", { exact: true });
    await searchInput.fill(token);
    const topicCard = gv.page.locator("article.topic-card").filter({ hasText: token });
    await expect(topicCard).toHaveCount(1);
    await topicCard.getByRole("button", { name: "Xem chi tiết", exact: true }).click();

    const drawer = gv.page.locator(".dialog--drawer");
    await expect(drawer).toBeVisible();

    // Concurrent external update bumps row_version on the server
    const concurrentUpdate = await gv.page.request.patch(api + `/topics/${createdTopic.id}`, {
      headers: {
        "X-CSRF-Token": gvContext.csrf_token,
        "If-Match": String(createdTopic.row_version),
      },
      data: {
        title: createdTopic.title,
        description: "Cập nhật nền gây xung đột phiên bản",
        max_students: 2,
        requirements: [],
      },
    });
    expect(concurrentUpdate.status()).toBe(200);

    // Editing inside open drawer with stale row_version hits real 409 -> displays alert and auto-refreshes fresh version
    await drawer.locator("#topic-description").fill("Thao tác trễ để kích hoạt HTTP 409");
    await drawer.getByRole("button", { name: "Lưu chỉnh sửa", exact: true }).click();
    await expect(drawer.locator("p.alert-danger[role='alert']")).toBeVisible();
    await expect(drawer.locator("#topic-description")).toHaveValue("Cập nhật nền gây xung đột phiên bản");

    // Second save succeeds immediately using the auto-refreshed row_version
    await drawer.locator("#topic-description").fill("Đã lưu thành công sau khi tự làm mới phiên bản");
    await drawer.getByRole("button", { name: "Lưu chỉnh sửa", exact: true }).click();
    await expect(drawer.locator("p.alert-danger[role='alert']")).toHaveCount(0);
    await expect(drawer.getByText("Đã lưu đề tài.", { exact: true })).toBeVisible();

    // Press Escape: drawer closes and search filter stays intact
    await gv.page.keyboard.press("Escape");
    await expect(drawer).toHaveCount(0);
    await expect(searchInput).toHaveValue(token);

    // 4. NotificationsBell & ProfilePopup Escape focus restoration + controlled 429 & 401 session expiry
    await secondarySv.page.goto(web + "/topics");
    const notifTrigger = secondarySv.page.locator("button.notifications__trigger");
    await notifTrigger.click();
    await expect(secondarySv.page.getByRole("dialog", { name: "Thông báo", exact: true })).toBeVisible();
    await secondarySv.page.keyboard.press("Escape");
    await expect(secondarySv.page.getByRole("dialog", { name: "Thông báo", exact: true })).toHaveCount(0);
    await expect(notifTrigger).toBeFocused();

    const profileTrigger = secondarySv.page.locator('button[aria-label="Xem hồ sơ cá nhân"]');
    await profileTrigger.click();
    await expect(secondarySv.page.getByRole("dialog", { name: "Hồ sơ cá nhân", exact: true })).toBeVisible();
    await secondarySv.page.keyboard.press("Escape");
    await expect(secondarySv.page.getByRole("dialog", { name: "Hồ sơ cá nhân", exact: true })).toHaveCount(0);
    await expect(profileTrigger).toBeFocused();

    // Controlled Playwright network simulation for 429 rate-limit and 401 session-expired handling
    await secondarySv.page.route("**/api/v1/topics*", async (route) => {
      await route.fulfill({
        status: 429,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Too many requests" }),
      });
    });
    await secondarySv.page.getByRole("button", { name: "Làm mới", exact: true }).click();
    await expect(secondarySv.page.getByText("Bạn thao tác quá nhanh. Vui lòng chờ một lát rồi thử lại.", { exact: true })).toBeVisible();
    await secondarySv.page.unroute("**/api/v1/topics*");

    await secondarySv.page.route("**/api/v1/topics*", async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Sign-in session has expired" }),
      });
    });
    await secondarySv.page.getByRole("button", { name: "Làm mới", exact: true }).click();
    await expect(secondarySv.page.locator("#login-email")).toBeVisible();
    await expect(secondarySv.page.locator(".login-card [role='alert']")).toContainText("Phiên đăng nhập đã hết");
    await secondarySv.page.unroute("**/api/v1/topics*");

    expect(sv.pageErrors).toEqual([]);
    expect(admin.pageErrors).toEqual([]);
    expect(gv.pageErrors).toEqual([]);
    expect(secondarySv.pageErrors).toEqual([]);
  } finally {
    await Promise.all([
      sv.context.close().catch(() => undefined),
      admin.context.close().catch(() => undefined),
      gv.context.close().catch(() => undefined),
      secondarySv.context.close().catch(() => undefined),
    ]);
  }
});
