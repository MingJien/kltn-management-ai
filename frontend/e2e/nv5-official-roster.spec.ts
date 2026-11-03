import {test,expect} from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web=`http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;
const api=`http://127.0.0.1:${process.env.KLTN_E2E_API_PORT || "8001"}/api/v1`;

test("Danh sách chính thức đủ điều kiện ngay → kích hoạt email → SV đăng nhập",async({browser})=>{
  const admin=await browser.newContext();const student=await browser.newContext();
  const page=await admin.newPage();const sv=await student.newPage();
  try {
    await page.goto(web);await page.getByLabel("Email",{exact:true}).fill(accounts.admin.email);
    await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts.admin.password);
    await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
    const user=await(await page.request.get(api+"/me/context")).json();
    const rounds=await(await page.request.get(api+"/admin/rounds")).json();
    const round=rounds.find((r:{state:string})=>r.state==="OPEN");expect(round).toBeTruthy();
    await page.goto(web+"/administration/assignments");
    await page.getByRole("combobox",{name:"Đợt",exact:true}).selectOption(round.id);
    await page.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("ELIGIBILITY_IMPORTER");
    await page.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption(user.user_id);
    await page.getByLabel("Căn cứ phân công").fill("Khoa giao nhập danh sách chính thức");
    const assignments=await(await page.request.get(api+"/admin/round-assignments")).json();
    if(!assignments.some((a:{round_id:string;user_id:string;assignment_type:string})=>a.round_id===round.id&&a.user_id===user.user_id&&a.assignment_type==="ELIGIBILITY_IMPORTER")) {
      await page.getByRole("button",{name:"Lưu phân công",exact:true}).click();
      await expect(page.getByRole("status").filter({hasText:"Đã lưu phân công"})).toBeVisible();
    }
    await page.getByRole("link",{name:"Danh sách sinh viên",exact:true}).click();
    await page.getByRole("tab",{name:/Nhập danh sách/}).click();
    const email="official-roster@e2e.test";const code="E2E-OFFICIAL-ROSTER";
    const csv=`MSSV;Họ tên;Email;Mã bộ môn;Lớp;Mã ngành\n${code};Sinh viên kiểm thử chính thức;${email};SYN-DEMO-DEP;E2E-CLASS;7480201`;
    await page.locator('input[type="file"]').setInputFiles({name:"official-roster.csv",mimeType:"text/csv",buffer:Buffer.from(csv)});
    await page.getByLabel("Mã/số văn bản nguồn").fill("KHOA-SYNTHETIC-OFFICIAL");
    await page.getByRole("button",{name:"Kiểm tra tệp",exact:true}).click();
    await expect(page.getByRole("heading",{name:/Xem trước: 1 sinh viên/})).toBeVisible();
    await page.getByRole("button",{name:"Nhập sau khi kiểm",exact:true}).click();
    await expect(page.getByText(/Đã ghi nhận 1 sinh viên đủ điều kiện/)).toBeVisible();
    await page.getByRole("tab",{name:/Danh sách sinh viên/}).click();
    await page.getByRole("searchbox",{name:"Tìm sinh viên",exact:true}).fill(code);
    const row=page.locator("tbody tr").filter({hasText:code});
    await expect(row).toContainText("Đủ điều kiện");
    await expect(page.getByRole("button",{name:"Xác nhận đã đối chiếu",exact:true})).toHaveCount(0);
    await sv.goto(web+"/account/activation-request");
    await sv.getByLabel("MSSV hoặc mã giảng viên").fill(code);await sv.getByLabel("Email đã đăng ký").fill(email);
    await sv.getByRole("button",{name:"Gửi hướng dẫn",exact:true}).click();
    let link="";const outbox=path.join(process.env.KLTN_E2E_RUN_DIR!,"mail-outbox");
    await expect.poll(async()=>{
      for(const f of await fs.readdir(outbox).catch(()=>[])) {
        const text=await fs.readFile(path.join(outbox,f),"utf8");
        if(text.includes(`To: ${email}`))link=text.match(/http:\/\/[^\s]+\/account\/activate\?token=[^\s]+/)?.[0] || "";
      }
      return !!link;
    }).toBe(true);
    await sv.goto(link);await sv.getByLabel("Mật khẩu mới",{exact:true}).fill("synthetic-official-2026");
    await sv.getByLabel("Nhập lại mật khẩu",{exact:true}).fill("synthetic-official-2026");
    await sv.getByRole("button",{name:"Lưu mật khẩu",exact:true}).click();
    await expect(sv.getByText(/Đã cập nhật mật khẩu/)).toBeVisible();
    await sv.goto(web);await sv.getByLabel("Email",{exact:true}).fill(email);await sv.getByLabel("Mật khẩu",{exact:true}).fill("synthetic-official-2026");
    await sv.getByRole("button",{name:"Đăng nhập",exact:true}).click();
    await expect(sv.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
  } finally {await admin.close();await student.close();}
});
