import {test, expect, type Page} from "@playwright/test";
const accounts = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const api = "http://127.0.0.1:" + process.env.KLTN_E2E_API_PORT + "/api/v1";
async function login(page:Page, key:string) {
  await page.goto("/"); await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("button",{name:"Đăng xuất"})).toBeVisible();
}
async function get(page:Page, url:string) {
  const r=await page.request.get(api+url); expect(r.ok(),await r.text()).toBeTruthy(); return r.json();
}
async function post(page:Page,url:string,data?:unknown,version?:number) {
  const me=await get(page,"/me/context");
  const r=await page.request.post(api+url,{data,headers:{"X-CSRF-Token":me.csrf_token,...(version===undefined?{}:{"If-Match":String(version)})}});
  expect(r.ok(),await r.text()).toBeTruthy(); return r.status()===204 ? null : r.json();
}
function localFuture() {
  const d=new Date(Date.now()+90*86400000);
  return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")+"T12:00";
}
test("SV/GV use one submission hub: M1 before acceptance, M2 upload/review, M3, separate progress and faculty library",async({browser})=>{
  test.setTimeout(240000);
  const contexts=await Promise.all(["admin","gv","tbm","returnFlow","nv5Outsider"].map(()=>browser.newContext()));
  const pages=await Promise.all(contexts.map(c=>c.newPage()));
  for (const page of pages) page.setDefaultTimeout(20000);
  try {
    for(let i=0;i<pages.length;i++)await login(pages[i],["admin","gv","tbm","returnFlow","nv5Outsider"][i]);
    const [admin,gv,tbm,sv,outsider]=pages;
    const round=(await get(gv,"/rounds/open"))[0];
    let topic=await post(gv,"/topics",{round_id:round.id,title:"DEMO kiểm thử hồ sơ nộp tập trung",max_students:1});
    topic=await post(gv,"/topics/"+topic.id+"/submit",undefined,topic.row_version);
    await post(tbm,"/topics/"+topic.id+"/department-decision",{decision:"APPROVE"},topic.row_version);
    let reg=await post(sv,"/topic-registrations",{topic_id:topic.id});
    await sv.goto("/registrations?focus="+reg.id);
    await expect(sv.locator(".registration-forms")).toHaveCount(0);
    await sv.getByRole("link",{name:"Mở đơn Mẫu 1a/1b · nộp, tải & lịch sử"}).click();
    await expect(sv.getByRole("heading",{name:"Hồ sơ nộp & xét duyệt",exact:true})).toBeVisible();
    await sv.getByLabel(/Nộp đơn Mẫu 1a/).setInputFiles(process.env.KLTN_E2E_FORM_1A_FILE!);
    await sv.getByRole("button",{name:"Nộp phiên bản đơn",exact:true}).click();
    await expect(sv.getByRole("button",{name:"Tải đơn gốc v1",exact:true})).toBeEnabled({timeout:60000});
    expect((await get(sv,"/topic-registrations/"+reg.id+"/forms")).versions).toHaveLength(1);
    await outsider.goto("/submissions?registration="+reg.id);
    await expect(outsider.getByRole("alert")).toBeVisible();
    await expect(outsider.locator(".registration-forms")).toHaveCount(0);
    reg=await post(sv,"/topic-registrations/"+reg.id+"/submit");
    reg=await post(gv,"/topic-registrations/"+reg.id+"/lecturer-decision",{decision:"ACCEPT"},reg.row_version);
    const base="/theses/"+reg.thesis_id;
    await sv.reload();
    await expect(sv).toHaveURL(new RegExp(reg.thesis_id+".*kind=REGISTRATION"));
    await expect(sv.getByRole("button",{name:"Tải đơn gốc v1",exact:true})).toBeEnabled({timeout:60000});

    if (!(await get(tbm,base)).actions.includes("milestone:manage")) {
      await post(admin,"/admin/round-assignments",{round_id:round.id,user_id:(await get(tbm,"/me/context")).user_id,assignment_type:"KLTN_COORDINATOR",basis_ref:"Khoa giao điều phối để kiểm thử hồ sơ"});
    }
    for(const kind of ["PLAN","PROPOSAL","SUPPORTING"]){
      await tbm.goto(base+"?section=submissions&kind="+kind);
      const deadline=tbm.locator("section.card").filter({has:tbm.getByRole("heading",{name:kind==="PROPOSAL"?"Lịch nhận đề cương của đợt":"Lịch nhận tài liệu của đợt",exact:true})});
      await expect(deadline.getByLabel("Loại tài liệu",{exact:true}).locator("option")).toHaveCount(1);
      await deadline.getByLabel("Hạn mới (giờ Việt Nam)",{exact:true}).fill(localFuture());
      await deadline.getByLabel("Căn cứ / lý do",{exact:true}).fill("Mở nhận đúng từng loại hồ sơ để kiểm thử");
      await deadline.getByRole("button",{name:/^(Thiết lập cho cả đợt|Gia hạn cho cả đợt|Gia hạn và mở nhận lại cả đợt)$/}).click();
      await expect(tbm.getByRole("status").filter({hasText:/Đã (thiết lập hạn|gia hạn loại) tài liệu cho toàn đợt/})).toBeVisible();
    }
    await sv.getByRole("link",{name:/Mẫu 2 Kế hoạch thực hiện/}).click();
    await expect(sv.getByLabel(/Tệp cần nộp/)).toBeEnabled();
    await sv.getByLabel(/Tệp cần nộp/).setInputFiles({name:"wrong.txt",mimeType:"text/plain",buffer:Buffer.from("SYNTHETIC WRONG FORMAT")});
    await expect(sv.getByRole("button",{name:"Nộp kế hoạch Mẫu 2",exact:true})).toBeDisabled();
    await sv.getByLabel(/Tệp cần nộp/).setInputFiles(process.env.KLTN_E2E_PLAN_FILE!);
    await sv.getByRole("button",{name:"Nộp kế hoạch Mẫu 2",exact:true}).click();
    await expect(sv.getByRole("button",{name:"Tải bản nộp gốc v1",exact:true})).toBeEnabled({timeout:60000});
    await expect(sv.locator(".submission-update")).not.toHaveAttribute("open");
    expect((await get(gv,"/notifications?limit=100")).items.some((n:any) => n.url === base+"?section=submissions&kind=PLAN")).toBeTruthy();
    const docs=await get(sv,base+"/documents");
    expect(docs.filter((d:any)=>d.document_type==="PLAN")).toHaveLength(1);
    expect(docs.find((d:any)=>d.document_type==="PLAN").versions).toHaveLength(1);
    await expect(sv.getByText(/Xem toàn bộ biểu mẫu chính thức/)).toHaveCount(0);
    await sv.evaluate(() => window.scrollTo(0,0));
    await sv.screenshot({path:test.info().outputPath("student-submission-hub.png")});
    await gv.goto(base+"?section=documents");
    await expect(gv.getByRole("heading",{name:"Hồ sơ nộp & xét duyệt",exact:true})).toBeVisible();
    await gv.getByRole("checkbox",{name:/Chờ tôi xử lý/}).check();
    await expect(gv.locator(".submission-kinds > a")).toHaveCount(1);
    await gv.evaluate(() => window.scrollTo(0,0));
    await gv.screenshot({path:test.info().outputPath("lecturer-pending-hub.png")});
    await gv.getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    const modal=gv.getByRole("dialog");
    await modal.getByLabel("Kết quả",{exact:true}).selectOption("ACCEPT");
    await modal.getByLabel("Nhận xét tổng quát",{exact:true}).fill("Kế hoạch rõ ràng, tiếp nhận đúng phiên bản.");
    await modal.getByRole("button",{name:"Hoàn thành và gửi góp ý",exact:true}).click();
    await expect(modal).toHaveCount(0);
    await expect(gv.getByRole("heading",{name:"Không có hồ sơ đang chờ bạn xử lý",exact:true})).toBeVisible();
    await gv.getByRole("button",{name:"Xem tất cả hồ sơ",exact:true}).click();
    await expect(gv.getByRole("button",{name:/Xuất bản đã duyệt để ký ngoài/})).toBeEnabled();
    await sv.getByRole("link",{name:/Mẫu 3 Đề cương/}).click();
    await expect(sv.getByRole("button",{name:"Tải mẫu chính thức Mẫu 3",exact:true})).toBeVisible();
    await expect(sv.getByRole("button",{name:"Tải mẫu áp dụng · Mẫu 2",exact:true})).toHaveCount(0);
    await sv.getByLabel("Nộp đề cương PDF hoặc DOCX (tối đa 10 MB)").setInputFiles(process.env.KLTN_E2E_PROPOSAL_FILE!);
    await sv.getByRole("button",{name:"Nộp đề cương",exact:true}).click();
    await expect(sv.getByRole("button",{name:"Tải bản nộp gốc v1",exact:true})).toBeEnabled({timeout:60000});
    await sv.locator(".submission-kinds").getByRole("link",{name:/Tài liệu hỗ trợ/}).click();
    await expect(sv.getByRole("heading",{name:"Tài liệu hỗ trợ",exact:true})).toBeVisible();
    await expect(sv.getByText(/Phiên bản 1 ·/)).toHaveCount(0);
    await sv.getByLabel("Nội dung tài liệu",{exact:true}).selectOption("SUPPORTING_PUBLICATION");
    await sv.getByLabel(/Tệp cần nộp/).setInputFiles(process.env.KLTN_E2E_NV6_FILE!);
    await sv.getByRole("button",{name:"Nộp tài liệu",exact:true}).click();
    await expect(sv.locator(".submission-attachment > summary")).toContainText("Minh chứng công bố khoa học để xét điểm thưởng");
    expect((await get(sv,base+"/documents")).filter((doc:any)=>doc.document_type==="SUPPORTING")[0].versions).toHaveLength(1);
    await sv.setViewportSize({width:600,height:900});
    expect(await sv.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
    await sv.getByRole("tab",{name:"Báo cáo tiến độ",exact:true}).click();
    await expect(sv.locator(".submission-kinds")).toHaveCount(0);
    await expect(sv.getByRole("heading",{name:"Báo cáo tiến độ",exact:true})).toBeVisible();
    await sv.goto("/forms?round_id="+round.id);
    await expect(sv.getByRole("heading",{name:"Kho biểu mẫu & tài liệu Khoa",exact:true})).toBeVisible();
    await expect(sv.locator('input[type="file"]')).toHaveCount(0);
    await sv.getByRole("link",{name:"Mở hồ sơ nộp & xét duyệt",exact:true}).click();
    await expect(sv.getByRole("heading",{name:"Hồ sơ nộp & xét duyệt",exact:true})).toBeVisible();
    await expect(sv.getByRole("navigation",{name:"Chức năng"}).getByRole("link",{name:"Tài liệu khóa luận",exact:true})).toHaveCount(0);
  } finally {for(const context of contexts)await context.close();}
});
