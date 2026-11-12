import {test,expect,type Page} from "@playwright/test";
import {promises as fs} from "node:fs";
import path from "node:path";

const accounts:Record<string,{email:string;password:string}>=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON||"{}");
const web=`http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT||"5174"}`;
const api=`http://127.0.0.1:${process.env.KLTN_E2E_API_PORT||"8001"}/api/v1`;
async function read(page:Page,url:string){const r=await page.request.get(api+url);expect(r.status()).toBe(200);return r.json();}
async function post(page:Page,url:string,data?:unknown,version?:number){
  const auth=await read(page,"/me/context");
  return page.request.post(api+url,{data,headers:{"X-CSRF-Token":auth.csrf_token,...(version===undefined?{}:{"If-Match":String(version)})}});
}
test("Mẫu 1a/1b: nộp trước tiếp nhận, phiên bản bất biến, đổi nhóm và xuất bản nộp có footer",async({browser})=>{
  test.setTimeout(180000);
  const actors=await Promise.all(["gv2","tbm","formStudent","formMember","admin"].map(async key=>{
    const context=await browser.newContext();const page=await context.newPage();await page.goto(web);
    await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
    await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();return {context,page};
  }));
  const [gv,tbm,sv,member,admin]=actors.map(x=>x.page);
  try {
    const round=(await read(gv,"/rounds/open"))[0];
    let r=await post(gv,"/topics",{round_id:round.id,title:"Đăng ký có đơn Mẫu 1a và 1b",max_students:2});expect(r.status()).toBe(201);let topic=await r.json();
    topic=await(await post(gv,`/topics/${topic.id}/submit`,undefined,topic.row_version)).json();
    expect((await post(tbm,`/topics/${topic.id}/department-decision`,{decision:"APPROVE"},topic.row_version)).status()).toBe(200);
    r=await post(sv,"/topic-registrations",{topic_id:topic.id});expect(r.status()).toBe(201);const reg=await r.json();
    const base=`/topic-registrations/${reg.id}`;
    expect((await admin.request.get(api+base+"/forms")).status()).toBe(404);
    expect((await member.request.get(api+base+"/forms")).status()).toBe(404);
    await sv.goto(`${web}/registrations?focus=${reg.id}`);
    await sv.getByRole("link",{name:"Mở đơn Mẫu 1a/1b · nộp, tải & lịch sử",exact:true}).click();
    const forms=sv.locator(".registration-forms");
    await expect(forms.getByText("Mẫu áp dụng: 1a — cá nhân",{exact:true})).toBeVisible();
    const sourceA=process.env.KLTN_E2E_FORM_1A_FILE!;
    const submit=async(label:RegExp,file:string,version:number)=>{
      await forms.getByLabel(label).setInputFiles(file);
      const response=sv.waitForResponse(r=>r.request().method()==="POST"&&new URL(r.url()).pathname.endsWith(base+"/forms"),{timeout:120000});
      await forms.getByRole("button",{name:"Nộp phiên bản đơn",exact:true}).click();
      const uploaded=await response;expect(uploaded.status()).toBe(201);
      await expect(forms.getByText(new RegExp(`phiên bản ${version} ·`))).toBeVisible();
    };
    await submit(/Nộp đơn Mẫu 1a/,sourceA,1);
    let waiting=sv.waitForEvent("download");await forms.getByRole("button",{name:"Tải đơn gốc v1",exact:true}).click();
    let output=await waiting;const original=path.join(process.env.KLTN_E2E_RUN_DIR!,"application-original.docx");await output.saveAs(original);
    expect(await fs.readFile(original)).toEqual(await fs.readFile(sourceA));
    waiting=sv.waitForEvent("download");await forms.getByRole("button",{name:"Xuất bản nộp có footer v1",exact:true}).click();output=await waiting;
    await output.saveAs(path.join(process.env.KLTN_E2E_RUN_DIR!,"application-1a-print.docx"));
    await forms.getByText("Lịch sử xuất bản in v1",{exact:true}).click();
    await expect(forms.getByText("Bản nộp đăng ký — chưa xác nhận Khoa duyệt",{exact:true})).toBeVisible();
    await submit(/Nộp đơn Mẫu 1a/,sourceA,2);
    expect((await read(sv,base)).state).toBe("DRAFT");
    expect((await post(member,"/topic-registrations",{topic_id:topic.id})).status()).toBe(201);
    await forms.getByRole("button",{name:"Làm mới đơn đăng ký",exact:true}).click();
    await expect(forms.getByText("Mẫu áp dụng: 1b — theo nhóm",{exact:true})).toBeVisible();
    await expect(forms.getByRole("button",{name:/Xuất bản nộp có footer/})).toHaveCount(0);
    await submit(/Nộp đơn Mẫu 1b/,process.env.KLTN_E2E_FORM_1B_FILE!,3);
    waiting=sv.waitForEvent("download");await forms.getByRole("button",{name:"Xuất bản nộp có footer v3",exact:true}).click();output=await waiting;
    await output.saveAs(path.join(process.env.KLTN_E2E_RUN_DIR!,"application-1b-print.docx"));
    await sv.getByRole("link",{name:"Xem hồ sơ & quyết định đăng ký",exact:true}).click();
    await sv.getByRole("button",{name:"Gửi đăng ký cho GV",exact:true}).click();
    await gv.goto(`${web}/registrations?focus=${reg.id}`);
    await gv.getByRole("button",{name:"Chấp nhận chính thức và tạo khóa luận",exact:true}).click();
    await expect(gv.getByRole("link",{name:/Mở hồ sơ khóa luận/})).toBeVisible();
    const accepted=await read(gv,base);
    await sv.goto(`${web}/theses/${accepted.thesis_id}?section=submissions&kind=REGISTRATION`);
    await expect(forms.getByRole("button",{name:"Nộp phiên bản đơn",exact:true})).toHaveCount(0);
    await expect(forms.getByRole("button",{name:"Xuất bản nộp có footer v3",exact:true})).toBeEnabled();
  } finally {for(const actor of actors)await actor.context.close();}
});
