// UI regression checks against the production bundle with synthetic API responses.
// Run after npm run build --prefix frontend. Does not access any database.
import { createRequire } from 'node:module';
import { readFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'frontend/package.json'));
const { chromium, expect } = require('@playwright/test');
const { default: AxeBuilder } = require('@axe-core/playwright');
const browser = await chromium.launch({headless:true, ...(process.env.UI_CHROME_PATH ? {executablePath:process.env.UI_CHROME_PATH} : {})});
const member = {student_id:'s1',display_name:'Nguyễn Minh Anh',student_code:'SV001',is_coordinator:true,active:true,consent_status:'ACCEPTED',can_upload_evidence:true};
const topic = {id:'t1',code:'DT-001',title:'Nền tảng quản lý khóa luận và cộng tác học thuật',description:'Nghiên cứu quy trình đăng ký, theo dõi tiến độ và quản lý tài liệu.',round_id:'r1',round_label:'2026–2027',state:'APPROVED',row_version:1,proposer_type:'LECTURER',proposer_user_id:'gv1',receiving_lecturer_id:'l1',receiving_lecturer_name:'Trần Hoàng Nam',requirements:[],title_versions:[],registered_member_count:1,max_students:3,available:true};
const thesis = {id:'h1',title:topic.title,state:'ACTIVE',row_version:1,round_id:'r1',round_label:topic.round_label,members:[member],advisor_name:'Trần Hoàng Nam',advisor_history:[],cross_reviewers:[],actions:['proposal:view','document:view','progress:view','document:review','progress:review','proposal:review','work:view']};
const version = {id:'v1',version_no:1,row_version:1,state:'SUBMITTED',file_name:'bao-cao-nghien-cuu.pdf',byte_size:2048,sha256:'abc123',scan_state:'QUARANTINED',submitted_by_name:member.display_name,submitted_at:'2026-10-20T08:00:00Z',reviews:[]};
const registration = {id:'g1',topic_id:topic.id,topic_code:topic.code,topic_title:topic.title,state:'SUBMITTED',topic_state:'APPROVED',row_version:1,members:[member],expected_member_count:3,receiving_lecturer_name:thesis.advisor_name,receiving_lecturer_user_id:'u1',proposer_type:'LECTURER'};
let checked = 0;
await mkdir(path.join(root,'tmp/ui-review'),{recursive:true});
try {
  for (const role of (process.env.UI_ROLES?.split(',') || ['STUDENT','LECTURER','HEAD','ADMIN'])) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const errors=[]; page.on('pageerror', e=>{errors.push(e.message); if(process.env.UI_DEBUG==="1") console.log('PAGEERROR '+e.message+' '+e.stack);});
    await page.route('**/*',async route=>{
      const url=new URL(route.request().url());
      if(url.pathname.startsWith('/api/v1/')) {
        const key=url.pathname.slice(7);
        const actions=role==='ADMIN'?['account:manage','eligibility:view']:role==='HEAD'?['topic:department_decide','registration:department_finalize']:role==='STUDENT'?['registration:create']:['topic:create'];
        let data=[];
        if(key==='/me/context') data={user_id:'u1',base_role:role==='HEAD'?'LECTURER':role,actions,display_name:member.display_name,student_id:'s1',student_code:'SV001',csrf_token:'synthetic',email:'synthetic@example.test',can_change_password:true,lecturer_duties:[]};
        else if(key==='/rounds/open') data=[{id:'r1',label:'Năm học 2026–2027',academic_year:'2026–2027',code:'KLTN-26-27-D01',closes_at:'2026-12-01T08:00:00Z'}];
        else if(key==='/topics') data=[{...topic,state:role==='HEAD'?'SUBMITTED':'APPROVED'}];
        else if(key==='/topic-registrations') data=[registration];
        else if(key==='/lecturers') data=[{id:'l1',display_name:thesis.advisor_name,lecturer_code:'GV001'}];
        else if(key==='/admin/lecturers') data={items:[],delivery_mode:'',mail_ready:false};
        else if(key==='/theses') data=[thesis];
        else if(key==='/theses/h1') data=thesis;
        else if(key.endsWith('/proposal')) data={id:'p1',state:'SUBMITTED',row_version:1,current_version_no:1,versions:[version],reviewers:[]};
        else if(key.endsWith('/documents')) data=[{id:'d1',title:'Báo cáo nghiên cứu',document_type:'REPORT',versions:[version]}];
        else if(key.endsWith('/milestones')) data=[{id:'m1',title:'Báo cáo giữa kỳ',code:'GK',state:'OPEN',version_no:1,due_at:'2026-11-01T08:00:00Z',expected_ratio:50}];
        else if(key.endsWith('/progress-reports')) data=[{...version,milestone_id:'m1',summary:'Đã hoàn thiện phân tích và thiết kế.',reported_ratio:50}];
        else if(key==='/admin/rounds') data=[{id:'r1',code:'2026-D1',state:'OPEN',round_type:'MAIN',academic_year_code:'2026–2027',opens_at:'2026-09-01T08:00:00Z',closes_at:'2026-12-01T08:00:00Z'}];
        else if(key==='/admin/users') data=[{id:'u2',email:'lecturer@example.test',base_role:'LECTURER',status:'ACTIVE',verified:true}];
        else if(key==='/me/round-assignments') data=['ELIGIBILITY_IMPORTER','ELIGIBILITY_VERIFIER'].map(assignment_type=>({round_id:'r1',round_code:'2026-D1',assignment_type}));
        else if(key==='/rounds/r1/roster') data=[{...member,snapshot_id:'e1',state:'SUBMITTED',account_status:'ACTIVE',email:'synthetic@example.test'}];
        return route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
      }
      const name=/^\/(assets|fonts)\//.test(url.pathname)?url.pathname.slice(1):'index.html';
      try {return route.fulfill({contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':name.endsWith('.ttf')?'font/ttf':name.endsWith('.png')?'image/png':'text/html',body:await readFile(path.join(root,'frontend/dist',name))});} catch {return route.fulfill({status:404,body:''});}
    });
    const routes=role==='ADMIN'?['/','/administration','/rounds','/roster']:['/','/topics','/registrations','/theses','/theses/h1?section=overview','/theses/h1?section=proposal','/theses/h1?section=progress','/theses/h1?section=documents','/account','/lecturers/l1','/ai'];
    for(const width of (process.env.UI_WIDTHS?.split(',').map(Number) || [360,768,1440])) {
      await page.setViewportSize({width,height:960});
      for(const route of routes) { if(process.env.UI_ONLY_ROUTE && route!==process.env.UI_ONLY_ROUTE) continue; if(process.env.UI_DEBUG==="1") console.log("CHECK "+role+" "+width+" "+route);
        await page.goto('http://ui.test'+route);
        if(process.env.UI_DEBUG==="1") console.log("PAGE "+page.url()+" | "+(await page.locator("body").innerText()).slice(0,400));
        await expect(page.locator('h1')).toBeVisible();
        await page.waitForTimeout(100);
        expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${role} ${route} ${width}: horizontal overflow`).toBe(true);
        const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
        expect(result.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)})),`${role} ${route} ${width}: accessibility`).toEqual([]);
        if(route==='/topics') {
          await page.getByRole('button',{name:role==='HEAD'?'Xem và duyệt':'Xem chi tiết',exact:true}).click();
          await expect(page.getByRole('dialog')).toBeVisible();
          await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).toHaveCount(0);
        }
        if(width===1440 && (route==='/' || route==='/topics' || route==='/theses/h1?section=documents' || route==='/roster')) await page.screenshot({path:path.join(root,'tmp/ui-review',`${role}-${route==='/'?'overview':route==='/topics'?'topics':route==='/roster'?'roster':'documents'}.png`),fullPage:true});
        checked++;
      }
    }
    expect(errors).toEqual([]);
    await context.close();
    console.log(`${role}: pages, responsive, accessibility and dialog checks passed`);
  }
  console.log(`PASS: ${checked} page/viewport combinations (synthetic API; no backend integration).`);
} finally { await browser.close(); }
