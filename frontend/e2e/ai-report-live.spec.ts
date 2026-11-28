import {test,expect,type Browser} from '@playwright/test';

const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON||'{}');

async function login(browser:Browser,key:string) {
  const context=await browser.newContext();
  const page=await context.newPage();
  await page.goto('/');
  await page.getByLabel('Email',{exact:true}).fill(accounts[key].email);
  await page.getByLabel('Mật khẩu',{exact:true}).fill(accounts[key].password);
  await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Tổng quan',exact:true})).toBeVisible();
  return {context,page};
}

test('UI đối chiếu PDF scan với chữ và ảnh trong Word qua API thật',async({browser})=>{
  test.setTimeout(120000);
  const head=await login(browser,'tbm');
  const student=await login(browser,'sv1');
  try {
    await student.page.goto('/ai');
    await expect(student.page.getByRole('button',{name:'Đối chiếu báo cáo',exact:true})).toHaveCount(0);
    await head.page.goto('/ai');
    await head.page.getByRole('button',{name:'Đối chiếu báo cáo',exact:true}).click();
    await head.page.getByLabel('Đề tài thứ nhất',{exact:true}).selectOption({label:'Đối chiếu báo cáo OCR 1 · phiên bản 1'});
    await head.page.getByLabel('Đề tài thứ hai',{exact:true}).selectOption({label:'Đối chiếu báo cáo OCR 2 · phiên bản 1'});
    const [response]=await Promise.all([
      head.page.waitForResponse(r=>r.url().includes('/api/v1/ai/compare-reports?')&&r.request().method()==='POST'),
      head.page.locator('form').getByRole('button',{name:'Đối chiếu báo cáo',exact:true}).click(),
    ]);
    expect(response.status(),await response.text()).toBe(200);
    const result=await response.json();
    expect(result.coverage.map((row:any)=>row.images_seen)).toEqual([1,1]);
    expect(result.image_matches.length).toBeGreaterThan(0);
    if(process.env.KLTN_E2E_EXPECT_OCR==='true') {
      expect(result.coverage.map((row:any)=>row.images_ocr)).toEqual([1,1]);
      expect(result.text_matches.some((row:any)=>row.left_kind==='OCR'&&row.right_kind==='TEXT')).toBe(true);
      expect(result.text_matches.some((row:any)=>row.left_kind==='OCR'&&row.right_kind==='OCR')).toBe(true);
      await expect(head.page.getByText('Chữ từ ảnh · ',{exact:false}).first()).toBeVisible();
    }
    await expect(head.page.getByRole('heading',{name:'Phạm vi đọc',exact:true})).toBeVisible();
    await expect(head.page.getByRole('heading',{name:'Ảnh có dấu hiệu giống nhau',exact:true})).toBeVisible();
  } finally {await head.context.close();await student.context.close();}
});
