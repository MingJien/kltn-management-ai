import {test,expect,type Page} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "node:path";
const accounts=JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON||"{}");
const api=`http://127.0.0.1:${process.env.KLTN_E2E_API_PORT||"8001"}/api/v1`;
async function login(page:Page,key:string){await page.goto("/",{waitUntil:"domcontentloaded"});await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();}
async function read(page:Page,url:string){const r=await page.request.get(api+url);expect(r.status(),await r.text()).toBe(200);return r.json();}
test("Hồ sơ GV: nháp riêng, ảnh, TBM trả lại và duyệt; danh bạ và xem nhanh",async({browser})=>{
 test.setTimeout(150000);
 const contexts=await Promise.all(["gv","tbm","sv1","admin"].map(async key=>{const c=await browser.newContext();const p=await c.newPage();p.setDefaultTimeout(30000);p.setDefaultNavigationTimeout(60000);await login(p,key);return {c,p};}));
 const [gv,tbm,sv,admin]=contexts.map(x=>x.p);
 try{
  await gv.goto("/account",{waitUntil:"domcontentloaded"});await gv.getByRole("button",{name:"Cập nhật hồ sơ",exact:true}).click();
  await gv.getByLabel("Họ và tên",{exact:true}).fill("Giảng viên hồ sơ kiểm thử");
  await gv.getByLabel("Trình độ học vấn",{exact:true}).selectOption("DOCTOR");
  await gv.getByLabel("Chuyên môn",{exact:true}).fill("Công nghệ phần mềm\nTrí tuệ nhân tạo");
  await gv.getByLabel("Email liên hệ công khai",{exact:true}).fill("lecturer@example.test");
  await gv.getByLabel("Số điện thoại",{exact:true}).fill("0901234567");
  await gv.getByLabel("Giới thiệu",{exact:true}).fill("Giới thiệu chuyên môn giả kiểm thử hồ sơ giảng viên.");
  await gv.getByRole("button",{name:"Lưu bản nháp",exact:true}).click();
  await expect(gv.getByLabel("Ảnh đại diện mới",{exact:true})).toBeEnabled();
  // Valid synthetic PNG, decoded and re-encoded by the actual service and scanned by ClamAV.
  // Generate a 128px synthetic image using browser canvas, no external media.
  const bytes=await gv.evaluate(()=>{const c=document.createElement("canvas");c.width=c.height=128;const g=c.getContext("2d")!;g.fillStyle="#28785e";g.fillRect(0,0,128,128);return c.toDataURL("image/png").split(",")[1];});
  await gv.getByLabel("Ảnh đại diện mới",{exact:true}).setInputFiles({name:"avatar.png",mimeType:"image/png",buffer:Buffer.from(bytes,"base64")});
  await expect(gv.getByText("Đã quét an toàn",{exact:true})).toBeVisible();
  let w=await read(gv,"/account/lecturer-profile");const lecturerId=w.profile.id;expect(w.profile.avatar_url).toBeNull();
  expect((await sv.request.get(api+`/lecturer-profile-changes/${w.active_request.id}`)).status()).toBe(404);
  await gv.getByRole("button",{name:"Gửi Khoa duyệt",exact:true}).click();
  let dialog=gv.getByRole("dialog");await dialog.getByLabel("Nội dung cập nhật / căn cứ đề nghị").fill("Đề nghị duyệt cập nhật chuyên môn và ảnh mới");await dialog.getByRole("button",{name:"Xác nhận gửi duyệt",exact:true}).click();await expect(dialog).toHaveCount(0);
  await tbm.goto("/notifications",{waitUntil:"domcontentloaded"});await tbm.getByRole("button",{name:/gửi cập nhật hồ sơ giảng viên cần duyệt/}).click();
  await expect(tbm.getByRole("heading",{name:"Đối chiếu trước và sau cập nhật"})).toBeVisible();
  await tbm.getByRole("button",{name:"Yêu cầu bổ sung",exact:true}).click();dialog=tbm.getByRole("dialog");await dialog.getByLabel("Lý do xử lý hồ sơ").fill("Bổ sung phòng làm việc và giờ tiếp sinh viên");await dialog.getByRole("button",{name:"Gửi yêu cầu bổ sung",exact:true}).click();await expect(dialog).toHaveCount(0);
  await gv.goto("/account",{waitUntil:"domcontentloaded"});await gv.getByRole("button",{name:"Chỉnh sửa và gửi lại",exact:true}).click();
  await expect(gv.getByLabel("Họ và tên",{exact:true})).toHaveValue("Giảng viên hồ sơ kiểm thử");
  await gv.getByLabel("Phòng làm việc",{exact:true}).fill("Phòng mẫu 201");await gv.getByLabel("Giờ tiếp sinh viên",{exact:true}).fill("Thứ Hai 14:00–16:00");await gv.getByRole("button",{name:"Lưu bản nháp",exact:true}).click();
  await expect(gv.getByRole("button",{name:"Gửi Khoa duyệt",exact:true})).toBeEnabled();await gv.getByRole("button",{name:"Gửi Khoa duyệt",exact:true}).click();dialog=gv.getByRole("dialog");await dialog.getByLabel("Nội dung cập nhật / căn cứ đề nghị").fill("Đã bổ sung các nội dung được yêu cầu");await dialog.getByRole("button",{name:"Xác nhận gửi duyệt",exact:true}).click();await expect(dialog).toHaveCount(0);
  w=await read(gv,"/account/lecturer-profile");await tbm.goto(`/lecturer-profile-reviews?request=${w.active_request.id}`,{waitUntil:"domcontentloaded"});
  await tbm.getByRole("button",{name:"Duyệt và công bố",exact:true}).click();dialog=tbm.getByRole("dialog");await dialog.getByLabel("Lý do xử lý hồ sơ").fill("Đã đối chiếu chuyên môn, học vị và ảnh theo hồ sơ giả");await dialog.getByRole("checkbox",{name:/Tôi đã đối chiếu thông tin/}).check();await dialog.getByRole("button",{name:"Xác nhận duyệt hồ sơ",exact:true}).click();await expect(dialog).toHaveCount(0);
  await tbm.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,"lecturer-review.png"),fullPage:true});
  const published=await read(sv,`/lecturer-profiles/${lecturerId}`);expect(published.display_name).toBe("Giảng viên hồ sơ kiểm thử");expect(published.data.contact_phone).toBeNull();expect(published.account_email).toBeNull();expect((await sv.request.get(api.replace("/api/v1","")+published.avatar_url)).status()).toBe(200);
  await sv.goto("/lecturers",{waitUntil:"domcontentloaded"});await sv.getByLabel("Tìm giảng viên",{exact:true}).fill("ho so kiem thu");await sv.getByRole("button",{name:"Xem chi tiết Giảng viên hồ sơ kiểm thử",exact:true}).click();dialog=sv.getByRole("dialog");await expect(dialog.getByText("Phòng mẫu 201",{exact:true})).toBeVisible();await expect(dialog.getByRole("img",{name:/Ảnh đại diện Giảng viên/})).toBeVisible();
  await sv.locator(".dialog-overlay").click({position:{x:4,y:4}});await expect(sv.getByRole("dialog")).toHaveCount(0);await expect(sv).toHaveURL(/\/lecturers$/);
  await sv.goto("/topics",{waitUntil:"domcontentloaded"});await sv.getByRole("link",{name:"Giảng viên hồ sơ kiểm thử",exact:true}).first().click();await expect(sv.getByRole("dialog",{name:"Hồ sơ giảng viên"})).toBeVisible();await sv.keyboard.press("Escape");await expect(sv.getByRole("dialog")).toHaveCount(0);await expect(sv).toHaveURL(/\/topics$/);
  await admin.goto("/lecturers",{waitUntil:"domcontentloaded"});await expect(admin.getByRole("button",{name:"Xem chi tiết Giảng viên hồ sơ kiểm thử",exact:true})).toBeVisible();await expect(admin.getByRole("tab",{name:"Nhập Excel và kích hoạt"})).toBeVisible();
  await gv.goto("/account",{waitUntil:"domcontentloaded"});await expect(gv.getByRole("heading",{name:"Giảng viên hồ sơ kiểm thử",exact:true}).first()).toBeVisible();
  await sv.setViewportSize({width:390,height:844});await sv.goto(`/lecturers/${lecturerId}`,{waitUntil:"domcontentloaded"});await expect(sv.getByText("Phòng mẫu 201",{exact:true})).toBeVisible();expect(await sv.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  const axe=await new AxeBuilder({page:sv}).include(".lecturer-page").withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();expect(axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))).toEqual([]);
  await sv.screenshot({path:path.join(process.env.KLTN_E2E_RUN_DIR!,"lecturer-profile-mobile.png"),fullPage:true});
 }finally{for(const {c} of contexts)await c.close();}
});
