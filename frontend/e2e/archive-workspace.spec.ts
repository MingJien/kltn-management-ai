import {test,expect} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const context={user_id:"demo",base_role:"STUDENT",student_id:"student",lecturer_id:null,actions:[],display_name:"Nguyễn Văn An",
  department_id:"dep",department_code:"CNTT",department_name:"Công nghệ thông tin",email:"demo@example.invalid",
  student_code:"0023000001",class_name:"ĐHCNTT22A",major_code:"7480201",major_name:"Công nghệ thông tin",lecturer_code:null,
  lecturer_duties:[],csrf_token:"synthetic-csrf",can_change_password:false};
const entry={id:"thesis",title:"Hệ thống quản lý khóa luận và hỗ trợ tra cứu tài liệu",round_id:"round",round:"KLTN-DEMO",
  department:"Công nghệ thông tin",waiting:false,can_submit:true,can_decide:false,
  snapshot:{title:"Hệ thống quản lý khóa luận và hỗ trợ tra cứu tài liệu",advisor:"ThS. Nguyễn Văn Minh",students:[{name:"Nguyễn Văn An",code:"0023000001"}]},versions:[]};

test("SV nộp bản lưu, thấy trạng thái mới và không thể nộp trùng",async({page})=>{
  let submitted=false;
  await page.route("**/api/v1/**",async route=>{
    const endpoint=new URL(route.request().url()).pathname.replace("/api/v1","");
    if(endpoint==="/me/context")return route.fulfill({json:context});
    if(endpoint==="/thesis-archive/theses/thesis"){
      expect(route.request().method()).toBe("POST");
      expect(route.request().headers()["x-csrf-token"]).toBe("synthetic-csrf");
      expect(route.request().headers()["x-file-name"]).toBe("Ban-hoan-thien.pdf");
      submitted=true;return route.fulfill({status:201,json:{id:"version"}});
    }
    if(endpoint==="/thesis-archive")return route.fulfill({json:[submitted?{...entry,can_submit:false,versions:[{
      id:"version",number:1,revision:1,state:"SUBMITTED",filename:"Ban-hoan-thien.pdf",created_at:"2026-11-15T02:00:00Z",
      decided_at:null,decided_by:null,decision_note:null}]}:entry]});
    if(endpoint.includes("/notifications"))return route.fulfill({json:{items:[],unread_count:0,total:0}});
    return route.fulfill({json:[]});
  });
  await page.goto("/repository?focus=thesis");
  await page.getByLabel(/Bản khóa luận hoàn thiện sau bảo vệ/).setInputFiles({name:"Ban-hoan-thien.pdf",mimeType:"application/pdf",buffer:Buffer.from("Synthetic UI upload")});
  await page.getByRole("button",{name:"Nộp bản hoàn thiện",exact:true}).click();
  await expect(page.getByRole("status")).toContainText("Đã nộp bản hoàn thiện");
  await expect(page.getByText("Phiên bản 1 · Chờ bộ môn duyệt",{exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Nộp bản hoàn thiện",exact:true})).toHaveCount(0);
  for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:960});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  }
  const audit=await new AxeBuilder({page}).include(".defense-page").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
  expect(audit.violations).toEqual([]);
});

test("TBM trả bản lưu kèm lý do rồi thấy kết quả và người xử lý",async({page})=>{
  let processed=false;
  const version={id:"version",number:1,revision:3,state:"SUBMITTED",filename:"Ban-hoan-thien.pdf",created_at:"2026-11-15T02:00:00Z",
    decided_at:null,decided_by:null,decision_note:null};
  await page.route("**/api/v1/**",async route=>{
    const endpoint=new URL(route.request().url()).pathname.replace("/api/v1","");
    if(endpoint==="/me/context")return route.fulfill({json:{...context,base_role:"LECTURER",student_id:null,lecturer_id:"head"}});
    if(endpoint==="/thesis-archive/versions/version/decision"){
      expect(route.request().headers()["if-match"]).toBe("3");
      expect(route.request().postDataJSON()).toEqual({decision:"RETURNED",reason:"Cần bổ sung tài liệu triển khai theo kết luận hội đồng."});
      processed=true;return route.fulfill({status:204});
    }
    if(endpoint==="/thesis-archive")return route.fulfill({json:[{...entry,can_submit:false,can_decide:!processed,
      versions:[processed?{...version,state:"RETURNED",decided_at:"2026-11-15T03:00:00Z",decided_by:"Trưởng bộ môn",
        decision_note:"Cần bổ sung tài liệu triển khai theo kết luận hội đồng."}:version]}]});
    if(endpoint.includes("/notifications"))return route.fulfill({json:{items:[],unread_count:0,total:0}});
    return route.fulfill({json:[]});
  });
  await page.goto("/repository?focus=thesis");
  await page.getByRole("combobox",{name:"Kết quả kiểm tra",exact:true}).selectOption("RETURNED");
  await page.getByLabel("Nhận xét và căn cứ",{exact:true}).fill("Cần bổ sung tài liệu triển khai theo kết luận hội đồng.");
  await page.getByRole("button",{name:"Lưu quyết định",exact:true}).click();
  await expect(page.getByText("Phiên bản 1 · Cần nộp lại",{exact:true})).toBeVisible();
  await expect(page.getByText(/Trưởng bộ môn ·/)).toBeVisible();
  await expect(page.getByRole("button",{name:"Lưu quyết định",exact:true})).toHaveCount(0);
});
