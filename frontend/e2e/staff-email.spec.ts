import { test, expect } from "@playwright/test";

const accounts: Record<string,{email:string;password:string}> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = `http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;

test("ADMIN sửa email giảng viên trên tài khoản cũ, giữ UUID và cấp liên kết mới", async ({browser}) => {
  const admin = await browser.newContext();
  const page = await admin.newPage();
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  try {
    await page.goto(web);
    await page.getByLabel("Email",{exact:true}).fill(accounts.admin.email);
    await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts.admin.password);
    await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
    await page.goto(web+"/administration");
    const suffix = Date.now().toString().slice(-6);
    const oldEmail = `old-${suffix}@e2e.test`;
    const newEmail = `new-${suffix}@e2e.test`;
    await expect(page.getByLabel("Mã giảng viên")).toBeVisible();
    await page.getByLabel("Mã giảng viên").fill(`E2E-EMAIL-${suffix}`);
    await page.getByLabel("Họ tên").fill("GV sửa email");
    await page.getByLabel("Email",{exact:true}).fill(oldEmail);
    const department = page.getByLabel("Bộ môn");
    await expect(department.locator("option")).not.toHaveCount(1);
    await department.selectOption({index:1});
    await page.getByRole("button",{name:"Tạo và gửi lời mời"}).click();
    await expect(page.getByText(/Đã tạo tài khoản/)).toBeVisible();
    await page.getByLabel("Lý do thao tác tài khoản").fill("KHOA E2E xác minh mất hộp thư");
    await page.getByLabel("Tìm theo email hoặc MSSV").fill(oldEmail);
    const card = page.locator("section.card").filter({has: page.getByRole("heading",{name:"Tài khoản",exact:true})});
    const rows = card.locator(".account-list__row");
    await expect(rows).toHaveCount(1);
    await expect(rows.getByText(oldEmail)).toBeVisible();
    await rows.getByRole("button",{name:"Sửa email"}).click();
    await page.getByLabel("Lý do sửa email",{exact:true}).fill("KHOA E2E xác minh mất hộp thư");
    await expect(card.getByRole("heading",{name:"Sửa email trên tài khoản hiện có",exact:true})).toBeVisible();
    await expect(card.getByText("Đợt đối chiếu")).toHaveCount(0);
    await card.getByLabel("Email mới").fill(newEmail);
    await card.getByLabel("Căn cứ xác minh của Khoa").fill("KHOA-E2E-EMAIL");
    await card.getByRole("button",{name:"Lưu email mới"}).click();
    await expect(page.getByText(/Đã sửa email trên tài khoản cũ/)).toBeVisible();
    await page.getByLabel("Tìm theo email hoặc MSSV").fill(newEmail);
    await expect(rows).toHaveCount(1);
    await expect(rows.getByText(newEmail)).toBeVisible();
    await expect(rows.getByText("chưa kích hoạt")).toBeVisible();
    expect(errors).toEqual([]);
  } finally {await admin.close();}
});
