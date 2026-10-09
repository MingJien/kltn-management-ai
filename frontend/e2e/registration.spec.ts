import { test, expect, type Browser, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const accounts: Record<string,{email:string;password:string}> = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const api = "http://127.0.0.1:8001/api/v1";
async function login(browser: Browser, key: string) {
  const context = await browser.newContext({viewport:{width:1440,height:1000}});
  const page = await context.newPage();
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("http://127.0.0.1:5174/");
  await page.getByLabel("Email",{exact:true}).fill(accounts[key].email);
  await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[key].password);
  await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
  return {page,context,errors};
}
async function close(actors: Awaited<ReturnType<typeof login>>[]) {
  for (const actor of actors) {expect(actor.errors).toEqual([]); await actor.context.close();}
}
async function read(page: Page, path: string) {const r = await page.request.get(api + path); expect(r.status()).toBe(200); return r.json();}
async function write(page: Page, path: string, options: {data?: unknown; headers?: Record<string,string>} = {}) {
  const session = await read(page, "/me/context");
  return page.request.post(api + path, {
    ...options,
    headers: {"X-CSRF-Token": session.csrf_token, ...options.headers},
  });
}
function card(page: Page, title: string) {return page.locator("article").filter({has:page.getByRole("heading",{name:title,exact:true})});}
async function find(page: Page, title: string) {
  await page.goto("http://127.0.0.1:5174/topics");
  await page.getByRole("button",{name:"Đề tài có sẵn",exact:true}).click();
  await page.getByLabel("Tìm đề tài").fill(title);
  await expect(card(page,title)).toHaveCount(1);
  return card(page,title);
}
async function join(page: Page, title: string, second = false) {
  await (await find(page,title)).getByRole("button",{name:second ? "Tham gia" : "Đăng ký",exact:true}).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("checkbox").check();
  await dialog.getByRole("button",{name:second ? "Tham gia đề tài" : "Lập đăng ký của tôi",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Đăng ký đề tài",exact:true})).toBeVisible();
  return card(page,title);
}
async function proof(page: Page, title: string) {
  await card(page,title).locator('input[type="file"]').setInputFiles({name:"minh-chung-gia-lap.pdf",mimeType:"application/pdf",
    buffer:Buffer.from("%PDF-1.7\nSYNTHETIC TEST ONLY\n%%EOF")});
  await expect(card(page,title).getByRole("link",{name:/Tải minh chứng/}).last()).toBeVisible();
}
async function review(page: Page, title: string, receiver?: string) {
  await page.goto("http://127.0.0.1:5174/topics");
  await page.getByLabel("Tìm đề tài").fill(title);
  await card(page,title).getByRole("button",{name:"Xem và duyệt"}).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Tên đề tài sau khi duyệt").fill(title + " đã duyệt");
  if (receiver) await dialog.getByLabel("GV tiếp nhận (xác nhận hoặc chọn lại)").selectOption(receiver);
  await dialog.getByRole("button",{name:"Duyệt đề tài",exact:true}).click();
  await expect(dialog.getByText("Đã duyệt",{exact:true})).toBeVisible();
  await dialog.getByRole("button",{name:"Đóng",exact:true}).click();
}

test("GV tạo → TBM duyệt/sửa tên → SV tự đăng ký → GV nhận; bổ sung và xét lại", async ({browser}) => {
  const actors = await Promise.all(["gv","tbm","sv1","sv2","sv3"].map(key => login(browser,key)));
  const [gv,tbm,sv1,sv2,sv3] = actors;
  try {
    const title = "E2E Quản lý đề tài và đăng ký";
    await gv.page.goto("http://127.0.0.1:5174/topics");
    await gv.page.getByRole("button",{name:"Tạo đề tài",exact:true}).click();
    let dialog = gv.page.getByRole("dialog");
    await dialog.getByLabel("Tên đề tài",{exact:true}).fill(title);
    await dialog.getByLabel("Mô tả, mục tiêu và phạm vi").fill("Dữ liệu giả kiểm thử luồng nghiệp vụ.");
    await dialog.getByLabel("Số sinh viên tối đa").selectOption("2");
    await dialog.getByRole("button",{name:"+ Thêm yêu cầu"}).click();
    await dialog.getByLabel("Nội dung",{exact:true}).fill("Python và PostgreSQL");
    await dialog.getByRole("button",{name:"Tạo bản nháp",exact:true}).click();
    dialog = gv.page.getByRole("dialog");
    await dialog.getByRole("button",{name:"Gửi bộ môn duyệt"}).click();
    await expect(dialog.getByText("Đã gửi",{exact:true})).toBeVisible();
    await review(tbm.page,title);
    const approved = title + " đã duyệt";
    await join(sv1.page,approved);
    await expect(card(sv1.page,approved).getByText("1/2 SV",{exact:true})).toBeVisible();
    await proof(sv1.page,approved);
    await card(sv1.page,approved).getByRole("button",{name:"Gửi đăng ký cho GV"}).click();
    await expect(card(sv1.page,approved).getByText("Đã gửi",{exact:true}).first()).toBeVisible();
    await gv.page.goto("http://127.0.0.1:5174/registrations");
    await card(gv.page,approved).getByRole("button",{name:"Chấp nhận",exact:true}).click();
    await expect(card(gv.page,approved).getByText("GV đã chấp nhận",{exact:true})).toBeVisible();
    await join(sv2.page,approved,true);
    await expect(card(sv2.page,approved).getByText("2/2 SV",{exact:true})).toBeVisible();
    await proof(sv2.page,approved);
    const topic = (await read(sv3.page,"/topics?search=" + encodeURIComponent(approved)))[0];
    await expect((await find(sv3.page,approved)).getByRole("button",{name:"Đã đóng đăng ký"})).toBeDisabled();
    expect((await write(sv3.page,"/topic-registrations",{data:{topic_id:topic.id}})).status()).toBe(409);
    await gv.page.getByRole("button",{name:"Làm mới",exact:true}).click();
    await card(gv.page,approved).getByRole("button",{name:"Chấp nhận",exact:true}).click();
    await expect(card(gv.page,approved).getByText("GV đã chấp nhận",{exact:true})).toBeVisible();
    const registrations = (await read(gv.page,"/topic-registrations")).filter((r:{topic_id:string}) => r.topic_id === topic.id);
    expect(registrations).toHaveLength(1); expect(registrations[0].members).toHaveLength(2);
    expect(registrations[0].state).toBe("LECTURER_ACCEPTED");
    expect(topic.title_versions.map((v:{title:string}) => v.title)).toEqual([title,approved]);
    await sv1.page.reload();
    await expect(sv1.page.getByRole("heading",{name:"Đăng ký đề tài",exact:true})).toBeVisible();
    expect((await write(sv1.page,"/topics",{data:{round_id:topic.round_id,title:"SV không được tạo đề tài GV"}})).status()).toBe(403);
  } finally {await close(actors);}
});

test("SV đề xuất cá nhân → trả lại/sửa/duyệt → SV khác tham gia → GV từ chối có lý do", async ({browser}) => {
  const actors = await Promise.all(["sv3","proposalPeer","tbm","gv"].map(key => login(browser,key)));
  const [sv,peer,tbm,gv] = actors;
  try {
    const receiver = (await read(sv.page,"/lecturers")).find((l:{lecturer_code:string}) => l.lecturer_code === "SYN-DEMO-GV-1");
    const title = "E2E Đề tài do sinh viên đề xuất";
    await sv.page.goto("http://127.0.0.1:5174/topics");
    await sv.page.getByRole("button",{name:"Tự đề xuất đề tài",exact:true}).click();
    let dialog = sv.page.getByRole("dialog");
    await dialog.getByLabel("Tên đề tài",{exact:true}).fill(title);
    await dialog.getByLabel("Số sinh viên tối đa").selectOption("2");
    await dialog.getByLabel("GV mong muốn tiếp nhận").selectOption(receiver.id);
    await dialog.getByRole("checkbox").check();
    await dialog.getByRole("button",{name:"Lập đăng ký của tôi"}).click();
    await expect(sv.page.getByRole("heading",{name:"Đăng ký đề tài",exact:true})).toBeVisible();
    await sv.page.getByRole("button",{name:"Gửi đề xuất cho bộ môn"}).click();
    await expect(sv.page.getByText(/Đề xuất đang chờ/)).toBeVisible();
    expect(await read(peer.page,"/topics?search=" + encodeURIComponent(title))).toEqual([]);
    await tbm.page.goto("http://127.0.0.1:5174/topics");
    await tbm.page.getByLabel("Tìm đề tài").fill(title);
    await card(tbm.page,title).getByRole("button",{name:"Xem và duyệt"}).click();
    dialog = tbm.page.getByRole("dialog");
    await dialog.getByLabel("Góp ý / lý do").fill("Làm rõ phạm vi của đề tài");
    await dialog.getByRole("button",{name:"Trả lại để sửa"}).click();
    await expect(dialog.getByText("Trả lại để sửa",{exact:true}).first()).toBeVisible();
    await dialog.getByRole("button",{name:"Đóng",exact:true}).click();
    await sv.page.goto("http://127.0.0.1:5174/topics");
    await sv.page.getByRole("button",{name:"Đề xuất của tôi"}).click();
    await card(sv.page,title).getByRole("button",{name:"Xem chi tiết"}).click();
    dialog = sv.page.getByRole("dialog");
    await dialog.getByLabel("Mô tả, mục tiêu và phạm vi").fill("Phạm vi đăng ký và duyệt đề tài.");
    await dialog.getByRole("button",{name:"Lưu chỉnh sửa"}).click();
    await expect(dialog.getByText("Đã lưu đề tài.",{exact:true})).toBeVisible();
    await dialog.getByRole("button",{name:"Đóng",exact:true}).click();
    await sv.page.goto("http://127.0.0.1:5174/registrations");
    await sv.page.getByRole("button",{name:"Gửi đề xuất cho bộ môn"}).click();
    await review(tbm.page,title,receiver.id);
    await join(peer.page,title + " đã duyệt",true);
    await gv.page.goto("http://127.0.0.1:5174/registrations");
    await card(gv.page,title + " đã duyệt").getByRole("button",{name:"Từ chối",exact:true}).click();
    dialog = gv.page.getByRole("dialog");
    await expect(dialog.getByRole("button",{name:"Xác nhận từ chối"})).toBeDisabled();
    await dialog.getByLabel("Lý do từ chối").fill("Chưa phù hợp chuyên môn tiếp nhận");
    await dialog.getByRole("button",{name:"Xác nhận từ chối"}).click();
    await expect(dialog).toHaveCount(0);
    await expect(card(gv.page,title + " đã duyệt").getByText("GV từ chối",{exact:true})).toBeVisible();
    const reg = (await read(sv.page,"/topic-registrations")).find((r:{topic_title:string}) => r.topic_title === title + " đã duyệt");
    expect(reg.members.every((m:{active:boolean}) => !m.active)).toBe(true);
    expect((await read(sv.page,"/me/eligibility?round_id=" + reg.round_id)).has_active_registration).toBe(false);
  } finally {await close(actors);}
});

test("Hai SV tranh chỗ cuối: chỉ một người tham gia, không vượt sức chứa", async ({browser}) => {
  const actors = await Promise.all(["gv","tbm","race1","race2","race3"].map(key => login(browser,key)));
  const [gv,tbm,first,a,b] = actors;
  try {
    const round = (await read(gv.page,"/rounds/open"))[0];
    let response = await write(gv.page,"/topics",{data:{round_id:round.id,title:"E2E Concurrent capacity",max_students:2}});
    expect(response.status()).toBe(201); let topic = await response.json();
    topic = await (await write(gv.page,"/topics/" + topic.id + "/submit",{headers:{"If-Match":String(topic.row_version)}})).json();
    expect((await write(tbm.page,"/topics/" + topic.id + "/department-decision",{
      headers:{"If-Match":String(topic.row_version)},data:{decision:"APPROVE"}})).status()).toBe(200);
    expect((await write(first.page,"/topic-registrations",{data:{topic_id:topic.id}})).status()).toBe(201);
    const competing = await Promise.all([a,b].map(actor => write(actor.page,"/topic-registrations",{data:{topic_id:topic.id}})));
    expect(competing.map(r => r.status()).sort()).toEqual([201,409]);
    const groups = await read(first.page,"/topic-registrations");
    expect(groups).toHaveLength(1); expect(groups[0].members).toHaveLength(2);
  } finally {await close(actors);}
});

test("Di động, bàn phím, lỗi tiếng Việt, phiên đăng nhập và accessibility", async ({browser}) => {
  const context = await browser.newContext({viewport:{width:360,height:800}});
  const page = await context.newPage();
  async function accessible(scope?: string) {
    const builder = new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa"]);
    if (scope) builder.include(scope);
    const result = await builder.analyze();
    expect(result.violations.map(v => ({id:v.id,targets:v.nodes.map(n => n.target)}))).toEqual([]);
  }
  try {
    await page.goto("http://127.0.0.1:5174/");
    await page.getByLabel("Email",{exact:true}).fill(accounts.sv1.email);
    await page.getByLabel("Mật khẩu",{exact:true}).fill("incorrect-synthetic-password");
    await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
    await expect(page.getByRole("alert")).toContainText("Email hoặc mật khẩu");
    await accessible();
    await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts.sv1.password);
    await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
    await page.goto("http://127.0.0.1:5174/topics");
    await expect(page.getByRole("heading",{name:"Đề tài",exact:true})).toBeVisible();
    await expect(page).toHaveTitle("Đề tài · KLTN");
    expect(await page.locator("html").getAttribute("lang")).toBe("vi");
    expect(await page.locator('meta[name="robots"]').getAttribute("content")).toContain("noindex");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await accessible();
    await page.locator("article").first().getByRole("button",{name:"Xem chi tiết"}).click();
    await expect(page.getByRole("dialog")).toBeVisible(); await accessible('[role="dialog"]');
    await page.keyboard.press("Escape"); await expect(page.getByRole("dialog")).toHaveCount(0);
    await page.getByRole("button",{name:"Đăng xuất",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Đăng nhập",exact:true})).toBeVisible();
    expect((await page.request.get(api + "/me/context")).status()).toBe(401);
  } finally {await context.close();}
});
