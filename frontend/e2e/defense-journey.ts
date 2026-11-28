import { expect, type Page } from '@playwright/test';
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';

type Credentials = { email: string; password: string };
const code = '0023417801';
const email = 'nv6-journey@example.invalid';
export const journeyClass = 'CNTT-E2E';
export const journeyTitle = 'Đề tài kiểm thử NV6 xuyên suốt';

export async function signIn(page: Page, credentials: Credentials) {
  await page.goto('/');
  await page.getByLabel('Email', { exact: true }).fill(credentials.email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(credentials.password);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Tổng quan', exact: true })).toBeVisible();
}

export async function activateStudent(admin: Page, student: Page, adminEmail: string, chairId: string) {
  for (const [role, assignee] of [
    ['ELIGIBILITY_IMPORTER', { label: adminEmail }], ['KLTN_COORDINATOR', { value: chairId }],
  ] as const) {
    await admin.goto('/administration/assignments');
    await admin.getByRole('combobox', { name: 'Đợt', exact: true }).selectOption({ label: 'SYN-DEMO · OPEN' });
    await admin.getByLabel('Nhiệm vụ').selectOption(role);
    await admin.getByRole('combobox', { name: 'Người được giao', exact: true }).selectOption(assignee);
    await admin.getByLabel('Căn cứ phân công').fill('Phân công đợt kiểm thử tích hợp');
    await admin.getByRole('button', { name: 'Lưu phân công', exact: true }).click();
    await expect(admin.getByText('Đã lưu phân công.', { exact: true })).toBeVisible();
  }
  await admin.goto('/roster');
  await admin.getByRole('tab', { name: /Nhập danh sách/ }).click();
  const csv = [
    'MSSV;Họ và tên;Email;Mã bộ môn;Lớp;Mã ngành',
    `${code};Sinh viên thử nghiệm NV6;${email};SYN-DEMO-DEP;${journeyClass};7480201`,
  ].join('\n');
  await admin.locator('input[type="file"]').setInputFiles({ name: 'nv6-roster.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) });
  await admin.getByLabel('Mã/số văn bản nguồn').fill('E2E-ROSTER-NV6');
  await admin.getByRole('button', { name: 'Kiểm tra tệp' }).click();
  await expect(admin.getByRole('heading', { name: /Xem trước: 1 sinh viên/ })).toBeVisible();
  await admin.getByRole('button', { name: 'Nhập sau khi kiểm' }).click();
  await expect(admin.getByText(/Đã ghi nhận 1 sinh viên đủ điều kiện/)).toBeVisible();
  await student.goto('/account/activation-request');
  await student.getByLabel('MSSV hoặc mã giảng viên').fill(code);
  await student.getByLabel('Email đã đăng ký').fill(email);
  await student.getByRole('button', { name: 'Gửi hướng dẫn' }).click();
  await expect(student.getByText(/Nếu thông tin hợp lệ/)).toBeVisible();
  const mailbox = path.join(process.env.KLTN_E2E_RUN_DIR!, 'mail-outbox');
  let activation = '';
  await expect.poll(async () => {
    const files = await readdir(mailbox).catch(() => []);
    for (const file of files) {
      const message = await readFile(path.join(mailbox, file), 'utf8');
      if (message.split(/\r?\n/, 1)[0] === `To: ${email}`) {
        activation = message.match(/http:\/\/[^\s]+\/account\/activate\?token=[^\s]+/)?.[0] ?? '';
        break;
      }
    }
    return Boolean(activation);
  }).toBe(true);
  expect(new URL(activation).origin).toBe(new URL(student.url()).origin);
  await student.goto(activation);
  const password = 'Synthetic-NV6-Acceptance-2026!';
  await student.getByLabel('Mật khẩu mới', { exact: true }).fill(password);
  await student.getByLabel('Nhập lại mật khẩu', { exact: true }).fill(password);
  await student.getByRole('button', { name: 'Lưu mật khẩu' }).click();
  await expect(student.getByText(/Đã cập nhật mật khẩu/)).toBeVisible();
  await signIn(student, { email, password });
}

export async function registerTopic(advisor: Page, chair: Page, student: Page) {
  const card = (page: Page) => page.locator('article').filter({
    has: page.getByRole('heading', { name: journeyTitle, exact: true }),
  });
  await advisor.goto('/topics');
  await advisor.getByRole('button', { name: 'Tạo đề tài', exact: true }).click();
  let dialog = advisor.getByRole('dialog');
  await dialog.getByLabel('Tên đề tài', { exact: true }).fill(journeyTitle);
  await dialog.getByLabel('Mô tả, mục tiêu và phạm vi').fill('Dữ liệu giả kiểm thử liên tục từ đăng ký đến lưu kho.');
  await dialog.getByLabel('Số sinh viên tối đa').selectOption('1');
  await dialog.getByRole('button', { name: 'Tạo bản nháp', exact: true }).click();
  await dialog.getByRole('button', { name: 'Gửi bộ môn duyệt' }).click();
  await expect(dialog.getByText('Đã gửi', { exact: true })).toBeVisible();
  await chair.goto('/topics');
  await chair.getByLabel('Tìm đề tài').fill(journeyTitle);
  await card(chair).getByRole('button', { name: 'Xem và duyệt' }).click();
  dialog = chair.getByRole('dialog');
  await dialog.getByRole('button', { name: 'Duyệt đề tài', exact: true }).click();
  await expect(dialog.getByText('Đã duyệt', { exact: true })).toBeVisible();

  await student.goto('/topics');
  await student.getByRole('button', { name: /^Đề tài có sẵn/ }).click();
  await student.getByLabel('Tìm đề tài').fill(journeyTitle);
  await card(student).getByRole('button', { name: 'Đăng ký', exact: true }).click();
  dialog = student.getByRole('dialog');
  await dialog.getByRole('checkbox').check();
  await dialog.getByRole('button', { name: 'Lập đăng ký của tôi', exact: true }).click();
  await card(student).getByRole('link', { name: 'Mở đơn Mẫu 1a/1b · nộp, tải & lịch sử' }).click();
  await student.getByLabel(/Nộp đơn Mẫu 1a/).setInputFiles(process.env.KLTN_E2E_FORM_1A_FILE!);
  await student.getByRole('button', { name: 'Nộp phiên bản đơn', exact: true }).click();
  await expect(student.getByRole('button', { name: 'Tải đơn gốc v1', exact: true })).toBeEnabled({ timeout: 60000 });
  await student.goto('/registrations');
  await card(student).getByRole('button', { name: 'Gửi đăng ký cho GV' }).click();
  await expect(card(student).getByText('Đã gửi', { exact: true }).first()).toBeVisible();
  await advisor.goto('/registrations');
  await card(advisor).getByRole('button', { name: 'Chấp nhận chính thức và tạo khóa luận', exact: true }).click();
  await expect(card(advisor).getByText(/Đã tiếp nhận chính thức/).first()).toBeVisible();
  await student.reload();
  await card(student).getByRole('link', { name: /Mở hồ sơ khóa luận/ }).click();
  await expect(student).toHaveURL(/\/theses\/[\da-f-]{36}/);
  return new URL(student.url()).pathname.split('/')[2];
}

async function reviewSubmission(page: Page, decision: string, note: string) {
  await page.getByRole('button', { name: 'Xem tệp & nhận xét', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Kết quả', { exact: true }).selectOption(decision);
  await dialog.getByLabel('Nhận xét tổng quát', { exact: true }).fill(note);
  await dialog.getByRole('button', { name: 'Hoàn thành và gửi góp ý', exact: true }).click();
  await expect(dialog).toHaveCount(0);
}

export async function submitDocuments(thesis: string, chair: Page, student: Page, advisor: Page, deadlineValue: string) {
  const root = `/theses/${thesis}?section=submissions&kind=`;
  const documents = [
    { kind: 'PLAN', input: /Tệp cần nộp/, submit: 'Nộp kế hoạch Mẫu 2', file: process.env.KLTN_E2E_PLAN_FILE!, decision: 'ACCEPT' },
    { kind: 'PROPOSAL', input: /Nộp đề cương PDF hoặc DOCX/, submit: 'Nộp đề cương', file: process.env.KLTN_E2E_PROPOSAL_FILE!, decision: 'CONFIRM' },
    { kind: 'REPORT', input: /Tệp cần nộp/, submit: 'Nộp cuốn báo cáo', file: process.env.KLTN_E2E_NV6_FILE!, decision: 'ACCEPT' },
  ];
  for (const form of documents) {
    const url = root + form.kind;
    await chair.goto(url);
    const deadline = chair.locator('section.card').filter({
      has: chair.getByRole('heading', {
        name: form.kind === 'PROPOSAL' ? 'Lịch nhận đề cương của đợt' : 'Lịch nhận tài liệu của đợt',
        exact: true,
      }),
    });
    await deadline.getByLabel('Hạn mới (giờ Việt Nam)', { exact: true }).fill(deadlineValue);
    await deadline.getByLabel('Căn cứ / lý do', { exact: true }).fill('Mở nhận tài liệu cho đợt kiểm thử.');
    await deadline.getByRole('button', { name: /^(Thiết lập cho cả đợt|Gia hạn cho cả đợt|Gia hạn và mở nhận lại cả đợt)$/ }).click();
    await expect(chair.getByRole('status').filter({ hasText: /Đã (thiết lập hạn|gia hạn loại) tài liệu/ })).toBeVisible();
    await student.goto(url);
    await student.getByLabel(form.input).setInputFiles(form.file);
    await student.getByRole('button', { name: form.submit, exact: true }).click();
    await expect(student.getByRole('button', { name: 'Tải bản nộp gốc v1', exact: true })).toBeEnabled({ timeout: 60000 });
    await advisor.goto(url);
    await reviewSubmission(advisor, form.decision, 'GVHD đã đối chiếu đúng phiên bản nộp.');
    if (form.kind === 'PROPOSAL') {
      await chair.goto(url);
      const decision = chair.locator('section.card, div.card').filter({
        has: chair.getByRole('heading', { name: 'Trưởng bộ môn chốt đề cương', exact: true }),
      });
      await decision.getByLabel('Kết quả', { exact: true }).selectOption('FINALIZE');
      await decision.getByLabel('Nhận xét / lý do', { exact: true }).fill('TBM chốt phiên bản đề cương đã được GVHD xác nhận.');
      await decision.getByRole('button', { name: 'Gửi kết quả', exact: true }).click();
      await expect(chair.getByRole('status').filter({ hasText: 'Đã chốt đề cương.' })).toBeVisible();
    }
  }
}

export async function evaluateThesis(thesis: string, chair: Page, advisor: Page, reviewer: Page, reviewerId: string, memberId: string) {
  const url = `/evaluation/${thesis}`;
  await chair.goto(url);
  await chair.getByRole('button', { name: 'Phân công GV', exact: true }).click();
  const assignment = chair.getByRole('dialog');
  await assignment.getByLabel('Giảng viên phản biện', { exact: true }).selectOption(reviewerId);
  await assignment.getByLabel('Căn cứ / số văn bản đối chiếu').fill('E2E-QD-PHAN-BIEN');
  await assignment.getByLabel('Lý do / ghi chú nghiệp vụ').fill('Giao phản biện theo chuyên môn đã đối chiếu');
  await assignment.getByRole('button', { name: 'Xác nhận và lưu', exact: true }).click();
  await expect(assignment).toHaveCount(0);
  await reviewer.goto('/notifications');
  await reviewer.getByRole('button', { name: /Bạn được giao phản biện khóa luận/ }).click();
  await expect(reviewer).toHaveURL(new RegExp(url + '$'));
  await advisor.goto(url);
  for (const [page, type, fields] of [
    [advisor, 7, ['1. Tinh thần, thái độ của sinh viên', '2. Sự đáp ứng của nội dung khóa luận', '3. Hình thức khóa luận']],
    [reviewer, 8, ['1. Hình thức trình bày, kết cấu, bố cục', '2. Tính cấp thiết, tổng quan', '4. Kết quả và đóng góp mới về khoa học', '5. Những điểm cần trao đổi với tác giả', '6. Đánh giá chung']],
  ] as const) {
    await page.getByLabel('Sinh viên trong hồ sơ').selectOption(memberId);
    await page.getByRole('button', { name: `Lập phiếu Mẫu ${type}`, exact: true }).click();
    const dialog = page.getByRole('dialog');
    const reason = 'Đối chiếu bản báo cáo và ghi nhận ý kiến phản biện.';
    if (type === 8) await dialog.getByLabel(/Lý do lập phiếu/).fill(reason);
    await dialog.getByRole('button', { name: 'Tạo phiếu nháp', exact: true }).click();
    if (type === 8) {
      await expect(dialog.getByRole('alert')).toBeVisible();
      await dialog.getByRole('button', { name: 'Tải lại hồ sơ', exact: true }).click();
      await expect(dialog.getByRole('status')).toContainText('Đã tải lại hồ sơ');
      await expect(dialog.getByLabel(/Lý do lập phiếu/)).toHaveValue(reason);
      await dialog.getByRole('button', { name: 'Tạo phiếu nháp', exact: true }).click();
    }
    for (const field of fields) await dialog.getByLabel(field, { exact: false }).fill('Đã đối chiếu nội dung khóa luận trên bản báo cáo hiện hành.');
    if (type === 7) {
      await dialog.getByLabel('Xác nhận hoàn thành khóa luận', { exact: true }).selectOption('true');
      await dialog.getByLabel('Đề nghị của GVHD', { exact: true }).selectOption('true');
    }
    await dialog.getByRole('button', { name: 'Lưu nháp', exact: true }).click();
    await expect(dialog.getByRole('button', { name: 'Lưu nháp', exact: true })).toBeDisabled();
    await dialog.getByRole('button', { name: 'Kiểm tra và gửi nhận xét', exact: true }).click();
    await dialog.getByRole('checkbox', { name: /Tôi xác nhận nội dung nhận xét này/ }).check();
    await dialog.getByRole('button', { name: 'Xác nhận gửi nhận xét', exact: true }).click();
    await expect(dialog).toHaveCount(0);
  }
  await chair.goto(url);
  await chair.getByLabel('Sinh viên trong hồ sơ').selectOption(memberId);
  await chair.getByRole('button', { name: 'Xét và lưu điều kiện', exact: true }).click();
  const dialog = chair.getByRole('dialog');
  await dialog.getByLabel('Tình trạng kỷ luật theo nguồn đã đối chiếu').selectOption('CLEAR');
  await dialog.getByLabel('Căn cứ / số văn bản đối chiếu').fill('E2E-QD-DU-DIEU-KIEN');
  await dialog.getByLabel('Lý do / ghi chú nghiệp vụ').fill('Đã đối chiếu báo cáo, tình trạng kỷ luật và đề nghị của GVHD.');
  await expect(dialog.getByText('Dự kiến: đủ điều kiện dự bảo vệ', { exact: true })).toBeVisible();
  await dialog.getByRole('button', { name: 'Xác nhận và lưu', exact: true }).click();
  await expect(dialog).toHaveCount(0);
}
