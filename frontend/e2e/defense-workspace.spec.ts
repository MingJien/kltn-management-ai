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

test("Điều phối xem báo cáo theo đợt và mở kho nội bộ",async({page})=>{
  await page.goto("/");
  await page.getByLabel("Email",{exact:true}).fill(accounts.tbm.email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts.tbm.password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
  await page.goto("/reports");
  await expect(page.getByRole("heading",{name:"Báo cáo và thống kê KLTN",exact:true})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Điều kiện dự bảo vệ · theo SV",exact:true})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Đối chiếu từng sinh viên",exact:true})).toBeVisible();
  const [refreshed] = await Promise.all([
    page.waitForResponse(response=>{
      const url = new URL(response.url());
      return url.pathname.startsWith("/api/v1/nv6-reports/") && url.searchParams.get("refresh")==="true";
    }),
    page.getByRole("button",{name:"Làm mới thống kê",exact:true}).click(),
  ]);
  expect(refreshed.ok()).toBe(true);
  await expect(page.getByText(/^Số liệu cập nhật lúc /)).toBeVisible();
  for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:900});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  }
  const round = page.getByRole("combobox",{name:"Đợt KLTN",exact:true});
  const roundId = await round.inputValue();
  const roundLabel = (await round.locator("option:checked").textContent())!;
  await page.getByRole("link",{name:"Xem hồ sơ nộp lưu của đợt"}).click();
  await expect(page.getByRole("heading",{name:"Kho khóa luận nội bộ",exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Hồ sơ nộp lưu",exact:true})).toHaveAttribute("aria-pressed","true");
  await expect(round).toHaveValue(roundId);
  await expect(round.locator("option:checked")).toHaveText(roundLabel);
  await page.getByRole("button",{name:"Xóa bộ lọc",exact:true}).click();
  await page.getByRole("button",{name:"Tra cứu bản đã lưu",exact:true}).click();
  await expect(page.getByText("Chưa tìm thấy bản khóa luận đã duyệt trong phạm vi đang xem.",{exact:true})).toBeVisible();
});
