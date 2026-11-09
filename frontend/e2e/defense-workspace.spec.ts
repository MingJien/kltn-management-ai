import {test,expect} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON||"{}");
test("Hội đồng: biểu mẫu 5 thành viên và responsive 320–1440",async({page})=>{
  await page.goto("/");
  await page.getByLabel("Email",{exact:true}).fill(accounts.tbm.email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts.tbm.password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
  await page.goto("/defense");
  await expect(page.getByRole("heading",{name:"Hội đồng và bảo vệ",exact:true})).toBeVisible();
  await page.getByText("Lập hội đồng mới",{exact:true}).click();
  await expect(page.getByRole("combobox",{name:"Chủ tịch",exact:true})).toBeVisible();
  expect(await page.locator('select[name^="lecturer"]').count()).toBe(5);
  for(const width of [320,390,768,1024,1440]){
    await page.setViewportSize({width,height:960});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
  }
  const audit=await new AxeBuilder({page}).include(".defense-page").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
  expect(audit.violations).toEqual([]);
});
