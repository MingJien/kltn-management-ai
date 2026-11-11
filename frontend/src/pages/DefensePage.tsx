import {useCallback,useEffect,useState,useRef,type FormEvent,type ReactNode,type ComponentProps} from "react";
import {useSearchParams} from "react-router-dom";
import {request,type Context} from "../api";
import {downloadEvaluationFile,when} from "../evaluation";
import {errorMessage} from "../errors";
import "../styles/defense.css";
import PageHeader from "../components/layout/PageHeader";

type Person={id:string;name:string;role:string};
type Student={id:string;name:string;code:string};
type Council={id:string;name:string;reference:string;round_id:string;department_id:string;members:Person[];can_manage:boolean;closed_at:string|null;signature?:string};
type Scope={round_id:string;round_code:string;department_id:string;department_name:string;department_code?:string;faculty_id?:string};
type PlanningThesis={id:string;title:string;round_id:string;department_id:string;advisor_ids?:string[]};
type Mark={scores:string[];note:string;revision?:number};
type Result={average?:string|null;attendance:{status?:string;reason?:string;bonus?:string;bonus_reference?:string;bonus_evidence_version_id?:string};scores?:Array<string|null>};
type Slot={report_filename?:string;prior_slot_id?:string|null;absence_decisions?:Record<string,{outcome:string;reference:string;reason:string;recorded_by:string;recorded_at:string;revision:number}>;context_token:string;bonus_evidence:{id:string;name:string;filename?:string}[];id:string;thesis_id:string;title:string;council:Council;starts_at:string;ends_at:string;room:string;version:number;
  roster:Student[];results:Record<string,Result>;marks:Record<string,Record<string,Mark>>;
  role:string|null;lecturer_id:string|null;minutes:{discussion?:string;conclusion?:string};finalized_at:string|null;
  can_manage:boolean;schedule_editable:boolean;blockers:string[];council_attendance:{present_ids?:string[];reason?:string}};
type Workspace={scopes:Scope[];councils:Council[];eligible:{id:string;title:string;round_id:string;department_id:string;extension_starts_at:string|null;extension_until_at:string|null;advisor_ids?:string[]}[];
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
  const plans = (data.planning_theses ?? data.eligible).filter(t =>
    t.round_id === scope?.round_id && t.department_id === scope?.department_id);
  const selectedPlans = plans.filter(t => checkedTheses.includes(t.id));
  const query = searchText(search);
  const matchingPlans = plans.filter(t => !checkedTheses.includes(t.id) && searchText(t.title).includes(query));
  const blockedAdvisors = new Set(selectedPlans.flatMap(t => t.advisor_ids ?? []));
  const hasAdvisorConflict = chosen.some(id => blockedAdvisors.has(id));
  const isGuest = (candidate: Workspace["candidates"][number]) => !!scope?.faculty_id && candidate.faculty_id !== scope.faculty_id;
  const hasGuest = data.candidates.some(c => chosen.includes(c.id) && isGuest(c));
  const memberSelection = chosen.filter(Boolean).sort().join(",");
  const conflictSelection = [scope?.round_id, scope?.department_id, memberSelection, ...[...checkedTheses].sort()].join("|");
  const candidates = data.candidates.filter(c => scope?.department_code === "SYN-DEMO-DEP" || c.department_code !== "SYN-DEMO-DEP").sort((a, b) =>
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
  return <Card title="Lập hội đồng"><DraftForm className="stack" onSubmit={submit}>
    <label>Đợt và bộ môn<select name="scope" className="input" value={scopeIndex} disabled={!!council}
      onChange={e => {setScopeIndex(Number(e.target.value)); setCheckedTheses([]); setChosen(Array(5).fill("")); setSearch("");}}>
      {data.scopes.map((r,i)=>option(String(i), [r.round_code, r.department_code === "SYN-DEMO-DEP" ? null : r.department_code, r.department_name].filter(Boolean).join(" · ")))}
    </select></label>
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
    <label>Tên hội đồng<input name="name" defaultValue={council?.name} className="input" minLength={3} maxLength={200} required/></label>
    <label>Số quyết định hoặc căn cứ phân công<input name="reference" defaultValue={council?.reference} className="input" minLength={3} maxLength={300} required/></label>
    {availableCount < roles.length && <p className="alert alert-warning">Có {availableCount}/{roles.length} giảng viên phù hợp với các đề tài đã chọn. Cần thêm giảng viên có tài khoản hoạt động hoặc điều chỉnh nhóm đề tài.</p>}
    {roles.map((role,i)=><label key={i}>{data.roles[role]}{role==="REVIEWER"?` ${i-1}`:""}
      <select name={"lecturer"+i} className="input" value={chosen[i]} onChange={e=>setChosen(values=>values.map((v,index)=>index===i?e.target.value:v))} required>
        <option value="">Chọn giảng viên</option>
        {candidates.map(c=>{
          const usedIndex = chosen.findIndex((id, index) => id === c.id && index !== i);
          const unavailable = blockedAdvisors.has(c.id) ? "GVHD của đề tài đã chọn" : usedIndex >= 0 ? "Đã chọn ở vai trò khác" : "";
          return <option key={c.id} value={c.id} disabled={!!unavailable}>
            {[c.name, c.code, c.department_code === "SYN-DEMO-DEP" ? "Giảng viên demo" : c.department_code, isGuest(c) ? "Ngoài Khoa" : "", c.specializations?.slice(0, 2).join(", "),
              unavailable].filter(Boolean).join(" · ")}
          </option>;
        })}
      </select>
    </label>)}
    {hasAdvisorConflict && <p className="alert alert-danger" role="alert">Hãy thay thành viên đang hướng dẫn một đề tài đã chọn.</p>}
    <label className="defense-check"><input key={conflictSelection} name="conflict_checked" type="checkbox" required/>Đã đối chiếu thành viên không có quan hệ thân nhân với SV bảo vệ.</label>
    {hasGuest && <label className="defense-check"><input key={memberSelection} name="guests_checked" type="checkbox" required/>Đã đối chiếu người được mời ngoài Khoa với quyết định ghi trên.</label>}
    <div className="flex gap-3">
      <button className="btn btn-primary" disabled={busy || !scope || hasAdvisorConflict || (!council && plans.length > 0 && checkedTheses.length === 0)}>{council?"Lưu điều chỉnh hội đồng":"Tạo hội đồng"}</button>
    </div>
  </DraftForm></Card>;
}

function ScheduleForm({data,act,busy,slot,supplementary}:{data:Workspace;act:Act;busy:boolean;slot?:Slot;supplementary?:Slot}) {
  const available=data.councils.filter(c=>c.can_manage&&!c.closed_at&&(!supplementary||(c.round_id===supplementary.council.round_id&&c.department_id===supplementary.council.department_id)));
  const [councilId,setCouncilId]=useState(slot?.council.id??"");
  const [thesisId,setThesisId]=useState(slot?.thesis_id??supplementary?.thesis_id??"");
  const selected=data.eligible.find(t=>t.id===thesisId);
  const council=available.find(c=>c.id===councilId);
  const taken=new Set(data.slots.map(s=>s.thesis_id));
  const hasConflict = (t: PlanningThesis) => council?.members.some(m => t.advisor_ids?.includes(m.id));
  const options = supplementary
    ? [data.planning_theses?.find(t=>t.id===supplementary.thesis_id) ?? {id:supplementary.thesis_id,title:supplementary.title,round_id:supplementary.council.round_id,department_id:supplementary.council.department_id}]
    : data.eligible.filter(t=>t.round_id===council?.round_id&&t.department_id===council?.department_id&&
      (slot?t.id===slot.thesis_id:!taken.has(t.id)));
  const theses = options.filter(t => !hasConflict(t));
  function submit(e:FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form=new FormData(e.currentTarget);
    const end=e.currentTarget.elements.namedItem("end") as HTMLInputElement;
    if (!council || !theses.some(t=>t.id===text(form,"thesis"))) return;
    if(text(form,"end")<=text(form,"start")){end.setCustomValidity("Giờ kết thúc phải sau giờ bắt đầu.");end.reportValidity();return;}
    act(slot?slotPath(slot):root+"/slots",{council_id:councilId,thesis_id:text(form,"thesis"),
      starts_at:text(form,"start")+":00+07:00",ends_at:text(form,"end")+":00+07:00",room:text(form,"room"),prior_slot_id:supplementary?.id??slot?.prior_slot_id??null,thesis_member_ids:form.getAll("member")},
      slot?.version,slot?"PUT":"POST");
  }
  return <DraftForm className="stack" onSubmit={submit}>
    <label>Hội đồng<select className="input" value={councilId} required onChange={e=>{setCouncilId(e.target.value);setThesisId(supplementary?.thesis_id??"");}}>
      <option value="" disabled>Chọn hội đồng</option>{available.map(c=>option(c.id,c.name))}</select></label>
    <label>Đề tài đủ điều kiện<select key={councilId} name="thesis" className="input" required value={theses.some(t=>t.id===thesisId)?thesisId:""} onChange={e=>setThesisId(e.target.value)}><option value="" disabled>Chọn đề tài đủ điều kiện</option>
      {theses.map(t=>option(t.id,t.title))}</select></label>
    {supplementary&&<fieldset><legend>Sinh viên được Khoa cho bảo vệ bổ sung</legend>{supplementary.roster.filter(r=>supplementary.absence_decisions?.[r.id]?.outcome==="SUPPLEMENTARY"&&!data.slots.some(s=>s.prior_slot_id===supplementary.id&&s.roster.some(m=>m.id===r.id))).map(r=><label className="defense-check" key={r.id}><input type="checkbox" name="member" value={r.id}/>{r.name} · {r.code}</label>)}<p>Chỉ xếp lịch cho các SV được chọn. Điểm của thành viên đã bảo vệ được giữ nguyên.</p></fieldset>}
    {council && options.some(hasConflict) && <p>Đã loại đề tài có GVHD trong hội đồng. Chọn hội đồng khác cho đề tài đó.</p>}
    {council&&!theses.length&&<p>Chưa có đề tài phù hợp trong phạm vi hội đồng.</p>}
    {selected?.extension_until_at&&<p className="alert alert-info">Hồ sơ đã gia hạn: {when(selected.extension_starts_at)} → <strong>{when(selected.extension_until_at)}</strong>. Chọn kỳ bảo vệ thực tế của Khoa trong khoảng này; không kéo dài hạn khi đổi lịch.</p>}
    <label>Bắt đầu (giờ Việt Nam)<input name="start" className="input" type="datetime-local" min={selected?.extension_starts_at?dateLocal(selected.extension_starts_at):undefined} max={selected?.extension_until_at?dateLocal(selected.extension_until_at):undefined} defaultValue={slot?dateLocal(slot.starts_at):""} required/></label>
    <label>Kết thúc (giờ Việt Nam)<input name="end" onInput={e=>e.currentTarget.setCustomValidity("")} className="input" type="datetime-local" min={selected?.extension_starts_at?dateLocal(selected.extension_starts_at):undefined} max={selected?.extension_until_at?dateLocal(selected.extension_until_at):undefined} defaultValue={slot?dateLocal(slot.ends_at):""} required/></label>
    <label>Phòng bảo vệ<input name="room" className="input" defaultValue={slot?.room} required minLength={2} maxLength={200}/></label>
    <button className="btn btn-primary" disabled={busy||!theses.length}>Lưu lịch</button>
  </DraftForm>;
}

function StudentMarks({slot,student,data,act,download,busy,mode}:{slot:Slot;student:Student;data:Workspace;act:Act;download:Download;busy:boolean;mode:string}) {
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
      <button className="btn btn-secondary" disabled={busy}>Lưu điểm danh</button>
    </DraftForm>}
    {slot.role&&slot.bonus_evidence?.length>0&&<details className="defense-operation"><summary>Xem tài liệu minh chứng đã nộp</summary>{slot.bonus_evidence.map(f=><button key={f.id} className="btn btn-secondary" onClick={()=>download(endpoint+"/evidence/"+f.id,f.filename??f.name)}>{f.name}</button>)}</details>}
    {!slot.finalized_at&&slot.role==="CHAIR"&&<DraftForm className="stack" onSubmit={e=>submit("/bonus/"+student.id,e,f=>({points:text(f,"bonus"),reference:text(f,"reference"),evidence_version_id:text(f,"evidence")||null}))}>
      <label>Điểm thưởng chung cho sinh viên<input name="bonus" className="input" type="number" min={0} max={1} step=".01" defaultValue={recorded?.bonus??"0"} required/></label>
      <label>Minh chứng trong hồ sơ<select className="input" name="evidence" defaultValue={recorded?.bonus_evidence_version_id??""}><option value="">Chọn minh chứng đã nộp</option>{slot.bonus_evidence?.map(f=>option(f.id,f.name))}</select></label><label>Căn cứ công bố khoa học<input name="reference" className="input" maxLength={500} defaultValue={recorded?.bonus_reference}/></label>
      <button className="btn btn-secondary" disabled={busy}>Xác nhận điểm thưởng</button>
    </DraftForm>}
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
    {!slot.role&&<p>Minh chứng công bố khoa học nộp cùng tài liệu khóa luận ở mục Hồ sơ nộp & xét duyệt. Chủ tịch đối chiếu và xác nhận mức thưởng trước khi chốt.</p>}
    {!slot.finalized_at&&["CHAIR","SECRETARY"].includes(slot.role??"")&&Object.keys(slot.marks[student.id]??{}).length>0&&<details className="defense-operation"><summary>Hủy phiếu nhập nhầm</summary><DraftForm className="stack" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);if(window.confirm("Hủy hiệu lực phiếu này? Bản cũ vẫn được lưu trong lịch sử."))act(endpoint+"/marks/"+student.id+"/"+text(f,"lecturer")+"/void",{reason:text(f,"reason")},slot.version);}}><label>Phiếu cần hủy<select name="lecturer" className="input">{slot.council.members.filter(m=>slot.marks[student.id]?.[m.id]).map(m=>option(m.id,m.name))}</select></label><label>Lý do<input className="input" name="reason" required minLength={5} maxLength={500}/></label><button className="btn btn-secondary" disabled={busy}>Hủy hiệu lực phiếu</button></DraftForm></details>}
    {slot.finalized_at&&recorded?.status==="PRESENT"&&slot.council.members.filter(m=>(canExport||m.id===slot.lecturer_id)&&!!slot.marks[student.id]?.[m.id]).map(m=>
      <button key={m.id} className="btn btn-secondary" onClick={()=>download(endpoint+"/forms/6?student_id="+student.id+"&lecturer_id="+m.id,
        `Mau-06-${student.code}-${m.id.slice(0,8)}-v${slot.version}.xlsx`)}>Mẫu 6 · {m.name}</button>)}
    </div>
  </Card>;
}

function SlotCard({slot,data,act,download,busy}:{slot:Slot;data:Workspace;act:Act;download:Download;busy:boolean}) {
  const endpoint=slotPath(slot);
  const [tab,setTab]=useState("overview");
  return <Card title={slot.title}>
    <div className="defense-session-head"><strong>{slot.council.name} · {slot.room}</strong><span>{when(slot.starts_at)} → {when(slot.ends_at)}</span>
    <button className="btn btn-secondary" onClick={()=>download(endpoint+"/report",slot.report_filename??"Bao-cao-bao-ve")}>Tải báo cáo dùng để bảo vệ</button></div>
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
      <button className="btn btn-secondary" disabled={busy}>Lưu thành phần dự họp</button>
    </DraftForm>}
    </div><div hidden={tab!=="overview"}>
    <p>{slot.council.name} · {when(slot.starts_at)} → {when(slot.ends_at)} · {slot.room}</p>
    {slot.role&&<a className="btn btn-secondary" href={"/activity?resource_type=defense_slot&resource_id="+slot.id}>Xem lịch sử phiên bảo vệ</a>}
    <p>{slot.finalized_at?`Đã chốt v${slot.version} · ${when(slot.finalized_at)}`:"Đã xếp lịch"}{slot.role&&" · "+data.roles[slot.role]}</p>
    {slot.can_manage&&slot.schedule_editable&&<details><summary>Đổi hoặc hủy lịch</summary>
      <ScheduleForm data={data} slot={slot} act={act} busy={busy}/>
      <DraftForm className="stack" onSubmit={e=>{e.preventDefault();const reason=text(new FormData(e.currentTarget),"reason");
        if(window.confirm("Hủy lịch bảo vệ này?"))act(endpoint+"/cancel",{reason},slot.version);}}>
        <label>Lý do hủy lịch<input name="reason" className="input" minLength={5} maxLength={500} required/></label>
        <button className="btn btn-secondary" disabled={busy}>Hủy lịch</button>
      </DraftForm>
    </details>}
    </div><div hidden={tab!=="marks"&&tab!=="attendance"}>
    {slot.roster.map(s=><StudentMarks key={s.id} slot={slot} student={s} mode={tab} data={data} act={act} download={download} busy={busy}/>)}
    </div><div hidden={tab!=="minutes"}>
    {!slot.finalized_at&&slot.role==="SECRETARY"&&<DraftForm className="stack" onSubmit={e=>{
      e.preventDefault();const f=new FormData(e.currentTarget);
      act(endpoint+"/minutes",{discussion:text(f,"discussion"),conclusion:text(f,"conclusion")},slot.version,"PUT");}}>
      <h4>Biên bản Mẫu 9</h4>
      <label>Nội dung họp, câu hỏi và nhận xét<textarea name="discussion" className="input" defaultValue={slot.minutes.discussion} minLength={5} maxLength={10000} required/></label>
      <label>Kết luận<textarea name="conclusion" className="input" defaultValue={slot.minutes.conclusion} minLength={5} maxLength={5000} required/></label>
      <button className="btn btn-secondary" disabled={busy}>Lưu biên bản</button>
    </DraftForm>}
    </div><div hidden={tab!=="results"&&tab!=="overview"}>
    <div className="defense-results"><table><caption>Đối chiếu kết quả từng sinh viên</caption><thead><tr><th>Sinh viên</th><th>Điểm danh</th><th>Điểm thưởng</th><th>Điểm trung bình</th></tr></thead><tbody>{slot.roster.map(r=><tr key={r.id}><td>{r.name} · {r.code}</td><td>{slot.results[r.id]?.attendance.status==="ABSENT"?"Vắng · chờ xử lý học vụ":slot.results[r.id]?.attendance.status==="PRESENT"?"Có mặt":"Chưa điểm danh"}</td><td>{slot.results[r.id]?.attendance.bonus??"0"} / 1</td><td>{slot.results[r.id]?.average??"Chưa có kết quả"}</td></tr>)}</tbody></table></div>
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
    {!slot.finalized_at&&slot.blockers.length>0&&<aside className="defense-blockers"><h4>Việc cần hoàn tất trước khi chốt</h4><ul>{slot.blockers.map((text,i)=><li key={i}>{text}</li>)}</ul></aside>}
    {!slot.finalized_at&&["CHAIR","SECRETARY"].includes(slot.role??"")&&<button className="btn btn-primary" disabled={busy||slot.blockers.length>0} onClick={()=>{if(slot.blockers.length)return;if(hasDrafts()){window.alert("Cần lưu hoặc bỏ các nội dung đang nhập trước khi chốt.");return;}if(window.confirm("Chốt điểm và biên bản để xuất bản ký?"))act(endpoint+"/finalize",{},slot.version);}}>Chốt kết quả bảo vệ</button>}
    {slot.finalized_at&&!slot.council.closed_at&&["CHAIR","SECRETARY"].includes(slot.role??"")&&<details className="defense-operation">
      <summary>Sửa bản chưa ký và xuất lại</summary><DraftForm className="stack" onSubmit={e=>{
        e.preventDefault();const form=new FormData(e.currentTarget);
        act(endpoint+"/reopen-unsigned",{reason:text(form,"reason"),confirm_unsigned:form.get("unsigned")==="on"},slot.version);
      }}><p>Phiên bản cũ được giữ trong lịch sử. Sau sửa cần chốt lại và in đúng phiên bản mới để ký.</p>
        <label>Lý do điều chỉnh<input className="input" name="reason" minLength={5} maxLength={1000} required/></label>
        <label className="defense-check"><input type="checkbox" name="unsigned" required/>Tôi xác nhận hồ sơ này chưa được ký.</label>
        <button className="btn btn-secondary" disabled={busy}>Mở chỉnh sửa bản chưa ký</button>
      </DraftForm></details>}
    {slot.finalized_at&&(slot.can_manage||slot.role)&&<button className="btn btn-secondary" onClick={()=>download(endpoint+"/forms/9",
      `Mau-09-${slot.id}-v${slot.version}.docx`)}>Tải biên bản Mẫu 9</button>}
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
  const load=useCallback(async()=>setData(await request<Workspace>(root,context.user_id)),[context.user_id]);
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
  const focused=params.get("slot");
  const slots=data?.slots.filter(s=>(s.id===focused||!filter||s.council.id===filter)&&(s.title+" "+s.room+" "+s.council.name+" "+s.roster.map(r=>r.name+" "+r.code).join(" ")).toLocaleLowerCase("vi").includes(search.toLocaleLowerCase("vi")))??[];
  return <div className="stack defense-page">
    <PageHeader title="Hội đồng và bảo vệ" description="Hội đồng → lịch bảo vệ → điểm danh → chấm Mẫu 6 → biên bản → chốt và xuất bảng điểm.">
      <button className="btn btn-secondary" disabled={busy} onClick={()=>{void load().catch(e=>setError(errorMessage(e)));}}>Làm mới dữ liệu</button>
    </PageHeader>
    {error&&<p role="alert" className="alert alert-danger defense-notice">{error}</p>}
    {message&&<p role="status" className="alert alert-success defense-notice">{message}</p>}
    {!data&&!error&&<p role="status">Đang tải…</p>}
    {data&&<>
      {!!data.scopes.length&&<details className="defense-operation"><summary>Lập hội đồng mới</summary><CouncilForm data={data} act={act} busy={busy}/></details>}
      {data.councils.some(c=>c.can_manage&&!c.closed_at)&&<details className="defense-operation"><summary>Xếp lịch bảo vệ</summary><Card title="Xếp lịch bảo vệ"><ScheduleForm data={data} act={act} busy={busy}/></Card></details>}
      {!!data.councils.length&&<section className="stack"><h2>Hội đồng</h2>
        {data.councils.map(c=>{
          const ownRole=data.slots.find(s=>s.council.id===c.id)?.role;
          const path=councilPath(c);
          return <Card key={c.id} title={c.name}>
            <p>{c.reference} · {c.closed_at?"Đã khóa bảng điểm":"Đang xử lý"}</p>
            <p>{data.slots.filter(s=>s.council.id===c.id&&s.finalized_at).length}/{data.slots.filter(s=>s.council.id===c.id).length} phiên đã chốt</p><ul>{c.members.map(m=><li key={m.id}>{data.roles[m.role]} · {m.name}</li>)}</ul>
            <button className="btn btn-secondary" onClick={()=>{if(mayDiscard()){setFilter(c.id);document.getElementById("defense-schedules")?.scrollIntoView({behavior:"smooth"});}}}>Xem lịch hội đồng này</button>
            {c.can_manage&&!c.closed_at&&data.scopes.some(s=>s.round_id===c.round_id&&s.department_id===c.department_id)&&!data.slots.some(s=>s.council.id===c.id&&!s.schedule_editable)&&<details className="defense-operation"><summary>Điều chỉnh hội đồng trước buổi họp</summary><CouncilForm council={c} data={data} act={act} busy={busy}/></details>}
            {(c.can_manage||["CHAIR","SECRETARY"].includes(ownRole??""))&&<details className="defense-operation"><summary>Đối chiếu bảng điểm trước khi khóa</summary><div className="defense-results"><table><thead><tr><th>Sinh viên</th><th>Điểm</th><th>Trạng thái</th></tr></thead><tbody>{data.slots.filter(s=>s.council.id===c.id).flatMap(s=>s.roster.map(r=><tr key={s.id+r.id}><td>{r.name} · {r.code}</td><td>{s.results[r.id]?.average??"—"}</td><td>{s.finalized_at?"Đã chốt":"Chưa chốt"}{s.results[r.id]?.attendance.status==="ABSENT"&&" · Vắng, chưa có kết quả học vụ"}</td></tr>))}</tbody></table></div></details>}
            {c.can_manage&&!c.closed_at&&<button className="btn btn-primary" disabled={busy||!data.slots.some(s=>s.council.id===c.id)||data.slots.some(s=>s.council.id===c.id&&!s.finalized_at)}
              onClick={()=>{if(window.confirm("Khóa danh sách và điểm của hội đồng để xuất Mẫu 10 và 11?"))act(path+"/close",{});}}>Khóa bảng điểm hội đồng</button>}
            {c.closed_at&&(c.can_manage||["CHAIR","SECRETARY"].includes(ownRole??""))&&<div className="flex gap-3">
              <button className="btn btn-secondary" onClick={()=>download(path+"/forms/10",`Mau-10-${c.id}.docx`)}>Tải Mẫu 10</button>
              <button className="btn btn-secondary" onClick={()=>download(path+"/forms/11",`Mau-11-${c.id}.xlsx`)}>Tải Mẫu 11</button>
            </div>}
          </Card>;
        })}
      </section>}
      <h2 id="defense-schedules">Lịch và kết quả bảo vệ</h2>
      <label>Tìm lịch theo đề tài, hội đồng, phòng, tên SV hoặc MSSV<input className="input" value={search} onChange={e=>{if(!hasDrafts())setSearch(e.target.value);else setError("Hãy lưu nội dung đang nhập trước khi lọc danh sách.");}}/></label>
      {filter&&<button className="btn btn-secondary" onClick={()=>{if(mayDiscard())setFilter("");}}>Hiện tất cả lịch</button>}
      {!slots.length&&<p>{search||filter?"Không có kết quả phù hợp. Hãy đổi từ khóa hoặc xóa bộ lọc.":"Chưa có lịch trong phạm vi của bạn."}</p>}
      {[...slots].sort((a,b)=>Number(b.id===focused)-Number(a.id===focused)).map(slot=><details key={slot.id} className="defense-operation defense-session" open={slot.id===focused||slots.length===1}><summary>{when(slot.starts_at)} · {slot.room} · {slot.title}</summary><SlotCard slot={slot} data={data} act={act} download={download} busy={busy}/></details>)}
    </>}
  </div>;
}
