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
test("Đổi đề tài và gia hạn theo quyết định, bố cục 320–1920px",async({browser})=>{
  test.setTimeout(180000);
  const contexts=await Promise.all(["admin","tbm","gv","nv6Student","nv6Member"].map(async key=>{
    const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(15000);await login(page,key);return {context,page};
  }));
  const [admin,tbm,gv,sv,peer]=contexts.map(c=>c.page);
  try {
    const round=(await read(gv,"/rounds/open")).find((item:{code:string})=>item.code==="SYN-DEMO");
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
    // Simulate a stale request to verify that the user sees the actionable reason.
    await sv.route("**/api/v1/theses/*/change-requests",route=>route.fulfill({status:409,
      contentType:"application/json",body:JSON.stringify({detail:"Nhóm đã có yêu cầu đổi đề tài chờ xử lý"})}),{times:1});
    await dialog.getByRole("button",{name:"Gửi yêu cầu",exact:true}).click();
    await expect(dialog.getByRole("alert")).toHaveText("Nhóm đã có yêu cầu đổi đề tài chờ xử lý");
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
    await sv.reload();
    await sv.getByRole("button",{name:"Xin gia hạn KLTN",exact:true}).click();
    await sv.getByRole("button",{name:"Xin gia hạn KLTN",exact:true}).last().click();
    dialog=sv.getByRole("dialog");
    const extended=new Date(Date.now()+30*86400000+7*3600000).toISOString().slice(0,16);
    await dialog.getByLabel("Lý do xin gia hạn",{exact:true}).fill("Synthetic request to complete the academic work.");
    await dialog.getByLabel("Tôi đồng ý xin gia hạn và hiểu rằng các thành viên khác phải tự xác nhận nguyện vọng.").check();
    await dialog.getByRole("button",{name:"Gửi yêu cầu gia hạn",exact:true}).click();
    await expect(dialog).toHaveCount(0);
    await peer.reload();
    await peer.getByRole("button",{name:"Xin gia hạn KLTN",exact:true}).click();
    await peer.getByRole("button",{name:"Xác nhận xin gia hạn",exact:true}).click();
    await peer.getByRole("dialog").getByRole("button",{name:"Xác nhận",exact:true}).click();
    await expect(peer.getByRole("dialog")).toHaveCount(0);
    await gv.reload();
    await gv.getByRole("button",{name:"Xin gia hạn KLTN",exact:true}).click();
    await gv.getByRole("button",{name:"GVHD cho ý kiến",exact:true}).click();
    await gv.getByRole("dialog").getByLabel("Ý kiến và căn cứ",{exact:true}).fill("The group can complete the thesis after extension.");
    await gv.getByRole("dialog").getByRole("button",{name:"Xác nhận",exact:true}).click();
    await expect(gv.getByRole("dialog")).toHaveCount(0);
    await tbm.reload();
    await tbm.getByRole("button",{name:"Xin gia hạn KLTN",exact:true}).click();
    await tbm.getByRole("button",{name:"TBM xét gia hạn",exact:true}).click();
    dialog=tbm.getByRole("dialog");
    await dialog.getByLabel("Kết quả",{exact:true}).selectOption("APPROVE");
    await dialog.getByLabel("Ngày quyết định",{exact:true}).fill(new Date().toLocaleDateString("en-CA",{timeZone:"Asia/Ho_Chi_Minh"}));
    await dialog.getByLabel("Bắt đầu gia hạn theo quyết định (giờ Việt Nam)",{exact:true}).fill(new Date(Date.now()+7*86400000+7*3600000).toISOString().slice(0,16));
    const untilInput=dialog.getByLabel("Hạn mới được duyệt (giờ Việt Nam)",{exact:true});
    await untilInput.fill(new Date(Date.now()+220*86400000+7*3600000).toISOString().slice(0,16));
    expect(await untilInput.evaluate((element:HTMLInputElement)=>element.validity.rangeOverflow)).toBe(true);
    await untilInput.fill(extended);
    await dialog.getByLabel("Số hoặc căn cứ quyết định",{exact:true}).fill("QD-SYN-EXTENSION-01");
    await dialog.getByLabel("Ý kiến và căn cứ",{exact:true}).fill("Synthetic external decision grants additional time.");
    await dialog.getByLabel("Tôi đã đối chiếu quyết định và mốc thời gian ghi nhận.").check();
    await dialog.getByRole("button",{name:"Xác nhận",exact:true}).click();
    await expect(dialog).toHaveCount(0);
    await expect(tbm.getByText("Đã ghi nhận một lần",{exact:true})).toBeVisible();
    await expect(tbm.getByText("Chờ Khoa xếp kỳ bảo vệ tiếp theo trong thời hạn gia hạn được duyệt.",{exact:true})).toBeVisible();
    await expect(tbm.getByText("QD-SYN-EXTENSION-01",{exact:true}).last()).toBeVisible();
    await sv.reload();
    await sv.getByRole("button",{name:"Xin gia hạn KLTN",exact:true}).click();
    await expect(sv.getByText("Chờ Khoa xếp kỳ bảo vệ tiếp theo trong thời hạn gia hạn được duyệt.",{exact:true})).toBeVisible();


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

test("Tách cá nhân giữ nhóm cũ và GVHD đặt mốc riêng cho từng khóa luận",async({browser})=>{
  test.setTimeout(180000);
  const contexts=await Promise.all(["tbm","gv","formStudent","formMember"].map(async key=>{
    const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(15000);await login(page,key);return {context,page};
  }));
  const [tbm,gv,sv,peer]=contexts.map(c=>c.page);
  try {
    const round=(await read(gv,"/rounds/open")).find((item:{code:string})=>item.code==="SYN-DEMO");
    async function publish(title:string,capacity:number) {
      let row=await mutate(gv,"/topics",{round_id:round.id,title,description:"Synthetic UI fixture for personal topic transfer",max_students:capacity});
      row=await mutate(gv,`/topics/${row.id}/submit`,{},row.row_version);
      return mutate(tbm,`/topics/${row.id}/department-decision`,{decision:"APPROVE"},row.row_version);
    }
    const topic=await publish("Synthetic source group retained after individual change",2);
    const target=await publish("Synthetic personal destination after individual change",1);
    let reg=await mutate(sv,"/topic-registrations",{topic_id:topic.id});
    await mutate(peer,"/topic-registrations",{topic_id:topic.id});
    reg=await mutate(sv,`/topic-registrations/${reg.id}/submit`,{});
    reg=await mutate(gv,`/topic-registrations/${reg.id}/lecturer-decision`,{decision:"ACCEPT"},reg.row_version);
    const source=reg.thesis_id;
    await sv.goto(`/changes?thesis=${source}`);
    await sv.getByRole("button",{name:"Đề nghị đổi đề tài",exact:true}).click();
    let dialog=sv.getByRole("dialog");
    await dialog.getByLabel("Phạm vi thay đổi",{exact:true}).selectOption("INDIVIDUAL");
    await dialog.getByLabel("Đề tài mới",{exact:true}).selectOption(target.id);
    await dialog.getByLabel("Lý do thay đổi",{exact:true}).fill("Synthetic individual change with remaining member continuing.");
    await dialog.getByLabel("Tôi đồng ý nội dung đề nghị và việc cập nhật hồ sơ sau khi được duyệt.").check();
    await dialog.getByRole("button",{name:"Gửi yêu cầu",exact:true}).click();
    await expect(dialog).toHaveCount(0);
    await peer.goto(`/changes?thesis=${source}`);
    await expect(peer.getByRole("button",{name:"Xác nhận nguyện vọng",exact:true})).toHaveCount(0);
    await gv.goto(`/changes?thesis=${source}`);
    await gv.getByRole("button",{name:"GVHD hiện tại xem xét",exact:true}).click();
    await gv.getByLabel("Ý kiến và căn cứ",{exact:true}).fill("Both theses have a feasible independent academic scope.");
    await gv.getByRole("dialog").getByRole("button",{name:"Xác nhận",exact:true}).click();
    await expect(gv.getByRole("dialog")).toHaveCount(0);
    await tbm.goto(`/changes?thesis=${source}`);
    await tbm.getByRole("button",{name:"Bộ môn xét duyệt",exact:true}).click();
    await tbm.getByLabel("Ý kiến và căn cứ",{exact:true}).fill("Approved separate scope; the remaining member continues the original thesis.");
    await tbm.getByRole("dialog").getByRole("button",{name:"Xác nhận",exact:true}).click();
    await expect(tbm.getByRole("dialog")).toHaveCount(0);
    await sv.reload();
    await sv.getByRole("combobox",{name:"Trạng thái yêu cầu",exact:true}).selectOption("ALL");
    await sv.getByRole("link",{name:"Cập nhật hồ sơ",exact:true}).click();
    await expect(sv).toHaveURL(/\/theses\/.+section=submissions/);
    const destination=sv.url().match(/\/theses\/([^?]+)/)![1];
    expect(destination).not.toBe(source);
    expect((await sv.request.get(api+`/theses/${source}`)).status()).toBe(404);
    expect((await peer.request.get(api+`/theses/${destination}`)).status()).toBe(404);
    expect((await read(peer,`/theses/${source}`)).title).toBe(topic.title);
    async function privateMilestone(thesis:string,title:string) {
      await gv.goto(`/theses/${thesis}?section=progress`);
      await expect(gv.getByRole("heading",{name:"Tạo mốc nội bộ của khóa luận",exact:true})).toBeVisible();
      await gv.getByLabel("Mã mốc",{exact:true}).fill("PRIVATE_WEEK_1");
      await gv.getByLabel("Tên mốc",{exact:true}).fill(title);
      await gv.getByLabel("Hạn nộp (giờ Việt Nam)",{exact:true}).fill(new Date(Date.now()+7*86400000+7*3600000).toISOString().slice(0,16));
      await gv.getByLabel("Tiến độ dự kiến (%)",{exact:true}).fill("40");
      await gv.getByRole("button",{name:"Tạo mốc nội bộ",exact:true}).click();
      await expect(gv.getByRole("heading",{name:title+" · v1",exact:true})).toBeVisible();
    }
    await privateMilestone(source,"Synthetic weekly milestone for remaining member");
    await privateMilestone(destination,"Synthetic weekly milestone for moved member");
    await peer.goto(`/theses/${source}?section=progress`);
    await expect(peer.getByRole("heading",{name:"Synthetic weekly milestone for remaining member · v1",exact:true})).toBeVisible();
    await expect(peer.getByText("Synthetic weekly milestone for moved member",{exact:false})).toHaveCount(0);
    await peer.getByLabel("Mốc báo cáo",{exact:true}).selectOption({label:"Synthetic weekly milestone for remaining member · v1"});
    await peer.getByLabel("Kết quả, khó khăn và kế hoạch",{exact:true}).fill("Synthetic progress on the retained thesis; next step is implementation.");
    await peer.getByLabel("Tiến độ tự báo cáo (%)",{exact:true}).fill("40");
    await peer.getByRole("button",{name:"Gửi báo cáo",exact:true}).click();
    await expect(peer.locator(".progress-report")).toContainText("Synthetic progress on the retained thesis");
    await gv.goto(`/theses/${source}?section=progress`);
    const report=gv.locator(".progress-report");
    await report.getByLabel("Nhận xét / lý do",{exact:true}).fill("Synthetic feedback confirms the work for this thesis only.");
    await report.getByRole("button",{name:"Gửi kết quả",exact:true}).click();
    await expect(report).toContainText("Synthetic feedback confirms the work");
    const headMilestones=await read(tbm,`/theses/${source}/milestones`);
    expect(headMilestones.some((row:{scope:string})=>row.scope==="THESIS")).toBe(false);
    const notices=(await read(tbm,"/notifications")).items;
    expect(notices.some((row:{message:string})=>row.message.includes("Synthetic weekly milestone"))).toBe(false);
    await sv.goto(`/theses/${destination}?section=progress`);
    await expect(sv.getByRole("heading",{name:"Synthetic weekly milestone for moved member · v1",exact:true})).toBeVisible();
    await sv.setViewportSize({width:390,height:900});
    await expect.poll(()=>sv.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
    const overflow=await sv.evaluate(()=>Array.from(document.querySelectorAll('#main-content *')).filter(node=>node.getBoundingClientRect().right>innerWidth+1).slice(0,8).map(node=>({tag:node.tagName,cls:node.className,right:node.getBoundingClientRect().right,text:node.textContent?.slice(0,60)})));
    expect(overflow,"Content must fit the progress screen").toEqual([]);
    await sv.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,"individual-thesis-private-progress.png"),fullPage:true});
  } finally {await Promise.allSettled(contexts.map(item=>item.context.close()));}
});
