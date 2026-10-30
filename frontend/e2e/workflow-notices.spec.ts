import {test,expect,type Page} from "@playwright/test";

const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web=`http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;
const api=`http://127.0.0.1:${process.env.KLTN_E2E_API_PORT || "8001"}/api/v1`;
async function read(page:Page,url:string){const r=await page.request.get(api+url);expect(r.status()).toBe(200);return r.json();}
async function post(page:Page,url:string,data?:unknown,version?:number){const auth=await read(page,"/me/context");return page.request.post(api+url,{data,headers:{"X-CSRF-Token":auth.csrf_token,...(version===undefined?{}:{"If-Match":String(version)})}});}
const local=(date:Date)=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}-${String(date.getDate()).padStart(2,"0")}T${String(date.getHours()).padStart(2,"0")}:${String(date.getMinutes()).padStart(2,"0")}`;
async function bell(page:Page,text:RegExp){await page.getByRole("button",{name:/^Thông báo, \d+ chưa xem$/}).click();const panel=page.getByRole("dialog",{name:"Thông báo",exact:true});await expect(panel.getByRole("button",{name:text})).toBeVisible();await panel.getByRole("button",{name:text}).click();}
function pdf(){
  const content="BT /F1 16 Tf 60 700 Td (CUON BAO CAO KLTN - SYNTHETIC DEMO) Tj ET";
  const objects=["<< /Type /Catalog /Pages 2 0 R >>","<< /Type /Pages /Kids [3 0 R] /Count 1 >>","<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>","<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",`<< /Length ${content.length} >>\nstream\n${content}\nendstream`];
  let value="%PDF-1.4\n";const offsets=[0];objects.forEach((item,i)=>{offsets.push(Buffer.byteLength(value));value+=`${i+1} 0 obj\n${item}\nendobj\n`;});const xref=Buffer.byteLength(value);value+=`xref\n0 6\n0000000000 65535 f \n${offsets.slice(1).map(offset=>String(offset).padStart(10,"0")+" 00000 n \n").join("")}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;return Buffer.from(value);
}

test("Cuốn báo cáo trước bảo vệ, chuông đúng nhóm/GVHD/TBM và danh sách đề tài dùng chung",async({browser})=>{
  test.setTimeout(180000);
  const actors:{context:Awaited<ReturnType<typeof browser.newContext>>;page:Page}[]=[];
  async function login(key:string){const context=await browser.newContext(),page=await context.newPage();page.setDefaultTimeout(20000);await page.goto(web);await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();actors.push({context,page});return page;}
  try{
    const gv=await login("gv2"),tbm=await login("tbm"),sv=await login("formStudent"),member=await login("formMember"),admin=await login("admin"),other=await login("gv");
    const round=(await read(gv,"/rounds/open"))[0];
    let r=await post(gv,"/topics",{round_id:round.id,title:"DEMO thông báo và cuốn báo cáo KLTN",max_students:2});expect(r.status()).toBe(201);let topic=await r.json();
    topic=await(await post(gv,`/topics/${topic.id}/submit`,undefined,topic.row_version)).json();
    await bell(tbm,/đã gửi đề tài chờ bộ môn duyệt.*DEMO thông báo/);await expect(tbm).toHaveURL(new RegExp(`topics\\?focus=${topic.id}`));
    expect((await post(tbm,`/topics/${topic.id}/department-decision`,{decision:"APPROVE"},topic.row_version)).status()).toBe(200);
    let reg=await(await post(sv,"/topic-registrations",{topic_id:topic.id})).json();
    expect((await post(member,"/topic-registrations",{topic_id:topic.id})).status()).toBe(201);
    reg=await(await post(sv,`/topic-registrations/${reg.id}/submit`)).json();reg=await(await post(gv,`/topic-registrations/${reg.id}/lecturer-decision`,{decision:"ACCEPT"},reg.row_version)).json();expect(reg.state).toBe("FINALIZED");const base=`/theses/${reg.thesis_id}`;
    await tbm.goto(web);
    expect((await post(admin,"/admin/round-assignments",{round_id:round.id,user_id:(await read(tbm,"/me/context")).user_id,assignment_type:"KLTN_COORDINATOR",basis_ref:"Khoa giao điều phối đợt DEMO"})).status()).toBe(201);
    await bell(tbm,/giao nhiệm vụ Điều phối mốc tiến độ/);await expect(tbm).toHaveURL(web+"/account");
    await tbm.goto(web+base+"?section=progress");
    const deadlines=tbm.locator("section.card").filter({has:tbm.getByRole("heading",{name:"Hạn nộp tài liệu theo đợt",exact:true})});
    await deadlines.getByLabel("Loại tài liệu",{exact:true}).selectOption("REPORT");await deadlines.getByLabel("Hạn mới (giờ Việt Nam)",{exact:true}).fill(local(new Date(Date.now()+7*86400000)));await deadlines.getByLabel("Căn cứ / lý do",{exact:true}).fill("Khoa nhận cuốn báo cáo KLTN trước bảo vệ để chuẩn bị đối chiếu");await deadlines.getByRole("button",{name:"Thiết lập cho cả đợt",exact:true}).click();await expect(tbm.getByRole("status").filter({hasText:"Đã thiết lập hạn tài liệu"})).toBeVisible();
    await sv.goto(web+base+"?section=documents");await sv.getByLabel("Loại tài liệu",{exact:true}).selectOption("REPORT");await sv.getByLabel("Tên tài liệu",{exact:true}).fill("Cuốn báo cáo KLTN trước bảo vệ DEMO");await sv.getByRole("button",{name:"Tạo hồ sơ tài liệu",exact:true}).click();
    const card=sv.locator("article.card").filter({has:sv.getByRole("heading",{name:"Cuốn báo cáo KLTN trước bảo vệ DEMO",exact:true})});await card.getByLabel(/Nộp phiên bản mới/).setInputFiles({name:"cuon-bao-cao-demo.pdf",mimeType:"application/pdf",buffer:pdf()});await card.getByRole("button",{name:"Nộp tài liệu",exact:true}).click();await expect(card.getByText(/Phiên bản 1 · cuon-bao-cao-demo.pdf/)).toBeVisible();
    await bell(gv,/đã nộp.*Cuốn báo cáo/);await expect(gv).toHaveURL(new RegExp(`${reg.thesis_id}.*section=documents`));
    const gvCard=gv.locator("article.card").filter({has:gv.getByRole("heading",{name:"Cuốn báo cáo KLTN trước bảo vệ DEMO",exact:true})});await gvCard.getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();const modal=gv.getByRole("dialog");await modal.getByLabel("Nhận xét tổng quát",{exact:true}).fill("GVHD đã kiểm tra cuốn báo cáo DEMO, giữ bản này để đối chiếu");await modal.getByLabel("Kết quả",{exact:true}).selectOption("ACCEPT");await modal.getByRole("button",{name:"Hoàn thành và gửi góp ý",exact:true}).click();await expect(modal).toHaveCount(0);
    for(const student of [sv,member]){await bell(student,/tiếp nhận.*Cuốn báo cáo/);await expect(student).toHaveURL(new RegExp(`${reg.thesis_id}.*section=documents`));await expect(student.getByText("GVHD đã kiểm tra cuốn báo cáo DEMO, giữ bản này để đối chiếu",{exact:true})).toBeVisible();}
    await sv.screenshot({path:test.info().outputPath("final-report-student.png"),fullPage:true});
    // Weekly progress is a separate private workflow.
    r=await post(tbm,base+"/milestones",{code:"PRIVATE_WEEK",title:"Mốc báo cáo tuần riêng",due_at:new Date(Date.now()+86400000).toISOString()});expect(r.status()).toBe(201);const milestone=await r.json();
    await sv.goto(web+base+"?section=progress");await sv.getByLabel("Mốc báo cáo",{exact:true}).selectOption(milestone.id);await sv.getByLabel("Kết quả, khó khăn và kế hoạch",{exact:true}).fill("Nội dung báo cáo tuần chỉ nhóm và GVHD được xem");await sv.getByLabel("Tiến độ tự báo cáo (%)",{exact:true}).fill("45");await sv.getByRole("button",{name:"Gửi báo cáo",exact:true}).click();await expect(sv.getByText("Nội dung báo cáo tuần chỉ nhóm và GVHD được xem",{exact:true})).toBeVisible();
    await bell(gv,/đã nộp báo cáo tiến độ.*DEMO thông báo/);await expect(gv).toHaveURL(new RegExp(`${reg.thesis_id}.*section=progress`));await expect(gv.getByText("Nội dung báo cáo tuần chỉ nhóm và GVHD được xem",{exact:true})).toBeVisible();
    for(const person of [tbm,admin,other]){const inbox=await read(person,"/notifications?limit=100");expect(inbox.items.some((item:any)=>item.message.includes("đã nộp báo cáo tiến độ"))).toBe(false);expect((await person.request.get(api+base+"/progress-reports")).status()).toBe(person===tbm?403:404);}
    await tbm.goto(web+base+"?section=progress");await expect(tbm.getByText("Nội dung báo cáo tuần chỉ nhóm và GVHD được xem",{exact:true})).toHaveCount(0);await expect(tbm.getByText(/Nội dung báo cáo, minh chứng và nhận xét riêng chỉ nhóm/)).toBeVisible();
    await admin.goto(web+"/topics");await expect(admin.getByRole("heading",{name:"Đề tài",exact:true})).toBeVisible();await expect(admin.getByText("DEMO thông báo và cuốn báo cáo KLTN",{exact:true}).first()).toBeVisible();await expect(admin.getByRole("button",{name:"Tạo đề tài",exact:true})).toHaveCount(0);
    await sv.screenshot({path:test.info().outputPath("private-progress-student.png"),fullPage:true});await admin.screenshot({path:test.info().outputPath("admin-public-topics.png"),fullPage:true});
  }finally{for(const actor of actors)await actor.context.close();}
});
