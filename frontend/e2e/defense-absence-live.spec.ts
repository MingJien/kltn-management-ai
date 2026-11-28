import {test,expect,type Browser,type Page} from '@playwright/test';

const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON||'{}');
const thesis=process.env.KLTN_E2E_DEFENSE_THESIS!;
const api=`http://127.0.0.1:${process.env.KLTN_E2E_API_PORT}/api/v1`;
const title='Hội đồng kiểm thử thực tế';

async function login(browser:Browser,key:string) {
  const context=await browser.newContext();
  const page=await context.newPage();
  page.setDefaultTimeout(15000);
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
async function context(page:Page) {return (await page.request.get(api+'/me/context')).json();}
const localDate=(date:Date)=>new Date(date.getTime()+7*3600000).toISOString().slice(0,16);
const studentCard=(page:Page,row:any)=>page.getByRole('heading',{
  name:`${row.name} · ${row.code}`,exact:true}).locator('..').locator('..');

test('Nhóm hai SV: một người vắng, Khoa cho bảo vệ bổ sung và giữ điểm người đã bảo vệ',async({browser})=>{
  test.setTimeout(240000);
  const chair=await login(browser,'tbm');
  const secretary=await login(browser,'gv2');
  const reviewer=await login(browser,'council1');
  const student1=await login(browser,'sv1');
  const student2=await login(browser,'sv2');
  const actors=[chair,secretary,reviewer,student1,student2];
  const readSlot=async(page:Page,id:string)=>(await workspace(page)).slots.find((s:any)=>s.id===id);
  try {
    await chair.page.goto('/defense');
    await chair.page.getByRole('button',{name:'Lập hội đồng mới',exact:true}).click();
    const dialog=chair.page.getByRole('dialog');
    const data=await workspace(chair.page);
    const plan=data.planning_theses.find((row:any)=>row.id===thesis);
    expect(plan).toBeTruthy();
    await dialog.locator('select[name="round"]').selectOption(plan.round_id);
    const scope=data.scopes.findIndex((row:any)=>row.round_id===plan.round_id&&row.department_id===plan.department_id);
    await dialog.locator('select[name="scope"]').selectOption(String(scope));
    await dialog.getByLabel('Tìm đề tài').fill(title);
    await dialog.getByLabel('Thêm đề tài').selectOption(thesis);
    await dialog.getByLabel('Tên hội đồng',{exact:true}).fill('Hội đồng kiểm thử vắng bảo vệ');
    await dialog.getByLabel('Số quyết định hoặc căn cứ phân công').fill('E2E-QD-VANG');
    const people=[(await context(chair.page)).lecturer_id,(await context(secretary.page)).lecturer_id,
      (await context(reviewer.page)).lecturer_id,data.candidates.find((r:any)=>r.code==='E2E-HD-2').id,
      data.candidates.find((r:any)=>r.code==='E2E-HD-3').id];
    for(const [i,id] of people.entries())await dialog.locator(`select[name="lecturer${i}"]`).selectOption(id);
    await dialog.getByRole('checkbox',{name:/Đã đối chiếu thành viên không có quan hệ thân nhân/}).check();
    await dialog.getByRole('button',{name:'Tạo hội đồng',exact:true}).click();
    await expect(dialog).toHaveCount(0);
    const council=(await workspace(chair.page)).councils.find((c:any)=>c.name==='Hội đồng kiểm thử vắng bảo vệ');
    expect(council).toBeTruthy();
    await chair.page.getByRole('button',{name:'Xếp lịch bảo vệ',exact:true}).click();
    const batch=chair.page.getByRole('dialog');
    await batch.locator('.defense-schedule-form select').first().selectOption(council.id);
    await batch.getByRole('checkbox',{name:title,exact:true}).check();
    await batch.getByRole('checkbox',{name:/Đã đối chiếu không có quan hệ thân nhân/}).check();
    await batch.getByLabel('Bắt đầu (giờ Việt Nam)').fill(localDate(new Date(Date.now()-120*60000)));
    await batch.getByRole('checkbox',{name:/Áp dụng cùng giờ tập trung/}).uncheck();
    await batch.getByLabel('Phòng bảo vệ').fill('E2E-VANG-101');
    await batch.getByRole('button',{name:'Lưu lịch cho 1 đề tài',exact:true}).click();
    await expect(batch).toHaveCount(0);
    const original=(await workspace(chair.page)).slots.find((s:any)=>s.thesis_id===thesis);
    expect(original.roster).toHaveLength(2);
    const firstId=(await context(student1.page)).student_id;
    const secondId=(await context(student2.page)).student_id;
    const first=original.roster.find((r:any)=>r.student_id===firstId);
    const second=original.roster.find((r:any)=>r.student_id===secondId);
    expect(first).toBeTruthy(); expect(second).toBeTruthy();
    const firstUrl=`/defense?slot=${original.id}`;

    await secretary.page.goto(firstUrl);
    await secretary.page.getByRole('button',{name:'Điểm danh',exact:true}).click();
    for(const label of [/Chủ tịch/,/Thư ký/,/Phản biện Hội đồng.*GV Hội đồng 1/])
      await secretary.page.getByRole('checkbox',{name:label}).check();
    await secretary.page.getByLabel('Ghi nhận thành phần dự họp').fill('Ba giảng viên có mặt theo danh sách.');
    await secretary.page.getByRole('button',{name:'Lưu thành phần dự họp'}).click();
    await expect.poll(async()=> (await readSlot(secretary.page,original.id)).council_attendance?.present_ids?.length??0).toBe(3);
    await studentCard(secretary.page,first).getByRole('button',{name:'Lưu điểm danh',exact:true}).click();
    await expect.poll(async()=> (await readSlot(secretary.page,original.id)).results[first.id]?.attendance.status).toBe('PRESENT');
    await expect(studentCard(secretary.page,second).getByRole('combobox',{name:/Điểm danh/})).toBeVisible();
    await studentCard(secretary.page,second).locator('select[name="status"]').selectOption('ABSENT');
    await studentCard(secretary.page,second).locator('input[name="reason"]').fill('Có lý do, chờ Khoa xem xét.');
    await studentCard(secretary.page,second).getByRole('button',{name:'Lưu điểm danh',exact:true}).click();
    await expect.poll(async()=> (await readSlot(secretary.page,original.id)).results[second.id]?.attendance.status).toBe('ABSENT');

    const scores=['1','0.5','0.5','0.5','0.5','1','1','0.5','0.5','1','1','1'];
    async function markAndFinalize(slotId:string, student:any) {
      const url=`/defense?slot=${slotId}`;
      for(const actor of [chair,secretary,reviewer]) {
        await actor.page.goto(url);
        await actor.page.getByRole('button',{name:'Phiếu chấm',exact:true}).click();
        const card=studentCard(actor.page,student);
        await card.getByText(/Phiếu chấm Mẫu 6 · Điểm thưởng/).click();
        const fields=card.locator('form.defense-ballot input[type=number]');
        await expect(fields).toHaveCount(12);
        for(let i=0;i<scores.length;i++)await fields.nth(i).fill(scores[i]);
        await card.getByLabel('Nhận xét',{exact:true}).fill('Đánh giá theo phần bảo vệ của từng sinh viên.');
        await card.getByRole('button',{name:'Lưu phiếu chấm',exact:true}).click();
        const lecturerId=(await context(actor.page)).lecturer_id;
        await expect.poll(async()=> (await readSlot(actor.page,slotId)).marks?.[student.id]?.[lecturerId]?.scores?.length??0).toBe(12);
      }
      await secretary.page.goto(url);
      await secretary.page.getByRole('button',{name:'Biên bản',exact:true}).click();
      for(const label of ['Mục tiêu','Chức năng','Kết quả đạt được','Nội dung trao đổi và trả lời câu hỏi','Kết luận của Chủ tịch hội đồng'])
        await secretary.page.getByRole('textbox',{name:label,exact:true}).fill('Nội dung cuộc họp bảo vệ đã được ghi nhận.');
      await secretary.page.getByRole('checkbox',{name:'Hội đồng xác nhận không có kiến nghị'}).check();
      await secretary.page.getByLabel(/Xếp loại được hội đồng xác nhận/).selectOption('Giỏi');
      await secretary.page.getByRole('button',{name:'Lưu biên bản',exact:true}).click();
      await secretary.page.getByRole('button',{name:'Kết quả & xuất',exact:true}).click();
      await expect(secretary.page.getByRole('button',{name:'Chốt kết quả bảo vệ'})).toBeEnabled();
      await secretary.page.getByRole('button',{name:'Chốt kết quả bảo vệ'}).click();
      await secretary.page.getByRole('dialog').getByRole('button',{name:'Chốt kết quả',exact:true}).click();
      await expect.poll(async()=> (await readSlot(secretary.page,slotId)).finalized_at).toBeTruthy();
    }
    await markAndFinalize(original.id,first);
    const firstResult=(await readSlot(chair.page,original.id)).results;
    expect(firstResult[first.id].average).toBe('9.0');
    expect(firstResult[second.id].average).toBeNull();

    await chair.page.goto(firstUrl);
    await chair.page.getByRole('button',{name:'Kết quả & xuất',exact:true}).click();
    await expect(chair.page.getByText(/Chờ Khoa ghi nhận quyết định/)).toBeVisible();
    await chair.page.getByRole('combobox',{name:'Quyết định của Khoa',exact:true}).selectOption('SUPPLEMENTARY');
    await chair.page.getByLabel('Số / căn cứ quyết định',{exact:true}).fill('QD-E2E-BO-SUNG');
    await chair.page.getByLabel('Lý do',{exact:true}).fill('Khoa xem xét và cho phép bảo vệ bổ sung.');
    await chair.page.getByRole('button',{name:'Ghi nhận quyết định của Khoa',exact:true}).click();
    await expect.poll(async()=> (await readSlot(chair.page,original.id)).absence_decisions?.[second.id]?.outcome).toBe('SUPPLEMENTARY');
    await chair.page.getByText('Xếp lịch bảo vệ bổ sung theo quyết định',{exact:true}).click();
    const supplementary=chair.page.locator('form').filter({has:chair.page.getByRole('group',{name:'Sinh viên được Khoa cho bảo vệ bổ sung'})});
    await supplementary.getByRole('combobox',{name:'Hội đồng',exact:true}).selectOption(council.id);
    await supplementary.getByLabel(`${second.name} · ${second.code}`,{exact:true}).check();
    await supplementary.getByLabel('Bắt đầu (giờ Việt Nam)',{exact:true}).fill(localDate(new Date(Date.now()-15*60000)));
    await supplementary.getByLabel('Kết thúc (giờ Việt Nam)',{exact:true}).fill(localDate(new Date(Date.now()+30*60000)));
    await supplementary.getByLabel('Phòng bảo vệ',{exact:true}).fill('E2E-VANG-202');
    await supplementary.getByLabel(/Đã đối chiếu thành viên hội đồng không có quan hệ thân nhân/).check();
    await supplementary.getByRole('button',{name:'Lưu lịch',exact:true}).click();
    await expect.poll(async()=> (await workspace(chair.page)).slots.filter((s:any)=>s.prior_slot_id===original.id).length).toBe(1);
    const next=(await workspace(chair.page)).slots.find((s:any)=>s.prior_slot_id===original.id);
    expect(next.roster.map((r:any)=>r.id)).toEqual([second.id]);

    await secretary.page.goto(`/defense?slot=${next.id}`);
    await secretary.page.getByRole('button',{name:'Điểm danh',exact:true}).click();
    for(const label of [/Chủ tịch/,/Thư ký/,/Phản biện Hội đồng.*GV Hội đồng 1/])
      await secretary.page.getByRole('checkbox',{name:label}).check();
    await secretary.page.getByLabel('Ghi nhận thành phần dự họp').fill('Ba giảng viên có mặt trong phiên bổ sung.');
    await secretary.page.getByRole('button',{name:'Lưu thành phần dự họp'}).click();
    await expect.poll(async()=> (await readSlot(secretary.page,next.id)).council_attendance?.present_ids?.length??0).toBe(3);
    await studentCard(secretary.page,second).getByRole('button',{name:'Lưu điểm danh',exact:true}).click();
    await expect.poll(async()=> (await readSlot(secretary.page,next.id)).results[second.id]?.attendance.status).toBe('PRESENT');
    await markAndFinalize(next.id,second);
    expect((await readSlot(chair.page,original.id)).results[first.id].average).toBe(firstResult[first.id].average);
    expect((await readSlot(chair.page,next.id)).results[second.id].average).toBe('9.0');
    expect((await readSlot(student1.page,original.id)).results[second.id]).toBeUndefined();
    expect((await readSlot(student2.page,next.id)).results[first.id]).toBeUndefined();
  } finally { for(const actor of actors)await actor.context.close(); }
});
