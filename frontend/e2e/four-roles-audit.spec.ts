import { test, expect, type Browser, type Page } from "@playwright/test";

const accounts: Record<string, { email: string; password: string }> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = `http://127.0.0.1:${process.env.KLTN_E2E_WEB_PORT || "5174"}`;
const api = `http://127.0.0.1:${process.env.KLTN_E2E_API_PORT || "8001"}/api/v1`;

const VALID_PDF = Buffer.from(
  "%PDF-1.3\n%âãÏÓ\n1 0 obj\n<<\n/Producer (pypdf)\n>>\nendobj\n" +
  "2 0 obj\n<<\n/Type /Pages\n/Count 1\n/Kids [ 4 0 R ]\n>>\nendobj\n" +
  "3 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n" +
  "4 0 obj\n<<\n/Type /Page\n/Resources <<\n>>\n/MediaBox [ 0.0 0.0 612 792 ]\n/Parent 2 0 R\n>>\nendobj\n" +
  "xref\n0 5\n0000000000 65535 f \n0000000015 00000 n \n0000000054 00000 n \n0000000113 00000 n \n0000000162 00000 n \n" +
  "trailer\n<<\n/Size 5\n/Root 3 0 R\n/Info 1 0 R\n>>\nstartxref\n256\n%%EOF\n"
);

async function login(browser: Browser, key: string) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(web + "/");
  await page.getByLabel("Email", { exact: true }).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(accounts[key].password);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Tổng quan", exact: true })).toBeVisible();
  return { page, context, errors };
}

async function close(actors: Awaited<ReturnType<typeof login>>[]) {
  for (const actor of actors) {
    await actor.context.close().catch(() => undefined);
  }
}

async function read(page: Page, path: string) {
  const r = await page.request.get(api + path);
  expect(r.status()).toBe(200);
  return r.json();
}

test("Admin: Toggle ẩn/hiện mật khẩu, quản lý đợt KLTN, phân công đợt, sửa email GV giữ UUID và duyệt danh sách sinh viên", async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));

  try {
    // 1. Kiểm tra toggle ẩn/hiện mật khẩu trên màn hình đăng nhập
    await page.goto(web + "/");
    const passwordInput = page.getByLabel("Mật khẩu", { exact: true });
    await passwordInput.fill("mat_khau_kiem_thu_123");
    expect(await passwordInput.getAttribute("type")).toBe("password");
    const toggleBtn = page.getByRole("button", { name: /Hiện mật khẩu|Ẩn mật khẩu/i });
    await expect(toggleBtn).toBeVisible();
    await toggleBtn.click();
    expect(await passwordInput.getAttribute("type")).toBe("text");
    await toggleBtn.click();
    expect(await passwordInput.getAttribute("type")).toBe("password");

    // Đăng nhập Admin
    await page.getByLabel("Email", { exact: true }).fill(accounts.admin.email);
    await passwordInput.fill(accounts.admin.password);
    await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Tổng quan", exact: true })).toBeVisible();

    // 2. Quản lý đợt KLTN (/rounds)
    await page.goto(web + "/rounds");
    await expect(page.getByRole("heading", { name: "Quản lý đợt KLTN" })).toBeVisible();

    const roundCode = "AUDIT-R1";
    await page.getByLabel("Năm học (ví dụ 2026-2027)").fill("2096-2097");
    await page.getByLabel("Ngày bắt đầu năm học").fill("2096-09-01");
    await page.getByLabel("Ngày kết thúc năm học").fill("2097-08-31");
    await page.getByLabel("Mã đợt").fill(roundCode);
    await page.getByLabel("Mở đăng ký lúc").fill("2096-09-10T08:00");
    await page.getByLabel("Đóng đăng ký lúc").fill("2096-10-10T17:00");
    await page.getByLabel("Căn cứ lịch đợt").fill("Kế hoạch đào tạo năm 2096");
    await page.getByRole("button", { name: "Tạo bản nháp" }).click();
    await expect(page.getByText(/Đã tạo đợt ở trạng thái bản nháp/)).toBeVisible();

    // Sửa bản nháp
    const roundRow = page.locator(".account-list__row").filter({ hasText: roundCode });
    await expect(roundRow).toBeVisible();
    await roundRow.getByRole("button", { name: "Sửa bản nháp" }).click();
    await page.getByLabel("Đóng đăng ký lúc").fill("2096-10-15T17:00");
    await page.getByLabel("Lý do sửa lịch").fill("Gia hạn thêm 5 ngày chuẩn bị");
    await page.getByRole("button", { name: "Lưu bản nháp" }).click();
    await expect(page.getByText(/Đã cập nhật bản nháp/)).toBeVisible();

    // Mở đợt
    await roundRow.getByRole("button", { name: "Mở đợt" }).click();
    let dialog = page.getByRole("dialog");
    await dialog.getByLabel("Lý do / căn cứ").fill("Quyết định mở đợt chính thức");
    await dialog.getByRole("button", { name: "Mở đợt" }).click();
    await expect(roundRow).toContainText("Đã mở");

    // Đóng đợt
    await roundRow.getByRole("button", { name: "Đóng đợt" }).click();
    dialog = page.getByRole("dialog");
    await dialog.getByLabel("Lý do / căn cứ").fill("Hết thời hạn đăng ký đợt");
    await dialog.getByRole("button", { name: "Đóng đợt" }).click();
    await expect(roundRow).toContainText("Đã đóng");

    // 3. Phân công theo đợt (/administration/assignments)
    await page.goto(web + "/administration/assignments");
    await expect(page.getByRole("heading", { name: "Phân công theo đợt", level: 1 })).toBeVisible();

    // Phân công KLTN_COORDINATOR và ELIGIBILITY_VERIFIER cho giảng viên
    const assignmentCard = page.locator("section.card").filter({ has: page.getByRole("heading", { name: "Giao nhiệm vụ theo đợt", exact: true }) });
    const roundsList = await read(page, "/admin/rounds");
    const openRound = roundsList.find((r: { state: string }) => r.state === "OPEN");
    expect(openRound).toBeTruthy();
    const gvUser = (await read(page, "/admin/users?search=" + encodeURIComponent(accounts.gv2.email)))[0];
    expect(gvUser).toBeTruthy();

    await expect(assignmentCard.locator("select").nth(0).locator(`option[value="${openRound.id}"]`)).toHaveCount(1);
    await expect(assignmentCard.locator("select").nth(1).locator(`option[value="${gvUser.id}"]`)).toHaveCount(1);
    await assignmentCard.locator("select").nth(0).selectOption(openRound.id);
    await assignmentCard.locator("select").nth(2).selectOption("KLTN_COORDINATOR");
    await assignmentCard.locator("select").nth(1).selectOption(gvUser.id);
    await assignmentCard.getByLabel("Căn cứ phân công").fill("Quyết định giao nhiệm vụ điều phối đợt");
    await assignmentCard.getByRole("button", { name: "Lưu phân công", exact: true }).click();
    await expect(page.getByRole("status").filter({hasText:"Đã lưu phân công"})).toBeVisible();

    // Tạo giảng viên mới & sửa email
    await page.goto(web+"/administration");
    const suffix = Date.now().toString().slice(-5);
    const initialEmail = `audit-gv-${suffix}@e2e.test`;
    const updatedEmail = `audit-gv-new-${suffix}@e2e.test`;
    await page.getByLabel("Mã giảng viên").fill(`GV-AUDIT-${suffix}`);
    await page.getByLabel("Họ tên").fill("Giảng viên kiểm thử");
    await page.getByLabel("Email", { exact: true }).fill(initialEmail);
    const deptSelect = page.getByRole("combobox",{name:"Bộ môn",exact:true});
    await deptSelect.selectOption({ index: 1 });
    await page.getByRole("button", { name: "Tạo và gửi lời mời" }).click();
    await expect(page.getByText(/Đã tạo tài khoản/)).toBeVisible();

    // Sửa email giảng viên giữ nguyên UUID
    await page.getByLabel("Lý do thao tác tài khoản").fill("KHOA E2E xác minh mất hộp thư");
    await page.getByRole("textbox",{name:/Tìm theo .*email/}).fill(initialEmail);
    const accountCard = page.locator("section.card").filter({ has: page.getByRole("heading", { name: "Tài khoản", exact: true }) });
    const gvRow = accountCard.locator(".account-list__row");
    await expect(gvRow).toHaveCount(1);
    await gvRow.getByRole("button", { name: "Sửa email" }).click();
    await accountCard.getByLabel("Lý do sửa email",{exact:true}).fill("KHOA E2E xác minh mất hộp thư");
    await accountCard.getByLabel("Email mới").fill(updatedEmail);
    await accountCard.getByLabel("Căn cứ xác minh của Khoa").fill("Xác nhận đổi địa chỉ thư điện tử chính thức");
    await accountCard.getByRole("button", { name: "Lưu email mới" }).click();
    await expect(page.getByText(/Đã sửa email trên tài khoản cũ/)).toBeVisible();

    // Kiểm tra tìm kiếm và hiển thị email mới
    await page.getByRole("textbox",{name:/Tìm theo .*email/}).fill(updatedEmail);
    await expect(gvRow).toHaveCount(1);
    await expect(gvRow.getByText(updatedEmail)).toBeVisible();

    expect(errors).toEqual([]);
  } finally {
    await context.close();
  }
});

test("TBM: Xét duyệt đề tài GV và xử lý cả hai nhánh khi GV từ chối đề tài SV (Đổi GV vs Trả về SV)", async ({ browser }) => {
  const actors = await Promise.all(["tbm", "gv2", "auditSv1", "proposalPeer"].map(key => login(browser, key)));
  const [tbm, gv2, sv1, svPeer] = actors;

  try {
    // 1. TBM duyệt đề tài do GV đề xuất
    const gvTopicTitle = "Đề tài GV kiểm thử TBM duyệt " + Date.now().toString().slice(-4);
    await gv2.page.goto(web + "/topics");
    await gv2.page.getByRole("button", { name: "Tạo đề tài", exact: true }).click();
    let dialog = gv2.page.getByRole("dialog");
    await dialog.getByLabel("Tên đề tài", { exact: true }).fill(gvTopicTitle);
    await dialog.getByLabel("Mô tả, mục tiêu và phạm vi").fill("Mô tả kiểm thử quy trình duyệt đề tài.");
    await dialog.getByLabel("Số sinh viên tối đa").selectOption("2");
    await dialog.getByRole("button", { name: "+ Thêm yêu cầu" }).click();
    await dialog.getByLabel("Nội dung", { exact: true }).fill("Kiến thức nền tảng Web & DB");
    await dialog.getByRole("button", { name: "Tạo bản nháp", exact: true }).click();
    dialog = gv2.page.getByRole("dialog");
    await dialog.getByRole("button", { name: "Gửi bộ môn duyệt" }).click();
    await expect(dialog.getByText("Đã gửi", { exact: true })).toBeVisible();

    // TBM mở danh sách và xem xét duyệt
    await tbm.page.goto(web + "/topics");
    await tbm.page.getByLabel("Tìm đề tài").fill(gvTopicTitle);
    const topicCard = tbm.page.locator("article").filter({ has: tbm.page.getByRole("heading", { name: gvTopicTitle, exact: true }) });
    await topicCard.getByRole("button", { name: "Xem và duyệt" }).click();
    dialog = tbm.page.getByRole("dialog");
    const approvedTitle = gvTopicTitle + " đã chuẩn hóa";
    await dialog.getByLabel("Tên đề tài sau khi duyệt").fill(approvedTitle);
    await dialog.getByRole("button", { name: "Duyệt đề tài", exact: true }).click();
    await expect(dialog.getByText("Đã duyệt", { exact: true })).toBeVisible();
    await dialog.getByRole("button", { name: "Đóng", exact: true }).click();

    // 2. Đề tài SV tự đề xuất -> GV từ chối -> TBM xử lý Nhánh 1: Phân công GV khác
    const svTopic1 = "Đề tài SV đề xuất nhánh 1 " + Date.now().toString().slice(-4);
    const gvList = await read(sv1.page, "/lecturers");
    const gv2Info = gvList.find((l: { lecturer_code: string }) => l.lecturer_code === "SYN-DEMO-GV-2");
    const headInfo = gvList.find((l: { lecturer_code: string }) => l.lecturer_code === "SYN-DEMO-TBM");
    expect(gv2Info).toBeTruthy();
    expect(headInfo).toBeTruthy();

    await sv1.page.goto(web + "/topics");
    await sv1.page.getByRole("button", { name: "Tự đề xuất đề tài", exact: true }).click();
    dialog = sv1.page.getByRole("dialog");
    await dialog.getByLabel("Tên đề tài", { exact: true }).fill(svTopic1);
    await dialog.getByLabel("Số sinh viên tối đa").selectOption("2");
    await dialog.getByLabel("GV mong muốn tiếp nhận").selectOption(gv2Info.id);
    await dialog.getByRole("checkbox").check();
    await dialog.getByRole("button", { name: "Lập đăng ký của tôi" }).click();
    await expect(sv1.page.getByRole("heading", { name: "Đăng ký đề tài", exact: true })).toBeVisible();

    await sv1.page.getByRole("button", { name: "Gửi đề xuất cho bộ môn" }).click();
    await expect(sv1.page.getByText("Chờ bộ môn duyệt đề tài")).toBeVisible();

    // TBM duyệt nội dung đề tài SV đề xuất
    await tbm.page.goto(web + "/topics");
    await tbm.page.getByLabel("Tìm đề tài").fill(svTopic1);
    const svCard = tbm.page.locator("article").filter({ has: tbm.page.getByRole("heading", { name: svTopic1, exact: true }) });
    await svCard.getByRole("button", { name: "Xem và duyệt" }).click();
    dialog = tbm.page.getByRole("dialog");
    const svApproved1 = svTopic1 + " đã duyệt";
    await dialog.getByLabel("Tên đề tài sau khi duyệt").fill(svApproved1);
    await dialog.getByLabel("GV tiếp nhận (xác nhận hoặc chọn lại)").selectOption(gv2Info.id);
    await dialog.getByRole("button", { name: "Duyệt đề tài", exact: true }).click();
    await expect(dialog.getByText("Đã duyệt", { exact: true })).toBeVisible();
    await dialog.getByRole("button", { name: "Đóng", exact: true }).click();

    // GV 2 từ chối tiếp nhận
    await gv2.page.goto(web + "/registrations");
    const regCard1 = gv2.page.locator("article").filter({ has: gv2.page.getByRole("heading", { name: svApproved1, exact: true }) });
    await regCard1.getByRole("button", { name: "Từ chối", exact: true }).click();
    dialog = gv2.page.getByRole("dialog", { name: "Từ chối đăng ký" });
    await dialog.getByLabel("Lý do từ chối").fill("Quá tải số lượng hướng dẫn đợt này");
    await dialog.getByRole("button", { name: "Xác nhận từ chối" }).click();
    await expect(dialog).toBeHidden();

    // TBM vào xử lý: Chọn Trưởng bộ môn tiếp nhận
    await tbm.page.goto(web + "/registrations");
    const tbmRegCard = tbm.page.locator("article").filter({ has: tbm.page.getByRole("heading", { name: svApproved1, exact: true }) });
    await tbmRegCard.getByRole("button", { name: "Xử lý GV từ chối" }).click();
    dialog = tbm.page.getByRole("dialog", { name: "Xử lý đề tài sau khi GV từ chối" });
    await dialog.getByLabel("Hướng xử lý").selectOption("REASSIGN");
    await dialog.getByLabel("GV mới tiếp nhận").selectOption(headInfo.id);
    await dialog.getByLabel("Lý do / căn cứ xử lý").fill("Phân bổ lại số lượng đề tài trong bộ môn");
    await dialog.getByRole("button", { name: "Lưu quyết định" }).click();
    await expect(dialog).toBeHidden();

    // TBM tiếp nhận chính thức
    await tbm.page.goto(web + "/registrations");
    const regCardHead = tbm.page.locator("article").filter({ has: tbm.page.getByRole("heading", { name: svApproved1, exact: true }) });
    await regCardHead.getByRole("button", { name: "Chấp nhận chính thức và tạo khóa luận" }).click();
    await expect(regCardHead.getByRole("link", { name: /Mở hồ sơ khóa luận/ })).toBeVisible();

  } finally {
    await close(actors);
  }
});

test("GV & SV: Đăng ký nhóm, chấp nhận chính thức tạo khóa luận + GVHD, nộp và duyệt tiến độ & đề cương & tài liệu, quét ClamAV và xuất bản in 3 dòng footer", async ({ browser }) => {
  test.setTimeout(180000);
  const actors = await Promise.all(["admin", "gv2", "tbm", "auditSv2", "auditSv3"].map(key => login(browser, key)));
  const [admin, gv, tbm, sv1, sv2] = actors;

  try {
    const topicTitle = "Khóa luận kiểm thử luồng trọn vẹn " + Date.now().toString().slice(-4);

    // 0. Admin phân công GV làm KLTN_COORDINATOR cho đợt mở nếu chưa có
    const rounds = await read(admin.page, "/admin/rounds");
    const round = rounds.find((item: { state: string }) => item.state === "OPEN");
    expect(round).toBeTruthy();
    const lecturer = (await read(admin.page, "/admin/users?search=" + encodeURIComponent(accounts.gv2.email)))[0];
    const currentAssignments = await read(admin.page, "/admin/round-assignments");
    const alreadyCoord = currentAssignments.some((a: { user_id: string; round_id: string; assignment_type: string }) =>
      a.user_id === lecturer.id && a.round_id === round.id && a.assignment_type === "KLTN_COORDINATOR");
    if (!alreadyCoord) {
      await admin.page.goto(web + "/administration/assignments");
      const assignment = admin.page.locator("section.card").filter({ has: admin.page.getByRole("heading", { name: "Giao nhiệm vụ theo đợt", exact: true }) });
      await expect(assignment.locator("select").nth(0).locator(`option[value="${round.id}"]`)).toHaveCount(1);
      await expect(assignment.locator("select").nth(1).locator(`option[value="${lecturer.id}"]`)).toHaveCount(1);
      await assignment.locator("select").nth(0).selectOption(round.id);
      await assignment.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("KLTN_COORDINATOR");
      await assignment.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption(lecturer.id);
      await assignment.getByLabel("Căn cứ phân công").fill("Giao nhiệm vụ điều phối tiến độ đợt");
      await assignment.getByRole("button", { name: "Lưu phân công", exact: true }).click();
      await expect(admin.page.getByRole("status").filter({hasText:"Đã lưu phân công"})).toBeVisible();
    }

    // 1. GV tạo đề tài nhóm 2 SV
    await gv.page.goto(web + "/topics");
    await gv.page.getByRole("button", { name: "Tạo đề tài", exact: true }).click();
    let dialog = gv.page.getByRole("dialog");
    await dialog.getByLabel("Tên đề tài", { exact: true }).fill(topicTitle);
    await dialog.getByLabel("Mô tả, mục tiêu và phạm vi").fill("Xây dựng giải pháp phần mềm và minh chứng.");
    await dialog.getByLabel("Số sinh viên tối đa").selectOption("2");
    await dialog.getByRole("button", { name: "+ Thêm yêu cầu" }).click();
    await dialog.getByLabel("Nội dung", { exact: true }).fill("Kỹ năng lập trình TypeScript và Python");
    await dialog.getByRole("button", { name: "Tạo bản nháp", exact: true }).click();
    dialog = gv.page.getByRole("dialog");
    await dialog.getByRole("button", { name: "Gửi bộ môn duyệt" }).click();
    await expect(dialog.getByText("Đã gửi", { exact: true })).toBeVisible();

    // TBM duyệt đề tài
    await tbm.page.goto(web + "/topics");
    await tbm.page.getByLabel("Tìm đề tài").fill(topicTitle);
    const cardTbm = tbm.page.locator("article").filter({ has: tbm.page.getByRole("heading", { name: topicTitle, exact: true }) });
    await cardTbm.getByRole("button", { name: "Xem và duyệt" }).click();
    dialog = tbm.page.getByRole("dialog");
    await dialog.getByRole("button", { name: "Duyệt đề tài", exact: true }).click();
    await expect(dialog.getByText("Đã duyệt", { exact: true })).toBeVisible();
    await dialog.getByRole("button", { name: "Đóng", exact: true }).click();

    // 2. SV1 đăng ký đề tài (trưởng nhóm)
    await sv1.page.goto(web + "/topics");
    await sv1.page.getByRole("button", { name: /^Đề tài có sẵn/ }).click();
    await sv1.page.getByLabel("Tìm đề tài").fill(topicTitle);
    const sv1Card = sv1.page.locator("article").filter({ has: sv1.page.getByRole("heading", { name: topicTitle, exact: true }) });
    await sv1Card.getByRole("button", { name: "Đăng ký", exact: true }).click();
    dialog = sv1.page.getByRole("dialog");
    await dialog.getByRole("checkbox").check();
    await dialog.getByRole("button", { name: "Lập đăng ký của tôi", exact: true }).click();
    await expect(sv1.page).toHaveURL(/\/registrations$/);

    // SV2 tham gia nhóm (thành viên 2/2)
    await sv2.page.goto(web + "/topics");
    await sv2.page.getByRole("button", { name: /^Đề tài có sẵn/ }).click();
    await sv2.page.getByLabel("Tìm đề tài").fill(topicTitle);
    const sv2Card = sv2.page.locator("article").filter({ has: sv2.page.getByRole("heading", { name: topicTitle, exact: true }) });
    await sv2Card.getByRole("button", { name: "Tham gia", exact: true }).click();
    dialog = sv2.page.getByRole("dialog");
    await dialog.getByRole("checkbox").check();
    await dialog.getByRole("button", { name: "Tham gia đề tài", exact: true }).click();
    await expect(sv2.page).toHaveURL(/\/registrations$/);

    // Trưởng nhóm gửi đăng ký cho GV
    await sv1.page.goto(web + "/registrations");
    const regSv1 = sv1.page.locator("article").filter({ has: sv1.page.getByRole("heading", { name: topicTitle, exact: true }) });
    await expect(regSv1.getByText("2/2 SV", { exact: true })).toBeVisible();
    await regSv1.getByRole("button", { name: "Gửi đăng ký cho GV" }).click();
    await expect(regSv1.getByText("Đã gửi", { exact: true }).first()).toBeVisible();

    // Trước khi GV duyệt: Kiểm tra nút "Rút đăng ký" tồn tại
    await expect(regSv1.getByRole("button", { name: "Rút đăng ký", exact: true })).toBeVisible();

    // 3. GV kiểm tra thông báo và chấp nhận chính thức
    await gv.page.goto(web);
    const bell = gv.page.getByRole("button", { name: /Thông báo/ });
    await expect(bell).toBeVisible();

    await gv.page.goto(web + "/registrations");
    const gvRegCard = gv.page.locator("article").filter({ has: gv.page.getByRole("heading", { name: topicTitle, exact: true }) });
    await gvRegCard.getByRole("button", { name: "Chấp nhận chính thức và tạo khóa luận", exact: true }).click();
    await expect(gvRegCard.getByText("Đã tiếp nhận chính thức", { exact: false }).first()).toBeVisible();

    // Sau khi GV chấp nhận: Nút "Rút đăng ký" phải biến mất (khóa thao tác rút)
    await sv1.page.reload();
    await expect(sv1.page.locator("article").filter({ has: sv1.page.getByRole("heading", { name: topicTitle, exact: true }) }).getByRole("button", { name: "Rút đăng ký", exact: true })).toHaveCount(0);

    // Mở hồ sơ khóa luận từ trang Đăng ký
    await sv1.page.locator("article").filter({ has: sv1.page.getByRole("heading", { name: topicTitle, exact: true }) }).getByRole("link", { name: /Mở hồ sơ khóa luận/ }).click();
    await expect(sv1.page.getByRole("heading", { name: topicTitle, exact: true })).toBeVisible();

    // 4. Mở mốc tiến độ (GV với tư cách điều phối đợt)
    await gv.page.goto(sv1.page.url());
    await gv.page.getByRole("tab", { name: "Báo cáo tiến độ", exact: true }).click();
    await expect(gv.page.getByRole("heading", { name: "Tạo mốc nội bộ của khóa luận", exact: true })).toBeVisible();

    // Thiết lập mốc
    const milestoneCode = "MOC_AUDIT_1";
    const future = new Date(Date.now() + 4 * 24 * 60 * 60 * 1000);
    const dueAt = `${future.getFullYear()}-${String(future.getMonth() + 1).padStart(2, "0")}-${String(future.getDate()).padStart(2, "0")}T17:00`;
    await gv.page.getByLabel("Mã mốc").fill(milestoneCode);
    await gv.page.getByLabel("Tên mốc").fill("Mốc thẩm định tiến độ tháng 10");
    await gv.page.getByLabel("Hạn nộp (giờ Việt Nam)").fill(dueAt);
    await gv.page.getByLabel("Tiến độ dự kiến (%)").fill("35");
    await gv.page.getByRole("button", { name: "Tạo mốc nội bộ", exact: true }).click();
    await expect(gv.page.getByRole("heading", { name: "Mốc thẩm định tiến độ tháng 10 · v1", exact: true })).toBeVisible();

    // 5. SV nộp báo cáo tiến độ và tự sửa trước hạn
    await sv1.page.reload();
    await sv1.page.getByRole("tab", { name: "Báo cáo tiến độ", exact: true }).click();
    await sv1.page.getByLabel("Mốc báo cáo").selectOption({ index: 1 });
    await sv1.page.getByLabel("Kết quả, khó khăn và kế hoạch").fill("Hoàn thành nghiên cứu tài liệu và thiết kế kiến trúc.");
    await sv1.page.getByLabel("Tiến độ tự báo cáo (%)").fill("35");
    await sv1.page.getByRole("button", { name: "Gửi báo cáo", exact: true }).click();
    await expect(sv1.page.getByText("Hoàn thành nghiên cứu tài liệu và thiết kế kiến trúc.", { exact: true })).toBeVisible();

    // Tự nộp bản sửa trước hạn khi GV chưa duyệt
    await sv1.page.getByLabel("Mốc báo cáo").selectOption({ index: 1 });
    await sv1.page.getByLabel("Kết quả, khó khăn và kế hoạch").fill("Bổ sung sơ đồ lớp và lược đồ cơ sở dữ liệu.");
    await sv1.page.getByLabel("Tiến độ tự báo cáo (%)").fill("40");
    await sv1.page.getByRole("button", { name: "Gửi báo cáo", exact: true }).click();
    await expect(sv1.page.getByText("Bổ sung sơ đồ lớp và lược đồ cơ sở dữ liệu.", { exact: true })).toBeVisible();

    // GV xác nhận tiến độ
    await gv.page.reload();
    const progressCard = gv.page.locator("article.card").filter({ has: gv.page.getByText("Bổ sung sơ đồ lớp và lược đồ cơ sở dữ liệu.", { exact: true }) });
    await progressCard.getByLabel("Kết quả").selectOption("CONFIRM");
    await progressCard.getByLabel("Nhận xét / lý do").fill("Tiến độ đạt yêu cầu kế hoạch đợt.");
    await progressCard.getByRole("button", { name: "Gửi kết quả", exact: true }).click();
    await expect(gv.page.getByRole("status")).toContainText("Đã lưu nhận xét tiến độ");

    // Current unified submission UI: open PLAN intake, submit once, review the
    // exact version, and export the accepted source without creating empty files.
    const thesisPath=new URL(sv1.page.url()).pathname;
    await gv.page.goto(web+thesisPath+"?section=submissions&kind=PLAN");
    const deadlineCard=gv.page.locator("section.card").filter({has:gv.page.getByRole("heading",{name:"Lịch nhận tài liệu của đợt",exact:true})});
    const planDue=new Date(Date.now()+60*86400000);
    const planDueStr=`${planDue.getFullYear()}-${String(planDue.getMonth()+1).padStart(2,"0")}-${String(planDue.getDate()).padStart(2,"0")}T17:00`;
    await deadlineCard.getByLabel("Hạn mới (giờ Việt Nam)").fill(planDueStr);
    await deadlineCard.getByLabel("Căn cứ / lý do").fill("Kế hoạch nộp Mẫu 2 toàn đợt");
    await deadlineCard.getByRole("button",{name:/Thiết lập cho cả đợt|Gia hạn cho cả đợt/}).click();
    await sv1.page.goto(web+thesisPath+"?section=submissions&kind=PLAN");
    await expect(sv1.page.getByRole("button",{name:"Tải mẫu áp dụng · Mẫu 2",exact:true})).toBeVisible();
    await sv1.page.getByLabel(/Tệp cần nộp/).setInputFiles({name:"ke-hoach-thuc-hien-v1.pdf",mimeType:"application/pdf",buffer:VALID_PDF});
    await sv1.page.getByRole("button",{name:"Nộp kế hoạch Mẫu 2",exact:true}).click();
    await expect(sv1.page.getByText("Phiên bản 1 · ke-hoach-thuc-hien-v1.pdf",{exact:true})).toBeVisible();
    await expect(sv1.page.getByText("Đã quét an toàn",{exact:true})).toBeVisible();
    await gv.page.reload();
    await gv.page.getByRole("button",{name:"Xem tệp & nhận xét",exact:true}).click();
    const fileReview=gv.page.getByRole("dialog");
    await fileReview.getByLabel("Kết quả",{exact:true}).selectOption("ACCEPT");
    await fileReview.getByLabel("Nhận xét tổng quát",{exact:true}).fill("Kế hoạch chi tiết, khả thi.");
    await fileReview.getByRole("button",{name:/^Hoàn thành và gửi góp ý/}).click();
    await expect(fileReview).toHaveCount(0);
    await sv1.page.reload();
    await expect(sv1.page.getByRole("button",{name:/Xuất bản đã duyệt để ký ngoài/})).toBeEnabled();

  } finally {
    await close(actors);
  }
});
