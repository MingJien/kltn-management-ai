import { test, expect } from "@playwright/test";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";

const accounts: Record<string,{email:string;password:string}> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = `http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;

test("Khoa phân quyền, nhập và xác nhận danh sách; SV tự kích hoạt", async ({browser}) => {
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
    await page.goto(web+"/rounds");
    await page.getByLabel("Năm học (ví dụ 2026-2027)").fill("2098-2099");
    await page.getByLabel("Ngày bắt đầu năm học").fill("2098-09-01");
    await page.getByLabel("Ngày kết thúc năm học").fill("2099-08-31");
    await page.getByLabel("Mã đợt").fill("E2E-D1");
    await page.getByLabel("Mở đăng ký lúc").fill("2098-09-20T08:00");
    await page.getByLabel("Đóng đăng ký lúc").fill("2098-10-20T17:00");
    await page.getByLabel("Căn cứ lịch đợt").fill("SYNTHETIC E2E PLAN");
    await page.getByRole("button",{name:"Tạo bản nháp"}).click();
    await expect(page.getByText(/Đã tạo đợt ở trạng thái bản nháp/)).toBeVisible();
    const newRound = page.locator(".account-list__row").filter({hasText:"E2E-D1"});
    await newRound.getByRole("button",{name:"Sửa bản nháp"}).click();
    await page.getByLabel("Đóng đăng ký lúc").fill("2098-10-25T17:00");
    await page.getByLabel("Lý do sửa lịch").fill("SYNTHETIC E2E CORRECTION");
    await page.getByRole("button",{name:"Lưu bản nháp"}).click();
    await expect(page.getByText(/Đã cập nhật bản nháp/)).toBeVisible();
    await newRound.getByRole("button",{name:"Mở đợt"}).click();
    await page.getByRole("dialog").getByLabel("Lý do / căn cứ").fill("SYNTHETIC E2E PLAN");
    await page.getByRole("dialog").getByRole("button",{name:"Mở đợt"}).click();
    await expect(newRound).toContainText("Đã mở");
    await newRound.getByRole("button",{name:"Đóng đợt"}).click();
    await page.getByRole("dialog").getByLabel("Lý do / căn cứ").fill("SYNTHETIC E2E CLOSE");
    await page.getByRole("dialog").getByRole("button",{name:"Đóng đợt"}).click();
    await expect(newRound).toContainText("Đã đóng");
    await page.getByRole("link",{name:"Tài khoản và phân công"}).click();
    await page.getByRole("combobox",{name:"Đợt",exact:true}).selectOption({label:"SYN-DEMO · OPEN"});
    await page.getByLabel("Người được giao").selectOption({label:accounts.admin.email});
    await page.getByLabel("Căn cứ phân công").fill("SYNTHETIC-E2E");
    await page.getByRole("button",{name:"Lưu phân công"}).click();
    await expect(page.getByRole("link",{name:"Danh sách sinh viên"})).toBeVisible();
    await page.getByLabel("Nhiệm vụ").selectOption("ELIGIBILITY_VERIFIER");
    await page.getByRole("button",{name:"Lưu phân công"}).click();
    await page.getByRole("link",{name:"Danh sách sinh viên"}).click();
    await expect(page.getByRole("heading",{name:"Danh sách đủ điều kiện"})).toBeVisible();
    await page.getByRole("tab",{name:/Nhập danh sách/}).click();
    const code = "E2E-ROSTER-001";
    const email = "roster-student@e2e.test";
    const csv = ["MSSV;Họ và tên;Email;Mã bộ môn;Lớp;Mã ngành",
      `${code};Sinh viên giả lập;${email};SYN-DEMO-DEP;CNTT-E2E;7480201`].join("\n");
    await page.locator('input[type="file"]').setInputFiles({name:"roster.csv",mimeType:"text/csv",buffer:Buffer.from(csv)});
    await page.getByLabel("Mã/số văn bản nguồn").fill("SYNTHETIC-E2E");
    await page.getByRole("button",{name:"Kiểm tra tệp"}).click();
    await expect(page.getByRole("heading",{name:/Xem trước: 1 sinh viên/})).toBeVisible();
    await page.getByRole("button",{name:"Nhập sau khi kiểm"}).click();
    await expect(page.getByText(/Đã nhập 1 kết quả chờ xác nhận/)).toBeVisible();
    await page.getByRole("tab",{name:/Danh sách & xác nhận/}).click();
    // Simulate a backend process that has not yet restarted after adding account_activated.
    await page.route("**/api/v1/rounds/*/roster",async route=>{
      if(route.request().method()!=="GET") return route.continue();
      const response=await route.fetch();
      const rows=await response.json() as Array<Record<string,unknown>>;
      for(const row of rows) delete row.account_activated;
      await route.fulfill({response,json:rows});
    });
    await page.reload();
    await page.getByRole("combobox",{name:"Kích hoạt tài khoản"}).selectOption("activated");
    await expect(page.getByText(/Đang hiện [1-9]\d*\/\d+ sinh viên thuộc đợt đã chọn/)).toBeVisible();
    await page.getByRole("combobox",{name:"Kích hoạt tài khoản"}).selectOption("not-activated");
    await page.getByRole("searchbox",{name:"Tìm sinh viên",exact:true}).fill(code);
    await expect(page.getByText(/Đang hiện 1\/\d+ sinh viên thuộc đợt đã chọn/)).toBeVisible();
    await page.getByRole("searchbox",{name:"Tìm sinh viên",exact:true}).fill("khong-ton-tai");
    await expect(page.getByText("Không có sinh viên khớp bộ lọc.")).toBeVisible();
    await page.getByRole("searchbox",{name:"Tìm sinh viên",exact:true}).fill(code);
    await page.getByRole("tab",{name:/Ngoại lệ Hiệu trưởng/}).click();
    await page.getByRole("searchbox",{name:"Tìm sinh viên được xét ngoại lệ"}).fill(code);
    await expect(page.getByRole("combobox",{name:"Sinh viên được xét ngoại lệ"}).locator("option")).toHaveCount(2);
    await page.getByRole("tab",{name:/Danh sách & xác nhận/}).click();
    await page.getByLabel("Căn cứ đối chiếu danh sách").fill("SYNTHETIC-E2E-APPROVAL");
    await page.getByRole("button",{name:"Chọn tất cả chờ xác nhận"}).click();
    await page.getByRole("button",{name:"Xác nhận đã đối chiếu"}).click();
    await expect(page.getByText(/Đã xác nhận 1 sinh viên/)).toBeVisible();
    await page.getByText("Thu hồi kết quả đã xác nhận",{exact:false}).click();
    await page.getByRole("searchbox",{name:"Tìm sinh viên cần thu hồi"}).fill(code);
    await expect(page.getByRole("combobox",{name:"Sinh viên cần thu hồi"}).locator("option")).toHaveCount(2);
    await page.getByRole("combobox",{name:"Sinh viên cần thu hồi"}).selectOption({label:`${code} · Sinh viên giả lập`});
    await page.getByLabel("Văn bản nguồn thu hồi").fill("SYNTHETIC-E2E-REVOKE");
    await page.getByLabel("Lý do",{exact:true}).fill("SYNTHETIC-E2E-REASON");
    await page.getByRole("button",{name:"Thu hồi quyền tham gia"}).click();
    await expect(page.getByText(/Đã thu hồi quyền tham gia/)).toBeVisible();
    await page.getByRole("tab",{name:/Đính chính hồ sơ/}).click();
    await page.getByRole("searchbox",{name:/Tìm sinh viên cần đính chính/}).fill(code);
    await page.getByRole("combobox",{name:"Sinh viên cần đính chính"}).selectOption({label:`${code} · Sinh viên giả lập`});
    await expect(page.getByRole("combobox",{name:"Sinh viên cần đính chính"})).toHaveValue(/.+/);

    const student = await browser.newContext();
    const studentPage = await student.newPage();
    studentPage.on("pageerror", error => errors.push(error.message));
    try {
      await studentPage.goto(web+"/account/activation-request");
      await studentPage.getByLabel("MSSV hoặc mã giảng viên").fill(code);
      await studentPage.getByLabel("Email đã đăng ký").fill(email);
      await studentPage.getByRole("button",{name:"Gửi hướng dẫn"}).click();
      await expect(studentPage.getByText(/Nếu thông tin hợp lệ/)).toBeVisible();
      const outbox = path.join(process.env.KLTN_E2E_RUN_DIR!,"mail-outbox");
      let link = "";
      await expect.poll(()=>{
        if (!existsSync(outbox)) return "";
        for (const file of readdirSync(outbox)) {
          const message = readFileSync(path.join(outbox,file),"utf-8");
          if (message.includes(`To: ${email}`)) link = message.match(/http:\/\/[^\s]+\/account\/activate\?token=[^\s]+/)?.[0] || "";
        }
        return link;
      }).not.toBe("");
      // The email link must render even in a browser already signed in as Admin.
      await page.goto(link);
      await expect(page.getByRole("heading",{name:"Tạo mật khẩu"})).toBeVisible();
      await expect(page.getByText(/Bạn đang đăng nhập với tài khoản/)).toBeVisible();
      await page.getByLabel("Mật khẩu mới").fill("synthetic-password-123456");
      await page.getByLabel("Nhập lại mật khẩu").fill("synthetic-password-123456");
      await page.getByRole("button",{name:"Lưu mật khẩu"}).click();
      await expect(page.getByText(/Đã cập nhật mật khẩu/)).toBeVisible();
      await page.getByRole("link",{name:"Quay lại đăng nhập"}).click();
      await expect(page.getByLabel("Email",{exact:true})).toBeVisible();
      await studentPage.goto(web);
      await studentPage.getByLabel("Email",{exact:true}).fill(email);
      await studentPage.getByLabel("Mật khẩu",{exact:true}).fill("synthetic-password-123456");
      await studentPage.getByRole("button",{name:"Đăng nhập",exact:true}).click();
      await expect(studentPage.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
    } finally {await student.close();}
    expect(errors).toEqual([]);
  } finally {await admin.close();}
});
