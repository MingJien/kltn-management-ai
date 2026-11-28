import {test,expect,type Browser,type Page} from '@playwright/test';

const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON||'{}');
const firstId=process.env.KLTN_E2E_DEFENSE_THESIS!;
const secondId=process.env.KLTN_E2E_DEFENSE_SECOND_THESIS!;
const api=`http://127.0.0.1:${process.env.KLTN_E2E_API_PORT}/api/v1`;
const title1='Hội đồng kiểm thử thực tế';
const title2='Đề tài kiểm thử xếp lịch thứ hai';
const localDate=(date:Date)=>new Date(date.getTime()+7*3600000).toISOString().slice(0,16);

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
async function get(page:Page,path:string) {
  const response=await page.request.get(api+path);
  expect(response.status(),await response.text()).toBe(200);
  return response.json();
}

test('Xếp hai đề tài cùng hội đồng và công bố danh sách bằng UI/API thật',async({browser})=>{
  test.setTimeout(180000);
  const chair=await login(browser,'tbm');
  const secretary=await login(browser,'gv2');
  const reviewer=await login(browser,'council1');
  const student1=await login(browser,'sv1');
  const student2=await login(browser,'sv2');
  const actors=[chair,secretary,reviewer,student1,student2];
  try {
    await chair.page.goto('/defense');
    await chair.page.getByRole('button',{name:'Lập hội đồng mới',exact:true}).click();
    const dialog=chair.page.getByRole('dialog');
    const data=await get(chair.page,'/defense');
    const plan=data.planning_theses.find((r:any)=>r.id===firstId);
    expect(data.planning_theses.some((r:any)=>r.id===secondId)).toBe(true);
    await dialog.locator('select[name="round"]').selectOption(plan.round_id);
    const scope=data.scopes.findIndex((r:any)=>r.round_id===plan.round_id&&r.department_id===plan.department_id);
    expect(scope).toBeGreaterThanOrEqual(0);
    await dialog.locator('select[name="scope"]').selectOption(String(scope));
    for(const [title,id] of [[title1,firstId],[title2,secondId]]) {
      await dialog.getByLabel('Tìm đề tài').fill(title);
      await dialog.getByLabel('Thêm đề tài').selectOption(id);
    }
    await expect(dialog.getByText('Xem đề tài đã chọn (2)',{exact:true})).toBeVisible();
    await dialog.getByLabel('Tên hội đồng',{exact:true}).fill('Hội đồng hai đề tài E2E');
    await dialog.getByLabel('Số quyết định hoặc căn cứ phân công').fill('E2E-QD-HAI-DE-TAI');
    const people=[(await get(chair.page,'/me/context')).lecturer_id,(await get(secretary.page,'/me/context')).lecturer_id,
      (await get(reviewer.page,'/me/context')).lecturer_id,data.candidates.find((r:any)=>r.code==='E2E-HD-2').id,
      data.candidates.find((r:any)=>r.code==='E2E-HD-3').id];
    for(const [i,id] of people.entries())await dialog.locator(`select[name="lecturer${i}"]`).selectOption(id);
    await dialog.getByRole('checkbox',{name:/Đã đối chiếu thành viên không có quan hệ thân nhân/}).check();
    await dialog.getByRole('button',{name:'Tạo hội đồng',exact:true}).click();
    await expect(dialog).toHaveCount(0);
    const council=(await get(chair.page,'/defense')).councils.find((r:any)=>r.name==='Hội đồng hai đề tài E2E');
    expect(council).toBeTruthy();
    await chair.page.getByRole('button',{name:'Xếp lịch bảo vệ',exact:true}).click();
    const schedule=chair.page.getByRole('dialog');
    await schedule.getByRole('combobox',{name:'Hội đồng',exact:true}).selectOption(council.id);
    await schedule.getByRole('button',{name:'Chọn tất cả',exact:true}).click();
    const start=new Date(Date.now()+24*60*60000);
    await schedule.getByLabel('Bắt đầu (giờ Việt Nam)',{exact:true}).fill(localDate(start));
    await schedule.getByLabel(/Giờ tập trung chung/).fill(localDate(new Date(start.getTime()-30*60000)));
    await schedule.getByLabel('Phòng bảo vệ',{exact:true}).fill('E2E-H2-101');
    await schedule.getByRole('checkbox',{name:/Đã đối chiếu/}).check();
    await schedule.getByRole('button',{name:'Lưu lịch cho 2 đề tài',exact:true}).click();
    await expect(schedule).toHaveCount(0);
    const slots=(await get(chair.page,'/defense')).slots.filter((r:any)=>r.council.id===council.id)
      .sort((a:any,b:any)=>Date.parse(a.starts_at)-Date.parse(b.starts_at));
    expect(slots).toHaveLength(2);
    expect(new Set(slots.map((s:any)=>s.thesis_id))).toEqual(new Set([firstId,secondId]));
    expect(Date.parse(slots[1].starts_at)-Date.parse(slots[0].ends_at)).toBe(5*60000);
    expect(slots[0].arrival_at).toBe(slots[1].arrival_at);
    expect(slots.every((s:any)=>s.room==='E2E-H2-101')).toBe(true);
    await chair.page.getByRole('button',{name:/^Hội đồng(?:\s|$)/}).click();
    await chair.page.getByText('Công bố danh sách bảo vệ cho sinh viên',{exact:true}).click();
    await chair.page.getByRole('button',{name:'Xem trước danh sách cần công bố',exact:true}).click();
    await expect(chair.page.getByRole('table').filter({hasText:title1}).filter({hasText:title2})).toBeVisible();
    await chair.page.getByRole('button',{name:'Công bố và thông báo danh sách',exact:true}).click();
    await chair.page.getByRole('dialog').getByRole('button',{name:'Công bố và gửi',exact:true}).click();
    await expect.poll(async()=> (await get(student1.page,'/defense/schedule-notices')).length).toBeGreaterThan(0);
    for(const actor of [student1,student2]) {
      await actor.page.goto('/defense?section=announcements');
      await expect(actor.page.getByRole('heading',{name:'Danh sách bảo vệ đã công bố',exact:true})).toBeVisible();
      await actor.page.getByText(/Hội đồng hai đề tài E2E.*Bản 1/).click();
      await expect(actor.page.getByRole('table').filter({hasText:title1}).filter({hasText:title2})).toBeVisible();
      const notices=await get(actor.page,'/notifications?limit=100');
      expect(notices.items.some((n:any)=>n.message.includes('công bố')&&n.message.includes('Hội đồng hai đề tài E2E'))).toBe(true);
    }
  } finally { for(const actor of actors)await actor.context.close(); }
});
