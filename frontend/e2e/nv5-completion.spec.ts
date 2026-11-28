import {test,expect,type Page} from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
import JSZip from "jszip";

// All setup and assertions use the real API and PostgreSQL fixture; no route mocks.
const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web=`http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;
const api=`http://127.0.0.1:${process.env.KLTN_E2E_API_PORT || "8001"}/api/v1`;
const local=(date:Date)=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}-${String(date.getDate()).padStart(2,"0")}T${String(date.getHours()).padStart(2,"0")}:${String(date.getMinutes()).padStart(2,"0")}`;
async function read(page:Page,url:string) {const r=await page.request.get(api+url);expect(r.status()).toBe(200);return r.json();}
async function post(page:Page,url:string,data?:unknown,version?:number) {
  const auth=await read(page,"/me/context");
  return page.request.post(api+url,{data,headers:{"X-CSRF-Token":auth.csrf_token,...(version===undefined?{}:{"If-Match":String(version)})}});
}
async function review(page:Page,scope:ReturnType<Page["locator"]>,decision:string,comment:string) {
  await expect(scope).toBeVisible();
  const open = scope.getByRole("button", {name:/^(Mở tệp và phản hồi theo vị trí|Xem tệp & nhận xét)$/});
  if (await page.getByRole("dialog").count()) scope = page.getByRole("dialog");
  else if (await open.count()) {await open.click(); scope = page.getByRole("dialog");}
  await scope.getByLabel("Kết quả",{exact:true}).selectOption(decision);
  await scope.getByLabel(await scope.getByLabel("Nhận xét tổng quát",{exact:true}).count() ? "Nhận xét tổng quát" : "Nhận xét / lý do",{exact:true}).fill(comment);
  const inWorkspace = await page.getByRole("dialog").count() > 0;
  await scope.getByRole("button",{name:/^(Gửi kết quả|Hoàn thành và gửi góp ý)/}).click();
  if (inWorkspace) await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("status").filter({hasText:/Đã lưu|Đã chốt|Đã đóng|Đã gửi phản hồi/})).toBeVisible();
}
async function savedDownload(page:Page,button:ReturnType<Page["getByRole"]>,filename:string) {
  const waiting=page.waitForEvent("download");await button.click();const download=await waiting;
  const output=path.join(process.env.KLTN_E2E_RUN_DIR!,filename);await download.saveAs(output);return output;
}

test("NV5 hoàn chỉnh: trễ, gia hạn, sửa sau đóng, riêng tư theo GVHD, tài liệu và bản in mẫu chính thức",async({browser})=>{
  test.setTimeout(360000);
  expect(process.env.KLTN_E2E_PLAN_FILE,"Mẫu 2 chính thức phải có để kiểm bản xuất").toBeTruthy();
  expect(process.env.KLTN_E2E_PROPOSAL_FILE,"Mẫu 3 chính thức phải có để kiểm bản xuất").toBeTruthy();
  const contexts=await Promise.all(["admin","tbm","gv2","gv","nv5Student","nv5Outsider"].map(async key=>{
    const context=await browser.newContext();const page=await context.newPage();
    page.setDefaultTimeout(20000);
    await page.goto(web);await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);
    await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
    await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();return {context,page};
  }));
  const [admin,tbm,gv,peer,sv,outsider]=contexts.map(x=>x.page);
  try {
    const round=(await read(gv,"/rounds/open"))[0];
    let r=await post(gv,"/topics",{round_id:round.id,title:"NV5 kiểm thử sau tiếp nhận",max_students:1});expect(r.status()).toBe(201);let topic=await r.json();
    topic=await(await post(gv,`/topics/${topic.id}/submit`,undefined,topic.row_version)).json();
    expect((await post(tbm,`/topics/${topic.id}/department-decision`,{decision:"APPROVE"},topic.row_version)).status()).toBe(200);
    r=await post(sv,"/topic-registrations",{topic_id:topic.id});expect(r.status()).toBe(201);let reg=await r.json();
    // Optional registration evidence must pass the same real scanner as thesis files.
    const proof = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a8ZsAAAAASUVORK5CYII=", "base64");
    await sv.goto(web + "/registrations");
    await sv.getByLabel(/Minh chứng của tôi \(tùy chọn\)/).setInputFiles({name:"minh-chung-dang-ky.png",mimeType:"image/png",buffer:proof});
    await sv.getByRole("button",{name:"Tải lên",exact:true}).click();
    await expect(sv.getByRole("link",{name:"Tải minh chứng: minh-chung-dang-ky.png",exact:true})).toBeVisible();
    reg = await read(sv,`/topic-registrations/${reg.id}`);
    reg=await(await post(sv,`/topic-registrations/${reg.id}/submit`)).json();
    r=await post(gv,`/topic-registrations/${reg.id}/lecturer-decision`,{decision:"ACCEPT"},reg.row_version);expect(r.status()).toBe(200);reg=await r.json();
    expect(reg.state).toBe("FINALIZED");const id=reg.thesis_id;expect(id).toBeTruthy();
    await gv.goto(web + "/registrations");
    const evidenceWait = gv.waitForEvent("download");
    await gv.getByRole("link",{name:"Tải minh chứng: minh-chung-dang-ky.png",exact:true}).click();
    const proofDownload = await evidenceWait;
    const proofPath = path.join(process.env.KLTN_E2E_RUN_DIR!,"registration-proof.png");
    await proofDownload.saveAs(proofPath);
    expect(await fs.readFile(proofPath)).toEqual(proof);
    const base=`/theses/${id}`;
    await sv.goto(web+"/registrations");await sv.getByRole("link",{name:/Mở hồ sơ khóa luận/}).click();
    await expect(sv.getByRole("heading",{name:/^(GVHD chính thức|Giảng viên hướng dẫn chính thức)$/})).toBeVisible();
    expect((await outsider.request.get(api+base)).status()).toBe(404);
    expect((await admin.request.get(api+base)).status()).toBe(404);

    // Coordinator is assigned through the real administration form.
    await admin.goto(web+"/administration/assignments");
    const assignment=admin.locator("section.card").filter({has:admin.getByRole("heading",{name:"Giao nhiệm vụ theo đợt",exact:true})});
    await assignment.getByRole("combobox",{name:"Đợt",exact:true}).selectOption(round.id);
    await assignment.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("KLTN_COORDINATOR");
    await assignment.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption((await read(tbm,"/me/context")).user_id);
    await assignment.getByLabel("Căn cứ phân công").fill("Khoa giao điều phối NV5");
    await assignment.getByRole("button",{name:"Lưu phân công",exact:true}).click();
    await expect(admin.getByRole("status").filter({hasText:"Đã lưu phân công"})).toBeVisible();
    await tbm.goto(web + "/progress");
    const thesisLink = tbm.getByRole("link", {name: "NV5 kiểm thử sau tiếp nhận", exact: true});
    const milestoneCode = tbm.getByLabel("Mã mốc", {exact: true});
    await expect(thesisLink.or(milestoneCode)).toBeVisible();
    if (await thesisLink.isVisible()) await thesisLink.click();
    await expect(tbm).toHaveURL(new RegExp(`${id}.*section=progress`));
    await tbm.getByLabel("Mã mốc",{exact:true}).fill("NV5_LATE");
    await tbm.getByLabel("Tên mốc",{exact:true}).fill("Mốc báo cáo NV5");
    await tbm.getByLabel("Hạn nộp (giờ Việt Nam)",{exact:true}).fill(local(new Date(Date.now()-3600000)));
    await tbm.getByRole("button",{name:"Mở mốc cho đợt",exact:true}).click();
    await expect(tbm.getByRole("heading",{name:"Mốc báo cáo NV5 · v1",exact:true})).toBeVisible();

    await sv.getByRole("tab",{name:"Báo cáo tiến độ",exact:true}).click();
    await sv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await sv.getByLabel("Mốc báo cáo",{exact:true}).selectOption({label:"Mốc báo cáo NV5 · v1"});
    await sv.getByLabel("Kết quả, khó khăn và kế hoạch",{exact:true}).fill("Báo cáo nộp trễ có minh chứng");
    await sv.getByLabel("Tiến độ tự báo cáo (%)",{exact:true}).fill("25");
    await sv.getByLabel(/Minh chứng tiến độ từ máy/).setInputFiles({name:"minh-chung-v1.txt",mimeType:"text/plain",buffer:Buffer.from("SYNTHETIC NV5 PROGRESS V1")});
    await sv.getByRole("button",{name:"Gửi báo cáo",exact:true}).click();
    const report1=sv.locator("article.card").filter({has:sv.getByText("Báo cáo nộp trễ có minh chứng",{exact:true})});
    await expect(report1.getByLabel("Nộp trễ",{exact:true})).toBeVisible();
    await expect(report1.getByRole("button",{name:"Tải minh chứng của báo cáo",exact:true})).toBeEnabled();
    await expect(sv.getByRole("heading",{name:"Chưa có mốc bạn có thể nộp lúc này",exact:true})).toBeVisible();
    await expect(sv.getByRole("button",{name:"Gửi báo cáo",exact:true})).toHaveCount(0);
    await sv.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,"nv5-progress-student.png"),fullPage:true});

    // Extending the round does not rewrite the first report's original lateness.
    const milestone=tbm.locator("article.card").filter({has:tbm.getByRole("heading",{name:"Mốc báo cáo NV5 · v1",exact:true})});
    await milestone.getByText("Gia hạn cho toàn đợt",{exact:true}).click();
    await milestone.getByLabel("Hạn mới (giờ Việt Nam)",{exact:true}).fill(local(new Date(Date.now()+86400000)));
    await milestone.getByLabel("Lý do gia hạn",{exact:true}).fill("Khoa gia hạn toàn đợt NV5");
    await milestone.getByRole("button",{name:"Lưu gia hạn",exact:true}).click();
    await expect(tbm.getByText(/NV5_LATE:.*Khoa gia hạn toàn đợt NV5/)).toBeVisible();
    await sv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await expect(report1.getByLabel("Nộp trễ",{exact:true})).toBeVisible();
    await milestone.getByText("Đóng mốc cho toàn đợt",{exact:true}).click();
    await review(tbm,milestone,"CLOSE","Khoa đóng mốc NV5");
    await gv.goto(`${web}${base}?section=progress`);
    expect(await gv.getByRole("button",{name:"Lưu gia hạn",exact:true}).count()).toBe(0);
    let reportCard=gv.locator("article.card").filter({has:gv.getByText("Báo cáo nộp trễ có minh chứng",{exact:true})});
    const evidence=await savedDownload(gv,reportCard.getByRole("button",{name:"Tải minh chứng của báo cáo",exact:true}),"progress-evidence.txt");
    expect(await fs.readFile(evidence,"utf8")).toBe("SYNTHETIC NV5 PROGRESS V1");
    await reportCard.getByRole("button",{name:"Mở tệp và phản hồi theo vị trí",exact:true}).click();
    await expect(gv.getByRole("dialog").locator(".review-text-sheet")).toContainText("SYNTHETIC NV5 PROGRESS V1");
    await review(gv,reportCard,"REVISION_REQUIRED","GVHD yêu cầu bổ sung sau đóng mốc");
    await sv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await sv.getByLabel("Mốc báo cáo",{exact:true}).selectOption({index:1});
    await sv.getByLabel("Kết quả, khó khăn và kế hoạch",{exact:true}).fill("Báo cáo bản 2 sau yêu cầu sửa");
    await sv.getByLabel(/Minh chứng tiến độ từ máy/).setInputFiles({name:"minh-chung-v2.txt",mimeType:"text/plain",buffer:Buffer.from("SYNTHETIC NV5 PROGRESS V2")});
    await sv.getByRole("button",{name:"Gửi báo cáo",exact:true}).click();
    await expect(sv.getByText("Báo cáo bản 2 sau yêu cầu sửa",{exact:true})).toBeVisible();

    await tbm.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await expect(tbm.getByText("Báo cáo bản 2 sau yêu cầu sửa",{exact:true})).toHaveCount(0);
    expect((await tbm.request.get(api+base+"/progress-reports")).status()).toBe(403);
    expect((await peer.request.get(api+base+"/progress-reports")).status()).toBe(404);
    expect((await admin.request.get(api+base+"/progress-reports")).status()).toBe(404);
    await expect(tbm.getByRole("button",{name:"Giao góp ý chéo",exact:true})).toHaveCount(0);
    await gv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    reportCard=gv.locator("article.card").filter({has:gv.getByText("Báo cáo bản 2 sau yêu cầu sửa",{exact:true})});
    await review(gv,reportCard,"CONFIRM","GVHD xác nhận báo cáo bản 2");

    // Real Mẫu 2, immutable versions, close, request revision, accept, download and print.
    await sv.goto(`${web}${base}?section=submissions&kind=PLAN`);
    const originalPlan=await fs.readFile(process.env.KLTN_E2E_PLAN_FILE!);
    const zip=await JSZip.loadAsync(originalPlan);
    const styles=await zip.file("word/styles.xml")!.async("string");
    zip.file("word/styles.xml",styles.replace("</w:styles>",'<w:style w:type="paragraph" w:styleId="KLTNReviewProof"><w:name w:val="KLTNReviewProof"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:b/><w:color w:val="C02030"/><w:sz w:val="40"/></w:rPr></w:style></w:styles>'));
    const xml=await zip.file("word/document.xml")!.async("string");
    const cut=xml.lastIndexOf("<w:sectPr"); expect(cut).toBeGreaterThan(0);
    zip.file("word/document.xml",xml.slice(0,cut)+'<w:p><w:pPr><w:pStyle w:val="KLTNReviewProof"/></w:pPr><w:r><w:t>KIỂM THỬ ĐỊNH DẠNG</w:t></w:r></w:p>'+xml.slice(cut));
    const source=await zip.generateAsync({type:"nodebuffer"});
    await savedDownload(sv,sv.getByRole("button",{name:"Tải mẫu áp dụng · Mẫu 2",exact:true}),"official-plan.docx");
    await expect(sv.getByRole("link",{name:/Mẫu 3 Đề cương/})).toHaveAttribute("href",`${base}?section=submissions&kind=PROPOSAL`);
    await expect(sv.getByLabel(/Tệp cần nộp/)).toHaveAttribute("accept",".pdf,.docx");
    await sv.getByLabel(/Tệp cần nộp/).setInputFiles({name:"wrong-plan.txt",mimeType:"text/plain",buffer:Buffer.from("Wrong layout")});
    await expect(sv.getByRole("button",{name:"Nộp kế hoạch Mẫu 2",exact:true})).toBeDisabled();
    await expect(sv.getByRole("alert")).toContainText("Tệp phải đúng định dạng");
    const upload=async(name:string)=>{
      const payload={name,mimeType:"application/vnd.openxmlformats-officedocument.wordprocessingml.document",buffer:source};
      if(await sv.getByLabel(/Tệp cần nộp/).count()){
        await sv.getByLabel(/Tệp cần nộp/).setInputFiles(payload);
        await sv.getByRole("button",{name:"Nộp kế hoạch Mẫu 2",exact:true}).click();
      }else{
        const update=sv.locator("details.submission-update");
        if((await update.getAttribute("open"))===null)await update.locator("summary").click();
        await sv.getByLabel(/Nộp phiên bản mới/).setInputFiles(payload);
        await sv.getByRole("button",{name:"Nộp tài liệu",exact:true}).click();
      }
      await expect(sv.getByText(new RegExp(`Phiên bản \\d+ · ${name}`))).toBeVisible();
    };
    await upload("ke-hoach-v1.docx");
    await gv.goto(`${web}${base}?section=submissions&kind=PLAN`);
    await gv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    const oldCard=gv.locator(".core-version").filter({has:gv.getByText("Phiên bản 1 · ke-hoach-v1.docx",{exact:true})});
    await oldCard.getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    let docModal = gv.getByRole("dialog");
    await expect(docModal.locator(".review-text-sheet [data-review-block]").first()).toBeVisible();
    await docModal.getByLabel("Kết quả",{exact:true}).selectOption("ACCEPT");
    await docModal.getByLabel("Nhận xét tổng quát",{exact:true}).fill("GV đang xem phiên bản 1");
    await upload("ke-hoach-v2.docx");
    const staleWarning = docModal.getByRole("alert").filter({hasText:"Bản nháp vẫn được giữ"});
    if(!await staleWarning.isVisible()) {
      // Autosave can discover the replacement before the reviewer clicks Send.
      try {await docModal.getByRole("button",{name:"Hoàn thành và gửi góp ý",exact:true}).click({timeout:3500});}
      catch (error) {if(!await staleWarning.isVisible())throw error;}
    }
    await expect(staleWarning).toBeVisible();
    await expect(docModal.getByLabel("Nhận xét tổng quát",{exact:true})).toHaveValue("GV đang xem phiên bản 1");
    await expect(docModal.getByRole("button",{name:"Hoàn thành và gửi góp ý",exact:true})).toBeDisabled();
    const unchanged=(await read(gv,base+"/documents")).find((d:any)=>d.title==="Kế hoạch thực hiện (Mẫu 2)");
    expect(unchanged.versions.map((v:any)=>v.state)).toEqual(["SUBMITTED","SUPERSEDED"]);
    expect(unchanged.versions[0].reviews).toHaveLength(0);
    await docModal.getByRole("button",{name:"Quay lại",exact:true}).click();
    await gv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await expect(oldCard).not.toBeVisible();
    await gv.getByText("Lịch sử cập nhật (1 bản trước)",{exact:true}).click();
    await gv.locator(".version-history-item > summary").first().click();
    await oldCard.getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    await expect(gv.getByRole("dialog").getByRole("button",{name:"Hoàn thành và gửi góp ý",exact:true})).toHaveCount(0);
    await gv.getByRole("dialog").getByRole("button",{name:"Quay lại",exact:true}).click();
    await tbm.goto(`${web}${base}?section=documents`);
    await tbm.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    const deadline=tbm.locator("section.card").filter({has:tbm.getByRole("heading",{name:"Lịch nhận tài liệu của đợt",exact:true})});
    await deadline.getByLabel("Loại tài liệu",{exact:true}).selectOption("PLAN");
    await deadline.getByLabel("Hạn mới (giờ Việt Nam)",{exact:true}).fill(local(new Date(Date.now()+70*86400000)));
    await deadline.getByLabel("Căn cứ / lý do",{exact:true}).fill("Khoa gia hạn Mẫu 2 cả đợt");
    await deadline.getByRole("button",{name:"Gia hạn cho cả đợt",exact:true}).click();
    await deadline.getByText("Lịch sử hạn nộp tài liệu của đợt",{exact:true}).click();
    await expect(deadline.getByText(/PLAN:.*Khoa gia hạn Mẫu 2 cả đợt/)).toBeVisible();
    await deadline.getByText("Đóng nhận Kế hoạch thực hiện (Mẫu 2) cho cả đợt",{exact:true}).click();
    await deadline.getByLabel("Lý do đóng",{exact:true}).fill("Khoa kết thúc nhận kế hoạch");
    await deadline.getByRole("button",{name:"Đóng nhận cho cả đợt",exact:true}).click();
    await gv.goto(`${web}${base}?section=submissions&kind=PLAN`);
    await gv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await gv.locator(".core-version").filter({has:gv.getByText("Phiên bản 2 · ke-hoach-v2.docx",{exact:true})}).getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    docModal = gv.getByRole("dialog");
    await expect(docModal.locator(".review-text-sheet [data-review-block]").first()).toBeVisible();
    const first=docModal.locator(".review-text-sheet [data-review-block]").first();
    await first.evaluate(element=>{
      const root=element.getRootNode() as ShadowRoot;
      const paragraphs=root.querySelectorAll("[data-review-block]");
      const range=document.createRange();range.setStartBefore(paragraphs[0].firstChild!);range.setEndAfter(paragraphs[1].lastChild!);
      const selection=(root as ShadowRoot & {getSelection?:()=>Selection|null}).getSelection?.() || window.getSelection();
      selection!.removeAllRanges();selection!.addRange(range);
      paragraphs[1].dispatchEvent(new PointerEvent("pointerup",{bubbles:true,composed:true}));
    });
    await docModal.getByLabel("Góp ý cần thực hiện",{exact:true}).fill("Góp ý liên đoạn để kiểm tra vị trí bắt đầu.");
    await expect(docModal.getByText("Đã lưu nháp",{exact:true})).toBeVisible();
    await expect(docModal.locator(".review-text-sheet [data-note-id]")).toHaveCount(1);
    await expect(first.locator("[data-note-id]")).toHaveCount(1);
    await docModal.getByRole("button",{name:"Bỏ ghim nháp",exact:true}).click();
    await expect(docModal.getByLabel("Góp ý cần thực hiện",{exact:true})).toHaveCount(0);
    const formatted=docModal.locator(".review-text-sheet [data-review-block]").filter({hasText:"KIỂM THỬ ĐỊNH DẠNG"});
    const formattedText=formatted.locator("span").last();
    await expect(formattedText).toHaveCSS("font-family",/Arial/);
    const format=await formattedText.evaluate(element=>{const style=getComputedStyle(element);return {size:style.fontSize,weight:style.fontWeight,color:style.color};});
    expect(parseFloat(format.size)).toBeCloseTo(26.6667,1);
    expect(Number(format.weight)).toBeGreaterThanOrEqual(700);
    expect(format.color).toBe("rgb(192, 32, 48)");
    // Select actual text with the mouse; no prior click on Đặt ghim.
    await formatted.scrollIntoViewIfNeeded();
    const rectangle=await formatted.boundingBox();expect(rectangle).toBeTruthy();
    await gv.mouse.move(rectangle!.x+2,rectangle!.y+rectangle!.height/2);
    await gv.mouse.down();
    await gv.mouse.move(rectangle!.x+Math.min(rectangle!.width-3,260),rectangle!.y+rectangle!.height/2,{steps:12});
    await gv.mouse.up();
    await expect(docModal.getByLabel("Góp ý cần thực hiện",{exact:true})).toBeFocused();
    await expect(docModal.getByLabel("Đoạn trích (không bắt buộc)",{exact:true})).not.toHaveValue("");
    await docModal.getByLabel("Góp ý cần thực hiện",{exact:true}).fill("Bổ sung nội dung kế hoạch tại đoạn này.");
    await expect(docModal.getByText("Đã lưu nháp",{exact:true})).toBeVisible();
    await docModal.getByRole("button",{name:"Quay lại",exact:true}).click();
    await gv.locator(".core-version").filter({has:gv.getByText("Phiên bản 2 · ke-hoach-v2.docx",{exact:true})}).getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    await expect(gv.getByRole("dialog").getByLabel("Góp ý cần thực hiện",{exact:true})).toHaveValue("Bổ sung nội dung kế hoạch tại đoạn này.");
    await expect(gv.getByRole("dialog").locator(".review-text-sheet [data-review-block]").filter({hasText:"KIỂM THỬ ĐỊNH DẠNG"})).toBeVisible();
    await expect.poll(()=>gv.getByRole("dialog").locator(".review-document-scroll").evaluate(element=>element.scrollTop)).toBeGreaterThan(80);
    await gv.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,"document-docx-review.png")});
    await review(gv,gv.locator(".core-version").filter({has:gv.getByText("Phiên bản 2 · ke-hoach-v2.docx",{exact:true})}),"REVISION_REQUIRED","Sửa kế hoạch sau khi đóng nhận");
    await sv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await sv.locator(".core-version").filter({has:sv.getByText("Phiên bản 2 · ke-hoach-v2.docx",{exact:true})}).getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    await expect(sv.getByRole("dialog").getByText("Bổ sung nội dung kế hoạch tại đoạn này.",{exact:true})).toBeVisible();
    await expect(sv.getByRole("dialog").locator(".review-text-sheet [data-note-id]")).toBeVisible();
    await expect(sv.getByRole("dialog").getByRole("button",{name:"Đặt ghim",exact:true})).toHaveCount(0);
    await sv.getByRole("dialog").getByRole("button",{name:"Quay lại",exact:true}).click();
    await sv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await expect(sv.getByRole("heading",{name:"Nộp bản sửa v3 theo yêu cầu cập nhật",exact:true})).toBeVisible();
    expect((await read(sv,base+"/documents")).filter((d:any)=>d.document_type==="PLAN")).toHaveLength(1);
    await upload("ke-hoach-v3.docx");
    await gv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await review(gv,gv.locator(".core-version").filter({has:gv.getByText("Phiên bản 3 · ke-hoach-v3.docx",{exact:true})}),"ACCEPT","GVHD tiếp nhận kế hoạch phiên bản 3");
    await gv.locator(".core-version").filter({has:gv.getByText("Phiên bản 3 · ke-hoach-v3.docx",{exact:true})}).getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    await expect(gv.getByRole("dialog").getByRole("note")).toContainText("Phiên bản này đã được GVHD tiếp nhận");
    await expect(gv.getByRole("dialog").getByText("Đã khôi phục bản nháp và vị trí xem",{exact:true})).toHaveCount(0);
    await expect(gv.getByRole("dialog").getByRole("button",{name:"Hoàn thành và gửi góp ý",exact:true})).toHaveCount(0);
    await gv.getByRole("dialog").getByRole("button",{name:"Quay lại",exact:true}).click();
    await sv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    const original=await savedDownload(sv,sv.getByRole("button",{name:"Tải bản nộp gốc v3",exact:true}),"plan-original-v3.docx");
    expect(await fs.readFile(original)).toEqual(source);
    await savedDownload(sv,sv.getByRole("button",{name:/Xuất bản đã duyệt để ký ngoài/}),"plan-print-v3.docx");
    const planVersion = sv.locator(".core-version").filter({has:sv.getByText("Phiên bản 3 · ke-hoach-v3.docx",{exact:true})});
    await planVersion.getByText("Lịch sử xuất bản in v3",{exact:true}).click();
    await expect(planVersion.getByText("Xuất từ phiên bản đã duyệt",{exact:true})).toBeVisible();
    await sv.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,"nv5-documents-student.png"),fullPage:true});

    // Real Mẫu 3 → GVHD confirmation → TBM finalization → traced print copy.
    await sv.goto(`${web}${base}?section=submissions&kind=PROPOSAL`);
    for (const version of [1, 2]) {
      await sv.getByLabel(/Nộp đề cương PDF hoặc DOCX/).setInputFiles(process.env.KLTN_E2E_PROPOSAL_FILE!);
      const submitted=sv.waitForResponse(response=>response.request().method()==="POST" &&
        new URL(response.url()).pathname.endsWith(base+"/proposal/versions"),{timeout:110000});
      await sv.getByRole("button",{name:"Nộp đề cương",exact:true}).click();
      expect((await submitted).status()).toBe(201);
      await expect(sv.getByText(`Phiên bản ${version} · synthetic-proposal.docx`,{exact:true})).toBeVisible();
    }
    await expect(sv.getByText("Phiên bản 1 · synthetic-proposal.docx",{exact:true})).not.toBeVisible();
    await sv.getByText("Lịch sử cập nhật (1 bản trước)",{exact:true}).click();
    await sv.locator(".version-history-item > summary").click();
    await sv.locator(".core-version").filter({has:sv.getByText("Phiên bản 1 · synthetic-proposal.docx",{exact:true})}).getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    await expect(sv.getByRole("dialog").locator(".review-text-sheet [data-review-block]").first()).toBeVisible();
    await expect(sv.getByRole("dialog").getByRole("button",{name:"Đặt ghim",exact:true})).toHaveCount(0);
    await sv.getByRole("dialog").getByRole("button",{name:"Quay lại",exact:true}).click();
    await gv.goto(`${web}${base}?section=submissions&kind=PROPOSAL`);
    await gv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await gv.locator(".core-version").filter({has:gv.getByText("Phiên bản 2 · synthetic-proposal.docx",{exact:true})}).getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    await expect(gv.getByRole("dialog").locator(".review-text-sheet [data-review-block]").first()).toBeVisible();
    await gv.getByRole("dialog").getByRole("button",{name:"Đặt ghim",exact:true}).click();
    await gv.getByRole("dialog").locator(".review-text-sheet [data-review-block]").first().click();
    await gv.getByRole("dialog").getByLabel("Góp ý cần thực hiện",{exact:true}).fill("Đề cương đã đủ nội dung ở đúng phiên bản 2.");
    await expect(gv.getByRole("dialog").getByText("Đã lưu nháp",{exact:true})).toBeVisible();
    await review(gv,gv.locator(".core-version").filter({has:gv.getByText("Phiên bản 2 · synthetic-proposal.docx",{exact:true})}),"CONFIRM","GVHD xác nhận Mẫu 3 phiên bản 2");
    await sv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await sv.locator(".core-version").filter({has:sv.getByText("Phiên bản 2 · synthetic-proposal.docx",{exact:true})}).getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    await expect(sv.getByRole("dialog").getByText("Đề cương đã đủ nội dung ở đúng phiên bản 2.",{exact:true})).toBeVisible();
    await expect(sv.getByRole("dialog").locator(".review-text-sheet [data-note-id]")).toBeVisible();
    await sv.getByRole("dialog").getByRole("button",{name:"Đoạn 1",exact:false}).first().click();
    await expect(sv.getByRole("dialog").locator(".review-block--selected")).toBeVisible();
    await sv.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,"proposal-docx-published-review.png")});
    await sv.getByRole("dialog").getByRole("button",{name:"Quay lại",exact:true}).click();
    await tbm.goto(`${web}${base}?section=submissions&kind=PROPOSAL`);
    await tbm.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await review(tbm,tbm.locator(".card").filter({has:tbm.getByRole("heading",{name:/Trưởng bộ môn/})}),"FINALIZE","TBM chốt bản đề cương hiện hành");
    await sv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await savedDownload(sv,sv.getByRole("button",{name:/Xuất bản để ký ngoài/}),"proposal-print-v2.docx");
    await sv.getByText("Lịch sử xuất bản in v2",{exact:true}).click();
    await expect(sv.getByText("Xuất từ phiên bản đã duyệt",{exact:true})).toBeVisible();
    expect((await read(sv,base+"/proposal")).state).toBe("DEPARTMENT_FINALIZED");
    await sv.goto(`${web}${base}?section=submissions&kind=PLAN`);
    await tbm.goto(`${web}${base}?section=submissions&kind=SUPPORTING`);
    const supportingDeadline=tbm.locator("section.card").filter({has:tbm.getByRole("heading",{name:"Lịch nhận tài liệu của đợt",exact:true})});
    await supportingDeadline.getByLabel("Hạn mới (giờ Việt Nam)",{exact:true}).fill(local(new Date(Date.now()+80*86400000)));
    await supportingDeadline.getByLabel("Căn cứ / lý do",{exact:true}).fill("Khoa mở nhận tài liệu hỗ trợ theo đợt");
    await supportingDeadline.getByRole("button",{name:/Thiết lập cho cả đợt|Gia hạn cho cả đợt/}).click();
    await sv.goto(`${web}${base}?section=submissions&kind=SUPPORTING`);
    await expect(sv.getByRole("heading",{name:/Minh chứng công bố khoa học/})).toBeVisible();
    await expect(sv.getByRole("button",{name:"Nộp tài liệu",exact:true})).toHaveCount(0);
    await expect(sv.getByText("Nộp hồ sơ xét điểm thưởng",{exact:true})).toBeVisible();
    expect((await outsider.request.get(api+base+"/document-deadline-history")).status()).toBe(404);
    // The faculty can reopen a closed intake with a later round-wide deadline.
    await tbm.getByRole("tab",{name:"Báo cáo tiến độ",exact:true}).click();
    await tbm.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    await milestone.getByText("Gia hạn và mở lại toàn đợt",{exact:true}).click();
    await milestone.getByLabel("Hạn mới (giờ Việt Nam)",{exact:true}).fill(local(new Date(Date.now()+3*86400000)));
    await milestone.getByLabel("Lý do gia hạn",{exact:true}).fill("Khoa mở lại mốc cho toàn đợt");
    await milestone.getByRole("button",{name:"Gia hạn và mở lại mốc",exact:true}).click();
    await expect(tbm.getByText(/NV5_LATE:.*Khoa mở lại mốc cho toàn đợt/)).toBeVisible();
    await tbm.goto(`${web}${base}?section=documents`);
    await deadline.getByLabel("Loại tài liệu",{exact:true}).selectOption("PLAN");
    await deadline.getByLabel("Hạn mới (giờ Việt Nam)",{exact:true}).fill(local(new Date(Date.now()+90*86400000)));
    await deadline.getByLabel("Căn cứ / lý do",{exact:true}).fill("Khoa mở lại hạn kế hoạch cả đợt");
    await deadline.getByRole("button",{name:"Gia hạn và mở nhận lại cả đợt",exact:true}).click();
    await deadline.getByText("Lịch sử hạn nộp tài liệu của đợt",{exact:true}).click();
    await expect(deadline.getByText(/PLAN:.*Khoa mở lại hạn kế hoạch cả đợt/)).toBeVisible();
    await sv.getByRole("tab",{name:"Báo cáo tiến độ",exact:true}).click();
    await sv.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
    const historyCard = sv.locator("article.card").filter({has:sv.getByText("Báo cáo nộp trễ có minh chứng",{exact:true})});
    await historyCard.getByText("Lịch sử cập nhật (1 bản trước)",{exact:true}).click();
    await expect(historyCard.getByLabel("Nộp trễ",{exact:true}).first()).toBeVisible();
  } finally {for(const actor of contexts)await actor.context.close();}
});
