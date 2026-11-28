import {test, expect, type Page} from "@playwright/test";
import {readFile} from "node:fs/promises";
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
function syntheticPdf() {
  const stream = (text: string) => `<< /Length ${text.length} >>\nstream\n${text}\nendstream`;
  const objects = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    stream("BT /F1 20 Tf 60 700 Td (SYNTHETIC PROGRESS - PAGE ONE) Tj ET"),
    stream("BT /F1 20 Tf 60 700 Td (MEASUREMENTS - PAGE TWO) Tj ET")];
  let pdf = "%PDF-1.4\n"; const offsets = [0];
  objects.forEach((object, index) => {offsets.push(Buffer.byteLength(pdf)); pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;});
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n` + offsets.slice(1).map(offset => `${String(offset).padStart(10, "0")} 00000 n \n`).join("");
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(pdf);
}


async function listXlsx() {
 const zip=new JSZip();
 zip.file("[Content_Types].xml",`<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>`);
 zip.file("_rels/.rels",`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`);
 zip.file("xl/workbook.xml",`<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Danh sách DEMO" sheetId="1" r:id="r1"/></sheets></workbook>`);
 zip.file("xl/_rels/workbook.xml.rels",`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>`);
 zip.file("xl/worksheets/sheet1.xml",`<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>MSSV</t></is></c><c r="B1" t="inlineStr"><is><t>Họ tên</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>000123</t></is></c><c r="B2" t="inlineStr"><is><t>Sinh viên DEMO</t></is></c></row></sheetData></worksheet>`);
 return zip.generateAsync({type:"nodebuffer"});
}

test("Kho mẫu động: Admin cấp quyền, TBM cập nhật/phát hành, SV/GV xem đúng phạm vi và lịch sử",async({browser})=>{
 test.setTimeout(480000);
 const actors:{context:Awaited<ReturnType<typeof browser.newContext>>;page:Page}[]=[];
 async function login(key:string){const context=await browser.newContext(),page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(web);await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();actors.push({context,page});return page;}
 try {
  const admin=await login("admin"),manager=await login("tbm"),sv=await login("formStudent"),gv=await login("gv2");
  const round=(await read(manager,"/rounds/open"))[0],managerId=(await read(manager,"/me/context")).user_id;
  const originalSources = await read(admin, `/school-forms/rounds/${round.id}/sources`);
  expect(originalSources.some((source: {id:string}) => source.id === "hop-hoi-dong")).toBe(false);
  expect((await post(admin, "/school-forms", {
    round_id:round.id, code:"don-xin-thoi", title:"Đơn xin thôi thực hiện KLTN", document_kind:"FORM",
    audience:"STUDENT_AND_LECTURER", reason:"Synthetic existing withdrawal catalog entry",
  })).status()).toBe(201);
  await admin.goto(web+`/forms?round_id=${round.id}`);
  const adminRows = admin.getByRole("region", {name:"Danh mục biểu mẫu Khoa"}).locator("tbody tr");
  await expect(adminRows).toHaveCount(originalSources.length);
  await expect(adminRows.getByText("mau 2.Ke hoach thuc hien cua SV.docx", {exact:true})).toBeVisible();
  const withdrawalRow=adminRows.filter({hasText:"Đơn xin thôi thực hiện KLTN"});
  await expect(withdrawalRow).toHaveCount(1);
  await expect(withdrawalRow.getByText("Don_xin_thoi_thuc_hien_KLTN.docx", {exact:true})).toBeVisible();
  await expect(withdrawalRow.getByRole("button", {name:"Lịch sử phiên bản",exact:true})).toBeVisible();
  const desktopViewport = admin.viewportSize();
  for (const source of originalSources.filter((row: {id:string}) => ["mau-02", "mau-04", "don-xin-thoi"].includes(row.id))) {
    if (source.id === "mau-04") await admin.setViewportSize({width:390,height:900});
    const previewUrl = `**/school-forms/rounds/${round.id}/sources/${source.id}/preview`;
    await admin.route(previewUrl, route=>route.fulfill({contentType:"application/pdf",body:syntheticPdf(),headers:{
      "Access-Control-Allow-Origin":web,"Access-Control-Allow-Credentials":"true",
    }}));
    await admin.getByRole("button", {name:`Xem tệp nguồn ${source.title}`,exact:true}).click();
    const preview=admin.getByRole("dialog", {name:"Xem tài liệu Khoa"});
    await expect(preview.getByLabel("Nội dung PDF trang 1", {exact:true})).toBeVisible();
    await preview.getByRole("button", {name:"Trang sau của tài liệu",exact:true}).click();
    await expect(preview.getByLabel("Nội dung PDF trang 2", {exact:true})).toBeVisible();
    await expect(preview.getByRole("button", {name:"Tải tệp gốc",exact:true})).toBeEnabled();
    await preview.getByRole("button", {name:"Quay lại",exact:true}).click();
    await admin.unroute(previewUrl);
  }
  if (desktopViewport) await admin.setViewportSize(desktopViewport);
  await manager.goto(web+"/forms");await expect(manager.getByText("Thêm biểu mẫu hoặc tài liệu công bố",{exact:true})).toHaveCount(0);
  expect((await post(manager,"/school-forms",{round_id:round.id,code:"test-no-right",title:"No assignment",document_kind:"FORM",audience:"LECTURER",reason:"Synthetic denied attempt"})).status()).toBe(403);
  await admin.goto(web+"/administration/assignments");
  const assignment=admin.locator("section.card").filter({has:admin.getByRole("heading",{name:"Giao nhiệm vụ theo đợt",exact:true})});
  await assignment.getByRole("combobox",{name:"Đợt",exact:true}).selectOption(round.id);
  await assignment.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("FORM_MANAGER");
  await assignment.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption(managerId);
  await assignment.getByLabel("Căn cứ phân công",{exact:true}).fill("Khoa giao quản lý biểu mẫu cho TBM DEMO");
  await assignment.getByRole("button",{name:"Lưu phân công",exact:true}).click();
  await expect(admin.getByRole("status").filter({hasText:"Đã lưu phân công"})).toBeVisible();
  await manager.bringToFront();await manager.evaluate(()=>window.dispatchEvent(new Event("focus")));
  await expect(manager.getByRole("link",{name:"Quản lý kho biểu mẫu Khoa",exact:true})).toBeVisible();
  await manager.reload();
  const managerRows = manager.getByRole("region", {name:"Danh mục biểu mẫu Khoa"}).locator("tbody tr");
  await expect(managerRows).toHaveCount(originalSources.length);
  const originalPlan = managerRows.filter({hasText:"Mẫu 2 - Kế hoạch thực hiện của SV"});
  await expect(originalPlan.getByText("Tệp nguồn của Khoa", {exact:true})).toBeVisible();
  const sourceDownload = manager.waitForEvent("download");
  await originalPlan.getByRole("button",{name:"Tải tệp nguồn Mẫu 2 - Kế hoạch thực hiện của SV",exact:true}).click();
  expect((await sourceDownload).suggestedFilename()).toBe("mau 2.Ke hoach thuc hien cua SV.docx");
  await manager.getByText("Bổ sung mẫu nguồn vào đợt",{exact:true}).click();
  await manager.getByLabel("Tôi đã đối chiếu bộ mẫu nguồn được Khoa chấp thuận.",{exact:true}).check();
  await manager.getByRole("button",{name:"Bổ sung các mẫu còn thiếu",exact:true}).click();
  await expect(manager.getByRole("status").filter({hasText:"Đã bổ sung các mẫu gốc sẵn có"})).toBeVisible({timeout:300000});
  await expect(managerRows).toHaveCount(originalSources.length);
  await expect(originalPlan.getByRole("button",{name:"Lịch sử phiên bản",exact:true})).toBeVisible();
  await assignment.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("KLTN_COORDINATOR");
  await assignment.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption(managerId);
  await assignment.getByLabel("Căn cứ phân công",{exact:true}).fill("Khoa giao điều phối đợt DEMO");
  await assignment.getByRole("button",{name:"Lưu phân công",exact:true}).click();
  await expect(admin.getByRole("status").filter({hasText:"Đã lưu phân công"})).toBeVisible();
  await manager.goto(web+"/topics");
  await expect(manager.getByRole("link",{name:"Mốc & báo cáo tiến độ",exact:true})).toBeVisible();
  await expect(manager.getByText("Đợt này chưa có sinh viên đang thực hiện khóa luận.",{exact:false})).toBeVisible();
  await expect(manager.getByRole("button",{name:"Xuất danh sách đã điền theo Mẫu 4",exact:true})).toBeDisabled();
  await admin.goto(web+"/forms?round_id="+round.id);
  await admin.getByRole("link",{name:"Xuất danh sách theo Mẫu 4",exact:true}).click();
  await expect(admin.getByText("Đợt này chưa có sinh viên đang thực hiện khóa luận.",{exact:false})).toBeVisible();
  await expect(admin.getByRole("button",{name:"Xuất danh sách đã điền theo Mẫu 4",exact:true})).toBeDisabled();
  await manager.goto(web+`/forms?round_id=${round.id}`);
  const roundForms = `/forms?round_id=${round.id}`;
  await sv.goto(web+roundForms);
  await expect(sv.getByRole("heading",{name:"Tài liệu Khoa công bố",exact:true})).toBeVisible();
  await expect(sv.getByRole("heading",{name:"Chưa có tài liệu trong phạm vi này",exact:true})).toBeVisible();
  await gv.goto(web+roundForms);
  await expect(gv.getByRole("heading",{name:"Chưa có tài liệu trong phạm vi này",exact:true})).toBeVisible();
  const catalog = await read(manager,`/school-forms?round_id=${round.id}`);
  const planForm = catalog.find((item:any)=>item.code==="mau-02");
  await sv.goto(web+roundForms+`&form_id=${planForm.id}`);
  await expect(sv.locator(".table-container table tbody tr")).toHaveCount(1);
  const directRow=sv.locator(".table-container table tbody tr").filter({hasText:"Mẫu 2 - Kế hoạch thực hiện của SV"});
  await expect(directRow.locator("td").nth(5)).toHaveCSS("white-space","nowrap");
  const studentActionsWidth=await directRow.locator("td").nth(5).evaluate(node=>node.getBoundingClientRect().width);
  expect(studentActionsWidth).toBeLessThan(195);
  await expect(directRow.getByRole("button",{name:"Xem trực tiếp",exact:true})).toHaveCount(0);
  const directDownload=sv.waitForEvent("download");
  await directRow.getByRole("button",{name:"Tải tệp gốc",exact:true}).click();
  expect((await directDownload).suggestedFilename()).toMatch(/\.docx$/i);
  expect((await read(sv,"/theses")).length).toBe(0); // Forms work before a thesis exists.
  const lecturerForm=catalog.find((item:any)=>item.code==="mau-06");
  expect((await sv.request.get(api+`/school-forms/${lecturerForm.id}/versions/${lecturerForm.versions[0].id}/download`)).status()).toBe(404);
  const title="Mẫu 2 - Kế hoạch thực hiện của SV";
  const card=(page:Page)=>page.locator(".school-form-card").filter({has:page.getByRole("heading",{name:title,exact:true})});
  const choose=async(page:Page,title:string)=>{const row=page.locator(".table-container table tbody tr").filter({hasText:title});const button=row.getByRole("button",{name:/Lịch sử phiên bản|Thu gọn/});if(await button.textContent()!=="Thu gọn")await button.click();};
  await choose(sv,title);
  const managerRow=manager.locator(".table-container table tbody tr").filter({hasText:title});
  await expect(managerRow.locator("td").nth(5)).toHaveCSS("white-space","nowrap");
  const managerActionsWidth=await managerRow.locator("td").nth(5).evaluate(node=>node.getBoundingClientRect().width);
  expect(managerActionsWidth).toBeLessThan(240);
  await managerRow.getByRole("button",{name:"Cập nhật tệp",exact:true}).click();
  await card(manager).getByLabel("Lý do thao tác / cập nhật phiên bản",{exact:true}).fill("Khoa điều chỉnh Mẫu 2 theo góp ý DEMO");
  await card(manager).getByLabel("Nguồn / văn bản áp dụng",{exact:true}).fill("Thông báo Khoa DEMO 28/10");
  const updated=syntheticPdf();await card(manager).getByLabel("Tải phiên bản mới (PDF/DOCX/XLSX)",{exact:true}).setInputFiles({name:"mau-2-cap-nhat.pdf",mimeType:"application/pdf",buffer:updated});
  await card(manager).getByRole("button",{name:"Lưu bản nháp",exact:true}).click();
  await expect(card(manager).getByRole("button",{name:"Phát hành v2",exact:true})).toBeEnabled();
  await sv.getByRole("button",{name:"Làm mới kho",exact:true}).click();await expect(card(sv).getByText("v2 · mau-2-cap-nhat.pdf",{exact:true})).toHaveCount(0);
  await card(manager).getByRole("button",{name:"Phát hành v2",exact:true}).click();
  await expect(manager.getByRole("status").filter({hasText:"Đã phát hành"})).toBeVisible();
  await sv.getByRole("button",{name:"Làm mới kho",exact:true}).click();await expect(card(sv).getByText("v2 · mau-2-cap-nhat.pdf",{exact:true})).toBeVisible();
  await card(sv).getByRole("button",{name:"Xem trực tiếp",exact:true}).first().click();
  await expect(sv.getByRole("dialog").getByLabel("Nội dung PDF trang 1",{exact:true})).toBeVisible();
  await sv.getByRole("dialog").getByRole("button",{name:"Quay lại",exact:true}).click();
  expect(await(await sv.request.get(api+`/form-templates/plan?round_id=${round.id}`)).body()).toEqual(updated);
  await expect(card(sv).getByText("Lịch sử phiên bản (1 bản trước)",{exact:true})).toBeVisible();await card(sv).locator("details details > summary").first().click();
  await expect(card(sv).getByRole("button",{name:"Tải tệp v1",exact:true})).toBeEnabled();
  // A filled Excel publication is a separate catalog item, not an import action or a blank form.
  await manager.getByText("Thêm biểu mẫu hoặc tài liệu công bố",{exact:true}).click();
  const create=manager.locator("form").filter({has:manager.getByRole("button",{name:"Tạo và lưu tệp nháp",exact:true})});
  await create.getByLabel("Mã tài liệu",{exact:true}).fill("ds-sv-da-chot");await create.getByLabel("Tên tài liệu",{exact:true}).fill("Danh sách SV đã chốt DEMO");
  await create.getByLabel("Phân loại",{exact:true}).selectOption("PUBLICATION");await create.getByLabel("Lý do tạo danh mục",{exact:true}).fill("Khoa công bố danh sách sinh viên DEMO theo đợt");
  await create.getByLabel("Nguồn / văn bản áp dụng",{exact:true}).fill("Quyết định DEMO 28/10");
  const xlsx=await listXlsx();await create.getByLabel("Tệp biểu mẫu hoặc tài liệu (PDF, DOCX, XLSX)",{exact:true}).setInputFiles({name:"danh-sach-chot.xlsx",mimeType:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",buffer:xlsx});
  await create.getByRole("button",{name:"Tạo và lưu tệp nháp",exact:true}).click();
  const list=manager.locator(".school-form-card").filter({has:manager.getByRole("heading",{name:"Danh sách SV đã chốt DEMO",exact:true})});
  await expect(list.getByRole("button",{name:"Phát hành v1",exact:true})).toBeEnabled();await list.getByRole("button",{name:"Phát hành v1",exact:true}).click();
  await expect(manager.getByRole("status").filter({hasText:"Đã phát hành"})).toBeVisible();
  await sv.getByRole("button",{name:"Làm mới kho",exact:true}).click();
  await choose(sv,"Danh sách SV đã chốt DEMO");
  const studentList=sv.locator(".school-form-card").filter({has:sv.getByRole("heading",{name:"Danh sách SV đã chốt DEMO",exact:true})});
  await expect(studentList.getByRole("button",{name:"Xem trực tiếp",exact:true})).toHaveCount(0);
  const excelDownload=sv.waitForEvent("download");
  await studentList.getByRole("button",{name:"Tải tệp v1",exact:true}).click();
  expect(await readFile(await (await excelDownload).path())).toEqual(xlsx);
  await sv.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,"school-publication-excel.png")});
  expect((await read(admin,"/admin/users/directory?search=000123&limit=10")).total).toBe(0);
  // No publication leak to a different, not-yet-enrolled round, including direct URLs.
  let response=await post(admin,"/admin/rounds",{academic_year_code:"2031-2032",year_starts_on:"2031-08-01",year_ends_on:"2032-07-31",code:"OTHER-DEMO",round_type:"MAIN",opens_at:"2031-08-15T00:00:00Z",closes_at:"2031-08-31T00:00:00Z",basis_ref:"Synthetic second round"});
  expect(response.status()).toBe(201);const other=await response.json();
  expect((await post(admin,"/admin/round-assignments",{round_id:other.id,user_id:managerId,assignment_type:"FORM_MANAGER",basis_ref:"Synthetic second-round assignment"})).status()).toBe(201);
  response=await post(manager,"/school-forms",{round_id:other.id,code:"ds-other",title:"Danh sách đợt khác",document_kind:"PUBLICATION",audience:"STUDENT_AND_LECTURER",reason:"Synthetic other-round list"});expect(response.status()).toBe(201);let privateItem=await response.json();
  const auth=await read(manager,"/me/context");response=await manager.request.post(api+`/school-forms/${privateItem.id}/versions`,{multipart:{source_reference:"DEMO",reason:"Other-round-list",file:{name:"other.xlsx",mimeType:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",buffer:xlsx}},headers:{"X-CSRF-Token":auth.csrf_token,"If-Match":String(privateItem.row_version)}});expect(response.status()).toBe(201);privateItem=await response.json();
  expect((await post(manager,`/school-forms/${privateItem.id}/versions/${privateItem.versions[0].id}/publish`,{reason:"Publish synthetic other-round list"},privateItem.versions[0].row_version)).status()).toBe(200);
  expect((await sv.request.get(api+`/school-forms/${privateItem.id}/versions/${privateItem.versions[0].id}/spreadsheet`)).status()).toBe(404);
  expect((await gv.request.get(api+`/school-forms/${privateItem.id}/versions/${privateItem.versions[0].id}/download`)).status()).toBe(404);
  await manager.screenshot({path:test.info().outputPath("forms-manager.png"),fullPage:true});
  await sv.screenshot({path:test.info().outputPath("forms-student.png"),fullPage:true});
  // Admin has catalog rights without a per-round assignment; removal preserves versions.
  await admin.goto(web+`/forms?round_id=${round.id}`);
  const adminRow=admin.locator(".table-container table tbody tr").filter({hasText:title});
  await adminRow.getByRole("button",{name:"Lịch sử phiên bản",exact:true}).click();
  await card(admin).getByText("Sửa tên / đối tượng xem",{exact:true}).click();
  await expect(card(admin).getByLabel("Tên hiển thị",{exact:true})).toBeVisible();
  await card(admin).getByLabel("Lý do sửa danh mục",{exact:true}).fill("Admin xác nhận thông tin biểu mẫu DEMO");
  await card(admin).getByRole("button",{name:"Lưu danh mục",exact:true}).click();
  await expect(admin.getByRole("status").filter({hasText:"Đã cập nhật danh mục"})).toBeVisible();
  await adminRow.getByRole("button",{name:"Gỡ khỏi kho",exact:true}).click();
  await card(admin).getByLabel("Lý do gỡ / khôi phục",{exact:true}).fill("Tạm gỡ mẫu DEMO để đối chiếu");
  await card(admin).getByRole("button",{name:"Xác nhận gỡ khỏi kho",exact:true}).click();
  await expect(admin.getByRole("status").filter({hasText:"Đã gỡ khỏi kho"})).toBeVisible();
  await sv.getByRole("button",{name:"Làm mới kho",exact:true}).click();
  await expect(sv.locator(".table-container table tbody tr").filter({hasText:title})).toHaveCount(0);
  expect((await sv.request.get(api+`/form-templates/plan?round_id=${round.id}`)).status()).toBe(403);
  await adminRow.getByRole("button",{name:"Khôi phục",exact:true}).click();
  await card(admin).getByLabel("Lý do gỡ / khôi phục",{exact:true}).fill("Khôi phục mẫu DEMO đã đối chiếu");
  await card(admin).getByRole("button",{name:"Xác nhận khôi phục",exact:true}).click();
  await expect(admin.getByRole("status").filter({hasText:"Đã khôi phục"})).toBeVisible();
  await sv.getByRole("button",{name:"Làm mới kho",exact:true}).click();
  await expect(sv.locator(".table-container table tbody tr").filter({hasText:title})).toHaveCount(1);
  await manager.getByRole("button",{name:"Làm mới kho",exact:true}).click();
  // Withdrawal never silently brings the old local template back.
  await choose(manager,title);
  await card(manager).getByText("Thu hồi v2",{exact:true}).click();await card(manager).getByLabel("Lý do thu hồi phiên bản",{exact:true}).first().fill("Khoa thu hồi mẫu DEMO đang điều chỉnh");
  await card(manager).getByRole("button",{name:"Xác nhận thu hồi v2",exact:true}).click();await expect(manager.getByRole("status").filter({hasText:"Đã thu hồi"})).toBeVisible();
  expect((await sv.request.get(api+`/form-templates/plan?round_id=${round.id}`)).status()).toBe(409);
  const assigned=(await read(admin,"/admin/round-assignments")).find((row:any)=>row.assignment_type==="FORM_MANAGER" && row.user_id===managerId && row.round_id===round.id);
  expect((await post(admin,`/admin/round-assignments/${assigned.id}/revoke`,{reason:"Kết thúc phân công DEMO"})).status()).toBe(204);
  expect((await post(manager,"/school-forms",{round_id:round.id,code:"not-authorized",title:"Forbidden after revoke",document_kind:"FORM",audience:"LECTURER",reason:"Synthetic revoked attempt"})).status()).toBe(403);
  const otherAssigned=(await read(admin,"/admin/round-assignments")).find((row:any)=>row.assignment_type==="FORM_MANAGER" && row.user_id===managerId && row.round_id===other.id);
  expect((await post(admin,`/admin/round-assignments/${otherAssigned.id}/revoke`,{reason:"End second round synthetic assignment"})).status()).toBe(204);
  await manager.bringToFront();await manager.evaluate(()=>window.dispatchEvent(new Event("focus")));
  await expect(manager.getByRole("link",{name:"Quản lý kho biểu mẫu Khoa",exact:true})).toHaveCount(0);
  await expect(manager.getByText("Thêm biểu mẫu hoặc tài liệu công bố",{exact:true})).toHaveCount(0);
  // Both roster duties and student account management expose only their matching menu.
  for (const [kind,label] of [["ELIGIBILITY_IMPORTER","Danh sách sinh viên"],["ELIGIBILITY_VERIFIER","Danh sách sinh viên"],["ACCOUNT_MANAGER","Quản lý tài khoản"]]) {
    const grant=await post(admin,"/admin/round-assignments",{round_id:round.id,user_id:managerId,assignment_type:kind,basis_ref:"Synthetic navigation permission check"});expect(grant.status()).toBe(201);
    const granted=await grant.json();
    const link=manager.getByRole("navigation",{name:"Chức năng"}).getByRole("link",{name:label,exact:true});
    await manager.bringToFront();await manager.evaluate(()=>window.dispatchEvent(new Event("focus")));
    await expect(link).toBeVisible();
    await link.click();
    await expect(manager.getByRole("heading",{name:kind==="ACCOUNT_MANAGER"?"Tài khoản sinh viên theo đợt":"Danh sách đủ điều kiện",exact:false}).first()).toBeVisible();
    expect((await post(admin,`/admin/round-assignments/${granted.assignment_id}/revoke`,{reason:"End synthetic menu check"})).status()).toBe(204);
    await manager.bringToFront();await manager.evaluate(()=>window.dispatchEvent(new Event("focus")));
    await expect(link).toHaveCount(0);
  }
 } finally {for(const actor of actors)await actor.context.close();}
});
