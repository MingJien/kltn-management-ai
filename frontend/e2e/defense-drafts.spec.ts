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

test("Tách đợt/bộ môn, gợi ý tên và biểu mẫu riêng không đẩy dài danh sách",async({page})=>{
  const scopes=[{...workspace.scopes[0],department_code:"BM-CNTT"},{round_id:"round-next",round_code:"KLTN26-27-D02",department_id:"department-next",department_code:"BM-KHMT",department_name:"Khoa học máy tính"}];
  const catalog=[...scopes,{...scopes[1],department_id:"department-locked",department_code:"BM-KT",department_name:"Kỹ thuật",can_manage:false}];
  await page.route("**/api/v1/**",async route=>{
    const endpoint=new URL(route.request().url()).pathname.replace("/api/v1","");
    if(endpoint==="/me/context")return route.fulfill({json:context});
    if(endpoint==="/defense")return route.fulfill({json:{...workspace,scopes,scope_catalog:catalog,slots:[]}});
    if(endpoint.includes("/notifications"))return route.fulfill({json:{items:[],unread_count:0,total:0}});
    return route.fulfill({json:[]});
  });
  await page.goto("/defense");
  await page.getByRole("button",{name:"Lập hội đồng mới",exact:true}).click();
  const editor=page.getByRole("dialog",{name:"Lập hội đồng mới",exact:true});
  await expect(editor.getByRole("combobox",{name:"Đợt KLTN",exact:true})).toHaveValue("round-demo");
  await expect(editor.locator('input[name="name"]')).toHaveValue(/Hội đồng bảo vệ KLTN 02.*BM-CNTT/);
  await editor.getByRole("combobox",{name:"Đợt KLTN",exact:true}).selectOption("round-next");
  await expect(editor.getByRole("combobox",{name:"Bộ môn",exact:true})).toHaveValue("1");
  await expect(editor.getByRole("combobox",{name:"Bộ môn",exact:true}).locator('option[value="round-nextdepartment-locked"]')).toHaveJSProperty("disabled",true);
  await expect(editor.locator('input[name="name"]')).toHaveValue(/Hội đồng bảo vệ KLTN 01.*BM-KHMT.*KLTN26-27-D02/);
  await editor.getByRole("combobox",{name:"Chủ tịch",exact:true}).selectOption(members[0].id);
  await expect(editor.getByRole("combobox",{name:"Thư ký",exact:true}).locator(`option[value="${members[0].id}"]`)).toHaveJSProperty("disabled",true);
  for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:960});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    await expect.poll(()=>editor.evaluate(el=>el.scrollWidth<=el.clientWidth+1)).toBe(true);
  }
  const audit=await new AxeBuilder({page}).include(".defense-editor").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
  expect(audit.violations).toEqual([]);
  page.once("dialog",d=>d.accept());
  await editor.getByRole("button",{name:"Đóng",exact:true}).click();
  await expect(editor).not.toBeVisible();
  await page.getByRole("button",{name:/Hội đồng \(/}).click();
  await expect(page.getByRole("heading",{name:"Danh sách hội đồng",exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Xem lịch hội đồng này",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Lịch và kết quả bảo vệ",exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Xếp lịch bảo vệ",exact:true}).click();
  await page.getByRole("dialog").getByRole("combobox",{name:"Hội đồng",exact:true}).selectOption(council.id);
  await expect(page.getByRole("dialog").getByText("Chưa có đề tài đủ điều kiện trong phạm vi hội đồng.",{exact:true})).toBeVisible();
  await page.getByText("Vì sao đề tài chưa có trong danh sách?",{exact:true}).click();
  await expect(page.getByText(/Cùng đợt và bộ môn; mọi SV/)).toBeVisible();
});

test("Đổi lịch có đề tài hiện tại, giờ/phòng thẳng hàng và chặn giờ kết thúc sai",async({page})=>{
  let saved:Record<string,unknown>|null=null;
  await page.route("**/api/v1/**",async route=>{
    const endpoint=new URL(route.request().url()).pathname.replace("/api/v1","");
    if(endpoint==="/me/context")return route.fulfill({json:context});
    if(endpoint==="/defense")return route.fulfill({json:{...workspace,slots:[{...slot,schedule_editable:true}],eligible:[{id:slot.thesis_id,title:slot.title,round_id:council.round_id,department_id:council.department_id,advisor_ids:[]}]}});
    if(endpoint==="/defense/slots/slot-demo"){saved=route.request().postDataJSON();return route.fulfill({status:204});}
    if(endpoint.includes("/notifications"))return route.fulfill({json:{items:[],unread_count:0,total:0}});
    return route.fulfill({json:[]});
  });
  await page.goto("/defense");
  await page.getByText("Đổi đề tài, giờ, phòng hoặc hủy lịch",{exact:true}).click();
  const form=page.locator(".defense-schedule-form");
  await expect(form.getByRole("combobox",{name:"Đề tài đủ điều kiện",exact:true})).toHaveValue(slot.thesis_id);
  for(const width of [320,768,1440]){
    await page.setViewportSize({width,height:960});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  }
  await form.locator('[name="end"]').fill("2026-11-09T07:00");
  await form.getByRole("button",{name:"Lưu thay đổi lịch",exact:true}).click();
  expect(saved).toBeNull();
  await form.locator('[name="end"]').fill("2026-11-09T10:00");
  await form.locator('[name="room"]').fill("Phòng B.203");
  await form.getByRole("button",{name:"Lưu thay đổi lịch",exact:true}).click();
  await expect.poll(()=>saved?.room).toBe("Phòng B.203");
  expect(saved?.thesis_id).toBe(slot.thesis_id);
});

test("Xếp hai đề tài liên tiếp chỉ nhập hội đồng, phòng và thời gian một lần",async({page})=>{
  let saved:any=null;
  await page.route("**/api/v1/**",async route=>{
    const endpoint=new URL(route.request().url()).pathname.replace("/api/v1","");
    if(endpoint==="/me/context")return route.fulfill({json:context});
    if(endpoint==="/defense")return route.fulfill({json:{...workspace,slots:[],eligible:[1,2].map(i=>({id:'topic-'+i,title:'Đề tài demo '+i,round_id:council.round_id,department_id:council.department_id,advisor_ids:[]}))}});
    if(endpoint==="/defense/slots-batch"){saved=route.request().postDataJSON();return route.fulfill({status:201,json:{slots:[{id:'one'},{id:'two'}]}});}
    if(endpoint.includes("/notifications"))return route.fulfill({json:{items:[],unread_count:0,total:0}});
    return route.fulfill({json:[]});
  });
  await page.goto('/defense');await page.getByRole('button',{name:'Xếp lịch bảo vệ',exact:true}).click();
  const dialog=page.getByRole('dialog');await dialog.getByRole('combobox',{name:'Hội đồng',exact:true}).selectOption(council.id);
  await dialog.getByRole('button',{name:'Chọn tất cả',exact:true}).click();
  await dialog.getByLabel('Bắt đầu (giờ Việt Nam)',{exact:true}).fill('2026-11-20T08:00');
  await dialog.getByLabel('Phòng bảo vệ',{exact:true}).fill('A.301');
  await dialog.getByRole('checkbox',{name:/Đã đối chiếu/}).check();
  for(const width of [320,768,1440]){await page.setViewportSize({width,height:960});await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);}
  await dialog.getByRole('button',{name:'Lưu lịch cho 2 đề tài',exact:true}).click();
  await expect.poll(()=>saved?.slots?.length).toBe(2);
  expect(Date.parse(saved.slots[1].starts_at)-Date.parse(saved.slots[0].ends_at)).toBe(5*60000);
  expect(saved.slots[0].room).toBe('A.301');await expect(dialog).not.toBeVisible();
});

test("Thư ký định dạng trực tiếp bản xem, Enter/Tab không thay đổi chữ hoặc điểm",async({page})=>{
 const source='Nhận xét demo giữ nguyên';let lastUrl='';
 await page.route('**/api/v1/**',async route=>{
  const url=new URL(route.request().url()),endpoint=url.pathname.replace('/api/v1','');
  if(endpoint==='/me/context')return route.fulfill({json:context});
  if(endpoint==='/defense')return route.fulfill({json:{...workspace,slots:[{...slot,marks:{'student-1':{'lecturer-1':{scores:Array(12).fill('0.5'),note:source}}}}]}});
  if(endpoint.endsWith('/forms/6')){
   lastUrl=url.toString();
   if(url.searchParams.has('layout_fields'))return route.fulfill({json:{fields:[{key:'note',label:'Đề nghị / nhận xét',text:source}]}});
   if(url.searchParams.has('preview_revision'))return route.fulfill({json:{revision:'synthetic-layout'}});
   return route.fulfill({json:{sheets:[{name:'Mẫu 6',rows:[[{text:'III. Đề nghị (nếu có): '+source,rowspan:1,colspan:1,bold:false,italic:false,size:10,align:'left'}]]}]}});
  }
  if(endpoint.includes('/notifications'))return route.fulfill({json:{items:[],unread_count:0,total:0}});
  return route.fulfill({json:[]});
 });
 await page.goto('/defense');await page.getByRole('button',{name:'Phiếu chấm',exact:true}).click();
 await page.getByText('Xem trước & định dạng · Mẫu 6 · '+members[1].name+' · '+roster[0].name,{exact:true}).click();
 const print=page.locator('.defense-print').first();await print.getByRole('button',{name:'Áp dụng & xem trước',exact:true}).click();
 const field=print.getByRole('textbox',{name:'Định dạng Đề nghị / nhận xét',exact:true});await expect(field).toHaveText(source);
 await field.focus();await field.press('Home');for(let i=0;i<5;i++)await field.press('ArrowRight');
 await field.press('Enter');await field.press('Tab');await field.press('X');
 expect((await field.textContent())?.replace(/[\n\t]/g,'')).toBe(source);
 await print.getByRole('button',{name:'Đậm',exact:true}).click();
 await expect(print.getByRole('button',{name:'Tải bản theo định dạng đã chọn',exact:true})).toBeDisabled();
 await print.getByRole('button',{name:'Áp dụng & xem trước',exact:true}).click();
 await expect.poll(()=>new URL(lastUrl).searchParams.get('line_breaks')).toContain('5');
 expect(new URL(lastUrl).searchParams.get('tabs')).toContain('5');
 expect(new URL(lastUrl).searchParams.get('field_styles')).toContain('"bold":true');
});

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
  const discussion=page.getByLabel("Nội dung trao đổi và trả lời câu hỏi",{exact:true});
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

test("Mẫu 11 toàn đợt yêu cầu chọn mã và dùng cùng mã khi xem hoặc lưu",async({page})=>{
  const register="/defense/round-register/round-demo";
  let savedCode="";
  await page.route("**/api/v1/**",async route=>{
    const url=new URL(route.request().url());
    const endpoint=url.pathname.replace("/api/v1","");
    if(endpoint==="/me/context")return route.fulfill({json:context});
    if(endpoint==="/defense")return route.fulfill({json:{...workspace,slots:[],export_rounds:[{id:"round-demo",code:"KLTN-DEMO"}]}});
    if(endpoint===register)return route.fulfill({json:{code:"KLTN-DEMO",issues:[],rows:[
      {name:"Sinh viên A",code:"0023000001",class_name:"CNTT22",grade:"8.5",status:"Đã chốt điểm",slot_id:"slot-main",council:"Hội đồng chính",has_birth_date:true},
      {name:"Sinh viên B",code:"0023000002",class_name:"CNTT22",grade:"8.0",status:"Đã chốt điểm",slot_id:"slot-extra",council:"Hội đồng bổ sung",has_birth_date:true},
    ]}});
    if(endpoint===register+"/forms/11"){
      if(url.searchParams.has('preview_revision'))return route.fulfill({json:{revision:'synthetic-revision'}});
      const code=url.searchParams.get("course_code")??"";
      if(route.request().method()==="POST"){
        savedCode=code;
        return route.fulfill({body:"Synthetic browser download",contentType:"application/octet-stream",
          headers:{"content-disposition":'attachment; filename="Mau-11-KLTN-DEMO.xlsx"',"access-control-expose-headers":"Content-Disposition"}});
      }
      return route.fulfill({json:{sheets:[{name:"Bảng điểm",rows:[[{text:`Mã học phần ${code}`,rowspan:1,colspan:1,bold:true,italic:false,size:11,align:"left"}]]}]}});
    }
    if(endpoint.includes("/notifications"))return route.fulfill({json:{items:[],unread_count:0,total:0}});
    return route.fulfill({json:[]});
  });
  await page.goto("/defense");
  await page.getByRole("button",{name:"Bảng điểm toàn đợt",exact:true}).click();
  await page.getByText("Bảng điểm toàn đợt · Mẫu 10 và 11",{exact:true}).click();
  await page.getByRole("combobox",{name:/Đợt bảo vệ/}).selectOption("round-demo");
  await expect(page.getByRole("cell",{name:"Hội đồng bổ sung",exact:true})).toBeVisible();
  await expect(page.getByText(/Xem trước & định dạng · Mẫu 11/)).toHaveCount(0);
  await page.getByRole("combobox",{name:/Mã học phần của bảng/}).selectOption("IN4299N");
  await expect(page.getByText("Xem trước & định dạng · Mẫu 11 · IN4299N",{exact:true})).toBeVisible();
  await page.getByRole("combobox",{name:/Mã học phần của bảng/}).selectOption("other");
  await page.getByRole("textbox",{name:/Mã học phần khác/}).fill("CT2026");
  await page.getByText("Xem trước & định dạng · Mẫu 11 · CT2026",{exact:true}).click();
  await page.getByRole("button",{name:"Áp dụng & xem trước",exact:true}).click();
  await expect(page.getByRole("cell",{name:"Mã học phần CT2026",exact:true})).toBeVisible();
  for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:900});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
  }
  const download = page.waitForEvent("download");
  await page.getByRole("button",{name:"Lưu và tải bản dùng để ký",exact:true}).click();
  expect((await download).suggestedFilename()).toBe("Mau-11-KLTN-DEMO.xlsx");
  expect(savedCode).toBe("CT2026");
});

test('Đính chính sau khóa: nhập căn cứ, đối chiếu và duyệt không mở khóa điểm',async({page})=>{
  let proposal:any=null,approved=false;
  const minutes={objectives:'Mục tiêu có căn cứ',functions:'Chức năng đã trình bày',achievements:'Kết quả đã đối chiếu',discussion:'Nội dung trao đổi tại hội đồng',conclusion:'Kết luận của chủ tịch',recommendations:'Hoàn thiện tài liệu',classifications:{'student-1':'Giỏi','student-2':'Khá'}};
  await page.route('**/api/v1/**',async route=>{
    const endpoint=new URL(route.request().url()).pathname.replace('/api/v1','');
    if(endpoint==='/me/context')return route.fulfill({json:context});
    if(endpoint==='/defense')return route.fulfill({json:{...workspace,councils:[{...council,closed_at:'2026-11-16T01:00:00Z'}],slots:[{...slot,council:{...council,closed_at:'2026-11-16T01:00:00Z'},minutes,finalized_at:'2026-11-16T01:00:00Z',schedule_editable:false}]}});
    if(endpoint==='/defense/slots/slot-demo/corrections'){
      if(route.request().method()==='POST'){proposal=route.request().postDataJSON();expect(route.request().headers()['if-match']).toBe('1');return route.fulfill({status:204});}
      return route.fulfill({json:{can_approve:true,missing:[],items:proposal?[{id:'correction',version:1,state:approved?'APPROVED':'PENDING',reference:proposal.reference,reason:proposal.reason,proposal,before:{marks:{},minutes},can_decide:true,can_cancel:false,decision_note:approved?'Đã kiểm tra biên bản và căn cứ':'Không'}]:[]}});
    }
    if(endpoint==='/defense/corrections/correction/decision'){expect(route.request().postDataJSON().decision).toBe('APPROVED');approved=true;return route.fulfill({status:204});}
    if(endpoint.includes('/notifications'))return route.fulfill({json:{items:[],unread_count:0,total:0}});
    return route.fulfill({json:[]});
  });
  await page.goto('/defense');
  await page.getByText('Đính chính hồ sơ sau khóa',{exact:true}).click();
  const form=page.locator('form').filter({has:page.getByRole('button',{name:'Gửi đề nghị đính chính',exact:true})});
  await form.getByLabel('Số văn bản / căn cứ đính chính',{exact:true}).fill('BB-CHINH-2026');
  await form.getByLabel('Lý do đính chính',{exact:true}).fill('Bổ sung nội dung được hội đồng xác nhận');
  await form.getByRole('button',{name:'Gửi đề nghị đính chính',exact:true}).click();
  await expect(page.getByRole('columnheader',{name:'Đề nghị',exact:true})).toBeVisible();
  await page.getByRole('combobox',{name:'Quyết định',exact:true}).selectOption('APPROVED');
  await page.getByLabel('Nhận xét quyết định',{exact:true}).fill('Đã kiểm tra biên bản và căn cứ');
  await page.getByRole('button',{name:'Lưu quyết định đính chính',exact:true}).click();
  await expect(page.getByText('Đã duyệt · Biên bản',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Khóa bảng điểm hội đồng',exact:true})).toHaveCount(0);
  for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:960});await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);}
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
