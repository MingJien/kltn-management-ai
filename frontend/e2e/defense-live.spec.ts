import {test, expect, type Browser, type Page} from '@playwright/test';
import {execFileSync} from 'node:child_process';

const accounts = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || '{}');
const thesis = process.env.KLTN_E2E_DEFENSE_THESIS!;
const api = `http://127.0.0.1:${process.env.KLTN_E2E_API_PORT}/api/v1`;

async function login(browser:Browser, key:string) {
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(12000);
  await page.goto('/');
  await page.getByLabel('Email',{exact:true}).fill(accounts[key].email);
  await page.getByLabel('Mật khẩu',{exact:true}).fill(accounts[key].password);
  await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Tổng quan',exact:true})).toBeVisible();
  return {context,page};
}
async function workspace(page:Page) {
  const response=await page.request.get(api+'/defense');
  expect(response.status(),await response.text()).toBe(200);
  return response.json();
}
function localDate(date:Date) { return new Date(date.getTime()+7*3600000).toISOString().slice(0,16); }

test('Hội đồng thật: lập, xếp lịch, điểm danh, chấm, chốt, khóa và nộp lưu', async ({browser})=>{
  test.setTimeout(240000);
  const chair=await login(browser,'tbm');
  const secretary=await login(browser,'gv2');
  const reviewer=await login(browser,'council1');
  const student=await login(browser,'sv1');
  const advisor=await login(browser,'gv');
  const pages=[chair,secretary,reviewer,student,advisor];
  const title='Hội đồng kiểm thử thực tế';
  try {
    const submissions=`/theses/${thesis}?section=submissions&kind=SUPPORTING`;
    const claims=(page:Page)=>page.locator('section.card').filter({has:page.getByRole('heading',{name:'Minh chứng công bố khoa học · Xét điểm thưởng',exact:true})});
    await chair.page.goto(submissions);
    const deadline=chair.page.locator('section.card').filter({has:chair.page.getByRole('heading',{name:'Lịch nhận tài liệu của đợt',exact:true})});
    await deadline.getByLabel('Hạn mới (giờ Việt Nam)',{exact:true}).fill(localDate(new Date(Date.now()+90*86400000)));
    await deadline.getByLabel('Căn cứ / lý do',{exact:true}).fill('Mở nhận minh chứng cho kiểm thử tích hợp.');
    await deadline.getByRole('button',{name:/^(Thiết lập cho cả đợt|Gia hạn cho cả đợt|Gia hạn và mở nhận lại cả đợt)$/}).click();
    await expect(chair.page.getByRole('status').filter({hasText:/Đã (thiết lập hạn|gia hạn loại) tài liệu cho toàn đợt/})).toBeVisible();
    await student.page.goto(submissions);
    await claims(student.page).getByText('Nộp hồ sơ xét điểm thưởng',{exact:true}).click();
    await claims(student.page).getByLabel('Tên công bố',{exact:true}).fill('Công bố khoa học của hồ sơ kiểm thử');
    await claims(student.page).getByLabel('Tạp chí / hội nghị / đơn vị công bố').fill('Hội nghị kiểm thử');
    await claims(student.page).getByLabel('Thông tin công bố (ngày, số, DOI hoặc đường dẫn)').fill('DOI: synthetic-live-bonus');
    await claims(student.page).getByLabel('Liên quan đến khóa luận và đóng góp cụ thể của từng SV').fill('Sinh viên thực hiện nghiên cứu và tổng hợp kết quả đề tài.');
    await claims(student.page).getByRole('checkbox').check();
    await claims(student.page).getByLabel(/Tải minh chứng mới/).setInputFiles(process.env.KLTN_E2E_NV6_FILE!);
    await claims(student.page).getByRole('button',{name:'Gửi GVHD kiểm tra',exact:true}).click();
    await expect(claims(student.page).getByText('Đã gửi · Chờ GVHD',{exact:true}).first()).toBeVisible({timeout:60000});
    await advisor.page.goto(submissions);
    await claims(advisor.page).getByLabel('Nhận xét kiểm tra công bố và đóng góp').fill('Công bố liên quan đề tài và sinh viên có đóng góp.');
    await claims(advisor.page).getByRole('button',{name:'Lưu kết quả GVHD',exact:true}).click();
    await expect(claims(advisor.page).getByText('GVHD xác nhận · Chờ TBM',{exact:true}).first()).toBeVisible();
    await chair.page.goto(submissions);
    await claims(chair.page).getByLabel(/Mức thưởng ·/).fill('1');
    await claims(chair.page).getByLabel('Căn cứ xét duyệt và giải thích mức thưởng').fill('Đã đối chiếu công bố và duyệt 1 điểm cho sinh viên.');
    await claims(chair.page).getByRole('button',{name:'Lưu kết quả TBM',exact:true}).click();
    await expect(claims(chair.page).getByText(/Được duyệt 1 \/ 1 điểm/)).toBeVisible();
    console.log('Hội đồng live: đã duyệt điểm thưởng 1');
    console.log('Hội đồng live: mở biểu mẫu');
    await chair.page.goto('/defense');
    await chair.page.getByRole('button',{name:'Lập hội đồng mới',exact:true}).click();
    const dialog=chair.page.getByRole('dialog');
    const data=await workspace(chair.page);
    const plan=data.planning_theses.find((row:any)=>row.id===thesis);
    expect(plan).toBeTruthy();
    await dialog.locator('select[name="round"]').selectOption(plan.round_id);
    const scope=data.scopes.findIndex((row:any)=>row.round_id===plan.round_id && row.department_id===plan.department_id);
    expect(scope).toBeGreaterThanOrEqual(0);
    await dialog.locator('select[name="scope"]').selectOption(String(scope));
    await dialog.getByLabel('Tìm đề tài').fill(title);
    await dialog.getByLabel('Thêm đề tài').selectOption(thesis);
    await dialog.getByLabel('Tên hội đồng',{exact:true}).fill('Hội đồng E2E thực tế');
    await dialog.getByLabel('Số quyết định hoặc căn cứ phân công').fill('E2E-QD-001');
    const head=await (await chair.page.request.get(api+'/me/context')).json();
    const sec=await (await secretary.page.request.get(api+'/me/context')).json();
    const review=await (await reviewer.page.request.get(api+'/me/context')).json();
    const extra2=data.candidates.find((row:any)=>row.code==='E2E-HD-2');
    const extra3=data.candidates.find((row:any)=>row.code==='E2E-HD-3');
    for(const [index,person] of [head.lecturer_id,sec.lecturer_id,review.lecturer_id,extra2.id,extra3.id].entries())
      await dialog.locator(`select[name="lecturer${index}"]`).selectOption(person);
    await dialog.getByRole('checkbox',{name:/Đã đối chiếu thành viên không có quan hệ thân nhân/}).check();
    await dialog.getByRole('button',{name:'Tạo hội đồng',exact:true}).click();
    await expect(dialog).toHaveCount(0);
    console.log('Hội đồng live: đã tạo hội đồng');
    let state=await workspace(chair.page);
    const council=state.councils.find((row:any)=>row.name==='Hội đồng E2E thực tế');
    expect(council).toBeTruthy();

    await chair.page.getByRole('button',{name:'Xếp lịch bảo vệ',exact:true}).click();
    const schedule=chair.page.getByRole('dialog');
    await schedule.locator('.defense-schedule-form select').first().selectOption(council.id);
    await schedule.getByRole('checkbox',{name:title,exact:true}).check();
    await schedule.getByRole('checkbox',{name:/Đã đối chiếu không có quan hệ thân nhân/}).check();
    await schedule.getByLabel('Bắt đầu (giờ Việt Nam)').fill(localDate(new Date(Date.now()-5*60000)));
    await schedule.getByRole('checkbox',{name:/Áp dụng cùng giờ tập trung/}).uncheck();
    await schedule.getByLabel('Phòng bảo vệ').fill('E2E-101');
    await schedule.getByRole('button',{name:'Lưu lịch cho 1 đề tài',exact:true}).click();
    await expect(schedule).toHaveCount(0);
    console.log('Hội đồng live: đã xếp lịch');
    state=await workspace(chair.page);
    const slot=state.slots.find((row:any)=>row.thesis_id===thesis);
    expect(slot).toBeTruthy();
    const sessionUrl=`/defense?slot=${slot.id}`;

    await chair.page.goto(sessionUrl);
    await chair.page.getByText('Đổi đề tài, giờ, phòng hoặc hủy lịch',{exact:true}).click();
    const editSchedule=chair.page.locator('.defense-schedule-form');
    await expect(editSchedule.getByRole('combobox',{name:'Đề tài đủ điều kiện',exact:true})).toHaveValue(thesis);
    await editSchedule.getByLabel('Phòng bảo vệ',{exact:true}).fill('E2E-202');
    await editSchedule.getByRole('button',{name:'Lưu thay đổi lịch',exact:true}).click();
    await expect.poll(async()=> (await workspace(chair.page)).slots.find((s:any)=>s.id===slot.id)?.room).toBe('E2E-202');
    for(const actor of [student,advisor,reviewer]) {
      const notices=await (await actor.page.request.get(api+'/notifications?limit=100')).json();
      expect(notices.items.some((n:any)=>n.message.includes('Lịch bảo vệ đã thay đổi')&&n.message.includes('E2E-202'))).toBe(true);
    }

    await secretary.page.goto(sessionUrl);
    await secretary.page.getByRole('button',{name:'Điểm danh',exact:true}).click();
    await secretary.page.getByRole('checkbox',{name:/Chủ tịch/}).check();
    await secretary.page.getByRole('checkbox',{name:/Thư ký/}).check();
    await secretary.page.getByRole('checkbox',{name:/Phản biện Hội đồng.*GV Hội đồng 1/}).check();
    await secretary.page.getByLabel('Ghi nhận thành phần dự họp').fill('Ba thành viên có mặt theo danh sách');
    await secretary.page.getByRole('button',{name:'Lưu thành phần dự họp'}).click();
    await expect.poll(async()=> (await workspace(secretary.page)).slots.find((s:any)=>s.id===slot.id)?.council_attendance?.present_ids?.length ?? 0).toBe(3);
    await secretary.page.getByRole('button',{name:'Lưu điểm danh',exact:true}).click();
    await expect.poll(async()=> (await workspace(secretary.page)).slots.find((s:any)=>s.id===slot.id).results[slot.roster[0].id]?.attendance?.status).toBe('PRESENT');
    await chair.page.goto(sessionUrl);
    await chair.page.getByRole('button',{name:'Điểm danh',exact:true}).click();
    await expect(chair.page.getByText(/Điểm thưởng đã được TBM duyệt: 1(?:\.0+)? \/ 1/)).toBeVisible();
    await chair.page.getByRole('button',{name:'Đã đối chiếu mức thưởng của TBM'}).click();
    await expect.poll(async()=> (await workspace(chair.page)).slots.find((s:any)=>s.id===slot.id).results[slot.roster[0].id]?.attendance?.bonus_confirmed_by).toBeTruthy();
    console.log('Hội đồng live: đã điểm danh');

    const scores=['1','0.5','0.5','0.5','0.5','1','1','0.5','0.5','1','1','1'];
    const expected=Math.min(10,scores.reduce((a,b)=>a+Number(b),0)+1).toFixed(1);
    for (const actor of [chair,secretary,reviewer]) {
      await actor.page.goto(sessionUrl);
      await actor.page.getByRole('button',{name:'Phiếu chấm',exact:true}).click();
      await expect(actor.page.getByText(/Phiếu chấm Mẫu 6 · Điểm thưởng 1(?:\.0+)?/)).toBeVisible();
      await actor.page.getByText(/Phiếu chấm Mẫu 6 · Điểm thưởng/).click();
      const inputs=actor.page.locator('form.defense-ballot input[type=number]');
      await expect(inputs).toHaveCount(12);
      for(let i=0;i<scores.length;i++) await inputs.nth(i).fill(scores[i]);
      await actor.page.getByLabel('Nhận xét',{exact:true}).fill('Nội dung và sản phẩm đạt yêu cầu kiểm thử.');
      await actor.page.getByRole('button',{name:'Lưu phiếu chấm',exact:true}).click();
      await expect(actor.page.getByText(/Đã lưu/).first()).toBeVisible();
    }
    await secretary.page.goto(sessionUrl);
    await secretary.page.getByRole('button',{name:'Biên bản',exact:true}).click();
    for(const label of ['Mục tiêu','Chức năng','Kết quả đạt được','Nội dung trao đổi và trả lời câu hỏi','Kết luận của Chủ tịch hội đồng'])
      await secretary.page.getByRole('textbox',{name:label,exact:true}).fill('Nội dung cuộc họp kiểm thử đã được ghi nhận.');
    await secretary.page.getByRole('checkbox',{name:'Hội đồng xác nhận không có kiến nghị'}).check();
    await secretary.page.getByLabel(/Xếp loại được hội đồng xác nhận/).selectOption('Giỏi');
    await secretary.page.getByRole('button',{name:'Lưu biên bản',exact:true}).click();
    await secretary.page.getByRole('button',{name:'Kết quả & xuất',exact:true}).click();
    await expect(secretary.page.getByRole('button',{name:'Chốt kết quả bảo vệ'})).toBeEnabled();
    await secretary.page.getByRole('button',{name:'Chốt kết quả bảo vệ'}).click();
    await secretary.page.getByRole('dialog').getByRole('button',{name:'Chốt kết quả',exact:true}).click();
    await expect.poll(async()=> (await workspace(secretary.page)).slots.find((s:any)=>s.id===slot.id).finalized_at).toBeTruthy();
    await secretary.page.getByRole('button',{name:'Phiếu chấm',exact:true}).click();
    const form6=secretary.page.locator('details.defense-print').filter({hasText:'Mẫu 6 ·'}).first();
    await form6.locator('summary').click();
    await form6.getByRole('button',{name:'Áp dụng & xem trước'}).click();
    await expect(form6.getByRole('button',{name:'Lưu và tải bản dùng để ký'})).toBeEnabled({timeout:60000});
    const [scoreFile]=await Promise.all([secretary.page.waitForEvent('download'),form6.getByRole('button',{name:'Lưu và tải bản dùng để ký'}).click()]);
    expect(scoreFile.suggestedFilename()).toMatch(/\.xlsx$/i);
    const scorePath=test.info().outputPath('mau-6.xlsx');
    await scoreFile.saveAs(scorePath);
    await secretary.page.getByRole('button',{name:'Kết quả & xuất',exact:true}).click();
    const form9=secretary.page.locator('details.defense-print').filter({hasText:'Biên bản Mẫu 9'}).first();
    await form9.locator('summary').click();
    await form9.getByRole('button',{name:'Áp dụng & xem trước'}).click();
    await expect(form9.getByRole('button',{name:'Lưu và tải bản dùng để ký'})).toBeEnabled({timeout:60000});
    const [minutesFile]=await Promise.all([secretary.page.waitForEvent('download'),form9.getByRole('button',{name:'Lưu và tải bản dùng để ký'}).click()]);
    expect(minutesFile.suggestedFilename()).toMatch(/\.docx$/i);
    const minutesPath=test.info().outputPath('mau-9.docx');
    await minutesFile.saveAs(minutesPath);
    await chair.page.goto('/defense');
    await chair.page.getByRole('button',{name:/^Hội đồng(?:\s|$)/}).click();
    await chair.page.getByRole('button',{name:'Khóa bảng điểm hội đồng'}).click();
    await chair.page.getByRole('dialog').getByRole('button',{name:'Khóa bảng điểm',exact:true}).click();
    await expect.poll(async()=> (await workspace(chair.page)).councils.find((c:any)=>c.id===council.id).closed_at).toBeTruthy();
    console.log('Hội đồng live: đã khóa bảng điểm');
    const final=(await workspace(chair.page)).slots.find((s:any)=>s.id===slot.id);
    expect(final.results[slot.roster[0].id].average).toBe(expected);

    await chair.page.getByRole('button',{name:'Bảng điểm toàn đợt',exact:true}).click();
    await chair.page.getByText('Bảng điểm toàn đợt · Mẫu 10 và 11',{exact:true}).click();
    await chair.page.getByRole('combobox',{name:'Đợt bảo vệ'}).selectOption(plan.round_id);
    const form10=chair.page.locator('details.defense-print').filter({hasText:'Mẫu 10 · Bảng điểm tổng hợp'});
    await form10.locator('summary').click();
    await form10.getByRole('button',{name:'Áp dụng & xem trước'}).click();
    await expect(form10.getByRole('button',{name:'Lưu và tải bản dùng để ký'})).toBeEnabled({timeout:60000});
    const [registerFile]=await Promise.all([chair.page.waitForEvent('download'),form10.getByRole('button',{name:'Lưu và tải bản dùng để ký'}).click()]);
    expect(registerFile.suggestedFilename()).toMatch(/\.docx$/i);
    const registerPath=test.info().outputPath('mau-10.docx');
    await registerFile.saveAs(registerPath);
    await chair.page.getByRole('combobox',{name:'Mã học phần của bảng Mẫu 11'}).selectOption('IN4299N');
    const form11=chair.page.locator('details.defense-print').filter({hasText:'Mẫu 11 · IN4299N'});
    await form11.locator('summary').click();
    await form11.getByRole('button',{name:'Áp dụng & xem trước'}).click();
    await expect(form11.getByRole('button',{name:'Lưu và tải bản dùng để ký'})).toBeEnabled({timeout:60000});
    const [gradeFile]=await Promise.all([chair.page.waitForEvent('download'),form11.getByRole('button',{name:'Lưu và tải bản dùng để ký'}).click()]);
    expect(gradeFile.suggestedFilename()).toMatch(/\.xlsx$/i);
    const gradePath=test.info().outputPath('mau-11.xlsx');
    await gradeFile.saveAs(gradePath);
    const verify=`import sys
from docx import Document
from openpyxl import load_workbook
score,minutes,register,grade,student_code,expected=sys.argv[1:]
sheet=load_workbook(score,data_only=False).active
assert 'LOP-E2E' in str(sheet['A7'].value)
assert float(sheet['F29'].value)==float(expected)
def text(path):
 d=Document(path)
 return '\\n'.join([p.text for p in d.paragraphs]+[cell.text for table in d.tables for row in table.rows for cell in row.cells])
assert 'Nội dung cuộc họp kiểm thử' in text(minutes)
assert student_code in text(register) and 'LOP-E2E' in text(register)
rows=load_workbook(grade,data_only=False).active.iter_rows()
student_row=next(row for row in rows if str(row[1].value)==student_code)
assert float(student_row[5].value)==float(expected)
`;
    execFileSync(process.env.KLTN_E2E_PYTHON!,['-c',verify,scorePath,minutesPath,registerPath,gradePath,slot.roster[0].code,expected]);

    await secretary.page.goto(sessionUrl);
    await secretary.page.getByText('Đính chính hồ sơ sau khóa',{exact:true}).click();
    const secretaryCorrection=secretary.page.getByText('Đính chính hồ sơ sau khóa',{exact:true}).locator('..');
    const proposal=secretaryCorrection.locator('form').last();
    await expect(proposal.getByRole('button',{name:'Gửi đề nghị đính chính',exact:true})).toBeVisible();
    await proposal.locator('textarea[name="objectives"]').fill('Đính chính mục tiêu theo biên bản đã đối chiếu.');
    await proposal.getByLabel('Số văn bản / căn cứ đính chính',{exact:true}).fill('E2E-BB-DINH-CHINH');
    await proposal.getByLabel('Lý do đính chính',{exact:true}).fill('Bổ sung mục tiêu theo nội dung họp đã được đối chiếu.');
    await proposal.getByRole('button',{name:'Gửi đề nghị đính chính',exact:true}).click();
    await expect(secretaryCorrection.getByText('Chờ TBM duyệt · Biên bản',{exact:true})).toBeVisible();
    await expect(secretaryCorrection.locator('option[value="APPROVED"]')).toHaveCount(0);
    expect((await workspace(secretary.page)).slots.find((s:any)=>s.id===slot.id).minutes.objectives).not.toContain('Đính chính');
    await chair.page.goto(sessionUrl);
    await chair.page.getByText('Đính chính hồ sơ sau khóa',{exact:true}).click();
    const chairCorrection=chair.page.getByText('Đính chính hồ sơ sau khóa',{exact:true}).locator('..');
    await chairCorrection.getByRole('combobox',{name:'Quyết định',exact:true}).selectOption('APPROVED');
    await chairCorrection.getByLabel('Nhận xét quyết định',{exact:true}).fill('Đã đối chiếu nội dung với biên bản của hội đồng.');
    await chairCorrection.getByRole('button',{name:'Lưu quyết định đính chính',exact:true}).click();
    await expect.poll(async()=> (await workspace(chair.page)).slots.find((s:any)=>s.id===slot.id).minutes.objectives).toContain('Đính chính');
    expect((await workspace(chair.page)).slots.find((s:any)=>s.id===slot.id).results[slot.roster[0].id].average).toBe(expected);

    await student.page.goto(`/repository?focus=${thesis}`);
    await student.page.getByLabel(/Bản khóa luận hoàn thiện sau bảo vệ/).setInputFiles(process.env.KLTN_E2E_NV6_FILE!);
    await student.page.getByRole('button',{name:'Nộp bản hoàn thiện',exact:true}).click();
    await expect(student.page.getByText('Phiên bản 1 · Chờ bộ môn duyệt',{exact:true})).toBeVisible({timeout:60000});
    await chair.page.goto(`/repository?mode=work&focus=${thesis}`);
    await chair.page.getByRole('combobox',{name:'Kết quả kiểm tra',exact:true}).selectOption('ACCEPTED');
    await chair.page.getByLabel('Nhận xét và căn cứ',{exact:true}).fill('Đã kiểm tra đúng bản hoàn thiện thử nghiệm.');
    await chair.page.getByRole('button',{name:'Lưu quyết định',exact:true}).click();
    await expect(chair.page.getByText('Phiên bản 1 · Đã duyệt lưu',{exact:true})).toBeVisible();
  } finally { for(const actor of pages) await actor.context.close(); }
});
