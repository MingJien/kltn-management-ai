import {test, expect, type Page} from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const accounts: Record<string,{email:string;password:string}> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const api = `http://127.0.0.1:${process.env.KLTN_E2E_API_PORT || "8001"}/api/v1`;
const outbox = path.join(process.env.KLTN_E2E_RUN_DIR!, "mail-outbox");
const department = process.env.KLTN_E2E_SAMPLE_DEPARTMENT === "true" ? "BM-CNTT" : "SYN-DEMO-DEP";
const demos = [
  {code:"1124011001",name:"Nguyễn Minh An",email:"sv-demo-01@example.invalid"},
  {code:"1124011002",name:"Trần Ngọc Bình",email:"sv-demo-02@example.invalid"},
  {code:"1124011003",name:"Lê Gia Hân",email:"sv-demo-03@example.invalid"},
  {code:"1124011004",name:"Phạm Minh Khang",email:"sv-demo-04@example.invalid"},
];
const password = "Synthetic-Demo-2026!";

async function read(page:Page, route:string) {
  const response = await page.request.get(api + route);
  expect(response.status()).toBe(200);
  return response.json();
}
async function post(page:Page, route:string, data?:unknown, version?:number) {
  const auth = await read(page,"/me/context");
  const response = await page.request.post(api + route, {data,headers:{"X-CSRF-Token":auth.csrf_token,
    ...(version === undefined ? {} : {"If-Match":String(version)})}});
  expect(response.ok(),await response.text()).toBeTruthy();
  return response.json();
}
async function login(page:Page,email:string,secret:string) {
  await page.goto("/");
  await page.getByLabel("Email",{exact:true}).fill(email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(secret);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
}
async function openAssignments(page:Page) {
  await page.goto("/administration/assignments");
  await expect.poll(async()=>new URL(page.url()).pathname === "/" ||
    await page.getByRole("combobox",{name:"Đợt",exact:true}).isVisible()).toBe(true);
  if (new URL(page.url()).pathname === "/") await page.goto("/administration");
}

test("Bốn SV demo kích hoạt, đăng ký đề tài GV1 và xử lý xin thôi", async ({browser}) => {
  test.setTimeout(240000);
  const contexts = await Promise.all(Array.from({length:8},()=>browser.newContext()));
  const [admin,tbm,gv,...otherPages] = await Promise.all(contexts.map(c=>c.newPage()));
  for (const page of [admin,tbm,gv,...otherPages]) page.setDefaultTimeout(20000);
  const students=otherPages.slice(0,4), outsider=otherPages[4];
  try {
    await login(admin,accounts.admin.email,accounts.admin.password);
    await login(tbm,accounts.tbm.email,accounts.tbm.password);
    await login(gv,accounts.gv.email,accounts.gv.password);
    await login(outsider,accounts.nv6Outsider.email,accounts.nv6Outsider.password);
    const round = (await read(gv,"/rounds/open"))[0];
    await openAssignments(admin);
    await admin.getByRole("combobox",{name:"Đợt",exact:true}).selectOption(round.id);
    await admin.getByLabel("Nhiệm vụ").selectOption("ELIGIBILITY_IMPORTER");
    await admin.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption((await read(admin,"/me/context")).user_id);
    await admin.getByLabel("Căn cứ phân công").fill("Danh sách thử nghiệm tự động");
    await admin.getByRole("button",{name:"Lưu phân công"}).click();
    await expect(admin.getByText("Đã lưu phân công.",{exact:true})).toBeVisible();
    await admin.goto("/roster");
    await admin.getByRole("tab",{name:/Nhập danh sách/}).click();
    const csv = ["MSSV;Họ và tên;Email;Mã bộ môn;Lớp;Mã ngành",
      ...demos.map(d=>`${d.code};${d.name};${d.email};${department};ĐHCNTT23F-IT;7480201`)].join("\n");
    await admin.locator('input[type="file"]').setInputFiles({name:"sinh-vien-demo.csv",mimeType:"text/csv",buffer:Buffer.from(csv)});
    await admin.getByLabel("Mã/số văn bản nguồn").fill("DANH-SACH-DEMO-2026");
    await admin.getByRole("button",{name:"Kiểm tra tệp"}).click();
    await expect(admin.getByRole("heading",{name:/Xem trước: 4 sinh viên/})).toBeVisible();
    await admin.getByRole("button",{name:"Nhập sau khi kiểm"}).click();
    await expect(admin.getByText(/Đã ghi nhận 4 sinh viên đủ điều kiện/)).toBeVisible();

    for (let i=0;i<demos.length;i++) {
      const page=students[i], demo=demos[i];
      await page.goto("/account/activation-request");
      await page.getByLabel("MSSV hoặc mã giảng viên").fill(demo.code);
      await page.getByLabel("Email đã đăng ký").fill(demo.email);
      await page.getByRole("button",{name:"Gửi hướng dẫn"}).click();
      await expect(page.getByText(/Nếu thông tin hợp lệ/)).toBeVisible();
      let mail="";
      await expect.poll(async()=>{
        for(const file of await fs.readdir(outbox).catch(()=>[] as string[])) {
          const text=await fs.readFile(path.join(outbox,file),"utf8");
          if(text.startsWith(`To: ${demo.email}`)) mail=text;
        }
        return mail.includes("/account/activate?token=");
      }).toBeTruthy();
      const link=mail.match(/http[^\s]+\/account\/activate\?token=[^\s]+/)?.[0];
      expect(link).toBeTruthy();
      await page.goto(link!);
      await page.getByLabel("Mật khẩu mới",{exact:true}).fill(password);
      await page.getByLabel("Nhập lại mật khẩu",{exact:true}).fill(password);
      await page.getByRole("button",{name:"Lưu mật khẩu"}).click();
      await expect(page.getByText("Đã cập nhật mật khẩu. Bạn có thể đăng nhập.")).toBeVisible();
      await login(page,demo.email,password);
      expect((await read(page,`/me/eligibility?round_id=${round.id}`)).eligible).toBe(true);
    }

    for(let group=0;group<2;group++) {
      let topic=await post(gv,"/topics",{round_id:round.id,title:`Đề tài GV1 kiểm thử nhóm ${group+1}`,max_students:2});
      topic=await post(gv,`/topics/${topic.id}/submit`,undefined,topic.row_version);
      await post(tbm,`/topics/${topic.id}/department-decision`,{decision:"APPROVE"},topic.row_version);
      if(group===1) {
        await openAssignments(admin);
        await admin.getByRole("combobox",{name:"Đợt",exact:true}).selectOption(round.id);
        await admin.getByLabel("Nhiệm vụ").selectOption("ELIGIBILITY_VERIFIER");
        await admin.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption((await read(admin,"/me/context")).user_id);
        await admin.getByLabel("Căn cứ phân công").fill("Đối chiếu dữ liệu giả lập");
        await admin.getByRole("button",{name:"Lưu phân công"}).click();
        await admin.goto("/roster");
        await admin.getByText("Thu hồi kết quả đã xác nhận",{exact:true}).click();
        await admin.getByRole("searchbox",{name:"Tìm sinh viên cần thu hồi"}).fill("E2E-nv6Outsider");
        await admin.getByRole("combobox",{name:"Sinh viên cần thu hồi",exact:true}).selectOption({label:"E2E-nv6Outsider · SV kiểm thử nv6Outsider"});
        await admin.getByLabel("Văn bản nguồn thu hồi").fill("THU-HOI-DEMO");
        await admin.getByLabel("Lý do",{exact:true}).fill("Mô phỏng kiểm tra điều kiện");
        await admin.getByRole("button",{name:"Thu hồi quyền tham gia",exact:true}).click();
        await expect(admin.getByText("Đã thu hồi quyền tham gia; hồ sơ cũ được giữ để rà soát.")).toBeVisible();
        const page=outsider;
        expect((await read(page,`/me/eligibility?round_id=${round.id}`)).eligible).toBe(false);
        await page.goto("/topics");
        await page.getByRole("button",{name:"Đề tài có sẵn",exact:true}).click();
        await page.getByLabel("Tìm đề tài").fill(topic.title);
        const card=page.locator("article").filter({has:page.getByRole("heading",{name:topic.title,exact:true})});
        await card.getByRole("button",{name:"Đăng ký",exact:true}).click();
        const dialog=page.getByRole("dialog");
        await expect(dialog.getByText("Bạn chưa được xác nhận đủ điều kiện ở đợt này. Liên hệ người phụ trách của Khoa.")).toBeVisible();
        await dialog.getByRole("checkbox").check();
        await expect(dialog.getByRole("button",{name:"Lập đăng ký của tôi"})).toBeDisabled();
      }
      for(let i=0;i<2;i++) {
        const page=students[group*2+i];
        await page.goto("/topics");
        await page.getByRole("button",{name:"Đề tài có sẵn",exact:true}).click();
        await page.getByLabel("Tìm đề tài").fill(topic.title);
        const card=page.locator("article").filter({has:page.getByRole("heading",{name:topic.title,exact:true})});
        await card.getByRole("button",{name:i ? "Tham gia" : "Đăng ký",exact:true}).click();
        const dialog=page.getByRole("dialog");
        await dialog.getByRole("checkbox").check();
        await dialog.getByRole("button",{name:i ? "Tham gia đề tài" : "Lập đăng ký của tôi",exact:true}).click();
        await expect(page.getByRole("heading",{name:"Đăng ký đề tài",exact:true})).toBeVisible();
      }
      await students[group*2].getByRole("button",{name:"Gửi đăng ký cho GV",exact:true}).click();
      await expect(students[group*2].getByRole("status")).toContainText("Đã gửi đăng ký");
      await gv.goto("/registrations");
      const registration=gv.locator("article").filter({hasText:topic.title});
      await registration.getByRole("button",{name:"Chấp nhận chính thức và tạo khóa luận"}).click();
      await expect(registration).toContainText("GV đã chấp nhận chính thức");
    }
    const thesis=(await read(students[0],"/withdrawals")).theses[0];
    expect(thesis).toBeTruthy();

    await openAssignments(admin);
    await admin.getByRole("combobox",{name:"Đợt",exact:true}).selectOption(round.id);
    await admin.getByLabel("Nhiệm vụ").selectOption("KLTN_COORDINATOR");
    await admin.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption((await read(tbm,"/me/context")).user_id);
    await admin.getByLabel("Căn cứ phân công").fill("Điều phối thử nghiệm");
    await admin.getByRole("button",{name:"Lưu phân công"}).click();
    await tbm.goto("/withdrawals");
    const plan=tbm.locator("details.card").filter({hasText:round.code});
    await plan.locator("summary").click();
    await plan.getByLabel("Ngày bắt đầu thực hiện",{exact:true}).fill(new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Ho_Chi_Minh"}).format(new Date()));
    await plan.getByLabel("Căn cứ kế hoạch Khoa",{exact:true}).fill("Kế hoạch ngày bắt đầu giả lập");
    await plan.getByRole("button",{name:"Lưu ngày bắt đầu"}).click();
    await expect(tbm.getByRole("status")).toContainText("Đã ghi nhận ngày bắt đầu");
    await students[0].goto("/withdrawals");
    await students[0].getByText("Lập yêu cầu xin thôi KLTN",{exact:true}).click();
    await students[0].getByLabel("Lý do xin thôi").fill("Lý do giả lập: xin chuyển sang học phần thay thế.");
    await students[0].getByLabel(/Tôi đề nghị chuyển sang học phần thay thế/).check();
    await students[0].getByRole("button",{name:"Gửi đơn đến điều phối đợt"}).click();
    await expect(students[0].getByRole("status")).toContainText("Đã gửi yêu cầu đến điều phối đợt");
    const pending=(await read(students[0],"/withdrawals")).requests[0];
    await tbm.goto(`/withdrawals?focus=${pending.id}`);
    await tbm.getByLabel("Lý do xử lý").fill("Chấp thuận yêu cầu xin thôi của sinh viên giả lập.");
    tbm.once("dialog", dialog=>dialog.accept());
    await tbm.getByRole("button",{name:"Xác nhận kết quả"}).click();
    await expect(tbm.getByRole("status")).toContainText("Đã cập nhật kết quả xử lý");
    const item=(await read(students[0],"/withdrawals")).requests[0];
    expect(item.state).toBe("RECORDED");
    expect((await read(students[1],`/theses/${thesis.id}`)).members).toHaveLength(1);
    expect((await students[0].request.get(api+`/theses/${thesis.id}`)).status()).toBe(404);
  } finally {for (const context of contexts) await context.close();}
});
