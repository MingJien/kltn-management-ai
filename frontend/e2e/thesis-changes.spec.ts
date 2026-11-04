import {test,expect,type Page} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "node:path";
const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON||"{}");
const api=`http://127.0.0.1:${process.env.KLTN_E2E_API_PORT||"8001"}/api/v1`;
async function login(page:Page,key:string) {
  await page.goto("/");await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
}
async function read(page:Page,path:string) {
  const r=await page.request.get(api+path);expect(r.status(),await r.text()).toBe(200);return r.json();
}
async function mutate(page:Page,path:string,body:unknown,version?:number,method="POST") {
  const context=await read(page,"/me/context");
  const r=await page.request.fetch(api+path,{method,data:body,headers:{"X-CSRF-Token":context.csrf_token,...(version?{"If-Match":String(version)}:{})}});
  expect(r.ok(),await r.text()).toBeTruthy();return r.status()===204?undefined:r.json();
}
test("Đổi đề tài có đồng ý cả nhóm và gia hạn riêng, bố cục ở 320–1920px",async({browser})=>{
  test.setTimeout(180000);
  const contexts=await Promise.all(["admin","tbm","gv","nv6Student","nv6Member"].map(async key=>{
    const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(15000);await login(page,key);return {context,page};
  }));
  const [admin,tbm,gv,sv,peer]=contexts.map(c=>c.page);
  try {
    const round=(await read(gv,"/rounds/open"))[0];
    const head=(await read(tbm,"/me/context")).user_id;
    const assignments=await read(admin,"/admin/round-assignments");
    if(!assignments.some((a:{user_id:string;round_id:string;assignment_type:string})=>a.user_id===head&&a.round_id===round.id&&a.assignment_type==="KLTN_COORDINATOR"))
      await mutate(admin,"/admin/round-assignments",{round_id:round.id,user_id:head,assignment_type:"KLTN_COORDINATOR",basis_ref:"Synthetic change QA coordination"});
    let topic=await mutate(gv,"/topics",{round_id:round.id,title:"Synthetic change workflow and group approvals",description:"Synthetic objectives for a well scoped thesis",max_students:2});
    topic=await mutate(gv,`/topics/${topic.id}/submit`,{},topic.row_version);
    await mutate(tbm,`/topics/${topic.id}/department-decision`,{decision:"APPROVE"},topic.row_version);
    let reg=await mutate(sv,"/topic-registrations",{topic_id:topic.id});
    await mutate(peer,"/topic-registrations",{topic_id:topic.id});
    reg=await mutate(sv,`/topic-registrations/${reg.id}/submit`,{});
    reg=await mutate(gv,`/topic-registrations/${reg.id}/lecturer-decision`,{decision:"ACCEPT"},reg.row_version);
    const thesis=reg.thesis_id;
    const plan=(await read(tbm,"/withdrawals")).rounds.find((r:{id:string})=>r.id===round.id);
    if(!plan.starts_on)await mutate(tbm,`/withdrawal-rounds/${round.id}/start`,{
      starts_on:new Date().toLocaleDateString("en-CA",{timeZone:"Asia/Ho_Chi_Minh"}),reference:"Synthetic execution start"},
      plan.row_version,"PUT");

    await sv.goto(`/changes?thesis=${thesis}`);
    await sv.getByRole("button",{name:"Đề nghị đổi đề tài",exact:true}).click();
    let dialog=sv.getByRole("dialog");
    await dialog.getByLabel("Tên đề tài đề nghị",{exact:true}).fill("Synthetic revised scope with consent");
    await dialog.getByLabel("Mục tiêu và phạm vi mới",{exact:true}).fill("Build and evaluate the synthetic full workflow in scope.");
    await dialog.getByLabel("Lý do thay đổi",{exact:true}).fill("Revise the synthetic scope to fit the group.");
    await dialog.getByLabel("Tôi đồng ý nội dung đề nghị và việc cập nhật hồ sơ sau khi được duyệt.").check();
    await sv.setViewportSize({width:390,height:900});
    await expect.poll(()=>sv.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
    await sv.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,"change-dialog-mobile.png"),fullPage:true});
    const dialogAxe=await new AxeBuilder({page:sv}).include(".dialog").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
    expect(dialogAxe.violations).toEqual([]);
    await dialog.getByRole("button",{name:"Gửi yêu cầu",exact:true}).click();
    await expect(dialog).toHaveCount(0);
    await expect(sv.getByRole("status")).toContainText("Đã lưu");

    await peer.goto(`/changes?thesis=${thesis}`);
    await peer.getByRole("button",{name:"Xác nhận nguyện vọng",exact:true}).click();
    await peer.getByRole("dialog").getByRole("button",{name:"Xác nhận",exact:true}).click();
    await expect(peer.getByRole("dialog")).toHaveCount(0);

    await gv.goto(`/changes?thesis=${thesis}`);
    await gv.getByRole("button",{name:"GVHD hiện tại xem xét",exact:true}).click();
    await gv.getByLabel("Ý kiến và căn cứ",{exact:true}).fill("The revised academic scope is feasible.");
    await gv.getByRole("dialog").getByRole("button",{name:"Xác nhận",exact:true}).click();
    await expect(gv.getByRole("dialog")).toHaveCount(0);

    await tbm.goto(`/changes?thesis=${thesis}`);
    await tbm.getByRole("button",{name:"Bộ môn xét duyệt",exact:true}).click();
    await tbm.getByLabel("Ý kiến và căn cứ",{exact:true}).fill("Department approves the agreed synthetic revision.");
    await tbm.getByRole("dialog").getByRole("button",{name:"Xác nhận",exact:true}).click();
    await expect(tbm.getByRole("dialog")).toHaveCount(0);
    await tbm.getByRole("combobox",{name:"Trạng thái yêu cầu",exact:true}).selectOption("ALL");
    await expect(tbm.locator(".change-status").filter({hasText:"Đã chấp thuận"})).toBeVisible();

    await mutate(tbm,`/theses/${thesis}/document-deadlines`,{document_type:"REPORT",
      due_at:new Date(Date.now()+7*86400000).toISOString(),reason:"Synthetic original report schedule"});
    await tbm.reload();
    await tbm.getByRole("button",{name:"Ghi nhận gia hạn",exact:true}).click();
    dialog=tbm.getByRole("dialog");
    await dialog.getByLabel("Ngày quyết định",{exact:true}).fill(new Date().toLocaleDateString("en-CA",{timeZone:"Asia/Ho_Chi_Minh"}));
    const extended=new Date(Date.now()+30*86400000+7*3600000).toISOString().slice(0,16);
    await dialog.getByLabel("Hạn mới (giờ Việt Nam)",{exact:true}).fill(extended);
    await dialog.getByLabel("Số hoặc căn cứ quyết định",{exact:true}).fill("QD-SYN-EXTENSION-01");
    await dialog.getByLabel("Lý do gia hạn",{exact:true}).fill("Synthetic external decision grants additional time.");
    await dialog.getByLabel("Tôi đã đối chiếu quyết định và xác nhận các thông tin được ghi nhận.").check();
    await dialog.getByRole("button",{name:"Ghi nhận quyết định",exact:true}).click();
    await expect(dialog).toHaveCount(0);
    await expect(tbm.getByText("Đã ghi nhận một lần",{exact:true})).toBeVisible();

    await sv.reload();
    await sv.getByRole("combobox",{name:"Trạng thái yêu cầu",exact:true}).selectOption("ALL");
    for(const width of [320,360,390,768,1024,1440,1920]) {
      await sv.setViewportSize({width,height:960});
      await expect(sv.getByRole("heading",{name:"Đổi đề tài & gia hạn",exact:true})).toBeVisible();
      await expect.poll(()=>sv.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
      if(width===360||width===1440)await sv.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,`changes-${width}.png`),fullPage:true});
    }
    const axe=await new AxeBuilder({page:sv}).include(".changes-page").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
    expect(axe.violations).toEqual([]);
  } finally {await Promise.allSettled(contexts.map(item=>item.context.close()));}
});

test("Admin gia hạn đăng ký và mở lại đợt đóng với xác nhận, có lịch sử",async({browser})=>{
  const context=await browser.newContext();const page=await context.newPage();
  try {
    await login(page,"admin");
    await mutate(page,"/admin/rounds",{academic_year_code:"2026-2027",year_starts_on:"2026-09-01",year_ends_on:"2027-08-31",
      code:"SYN-EXT-UI",round_type:"SUPPLEMENTARY",opens_at:new Date(Date.now()-86400000).toISOString(),
      closes_at:new Date(Date.now()+2*86400000).toISOString(),basis_ref:"Synthetic registration schedule"});
    let row=(await read(page,"/admin/rounds")).find((r:{code:string})=>r.code==="SYN-EXT-UI");
    await mutate(page,`/admin/rounds/${row.id}`,{state:"OPEN",reason:"Synthetic opening"},row.row_version,"PATCH");
    row=(await read(page,"/admin/rounds")).find((r:{code:string})=>r.code==="SYN-EXT-UI");
    await mutate(page,`/admin/rounds/${row.id}`,{state:"CLOSED",reason:"Synthetic closure"},row.row_version,"PATCH");
    await page.goto("/rounds");
    const card=page.locator(".account-list__row").filter({hasText:"SYN-EXT-UI"});
    await card.getByRole("button",{name:"Gia hạn và mở lại",exact:true}).click();
    const dialog=page.getByRole("dialog");
    await dialog.getByLabel("Hạn đăng ký mới (giờ Việt Nam)",{exact:true}).fill(new Date(Date.now()+4*86400000+7*3600000).toISOString().slice(0,16));
    await dialog.getByLabel("Căn cứ / số văn bản",{exact:true}).fill("QD-SYN-OPEN-01");
    await dialog.getByLabel("Lý do gia hạn",{exact:true}).fill("Synthetic additional registration intake");
    await expect(dialog.getByRole("button",{name:"Xác nhận gia hạn",exact:true})).toBeDisabled();
    await dialog.getByLabel("Tôi xác nhận mở nhận đăng ký trở lại đến hạn mới.").check();
    await dialog.getByRole("button",{name:"Xác nhận gia hạn",exact:true}).click();
    await expect(dialog).toHaveCount(0);
    await card.getByText("Lịch sử đợt",{exact:true}).click();
    await expect(card.getByText("QD-SYN-OPEN-01",{exact:true})).toBeVisible();
    await page.setViewportSize({width:360,height:900});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
  } finally {await context.close();}
});
