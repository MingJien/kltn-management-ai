import {test,expect} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import {readFileSync} from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
const root=fileURLToPath(new URL("../../",import.meta.url));
const roles={CHAIR:'Chủ tịch',SECRETARY:'Thư ký',REVIEWER:'Phản biện Hội đồng',MEMBER:'Ủy viên'};
const members=['CHAIR','SECRETARY','REVIEWER','REVIEWER','MEMBER'].map((role,i)=>({id:'lecturer-'+i,name:['Nguyễn Minh An','Trần Hoàng Bình','Lê Thu Hương','Phạm Quốc Dũng','Võ Thanh Hà'][i],role}));
const council={id:'council-demo',name:'Hội đồng Công nghệ thông tin số 01',reference:'QD-KIEM-THU-UI',round_id:'round-demo',department_id:'department-demo',members,can_manage:true,closed_at:null};
const criteria=[...readFileSync(path.join(root,'backend/services/defense.py'),'utf8').matchAll(/\('([\d.]+)', '([^']+)', '([\d.]+)'\)/g)].map(([,code,label,max])=>[code,label,max]);
const roster=[{id:'student-1',name:'Nguyễn Văn Khánh',code:'0023412345'},{id:'student-2',name:'Trần Thị Mai',code:'0023412346'}];
const slot={id:'slot-demo',thesis_id:'thesis-demo',title:'Xây dựng hệ thống quản lý khóa luận tốt nghiệp và hỗ trợ tra cứu bằng trí tuệ nhân tạo',council,starts_at:'2026-11-09T01:00:00Z',ends_at:'2026-11-09T02:00:00Z',room:'Phòng A.301',version:1,context_token:'synthetic-token',bonus_evidence:[],roster,results:Object.fromEntries(roster.map(s=>[s.id,{attendance:{status:'PRESENT'},scores:[null,null,null,null,null],average:null}])),marks:{},role:'SECRETARY',lecturer_id:'lecturer-1',minutes:{},finalized_at:null,can_manage:true,schedule_editable:false,blockers:['Thư ký cần lưu nội dung họp và kết luận','Nguyễn Văn Khánh còn thiếu phiếu của các thành viên hội đồng'],council_attendance:{present_ids:members.map(m=>m.id),reason:'Đủ năm thành viên có mặt'}};
const workspace={scopes:[{round_id:'round-demo',round_code:'KLTN 2026',department_id:'department-demo',department_name:'Công nghệ thông tin'}],councils:[council],eligible:[],candidates:members.map((m,i)=>({...m,code:'GV00'+i})),slots:[slot],criteria,roles};
const context={user_id:'user-demo',base_role:'LECTURER',student_id:null,lecturer_id:'lecturer-1',actions:[],display_name:'Trần Hoàng Bình',department_id:'department-demo',department_code:'CNTT',department_name:'Công nghệ thông tin',email:'secretary@example.test',student_code:null,class_name:null,major_code:null,major_name:null,lecturer_code:'GV001',lecturer_duties:[],csrf_token:'synthetic-ui-token',can_change_password:false};

test("Giữ nháp khi lưu điểm danh, làm tròn đúng và responsive có dữ liệu",async({page})=>{
  let revision=1;
  await page.route("**/api/v1/**",async route=>{
    const endpoint=new URL(route.request().url()).pathname.replace("/api/v1","");
    if(endpoint==="/me/context")return route.fulfill({json:context});
    if(endpoint==="/defense")return route.fulfill({json:{...workspace,slots:[{...slot,version:revision}]}});
    if(endpoint.endsWith("/attendance/student-1")){revision++;return route.fulfill({status:204});}
    if(endpoint.includes("/notifications"))return route.fulfill({json:{items:[],unread_count:0,total:0}});
    return route.fulfill({json:[]});
  });
  await page.goto("/defense");
  await page.getByRole("button",{name:"Biên bản",exact:true}).click();
  const discussion=page.getByLabel("Nội dung họp, câu hỏi và nhận xét",{exact:true});
  await discussion.fill("Biên bản đang soạn chưa lưu");
  await page.getByRole("button",{name:"Phiếu chấm",exact:true}).click();
  await page.getByText("Phiếu chấm Mẫu 6 · Điểm thưởng 0",{exact:true}).first().click();
  const values=["0.27","0.01","0.31","0.10","0.40","0.73","0.62","0.28","0.07","0.29","0.70","0.07"];
  for(let i=0;i<workspace.criteria.length;i++)await page.locator(`input[name="${workspace.criteria[i][0]}"]`).first().fill(values[i]);
  await expect(page.locator(".defense-score-preview").first()).toContainText("3.9 / 10");
  for(const width of [320,390,768,1024,1440]){
    await page.setViewportSize({width,height:960});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  }
  const audit=await new AxeBuilder({page}).include(".defense-page").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
  expect(audit.violations).toEqual([]);
  await page.getByRole("button",{name:"Điểm danh",exact:true}).click();
  await page.getByRole("button",{name:"Lưu điểm danh",exact:true}).first().click();
  await expect(page.getByRole("status").filter({hasText:"Đã lưu thay đổi."})).toBeVisible();
  await expect(discussion).toHaveValue("Biên bản đang soạn chưa lưu");
  await page.getByRole("button",{name:"Phiếu chấm",exact:true}).click();
  await expect(page.locator('input[name="1.1"]').first()).toHaveValue("0.27");
  await expect(page.getByText("In phiếu chấm trước buổi họp",{exact:true}).first()).toBeVisible();
  page.once("dialog",d=>d.accept());await page.reload();
  await page.getByLabel("Tìm lịch theo đề tài, hội đồng, phòng, tên SV hoặc MSSV").fill("0023412345");
  await expect(page.getByRole("heading",{name:slot.title,exact:true})).toBeVisible();
});

test("Khoa quyết định SV vắng rồi xếp lịch bổ sung đúng người",async({page})=>{
  test.setTimeout(30000);
  let decided=false;
  let scheduled:Record<string,unknown>|null=null;
  await page.route("**/api/v1/**",async route=>{
    const endpoint=new URL(route.request().url()).pathname.replace("/api/v1","");
    if(endpoint==="/me/context")return route.fulfill({json:context});
    if(endpoint.endsWith("/absence/student-2")){decided=true;return route.fulfill({status:204});}
    if(endpoint==="/defense/slots"&&route.request().method()==="POST"){
      scheduled=route.request().postDataJSON();return route.fulfill({status:201,json:{id:"supplementary"}});
    }
    if(endpoint==="/defense")return route.fulfill({json:{...workspace,slots:[{...slot,finalized_at:"2026-11-09T03:00:00Z",
      schedule_editable:false,absence_decisions:decided?{"student-2":{outcome:"SUPPLEMENTARY",reference:"QD-BO-SUNG",reason:"Khoa cho phép bảo vệ bổ sung",revision:1,recorded_by:"Người quản lý",recorded_at:"2026-11-10T01:00:00Z"}}:{},
      results:{"student-1":{attendance:{status:"PRESENT"},average:"8.0"},"student-2":{attendance:{status:"ABSENT",reason:"Có lý do"},average:null}}}]}});
    if(endpoint.includes("/notifications"))return route.fulfill({json:{items:[],unread_count:0,total:0}});
    return route.fulfill({json:[]});
  });
  await page.goto("/defense");
  await page.getByRole("button",{name:"Kết quả & xuất",exact:true}).click();
  await page.getByRole("combobox",{name:"Quyết định của Khoa",exact:true}).selectOption("SUPPLEMENTARY");
  await page.getByLabel("Số / căn cứ quyết định",{exact:true}).fill("QD-BO-SUNG");
  await page.getByLabel("Lý do",{exact:true}).fill("Khoa cho phép bảo vệ bổ sung");
  await page.getByRole("button",{name:"Ghi nhận quyết định của Khoa",exact:true}).click();
  await page.getByText("Xếp lịch bảo vệ bổ sung theo quyết định",{exact:true}).click();
  const form=page.locator("form").filter({has:page.getByRole("group",{name:"Sinh viên được Khoa cho bảo vệ bổ sung"})});
  await form.getByRole("combobox",{name:"Hội đồng",exact:true}).selectOption("council-demo");
  await form.getByLabel("Trần Thị Mai · 0023412346",{exact:true}).check();
  await form.getByLabel("Bắt đầu (giờ Việt Nam)",{exact:true}).fill("2026-11-11T08:00");
  await form.getByLabel("Kết thúc (giờ Việt Nam)",{exact:true}).fill("2026-11-11T09:00");
  await form.getByLabel("Phòng bảo vệ",{exact:true}).fill("A.301");
  await form.getByLabel(/Đã đối chiếu thành viên hội đồng không có quan hệ thân nhân/).check();
  await form.getByRole("button",{name:"Lưu lịch",exact:true}).click();
  await expect.poll(()=>scheduled).toMatchObject({prior_slot_id:"slot-demo",thesis_member_ids:["student-2"]});
});
