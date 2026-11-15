import { test, expect, type Browser, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const accounts: Record<string,{email:string;password:string}> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = `http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;
const api = `http://127.0.0.1:${process.env.KLTN_E2E_API_PORT || "8001"}/api/v1`;
async function login(browser: Browser, key: string) {
  const context = await browser.newContext({viewport:{width:1440,height:1000}});
  const page = await context.newPage();
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(web + "/");
  await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
  return {page,context,errors};
}
async function close(actors: Awaited<ReturnType<typeof login>>[]) {
  for (const actor of actors) {
    await actor.context.close().catch(() => undefined);
  }
}
async function headerGeometry(page: Page) {
  return page.locator(".header").evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
  });
}
const VALID_PDF = Buffer.from(
  "%PDF-1.3\n%âãÏÓ\n1 0 obj\n<<\n/Producer (pypdf)\n>>\nendobj\n" +
  "2 0 obj\n<<\n/Type /Pages\n/Count 1\n/Kids [ 4 0 R ]\n>>\nendobj\n" +
  "3 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n" +
  "4 0 obj\n<<\n/Type /Page\n/Resources <<\n>>\n/MediaBox [ 0.0 0.0 612 792 ]\n/Parent 2 0 R\n>>\nendobj\n" +
  "xref\n0 5\n0000000000 65535 f \n0000000015 00000 n \n0000000054 00000 n \n0000000113 00000 n \n0000000162 00000 n \n" +
  "trailer\n<<\n/Size 5\n/Root 3 0 R\n/Info 1 0 R\n>>\nstartxref\n256\n%%EOF\n"
);

async function read(page: Page, path: string) {const r = await page.request.get(api + path); expect(r.status()).toBe(200); return r.json();}
async function write(page: Page, path: string, options: {data?: unknown; headers?: Record<string,string>} = {}) {
  const session = await read(page, "/me/context");
  return page.request.post(api + path, {
    ...options,
    headers: {"X-CSRF-Token": session.csrf_token, ...options.headers},
  });
}
function card(page: Page, title: string) {return page.locator("article").filter({has:page.getByRole("heading",{name:title,exact:true})});}
async function find(page: Page, title: string) {
  await page.goto(web + "/topics");
  await page.getByRole("button",{name:"Đề tài có sẵn",exact:true}).click();
  await page.getByLabel("Tìm đề tài").fill(title);
  await expect(card(page,title)).toHaveCount(1);
  return card(page,title);
}
async function join(page: Page, title: string, second = false, withEvidence = false) {
  await (await find(page,title)).getByRole("button",{name:second ? "Tham gia" : "Đăng ký",exact:true}).click();
  const dialog = page.getByRole("dialog");
  if (withEvidence) await dialog.getByLabel("Tệp minh chứng").setInputFiles({name:"minh-chung-khi-dang-ky.pdf",mimeType:"application/pdf",
    buffer:VALID_PDF});
  await dialog.getByRole("checkbox").check();
  await dialog.getByRole("button",{name:second ? "Tham gia đề tài" : "Lập đăng ký của tôi",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Đăng ký đề tài",exact:true})).toBeVisible();
  return card(page,title);
}
async function proof(page: Page, title: string) {
  await card(page,title).locator('input[type="file"]').setInputFiles({name:"minh-chung-gia-lap.pdf",mimeType:"application/pdf",
    buffer:VALID_PDF});
  await expect(card(page,title).getByRole("link",{name:/Tải minh chứng/}).last()).toBeVisible();
}
async function review(page: Page, title: string, receiver?: string) {
  await page.goto(web + "/topics");
  await page.getByLabel("Tìm đề tài").fill(title);
  await card(page,title).getByRole("button",{name:"Xem và duyệt"}).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Tên đề tài sau khi duyệt").fill(title + " đã duyệt");
  if (receiver) await dialog.getByLabel("GV tiếp nhận (xác nhận hoặc chọn lại)").selectOption(receiver);
  await dialog.getByRole("button",{name:"Duyệt đề tài",exact:true}).click();
  await expect(dialog.getByText("Đã duyệt",{exact:true})).toBeVisible();
  await dialog.getByRole("button",{name:"Đóng",exact:true}).click();
}

test("Header giữ nguyên vị trí khi đổi giữa các trang có chiều cao khác nhau", async ({browser}) => {
  const actor = await login(browser, "gv");
  try {
    const baseline = await headerGeometry(actor.page);
    for (const path of ["/topics?view=mine", "/theses", "/"]) {
      await actor.page.goto(web + path);
      await expect(actor.page.locator(".header")).toBeVisible();
      const current = await headerGeometry(actor.page);
      expect(current.x).toBeCloseTo(baseline.x, 3);
      expect(current.y).toBeCloseTo(baseline.y, 3);
      expect(current.width).toBeCloseTo(baseline.width, 3);
      expect(current.height).toBeCloseTo(baseline.height, 3);
    }
  } finally {await close([actor]);}
});

test("GV giả lập 2 đăng nhập bằng tài khoản riêng", async ({browser}) => {
  const actor = await login(browser, "gv2");
  try {
    const me = await read(actor.page, "/me/context");
    expect(me.base_role).toBe("LECTURER");
    expect(me.lecturer_code).toBe("SYN-DEMO-GV-2");
  } finally {await close([actor]);}
});

test("GV tạo → TBM duyệt/sửa tên → nhóm đăng ký → GV nhận chính thức → tiến độ và tài liệu", async ({browser}) => {
  test.setTimeout(240_000);
  const actors = await Promise.all(["gv","tbm","sv1","sv2","sv3","admin"].map(key => login(browser,key)));
  const [gv,tbm,sv1,sv2,sv3,admin] = actors;
  for(const actor of actors)actor.page.setDefaultTimeout(12000);
  try {
    const title = "E2E Quản lý đề tài và đăng ký";
    await gv.page.goto(web + "/topics");
    await gv.page.getByRole("button",{name:"Tạo đề tài",exact:true}).click();
    let dialog = gv.page.getByRole("dialog");
    await dialog.getByLabel("Tên đề tài",{exact:true}).fill(title);
    await dialog.getByLabel("Mô tả, mục tiêu và phạm vi").fill("Dữ liệu giả kiểm thử luồng nghiệp vụ.");
    await dialog.getByLabel("Số sinh viên tối đa").selectOption("2");
    await dialog.getByRole("button",{name:"+ Thêm yêu cầu"}).click();
    await dialog.getByLabel("Nội dung",{exact:true}).fill("Python và PostgreSQL");
    await dialog.getByRole("button",{name:"Tạo bản nháp",exact:true}).click();
    dialog = gv.page.getByRole("dialog");
    await dialog.getByRole("button",{name:"Gửi bộ môn duyệt"}).click();
    await expect(dialog.getByText("Đã gửi",{exact:true})).toBeVisible();
    await review(tbm.page,title);
    const approved = title + " đã duyệt";
    const listing = await find(sv1.page,approved);
    await expect(listing.getByText("Năm học",{exact:true})).toBeVisible();
    await expect(listing.getByText("Giảng viên đề xuất",{exact:true})).toBeVisible();
    await expect(listing.locator(".requirement-preview")).toContainText("Python và PostgreSQL");
    await listing.getByRole("button",{name:"Xem chi tiết"}).click();
    await expect(sv1.page.getByRole("dialog").getByText("Dữ liệu giả kiểm thử luồng nghiệp vụ.")).toBeVisible();
    await expect(sv1.page.getByRole("dialog").getByText("Python và PostgreSQL")).toBeVisible();
    await sv1.page.getByRole("dialog").getByRole("button",{name:"Đóng"}).click();
    await join(sv1.page,approved,false,true);
    await expect(card(sv1.page,approved).getByText("1/2 SV",{exact:true})).toBeVisible();
    await expect(card(sv1.page,approved).getByRole("link",{name:/Tải minh chứng: minh-chung-khi-dang-ky.pdf/})).toBeVisible();
    await card(sv1.page,approved).getByRole("button",{name:"Gửi đăng ký cho GV"}).click();
    await expect(card(sv1.page,approved).getByText("Đã gửi",{exact:true}).first()).toBeVisible();
    await sv1.page.goto(web + "/registrations");
    await expect(card(sv1.page,approved).getByRole("button",{name:"Rút đăng ký",exact:true})).toBeVisible();
    await gv.page.goto(web);
    await expect(gv.page.getByRole("heading",{name:/Hồ sơ cần xử lý [1-9]\d*/})).toBeVisible();
    const bell = gv.page.getByRole("button",{name:/Thông báo, [1-9]\d* chưa xem/});
    await expect(bell).toBeVisible();
    await bell.click();
    const notice = gv.page.getByRole("dialog",{name:"Thông báo"});
    await expect(notice.getByText(new RegExp("Sinh viên giả lập 1 đã đăng ký đề tài: " + approved))).toBeVisible();
    const registrationNotice=notice.locator(".notifications__item").filter({hasText:"Sinh viên giả lập 1 đã đăng ký đề tài: " + approved});
    await expect(registrationNotice.locator("time")).toHaveAttribute("datetime",/^\d{4}-\d{2}-\d{2}T/);
    await registrationNotice.click();
    await expect(gv.page).toHaveURL(/\/registrations\?focus=/);
    await expect(card(gv.page,approved).getByRole("link",{name:/Tải minh chứng: minh-chung-khi-dang-ky.pdf/})).toBeVisible();
    await join(sv2.page,approved,true);
    await expect(card(sv2.page,approved).getByText("2/2 SV",{exact:true})).toBeVisible();
    await proof(sv2.page,approved);
    await gv.page.getByRole("button",{name:"Làm mới",exact:true}).click();
    await card(gv.page,approved).getByRole("button",{name:"Chấp nhận chính thức và tạo khóa luận",exact:true}).click();
    await expect(card(gv.page,approved).getByText("Đã tiếp nhận chính thức",{exact:false}).first()).toBeVisible();
    await sv1.page.reload();
    await expect(card(sv1.page,approved).getByRole("button",{name:"Rút đăng ký",exact:true})).toHaveCount(0);
    await sv2.page.reload();
    await expect(card(sv2.page,approved).getByRole("button",{name:"Rút đăng ký",exact:true})).toHaveCount(0);
    const topic = (await read(gv.page,"/topics?view=mine&search=" + encodeURIComponent(approved)))[0];
    await sv3.page.goto(web + "/topics");
    await sv3.page.getByRole("button",{name:"Đề tài có sẵn",exact:true}).click();
    await sv3.page.getByLabel("Tìm đề tài").fill(approved);
    await expect(card(sv3.page,approved).getByRole("button",{name:/^(Đăng ký|Tham gia)$/})).toHaveCount(0);
    expect((await write(sv3.page,"/topic-registrations",{data:{topic_id:topic.id}})).status()).toBe(409);
    const registrations = (await read(gv.page,"/topic-registrations")).filter((r:{topic_id:string}) => r.topic_id === topic.id);
    expect(registrations).toHaveLength(1); expect(registrations[0].members).toHaveLength(2);
    expect(registrations[0].state).toBe("FINALIZED");
    expect(registrations[0].thesis_id).toBeTruthy();
    const thesisId = registrations[0].thesis_id as string;
    await sv1.page.reload();
    await card(sv1.page,approved).getByRole("link",{name:/Mở hồ sơ khóa luận/}).click();
    await sv1.page.getByRole("tab",{name:"Báo cáo tiến độ",exact:true}).click({timeout:10000});
    await expect(sv1.page.getByRole("heading",{name:"Chưa có mốc tiến độ trong hồ sơ này",exact:true})).toBeVisible();
    const rounds = await read(admin.page,"/admin/rounds");
    const round = rounds.find((item:{state:string}) => item.state === "OPEN");
    expect(round).toBeTruthy();
    const lecturer = (await read(admin.page,"/admin/users?search="+encodeURIComponent(accounts.gv.email)))[0];
    await admin.page.goto(web+"/administration/assignments");
    const assignment = admin.page.locator("section.card").filter({has:admin.page.getByRole("heading",{name:"Phân công theo đợt",exact:true})});
    await assignment.locator("select").first().selectOption(round.id);
    await assignment.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("KLTN_COORDINATOR");
    await assignment.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption(lecturer.id);
    await assignment.getByLabel("Căn cứ phân công").fill("E2E SYNTHETIC ROUND COORDINATION");
    await assignment.getByRole("button",{name:"Lưu phân công",exact:true}).click();
    await expect(admin.page.getByRole("status").filter({hasText:"Đã lưu phân công"})).toBeVisible();

    await gv.page.goto(`${web}/theses/${thesisId}?section=progress`);
    await gv.page.getByRole("combobox",{name:/Phạm vi mốc/}).selectOption("ROUND");
    await expect(gv.page.getByRole("heading",{name:"Mở mốc theo kế hoạch đợt",exact:true})).toBeVisible();
    const future = new Date(Date.now()+5*24*60*60*1000);
    const dueAt = `${future.getFullYear()}-${String(future.getMonth()+1).padStart(2,"0")}-${String(future.getDate()).padStart(2,"0")}T17:00`;
    await gv.page.getByLabel("Mã mốc").fill("E2E_CHECKPOINT");
    await gv.page.getByLabel("Tên mốc").fill("Mốc kiểm tra giao diện");
    await gv.page.getByLabel("Hạn nộp (giờ Việt Nam)").fill(dueAt);
    await gv.page.getByLabel("Tiến độ dự kiến (%)").fill("30");
    await gv.page.getByRole("button",{name:"Mở mốc cho đợt",exact:true}).click();
    await expect(gv.page.getByRole("heading",{name:"Mốc kiểm tra giao diện · v1",exact:true})).toBeVisible();
    await sv1.page.reload();
    await sv1.page.getByLabel("Mốc báo cáo").selectOption({label:"Mốc kiểm tra giao diện · v1"});
    await sv1.page.getByLabel("Kết quả, khó khăn và kế hoạch").fill("Đã hoàn thành thiết kế; tiếp tục tích hợp và kiểm thử.");
    await sv1.page.getByLabel("Tiến độ tự báo cáo (%)").fill("30");
    await sv1.page.getByRole("button",{name:"Gửi báo cáo",exact:true}).click();
    console.log("E2E progress v1 submitted");
    await expect(sv1.page.getByText("Đã hoàn thành thiết kế; tiếp tục tích hợp và kiểm thử.",{exact:true})).toBeVisible();
    await sv2.page.goto(`${web}/theses/${thesisId}?section=progress`);
    await sv2.page.getByLabel("Mốc báo cáo").selectOption({label:"Mốc kiểm tra giao diện · v1 · nộp phiên bản mới"});
    await sv2.page.getByLabel("Kết quả, khó khăn và kế hoạch").fill("Thành viên cập nhật tiến độ trước khi GVHD phản hồi.");
    await sv2.page.getByLabel("Tiến độ tự báo cáo (%)").fill("45");
    await sv2.page.getByRole("button",{name:"Gửi báo cáo",exact:true}).click();
    await expect(sv2.page.getByRole("status")).toContainText("Đã gửi báo cáo tiến độ");
    const progress = await read(sv2.page,`/theses/${thesisId}/progress-reports`);
    expect(progress.find(row => row.version_no === 2)?.submitted_by_student_id).toBe((await read(sv2.page,"/me/context")).student_id);
    await sv1.page.reload();
    await expect(sv1.page.getByText("Thành viên cập nhật tiến độ trước khi GVHD phản hồi.",{exact:true})).toBeVisible();
    await sv1.page.locator(".progress-report-history > summary").click();
    await sv1.page.locator(".progress-report-history__version > summary").click();
    await expect(sv1.page.getByText("Đã hoàn thành thiết kế; tiếp tục tích hợp và kiểm thử.",{exact:true})).toBeVisible();
    await gv.page.reload();
    const reportCard = gv.page.locator("article.card").filter({has:gv.page.getByText("Thành viên cập nhật tiến độ trước khi GVHD phản hồi.",{exact:true})});
    await reportCard.getByLabel("Kết quả").selectOption("CONFIRM");
    await reportCard.getByLabel("Nhận xét / lý do").fill("Báo cáo tiến độ đã được xác nhận.");
    await reportCard.getByRole("button",{name:"Gửi kết quả",exact:true}).click();
    await expect(gv.page.getByRole("status")).toContainText("Đã lưu nhận xét tiến độ");

    const planUrl=`${web}/theses/${thesisId}?section=submissions&kind=PLAN`;
    await gv.page.goto(planUrl);
    const deadlineCard = gv.page.locator("section.card").filter({has:gv.page.getByRole("heading",{name:"Lịch nhận tài liệu của đợt",exact:true})});
    const later = new Date(Date.now()+70*24*60*60*1000);
    const laterDueAt = `${later.getFullYear()}-${String(later.getMonth()+1).padStart(2,"0")}-${String(later.getDate()).padStart(2,"0")}T17:00`;
    await deadlineCard.getByLabel("Hạn mới (giờ Việt Nam)").fill(laterDueAt);
    await deadlineCard.getByLabel("Căn cứ / lý do").fill("Kế hoạch nộp tài liệu đợt kiểm thử");
    await deadlineCard.getByRole("button",{name:/Thiết lập cho cả đợt|Gia hạn cho cả đợt/}).click({timeout:10000});

    await expect(gv.page.getByRole("status")).toContainText(/Đã (thiết lập hạn|gia hạn loại) tài liệu/);
    await sv1.page.goto(planUrl);
    const fileInput = sv1.page.getByLabel(/Tệp cần nộp/);
    await fileInput.setInputFiles({name:"bao-cao-v1.pdf",mimeType:"application/pdf",
      buffer:VALID_PDF});
    await sv1.page.getByRole("button",{name:"Nộp kế hoạch Mẫu 2",exact:true}).click();
    await expect(sv1.page.getByText("Phiên bản 1 · bao-cao-v1.pdf",{exact:true})).toBeVisible();
    const update=sv1.page.locator("details.submission-update");
    if((await update.getAttribute("open"))===null)await update.locator("summary").click();
    await sv1.page.getByLabel(/Nộp phiên bản mới/).setInputFiles({name:"bao-cao-v2.pdf",mimeType:"application/pdf",
      buffer:VALID_PDF});
    await update.getByRole("button",{name:"Nộp tài liệu",exact:true}).click();
    await expect(sv1.page.getByText("Phiên bản 2 · bao-cao-v2.pdf",{exact:true})).toBeVisible();
    await sv1.page.getByText("Lịch sử cập nhật (1 bản trước)",{exact:true}).click();
    await sv1.page.locator(".version-history-item > summary").first().click();
    await expect(sv1.page.getByText("Phiên bản 1 · bao-cao-v1.pdf",{exact:true})).toBeVisible();
    const uploaded = (await read(sv1.page,`/theses/${thesisId}/documents`)).find((item:{document_type:string})=>item.document_type === "PLAN");
    expect(uploaded.versions).toHaveLength(2);
    expect(uploaded.versions[0].state).toBe("SUBMITTED");
    expect(uploaded.versions[1].state).toBe("SUPERSEDED");
    expect(uploaded.versions[0].scan_state).toBe("CLEAN");
    await expect(sv1.page.getByRole("button",{name:"Tải bản nộp gốc v2",exact:true})).toBeEnabled();
    await gv.page.goto(planUrl);
    await gv.page.locator(".core-version").filter({hasText:"Phiên bản 2 · bao-cao-v2.pdf"}).getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click({timeout:10000});
    const documentReview=gv.page.getByRole("dialog");
    await documentReview.getByLabel("Kết quả",{exact:true}).selectOption("ACCEPT");
    await documentReview.getByLabel("Nhận xét tổng quát",{exact:true}).fill("Bản sửa đã đạt; tiếp nhận phiên bản 2.");
    await documentReview.getByRole("button",{name:"Hoàn thành và gửi góp ý",exact:true}).click();
    await expect(documentReview).toHaveCount(0);
    expect(topic.title_versions.map((v:{title:string}) => v.title)).toEqual([title,approved]);
    await sv1.page.reload();
    await expect(sv1.page.getByText("Phiên bản 2 · bao-cao-v2.pdf",{exact:true})).toBeVisible();
    expect((await write(sv1.page,"/topics",{data:{round_id:topic.round_id,title:"SV không được tạo đề tài GV"}})).status()).toBe(403);
    await gv.page.goto(web+"/registrations");
    await expect(card(gv.page,approved).getByRole("link",{name:/Mở hồ sơ khóa luận/})).toBeVisible();
  } finally {await close(actors);}
});

test("SV đề xuất → trả lại/sửa/duyệt → GV từ chối → TBM chọn GV khác → tiếp nhận chính thức", async ({browser}) => {
  const actors = await Promise.all(["sv3","proposalPeer","tbm","gv","gv2"].map(key => login(browser,key)));
  const [sv,peer,tbm,gv,gv2] = actors;
  try {
    const receiver = (await read(sv.page,"/lecturers")).find((l:{lecturer_code:string}) => l.lecturer_code === "SYN-DEMO-GV-1");
    const title = "E2E Đề tài do sinh viên đề xuất";
    await sv.page.goto(web + "/topics");
    await sv.page.getByRole("button",{name:"Tự đề xuất đề tài",exact:true}).click();
    let dialog = sv.page.getByRole("dialog");
    await dialog.getByLabel("Tên đề tài",{exact:true}).fill(title);
    await dialog.getByLabel("Số sinh viên tối đa").selectOption("2");
    await dialog.getByLabel("GV mong muốn tiếp nhận").selectOption(receiver.id);
    await dialog.getByRole("checkbox").check();
    await dialog.getByRole("button",{name:"Lập đăng ký của tôi"}).click();
    await expect(sv.page.getByRole("heading",{name:"Đăng ký đề tài",exact:true})).toBeVisible();
    await sv.page.getByRole("button",{name:"Gửi đề xuất cho bộ môn"}).click();
    await expect(sv.page.getByText("Chờ bộ môn duyệt đề tài")).toBeVisible();
    const proposedNotices = await read(gv.page,"/notifications");
    expect(proposedNotices.items.some((item:{message:string}) => item.message.includes(title) && item.message.includes("chờ bộ môn duyệt"))).toBe(true);
    await gv.page.goto(web + "/topics");
    await gv.page.getByRole("button",{name:"SV đề xuất cho tôi"}).click();
    await expect(card(gv.page,title)).toContainText("GV được SV đề xuất");
    await card(gv.page,title).getByRole("button",{name:"Xem chi tiết"}).click();
    await expect(gv.page.getByRole("dialog")).toContainText("Đang chờ bộ môn xét đề tài");
    await gv.page.getByRole("dialog").getByRole("button",{name:"Đóng",exact:true}).click();
    await gv.page.goto(web + "/registrations");
    await expect(card(gv.page,title)).toContainText("GV được SV đề xuất");
    await expect(card(gv.page,title).getByRole("button",{name:"Chấp nhận"})).toHaveCount(0);
    await card(gv.page,title).getByRole("link",{name:"Xem mô tả và yêu cầu đề tài"}).click();
    await expect(gv.page).toHaveURL(/\/topics\?focus=/);
    await expect(gv.page.getByRole("dialog")).toContainText(title);
    expect(await read(peer.page,"/topics?search=" + encodeURIComponent(title))).toEqual([]);
    await tbm.page.goto(web + "/topics");
    await tbm.page.getByLabel("Tìm đề tài").fill(title);
    await card(tbm.page,title).getByRole("button",{name:"Xem và duyệt"}).click();
    dialog = tbm.page.getByRole("dialog");
    await dialog.getByLabel("Góp ý / lý do").fill("Làm rõ phạm vi của đề tài");
    await dialog.getByRole("button",{name:"Trả lại để sửa"}).click();
    await expect(dialog.getByText("Trả lại để sửa",{exact:true}).first()).toBeVisible();
    await dialog.getByRole("button",{name:"Đóng",exact:true}).click();
    await sv.page.goto(web + "/topics");
    await sv.page.getByRole("button",{name:"Đề xuất của tôi"}).click();
    await card(sv.page,title).getByRole("button",{name:"Xem chi tiết"}).click();
    dialog = sv.page.getByRole("dialog");
    await dialog.getByLabel("Mô tả, mục tiêu và phạm vi").fill("Phạm vi đăng ký và duyệt đề tài.");
    await dialog.getByRole("button",{name:"Lưu chỉnh sửa"}).click();
    await expect(dialog.getByText("Đã lưu đề tài.",{exact:true})).toBeVisible();
    await dialog.getByRole("button",{name:"Đóng",exact:true}).click();
    await sv.page.goto(web + "/registrations");
    await sv.page.getByRole("button",{name:"Gửi đề xuất cho bộ môn"}).click();
    await review(tbm.page,title,receiver.id);
    await sv.page.goto(web + "/registrations");
    await expect(card(sv.page,title + " đã duyệt").getByText("Bộ môn đã duyệt đề tài")).toBeVisible();
    await expect((await find(peer.page,title + " đã duyệt")).getByText("Sinh viên đề xuất",{exact:true})).toBeVisible();
    await join(peer.page,title + " đã duyệt",true);
    await gv.page.goto(web + "/registrations");
    await card(gv.page,title + " đã duyệt").getByRole("button",{name:"Từ chối",exact:true}).click();
    dialog = gv.page.getByRole("dialog");
    await expect(dialog.getByRole("button",{name:"Xác nhận từ chối"})).toBeDisabled();
    await dialog.getByLabel("Lý do từ chối").fill("Chưa phù hợp chuyên môn tiếp nhận");
    await dialog.getByRole("button",{name:"Xác nhận từ chối"}).click();
    await expect(dialog).toHaveCount(0);
    await expect(card(gv.page,title + " đã duyệt").getByText("GV từ chối",{exact:true})).toBeVisible();
    const reg = (await read(sv.page,"/topic-registrations")).find((r:{topic_title:string}) => r.topic_title === title + " đã duyệt");
    expect(reg.members.every((m:{active:boolean}) => m.active)).toBe(true);
    expect((await read(sv.page,"/me/eligibility?round_id=" + reg.round_id)).has_active_registration).toBe(true);
    await tbm.page.goto(web + "/registrations");
    await card(tbm.page,title + " đã duyệt").getByRole("button",{name:"Xử lý GV từ chối"}).click();
    dialog = tbm.page.getByRole("dialog",{name:"Xử lý đề tài sau khi GV từ chối"});
    const newReceiver = (await read(tbm.page,"/lecturers")).find((l:{lecturer_code:string}) => l.lecturer_code === "SYN-DEMO-GV-2");
    await dialog.getByLabel("GV mới tiếp nhận").selectOption(newReceiver.id);
    await dialog.getByLabel("Lý do / căn cứ xử lý").fill("Phân công GV phù hợp chuyên môn hơn");
    await dialog.getByRole("button",{name:"Lưu quyết định"}).click();
    await expect(dialog).toHaveCount(0);
    await gv2.page.goto(web + "/registrations");
    await card(gv2.page,title + " đã duyệt").getByRole("button",{name:"Chấp nhận chính thức và tạo khóa luận"}).click();
    await expect(card(gv2.page,title + " đã duyệt").getByRole("link",{name:/Mở hồ sơ khóa luận/})).toBeVisible();
  } finally {await close(actors);}
});

test("GV từ chối đề tài SV → TBM trả về → SV sửa, chọn GV mới và gửi lại", async ({browser}) => {
  const actors = await Promise.all(["returnFlow","tbm","gv","gv2"].map(key => login(browser,key)));
  const [sv,tbm,gv,gv2] = actors;
  try {
    const lecturerRows = await read(sv.page,"/lecturers");
    const first = lecturerRows.find((l:{lecturer_code:string}) => l.lecturer_code === "SYN-DEMO-GV-1");
    const second = lecturerRows.find((l:{lecturer_code:string}) => l.lecturer_code === "SYN-DEMO-GV-2");
    const title = "E2E SV sửa sau GV từ chối";
    await sv.page.goto(web+"/topics");
    await sv.page.getByRole("button",{name:"Tự đề xuất đề tài"}).click();
    let dialog = sv.page.getByRole("dialog");
    await dialog.getByLabel("Tên đề tài",{exact:true}).fill(title);
    await dialog.getByLabel("Số sinh viên tối đa").selectOption("1");
    await dialog.getByLabel("GV mong muốn tiếp nhận").selectOption(first.id);
    await dialog.getByRole("checkbox").check();
    await dialog.getByRole("button",{name:"Lập đăng ký của tôi"}).click();
    await expect(sv.page.getByRole("heading",{name:"Đăng ký đề tài"})).toBeVisible();
    await sv.page.getByRole("button",{name:"Gửi đề xuất cho bộ môn"}).click();
    await review(tbm.page,title,first.id);
    await gv.page.goto(web+"/registrations");
    await card(gv.page,title+" đã duyệt").getByRole("button",{name:"Từ chối"}).click();
    dialog = gv.page.getByRole("dialog",{name:"Từ chối đăng ký"});
    await dialog.getByLabel("Lý do từ chối").fill("Cần điều chỉnh phạm vi trước khi phân công");
    await dialog.getByRole("button",{name:"Xác nhận từ chối"}).click();
    await tbm.page.goto(web+"/registrations");
    await card(tbm.page,title+" đã duyệt").getByRole("button",{name:"Xử lý GV từ chối"}).click();
    dialog = tbm.page.getByRole("dialog",{name:"Xử lý đề tài sau khi GV từ chối"});
    await dialog.getByLabel("Hướng xử lý").selectOption("RETURN_TO_STUDENT");
    await dialog.getByLabel("Lý do / căn cứ xử lý").fill("Trả SV làm rõ mục tiêu và đề xuất GV khác");
    await dialog.getByRole("button",{name:"Lưu quyết định"}).click();
    await expect(dialog).toBeHidden();
    await sv.page.goto(web+"/topics");
    await sv.page.getByRole("button",{name:"Đề xuất của tôi"}).click();
    await card(sv.page,title+" đã duyệt").getByRole("button",{name:"Xem chi tiết"}).click();
    dialog = sv.page.getByRole("dialog");
    await dialog.getByLabel("Tên đề tài",{exact:true}).fill(title+" chỉnh phạm vi");
    await dialog.getByLabel("Mô tả, mục tiêu và phạm vi").fill("Phạm vi mới sau góp ý của bộ môn.");
    await dialog.getByLabel("GV mong muốn tiếp nhận").selectOption(second.id);
    await dialog.getByRole("button",{name:"Lưu chỉnh sửa"}).click();
    await expect(dialog.getByText("Đã lưu đề tài.",{exact:true})).toBeVisible();
    await dialog.getByRole("button",{name:"Đóng",exact:true}).click();
    await sv.page.goto(web+"/registrations");
    await card(sv.page,title+" chỉnh phạm vi").getByRole("button",{name:"Xác nhận đăng ký cũ của tôi"}).click();
    await card(sv.page,title+" chỉnh phạm vi").getByRole("button",{name:"Gửi đề xuất cho bộ môn"}).click();
    await review(tbm.page,title+" chỉnh phạm vi",second.id);
    await gv2.page.goto(web+"/registrations");
    await card(gv2.page,title+" chỉnh phạm vi đã duyệt").getByRole("button",{name:"Chấp nhận chính thức và tạo khóa luận"}).click();
    await expect(card(gv2.page,title+" chỉnh phạm vi đã duyệt").getByRole("link",{name:/Mở hồ sơ khóa luận/})).toBeVisible();
  } finally {await close(actors);}
});

test("Hai SV tranh chỗ cuối: chỉ một người tham gia, không vượt sức chứa", async ({browser}) => {
  const actors = await Promise.all(["gv","tbm","race1","race2","race3"].map(key => login(browser,key)));
  const [gv,tbm,first,a,b] = actors;
  try {
    const round = (await read(gv.page,"/rounds/open"))[0];
    let response = await write(gv.page,"/topics",{data:{round_id:round.id,title:"E2E Concurrent capacity",max_students:2}});
    expect(response.status()).toBe(201); let topic = await response.json();
    topic = await (await write(gv.page,"/topics/" + topic.id + "/submit",{headers:{"If-Match":String(topic.row_version)}})).json();
    expect((await write(tbm.page,"/topics/" + topic.id + "/department-decision",{
      headers:{"If-Match":String(topic.row_version)},data:{decision:"APPROVE"}})).status()).toBe(200);
    expect((await write(first.page,"/topic-registrations",{data:{topic_id:topic.id}})).status()).toBe(201);
    const competing = await Promise.all([a,b].map(actor => write(actor.page,"/topic-registrations",{data:{topic_id:topic.id}})));
    expect(competing.map(r => r.status()).sort()).toEqual([201,409]);
    const groups = await read(first.page,"/topic-registrations");
    expect(groups).toHaveLength(1); expect(groups[0].members).toHaveLength(2);
  } finally {await close(actors);}
});

test("SV nộp đề cương; tệp chưa quét được giữ cách ly và chặn nhận xét", async ({browser}) => {
  const actors = await Promise.all(["gv","tbm","proposalFlow"].map(key => login(browser,key)));
  const [gv,tbm,sv] = actors;
  try {
    const round = (await read(gv.page,"/rounds/open"))[0];
    let response = await write(gv.page,"/topics",{data:{round_id:round.id,title:"E2E Proposal workflow",max_students:1}});
    expect(response.status()).toBe(201); let topic = await response.json();
    topic = await (await write(gv.page,"/topics/"+topic.id+"/submit",{headers:{"If-Match":String(topic.row_version)}})).json();
    response = await write(tbm.page,"/topics/"+topic.id+"/department-decision",{
      headers:{"If-Match":String(topic.row_version)},data:{decision:"APPROVE"}});
    expect(response.status()).toBe(200);
    response = await write(sv.page,"/topic-registrations",{data:{topic_id:topic.id}});
    expect(response.status()).toBe(201); let registration = await response.json();
    response = await write(sv.page,"/topic-registrations/"+registration.id+"/submit");
    expect(response.status()).toBe(200); registration = await response.json();
    response = await write(gv.page,"/topic-registrations/"+registration.id+"/lecturer-decision",{
      headers:{"If-Match":String(registration.row_version)},data:{decision:"ACCEPT"}});
    expect(response.status()).toBe(200); registration = await response.json();
    expect(registration.state).toBe("FINALIZED");
    const thesisId = registration.thesis_id;
    expect(thesisId).toBeTruthy();
    await sv.page.goto(`${web}/theses/${thesisId}?section=proposal`);
    await expect(sv.page.getByRole("heading",{name:"Đề cương khóa luận"})).toBeVisible();
    await sv.page.getByLabel(/Nộp đề cương PDF hoặc DOCX/).setInputFiles({
      name:"de-cuong-v1.pdf",mimeType:"application/pdf",buffer:VALID_PDF});
    await sv.page.getByRole("button",{name:"Nộp đề cương",exact:true}).click();
    await expect(sv.page.getByText("Phiên bản 1 · de-cuong-v1.pdf",{exact:true})).toBeVisible();
    await expect(sv.page.getByText(/đã quét an toàn|Đang cách ly – chưa quét/i)).toBeVisible();
    const isQuarantined = await sv.page.getByText(/Đang cách ly – chưa quét/i).isVisible().catch(() => false);
    if (isQuarantined) {
      await expect(sv.page.getByRole("button",{name:"Tải bản nộp gốc v1",exact:true})).toBeDisabled();
      await gv.page.goto(`${web}/theses/${thesisId}?section=proposal`);
      await expect(gv.page.getByText(/Chưa thể nhận xét: tệp đang cách ly/)).toBeVisible();
      await expect(gv.page.getByLabel("Kết quả")).toHaveCount(0);
    } else {
      await expect(sv.page.getByRole("button",{name:"Tải bản nộp gốc v1",exact:true})).toBeEnabled();
      await gv.page.goto(`${web}/theses/${thesisId}?section=proposal`);
      await expect(gv.page.getByRole("button",{name:"Tải bản nộp gốc v1",exact:true})).toBeEnabled();
    }
    expect((await read(sv.page,`/theses/${thesisId}/proposal`)).state).toBe("SUBMITTED");
  } finally {await close(actors);}
});

test("Di động, bàn phím, lỗi tiếng Việt, phiên đăng nhập và accessibility", async ({browser}) => {
  const context = await browser.newContext({viewport:{width:360,height:800}});
  const page = await context.newPage();
  async function accessible(scope?: string) {
    const builder = new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa"]);
    if (scope) builder.include(scope);
    const result = await builder.analyze();
    expect(result.violations.map(v => ({id:v.id,targets:v.nodes.map(n => n.target)}))).toEqual([]);
  }
  try {
    await page.goto(web + "/");
    await page.getByLabel("Email",{exact:true}).fill(accounts.sv1.email);
    await page.getByLabel("Mật khẩu",{exact:true}).fill("incorrect-synthetic-password");
    await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
    await expect(page.getByRole("alert")).toContainText("Email hoặc mật khẩu");
    await accessible();
    await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts.sv1.password);
    await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
    await page.goto(web + "/topics");
    await expect(page.getByRole("heading",{name:"Đề tài",exact:true})).toBeVisible();
    await expect(page.locator("article").first()).toBeVisible();
    await expect(page).toHaveTitle("Đề tài · KLTN");
    expect(await page.locator("html").getAttribute("lang")).toBe("vi");
    expect(await page.locator('meta[name="robots"]').getAttribute("content")).toContain("noindex");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await accessible();
    await page.locator("article").first().getByRole("button",{name:"Xem chi tiết"}).click();
    await expect(page.getByRole("dialog")).toBeVisible(); await accessible('[role="dialog"]');
    await page.keyboard.press("Escape"); await expect(page.getByRole("dialog")).toHaveCount(0);
    await page.getByRole("button",{name:"Đăng xuất",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Đăng nhập hệ thống",exact:true})).toBeVisible();
    expect((await page.request.get(api + "/me/context")).status()).toBe(401);
  } finally {await context.close();}
});
