import {test, expect, type Page} from "@playwright/test";
import path from "node:path";

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

test("PDF ghim nhận xét: quét thật, tự lưu, mở lại đúng trang, riêng tư, gửi SV và giữ đúng bản", async ({browser}) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  const actors = await Promise.all(["gv2", "tbm", "annotationStudent", "admin", "nv5Outsider"].map(async key => {
    const context = await browser.newContext(); const page = await context.newPage();
    page.setDefaultTimeout(20000);
    page.on("pageerror", error => errors.push(error.message));
    await page.goto(web); await page.getByLabel("Email", {exact: true}).fill(accounts[key].email);
    await page.getByLabel("Mật khẩu", {exact: true}).fill(accounts[key].password);
    await page.getByRole("button", {name: "Đăng nhập", exact: true}).click();
    await expect(page.getByRole("heading", {name: "Tổng quan", exact: true})).toBeVisible();
    return {context, page};
  }));
  const [gv, tbm, sv, admin, outsider] = actors.map(actor => actor.page);
  try {
    const round = (await read(gv, "/rounds/open"))[0];
    let response = await post(gv, "/topics", {round_id: round.id, title: "DEMO nhận xét định vị PDF", max_students: 1});
    expect(response.status()).toBe(201); let topic = await response.json();
    topic = await (await post(gv, `/topics/${topic.id}/submit`, undefined, topic.row_version)).json();
    expect((await post(tbm, `/topics/${topic.id}/department-decision`, {decision: "APPROVE"}, topic.row_version)).status()).toBe(200);
    let reg = await (await post(sv, "/topic-registrations", {topic_id: topic.id})).json();
    reg = await (await post(sv, `/topic-registrations/${reg.id}/submit`)).json();
    reg = await (await post(gv, `/topic-registrations/${reg.id}/lecturer-decision`, {decision: "ACCEPT"}, reg.row_version)).json();
    expect(reg.state).toBe("FINALIZED");
    const base = `/theses/${reg.thesis_id}`;
    expect((await post(admin, "/admin/round-assignments", {round_id: round.id, user_id: (await read(tbm, "/me/context")).user_id,
      assignment_type: "KLTN_COORDINATOR", basis_ref: "Synthetic annotation UI test"})).status()).toBe(201);
    response = await post(tbm, base + "/milestones", {code: "PDF_REVIEW", title: "Mốc PDF nhận xét", due_at: new Date(Date.now() + 86400000).toISOString()});
    expect(response.status()).toBe(201); const milestone = await response.json();
    const pdf = syntheticPdf();
    async function submit(summary: string, file: string) {
      await sv.goto(`${web}${base}?section=progress`);
      await sv.getByLabel("Mốc báo cáo", {exact: true}).selectOption(milestone.id);
      await sv.getByLabel("Kết quả, khó khăn và kế hoạch", {exact: true}).fill(summary);
      await sv.getByLabel("Tiến độ tự báo cáo (%)", {exact: true}).fill("60");
      await sv.getByLabel(/Minh chứng tiến độ từ máy/).setInputFiles({name: file, mimeType: "application/pdf", buffer: pdf});
      await sv.getByRole("button", {name: "Gửi báo cáo", exact: true}).click();
      await expect(sv.getByText(summary, {exact: true})).toBeVisible();
      await expect(sv.getByRole("button", {name: "Xem tệp & nhận xét", exact: true})).toBeVisible({timeout: 120000});
    }
    await submit("Báo cáo PDF để GV ghim góp ý", "bao-cao-v1.pdf");
    const report = (await read(sv, base + "/progress-reports"))[0];
    expect(report.evidence_scan_state).toBe("CLEAN");
    const annotationPath = base + `/progress-reports/${report.id}/annotations`;
    await gv.goto(`${web}${base}?section=progress`);
    await gv.getByRole("button", {name: "Mở tệp và phản hồi theo vị trí", exact: true}).click();
    let modal = gv.getByRole("dialog");
    await expect(modal.getByLabel("Trang PDF")).toBeVisible();
    await expect(modal.getByText("/ 2", {exact: false})).toBeVisible();
    await modal.getByRole("button", {name: "Trang sau", exact: true}).click();
    await expect(modal.getByLabel("Trang PDF")).toHaveValue("2");
    await expect(modal.locator(".textLayer")).toContainText("MEASUREMENTS");
    const text = modal.locator(".textLayer span").filter({hasText:"MEASUREMENTS"});
    await text.scrollIntoViewIfNeeded();
    const box = await text.boundingBox(); expect(box).toBeTruthy();
    await gv.mouse.move(box!.x+2, box!.y+box!.height/2);
    await gv.mouse.down();
    await gv.mouse.move(box!.x+Math.min(box!.width-2,220), box!.y+box!.height/2,{steps:12});
    await gv.mouse.up();
    await expect(modal.getByLabel("Đoạn trích (không bắt buộc)",{exact:true})).not.toHaveValue("");
    await expect(modal.getByLabel("Góp ý cần thực hiện",{exact:true})).toBeFocused();
    const noteComment = modal.getByLabel("Góp ý cần thực hiện", {exact: true});
    await noteComment.fill("Bổ sung đơn vị đo và giải thích kết quả ở vị trí này.");
    await expect(modal.getByText("Đã lưu nháp", {exact: true})).toBeVisible();
    await modal.getByLabel("Nhận xét tổng quát", {exact: true}).fill("Sửa phần kết quả theo ghim trên trang 2.");
    await modal.getByRole("button", {name: "Phóng to PDF", exact: true}).click();
    await expect(modal.getByText("125%", {exact: true})).toBeVisible();
    await modal.locator(".review-document-scroll").evaluate(element => {element.scrollTop = 140;});
    await gv.screenshot({path: path.join(process.env.KLTN_E2E_RUN_DIR!, "progress-review-lecturer.png")});
    expect((await read(sv, annotationPath)).annotations).toEqual([]);
    expect((await outsider.request.get(api + annotationPath)).status()).toBe(404);
    await modal.getByRole("button", {name: "Quay lại", exact: true}).click();
    await expect(modal).toHaveCount(0);
    await gv.reload();
    await gv.getByRole("button", {name: "Mở tệp và phản hồi theo vị trí", exact: true}).click();
    modal = gv.getByRole("dialog");
    await expect(modal.getByLabel("Trang PDF")).toHaveValue("2");
    await expect(modal.getByText("125%", {exact: true})).toBeVisible();
    await expect(modal.getByLabel("Góp ý cần thực hiện", {exact: true})).toHaveValue("Bổ sung đơn vị đo và giải thích kết quả ở vị trí này.");
    await expect(modal.getByLabel("Nhận xét tổng quát", {exact: true})).toHaveValue("Sửa phần kết quả theo ghim trên trang 2.");
    await expect.poll(() => modal.locator(".review-document-scroll").evaluate(element => element.scrollTop)).toBeGreaterThan(40);
    await modal.getByLabel("Kết quả",{exact:true}).selectOption("REVISION_REQUIRED");
    await modal.getByRole("button", {name: "Hoàn thành và gửi góp ý", exact: true}).click();
    await expect(modal).toHaveCount(0);
    const published = await read(sv, annotationPath);
    expect(published.annotations.filter((note:any)=>note.annotation_kind === "PIN")).toHaveLength(1); expect(published.annotations.every((note:any)=>note.state === "PUBLISHED")).toBe(true);
    await sv.reload();
    await sv.getByRole("button", {name: "Xem tệp & nhận xét", exact: true}).click();
    const studentModal = sv.getByRole("dialog");
    await expect(studentModal.getByText("Bổ sung đơn vị đo và giải thích kết quả ở vị trí này.", {exact: true})).toBeVisible();
    await studentModal.getByRole("button", {name: "Trang 2", exact: false}).click();
    await expect(studentModal.getByLabel("Trang PDF")).toHaveValue("2");
    await expect(studentModal.locator(".review-pin")).toHaveCount(1);
    await expect(studentModal.getByRole("button", {name: "Đặt ghim", exact: true})).toHaveCount(0);
    await sv.setViewportSize({width: 390, height: 844});
    await expect(studentModal.locator(".review-pdf-loading")).toHaveCount(0);
    expect((await studentModal.locator(".review-header").boundingBox())!.height).toBeLessThan(180);
    await sv.screenshot({path: path.join(process.env.KLTN_E2E_RUN_DIR!, "progress-review-student-mobile.png")});
    await studentModal.getByRole("button", {name: "Quay lại", exact: true}).click();
    await sv.setViewportSize({width: 1440, height: 1000});
    await submit("Báo cáo PDF đã sửa theo góp ý", "bao-cao-v2.pdf");
    const reports = await read(sv, base + "/progress-reports");
    const newest = reports.find((item: any) => item.version_no === 2);
    expect((await read(sv, base + `/progress-reports/${newest.id}/annotations`)).annotations).toEqual([]);
    expect((await read(sv, annotationPath)).annotations[0].comment).toContain("Bổ sung đơn vị đo");
    const original = await sv.request.get(api + base + `/progress-reports/${report.id}/evidence`);
    expect(await original.body()).toEqual(pdf);
    expect(errors).toEqual([]);
  } finally {for (const actor of actors) await actor.context.close();}
});
