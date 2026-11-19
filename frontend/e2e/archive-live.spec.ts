import {expect,test,type Page} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import {readFile} from "node:fs/promises";

const accounts = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON||"{}");
const title = "Ứng dụng tra cứu khóa luận";

async function login(page:Page, key:string) {
  await page.goto("/");
  await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
}

test("Kho thật: nộp và quét, trả, duyệt, tra không dấu, thu hồi và giữ lịch sử", async ({browser})=>{
  test.setTimeout(240000);
  const id = process.env.KLTN_E2E_ARCHIVE_THESIS;
  const path = process.env.KLTN_E2E_NV6_FILE;
  expect(id).toBeTruthy();
  expect(path).toBeTruthy();
  const url = `/repository?focus=${id}`;
  const contexts = await Promise.all([browser.newContext(),browser.newContext(),browser.newContext()]);
  try {
    const [student,head,outsider] = await Promise.all(contexts.map(c=>c.newPage()));
    for (const page of [student,head,outsider]) page.setDefaultTimeout(15000);
    await Promise.all([login(student,"sv1"),login(head,"tbm"),login(outsider,"sv2")]);
    await outsider.goto(url);
    await expect(outsider.getByRole("alert")).toContainText("Không tìm thấy hồ sơ");
    await student.goto(`/theses/${id}`);
    await student.getByRole("link",{name:"Hồ sơ nộp lưu sau bảo vệ",exact:true}).click();
    await student.getByLabel(/Bản khóa luận hoàn thiện sau bảo vệ/).setInputFiles(path!);
    await student.getByRole("button",{name:"Nộp bản hoàn thiện",exact:true}).click();
    await expect(student.getByText("Phiên bản 1 · Chờ bộ môn duyệt",{exact:true})).toBeVisible({timeout:110000});

    await head.goto("/repository?mode=work");
    await expect(head.getByRole("link",{name:title,exact:true})).toBeVisible();
    await head.getByRole("combobox",{name:"Trạng thái",exact:true}).selectOption("SUBMITTED",{timeout:10000});
    await head.getByRole("link",{name:title,exact:true}).click();
    await head.reload();
    await head.getByRole("button",{name:"Quay về danh sách",exact:true}).click();
    await expect(head.getByLabel("Trạng thái",{exact:true})).toHaveValue("SUBMITTED");
    await head.getByRole("link",{name:title,exact:true}).click();
    await expect(head.locator(".archive-version")).toHaveCount(1);
    await head.getByRole("button",{name:"Làm mới",exact:true}).click();
    await expect(head.getByRole("button",{name:"Làm mới",exact:true})).toBeEnabled();
    await expect(head.locator(".archive-version")).toHaveCount(1);
    await head.getByRole("button",{name:"Xem nhanh v1",exact:true}).click();
    await expect(head.locator(".review-pdf-sheet canvas")).toBeVisible();
    await head.getByRole("button",{name:"Đóng bản xem",exact:true}).click();
    await head.getByRole("combobox",{name:"Kết quả kiểm tra",exact:true}).selectOption("RETURNED");
    await head.getByLabel("Nhận xét và căn cứ",{exact:true}).fill("Bổ sung hướng dẫn theo kết luận hội đồng.");
    await head.getByRole("button",{name:"Lưu quyết định",exact:true}).click();
    await expect(head.getByText("Phiên bản 1 · Cần nộp lại",{exact:true})).toBeVisible();

    await student.reload();
    await student.getByLabel(/Bản khóa luận hoàn thiện sau bảo vệ/).setInputFiles(path!);
    await student.getByRole("button",{name:"Nộp bản thay thế",exact:true}).click();
    await expect(student.getByText("Phiên bản 2 · Chờ bộ môn duyệt",{exact:true})).toBeVisible({timeout:110000});
    await head.reload();
    await head.getByRole("combobox",{name:"Kết quả kiểm tra",exact:true}).selectOption("ACCEPTED");
    await head.getByLabel("Nhận xét và căn cứ",{exact:true}).fill("Đã kiểm tra đúng bản hoàn thiện.");
    await head.getByRole("button",{name:"Lưu quyết định",exact:true}).click();
    await expect(head.getByText("Phiên bản 2 · Đã duyệt lưu",{exact:true})).toBeVisible();

    await student.goto(`/theses/${id}`);
    await expect(student.locator(".core-toolbar__status")).toContainText("Hoàn thành");
    await student.goto("/repository");
    const search = student.getByRole("searchbox",{name:"Tìm khóa luận",exact:true});
    await search.fill("tai lieu khong ton tai");
    await expect(student.getByText("0 khóa luận · Trang 1/1",{exact:true})).toBeVisible();
    await search.fill("ung dung tra cuu e2e-kho-001");
    await expect(student.getByText("1 khóa luận · Trang 1/1",{exact:true})).toBeVisible();
    await expect(student.locator(".archive-list dt").filter({hasText:"Sinh viên"})).toBeVisible();
    await student.reload();
    await expect(search).toHaveValue("ung dung tra cuu e2e-kho-001");
    await expect(student.getByRole("link",{name:title,exact:true})).toBeVisible();
    for (const width of [320,390,768,1440]) {
      await student.setViewportSize({width,height:900});
      await expect.poll(()=>student.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    }
    const listAudit = await new AxeBuilder({page:student}).include(".archive-page").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
    expect(listAudit.violations).toEqual([]);
    await student.screenshot({path:test.info().outputPath("archive-catalog-desktop.png")});
    await student.setViewportSize({width:390,height:844});
    await expect(student.locator(".sidebar-overlay")).toBeHidden();
    await expect.poll(()=>student.locator(".app-shell__main").evaluate(el=>el.getBoundingClientRect().left)).toBe(0);
    await student.screenshot({path:test.info().outputPath("archive-catalog-mobile.png"),fullPage:true});
    await student.getByRole("link",{name:title,exact:true}).click();
    const [download] = await Promise.all([
      student.waitForEvent("download"), student.getByRole("button",{name:"Tải phiên bản 2",exact:true}).click(),
    ]);
    expect(download.suggestedFilename()).toBe("Ban-luu-KLTN-v2-E2E-KHO-001.pdf");
    expect(await readFile((await download.path())!)).toEqual(await readFile(path!));
    for (const width of [320,390,768,1440]) {
      await student.setViewportSize({width,height:900});
      await expect.poll(()=>student.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    }
    const audit = await new AxeBuilder({page:student}).include(".archive-page").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
    expect(audit.violations).toEqual([]);

    await head.getByText("Thu hồi bản lưu và yêu cầu nộp lại",{exact:true}).click();
    await head.getByLabel("Lý do thu hồi",{exact:true}).fill("Đối chiếu lại phát hiện lưu nhầm bản báo cáo.");
    await head.getByLabel("Tôi đã đối chiếu đúng bản cần thu hồi.",{exact:true}).check();
    await head.getByRole("button",{name:"Thu hồi và thông báo nhóm",exact:true}).click();
    await expect(head.getByText("Phiên bản 2 · Đã thu hồi bản lưu",{exact:true})).toBeVisible();
    await expect(head.getByText("Đã kiểm tra đúng bản hoàn thiện.",{exact:false})).toBeVisible();
    await student.goto("/repository");
    await expect(student.getByText("Chưa tìm thấy bản khóa luận đã duyệt trong phạm vi đang xem.",{exact:true})).toBeVisible();
    await student.goto(url);
    await expect(student.getByRole("button",{name:"Nộp bản thay thế",exact:true})).toBeVisible();
    await student.getByText("Lịch sử bản nộp (1 bản trước)",{exact:true}).click();
    await expect(student.getByText("Phiên bản 1 · Cần nộp lại",{exact:true})).toBeVisible();
  } finally {
    await Promise.all(contexts.map(c=>c.close()));
  }
});

test("Bố cục các bước từ đăng ký đến lưu kho ở 320–1440 px", async ({page})=>{
  test.setTimeout(150000);
  const id = process.env.KLTN_E2E_ARCHIVE_THESIS;
  await login(page,"sv1");
  const errors:string[]=[];
  page.on("pageerror",error=>errors.push(error.message));
  await page.setViewportSize({width:390,height:844});
  const menu = page.getByRole("button",{name:"Mở hoặc đóng menu"});
  await menu.click();
  await expect(page.getByRole("button",{name:"Đóng menu điều hướng"})).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(menu).toBeFocused();
  await menu.click();
  await page.getByRole("link",{name:"Kho khóa luận nội bộ",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Kho khóa luận nội bộ",exact:true})).toBeVisible();
  await expect(menu).toHaveAttribute("aria-expanded","false");
  const routes = ["/topics","/registrations",`/theses/${id}?section=submissions`,
    `/theses/${id}?section=progress`,`/evaluation/${id}`,"/defense","/notifications","/repository?mode=work"];
  for (const path of routes) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading",{level:1}).first()).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    for (const width of [320,390,768,1440]) {
      await page.setViewportSize({width,height:900});
      await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth),{message:`${path} · ${width}px`}).toBeLessThanOrEqual(width+1);
      if (width<1024) {
        await expect(page.locator(".sidebar-overlay")).toBeHidden();
        await expect.poll(()=>page.locator(".app-shell__main").evaluate(el=>el.getBoundingClientRect().left)).toBe(0);
      }
    }
  }
  expect(errors).toEqual([]);
});
