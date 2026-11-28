import {test, expect} from "@playwright/test";

const accounts = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = "http://127.0.0.1:" + (process.env.KLTN_E2E_WEB_PORT || "5174");

test("Tạo biểu mẫu kèm tệp nháp và phát hành cho sinh viên", async ({browser}) => {
  const adminContext=await browser.newContext(),studentContext=await browser.newContext();
  const admin=await adminContext.newPage(),student=await studentContext.newPage();
  async function login(page:typeof admin,key:string){
    await page.goto(web);
    await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);
    await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
    await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
  }
  try {
    await login(admin,"admin");await login(student,"formStudent");
    await admin.goto(web+"/forms");
    await admin.getByText("Thêm biểu mẫu hoặc tài liệu công bố",{exact:true}).click();
    const form=admin.locator("form").filter({has:admin.getByRole("button",{name:"Tạo và lưu tệp nháp",exact:true})});
    await form.getByLabel("Mã tài liệu",{exact:true}).fill("don-thoi-demo");
    await form.getByLabel("Tên tài liệu",{exact:true}).fill("Đơn xin thôi KLTN DEMO");
    await form.getByLabel("Phân loại",{exact:true}).selectOption("PUBLICATION");
    await form.getByLabel("Nguồn / văn bản áp dụng",{exact:true}).fill("Mẫu thử nghiệm của Khoa");
    await form.getByLabel("Lý do tạo danh mục",{exact:true}).fill("Thêm mẫu thử cho đợt demo");
    const upload=form.getByLabel("Tệp biểu mẫu hoặc tài liệu (PDF, DOCX, XLSX)",{exact:true});
    await upload.setInputFiles({name:"empty.pdf",mimeType:"application/pdf",buffer:Buffer.alloc(0)});
    await expect(form.getByRole("button",{name:"Tạo và lưu tệp nháp",exact:true})).toBeDisabled();
    await upload.setInputFiles(process.env.KLTN_E2E_NV6_FILE!);
    await admin.screenshot({path:process.env.KLTN_E2E_RUN_DIR!+"/school-form-create-desktop.png",fullPage:true});
    await admin.setViewportSize({width:390,height:844});
    await expect.poll(()=>admin.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    await admin.screenshot({path:process.env.KLTN_E2E_RUN_DIR!+"/school-form-create-mobile.png",fullPage:true});
    await admin.setViewportSize({width:1280,height:720});
    await form.getByRole("button",{name:"Tạo và lưu tệp nháp",exact:true}).click();
    const card=admin.locator(".school-form-card").filter({has:admin.getByRole("heading",{name:"Đơn xin thôi KLTN DEMO",exact:true})});
    await expect(card.getByText("Bản nháp",{exact:true})).toBeVisible();
    await expect(card.getByRole("button",{name:"Phát hành v1",exact:true})).toBeEnabled();
    await student.goto(web+"/forms");
    await expect(student.getByText("Đơn xin thôi KLTN DEMO",{exact:true})).toHaveCount(0);
    await card.getByRole("button",{name:"Phát hành v1",exact:true}).click();
    await expect(admin.getByRole("status").filter({hasText:"Đã phát hành"})).toBeVisible();
    await student.reload();
    await expect(student.getByText("Đơn xin thôi KLTN DEMO",{exact:true})).toBeVisible();
  } finally {await adminContext.close();await studentContext.close();}
});

test("Mất kết nối khi tải tệp vẫn có thể mở danh mục để tải lại", async ({page}) => {
  await page.goto(web);
  await page.getByLabel("Email",{exact:true}).fill(accounts.admin.email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts.admin.password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
  await page.goto(web+"/forms");
  await page.getByText("Thêm biểu mẫu hoặc tài liệu công bố",{exact:true}).click();
  const form=page.locator("form").filter({has:page.getByRole("button",{name:"Tạo và lưu tệp nháp",exact:true})});
  await form.getByLabel("Mã tài liệu",{exact:true}).fill("don-thoi-loi-demo");
  await form.getByLabel("Tên tài liệu",{exact:true}).fill("Đơn thử lỗi tải DEMO");
  await form.getByLabel("Nguồn / văn bản áp dụng",{exact:true}).fill("Nguồn thử của Khoa");
  await form.getByLabel("Lý do tạo danh mục",{exact:true}).fill("Thử khôi phục khi mất mạng");
  await form.getByLabel("Tệp biểu mẫu hoặc tài liệu (PDF, DOCX, XLSX)",{exact:true}).setInputFiles(process.env.KLTN_E2E_NV6_FILE!);
  const pattern="**/api/v1/school-forms/*/versions";
  await page.route(pattern, route=>route.abort());
  await form.getByRole("button",{name:"Tạo và lưu tệp nháp",exact:true}).click();
  await expect(page.getByRole("alert").filter({hasText:"Danh mục đã được tạo nhưng chưa xác nhận được kết quả tải tệp"})).toBeVisible();
  const card=page.locator(".school-form-card").filter({has:page.getByRole("heading",{name:"Đơn thử lỗi tải DEMO",exact:true})});
  await expect(card.getByText("Chưa có tệp phiên bản.",{exact:true})).toBeVisible();
  await page.unroute(pattern);
  await card.getByText("Cập nhật tệp biểu mẫu / tài liệu",{exact:true}).click();
  await card.getByLabel("Lý do thao tác / cập nhật phiên bản",{exact:true}).fill("Tải lại tệp sau lỗi kết nối");
  await card.getByLabel("Nguồn / văn bản áp dụng",{exact:true}).fill("Nguồn thử của Khoa");
  await card.getByLabel("Tải phiên bản mới (PDF/DOCX/XLSX)",{exact:true}).setInputFiles(process.env.KLTN_E2E_NV6_FILE!);
  await card.getByRole("button",{name:"Lưu bản nháp",exact:true}).click();
  await expect(card.getByText("Bản nháp",{exact:true})).toBeVisible();
});
