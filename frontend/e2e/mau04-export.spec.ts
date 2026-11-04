import {test, expect} from "@playwright/test";

const accounts = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const web = "http://127.0.0.1:" + (process.env.KLTN_E2E_WEB_PORT || "5174");

test("Mẫu 4 chỉ xuất khi đợt có hồ sơ và liên kết giữ đúng đợt", async ({page}) => {
  await page.goto(web);
  await page.getByLabel("Email",{exact:true}).fill(accounts.admin.email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts.admin.password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
  await page.goto(web+"/forms");
  const round = page.getByRole("combobox",{name:"Đợt KLTN",exact:true});
  await expect(round).not.toHaveValue("");
  const selected = await round.inputValue();
  await page.getByRole("link",{name:"Xuất danh sách theo Mẫu 4",exact:true}).click();
  await expect(page.getByRole("combobox",{name:"Đợt xuất danh sách",exact:true})).toHaveValue(selected);
  await expect(page.getByText("Đợt này chưa có sinh viên đang thực hiện khóa luận.",{exact:false})).toBeVisible();
  await expect(page.getByRole("button",{name:"Xuất danh sách đã điền theo Mẫu 4",exact:true})).toBeDisabled();
});
