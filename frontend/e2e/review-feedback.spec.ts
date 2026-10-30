import {test, expect, type Page} from "@playwright/test";
import path from "node:path";
import JSZip from "jszip";

const accounts = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = `http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;
const api = `http://127.0.0.1:${process.env.KLTN_E2E_API_PORT || "8001"}/api/v1`;
async function read(page: Page, url: string) {const response = await page.request.get(api + url); expect(response.status()).toBe(200); return response.json();}
async function post(page: Page, url: string, data?: unknown, version?: number) {
  const auth = await read(page, "/me/context");
  return page.request.post(api + url, {data, headers: {"X-CSRF-Token": auth.csrf_token, ...(version === undefined ? {} : {"If-Match": String(version)})}});
}
function syntheticPdf(feedback=false) {
  const stream = (text: string) => `<< /Length ${text.length} >>\nstream\n${text}\nendstream`;
  const objects = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    stream("BT /F1 20 Tf 60 700 Td (SYNTHETIC PROGRESS - PAGE ONE) Tj ET"),
    stream("BT /F1 20 Tf 60 700 Td (MEASUREMENTS - PAGE TWO) Tj ET")];
  if(feedback) {
    objects[3]=objects[3].replace("/Contents 7 0 R >>","/Contents 7 0 R /Annots [8 0 R] >>");
    objects.push("<< /Type /Annot /Subtype /Text /Rect [80 660 105 685] /T (Demo lecturer) /Contents (Add evidence for this conclusion.) /P 4 0 R /Open false >>");
  }
  let pdf = "%PDF-1.4\n"; const offsets = [0];
  objects.forEach((object, index) => {offsets.push(Buffer.byteLength(pdf)); pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;});
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n` + offsets.slice(1).map(offset => `${String(offset).padStart(10, "0")} 00000 n \n`).join("");
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(pdf);
}


async function feedbackDocx() {
  const zip=new JSZip();
  zip.file("[Content_Types].xml",`<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/></Types>`);
  zip.file("_rels/.rels",`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>`);
  zip.file("word/_rels/document.xml.rels",`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rComment" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/></Relationships>`);
  zip.file("word/document.xml",`<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:commentRangeStart w:id="0"/><w:r><w:t>Section needing a clearer explanation.</w:t></w:r><w:commentRangeEnd w:id="0"/><w:r><w:commentReference w:id="0"/></w:r></w:p><w:p><w:del w:id="1" w:author="GV Demo"><w:r><w:delText>Old sentence to remove.</w:delText></w:r></w:del><w:ins w:id="2" w:author="GV Demo"><w:r><w:t>Suggested replacement from lecturer.</w:t></w:r></w:ins></w:p><w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body></w:document>`);
  zip.file("word/comments.xml",`<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:comment w:id="0" w:author="GV Demo" w:date="2026-10-28T10:00:00Z"><w:p><w:r><w:t>Giải thích rõ phương pháp ở câu này. https://example.org/method</w:t></w:r></w:p></w:comment></w:comments>`);
  return zip.generateAsync({type:"nodebuffer"});
}

test("Tệp GV phản hồi, Word/PDF comments, nháp chung trên máy chủ và chỉ công bố khi hoàn thành",async({browser})=>{
  test.setTimeout(180000);
  const actors:{context:Awaited<ReturnType<typeof browser.newContext>>;page:Page}[]=[];
  async function login(key:string) {
    const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(20000);
    await page.goto(web);await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);
    await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
    await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
    actors.push({context,page});return page;
  }
  try {
    const gv=await login("gv2"),tbm=await login("tbm"),sv=await login("nv5Student"),admin=await login("admin");
    const round=(await read(gv,"/rounds/open"))[0];
    let response=await post(gv,"/topics",{round_id:round.id,title:"DEMO tệp giảng viên phản hồi",max_students:1});expect(response.status()).toBe(201);
    let topic=await response.json();topic=await(await post(gv,`/topics/${topic.id}/submit`,undefined,topic.row_version)).json();
    expect((await post(tbm,`/topics/${topic.id}/department-decision`,{decision:"APPROVE"},topic.row_version)).status()).toBe(200);
    let reg=await(await post(sv,"/topic-registrations",{topic_id:topic.id})).json();
    reg=await(await post(sv,`/topic-registrations/${reg.id}/submit`)).json();
    reg=await(await post(gv,`/topic-registrations/${reg.id}/lecturer-decision`,{decision:"ACCEPT"},reg.row_version)).json();
    expect(reg.state).toBe("FINALIZED");const base=`/theses/${reg.thesis_id}`;
    expect((await post(admin,"/admin/round-assignments",{round_id:round.id,user_id:(await read(tbm,"/me/context")).user_id,assignment_type:"KLTN_COORDINATOR",basis_ref:"Synthetic feedback UI test"})).status()).toBe(201);
    response=await post(tbm,base+"/milestones",{code:"FEEDBACK",title:"Mốc phản hồi có tệp",due_at:new Date(Date.now()+86400000).toISOString()});expect(response.status()).toBe(201);
    const milestone=await response.json(),pdf=syntheticPdf();
    await sv.goto(`${web}${base}?section=progress`);
    await sv.getByLabel("Mốc báo cáo",{exact:true}).selectOption(milestone.id);
    await sv.getByLabel("Kết quả, khó khăn và kế hoạch",{exact:true}).fill("Bản sinh viên cần giảng viên xem tệp");
    await sv.getByLabel("Tiến độ tự báo cáo (%)",{exact:true}).fill("45");
    await sv.getByLabel(/Minh chứng tiến độ từ máy/).setInputFiles({name:"source-v1.pdf",mimeType:"application/pdf",buffer:pdf});
    await sv.getByRole("button",{name:"Gửi báo cáo",exact:true}).click();
    await expect(sv.getByRole("button",{name:"Xem tệp & nhận xét",exact:true})).toBeVisible();
    const report=(await read(sv,base+"/progress-reports"))[0];expect(report.evidence_scan_state).toBe("CLEAN");
    const notes=base+`/progress-reports/${report.id}/annotations`;
    await gv.goto(`${web}${base}?section=progress`);
    await gv.getByRole("button",{name:"Mở tệp và phản hồi theo vị trí",exact:true}).click();
    let modal=gv.getByRole("dialog");
    const conclusion="Đề nghị sửa theo tệp và ghim. https://example.org/reference";
    await modal.getByLabel("Nhận xét tổng quát",{exact:true}).fill(conclusion);
    await modal.getByRole("button",{name:"Theo mục",exact:true}).click();
    await modal.getByLabel("Góp ý cần thực hiện",{exact:true}).fill("Xem cách trình bày tại https://example.org/layout");
    await modal.getByLabel(/Đính kèm bản đã nhận xét/).setInputFiles({name:"gv-nhan-xet.pdf",mimeType:"application/pdf",buffer:syntheticPdf(true)});
    await expect(modal.locator(".review-feedback-file").filter({hasText:"gv-nhan-xet.pdf"}).getByRole("button",{name:"Xem bản GV nhận xét",exact:true})).toBeEnabled();
    await modal.getByLabel(/Đính kèm bản đã nhận xét/).setInputFiles({name:"gv-nhan-xet.docx",mimeType:"application/vnd.openxmlformats-officedocument.wordprocessingml.document",buffer:await feedbackDocx()});
    await expect(modal.locator(".review-feedback-file")).toHaveCount(2);
    await expect(modal.locator(".review-feedback-file").filter({hasText:"gv-nhan-xet.docx"}).getByRole("button",{name:"Xem bản GV nhận xét",exact:true})).toBeEnabled();
    await modal.getByRole("button",{name:"Quay lại",exact:true}).click();
    expect((await read(sv,notes)).annotations).toEqual([]);
    const drafts=(await read(gv,notes)).annotations;
    expect(drafts.find((note:any)=>note.annotation_kind === "SUMMARY").comment).toBe(conclusion);
    const file=drafts.find((note:any)=>note.annotation_kind === "ATTACHMENT");
    expect((await sv.request.get(api+notes+`/${file.id}/attachment`)).status()).toBe(404);
    await sv.getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    await expect(sv.getByRole("dialog").getByLabel("Tệp GV phản hồi",{exact:true})).toHaveCount(0);
    await sv.getByRole("dialog").getByRole("button",{name:"Quay lại",exact:true}).click();

    // A new browser context has no local draft/cache: the server must restore the summary and files.
    const fresh=await login("gv2");await fresh.goto(`${web}${base}?section=progress`);
    await fresh.getByRole("button",{name:"Mở tệp và phản hồi theo vị trí",exact:true}).click();modal=fresh.getByRole("dialog");
    await expect(modal.getByLabel("Nhận xét tổng quát",{exact:true})).toHaveValue(conclusion);
    await expect(modal.locator(".review-feedback-file")).toHaveCount(2);
    await modal.locator(".review-feedback-file").filter({hasText:"gv-nhan-xet.docx"}).getByRole("button",{name:"Xem bản GV nhận xét",exact:true}).click();
    const preview=modal.getByRole("region",{name:"Bản GV đã nhận xét",exact:true});
    await expect(preview.getByText("Giải thích rõ phương pháp ở câu này.",{exact:false})).toBeVisible();
    await expect(preview.locator(".review-text-sheet ins")).toContainText("Suggested replacement from lecturer.");
    await expect(preview.locator(".review-text-sheet del")).toContainText("Old sentence to remove.");
    await preview.getByRole("button",{name:"Về bản SV",exact:true}).click();
    await modal.locator(".review-feedback-file").filter({hasText:"gv-nhan-xet.pdf"}).getByRole("button",{name:"Xem bản GV nhận xét",exact:true}).click();
    await preview.getByRole("button",{name:"Trang phản hồi sau",exact:true}).click();
    await expect(preview.getByText("Add evidence for this conclusion.",{exact:true})).toBeVisible();
    await preview.getByRole("button",{name:"Về bản SV",exact:true}).click();
    await modal.getByLabel("Kết quả",{exact:true}).selectOption("REVISION_REQUIRED");
    await modal.getByRole("button",{name:"Hoàn thành và gửi góp ý",exact:true}).click();
    await expect(modal).toHaveCount(0);
    const published=(await read(sv,notes)).annotations;
    expect(published.filter((note:any)=>note.annotation_kind === "ATTACHMENT")).toHaveLength(2);
    expect(published.every((note:any)=>note.state === "PUBLISHED")).toBe(true);
    await sv.reload();await sv.getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    const studentModal=sv.getByRole("dialog");await expect(studentModal.locator(".review-feedback-file")).toHaveCount(2);
    await expect(studentModal.getByRole("link",{name:"https://example.org/layout",exact:true})).toHaveAttribute("href","https://example.org/layout");
    await expect(studentModal.getByRole("button",{name:"Hoàn thành và gửi góp ý",exact:true})).toHaveCount(0);
    await studentModal.locator(".review-feedback-file").filter({hasText:"gv-nhan-xet.docx"}).getByRole("button",{name:"Xem bản GV nhận xét",exact:true}).click();
    await expect(studentModal.getByRole("region",{name:"Bản GV đã nhận xét",exact:true}).getByText("Giải thích rõ phương pháp ở câu này.",{exact:false})).toBeVisible();
    await sv.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,"student-lecturer-feedback.png")});
    expect(await(await sv.request.get(api+base+`/progress-reports/${report.id}/evidence`)).body()).toEqual(pdf);
  } finally {for(const actor of actors)await actor.context.close();}
});
