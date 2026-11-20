import {expect, test, type Page} from "@playwright/test";

const accounts = JSON.parse(process.env.KLTN_E2E_ACCOUNTS_JSON || "{}");
const thesis = "/theses/" + process.env.KLTN_E2E_ARCHIVE_THESIS;
const lecturer = "/lecturers/" + process.env.KLTN_E2E_LECTURER_ID;
const detail = "/evaluation/" + process.env.KLTN_E2E_ARCHIVE_THESIS;
const common = ["/", "/account", "/activity", "/notifications", "/lecturers", lecturer, "/topics", "/forms"];
const workflow = ["/registrations","/theses","/proposals","/progress","/submissions","/documents",
  "/evaluation",detail,"/defense","/repository","/repository?mode=work","/repository?focus="+process.env.KLTN_E2E_ARCHIVE_THESIS,
  "/changes","/withdrawals","/ai",thesis,thesis+"?section=submissions",thesis+"?section=progress"];
const routes = {
  public: ["/","/account/activation-request","/account/forgot-password","/account/activate","/account/reset-password"],
  admin: [...common,"/lecturers?tab=activation","/administration","/administration/assignments","/rounds","/positions","/reports"],
  sv1: [...common,...workflow,"/planned/expertise"],
  sv3: ["/theses","/proposals","/progress","/submissions","/documents"],
  gv: [...common,...workflow,"/reports"],
  tbm: [...common,...workflow,"/reports","/roster","/review-records","/lecturer-profile-reviews"],
};

const browserName = process.env.KLTN_E2E_MOBILE_BROWSER === "webkit" ? "webkit" : "chromium";
test.use({browserName,isMobile:true, hasTouch:true, locale:"vi-VN", viewport:{width:390,height:844}, reducedMotion:"reduce"});

async function checkLayout(page: Page, name: string, scope: string) {
  for (const [width,height] of [[320,568],[360,800],[375,812],[390,844],[430,932],[768,1024],[844,390]]) {
    await page.setViewportSize({width,height});
    const issues = await page.evaluate(async ({scope,width})=>{
      await new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve())));
      const problems: string[] = [];
      const root = document.querySelector(scope)!;
      if (document.documentElement.scrollWidth > width+1) {
        problems.push("page width "+document.documentElement.scrollWidth);
        const textNodes = document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
        while(textNodes.nextNode() && problems.length<5) {
          const node=textNodes.currentNode, parent=node.parentElement;
          if(!parent || !node.textContent?.trim() || !parent.checkVisibility({visibilityProperty:true})) continue;
          const range=document.createRange();
          range.selectNodeContents(node);
          if(range.getBoundingClientRect().right>width+1) problems.push(parent.tagName+"."+parent.className+" "+node.textContent.trim().slice(0,48));
        }
      }
      if (document.querySelector(".app-shell__main")?.getBoundingClientRect().left) problems.push("drawer displaces main");
      if(root.getAttribute("role")==="dialog"){
        const box=root.getBoundingClientRect();
        if(box.top < -1 || box.bottom > window.innerHeight+1 || box.left < -1 || box.right >width+1) problems.push("dialog outside viewport");
      }
      const controls = root.querySelectorAll<HTMLElement>("button,a,input,select,textarea,summary,h1,h2");
      for (const el of controls) {
        const rect = el.getBoundingClientRect();
        if (!rect.width || !rect.height || !el.checkVisibility({visibilityProperty:true})) continue;
        if (rect.left>=-1 && rect.right<=width+1) continue;
        // A wide table or tab strip can scroll locally when its own frame fits the viewport.
        let scrollable = false;
        for(let parent=el.parentElement; parent && parent!==document.body; parent=parent.parentElement) {
          if (!["auto","scroll"].includes(getComputedStyle(parent).overflowX) || parent.scrollWidth<=parent.clientWidth) continue;
          const bounds=parent.getBoundingClientRect();
          if(bounds.left>=-1 && bounds.right<=width+1) {scrollable=true; break;}
        }
        if (!scrollable) problems.push(el.tagName+"."+el.className+" in "+el.parentElement?.className+" "+(el.getAttribute("aria-label")||el.textContent||"").trim().slice(0,32));
      }
      return problems.slice(0,8);
    },{scope,width});
    expect.soft(issues,name+" at "+width+"×"+height).toEqual([]);
  }
}

for (const [role, paths] of Object.entries(routes)) {
  test("Bố cục di động · "+role, async ({page},info)=>{
    test.setTimeout(210000);
    const errors: string[] = [];
    page.on("pageerror",err=>errors.push(err.message));
    if (role!=="public") {
      await page.goto("/");
      await page.getByLabel("Email",{exact:true}).fill(accounts[role].email);
      await page.getByLabel("Mật khẩu",{exact:true}).fill(accounts[role].password);
      await page.getByRole("button",{name:"Đăng nhập",exact:true}).click();
      await expect(page.getByRole("heading",{name:"Tổng quan",exact:true})).toBeVisible();
      await page.waitForLoadState("networkidle");
    }
    for(const path of paths) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const destination = new URL(page.url()).pathname;
      const singleThesis = ["/theses","/proposals","/progress","/submissions","/documents"].includes(path);
      expect(singleThesis ? [path,thesis] : [path.split("?")[0]],path).toContain(destination);
      await expect(page.getByRole("heading").first()).toBeVisible();
      const scope = role==="public"?"#root":"#main-content";
      if(role!=="public") await expect(page.locator(scope).getByRole("alert")).toHaveCount(0);
      await checkLayout(page,role+" "+path,scope);
      if(role==="tbm" && path==="/defense"){
        await page.getByRole("button",{name:"Lập hội đồng mới",exact:true}).click();
        await expect(page.getByRole("combobox",{name:"Chủ tịch",exact:true})).toBeVisible();
        await checkLayout(page,"Lập hội đồng",'[role="dialog"]');
        await page.getByRole("button",{name:"Đóng",exact:true}).click();
        await page.getByRole("button",{name:/^Lịch & kết quả/}).click();
        await checkLayout(page,"Lịch và kết quả",scope);
      }
      if(role==="gv" && path==="/account"){
        await page.getByRole("button",{name:"Cập nhật hồ sơ",exact:true}).click();
        await expect(page.getByLabel("Họ và tên",{exact:true})).toBeVisible();
        await checkLayout(page,"Sửa hồ sơ GV",scope);
      }
      if(role==="gv" && path==="/ai"){
        for(const tab of ["Tìm đề tài tương đồng","Đối chiếu báo cáo"]){
          await page.getByRole("button",{name:tab,exact:true}).click();
          await checkLayout(page,tab,scope);
        }
      }
      if ((role==="admin" && ["/activity","/administration","/lecturers"].includes(path)) ||
          (role==="tbm" && path==="/defense") || (role==="sv1" && path==="/repository?mode=work")) {
        await page.setViewportSize({width:390,height:844});
        await page.screenshot({path:info.outputPath(path.replace(/[^a-z]+/g,"-")+"-mobile.png")});
      }
    }
    if(role==="admin") {
      await page.goto("/lecturers");
      await page.setViewportSize({width:320,height:568});
      const firstRow = page.getByRole("row").filter({has:page.getByRole("button",{name:/^Xem chi tiết /})}).first();
      const detailButton = firstRow.getByRole("button",{name:/^Xem chi tiết /});
      const box = await detailButton.boundingBox();
      expect(box).toBeTruthy();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x+box!.width).toBeLessThanOrEqual(320);
      await detailButton.tap();
      await expect(page.getByRole("dialog")).toBeVisible();
      await checkLayout(page,"Chi tiết giảng viên",'[role="dialog"]');
      await page.getByRole("button",{name:"Đóng",exact:true}).click();
      for (const trigger of [/^Thông báo,/,/^Xem hồ sơ cá nhân$/]) {
        await page.getByRole("button",{name:trigger}).click();
        await expect(page.getByRole("dialog")).toBeVisible();
        await checkLayout(page,String(trigger),'[role="dialog"]');
        await page.keyboard.press("Escape");
        await expect(page.getByRole("dialog")).toHaveCount(0);
      }
    }
    expect(errors).toEqual([]);
  });
}
