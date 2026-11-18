import {useCallback,useEffect,useState,useRef,type FormEvent,type ReactNode,type ComponentProps} from "react";
import {Link,useSearchParams} from "react-router-dom";
import {request,type Context} from "../api";
import {downloadEvaluationFile,when} from "../evaluation";
import {errorMessage} from "../errors";
import "../styles/defense.css";
import PageHeader from "../components/layout/PageHeader";
import DefensePrintPreview from "../components/domain/DefensePrintPreview";
import DefensePrintHistory from "../components/domain/DefensePrintHistory";
import DefenseRegister from "../components/domain/DefenseRegister";
import DefenseCorrections from "../components/domain/DefenseCorrections";
import Dialog from "../components/ui/Dialog";
import {ReadOnlyFilePreview} from "../components/domain/ReviewAttachmentPreview";
import BatchDefenseSchedule from "../components/domain/BatchDefenseSchedule";
import DefenseScheduleNotices,{PublishDefenseSchedule,SharedArrival} from "../components/domain/DefenseScheduleNotices";

type Person={id:string;name:string;role:string};
type Student={id:string;name:string;code:string;class_name?:string;major?:string;major_code?:string;department_id?:string;birth_date?:string;training_cohort?:string};
type Council={id:string;name:string;reference:string;round_id:string;department_id:string;members:Person[];can_manage:boolean;closed_at:string|null;signature?:string};
type Scope={can_manage?:boolean;round_id:string;round_code:string;department_id:string;department_name:string;department_code?:string;faculty_id?:string};
type PlanningThesis={id:string;title:string;round_id:string;department_id:string;advisor_ids?:string[];schedule_reason?:string|null;can_review_eligibility?:boolean};
type Mark={scores:string[];note:string;revision?:number};
type Result={average?:string|null;attendance:{status?:string;reason?:string;bonus?:string;bonus_reference?:string;bonus_evidence_version_id?:string};scores?:Array<string|null>};
type Slot={advisor_name?:string|null;arrival_at?:string|null;report_filename?:string;prior_slot_id?:string|null;absence_decisions?:Record<string,{outcome:string;reference:string;reason:string;recorded_by:string;recorded_at:string;revision:number}>;context_token:string;bonus_evidence:{id:string;name:string;filename?:string}[];id:string;thesis_id:string;title:string;council:Council;starts_at:string;ends_at:string;room:string;version:number;
  roster:Student[];results:Record<string,Result>;marks:Record<string,Record<string,Mark>>;
  role:string|null;lecturer_id:string|null;minutes:{discussion?:string;conclusion?:string;objectives?:string;functions?:string;achievements?:string;recommendations?:string;no_recommendations?:boolean;classifications?:Record<string,string>;oral_comments?:Record<string,Record<string,string>>};finalized_at:string|null;
  can_manage:boolean;schedule_editable:boolean;blockers:string[];council_attendance:{present_ids?:string[];reason?:string}};
type Workspace={export_rounds?:{id:string;code:string}[];academic_majors?:{department_id:string;code:string;name:string}[];scopes:Scope[];scope_catalog?:Scope[];councils:Council[];eligible:{id:string;title:string;round_id:string;department_id:string;extension_starts_at:string|null;extension_until_at:string|null;advisor_ids?:string[]}[];
  planning_theses?:PlanningThesis[];candidates:{id:string;name:string;code:string;department_code?:string;faculty_id?:string|null;specializations?:string[]}[];slots:Slot[];criteria:[string,string,string][];roles:Record<string,string>};
type Act=(path:string,body:unknown,version?:number|string,method?:string)=>Promise<boolean>;
type Download=(path:string,name:string)=>void;
const root="/defense";
const slotPath=(slot:Slot)=>root+"/slots/"+slot.id;
const councilPath=(council:Council)=>root+"/councils/"+council.id;
const dateLocal=(iso:string)=>new Date(Date.parse(iso)+7*3600000).toISOString().slice(0,16);
const option=(value:string,label:string)=><option value={value} key={value}>{label}</option>;
const text=(form:FormData,key:string)=>String(form.get(key)??"");
const searchText = (value: string) => value.toLocaleLowerCase("vi").normalize("NFD").replace(/\p{Diacritic}/gu, "").replace(/đ/g, "d").trim();
const councilContext = (data:Workspace,council:Council) => {
  const scope=(data.scope_catalog??data.scopes).find(s=>s.round_id===council.round_id&&s.department_id===council.department_id);
  return scope ? `${scope.round_code} · ${scope.department_code??scope.department_name}` : "";
};

const hasDrafts=()=>!!document.querySelector('form[data-dirty="true"]');
const mayDiscard=()=>!hasDrafts()||window.confirm("Còn nội dung chưa lưu. Bạn có muốn bỏ nội dung đang nhập?");
function DraftForm({children,onSubmit,onChange,...props}:ComponentProps<"form">) {
  const ref=useRef<HTMLFormElement>(null);
  const [status,setStatus]=useState("");
  useEffect(()=>{
    const form=ref.current!;
    const saved=()=>{form.dataset.dirty="false";setStatus("Đã lưu thành công.");};
    const failed=()=>setStatus("Chưa lưu được. Nội dung đang nhập vẫn được giữ; kiểm tra thông báo rồi thử lại.");
    form.addEventListener("defense:saved",saved);form.addEventListener("defense:error",failed);
    return()=>{form.removeEventListener("defense:saved",saved);form.removeEventListener("defense:error",failed);};
  },[]);
  return <form {...props} ref={ref} onChange={e=>{e.currentTarget.dataset.dirty="true";setStatus("Có nội dung chưa lưu");onChange?.(e);}}
    onSubmit={e=>{document.querySelectorAll('form[data-submitting]').forEach(f=>f.removeAttribute('data-submitting'));e.currentTarget.dataset.submitting="true";setStatus("Đang lưu…");onSubmit?.(e);const form=e.currentTarget;queueMicrotask(()=>form.removeAttribute("data-submitting"));}}>
    {children}{status&&<p className="defense-form-status" role="status">{status}</p>}
  </form>;
}

function AcademicProfiles({slot,data,act,busy}:{slot:Slot;data:Workspace;act:Act;busy:boolean}) {
  return <section className="defense-operation"><h4>Thông tin học vụ sinh viên</h4>
    {slot.roster.map(student=><details key={student.id}><summary>{student.name} · {student.code} · {student.class_name||"Thiếu lớp"} · {student.major||"Thiếu ngành"}</summary>
      {slot.can_manage?<DraftForm className="stack" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);
        act(slotPath(slot)+"/academic-profile/"+student.id,{class_name:text(f,"class_name"),major_code:text(f,"major_code"),birth_date:text(f,"birth_date")||null,training_cohort:text(f,"training_cohort"),source_reference:text(f,"source_reference"),reason:text(f,"reason")},slot.version,"PUT");}}>
        <p>Chỉ bổ sung hoặc đính chính thông tin học vụ; điểm đã chốt giữ nguyên. Hệ thống ghi lịch sử và mã bản xuất mới.</p>
        <div className="defense-form-grid">
          <label>Lớp<input name="class_name" className="input" defaultValue={student.class_name} required maxLength={100}/></label>
          <label>Ngành<select name="major_code" className="input" defaultValue={student.major_code||""} required><option value="">Chọn ngành</option>
            {student.major_code&&!(data.academic_majors??[]).some(m=>m.department_id===student.department_id&&m.code===student.major_code)&&option(student.major_code,student.major||student.major_code)}
            {(data.academic_majors??[]).filter(m=>m.department_id===student.department_id).map(m=>option(m.code,m.code+" · "+m.name))}</select></label>
          <label>Khóa học<input name="training_cohort" className="input" defaultValue={student.training_cohort} placeholder="Ví dụ: 2022–2026" maxLength={50}/></label>
          <label>Ngày sinh<input name="birth_date" className="input" type="date" min="1900-01-01" max={new Date().toISOString().slice(0,10)} defaultValue={student.birth_date}/></label>
        </div>
        <label>Căn cứ đính chính<input className="input" name="source_reference" required minLength={3} maxLength={500}/></label>
        <label>Lý do bổ sung / đính chính<input className="input" name="reason" required minLength={5} maxLength={1000}/></label>
        <button className="btn btn-secondary" disabled={busy}>Lưu thông tin học vụ</button>
      </DraftForm>:<p>TBM hoặc người điều phối bổ sung các thông tin còn thiếu theo hồ sơ sinh viên trước khi xuất bản ký.</p>}
    </details>)}
  </section>;
}

function Card({title,children}:{title:string;children:ReactNode}) {
  return <section className="card"><div className="card-body stack"><h3>{title}</h3>{children}</div></section>;
}

function CouncilForm({data,act,busy,council}:{data:Workspace;act:Act;busy:boolean;council?:Council}) {
  const [chosen,setChosen]=useState<string[]>(["CHAIR","SECRETARY","REVIEWER","REVIEWER","MEMBER"].map((role,i)=>council?.members.filter(m=>m.role===role)[role==="REVIEWER"?i-2:0]?.id??""));
  const roles = ["CHAIR", "SECRETARY", "REVIEWER", "REVIEWER", "MEMBER"];
  const [scopeIndex, setScopeIndex] = useState(Math.max(0, data.scopes.findIndex(r =>
    r.round_id === council?.round_id && r.department_id === council?.department_id)));
  const [checkedTheses, setCheckedTheses] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const scope = council ? data.scopes.find(r => r.round_id === council.round_id && r.department_id === council.department_id) : data.scopes[scopeIndex];
  const catalog=data.scope_catalog??data.scopes;
  const rounds=Array.from(new Map(catalog.map(s=>[s.round_id,s.round_code])).entries());
  const [roundId,setRoundId]=useState(scope?.round_id??rounds[0]?.[0]??"");
  const [customName,setCustomName]=useState<string|null>(council?.name??null);
  const sequence=data.councils.filter(c=>c.round_id===scope?.round_id&&c.department_id===scope?.department_id).length+1;
  const suggestedName=`Hội đồng bảo vệ KLTN ${String(sequence).padStart(2,"0")}${scope?` · ${scope.department_code??scope.department_name} · ${scope.round_code}`:""}`;
  function changeScope(index:number,nextRound=roundId) {
    if(!mayDiscard())return;
    setRoundId(nextRound);setScopeIndex(index);setCheckedTheses([]);setChosen(Array(5).fill(""));setSearch("");setCustomName(null);
  }
  const plans = (data.planning_theses ?? data.eligible).filter(t =>
    t.round_id === scope?.round_id && t.department_id === scope?.department_id);
  const selectedPlans = plans.filter(t => checkedTheses.includes(t.id));
  const query = searchText(search);
  const matchingPlans = plans.filter(t => !checkedTheses.includes(t.id) && searchText(t.title).includes(query));
  const blockedAdvisors = new Set(selectedPlans.flatMap(t => t.advisor_ids ?? []));
  const hasAdvisorConflict = chosen.some(id => blockedAdvisors.has(id));
  const isGuest = (candidate: Workspace["candidates"][number]) => !!scope?.faculty_id && candidate.faculty_id !== scope.faculty_id &&
    !(scope.round_code === "SYN-DEMO" && candidate.department_code === "SYN-DEMO-DEP");
  const hasGuest = data.candidates.some(c => chosen.includes(c.id) && isGuest(c));
  const memberSelection = chosen.filter(Boolean).sort().join(",");
  const conflictSelection = [scope?.round_id, scope?.department_id, memberSelection, ...[...checkedTheses].sort()].join("|");
  const candidates = data.candidates.filter(c => scope?.round_code === "SYN-DEMO" || c.department_code !== "SYN-DEMO-DEP").sort((a, b) =>
    Number(isGuest(a)) - Number(isGuest(b)) || Number(b.department_code === scope?.department_code) - Number(a.department_code === scope?.department_code));
  const availableCount = candidates.filter(c => !blockedAdvisors.has(c.id)).length;

  function submit(e:FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form=new FormData(e.currentTarget);
    if (!scope || hasAdvisorConflict || (!council && plans.length > 0 && checkedTheses.length === 0)) return;
    act(council?councilPath(council):root+"/councils",{round_id:scope.round_id,department_id:scope.department_id,name:text(form,"name"),
      reference:text(form,"reference"),thesis_ids:checkedTheses,confirmed_no_conflict:form.has("conflict_checked"),
      confirmed_guests:form.has("guests_checked"),members:roles.map((role,i)=>({role,lecturer_id:text(form,"lecturer"+i)}))},council?.signature,council?"PUT":"POST");
  }
  return <Card title={council?"Điều chỉnh hội đồng":"Thông tin hội đồng"}><DraftForm className="stack defense-council-form" onSubmit={submit}>
    <label>Đợt KLTN<select name="round" className="input" value={roundId} disabled={!!council}
      onChange={e=>changeScope(data.scopes.findIndex(s=>s.round_id===e.target.value),e.target.value)}>
      {rounds.map(([id,code])=>option(id,code))}
    </select></label>
    <label>Bộ môn<select name="scope" className="input" value={scope?.round_id===roundId?scopeIndex:""} disabled={!!council}
      onChange={e=>changeScope(Number(e.target.value))}>
      <option value="" disabled>Chọn bộ môn được phân công</option>
      {catalog.filter(r=>r.round_id===roundId).map(r=>{
        const index=data.scopes.findIndex(s=>s.round_id===r.round_id&&s.department_id===r.department_id);
        return <option key={r.round_id+r.department_id} value={index<0?r.round_id+r.department_id:String(index)} disabled={index<0}>
          {[r.department_code==="SYN-DEMO-DEP"?null:r.department_code,r.department_name,index<0?"Chưa được phân quyền":null].filter(Boolean).join(" · ")}
        </option>;
      })}
    </select></label>
    <p className="defense-wide text-muted">Bộ môn hiển thị theo đợt đã chọn. Mục “Chưa được phân quyền” cần Admin giao nhiệm vụ hoặc kiểm tra chức vụ TBM trước khi lập hội đồng.</p>
    <fieldset className="defense-planning">
      <legend>Đề tài đối chiếu thành phần ({checkedTheses.length} đã chọn)</legend>
      <p>Chọn một hoặc nhiều đề tài để loại GVHD của các đề tài đó. Mỗi đề tài sẽ có giờ và phòng riêng ở bước xếp lịch.</p>
      {plans.length ? <>
        <div className="defense-plan-search">
          <label>Tìm đề tài<input className="input" type="search" placeholder="Nhập một phần tên đề tài" value={search} onChange={e=>setSearch(e.target.value)}/></label>
          <label>Thêm đề tài<select className="input" value="" disabled={!matchingPlans.length || checkedTheses.length >= 100}
            onChange={e=>{const id=e.target.value; if(id) setCheckedTheses(ids=>[...ids,id]);}}>
            <option value="">{matchingPlans.length ? `Chọn trong ${matchingPlans.length} đề tài` : "Không có đề tài phù hợp"}</option>
            {matchingPlans.map(t=>option(t.id,t.title))}
          </select></label>
        </div>
        {selectedPlans.length > 0 && <details className="defense-selected-plans">
          <summary>Xem đề tài đã chọn ({selectedPlans.length})</summary>
          <ul>{selectedPlans.map(t=><li key={t.id}><span>{t.title}</span><button type="button" className="btn btn-secondary btn-sm"
            aria-label={`Bỏ đề tài ${t.title}`} onClick={()=>setCheckedTheses(ids=>ids.filter(id=>id!==t.id))}>Bỏ</button></li>)}</ul>
        </details>}
      </> : <p>Chưa có đề tài trong phạm vi này. Có thể lập danh sách hội đồng theo quyết định và xếp lịch sau.</p>}
    </fieldset>
    <label>Tên hội đồng<input aria-label="Tên hội đồng" name="name" value={customName??suggestedName} onChange={e=>setCustomName(e.target.value)} className="input" minLength={3} maxLength={200} required/><small>Gợi ý để phân biệt các hội đồng trong cùng đợt; có thể sửa theo quyết định thành lập. Tên này dùng trên lịch và biểu mẫu.</small></label>
    <label>Số quyết định hoặc căn cứ phân công<input name="reference" defaultValue={council?.reference} className="input" minLength={3} maxLength={300} required/></label>
    {availableCount < roles.length && <p className="alert alert-warning">Có {availableCount}/{roles.length} giảng viên phù hợp với các đề tài đã chọn. Cần thêm giảng viên có tài khoản hoạt động hoặc điều chỉnh nhóm đề tài.</p>}
    <fieldset className="defense-planning defense-member-grid"><legend>Thành phần hội đồng · 5 giảng viên</legend>{roles.map((role,i)=><label key={i}>{data.roles[role]}{role==="REVIEWER"?` ${i-1}`:""}
      <select name={"lecturer"+i} className="input" value={chosen[i]} onChange={e=>setChosen(values=>values.map((v,index)=>index===i?e.target.value:v))} required>
        <option value="">Chọn giảng viên</option>
        {candidates.map(c=>{
          const usedIndex = chosen.findIndex((id, index) => id === c.id && index !== i);
          const unavailable = blockedAdvisors.has(c.id) ? "GVHD của đề tài đã chọn" : usedIndex >= 0 ? "Đã chọn ở vai trò khác" : "";
          return <option key={c.id} value={c.id} disabled={!!unavailable}>
            {[c.name, c.code, c.department_code === "SYN-DEMO-DEP" ? "Giảng viên demo" : c.department_code, isGuest(c) ? "Ngoài Khoa" : c.department_code !== scope?.department_code ? "Khác bộ môn" : "", c.specializations?.slice(0, 2).join(", "),
              unavailable].filter(Boolean).join(" · ")}
          </option>;
        })}
      </select>
    </label>)}</fieldset>
    {hasAdvisorConflict && <p className="alert alert-danger" role="alert">Hãy thay thành viên đang hướng dẫn một đề tài đã chọn.</p>}
    {checkedTheses.length>0?<label className="defense-check"><input key={conflictSelection} name="conflict_checked" type="checkbox" required/>Đã đối chiếu thành viên không có quan hệ thân nhân với SV của các đề tài đã chọn.</label>:<p className="text-muted">Hội đồng chưa gắn đề tài. Sẽ đối chiếu quan hệ thân nhân với SV khi xếp lịch cho từng đề tài.</p>}
    {hasGuest && <label className="defense-check"><input key={memberSelection} name="guests_checked" type="checkbox" required/>Đã đối chiếu người được mời ngoài Khoa với quyết định ghi trên.</label>}
    <div className="flex gap-3">
      <button className="btn btn-primary" disabled={busy || !scope || hasAdvisorConflict || (!council && plans.length > 0 && checkedTheses.length === 0)}>{council?"Lưu điều chỉnh hội đồng":"Tạo hội đồng"}</button>
    </div>
  </DraftForm></Card>;
}

function ScheduleForm({data,act,busy,slot,supplementary}:{data:Workspace;act:Act;busy:boolean;slot?:Slot;supplementary?:Slot}) {
  const fixedTopic = supplementary ?? (slot?.prior_slot_id ? slot : undefined);
  const available=data.councils.filter(c=>c.can_manage&&!c.closed_at&&(!fixedTopic||
    (c.round_id===fixedTopic.council.round_id&&c.department_id===fixedTopic.council.department_id)));
  const [councilId,setCouncilId]=useState(slot?.council.id??"");
  const [thesisId,setThesisId]=useState(slot?.thesis_id??supplementary?.thesis_id??"");
  const selected=data.eligible.find(t=>t.id===thesisId);
  const council=available.find(c=>c.id===councilId);
  const taken=new Set(data.slots.filter(s=>s.id!==slot?.id).map(s=>s.thesis_id));
  const hasConflict = (t: PlanningThesis) => council?.members.some(m => t.advisor_ids?.includes(m.id));
  const options = fixedTopic
    ? [data.planning_theses?.find(t=>t.id===fixedTopic.thesis_id) ?? {id:fixedTopic.thesis_id,title:fixedTopic.title,round_id:fixedTopic.council.round_id,department_id:fixedTopic.council.department_id}]
    : data.eligible.filter(t=>t.round_id===council?.round_id&&t.department_id===council?.department_id&&
      !taken.has(t.id));
  const theses = options.filter(t => !hasConflict(t));
  const pending = (data.planning_theses ?? []).filter(t => t.round_id === council?.round_id && t.department_id === council?.department_id &&
    t.schedule_reason && !taken.has(t.id));
  function submit(e:FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form=new FormData(e.currentTarget);
    const end=e.currentTarget.elements.namedItem("end") as HTMLInputElement;
    if (!council || !theses.some(t=>t.id===text(form,"thesis"))) return;
    if(text(form,"end")<=text(form,"start")){end.setCustomValidity("Giờ kết thúc phải sau giờ bắt đầu.");end.reportValidity();return;}
    act(slot?slotPath(slot):root+"/slots",{council_id:councilId,thesis_id:text(form,"thesis"),
      starts_at:text(form,"start")+":00+07:00",ends_at:text(form,"end")+":00+07:00",arrival_at:text(form,"arrival")?text(form,"arrival")+":00+07:00":null,room:text(form,"room"),prior_slot_id:supplementary?.id??slot?.prior_slot_id??null,thesis_member_ids:form.getAll("member"),confirmed_no_conflict:form.has("conflict_checked")},
      slot?.version,slot?"PUT":"POST");
  }
  return <DraftForm className="stack defense-schedule-form" onSubmit={submit}>
    <label>Hội đồng<select className="input" value={councilId} required onChange={e=>{setCouncilId(e.target.value);setThesisId(fixedTopic?.thesis_id??thesisId);}}>
      <option value="" disabled>Chọn hội đồng</option>{available.map(c=>option(c.id,c.name.includes(councilContext(data,c).split(" · ")[0])?c.name:`${c.name} · ${councilContext(data,c)}`))}</select></label>
    <label>Đề tài đủ điều kiện<select key={councilId} name="thesis" className="input" required disabled={!council || !theses.length} value={theses.some(t=>t.id===thesisId)?thesisId:""} onChange={e=>setThesisId(e.target.value)}><option value="" disabled>{!council ? "Chọn hội đồng trước" : theses.length ? "Chọn đề tài đủ điều kiện" : "Chưa có đề tài đủ điều kiện"}</option>
      {theses.map(t=>option(t.id,t.title))}</select></label>
    <details className="defense-wide"><summary>Vì sao đề tài chưa có trong danh sách?</summary><p>Đề tài phải cùng đợt và bộ môn với hội đồng; mọi SV đang thực hiện đã được TBM chốt đủ điều kiện trên bản báo cáo hiện tại; hồ sơ sẵn sàng bảo vệ (hoặc gia hạn còn hiệu lực), chưa có lịch khác và không có GVHD trong hội đồng. Giờ, phòng và lịch giảng viên tiếp tục được kiểm tra khi lưu.</p></details>
    {(!slot||slot.council.id!==councilId||slot.thesis_id!==thesisId)&&<label className="defense-check"><input key={councilId+thesisId} name="conflict_checked" type="checkbox" required/>Đã đối chiếu thành viên hội đồng không có quan hệ thân nhân với các SV của đề tài này.</label>}
    {supplementary&&<fieldset><legend>Sinh viên được Khoa cho bảo vệ bổ sung</legend>{supplementary.roster.filter(r=>supplementary.absence_decisions?.[r.id]?.outcome==="SUPPLEMENTARY"&&!data.slots.some(s=>s.prior_slot_id===supplementary.id&&s.roster.some(m=>m.id===r.id))).map(r=><label className="defense-check" key={r.id}><input type="checkbox" name="member" value={r.id}/>{r.name} · {r.code}</label>)}<p>Chỉ xếp lịch cho các SV được chọn. Điểm của thành viên đã bảo vệ được giữ nguyên.</p></fieldset>}
    {council && options.some(hasConflict) && <p>Đã loại đề tài có GVHD trong hội đồng. Chọn hội đồng khác cho đề tài đó.</p>}
    {council&&!theses.length&&<p>Chưa có đề tài phù hợp trong phạm vi hội đồng.</p>}
    {council&&pending.length>0&&<details className="defense-operation"><summary>Hồ sơ cần xử lý trước khi xếp lịch ({pending.length})</summary><ul>{pending.map(t=><li key={t.id}><strong>{t.title}</strong> · {t.schedule_reason} {t.can_review_eligibility&&<Link to={`/evaluation/${t.id}`}>Mở xét điều kiện</Link>}</li>)}</ul></details>}
    {selected?.extension_until_at&&<p className="alert alert-info">Hồ sơ đã gia hạn: {when(selected.extension_starts_at)} → <strong>{when(selected.extension_until_at)}</strong>. Chọn kỳ bảo vệ thực tế của Khoa trong khoảng này; không kéo dài hạn khi đổi lịch.</p>}
    {slot&&<p>Khi lưu, hệ thống báo lịch mới cho các tài khoản liên quan. Nếu thay đề tài hoặc hội đồng, người không còn tham gia cũng nhận thông báo.</p>}
    <label>Bắt đầu (giờ Việt Nam)<input name="start" className="input" type="datetime-local" min={selected?.extension_starts_at?dateLocal(selected.extension_starts_at):undefined} max={selected?.extension_until_at?dateLocal(selected.extension_until_at):undefined} defaultValue={slot?dateLocal(slot.starts_at):""} required/></label>
    <label>Kết thúc (giờ Việt Nam)<input name="end" onInput={e=>e.currentTarget.setCustomValidity("")} className="input" type="datetime-local" min={selected?.extension_starts_at?dateLocal(selected.extension_starts_at):undefined} max={selected?.extension_until_at?dateLocal(selected.extension_until_at):undefined} defaultValue={slot?dateLocal(slot.ends_at):""} required/></label>
    <label>Giờ tập trung (giờ Việt Nam)<input name="arrival" className="input" type="datetime-local" defaultValue={slot?.arrival_at?dateLocal(slot.arrival_at):""}/></label>
    <label className="defense-wide">Phòng bảo vệ<input name="room" className="input" defaultValue={slot?.room} required minLength={2} maxLength={200}/></label>
    <button className="btn btn-primary" disabled={busy||!theses.some(t=>t.id===thesisId)}>{slot?"Lưu thay đổi lịch":"Lưu lịch"}</button>
  </DraftForm>;
}

function StudentMarks({slot,student,data,act,download,busy,mode,onRecord}:{slot:Slot;student:Student;data:Workspace;act:Act;download:Download;busy:boolean;mode:string;onRecord:()=>void}) {
  const [grader,setGrader]=useState(slot.lecturer_id??"");
  const result=slot.results[student.id];
  const recorded=result?.attendance;
  const mark=slot.marks[student.id]?.[grader];
  const endpoint=slotPath(slot);
  const [preview,setPreview]=useState<string[]>(mark?.scores??Array(12).fill(""));
  const formId=`ballot-${slot.id}-${student.id}`;
  const [base,setBase]=useState({revision:mark?.revision??0,token:slot.context_token});
  useEffect(()=>{
    if(document.getElementById(formId)?.dataset.dirty!=="true"){
      setPreview(mark?.scores??Array(12).fill(""));setBase({revision:mark?.revision??0,token:slot.context_token});
    }
  },[mark?.revision,slot.context_token,grader,formId]);
  const cents=preview.reduce((sum,value)=>sum+Math.round((Number(value)||0)*100),0)+Math.round(Number(recorded?.bonus??0)*100);
  const canExport=slot.can_manage||["CHAIR","SECRETARY"].includes(slot.role??"");
  function submit(path:string,e:FormEvent<HTMLFormElement>,payload:(form:FormData)=>unknown) {
    e.preventDefault();act(endpoint+path,payload(new FormData(e.currentTarget)),slot.version,"PUT");
  }
  return <Card title={student.name+" · "+student.code}>
    <p>{recorded?.status==="PRESENT"?"Có mặt":recorded?.status==="ABSENT"?"Vắng":"Chưa xác nhận có mặt"}
      {recorded?.reason&&" · "+recorded.reason}{result?.average&&" · Điểm trung bình "+result.average}
      {result?.scores&&" · Đã có "+result.scores.filter(s=>s!==null).length+"/"+result.scores.length+" phiếu"}</p>
    <div hidden={mode!=="attendance"}>
    {!slot.finalized_at&&slot.role==="SECRETARY"&&<DraftForm className="stack" onSubmit={e=>submit("/attendance/"+student.id,e,f=>({status:text(f,"status"),reason:text(f,"reason")}))}>
      <label>Điểm danh<select className="input" name="status" defaultValue={recorded?.status??"PRESENT"}>
        {option("PRESENT","Có mặt")}{option("ABSENT","Vắng")}</select></label>
      <label>Lý do nếu vắng<input name="reason" className="input" maxLength={500} defaultValue={recorded?.reason}/></label>
      {!slot.council_attendance.present_ids?.length&&<p className="text-muted">Mở phiên bằng điểm danh hội đồng trước, rồi ghi nhận sinh viên có mặt.</p>}
      <button className="btn btn-secondary" disabled={busy||Date.now()<Date.parse(slot.starts_at)||!slot.council_attendance.present_ids?.length}>Lưu điểm danh</button>
    </DraftForm>}
    {slot.role&&slot.bonus_evidence?.length>0&&<details className="defense-operation"><summary>Xem tài liệu minh chứng đã nộp</summary>{slot.bonus_evidence.map(f=><button key={f.id} className="btn btn-secondary" onClick={()=>download(endpoint+"/evidence/"+f.id,f.filename??f.name)}>{f.name}</button>)}</details>}
    <p className="alert alert-info">Điểm thưởng đã được TBM duyệt: <strong>{recorded?.bonus??"0"} / 1</strong>{recorded?.bonus_reference&&` · Căn cứ: ${recorded.bonus_reference}`}. Mức này tự áp dụng vào phiếu chấm từng thành viên Hội đồng.</p>
    {!slot.finalized_at&&slot.role==="CHAIR"&&<button className="btn btn-secondary" disabled={busy} onClick={()=>act(endpoint+"/bonus/"+student.id,{points:recorded?.bonus??"0",reference:recorded?.bonus_reference??"",evidence_version_id:recorded?.bonus_evidence_version_id??null},slot.version,"PUT")}>Đã đối chiếu mức thưởng của TBM</button>}

    </div><div hidden={mode!=="marks"}>
    {!slot.finalized_at&&slot.role&&recorded?.status==="PRESENT"&&<details><summary>Phiếu chấm Mẫu 6 · Điểm thưởng {recorded.bonus??"0"}</summary>
      {slot.role==="SECRETARY"&&<label>Người đánh giá<select className="input" value={grader} onChange={e=>{if(!mayDiscard())return;setGrader(e.target.value);setPreview(slot.marks[student.id]?.[e.target.value]?.scores??Array(12).fill(""));}}>
        {slot.council.members.filter(m=>slot.council_attendance.present_ids?.includes(m.id)).map(m=>option(m.id,m.name))}</select></label>}
      <DraftForm key={grader} id={formId} className="stack defense-ballot" onSubmit={e=>submit("/marks",e,f=>({thesis_member_id:student.id,lecturer_id:grader,
        scores:data.criteria.map(([code])=>text(f,code)),note:text(f,"note"),paper_entry_reason:text(f,"paper"),ballot_revision:base.revision,context_token:base.token}))}>
        {data.criteria.map(([code,label,max],i)=><div key={code} className="defense-criterion">{["1.1","2.1","3.1"].includes(code)&&<h4>{code==="1.1"?"1. Hình thức · 2 điểm":code==="2.1"?"2. Nội dung · 4 điểm":"3. Demo và trả lời · 4 điểm"}</h4>}<label>{code} · {label} (tối đa {max})
          <input name={code} className="input" type="number" min={0} max={max} step=".01" value={preview[i]} onChange={e=>setPreview(values=>values.map((v,index)=>index===i?e.target.value:v))} required/></label></div>)}
        {grader!==slot.lecturer_id&&<label>Căn cứ nhập hộ từ phiếu giấy<input name="paper" className="input" minLength={5} maxLength={500} required/></label>}
        <label>Nhận xét<textarea name="note" className="input" defaultValue={mark?.note} maxLength={3000}/></label>
        <p className="defense-score-preview">Tổng dự kiến ({preview.filter(Boolean).length}/12 tiêu chí) · {Math.min(10,Math.floor((cents+5)/10)/10).toFixed(1)} / 10 · gồm điểm thưởng {recorded?.bonus??"0"}</p>
        {(base.revision!==(mark?.revision??0)||base.token!==slot.context_token)&&<aside className="defense-blockers"><p>Dữ liệu đã thay đổi từ khi bạn bắt đầu nhập. Điểm đã lưu hiện tại: {mark?.scores.join(" · ")||"Chưa có phiếu"}. Điểm thưởng hiện tại: {recorded?.bonus??0}.</p><button type="button" className="btn btn-secondary" onClick={()=>{if(window.confirm("Đã đối chiếu dữ liệu mới và muốn tiếp tục lưu nội dung đang nhập?"))setBase({revision:mark?.revision??0,token:slot.context_token});}}>Đã đối chiếu, tiếp tục chỉnh sửa</button></aside>}
        <button className="btn btn-primary" disabled={busy}>Lưu phiếu chấm</button>
      </DraftForm>
    </details>}
    {slot.role&&<details className="defense-operation"><summary>In phiếu chấm trước buổi họp</summary><p>Phiếu trống có sẵn thông tin để chấm giấy; chưa phải bản kết quả đã chốt.</p>{slot.council.members.filter(m=>canExport||m.id===slot.lecturer_id).map(m=><button className="btn btn-secondary" key={m.id} onClick={()=>download(endpoint+"/forms/6?blank=true&student_id="+student.id+"&lecturer_id="+m.id,`Phieu-trong-${student.code}-${m.id}.xlsx`)}>In phiếu trống · {m.name}</button>)}</details>}
    {!slot.role&&<p>Nộp minh chứng công bố khoa học trong Hồ sơ nộp & xét duyệt. GVHD xác nhận đóng góp, TBM duyệt mức thưởng theo từng sinh viên; phiếu chấm tự nhận mức đã duyệt. Chủ tịch đối chiếu trước khi chốt.</p>}
    {!slot.finalized_at&&["CHAIR","SECRETARY"].includes(slot.role??"")&&Object.keys(slot.marks[student.id]??{}).length>0&&<details className="defense-operation"><summary>Hủy phiếu nhập nhầm</summary><DraftForm className="stack" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);if(window.confirm("Hủy hiệu lực phiếu này? Bản cũ vẫn được lưu trong lịch sử."))act(endpoint+"/marks/"+student.id+"/"+text(f,"lecturer")+"/void",{reason:text(f,"reason")},slot.version);}}><label>Phiếu cần hủy<select name="lecturer" className="input">{slot.council.members.filter(m=>slot.marks[student.id]?.[m.id]).map(m=>option(m.id,m.name))}</select></label><label>Lý do<input className="input" name="reason" required minLength={5} maxLength={500}/></label><button className="btn btn-secondary" disabled={busy}>Hủy hiệu lực phiếu</button></DraftForm></details>}
    {slot.role&&slot.role!=="SECRETARY"&&slot.lecturer_id&&!!slot.marks[student.id]?.[slot.lecturer_id]&&<button className="btn btn-secondary" onClick={()=>download(endpoint+"/forms/6?student_id="+student.id+"&lecturer_id="+slot.lecturer_id,"Mau-06-Phieu-cham.xlsx")}>Tải phiếu chấm đã lưu của tôi</button>}
    {slot.role==="SECRETARY"&&recorded?.status==="PRESENT"&&slot.council.members.filter(m=>!!slot.marks[student.id]?.[m.id]).map(m=><DefensePrintPreview key={"preview-"+m.id} endpoint={endpoint+"/forms/6?student_id="+student.id+"&lecturer_id="+m.id} name="Mau-06-Phieu-cham.xlsx" label={"Mẫu 6 · "+m.name+" · "+student.name} record={!!slot.finalized_at} onRecord={onRecord}/>)}
    </div>
  </Card>;
}

function SlotCard({slot,data,act,download,busy,initialTab}:{slot:Slot;data:Workspace;act:Act;download:Download;busy:boolean;initialTab?:string}) {
  const endpoint=slotPath(slot);
  const [tab,setTab]=useState(initialTab||"overview");
  const [history,setHistory]=useState(0);
  const [viewReport,setViewReport]=useState(false);
  const [noRecommendations,setNoRecommendations]=useState(!!slot.minutes.no_recommendations);
  const onRecord=()=>setHistory(value=>value+1);
  useEffect(()=>{if(initialTab)setTab(initialTab);},[initialTab]);
  return <Card title={slot.title}>
    <p>SV · {slot.roster.map(s=>s.name).join(", ")} · GVHD · {slot.advisor_name||"Chưa ghi nhận"}</p>
    <div className="defense-session-head"><strong>{slot.council.name} · {slot.room}</strong><span>Tập trung: {when(slot.arrival_at??slot.starts_at)}<br/>Bảo vệ dự kiến: {when(slot.starts_at)} → {when(slot.ends_at)}</span>
    <button className="btn btn-secondary" onClick={()=>setViewReport(true)}>Xem nhanh báo cáo</button>
    <button className="btn btn-secondary" onClick={()=>download(endpoint+"/report",slot.report_filename??"Bao-cao-bao-ve")}>Tải báo cáo dùng để bảo vệ</button></div>
    <Dialog open={viewReport} title="Báo cáo dùng để bảo vệ" size="lg" onClose={()=>setViewReport(false)}>{viewReport&&<ReadOnlyFilePreview name={slot.report_filename??"Bao-cao.pdf"} endpoint={endpoint+"/report"} label="Báo cáo khóa luận" caption="Đúng phiên bản gắn với lịch bảo vệ. Chỉ xem." backLabel="Đóng báo cáo" onBack={()=>setViewReport(false)}/>}</Dialog>
    {slot.report_filename&&<p>Tệp báo cáo đã gắn lịch: <strong>{slot.report_filename}</strong></p>}
    <nav className="defense-tabs" aria-label="Các bước buổi bảo vệ">{[["overview","Tổng quan"],["attendance","Điểm danh"],["marks","Phiếu chấm"],["minutes","Biên bản"],["results","Kết quả & xuất"]].filter(([id])=>slot.role||id==="overview"||id==="results").map(([id,label])=><button className={"btn "+(tab===id?"btn-primary":"btn-secondary")} aria-pressed={tab===id} key={id} onClick={()=>setTab(id)}>{label}</button>)}</nav>
    <div hidden={tab!=="attendance"}>
    {!slot.finalized_at&&slot.role==="SECRETARY"&&<DraftForm className="stack defense-attendance" onSubmit={e=>{
      e.preventDefault();const form=new FormData(e.currentTarget);
      act(endpoint+"/council-attendance",{present_ids:form.getAll("present"),reason:text(form,"reason")},slot.version,"PUT");
    }}>
      <h4>Điểm danh hội đồng trước khi chấm</h4><p>Cần ít nhất 3/5 người, gồm chủ tịch và thư ký.</p>
      {slot.council.members.map(m=><label key={m.id} className="defense-check"><input type="checkbox" name="present" value={m.id}
        defaultChecked={slot.council_attendance.present_ids?.includes(m.id)??false}/>{data.roles[m.role]} · {m.name}</label>)}
      <label>Ghi nhận thành phần dự họp<input name="reason" className="input" defaultValue={slot.council_attendance.reason} required minLength={5} maxLength={1000}/></label>
      <p className="text-muted">Chỉ mở phiên từ giờ bảo vệ đã xếp. Trước đó, người quản lý vẫn có thể đổi lịch.</p><button className="btn btn-secondary" disabled={busy||Date.now()<Date.parse(slot.starts_at)}>Lưu thành phần dự họp</button>
    </DraftForm>}
    </div><div hidden={tab!=="overview"}>
    {slot.role&&<a className="btn btn-secondary" href={"/activity?resource_type=defense_slot&resource_id="+slot.id}>Xem lịch sử phiên bảo vệ</a>}
    <p>{slot.finalized_at?`Đã chốt v${slot.version} · ${when(slot.finalized_at)}`:"Đã xếp lịch"}{slot.role&&" · "+data.roles[slot.role]}</p>
    {slot.can_manage&&slot.schedule_editable&&<details><summary>Đổi đề tài, giờ, phòng hoặc hủy lịch</summary>
      <ScheduleForm data={data} slot={slot} act={act} busy={busy}/>
      <DraftForm className="stack" onSubmit={e=>{e.preventDefault();const reason=text(new FormData(e.currentTarget),"reason");
        if(window.confirm("Hủy lịch bảo vệ này?"))act(endpoint+"/cancel",{reason},slot.version);}}>
        <label>Lý do hủy lịch<input name="reason" className="input" minLength={5} maxLength={500} required/></label>
        <button className="btn btn-secondary" disabled={busy}>Hủy lịch</button>
      </DraftForm>
    </details>}
    </div><div hidden={tab!=="marks"&&tab!=="attendance"}>
    {slot.roster.map(s=><StudentMarks key={s.id} slot={slot} student={s} mode={tab} data={data} act={act} download={download} busy={busy} onRecord={onRecord}/>)}
    </div><div hidden={tab!=="minutes"}>
    {!slot.finalized_at&&slot.role==="SECRETARY"&&<DraftForm className="stack" onSubmit={e=>{
      e.preventDefault();const f=new FormData(e.currentTarget);
      const oralComments = Object.fromEntries(slot.roster.map(student=>[student.id,Object.fromEntries(
        slot.council.members.map(person=>[person.id,text(f,`oral-${student.id}-${person.id}`).trim()]).filter(([,value])=>value))])
        .filter(([,comments])=>Object.keys(comments).length));
      act(endpoint+"/minutes",{discussion:text(f,"discussion"),conclusion:text(f,"conclusion"),objectives:text(f,"objectives"),functions:text(f,"functions"),achievements:text(f,"achievements"),recommendations:text(f,"recommendations"),no_recommendations:noRecommendations,oral_comments:oralComments,classifications:Object.fromEntries(slot.roster.map(s=>[s.id,text(f,"classification-"+s.id)]).filter(([,value])=>!!value))},slot.version,"PUT");}}>
      <h4>Biên bản Mẫu 9</h4>
      <p>Thư ký ghi biên bản theo nội dung hội đồng đã nghe và thống nhất. Nhận xét trên phiếu chấm tự tổng hợp theo người viết; phần dưới chỉ dùng bổ sung ý kiến phát biểu chưa có trên phiếu. Số phiếu và điểm được tính tự động.</p>
      {[["objectives","Mục tiêu"],["functions","Chức năng"],["achievements","Kết quả đạt được"]].map(([key,label])=><label key={key}>{label}<textarea name={key} className="input" defaultValue={slot.minutes[key as "objectives"]} maxLength={3000}/></label>)}
      <label>Nội dung trao đổi và trả lời câu hỏi<textarea name="discussion" className="input" defaultValue={slot.minutes.discussion} minLength={5} maxLength={10000} required/></label>
      {slot.roster.filter(student=>slot.results[student.id]?.attendance.status==="PRESENT").map(student=><details className="defense-operation" key={student.id}>
        <summary>Nhận xét đã lưu & ý kiến phát biểu bổ sung · {student.name}</summary>
        <p>Phiếu đã lưu tự điền vào Mẫu 9. Ghi thêm ý kiến phát biểu tại buổi họp nếu cần.</p>
        {slot.council.members.filter(person=>slot.council_attendance.present_ids?.includes(person.id)).map(person=><label key={person.id}>
          {data.roles[person.role]} · {person.name} <small>({slot.marks[student.id]?.[person.id]?.note?.trim()?"Đã có nhận xét trên phiếu":"Chưa có nhận xét trên phiếu"})</small>
          {slot.marks[student.id]?.[person.id]?.note&&<span className="defense-saved-comment">{slot.marks[student.id][person.id].note}</span>}
          <textarea className="input" rows={2} maxLength={1500} name={`oral-${student.id}-${person.id}`} defaultValue={slot.minutes.oral_comments?.[student.id]?.[person.id]}/>
        </label>)}
      </details>)}
      <label>Kết luận của Chủ tịch hội đồng<textarea name="conclusion" className="input" defaultValue={slot.minutes.conclusion} minLength={5} maxLength={5000} required/></label>
      <label className="defense-check"><input type="checkbox" checked={noRecommendations} onChange={event=>setNoRecommendations(event.target.checked)}/>Hội đồng xác nhận không có kiến nghị</label>
      <label>Kiến nghị của hội đồng<textarea name="recommendations" className="input" defaultValue={slot.minutes.recommendations} maxLength={5000} disabled={noRecommendations}/></label>
      {slot.roster.filter(s=>slot.results[s.id]?.attendance.status!=="ABSENT").map(s=><label key={s.id}>Xếp loại được hội đồng xác nhận · {s.name}<select name={"classification-"+s.id} className="input" defaultValue={slot.minutes.classifications?.[s.id]??""}><option value="">Chưa ghi nhận</option>{["Xuất sắc","Giỏi","Khá","Trung bình","Không đạt","Chờ xác nhận"].map(v=>option(v,v))}</select></label>)}
      <button className="btn btn-secondary" disabled={busy}>Lưu biên bản</button>
    </DraftForm>}
    </div><div hidden={tab!=="results"&&tab!=="overview"}>
    <div className="defense-results"><table><caption>Đối chiếu kết quả từng sinh viên</caption><thead><tr><th>Sinh viên</th><th>Điểm danh</th><th>Điểm thưởng</th><th>Điểm trung bình</th></tr></thead><tbody>{slot.roster.map(r=><tr key={r.id}><td>{r.name} · {r.code}</td><td>{slot.results[r.id]?.attendance.status==="ABSENT"?"Vắng · chờ xử lý học vụ":slot.results[r.id]?.attendance.status==="PRESENT"?"Có mặt":"Chưa điểm danh"}</td><td>{slot.results[r.id]?.attendance.bonus??"0"} / 1</td><td>{slot.results[r.id]?.average??"Chưa có kết quả"}</td></tr>)}</tbody></table></div>
    {(slot.can_manage||["CHAIR","SECRETARY"].includes(slot.role??""))&&<AcademicProfiles slot={slot} data={data} act={act} busy={busy}/>}
    {slot.finalized_at&&slot.roster.filter(r=>slot.results[r.id]?.attendance.status==="ABSENT").map(r=>{
      const decision=slot.absence_decisions?.[r.id];
      const scheduled=data.slots.some(s=>s.prior_slot_id===slot.id&&s.roster.some(m=>m.id===r.id));
      return <section className="defense-operation" key={r.id}><h4>Xử lý SV vắng · {r.name}</h4>
        <p>{decision?`${decision.outcome==="NOT_PASSED"?"Không đạt do vắng theo quyết định Khoa":scheduled?"Đã xếp lịch bảo vệ bổ sung":"Được phép bảo vệ bổ sung · chờ xếp lịch"} · ${decision.reference} · ${decision.reason} · ${decision.recorded_by} · ${when(decision.recorded_at)}`:"Chờ Khoa ghi nhận quyết định. Hệ thống giữ điểm trống, không tự gán 0."}</p>
        {slot.can_manage&&!scheduled&&<DraftForm className="stack" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);act(endpoint+"/absence/"+r.id,{outcome:text(f,"outcome"),reference:text(f,"reference"),reason:text(f,"reason"),revision:decision?.revision??0});}}>
          <label>Quyết định của Khoa<select name="outcome" className="input" defaultValue={decision?.outcome??""} required><option value="" disabled>Chọn kết quả theo văn bản được đối chiếu</option>{option("NOT_PASSED","Không đạt do vắng")}{option("SUPPLEMENTARY","Cho phép bảo vệ bổ sung")}</select></label>
          <label>Số / căn cứ quyết định<input className="input" name="reference" defaultValue={decision?.reference} required minLength={5} maxLength={300}/></label>
          <label>Lý do<input className="input" name="reason" defaultValue={decision?.reason} required minLength={10} maxLength={1000}/></label><button className="btn btn-primary" disabled={busy}>Ghi nhận quyết định của Khoa</button>
        </DraftForm>}
      </section>;
    })}
    {slot.can_manage&&slot.finalized_at&&slot.roster.some(r=>slot.absence_decisions?.[r.id]?.outcome==="SUPPLEMENTARY"&&!data.slots.some(s=>s.prior_slot_id===slot.id&&s.roster.some(m=>m.id===r.id)))&&<details className="defense-operation"><summary>Xếp lịch bảo vệ bổ sung theo quyết định</summary><ScheduleForm data={data} act={act} busy={busy} supplementary={slot}/></details>}
    {!slot.finalized_at&&slot.blockers.length>0&&<aside className="defense-blockers"><h4>Việc cần hoàn tất trước khi chốt</h4><ul>{slot.blockers.map((text,i)=><li key={i}>{text}</li>)}</ul>
      {slot.role&&<div className="button-row"><button className="btn btn-secondary" onClick={()=>setTab("attendance")}>Mở điểm danh</button><button className="btn btn-secondary" onClick={()=>setTab("marks")}>Mở phiếu chấm</button><button className="btn btn-secondary" onClick={()=>setTab("minutes")}>Mở biên bản</button></div>}</aside>}
    {!slot.finalized_at&&["CHAIR","SECRETARY"].includes(slot.role??"")&&<button className="btn btn-primary" disabled={busy||slot.blockers.length>0} onClick={()=>{if(slot.blockers.length)return;if(hasDrafts()){window.alert("Cần lưu hoặc bỏ các nội dung đang nhập trước khi chốt.");return;}if(window.confirm("Chốt điểm và biên bản để xuất bản ký?"))act(endpoint+"/finalize",{},slot.version);}}>Chốt kết quả bảo vệ</button>}
    {slot.finalized_at&&!slot.council.closed_at&&["CHAIR","SECRETARY"].includes(slot.role??"")&&<details className="defense-operation">
      <summary>Mở lại để GV sửa điểm và xuất lại</summary><DraftForm className="stack" onSubmit={e=>{
        e.preventDefault();const form=new FormData(e.currentTarget);
        act(endpoint+"/reopen-unsigned",{reason:text(form,"reason"),confirm_unsigned:form.get("unsigned")==="on"},slot.version);
      }}><p>Phiên bản cũ được giữ trong lịch sử. Sau sửa cần chốt lại và in đúng phiên bản mới để ký.</p>
        <label>Lý do điều chỉnh<input className="input" name="reason" minLength={5} maxLength={1000} required/></label>
        <label className="defense-check"><input type="checkbox" name="unsigned" required/>Tôi xác nhận hồ sơ này chưa được ký.</label>
        <button className="btn btn-secondary" disabled={busy}>Xác nhận mở lại cho GV cập nhật</button>
      </DraftForm></details>}
    {slot.finalized_at&&(slot.can_manage||slot.role)&&<>
      {slot.role==="SECRETARY"&&<DefensePrintPreview endpoint={endpoint+"/forms/9"} name="Mau-09-Bien-ban.docx" label="Biên bản Mẫu 9" record onRecord={onRecord}/>}
      <DefensePrintHistory endpoint={endpoint+"/prints"} revision={history}/>
    </>}
    </div>
  </Card>;
}

export default function DefensePage({context}:{context:Context}) {
  const [params]=useSearchParams();
  const [data,setData]=useState<Workspace>();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");
  const [filter,setFilter]=useState("");
  const [search,setSearch]=useState("");
  const [refresh,setRefresh]=useState(0);
  const [view,setView]=useState(params.get('section')==='announcements'?'announcements':"schedules");
  useEffect(()=>{if(params.get('section')==='announcements')setView('announcements');else if(params.get('slot')||params.get('focus'))setView('schedules');},[params]);
  const [operation,setOperation]=useState<"council"|"schedule"|null>(null);
  const load=useCallback(async()=>{setData(await request<Workspace>(root,context.user_id));setRefresh(value=>value+1);},[context.user_id]);
  useEffect(()=>{void load().catch(e=>setError(errorMessage(e)));},[load]);
  useEffect(()=>{
    const warn=(e:BeforeUnloadEvent)=>{if(hasDrafts()){e.preventDefault();e.returnValue="";}};
    const link=(e:MouseEvent)=>{if((e.target as Element).closest('a[href]')&&!mayDiscard()){e.preventDefault();e.stopPropagation();}};
    window.addEventListener("beforeunload",warn);document.addEventListener("click",link,true);
    return()=>{window.removeEventListener("beforeunload",warn);document.removeEventListener("click",link,true);};
  },[]);
  const act:Act=async(path,body,version,method="POST")=>{
    if(busy)return false;
    const form=document.querySelector('form[data-submitting="true"]');
    setBusy(true);setError("");setMessage("");
    try {
      await request(path,context.user_id,{method,body:JSON.stringify(body),headers:version?{"If-Match":String(version)}:undefined});
      form?.dispatchEvent(new Event("defense:saved"));
      setMessage("Đã lưu thay đổi.");
      try{await load();}catch{setError("Đã lưu thành công nhưng chưa tải được dữ liệu mới. Bấm Làm mới dữ liệu; không cần gửi lại.");}
      return true;
    }catch(e){setError(errorMessage(e));form?.dispatchEvent(new Event("defense:error"));await load().catch(()=>undefined);return false;}
    finally{form?.removeAttribute("data-submitting");setBusy(false);}
  };
  const download:Download=(path,name)=>{setError("");void downloadEvaluationFile(path,name).catch(e=>setError(errorMessage(e)));};
  const focused=params.get("slot")??params.get("focus");
  const initialTab=params.get("tab")==="results"?"results":undefined;
  const slots=data?.slots.filter(s=>s.id===focused||((!filter||s.council.id===filter)&&searchText(s.title+" "+s.room+" "+s.council.name+" "+s.roster.map(r=>r.name+" "+r.code).join(" ")).includes(searchText(search))))??[];
  useEffect(()=>{if(data&&focused)document.getElementById(`slot-${focused}`)?.scrollIntoView({block:"start"});},[focused,Boolean(data)]);
  return <div className="stack defense-page">
    <PageHeader title="Hội đồng và bảo vệ" description="Hội đồng → lịch bảo vệ → điểm danh → chấm Mẫu 6 → biên bản → chốt và xuất bảng điểm.">
      <button className="btn btn-secondary" disabled={busy} onClick={()=>{void load().catch(e=>setError(errorMessage(e)));}}>Làm mới dữ liệu</button>
    </PageHeader>
    {error&&!operation&&<p role="alert" className="alert alert-danger defense-notice">{error}</p>}
    {message&&<p role="status" className="alert alert-success defense-notice">{message}</p>}
    {!data&&!error&&<p role="status">Đang tải…</p>}
    {data&&<>
      <div className="defense-workspace-bar">
        <nav className="defense-tabs" aria-label="Quản lý bảo vệ">
          <button className={`btn ${view==="councils"?"btn-primary":"btn-secondary"}`} aria-pressed={view==="councils"} onClick={()=>setView("councils")}>Hội đồng ({data.councils.length})</button>
          <button className={`btn ${view==="schedules"?"btn-primary":"btn-secondary"}`} aria-pressed={view==="schedules"} onClick={()=>setView("schedules")}>Lịch & kết quả ({data.slots.length})</button>
          {!!data.export_rounds?.length&&<button className={`btn ${view==="register"?"btn-primary":"btn-secondary"}`} aria-pressed={view==="register"} onClick={()=>setView("register")}>Bảng điểm toàn đợt</button>}
          <button className={`btn ${view==='announcements'?'btn-primary':'btn-secondary'}`} aria-pressed={view==='announcements'} onClick={()=>setView('announcements')}>Danh sách công bố</button>
        </nav>
        <div className="button-row">
          {!!data.scopes.length&&<button className="btn btn-primary" onClick={()=>{if(mayDiscard())setOperation("council");}}>Lập hội đồng mới</button>}
          {data.councils.some(c=>c.can_manage&&!c.closed_at)&&<button className="btn btn-secondary" onClick={()=>{if(mayDiscard())setOperation("schedule");}}>Xếp lịch bảo vệ</button>}
        </div>
      </div>
      <Dialog open={!!operation} size="lg" title={operation==="council"?"Lập hội đồng mới":"Xếp lịch bảo vệ"} busy={busy} onClose={()=>{if(!busy&&mayDiscard())setOperation(null);}}>
        {operation&&<div className="defense-page defense-editor">
          {error&&<p role="alert" className="alert alert-danger">{error}</p>}
          {operation==="council"?<CouncilForm data={data} busy={busy} act={async(...args)=>{const ok=await act(...args);if(ok){setOperation(null);setView("councils");}return ok;}}/>:<Card title="Xếp lịch một hoặc nhiều đề tài"><BatchDefenseSchedule data={data} busy={busy} save={async body=>{const ok=await act(root+"/slots-batch",body);if(ok){setOperation(null);setView("schedules");}return ok;}}/></Card>}
        </div>}
      </Dialog>
      <div hidden={view!=="register"}>{!!data.export_rounds?.length&&<DefenseRegister rounds={data.export_rounds} refresh={refresh}/>}</div>
      <div hidden={view!=='announcements'}><DefenseScheduleNotices refresh={refresh}/></div>
      <div hidden={view!=="councils"}>
      {!data.councils.length&&<p>Chưa có hội đồng trong phạm vi của bạn. Chọn “Lập hội đồng mới” để bắt đầu nếu được phân quyền.</p>}
      {!!data.councils.length&&<section className="stack"><h2>Danh sách hội đồng</h2><div className="defense-council-grid">
        {data.councils.map(c=>{
          const ownRole=data.slots.find(s=>s.council.id===c.id)?.role;
          const path=councilPath(c);
          return <Card key={c.id} title={c.name}>
            <p>{councilContext(data,c)}</p><p>{c.reference} · {c.closed_at?"Đã khóa bảng điểm":"Đang xử lý"}</p>
            <p>{data.slots.filter(s=>s.council.id===c.id&&s.finalized_at).length}/{data.slots.filter(s=>s.council.id===c.id).length} phiên đã chốt</p><details><summary>Thành phần hội đồng · {c.members.length} giảng viên</summary><ul>{c.members.map(m=><li key={m.id}>{data.roles[m.role]} · {m.name}</li>)}</ul></details>
            <button className="btn btn-secondary" onClick={()=>{if(mayDiscard()){setFilter(c.id);setView("schedules");}}}>Xem lịch hội đồng này</button>
            {c.can_manage&&<PublishDefenseSchedule councilId={c.id} busy={busy} save={body=>act(councilPath(c)+'/publish-schedule',body)}/>}
            {c.can_manage&&<SharedArrival slots={data.slots.filter(s=>s.council.id===c.id&&s.schedule_editable)} busy={busy} save={body=>act(councilPath(c)+'/shared-arrival',body,undefined,'PUT')}/>}
            {c.can_manage&&!c.closed_at&&data.scopes.some(s=>s.round_id===c.round_id&&s.department_id===c.department_id)&&!data.slots.some(s=>s.council.id===c.id&&!s.schedule_editable)&&<details className="defense-operation"><summary>Điều chỉnh hội đồng trước buổi họp</summary><CouncilForm council={c} data={data} act={act} busy={busy}/></details>}
            {(c.can_manage||["CHAIR","SECRETARY"].includes(ownRole??""))&&<details className="defense-operation"><summary>Đối chiếu bảng điểm trước khi khóa</summary><div className="defense-results"><table><thead><tr><th>Sinh viên</th><th>Điểm</th><th>Trạng thái</th></tr></thead><tbody>{data.slots.filter(s=>s.council.id===c.id).flatMap(s=>s.roster.map(r=><tr key={s.id+r.id}><td>{r.name} · {r.code}</td><td>{s.results[r.id]?.average??"—"}</td><td>{s.finalized_at?"Đã chốt":"Chưa chốt"}{s.results[r.id]?.attendance.status==="ABSENT"&&" · Vắng, chưa có kết quả học vụ"}</td></tr>))}</tbody></table></div></details>}
            {c.can_manage&&!c.closed_at&&<button className="btn btn-primary" disabled={busy||!data.slots.some(s=>s.council.id===c.id)||data.slots.some(s=>s.council.id===c.id&&!s.finalized_at)}
              onClick={()=>{if(window.confirm("Khóa điểm của các phiên đã chốt trong hội đồng này?"))act(path+"/close",{});}}>Khóa bảng điểm hội đồng</button>}
          </Card>;
        })}
      </div></section>}
      </div><div hidden={view!=="schedules"} className="stack">
      <h2 id="defense-schedules">Lịch và kết quả bảo vệ</h2>
      <label>Tìm lịch theo đề tài, hội đồng, phòng, tên SV hoặc MSSV<input className="input" value={search} onChange={e=>{if(!hasDrafts())setSearch(e.target.value);else setError("Hãy lưu nội dung đang nhập trước khi lọc danh sách.");}}/></label>
      {filter&&<button className="btn btn-secondary" onClick={()=>{if(mayDiscard())setFilter("");}}>Hiện tất cả lịch</button>}
      {!slots.length&&<p>{search||filter?"Không có kết quả phù hợp. Hãy đổi từ khóa hoặc xóa bộ lọc.":"Chưa có lịch trong phạm vi của bạn."}</p>}
      {[...slots].sort((a,b)=>Number(b.id===focused)-Number(a.id===focused)).map(slot=><details id={`slot-${slot.id}`} key={slot.id} className="defense-operation defense-session" open={slot.id===focused||slots.length===1}><summary>{when(slot.starts_at)} · {slot.room} · {slot.title}</summary><SlotCard slot={slot} data={data} act={act} download={download} busy={busy} initialTab={slot.id===focused?initialTab:undefined}/>{slot.finalized_at&&slot.council.closed_at&&(slot.can_manage||['CHAIR','SECRETARY'].includes(slot.role??''))&&<DefenseCorrections slot={slot} criteria={data.criteria} saved={()=>void load().catch(e=>setError(errorMessage(e)))}/>}</details>)}
      </div>
    </>}
  </div>;
}
