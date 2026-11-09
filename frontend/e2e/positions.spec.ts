import {test,expect,type Page} from "@playwright/test";

const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON||"{}");
const api="http://127.0.0.1:"+(process.env.KLTN_E2E_API_PORT||"8001")+"/api/v1";
async function login(page:Page,key:string){
  await page.goto("/");await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
}
async function read(page:Page,url:string){const response=await page.request.get(api+url);expect(response.status()).toBe(200);return response.json();}
async function refresh(page:Page){await page.bringToFront();await page.evaluate(()=>window.dispatchEvent(new Event("focus")));}

test("Admin bổ nhiệm/thay người/thu hồi TBM; sidebar và quyền duyệt đổi đúng thời gian",async({browser})=>{
  test.setTimeout(180000);
  const adminContext=await browser.newContext(),headContext=await browser.newContext(),lecturerContext=await browser.newContext();
  try{
    const admin=await adminContext.newPage(),head=await headContext.newPage(),lecturer=await lecturerContext.newPage();
    for(const page of [admin,head,lecturer])page.setDefaultTimeout(15000);
    await login(admin,"admin");await login(head,"tbm");await login(lecturer,"gv2");
    const headInfo=await read(head,"/me/context"),nextInfo=await read(lecturer,"/me/context");
    expect(headInfo.department_id).toBe(nextInfo.department_id);
    await admin.getByRole("link",{name:"Phân công và chức vụ",exact:true}).click();
    await expect(admin.getByRole("link",{name:"Phân công theo đợt",exact:true})).toHaveAttribute("aria-current","page");
    await admin.getByRole("link",{name:"Chức vụ và phạm vi",exact:true}).click();
    await expect(admin.getByRole("link",{name:"Chức vụ và phạm vi",exact:true})).toHaveAttribute("aria-current","page");
    await expect(admin.getByRole("heading",{name:"Chức vụ và phạm vi",exact:true})).toBeVisible();
    const appointments=await read(admin,"/admin/positions?department_id="+headInfo.department_id);
    const previous=appointments.items.find((row:any)=>row.lecturer_id===headInfo.lecturer_id && row.status==="EFFECTIVE");
    expect(previous).toBeTruthy();
    await admin.getByLabel("Lọc theo bộ môn",{exact:true}).selectOption(headInfo.department_id);
    await admin.getByRole("button",{name:"Thay người",exact:true}).click();
    await admin.getByLabel("Quyết định cần xử lý",{exact:true}).selectOption(previous.id);
    const form=admin.locator("#position-action-form");
    await form.getByLabel("Giảng viên được bổ nhiệm",{exact:true}).selectOption(nextInfo.lecturer_id);
    await form.getByLabel("Căn cứ / số quyết định",{exact:true}).fill("QĐ DEMO UI thay TBM");
    await form.getByLabel("Nội dung ghi nhận / lý do",{exact:true}).fill("Dữ liệu giả kiểm thử thay người giữ chức vụ");
    await form.getByRole("button",{name:"Xác nhận thay người",exact:true}).click();
    await expect(admin.getByRole("status").filter({hasText:"Đã ghi nhận thay người"})).toBeVisible();
    await refresh(lecturer);await refresh(head);
    await expect(lecturer.getByRole("link",{name:"Duyệt hồ sơ giảng viên",exact:true})).toBeVisible();
    await expect(head.getByRole("link",{name:"Duyệt hồ sơ giảng viên",exact:true})).toHaveCount(0);
    expect((await read(head,"/me/context")).actions).not.toContain("topic:department_decide");
    await lecturer.getByRole("link",{name:"Duyệt hồ sơ giảng viên",exact:true}).click();
    await expect(lecturer.getByRole("heading",{name:"Duyệt hồ sơ giảng viên",exact:true})).toBeVisible();
    const notices=await read(lecturer,"/notifications");
    expect(notices.items.some((row:any)=>row.message.includes("bổ nhiệm Trưởng bộ môn"))).toBeTruthy();
    const afterReplacement=await read(admin,"/admin/positions/available");
    const activeDecision=afterReplacement.find((row:any)=>row.lecturer_id===nextInfo.lecturer_id);
    expect(activeDecision).toBeTruthy();
    await admin.getByRole("button",{name:"Thu hồi chức vụ",exact:true}).click();
    await admin.getByLabel("Quyết định cần xử lý",{exact:true}).selectOption(activeDecision.id);
    await form.getByLabel("Căn cứ / số quyết định",{exact:true}).fill("QĐ DEMO UI thu hồi");
    await form.getByLabel("Nội dung ghi nhận / lý do",{exact:true}).fill("Kết thúc kiểm thử quyền dữ liệu giả");
    await form.getByRole("button",{name:"Xác nhận thu hồi",exact:true}).click();
    await expect(admin.getByRole("status").filter({hasText:"Đã thu hồi bổ nhiệm"})).toBeVisible();
    await refresh(lecturer);
    await expect(lecturer.getByRole("link",{name:"Duyệt hồ sơ giảng viên",exact:true})).toHaveCount(0);
    // Schedule a new decision without granting its rights early.
    await form.getByLabel("Bộ môn bổ nhiệm",{exact:true}).selectOption(headInfo.department_id);
    await form.getByLabel("Giảng viên được bổ nhiệm",{exact:true}).selectOption(headInfo.lecturer_id);
    const tomorrow=new Date(Date.now()+86400000+7*3600000).toISOString().slice(0,16);
    await form.getByLabel("Bắt đầu hiệu lực (giờ Việt Nam)",{exact:true}).fill(tomorrow);
    await form.getByLabel("Căn cứ / số quyết định",{exact:true}).fill("QĐ DEMO UI chờ hiệu lực");
    await form.getByLabel("Nội dung ghi nhận / lý do",{exact:true}).fill("Lịch bổ nhiệm tương lai dùng cho kiểm thử");
    await form.getByRole("button",{name:"Lưu bổ nhiệm",exact:true}).click();
    await expect(admin.getByRole("status").filter({hasText:"Đã ghi nhận bổ nhiệm"})).toBeVisible();
    const scheduled=admin.getByRole("row").filter({hasText:headInfo.lecturer_code}).filter({hasText:"Chờ hiệu lực"});
    await expect(scheduled).toBeVisible();
    await refresh(head);
    expect((await read(head,"/me/context")).actions).not.toContain("topic:department_decide");
    const afterScheduling=await read(admin,"/admin/positions/available");
    const scheduledDecision=afterScheduling.find((row:any)=>row.lecturer_id===headInfo.lecturer_id && row.status==="SCHEDULED");
    expect(scheduledDecision).toBeTruthy();
    await admin.getByRole("button",{name:"Thu hồi chức vụ",exact:true}).click();
    await admin.getByLabel("Quyết định cần xử lý",{exact:true}).selectOption(scheduledDecision.id);
    await form.getByLabel("Căn cứ / số quyết định",{exact:true}).fill("QĐ DEMO UI hủy");
    await form.getByLabel("Nội dung ghi nhận / lý do",{exact:true}).fill("Hủy lịch giả sau khi kiểm tra");
    await form.getByRole("button",{name:"Xác nhận thu hồi",exact:true}).click();
    await expect(admin.getByRole("status").filter({hasText:"Đã thu hồi bổ nhiệm"})).toBeVisible();
    await admin.locator(".positions-history details").filter({hasText:nextInfo.display_name}).locator("summary").click();
    await expect(admin.getByText("QĐ DEMO UI thu hồi",{exact:false})).toBeVisible();
    expect((await lecturer.request.get(api+"/admin/positions")).status()).toBe(403);
  }finally{await Promise.allSettled([adminContext.close(),headContext.close(),lecturerContext.close()]);}
});
