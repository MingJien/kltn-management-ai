import { test, expect } from "@playwright/test";

const accounts: Record<string,{email:string;password:string}> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = `http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;

test("Danh sách tài khoản phân trang 20/trang và tìm kiếm về trang 1", async ({browser}) => {
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
    await page.locator("#main-content").getByRole("link",{name:"Tài khoản và phân công"}).click();
    await page.getByRole("combobox",{name:"Đợt",exact:true}).selectOption({label:"SYN-DEMO · OPEN"});
    await page.getByLabel("Người được giao").selectOption({label:accounts.admin.email});
    await page.getByLabel("Căn cứ phân công").fill("SYNTHETIC-PAG");
    await page.getByRole("button",{name:"Lưu phân công"}).click();
    await page.getByLabel("Nhiệm vụ").selectOption("ELIGIBILITY_VERIFIER");
    await page.getByLabel("Căn cứ phân công").fill("SYNTHETIC-PAG");
    await page.getByRole("button",{name:"Lưu phân công"}).click();
    const rosterLink = page.getByRole("link",{name:"Danh sách sinh viên"});
    await expect(rosterLink.or(page.getByText(/Phân công này đã tồn tại/))).toBeVisible({timeout:15000});
    await rosterLink.click();
    await page.getByRole("tab",{name:/Nhập danh sách/}).click();
    const csv = ["student_code,display_name,email,department_code,class_name,major_code"];
    for (let i = 1; i <= 25; i++) csv.push(
      `E2E-PAG-${String(i).padStart(3,"0")},SV phân trang,pag-student-${String(i).padStart(3,"0")}@e2e.test,SYN-DEMO-DEP,CNTT-E2E,7480201`);
    await page.locator('input[type="file"]').setInputFiles({name:"pag.csv",mimeType:"text/csv",buffer:Buffer.from(csv.join("\n"))});
    await page.getByLabel("Mã/số văn bản nguồn").fill("SYNTHETIC-PAG");
    await page.getByRole("button",{name:"Kiểm tra tệp"}).click();
    await expect(page.getByRole("heading",{name:/Xem trước: 25 sinh viên/})).toBeVisible();
    await page.getByRole("button",{name:"Nhập sau khi kiểm"}).click();
    await expect(page.getByText(/Đã nhập 25 kết quả chờ xác nhận/)).toBeVisible();
    await page.getByRole("tab",{name:/Danh sách & xác nhận/}).click();
    await page.getByRole("searchbox",{name:"Tìm sinh viên",exact:true}).fill("E2E-PAG-");
    await page.getByLabel("Căn cứ đối chiếu danh sách").fill("SYNTHETIC-PAG-APPROVAL");
    await page.getByRole("button",{name:"Chọn tất cả chờ xác nhận"}).click();
    await page.getByRole("button",{name:"Xác nhận đã đối chiếu"}).click();
    await expect(page.getByText(/Đã xác nhận 25 sinh viên/)).toBeVisible();

    await page.goto(web+"/administration");
    const card = page.locator("section.card").filter({has: page.getByRole("heading",{name:"Tài khoản",exact:true})});
    const list = card.locator(".account-list__row");
    const usersCall = (offset: number) => page.waitForResponse(r =>
      r.request().method() === "GET" && r.url().includes("/admin/users?") && r.url().includes("offset=" + String(offset)));
    const goPage = async (target: number) => {
      const resp = usersCall((target - 1) * 20);
      await card.getByRole("button",{name: "Trang sau"}).click();
      const rows = await (await resp).json() as unknown[];
      await expect(card.getByText("Trang " + String(target))).toBeVisible();
      return rows.length;
    };
    await expect(list).toHaveCount(20);
    await expect(card.getByText("Trang 1")).toBeVisible();
    await expect.poll(() => card.getByRole("button",{name:"Trang trước"}).isDisabled()).toBe(true);
    await expect(card.getByRole("button",{name:"Trang sau"})).toBeEnabled();
    let pageNo = 2;
    let size = await goPage(2);
    expect(size).toBeLessThanOrEqual(20);
    while (size === 20 && pageNo < 6) {
      pageNo += 1;
      size = await goPage(pageNo);
    }
    expect(size).toBeGreaterThan(0);
    expect(size).toBeLessThan(20);
    await expect.poll(() => card.getByRole("button",{name:"Trang sau"}).isDisabled()).toBe(true);
    await page.getByLabel("Tìm theo email hoặc MSSV").fill("pag-student-007");
    await expect(list).toHaveCount(1);
    await expect(card.getByText("Trang 1")).toBeVisible();
    await expect(card.getByRole("button",{name:"Trang sau"})).toBeDisabled();
    expect(errors).toEqual([]);
  } finally {await admin.close();}
});
