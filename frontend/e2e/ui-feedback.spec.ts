import {test, expect, type Page} from "@playwright/test";

// Browser regressions with controlled API responses (not database integration tests).
const account = (id: string, role: string) => ({id, email:`${id}@ui.test`,base_role:role,status:"ACTIVE",verified:true,student_code:null});
const context = {user_id:"admin",base_role:"ADMIN",student_id:null,lecturer_id:null,
  display_name:"UI test",actions:["account:manage","topic:department_decide"],csrf_token:"ui-only"};
const topic = {id:"topic",round_id:"round",title:"Đề tài UI đề xuất",description:"Kiểm thử tải chậm",max_students:2,state:"SUBMITTED",row_version:1,department_id:"dep",proposer_user_id:"sv",code:"UI-01",round_label:"2026",proposer_type:"STUDENT",receiving_lecturer_id:"gv",receiving_lecturer_name:"GV được đề xuất",requirements:[],title_versions:[],registered_member_count:1,remaining_slots:1,available:false};
async function mock(page: Page, handle: (path: string, method: string, body: any) => unknown | Promise<unknown>, role = "ADMIN") {
  await page.route("**/api/v1/**", async route => {
    const req = route.request();
    const cors = {"Access-Control-Allow-Origin":req.headers().origin || new URL(page.url()).origin,"Access-Control-Allow-Credentials":"true"};
    if (req.method() === "OPTIONS") {await route.fulfill({status:204,headers:{...cors,"Access-Control-Allow-Headers":"content-type,x-csrf-token,if-match","Access-Control-Allow-Methods":"GET,POST,PATCH,OPTIONS"}});return;}
    const path = new URL(req.url()).pathname.replace("/api/v1", "");
    if (path === "/admin/lecturers" && req.method() === "GET") {
      await route.fulfill({json:{items:[],delivery_mode:"development_outbox",mail_ready:true},headers:cors});return;
    }
    if(path.endsWith("/publication-claims")){await route.fulfill({json:{items:[],can_submit:false,can_review:false,can_approve:false},headers:cors});return;}
    if(path.startsWith("/lecturer-profiles/")&&req.method()==="GET"){
      const people=await handle("/lecturers","GET",null) as any[];
      const person=Array.isArray(people)?people.find(p=>p.id===path.split("/").pop()):null;
      await route.fulfill(person?{headers:cors,json:{...person,data:{display_name:person.display_name,specializations:[],research_interests:[],show_phone:false},positions:[],row_version:1,verified_at:null,verification_kind:null,avatar_url:null,can_manage_identity:false,is_owner:false}}:{status:404,headers:cors,json:{detail:"Không tìm thấy giảng viên"}});return;
    }
    const result = path === "/me/context" ? {...context,base_role:role} : path === "/notifications" ? {unread_count:0,items:[]} : await handle(path,req.method(),req.postDataJSON());
    await route.fulfill({json:result ?? [],headers:cors});
  });
}

test("UI: lý do sửa email nằm trong form riêng; đổi nhiệm vụ giữ hoặc xóa người đúng điều kiện", async ({page}) => {
  let emailPayload: any;
  await mock(page, (path, method, body) => {
    if ((path === "/admin/users" || path === "/admin/staff") && method === "GET") return [account("admin","ADMIN"),account("gv","LECTURER")];
    if (path === "/admin/users/directory" && method === "GET") return {items:[account("admin","ADMIN"),account("gv","LECTURER")],total:2,counts:{ALL:2,LECTURER:1,ADMIN:1},role_catalog:[]};
    if (path === "/admin/rounds") return [{id:"round",code:"UI-ROUND",state:"OPEN"}];
    if (path.endsWith("/contact-email")) {emailPayload=body;return {activation_sent:false};}
  });
  await page.goto("/administration/assignments");
  await page.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("ELIGIBILITY_VERIFIER");
  await page.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption("gv");
  await page.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("KLTN_COORDINATOR");
  await expect(page.getByRole("combobox",{name:"Người được giao",exact:true})).toHaveValue("gv");
  await page.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("ELIGIBILITY_VERIFIER");
  await page.getByRole("combobox",{name:"Người được giao",exact:true}).selectOption("admin");
  await page.getByRole("combobox",{name:"Nhiệm vụ",exact:true}).selectOption("KLTN_COORDINATOR");
  await expect(page.getByRole("combobox",{name:"Người được giao",exact:true})).toHaveValue("");
  await expect(page.getByText("Người đã chọn không phù hợp nhiệm vụ mới.",{exact:false})).toBeVisible();
  const save=page.getByRole("button",{name:"Lưu phân công",exact:true});
  if(await save.isEnabled()) {
    await save.click();
    await expect(page.locator("#assignment-hint")).toContainText("Vui lòng chọn đợt");
  } else await expect(page.locator("#assignment-hint")).toContainText("Vui lòng chọn lại");
  await page.goto("/administration");
  await page.locator(".account-list__row").filter({hasText:"gv@ui.test"}).getByRole("button",{name:"Sửa email",exact:true}).click();
  await page.getByLabel("Email mới",{exact:true}).fill("changed@ui.test");
  await page.getByLabel("Căn cứ xác minh của Khoa").fill("UI-VERIFY");
  await expect(page.getByRole("button",{name:"Lưu email mới",exact:true})).toBeDisabled();
  await expect(page.locator("#email-reason-hint")).toContainText("ít nhất 5 ký tự");
  await page.getByLabel("Lý do sửa email",{exact:true}).fill("Đối chiếu dữ liệu Khoa");
  await page.getByRole("button",{name:"Lưu email mới",exact:true}).click();
  await expect.poll(()=>emailPayload?.reason).toBe("Đối chiếu dữ liệu Khoa");
  expect(emailPayload.email).toBe("changed@ui.test");
});

test("UI: modal chờ danh sách GV, giữ GV đề xuất khi dữ liệu tải xong", async ({page}) => {
  let release!: () => void;
  const ready = new Promise<void>(resolve => {release=resolve;});
  let decision: any;
  await mock(page, async (path, method, body) => {
    if (path === "/topics") return [topic];
    if (path === "/lecturers") {await ready;return [{id:"gv",display_name:"GV được đề xuất",lecturer_code:"GV-UI"}];}
    if (path.endsWith("/department-decision")) {decision=body;return {...topic,state:"APPROVED"};}
  }, "LECTURER");
  await page.goto("/topics");
  await page.getByRole("button",{name:"Xem và duyệt",exact:true}).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Đang tải danh sách giảng viên…",{exact:true})).toBeVisible();
  await expect(dialog.getByRole("button",{name:"Duyệt đề tài",exact:true})).toBeDisabled();
  release();
  await expect(dialog.getByRole("combobox")).toHaveValue("gv");
  await dialog.getByRole("button",{name:"Duyệt đề tài",exact:true}).click();
  await expect.poll(()=>decision?.receiving_lecturer_id).toBe("gv");
});

test("UI: làm mới hồ sơ lấy dữ liệu mới, giữ tab và bản nháp; lỗi không xóa dữ liệu cũ", async ({page}) => {
  let title = "Khóa luận UI trước cập nhật";
  await mock(page, path => {
    if (path === "/theses/thesis") {
      return {id:"thesis",title,state:"IN_PROGRESS",round_label:"UI-ROUND",advisor_name:"GV UI",members:[],advisor_history:[],cross_reviewers:[],actions:["document:view","document:submit"],row_version:1};
    }
  }, "LECTURER");
  await page.goto("/theses/thesis?section=submissions&kind=SUPPORTING");
  await page.getByLabel("Tên tài liệu",{exact:true}).fill("Bản nháp chưa gửi");
  title="Khóa luận UI đã cập nhật";
  await page.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
  await expect(page.getByText(title,{exact:false})).toBeVisible();
  await expect(page.getByLabel("Tên tài liệu",{exact:true})).toHaveValue("Bản nháp chưa gửi");
  await expect(page).toHaveURL(/section=submissions.*kind=SUPPORTING/);
  await page.route("**/api/v1/theses/thesis", route=>route.fulfill({status:503,json:{detail:"UI server unavailable"}}));
  await page.getByRole("button",{name:"Làm mới dữ liệu",exact:true}).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByText(title,{exact:false})).toBeVisible();
  await expect(page.getByLabel("Tên tài liệu",{exact:true})).toHaveValue("Bản nháp chưa gửi");
});

test("UI: tải lại danh sách GV lỗi không tự gán một GV khác khi GV đề xuất không còn hợp lệ", async ({page}) => {
  await mock(page, path => path === "/topics" ? [topic] : path === "/lecturers" ? [{id:"other",display_name:"GV khác",lecturer_code:"GV-OTHER"}] : [], "LECTURER");
  let retryAllowed = false;
  await page.route(/\/api\/v1\/lecturers(?:\?.*)?$/, async route => {
    if (route.request().method() !== "OPTIONS" && !retryAllowed) await route.abort();
    else await route.fallback();
  });
  await page.goto("/topics");
  await page.getByRole("button",{name:"Xem và duyệt",exact:true}).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText(/Chưa tải được danh sách:/)).toBeVisible();
  await expect(dialog.getByRole("button",{name:"Duyệt đề tài",exact:true})).toBeDisabled();
  retryAllowed = true;
  await dialog.getByRole("button",{name:"Tải lại danh sách giảng viên"}).click();
  await expect(dialog.getByRole("combobox")).toBeEnabled();
  await expect(dialog.getByRole("combobox")).toHaveValue("");
  await expect(dialog.getByRole("button",{name:"Duyệt đề tài",exact:true})).toBeDisabled();
  await dialog.getByRole("combobox").selectOption("other");
  await expect(dialog.getByRole("button",{name:"Duyệt đề tài",exact:true})).toBeEnabled();
});

test("UI: hồ sơ GV có bộ môn, khoa; mã ngoài phạm vi không hiện tên truyền qua link", async ({page}) => {
  await mock(page, path => path === "/lecturers" ? [{id:"gv",display_name:"Giảng viên kiểm thử",lecturer_code:"GV-UI",department_name:"Bộ môn kiểm thử",faculty_name:"Khoa kiểm thử"}] : [], "STUDENT");
  await page.goto("/lecturers/gv");
  await expect(page.getByRole("heading",{name:"Giảng viên kiểm thử",exact:true})).toBeVisible();
  await expect(page.getByText("GV-UI · Bộ môn kiểm thử",{exact:true})).toBeVisible();
  await expect(page.getByText("Khoa kiểm thử",{exact:true})).toBeVisible();
  await page.goto("/lecturers/outside");
  await expect(page.getByRole("alert")).toContainText("Không tìm thấy");
  await expect(page.getByRole("heading",{name:"Giảng viên kiểm thử",exact:true})).toHaveCount(0);
});

test("UI: GV góp ý chéo thấy tiến độ, không có nút vào tài liệu ngoài quyền", async ({page}) => {
  await mock(page, path => path === "/theses" ? ["thesis","other"].map(id=>({id,title:"Khóa luận góp ý chéo "+id,state:"IN_PROGRESS",round_label:"UI-ROUND",advisor_name:"GVHD",advisor_history:[],members:[],actions:["view","progress:view","progress:comment"]})) : [], "LECTURER");
  await page.goto("/progress");
  await expect(page.locator("#main-content").getByRole("link",{name:"Xem mốc & báo cáo định kỳ",exact:true})).toHaveCount(2);
  await expect(page.getByRole("link",{name:"Mở tài liệu và phiên bản",exact:true})).toHaveCount(0);
  await expect(page.getByRole("link",{name:"Mở đề cương khóa luận",exact:true})).toHaveCount(0);
  await page.goto("/documents");
  await expect(page.getByRole("heading",{name:"Chưa có khóa luận trong phạm vi của bạn",exact:true})).toBeVisible();
});
