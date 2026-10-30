import {test,expect,type Page} from "@playwright/test";
const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const api=`http://127.0.0.1:${process.env.KLTN_E2E_API_PORT || "8001"}/api/v1`;
async function login(page:Page,key:string){await page.goto("/");await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();await expect(page.getByRole("button",{name:"Đăng xuất"})).toBeVisible();}
test("Admin sees real aggregate dashboard and dedicated complete lecturer directory",async({page})=>{
 await login(page,"admin");
 await expect(page.getByRole("heading",{name:"Thống kê hiện tại"})).toBeVisible();
 await expect(page.locator(".metric-card")).toHaveCount(4);
 await expect(page.locator(".dashboard-breakdown article").filter({has:page.getByRole("heading",{name:/^Tài khoản/})}).getByText("Đang hoạt động",{exact:true})).toBeVisible();
 await page.getByRole("region",{name:"Thống kê quản trị",exact:true}).scrollIntoViewIfNeeded();
 await page.screenshot({path:test.info().outputPath("admin-dashboard.png")});
 const response=await page.request.get(api+"/admin/dashboard");expect(response.status()).toBe(200);const summary=await response.json();await expect(page.locator(".metric-card").filter({hasText:"Giảng viên"}).locator("strong")).toHaveText(String(summary.accounts.LECTURER || 0));
 await page.getByRole("link",{name:"Danh sách giảng viên",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Danh sách giảng viên",exact:true})).toBeVisible();
 await expect(page.getByText("Chỉ hiển thị GV chưa kích hoạt")).toBeVisible();
 await expect(page.getByRole("checkbox",{name:"Chỉ hiển thị GV chưa kích hoạt"})).not.toBeChecked();
 await expect(page.locator("table").last()).toBeVisible();
 await expect(page.locator("table").last().locator("tbody tr").first()).toBeVisible();
 expect(await page.locator(".table-scroll").last().evaluate(el=>getComputedStyle(el).overflowX)).toBe("auto");
 await page.setViewportSize({width:900,height:900});
 const region=page.getByRole("region",{name:"Danh sách tài khoản giảng viên",exact:true});
 expect(await region.evaluate(el=>el.scrollWidth>el.clientWidth)).toBeTruthy();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});
test("Lecturer deletes draft and TBM archives/restores through explicit UI confirmation",async({browser})=>{
 const gvContext=await browser.newContext();const headContext=await browser.newContext();
 const gv=await gvContext.newPage(),head=await headContext.newPage();
 try{await login(gv,"gv");await login(head,"tbm");
 const auth=await (await gv.request.get(api+"/me/context")).json();const rounds=await(await gv.request.get(api+"/rounds/open")).json();
 const made=await gv.request.post(api+"/topics",{headers:{"X-CSRF-Token":auth.csrf_token},data:{round_id:rounds[0].id,title:"UX kiểm thử đề tài nháp có thể xóa",max_students:1}});expect(made.status()).toBe(201);const topic=await made.json();
 await gv.goto(`/topics?focus=${topic.id}`);await gv.getByText("Xóa đề tài nháp",{exact:true}).first().click();
 await expect(gv.getByRole("button",{name:"Xóa đề tài nháp",exact:true})).toBeDisabled();
 const panel=gv.locator("details").filter({has:gv.getByRole("button",{name:"Xóa đề tài nháp",exact:true})});
 await panel.getByLabel("Lý do",{exact:true}).fill("Nháp thử nghiệm tạo nhầm");await panel.getByRole("checkbox").check();
 await panel.getByRole("button",{name:"Xóa đề tài nháp",exact:true}).click();
 await expect(gv.getByText("Đã cập nhật đề tài và ghi nhật ký.",{exact:true})).toBeVisible();
 expect((await gv.request.get(api+`/topics/${topic.id}`)).status()).toBe(404);
 const r2=await gv.request.post(api+"/topics",{headers:{"X-CSRF-Token":auth.csrf_token},data:{round_id:rounds[0].id,title:"UX kiểm thử ngừng sử dụng và khôi phục",max_students:1}});expect(r2.status()).toBe(201);let t2=await r2.json();
 let result=await gv.request.post(api+`/topics/${t2.id}/submit`,{headers:{"X-CSRF-Token":auth.csrf_token,"If-Match":String(t2.row_version)}});expect(result.ok()).toBeTruthy();t2=await result.json();
 const headAuth=await (await head.request.get(api+"/me/context")).json();result=await head.request.post(api+`/topics/${t2.id}/department-decision`,{headers:{"X-CSRF-Token":headAuth.csrf_token,"If-Match":String(t2.row_version)},data:{decision:"APPROVE"}});expect(result.ok()).toBeTruthy();
 for(const label of ["Ngừng sử dụng đề tài","Khôi phục hiển thị đề tài"]){
  await head.goto(`/topics?focus=${t2.id}`);await head.getByText(label,{exact:true}).first().click();
  const manage=head.locator("details").filter({has:head.getByRole("button",{name:label,exact:true})});
  await manage.getByLabel("Lý do",{exact:true}).fill("Bộ môn kiểm thử vòng đời hiển thị");await manage.getByRole("checkbox").check();await manage.getByRole("button",{name:label,exact:true}).click();await expect(head.getByText("Đã cập nhật đề tài và ghi nhật ký.",{exact:true})).toBeVisible();
  const current=await (await head.request.get(api+`/topics/${t2.id}`)).json();expect(Boolean(current.archived_at)).toBe(label==="Ngừng sử dụng đề tài");expect(current.state).toBe("APPROVED");
 }

 }finally{await gvContext.close();await headContext.close();}
});

test("Thesis workspace separates overview, proposal, weekly progress and documents for SV and GV",async({browser})=>{
 const keys=["gv","tbm","nv5Student"];const contexts=await Promise.all(keys.map(()=>browser.newContext()));const pages=await Promise.all(contexts.map(c=>c.newPage()));
 try{for(let i=0;i<keys.length;i++)await login(pages[i],keys[i]);const [gv,head,sv]=pages;
 const get=async(p:Page,path:string)=>(await p.request.get(api+path)).json();
 const post=async(p:Page,path:string,data?:unknown,version?:number)=>{const me=await get(p,"/me/context");const r=await p.request.post(api+path,{data,headers:{"X-CSRF-Token":me.csrf_token,...(version===undefined?{}:{"If-Match":String(version)})}});expect(r.ok(),await r.text()).toBeTruthy();return r.status()===204?null:r.json();};
 const round=(await get(gv,"/rounds/open"))[0];let topic=await post(gv,"/topics",{round_id:round.id,title:"UX hồ sơ khóa luận phân hệ rõ ràng",max_students:1});topic=await post(gv,`/topics/${topic.id}/submit`,undefined,topic.row_version);await post(head,`/topics/${topic.id}/department-decision`,{decision:"APPROVE"},topic.row_version);
 let reg=await post(sv,"/topic-registrations",{topic_id:topic.id});reg=await post(sv,`/topic-registrations/${reg.id}/submit`);reg=await post(gv,`/topic-registrations/${reg.id}/lecturer-decision`,{decision:"ACCEPT"},reg.row_version);
 for(const page of [sv,gv]){
  await page.goto(`/theses/${reg.thesis_id}?section=overview`);await expect(page.getByRole("heading",{name:"Khóa luận & GVHD",exact:true})).toBeVisible();await expect(page.getByRole("heading",{name:"Nhóm sinh viên thực hiện"})).toBeVisible();
  await page.goto(`/theses/${reg.thesis_id}?section=progress`);await expect(page.getByRole("heading",{name:"Báo cáo tiến độ",exact:true})).toBeVisible();await expect(page.getByRole("heading",{name:"Lịch nhận đề cương của đợt"})).toHaveCount(0);await expect(page.getByRole("heading",{name:"Lịch nhận tài liệu của đợt"})).toHaveCount(0);
  await page.goto(`/theses/${reg.thesis_id}?section=proposal`);await expect(page.getByRole("heading",{name:"Lịch nhận đề cương của đợt",exact:true})).toBeVisible();await expect(page.getByRole("button",{name:"Tải mẫu chính thức Mẫu 3"})).toBeVisible();
  await page.goto(`/theses/${reg.thesis_id}?section=documents`);await expect(page.getByRole("heading",{name:"Lịch nhận tài liệu của đợt",exact:true})).toBeVisible();await expect(page.getByRole("heading",{name:"Lịch nhận đề cương của đợt"})).toHaveCount(0);
 }
 await sv.goto("/theses");await expect(sv).toHaveURL(new RegExp(`/theses/${reg.thesis_id}`));
 }finally{for(const context of contexts)await context.close();}
});
