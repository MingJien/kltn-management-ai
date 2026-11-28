import { test, expect, type Browser, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const accounts: Record<string, { email: string; password: string }> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = `http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;

async function login(browser: Browser, key: string) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  await page.goto(web + "/");
  await page.getByLabel("Email", { exact: true }).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(accounts[key].password);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Tổng quan", exact: true })).toBeVisible();
  return { context, page, pageErrors, consoleErrors };
}

test("AI Workspace: phân quyền Admin/SV/TBM, kiểm chứng hợp đồng lỗi và WCAG 2.1 AA", async ({ browser }) => {
  test.setTimeout(120000);
  const admin = await login(browser, "admin");
  const sv = await login(browser, "sv1");
  const tbm = await login(browser, "tbm");

  try {
    // 1. RBAC: Admin không thấy mục Tra cứu AI trên sidebar và bị chặn khi vào thẳng /ai
    await expect(admin.page.locator('#main-sidebar a[href="/ai"]')).toHaveCount(0);
    await admin.page.goto(web + "/ai");
    await expect(admin.page).toHaveURL(new RegExp(`${web.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/$`));
    await expect(admin.page.locator("#rag-question")).toHaveCount(0);

    // 2. RBAC: TBM thấy cả 3 tab (bao gồm Đối chiếu báo cáo); SV chỉ thấy Hỏi đáp & Tìm đề tài tương đồng
    await tbm.page.goto(web + "/ai");
    await expect(tbm.page.getByRole("heading", { name: "Tra cứu AI", exact: true })).toBeVisible();
    await expect(tbm.page.getByRole("button", { name: "Hỏi đáp", exact: true })).toBeVisible();
    await expect(tbm.page.getByRole("button", { name: "Tìm đề tài tương đồng", exact: true })).toBeVisible();
    await expect(tbm.page.getByRole("button", { name: "Đối chiếu báo cáo", exact: true })).toBeVisible();

    await sv.page.goto(web + "/ai");
    await expect(sv.page.getByRole("heading", { name: "Tra cứu AI", exact: true })).toBeVisible();
    await expect(sv.page.getByRole("button", { name: "Hỏi đáp", exact: true })).toBeVisible();
    await expect(sv.page.getByRole("button", { name: "Tìm đề tài tương đồng", exact: true })).toBeVisible();
    await expect(sv.page.getByRole("button", { name: "Đối chiếu báo cáo", exact: true })).toHaveCount(0);

    // 3. Unmocked smoke check against real local backend /api/v1/ai/chat
    const starterBtn = sv.page.locator(".ai-prompt-starters button").first();
    await starterBtn.click();
    await expect(sv.page.locator("#rag-question")).not.toHaveValue("");
    const [liveChatResponse] = await Promise.all([
      sv.page.waitForResponse((res) => res.url().includes("/api/v1/ai/chat") && res.request().method() === "POST"),
      sv.page.getByRole("button", { name: "Tra cứu", exact: true }).click(),
    ]);
    expect(liveChatResponse.status()).toBeLessThan(600);
    // Phải hiển thị thẻ trả lời hoặc thông báo tiếng Việt đã ánh xạ (không lộ thông báo tiếng Anh thô của Qdrant)
    await expect(sv.page.locator(".ai-answer-block, .alert-info, .empty-state, [role='alert']").first()).toBeVisible();
    await expect(sv.page.locator("body")).not.toContainText("Qdrant is not configured");

    // 4. Controlled Playwright route simulation for deterministic AI provider, key collision, 503, NO_EVIDENCE, and similarity edge cases
    // Simulation A: RETRIEVAL_ONLY with duplicate source_id across 2 citations (GUIDELINE + FORM)
    await sv.page.route("**/api/v1/ai/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "RETRIEVAL_ONLY",
          answer: null,
          provider_status: "NOT_CONFIGURED",
          citations: [
            {
              source_id: "shared-source-id",
              source_type: "GUIDELINE",
              origin_type: "OFFICIAL",
              title: "Hướng dẫn quy trình KLTN 2026",
              provenance: "Phòng Đào tạo Khoa CN&KT",
              source_ref: "Mục 2.1 · Điều kiện đăng ký",
              source_url: null,
              source_version: "1",
              representation: "CHUNK",
              excerpt: "Sinh viên cần được xác nhận đủ điều kiện trước khi đăng ký đề tài.",
            },
            {
              source_id: "shared-source-id",
              source_type: "FORM",
              origin_type: "OFFICIAL",
              title: "Biểu mẫu đăng ký Mẫu 1a",
              provenance: "Kho biểu mẫu Khoa CN&KT",
              source_ref: "Mẫu 1a · Trang 1",
              source_url: null,
              source_version: "2",
              representation: "CHUNK",
              excerpt: "Biểu mẫu nộp kèm hồ sơ đăng ký đề tài khóa luận tốt nghiệp.",
            },
          ],
        }),
      });
    });

    await sv.page.locator("#rag-question").fill("Điều kiện và biểu mẫu đăng ký đề tài KLTN là gì?");
    await sv.page.getByRole("button", { name: "Tra cứu", exact: true }).click();
    await expect(sv.page.locator(".ai-citation-card")).toHaveCount(2);
    await expect(sv.page.locator(".ai-citation-card").nth(0)).toContainText("Hướng dẫn");
    await expect(sv.page.locator(".ai-citation-card").nth(0)).toContainText("Mục 2.1 · Điều kiện đăng ký");
    await expect(sv.page.locator(".ai-citation-card").nth(0)).toContainText("Sinh viên cần được xác nhận đủ điều kiện trước khi đăng ký đề tài.");
    await expect(sv.page.locator(".ai-citation-card").nth(1)).toContainText("Biểu mẫu");
    await expect(sv.page.locator(".ai-citation-card").nth(1)).toContainText("Mẫu 1a · Trang 1");
    expect(sv.consoleErrors.filter((msg) => msg.includes("same key") || msg.includes("unique \"key\""))).toEqual([]);
    await sv.page.unroute("**/api/v1/ai/chat");

    // Simulation B: 503 clears stale answer/citations card and maps Qdrant message to Vietnamese
    await sv.page.route("**/api/v1/ai/chat", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Qdrant is not configured" }),
      });
    });
    await sv.page.locator("#rag-question").fill("Kiểm tra lỗi dịch vụ tra cứu AI 503");
    await sv.page.getByRole("button", { name: "Tra cứu", exact: true }).click();
    await expect(sv.page.locator("p.alert-danger[role='alert']")).toContainText("Dịch vụ tra cứu AI chưa được cấu hình");
    await expect(sv.page.locator(".ai-citation-card")).toHaveCount(0);
    await expect(sv.page.getByText("Nguồn tham khảo", { exact: true })).toHaveCount(0);
    await sv.page.unroute("**/api/v1/ai/chat");

    // Simulation C: NO_EVIDENCE state
    await sv.page.route("**/api/v1/ai/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "NO_EVIDENCE",
          answer: null,
          citations: [],
          provider_status: "NOT_CONFIGURED",
        }),
      });
    });
    await sv.page.locator("#rag-question").fill("Câu hỏi không có dữ liệu chứng cứ");
    await sv.page.getByRole("button", { name: "Tra cứu", exact: true }).click();
    await expect(sv.page.getByRole("heading", { name: "Không tìm thấy nguồn phù hợp", exact: true })).toBeVisible();
    await sv.page.unroute("**/api/v1/ai/chat");

    // 5. Similarity tab: empty result -> valid hits with negative & >1 clamped bar + Vietnamese badges
    await sv.page.getByRole("button", { name: "Tìm đề tài tương đồng", exact: true }).click();
    await sv.page.route("**/api/v1/ai/similar-topics", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await sv.page.locator("#ai-query").fill("Đề tài chưa từng có trong kho lưu trữ");
    await sv.page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
    await expect(sv.page.getByRole("heading", { name: "Không tìm thấy nguồn tương đồng", exact: true })).toBeVisible();
    await sv.page.unroute("**/api/v1/ai/similar-topics");

    await sv.page.route("**/api/v1/ai/similar-topics", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            source_id: "sim-1",
            source_type: "CAPSTONE_PROJECT",
            origin_type: "ARCHIVE",
            title: "Hệ thống điểm danh khuôn mặt tại DThU",
            score: -0.25,
            provenance: "Kho KLTN 2024",
            source_ref: null,
            source_url: null,
            source_version: "1",
            representation: "TITLE",
            excerpt: "Xây dựng ứng dụng nhận diện khuôn mặt hỗ trợ điểm danh.",
          },
          {
            source_id: "sim-2",
            source_type: "TERM_PROJECT",
            origin_type: "ARCHIVE",
            title: "Trợ lý RAG tra cứu quy chế học vụ",
            score: 1.4,
            provenance: "Kho niên luận 2025",
            source_ref: null,
            source_url: null,
            source_version: "2",
            representation: "TITLE",
            excerpt: "Tra cứu văn bản quy chế bằng tìm kiếm ngữ nghĩa.",
          },
        ]),
      });
    });
    await sv.page.locator("#ai-query").fill("Hệ thống hỗ trợ tra cứu học vụ DThU");
    await sv.page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
    await expect(sv.page.locator('[role="status"]').filter({ hasText: "không phải tỉ lệ đạo văn" })).toBeVisible();
    await expect(sv.page.locator("article.card").nth(0)).toContainText("Đồ án tốt nghiệp");
    await expect(sv.page.locator("article.card").nth(1)).toContainText("Niên luận");
    await expect(sv.page.locator(".ai-score-fill").nth(0)).toHaveAttribute("style", /width:\s*0%/);
    await expect(sv.page.locator(".ai-score-fill").nth(1)).toHaveAttribute("style", /width:\s*100%/);
    await sv.page.unroute("**/api/v1/ai/similar-topics");

    // 6. Responsive overflow + Axe WCAG 2.0/2.1 A/AA at 1440x900 and 390x844
    for (const vp of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
      await sv.page.setViewportSize(vp);
      const noOverflow = await sv.page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
      expect(noOverflow).toBe(true);
      const axe = await new AxeBuilder({ page: sv.page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      expect(axe.violations).toEqual([]);
    }

    expect(admin.pageErrors).toEqual([]);
    expect(sv.pageErrors).toEqual([]);
    expect(tbm.pageErrors).toEqual([]);
  } finally {
    await Promise.all([
      admin.context.close().catch(() => undefined),
      sv.context.close().catch(() => undefined),
      tbm.context.close().catch(() => undefined),
    ]);
  }
});
