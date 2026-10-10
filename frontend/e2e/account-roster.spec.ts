import { test, expect } from "@playwright/test";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";

const accounts: Record<string,{email:string;password:string}> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = "http://127.0.0.1:5174";
const api = "http://127.0.0.1:8001/api/v1";

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
    const current = await (await page.request.get(api+"/me/context")).json();
    const rounds = await (await page.request.get(api+"/admin/rounds")).json();
    const round = rounds.find((item:{code:string})=>item.code==="SYN-DEMO");
    expect(round).toBeTruthy();
    for (const assignment_type of ["ELIGIBILITY_IMPORTER","ELIGIBILITY_VERIFIER"]) {
      const response = await page.request.post(api+"/admin/round-assignments",{
        headers:{"X-CSRF-Token":current.csrf_token},
        data:{round_id:round.id,user_id:current.user_id,assignment_type,basis_ref:"SYNTHETIC-E2E"},
      });
      expect(response.status()).toBe(201);
    }
    await page.reload();
    await page.goto(web+"/roster");
    await expect(page.getByRole("heading",{name:"Danh sách đủ điều kiện"})).toBeVisible();
    const code = "E2E-ROSTER-001";
    const email = "roster-student@e2e.test";
    const csv = ["student_code,display_name,email,department_code,class_name,major_code",
      `${code},Sinh viên giả lập,${email},SYN-DEMO-DEP,CNTT-E2E,7480201`].join("\n");
    await page.locator('input[type="file"]').setInputFiles({name:"roster.csv",mimeType:"text/csv",buffer:Buffer.from(csv)});
    await page.getByLabel("Mã/số văn bản nguồn").fill("SYNTHETIC-E2E");
    await page.getByRole("button",{name:"Kiểm tra tệp"}).click();
    await expect(page.getByRole("heading",{name:/Xem trước: 1 sinh viên/})).toBeVisible();
    await page.getByRole("button",{name:"Nhập sau khi kiểm"}).click();
    await expect(page.getByText(/Đã nhập 1 kết quả chờ xác nhận/)).toBeVisible();
    await page.getByLabel("Căn cứ xác nhận/thu hồi").fill("SYNTHETIC-E2E-APPROVAL");
    await page.getByRole("button",{name:"Chọn tất cả chờ xác nhận"}).click();
    await page.getByRole("button",{name:"Xác nhận đã đối chiếu"}).click();
    await expect(page.getByText(/Đã xác nhận 1 sinh viên/)).toBeVisible();

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
      await studentPage.goto(link);
      await studentPage.getByLabel("Mật khẩu mới").fill("synthetic-password-123456");
      await studentPage.getByLabel("Nhập lại mật khẩu").fill("synthetic-password-123456");
      await studentPage.getByRole("button",{name:"Lưu mật khẩu"}).click();
      await expect(studentPage.getByText(/Đã cập nhật mật khẩu/)).toBeVisible();
      await studentPage.getByRole("link",{name:"Quay lại đăng nhập"}).click();
      await studentPage.getByLabel("Email",{exact:true}).fill(email);
      await studentPage.getByLabel("Mật khẩu",{exact:true}).fill("synthetic-password-123456");
      await studentPage.getByRole("button",{name:"Đăng nhập",exact:true}).click();
      await expect(studentPage.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
    } finally {await student.close();}
    expect(errors).toEqual([]);
  } finally {await admin.close();}
});
