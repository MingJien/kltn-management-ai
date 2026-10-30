import { test, expect, type Browser } from "@playwright/test";

const accounts: Record<string, {email:string;password:string}> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const api = `http://127.0.0.1:${process.env.KLTN_E2E_API_PORT || "8001"}/api/v1`;

async function login(browser: Browser, key: string) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await page.getByLabel("Email", {exact:true}).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu", {exact:true}).fill(accounts[key].password);
  await page.getByRole("button", {name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading", {name:"Tổng quan",exact:true})).toBeVisible();
  return {page, context, errors};
}

test("Nhật ký UI: Admin xem căn cứ và lịch sử tài khoản; SV/GV/TBM chỉ xem đúng phạm vi", async ({browser}) => {
  const admin = await login(browser, "admin");
  const actors = [admin];
  const reference = "KH-NHATKY-" + Date.now();
  try {
    await admin.page.goto("/rounds");
    await admin.page.getByLabel("Năm học (ví dụ 2026-2027)").fill("2094-2095");
    await admin.page.getByLabel("Ngày bắt đầu năm học").fill("2094-09-01");
    await admin.page.getByLabel("Ngày kết thúc năm học").fill("2095-08-31");
    await admin.page.getByLabel("Mã đợt").fill("ACTIVITY");
    await admin.page.getByLabel("Mở đăng ký lúc").fill("2094-09-10T08:00");
    await admin.page.getByLabel("Đóng đăng ký lúc").fill("2094-10-10T17:00");
    await admin.page.getByLabel("Căn cứ lịch đợt").fill(reference);
    await admin.page.getByRole("button", {name:"Tạo bản nháp",exact:true}).click();
    await expect(admin.page.getByText(/Đã tạo đợt ở trạng thái bản nháp/)).toBeVisible();
    await admin.page.getByRole("link", {name:"Nhật ký hệ thống",exact:true}).click();
    await admin.page.getByLabel("Người thao tác, lý do, căn cứ hoặc mã hồ sơ").fill(reference);
    await admin.page.getByRole("button", {name:"Tra cứu",exact:true}).click();
    await expect(admin.page.getByRole("heading", {name:"Tạo đợt KLTN",exact:true})).toBeVisible();
    await expect(admin.page.getByText(reference, {exact:false}).filter({has:admin.page.locator("strong")})).toBeVisible();
    await admin.page.screenshot({path:test.info().outputPath("activity-admin.png"),fullPage:true});
    await expect(admin.page.getByText("đây là thông tin do người dùng nhập, hệ thống chưa xác minh văn bản gốc.", {exact:true})).toHaveCount(0);

    await admin.page.goto("/administration");
    await admin.page.getByLabel("Tìm theo mã, tên hoặc email tài khoản").fill(accounts.admin.email);
    await admin.page.getByLabel("Tìm theo mã, tên hoặc email tài khoản").press("Enter");
    const row = admin.page.locator(".account-list__row")
      .filter({has:admin.page.getByRole("link", {name:"Lịch sử tài khoản",exact:true})})
      .filter({hasText:accounts.admin.email});
    await expect(row).toHaveCount(1);
    await row.getByRole("link", {name:"Lịch sử tài khoản",exact:true}).click();
    await expect(admin.page.getByRole("heading", {name:"Đăng nhập",exact:true}).first()).toBeVisible();
    const me = await (await admin.page.request.get(api + "/me/context")).json();
    const history = await (await admin.page.request.get(api + `/activity?resource_type=user_account&resource_id=${me.user_id}`)).json();
    expect(history.items.every((item:{resource_id:string}) => item.resource_id === me.user_id)).toBe(true);

    for (const key of ["sv1", "gv", "tbm"]) {
      const actor = await login(browser, key); actors.push(actor);
      await actor.page.getByRole("link", {name:"Lịch sử hoạt động",exact:true}).click();
      await expect(actor.page.getByRole("heading", {name:"Đăng nhập",exact:true}).first()).toBeVisible();
      await actor.page.getByLabel("Người thao tác, lý do, căn cứ hoặc mã hồ sơ").fill(reference);
      await actor.page.getByRole("button", {name:"Tra cứu",exact:true}).click();
      await expect(actor.page.getByText("Chưa có sự kiện phù hợp với phạm vi và bộ lọc đã chọn.")).toBeVisible();
      await expect(actor.page.getByText(reference, {exact:true})).toHaveCount(0);
      if (key === "sv1") {
        await actor.page.getByRole("button", {name:"Xóa bộ lọc",exact:true}).click();
        await expect(actor.page.getByRole("heading", {name:"Đăng nhập",exact:true}).first()).toBeVisible();
        await actor.page.setViewportSize({width:390,height:844});
        await expect.poll(() => actor.page.locator(".app-shell__main").evaluate(element => getComputedStyle(element).marginLeft)).toBe("0px");
        await expect.poll(() => actor.page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
        await actor.page.screenshot({path:test.info().outputPath("activity-student-mobile.png"),fullPage:true});
      }
    }
    for (const actor of actors) expect(actor.errors).toEqual([]);
  } finally {
    for (const actor of actors) await actor.context.close();
  }
});
