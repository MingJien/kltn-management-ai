import {test,expect,type BrowserContext,type Page} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "node:path";

// Cookie sessions, actual API, PostgreSQL and ClamAV. No intercepted or mocked routes.
const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON||"{}");
const web=`http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT||"5174"}`;
const api=`http://127.0.0.1:${process.env.KLTN_E2E_API_PORT||"8001"}/api/v1`;
const output=process.env.KLTN_E2E_RUN_DIR!;
const fixture=process.env.KLTN_E2E_NV6_FILE!;
async function read(page:Page,url:string){const r=await page.request.get(api+url);expect(r.status(),await r.text()).toBe(200);return r.json();}
async function post(page:Page,url:string,data?:unknown,version?:number){
  const auth=await read(page,"/me/context");
  return page.request.post(api+url,{data,headers:{"X-CSRF-Token":auth.csrf_token,...(version?{"If-Match":String(version)}:{})}});
}
async function login(page:Page,key:string){
  await page.goto(web);await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
}

test.describe.serial("NV6 tuần 1 · luồng thật theo từng vai trò",()=>{
  let contexts:BrowserContext[]=[],admin:Page,tbm:Page,advisor:Page,reviewer:Page,student:Page,member:Page,outsider:Page;
  let id:string,base:string,studentMemberIds:string[];
  test.beforeAll(async({browser})=>{
    test.setTimeout(180000);
    const pages=[];
    for(const key of ["admin","tbm","gv2","gv","nv6Student","nv6Member","nv6Outsider"]){
      const context=await browser.newContext();contexts.push(context);const page=await context.newPage();page.setDefaultTimeout(15000);
      await login(page,key);pages.push(page);
    }
    [admin,tbm,advisor,reviewer,student,member,outsider]=pages;
    const round=(await read(advisor,"/rounds/open"))[0];
    let r=await post(advisor,"/topics",{round_id:round.id,title:"NV6 · Phản biện và bảo vệ theo từng sinh viên",max_students:2});
    expect(r.status()).toBe(201);let topic=await r.json();
    topic=await(await post(advisor,`/topics/${topic.id}/submit`,undefined,topic.row_version)).json();
    r=await post(tbm,`/topics/${topic.id}/department-decision`,{decision:"APPROVE"},topic.row_version);expect(r.status()).toBe(200);
    r=await post(student,"/topic-registrations",{topic_id:topic.id,confirm_creator:true});expect(r.status()).toBe(201);let reg=await r.json();
    r=await post(member,"/topic-registrations",{topic_id:topic.id,confirm_creator:true});expect(r.status()).toBe(201);
    reg=await read(student,`/topic-registrations/${reg.id}`);
    r=await post(student,`/topic-registrations/${reg.id}/submit`,undefined,reg.row_version);expect(r.status()).toBe(200);reg=await r.json();
    r=await post(advisor,`/topic-registrations/${reg.id}/lecturer-decision`,{decision:"ACCEPT"},reg.row_version);
    expect(r.status(),await r.text()).toBe(200);id=(await r.json()).thesis_id;base=`/theses/${id}/evaluation`;
    r=await post(admin,"/admin/round-assignments",{round_id:round.id,user_id:(await read(tbm,"/me/context")).user_id,assignment_type:"KLTN_COORDINATOR",basis_ref:"SYNTHETIC NV6 COORDINATOR"});
    expect([200,201]).toContain(r.status());
    r=await post(tbm,`/theses/${id}/document-deadlines`,{document_type:"REPORT",due_at:new Date(Date.now()+7*86400000).toISOString(),reason:"Synthetic report submission deadline"});expect(r.status()).toBe(200);
    r=await post(student,`/theses/${id}/documents`,{document_type:"REPORT",title:"Cuốn báo cáo NV6"});expect(r.status()).toBe(201);const doc=await r.json();
    const csrf=(await read(student,"/me/context")).csrf_token;
    r=await student.request.post(api+`/theses/${id}/documents/${doc.id}/versions`,{data:await (await import("node:fs/promises")).readFile(fixture),headers:{"X-CSRF-Token":csrf,"If-Match":String(doc.row_version),"X-File-Name":"synthetic-nv6-report.pdf","Content-Type":"application/octet-stream"}});
    expect(r.status(),await r.text()).toBe(201);expect((await r.json()).versions[0].scan_state).toBe("CLEAN");
    studentMemberIds=(await read(tbm,base)).members.map((m:{id:string})=>m.id);
    expect(studentMemberIds).toHaveLength(2);
  });
  test.afterAll(async()=>{for(const context of contexts)await context.close();});

  test("TBM phân công, gia hạn; GVPB nhận thông báo, đọc báo cáo, lưu nháp và gửi Mẫu 8",async()=>{
    await tbm.goto(web+`/evaluation/${id}`);
    await tbm.getByRole("button",{name:"Phân công GV",exact:true}).click();
    let dialog=tbm.getByRole("dialog");
    const reviewerContext=await read(reviewer,"/me/context");
    await dialog.getByLabel("Giảng viên phản biện",{exact:true}).selectOption(reviewerContext.lecturer_id);
    await dialog.getByLabel("Căn cứ / số văn bản đối chiếu").fill("SYNTHETIC-QD-NV6-01");
    await dialog.getByLabel("Lý do / ghi chú nghiệp vụ").fill("Bộ môn giao phản biện theo chuyên môn đã đối chiếu");
    await dialog.getByRole("button",{name:"Xác nhận và lưu",exact:true}).click();await expect(dialog).toHaveCount(0);
    await expect(tbm.getByText(reviewerContext.display_name,{exact:true})).toBeVisible();
    await tbm.getByRole("button",{name:"Gia hạn phản biện",exact:true}).click();
    dialog=tbm.getByRole("dialog");await dialog.getByLabel("Căn cứ / số văn bản đối chiếu").fill("SYNTHETIC-GIA-HAN-01");
    await dialog.getByLabel("Lý do / ghi chú nghiệp vụ").fill("Bộ môn điều chỉnh lịch gửi nhận xét phản biện");
    await dialog.getByRole("button",{name:"Xác nhận và lưu",exact:true}).click();await expect(dialog).toHaveCount(0);
    await reviewer.goto(web+"/notifications");
    await reviewer.getByRole("button",{name:/Bạn được giao phản biện khóa luận/}).click();
    await expect(reviewer).toHaveURL(web+`/evaluation/${id}`);
    await reviewer.getByRole("button",{name:"Đọc báo cáo",exact:true}).click();
    await expect(reviewer.getByRole("dialog").locator("canvas")).toBeVisible();
    await reviewer.getByRole("dialog").getByRole("button",{name:"Đóng",exact:true}).click();
    await reviewer.getByLabel("Sinh viên trong hồ sơ").selectOption(studentMemberIds[0]);
    await reviewer.getByRole("button",{name:"Lập phiếu Mẫu 8",exact:true}).click();
    await reviewer.getByRole("dialog").getByRole("button",{name:"Tạo phiếu nháp",exact:true}).click();
    dialog=reviewer.getByRole("dialog");await expect(dialog.getByRole("heading",{name:/Mẫu 8/})).toBeVisible();
    const fields=["1. Hình thức trình bày, kết cấu, bố cục","2. Tính cấp thiết, tổng quan, mục đích, nhiệm vụ, đối tượng, phạm vi, phương pháp và ý nghĩa đề tài","4. Kết quả và đóng góp mới về khoa học","5. Những điểm cần trao đổi với tác giả","6. Đánh giá chung"];
    for(const label of fields)await dialog.getByLabel(label,{exact:false}).fill("Nhận xét phản biện kiểm thử đầy đủ: "+label);
    await dialog.getByRole("button",{name:"Lưu nháp",exact:true}).click();
    await expect(dialog.getByRole("button",{name:"Lưu nháp",exact:true})).toBeDisabled();
    expect((await read(tbm,base)).reviews).toHaveLength(0);
    const export8=reviewer.waitForEvent("download");await dialog.getByRole("button",{name:"Xuất phiếu đã điền để ký",exact:true}).click();
    await (await export8).saveAs(path.join(output,"nv6-mau8-filled.docx"));
    await dialog.getByText("Đính kèm bản quét (tùy chọn)",{exact:true}).click();
    await expect(dialog.getByLabel(/Đính kèm bản đã ký/)).toBeEnabled();
    await dialog.getByLabel(/Đính kèm bản đã ký/).setInputFiles(fixture);
    await expect(dialog.getByText("Đã quét an toàn",{exact:true})).toBeVisible();
    await dialog.getByRole("button",{name:"Kiểm tra và gửi nhận xét",exact:true}).click();
    await dialog.getByRole("checkbox",{name:/Tôi xác nhận nội dung nhận xét này/}).check();
    await dialog.getByRole("button",{name:"Xác nhận gửi nhận xét",exact:true}).click();await expect(dialog).toHaveCount(0);
    expect((await read(tbm,base)).reviews.filter((r:{kind:string})=>r.kind==="REVIEWER")).toHaveLength(1);
    await tbm.getByRole("button",{name:"Làm mới",exact:true}).click();
    await tbm.screenshot({path:path.join(output,"nv6-department-desktop.png"),fullPage:true});
  });

  test("GVHD gửi hai Mẫu 7; TBM xét từng SV; kết quả cá nhân và bản ký được bảo vệ",async()=>{
    for(const memberId of studentMemberIds){
      await advisor.goto(web+`/evaluation/${id}`);
      await advisor.getByLabel("Sinh viên trong hồ sơ").selectOption(memberId);
      await advisor.getByRole("button",{name:"Lập phiếu Mẫu 7",exact:true}).click();
      await advisor.getByRole("dialog").getByRole("button",{name:"Tạo phiếu nháp",exact:true}).click();
      const dialog=advisor.getByRole("dialog");
      for(const label of ["1. Tinh thần, thái độ của sinh viên","2. Sự đáp ứng của nội dung khóa luận","3. Hình thức khóa luận"])await dialog.getByLabel(label,{exact:false}).fill("GVHD xác nhận kết quả và đóng góp riêng của sinh viên. ");
      await dialog.getByLabel("Xác nhận hoàn thành khóa luận",{exact:true}).selectOption("true");
      await dialog.getByLabel("Đề nghị của GVHD",{exact:true}).selectOption("true");
      await dialog.getByRole("button",{name:"Lưu nháp",exact:true}).click();
      await expect(dialog.getByRole("button",{name:"Lưu nháp",exact:true})).toBeDisabled();
      await expect(dialog.getByRole("button",{name:"Xuất phiếu đã điền để ký",exact:true})).toBeEnabled();
      const export7=advisor.waitForEvent("download");await dialog.getByRole("button",{name:"Xuất phiếu đã điền để ký",exact:true}).click();
      await (await export7).saveAs(path.join(output,`nv6-mau7-${memberId}-filled.docx`));
      await dialog.getByText("Đính kèm bản quét (tùy chọn)",{exact:true}).click();
      await expect(dialog.getByLabel(/Đính kèm bản đã ký/)).toBeEnabled();
      await dialog.getByLabel(/Đính kèm bản đã ký/).setInputFiles(fixture);
      await expect(dialog.getByText("Đã quét an toàn",{exact:true})).toBeVisible();
      await dialog.getByRole("button",{name:"Kiểm tra và gửi nhận xét",exact:true}).click();
      await dialog.getByRole("checkbox",{name:/Tôi xác nhận nội dung nhận xét này/}).check();
      await dialog.getByRole("button",{name:"Xác nhận gửi nhận xét",exact:true}).click();await expect(dialog).toHaveCount(0);
      await tbm.goto(web+`/evaluation/${id}`);await tbm.getByLabel("Sinh viên trong hồ sơ").selectOption(memberId);
      await tbm.getByRole("button",{name:"Xét và lưu điều kiện",exact:true}).click();
      const check=tbm.getByRole("dialog");await check.getByLabel("Tình trạng kỷ luật theo nguồn đã đối chiếu").selectOption("CLEAR");
      await check.getByLabel("Căn cứ / số văn bản đối chiếu").fill("SYNTHETIC-CTSV-01");
      await check.getByLabel("Lý do / ghi chú nghiệp vụ").fill("Đã đối chiếu quy định, tình trạng kỷ luật và văn bản đồng ý của GVHD");
      await expect(check.getByText("Dự kiến: đủ điều kiện dự bảo vệ",{exact:true})).toBeVisible();
      await check.getByRole("button",{name:"Xác nhận và lưu",exact:true}).click();await expect(check).toHaveCount(0);
    }
    expect((await read(tbm,base)).state).toBe("READY_FOR_DEFENSE");
    for(const page of [student,member]){
      await page.goto(web+`/evaluation/${id}`);
      await expect(page.getByText("Đủ điều kiện",{exact:true})).toBeVisible();
      expect((await page.getByLabel("Sinh viên trong hồ sơ").locator("option").count())).toBe(1);
      const own=await read(page,base);expect(own.members).toHaveLength(1);
      expect(own.reviews.every((r:{thesis_member_id:string})=>r.thesis_member_id===own.members[0].id)).toBe(true);
      await expect(page.getByRole("button",{name:"Lập phiếu Mẫu 7",exact:true})).toHaveCount(0);
    }
    expect((await outsider.request.get(api+base)).status()).toBe(404);
    expect((await admin.request.get(api+base)).status()).toBe(404);
    const first=await read(student,base),other=await read(member,base);
    const ownReview=first.reviews.find((r:{kind:string})=>r.kind==="ADVISOR");
    expect((await member.request.get(api+base+`/reviews/${ownReview.id}/signed-copy`)).status()).toBe(404);
    const allowed=await student.request.get(api+base+`/reviews/${ownReview.id}/signed-copy`);expect(allowed.status()).toBe(200);
    await student.screenshot({path:path.join(output,"nv6-student-desktop.png"),fullPage:true});
    expect(other.eligibility_history.every((h:{thesis_member_id:string})=>h.thesis_member_id===other.members[0].id)).toBe(true);
  });

  test("Mở xét lại, thu hồi quyền, tìm kiếm và UI mobile có thể bàn giao",async()=>{
    await tbm.goto(web+`/evaluation/${id}`);await tbm.getByRole("button",{name:"Mở xét lại hồ sơ",exact:true}).click();
    let dialog=tbm.getByRole("dialog");await dialog.getByLabel("Lý do / ghi chú nghiệp vụ").fill("Cần đối chiếu bản báo cáo chỉnh sửa và xét lại điều kiện");
    await dialog.getByRole("button",{name:"Xác nhận và lưu",exact:true}).click();await expect(dialog).toHaveCount(0);
    expect((await read(tbm,base)).state).toBe("IN_PROGRESS");
    await tbm.getByRole("button",{name:"Thu hồi phân công",exact:true}).click();dialog=tbm.getByRole("dialog");
    await dialog.getByLabel("Lý do / ghi chú nghiệp vụ").fill("Thay đổi phân công phản biện theo quyết định mới của bộ môn");
    await dialog.getByRole("button",{name:"Xác nhận và lưu",exact:true}).click();await expect(dialog).toHaveCount(0);
    expect((await reviewer.request.get(api+base)).status()).toBe(404);
    const notices=await read(reviewer,"/notifications?limit=100");
    expect(notices.items.some((n:{url:string})=>n.url===`/evaluation/${id}`)).toBe(false);
    expect(notices.items.some((n:{message:string})=>n.message.includes("thu hồi phân công phản biện"))).toBe(true);
    await tbm.goto(web+"/evaluation");await tbm.getByLabel("Tìm khóa luận, sinh viên hoặc đợt").fill("NV6 · Phản biện");
    await expect(tbm.getByRole("link",{name:"NV6 · Phản biện và bảo vệ theo từng sinh viên",exact:true})).toBeVisible();
    await student.setViewportSize({width:390,height:844});await student.goto(web+`/evaluation/${id}`);
    await expect(student.getByRole("heading",{name:"Điều kiện dự bảo vệ",exact:true})).toBeVisible();
    expect(await student.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    const axe=await new AxeBuilder({page:student}).include(".evaluation-page").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
    expect(axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))).toEqual([]);
    await student.screenshot({path:path.join(output,"nv6-student-mobile.png"),fullPage:true});
  });
  test("Gửi nhận xét không bắt bản quét; cán bộ được giao nhận giấy đúng mã xuất",async()=>{
    await advisor.goto(web+"/evaluation/"+id);
    await advisor.getByLabel("Sinh viên trong hồ sơ").selectOption(studentMemberIds[0]);
    await advisor.getByRole("button",{name:"Lập phiếu Mẫu 7",exact:true}).click();
    await advisor.getByRole("dialog").getByLabel("Lý do lập phiếu / phiên bản sửa",{exact:true}).fill("Lập phiên bản nhận xét mới để thử tiếp nhận giấy không tải bản quét");
    await advisor.getByRole("dialog").getByRole("button",{name:"Tạo phiếu nháp",exact:true}).click();
    let dialog=advisor.getByRole("dialog");
    for(const label of ["1. Tinh thần, thái độ của sinh viên","2. Sự đáp ứng của nội dung khóa luận","3. Hình thức khóa luận"])
      await dialog.getByLabel(label,{exact:false}).fill("Nhận xét đã xác thực tài khoản, đối chiếu bản giấy sau khi ký.");
    await dialog.getByLabel("Xác nhận hoàn thành khóa luận",{exact:true}).selectOption("true");
    await dialog.getByLabel("Đề nghị của GVHD",{exact:true}).selectOption("true");
    await dialog.getByRole("button",{name:"Lưu nháp",exact:true}).click();
    await expect(dialog.getByRole("button",{name:"Lưu nháp",exact:true})).toBeDisabled();
    const exported=advisor.waitForEvent("download");
    await dialog.getByRole("button",{name:"Xuất phiếu đã điền để ký",exact:true}).click();
    const download=await exported;expect(download.suggestedFilename()).toMatch(/^Mau-07-GVHD-.+-v\d+\.docx$/);
    await download.saveAs(path.join(output,"nv6-paper-review.docx"));
    await dialog.getByRole("button",{name:"Kiểm tra và gửi nhận xét",exact:true}).click();
    await dialog.getByRole("checkbox",{name:/Tôi xác nhận nội dung nhận xét này/}).check();
    await dialog.getByRole("button",{name:"Xác nhận gửi nhận xét",exact:true}).click();
    await expect(dialog).toHaveCount(0);
    const submitted=(await read(advisor,base)).reviews.filter((r:any)=>r.kind==="ADVISOR"&&r.thesis_member_id===studentMemberIds[0]).sort((a:any,b:any)=>b.version_no-a.version_no)[0];
    expect(submitted.signed_file).toBeNull();
    let view=await read(tbm,base),memberState=view.members.find((m:any)=>m.id===studentMemberIds[0]);
    expect(memberState.eligibility.conditions.find((c:any)=>c.key==="completion").met).toBe(true);
    expect(memberState.eligibility.conditions.find((c:any)=>c.key==="consent").met).toBe(false);
    const round=view.round_id,receiver=(await read(reviewer,"/me/context")).user_id;
    await admin.goto(web+"/administration/assignments");
    const assignment=admin.locator("section.card").filter({has:admin.getByRole("heading",{name:"Phân công theo đợt",exact:true})});
    await assignment.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("REVIEW_RECORDS_MANAGER");
    await assignment.getByRole("combobox",{name:"Đợt",exact:true}).selectOption(round);
    await assignment.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption(receiver);
    await assignment.getByLabel("Căn cứ phân công").fill("DEMO giao tiếp nhận hồ sơ Mẫu 7–8");
    await assignment.getByRole("button",{name:"Lưu phân công",exact:true}).click();
    await expect(admin.getByRole("status").filter({hasText:"Đã lưu phân công"})).toBeVisible();
    await reviewer.bringToFront();await reviewer.evaluate(()=>window.dispatchEvent(new Event("focus")));
    await reviewer.getByRole("link",{name:"Tiếp nhận hồ sơ phản biện",exact:true}).click();
    await reviewer.getByRole("link",{name:"NV6 · Phản biện và bảo vệ theo từng sinh viên",exact:true}).click();
    await reviewer.getByLabel("Sinh viên trong hồ sơ").selectOption(studentMemberIds[0]);
    const card=reviewer.locator(".evaluation-review").filter({hasText:"Mẫu 7 · GVHD · Phiếu v"+submitted.version_no});
    await card.getByRole("button",{name:"Xác nhận văn bản đã ký",exact:true}).click();
    dialog=reviewer.getByRole("dialog");
    await dialog.getByLabel("Số / căn cứ tiếp nhận bản giấy",{exact:true}).fill("SO-TIEP-NHAN-DEMO-2026/01");
    await dialog.getByRole("checkbox",{name:/Tôi xác nhận văn bản đã có chữ ký/}).check();
    await dialog.getByRole("button",{name:"Lưu xác nhận văn bản đã ký",exact:true}).click();
    await expect(dialog).toHaveCount(0);
    await expect(card.getByText("Đã xác nhận văn bản có chữ ký",{exact:true})).toBeVisible();
    view=await read(tbm,base);memberState=view.members.find((m:any)=>m.id===studentMemberIds[0]);
    expect(memberState.eligibility.conditions.find((c:any)=>c.key==="consent").met).toBe(true);
    const grant=(await read(admin,"/admin/round-assignments")).find((g:any)=>g.round_id===round&&g.user_id===receiver&&g.assignment_type==="REVIEW_RECORDS_MANAGER");
    expect((await post(admin,"/admin/round-assignments/"+grant.id+"/revoke",{reason:"End DEMO paper reception duty"})).status()).toBe(204);
    await reviewer.bringToFront();await reviewer.evaluate(()=>window.dispatchEvent(new Event("focus")));
    await expect(reviewer.getByRole("link",{name:"Tiếp nhận hồ sơ phản biện",exact:true})).toHaveCount(0);
    expect((await reviewer.request.get(api+base)).status()).toBe(404);
  });

});
