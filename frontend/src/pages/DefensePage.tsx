import {useCallback,useEffect,useState,type FormEvent,type ReactNode} from "react";
import {useSearchParams} from "react-router-dom";
import {request,type Context} from "../api";
import {downloadEvaluationFile,when} from "../evaluation";
import {errorMessage} from "../errors";
import "../styles/defense.css";
import PageHeader from "../components/layout/PageHeader";

type Person={id:string;name:string;role:string};
type Student={id:string;name:string;code:string};
type Council={id:string;name:string;reference:string;round_id:string;department_id:string;members:Person[];can_manage:boolean;closed_at:string|null};
type Scope={round_id:string;round_code:string;department_id:string;department_name:string};
type Mark={scores:string[];note:string};
type Result={average?:string|null;attendance:{status?:string;reason?:string;bonus?:string;bonus_reference?:string};scores?:Array<string|null>};
type Slot={id:string;thesis_id:string;title:string;council:Council;starts_at:string;ends_at:string;room:string;version:number;
  roster:Student[];results:Record<string,Result>;marks:Record<string,Record<string,Mark>>;
  role:string|null;lecturer_id:string|null;minutes:{discussion?:string;conclusion?:string};finalized_at:string|null;
  can_manage:boolean;schedule_editable:boolean;blockers:string[];council_attendance:{present_ids?:string[];reason?:string}};
type Workspace={scopes:Scope[];councils:Council[];eligible:{id:string;title:string;round_id:string;department_id:string}[];
  candidates:{id:string;name:string;code:string}[];slots:Slot[];criteria:[string,string,string][];roles:Record<string,string>};
type Act=(path:string,body:unknown,version?:number,method?:string)=>void;
type Download=(path:string,name:string)=>void;
const root="/defense";
const slotPath=(slot:Slot)=>root+"/slots/"+slot.id;
const councilPath=(council:Council)=>root+"/councils/"+council.id;
const dateLocal=(iso:string)=>new Date(Date.parse(iso)+7*3600000).toISOString().slice(0,16);
const option=(value:string,label:string)=><option value={value} key={value}>{label}</option>;
const text=(form:FormData,key:string)=>String(form.get(key)??"");

function Card({title,children}:{title:string;children:ReactNode}) {
  return <section className="card"><div className="card-body stack"><h3>{title}</h3>{children}</div></section>;
}

function CouncilForm({data,act,busy}:{data:Workspace;act:Act;busy:boolean}) {
  const [roles]=useState(["CHAIR","SECRETARY","REVIEWER","REVIEWER","MEMBER"]);
  function submit(e:FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form=new FormData(e.currentTarget);
    const scope=data.scopes[Number(form.get("scope"))];
    if(!scope)return;
    act(root+"/councils",{round_id:scope.round_id,department_id:scope.department_id,name:text(form,"name"),
      reference:text(form,"reference"),members:roles.map((role,i)=>({role,lecturer_id:text(form,"lecturer"+i)}))});
  }
  return <Card title="Lập hội đồng"><form className="stack" onSubmit={submit}>
    <label>Đợt và bộ môn<select name="scope" className="input">{data.scopes.map((r,i)=>option(String(i),r.round_code+" · "+r.department_name))}</select></label>
    <label>Tên hội đồng<input name="name" className="input" minLength={3} maxLength={200} required/></label>
    <label>Số quyết định hoặc căn cứ phân công<input name="reference" className="input" minLength={3} maxLength={300} required/></label>
    {roles.map((role,i)=><label key={i}>{data.roles[role]}{role==="REVIEWER"?` ${i-1}`:""}
      <select name={"lecturer"+i} className="input" defaultValue="" required>
        <option value="" disabled>Chọn giảng viên</option>
        {data.candidates.map(c=>option(c.id,c.name+" · "+c.code))}
      </select>
    </label>)}
    <div className="flex gap-3">
      <button className="btn btn-primary" disabled={busy}>Tạo hội đồng</button>
    </div>
  </form></Card>;
}

function ScheduleForm({data,act,busy,slot}:{data:Workspace;act:Act;busy:boolean;slot?:Slot}) {
  const available=data.councils.filter(c=>c.can_manage&&!c.closed_at);
  const [councilId,setCouncilId]=useState(slot?.council.id??"");
  const council=available.find(c=>c.id===councilId);
  const taken=new Set(data.slots.map(s=>s.thesis_id));
  const theses=data.eligible.filter(t=>t.round_id===council?.round_id&&t.department_id===council?.department_id&&
    (slot?t.id===slot.thesis_id:!taken.has(t.id)));
  function submit(e:FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form=new FormData(e.currentTarget);
    act(slot?slotPath(slot):root+"/slots",{council_id:councilId,thesis_id:text(form,"thesis"),
      starts_at:text(form,"start")+":00+07:00",ends_at:text(form,"end")+":00+07:00",room:text(form,"room")},
      slot?.version,slot?"PUT":"POST");
  }
  return <form className="stack" onSubmit={submit}>
    <label>Hội đồng<select className="input" value={councilId} required onChange={e=>setCouncilId(e.target.value)}>
      <option value="" disabled>Chọn hội đồng</option>{available.map(c=>option(c.id,c.name))}</select></label>
    <label>Đề tài đủ điều kiện<select key={councilId} name="thesis" className="input" required>
      {theses.map(t=>option(t.id,t.title))}</select></label>
    {council&&!theses.length&&<p>Chưa có đề tài phù hợp trong phạm vi hội đồng.</p>}
    <label>Bắt đầu (giờ Việt Nam)<input name="start" className="input" type="datetime-local" defaultValue={slot?dateLocal(slot.starts_at):""} required/></label>
    <label>Kết thúc (giờ Việt Nam)<input name="end" className="input" type="datetime-local" defaultValue={slot?dateLocal(slot.ends_at):""} required/></label>
    <label>Phòng bảo vệ<input name="room" className="input" defaultValue={slot?.room} required minLength={2} maxLength={200}/></label>
    <button className="btn btn-primary" disabled={busy||!theses.length}>Lưu lịch</button>
  </form>;
}

function StudentMarks({slot,student,data,act,download,busy}:{slot:Slot;student:Student;data:Workspace;act:Act;download:Download;busy:boolean}) {
  const [grader,setGrader]=useState(slot.lecturer_id??"");
  const result=slot.results[student.id];
  const recorded=result?.attendance;
  const mark=slot.marks[student.id]?.[grader];
  const endpoint=slotPath(slot);
  const [preview,setPreview]=useState<string[]>(mark?.scores??Array(12).fill(""));
  const raw=preview.reduce((sum,value)=>sum+(Number(value)||0),0)+Number(recorded?.bonus??0);
  const canExport=slot.can_manage||["CHAIR","SECRETARY"].includes(slot.role??"");
  function submit(path:string,e:FormEvent<HTMLFormElement>,payload:(form:FormData)=>unknown) {
    e.preventDefault();act(endpoint+path,payload(new FormData(e.currentTarget)),slot.version,"PUT");
  }
  return <Card title={student.name+" · "+student.code}>
    <p>{recorded?.status==="PRESENT"?"Có mặt":recorded?.status==="ABSENT"?"Vắng":"Chưa xác nhận có mặt"}
      {recorded?.reason&&" · "+recorded.reason}{result?.average&&" · Điểm trung bình "+result.average}
      {result?.scores&&" · Đã có "+result.scores.filter(s=>s!==null).length+"/"+result.scores.length+" phiếu"}</p>
    {!slot.finalized_at&&slot.role==="SECRETARY"&&<form className="stack" onSubmit={e=>submit("/attendance/"+student.id,e,f=>({status:text(f,"status"),reason:text(f,"reason")}))}>
      <label>Điểm danh<select className="input" name="status" defaultValue={recorded?.status??"PRESENT"}>
        {option("PRESENT","Có mặt")}{option("ABSENT","Vắng")}</select></label>
      <label>Lý do nếu vắng<input name="reason" className="input" maxLength={500} defaultValue={recorded?.reason}/></label>
      <button className="btn btn-secondary" disabled={busy}>Lưu điểm danh</button>
    </form>}
    {!slot.finalized_at&&slot.role==="CHAIR"&&<form className="stack" onSubmit={e=>submit("/bonus/"+student.id,e,f=>({points:text(f,"bonus"),reference:text(f,"reference")}))}>
      <label>Điểm thưởng chung cho sinh viên<input name="bonus" className="input" type="number" min={0} max={1} step=".01" defaultValue={recorded?.bonus??"0"} required/></label>
      <label>Căn cứ công bố khoa học<input name="reference" className="input" maxLength={500} defaultValue={recorded?.bonus_reference}/></label>
      <button className="btn btn-secondary" disabled={busy}>Xác nhận điểm thưởng</button>
    </form>}
    {!slot.finalized_at&&slot.role&&recorded?.status==="PRESENT"&&<details><summary>Phiếu chấm Mẫu 6 · Điểm thưởng {recorded.bonus??"0"}</summary>
      {slot.role==="SECRETARY"&&<label>Người đánh giá<select className="input" value={grader} onChange={e=>{setGrader(e.target.value);setPreview(slot.marks[student.id]?.[e.target.value]?.scores??Array(12).fill(""));}}>
        {slot.council.members.map(m=>option(m.id,m.name))}</select></label>}
      <form key={grader} className="stack" onSubmit={e=>submit("/marks",e,f=>({thesis_member_id:student.id,lecturer_id:grader,
        scores:data.criteria.map(([code])=>text(f,code)),note:text(f,"note"),paper_entry_reason:text(f,"paper")}))}>
        {data.criteria.map(([code,label,max],i)=><label key={code}>{code} · {label} (tối đa {max})
          <input name={code} className="input" type="number" min={0} max={max} step=".01" value={preview[i]} onChange={e=>setPreview(values=>values.map((v,index)=>index===i?e.target.value:v))} required/></label>)}
        {grader!==slot.lecturer_id&&<label>Căn cứ nhập hộ từ phiếu giấy<input name="paper" className="input" minLength={5} maxLength={500} required/></label>}
        <label>Nhận xét<textarea name="note" className="input" defaultValue={mark?.note} maxLength={3000}/></label>
        <p className="defense-score-preview">Tổng dự kiến · {Math.min(10,Math.round(raw*10)/10).toFixed(1)} / 10 · gồm điểm thưởng {recorded?.bonus??"0"}</p>
        <button className="btn btn-primary" disabled={busy}>Lưu phiếu chấm</button>
      </form>
    </details>}
    {slot.finalized_at&&recorded?.status==="PRESENT"&&slot.council.members.filter(m=>(canExport||m.id===slot.lecturer_id)&&!!slot.marks[student.id]?.[m.id]).map(m=>
      <button key={m.id} className="btn btn-secondary" onClick={()=>download(endpoint+"/forms/6?student_id="+student.id+"&lecturer_id="+m.id,
        `Mau-06-${student.code}-${m.id.slice(0,8)}-v${slot.version}.xlsx`)}>Mẫu 6 · {m.name}</button>)}
  </Card>;
}

function SlotCard({slot,data,act,download,busy}:{slot:Slot;data:Workspace;act:Act;download:Download;busy:boolean}) {
  const endpoint=slotPath(slot);
  return <Card title={slot.title}>
    {!slot.finalized_at&&slot.role==="SECRETARY"&&<form className="stack defense-attendance" onSubmit={e=>{
      e.preventDefault();const form=new FormData(e.currentTarget);
      act(endpoint+"/council-attendance",{present_ids:form.getAll("present"),reason:text(form,"reason")},slot.version,"PUT");
    }}>
      <h4>Điểm danh hội đồng trước khi chấm</h4><p>Cần ít nhất 3/5 người, gồm chủ tịch và thư ký.</p>
      {slot.council.members.map(m=><label key={m.id} className="defense-check"><input type="checkbox" name="present" value={m.id}
        defaultChecked={slot.council_attendance.present_ids?.includes(m.id)??false}/>{data.roles[m.role]} · {m.name}</label>)}
      <label>Ghi nhận thành phần dự họp<input name="reason" className="input" defaultValue={slot.council_attendance.reason} required minLength={5} maxLength={1000}/></label>
      <button className="btn btn-secondary" disabled={busy}>Lưu thành phần dự họp</button>
    </form>}
    <p>{slot.council.name} · {when(slot.starts_at)} → {when(slot.ends_at)} · {slot.room}</p>
    <p>{slot.finalized_at?`Đã chốt v${slot.version} · ${when(slot.finalized_at)}`:"Đã xếp lịch"}{slot.role&&" · "+data.roles[slot.role]}</p>
    {slot.can_manage&&slot.schedule_editable&&<details><summary>Đổi hoặc hủy lịch</summary>
      <ScheduleForm data={data} slot={slot} act={act} busy={busy}/>
      <form className="stack" onSubmit={e=>{e.preventDefault();const reason=text(new FormData(e.currentTarget),"reason");
        if(window.confirm("Hủy lịch bảo vệ này?"))act(endpoint+"/cancel",{reason},slot.version);}}>
        <label>Lý do hủy lịch<input name="reason" className="input" minLength={5} maxLength={500} required/></label>
        <button className="btn btn-secondary" disabled={busy}>Hủy lịch</button>
      </form>
    </details>}
    {slot.roster.map(s=><StudentMarks key={s.id} slot={slot} student={s} data={data} act={act} download={download} busy={busy}/>)}
    {!slot.finalized_at&&slot.role==="SECRETARY"&&<form className="stack" onSubmit={e=>{
      e.preventDefault();const f=new FormData(e.currentTarget);
      act(endpoint+"/minutes",{discussion:text(f,"discussion"),conclusion:text(f,"conclusion")},slot.version,"PUT");}}>
      <h4>Biên bản Mẫu 9</h4>
      <label>Nội dung họp, câu hỏi và nhận xét<textarea name="discussion" className="input" defaultValue={slot.minutes.discussion} minLength={5} maxLength={10000} required/></label>
      <label>Kết luận<textarea name="conclusion" className="input" defaultValue={slot.minutes.conclusion} minLength={5} maxLength={5000} required/></label>
      <button className="btn btn-secondary" disabled={busy}>Lưu biên bản</button>
    </form>}
    {!slot.finalized_at&&slot.blockers.length>0&&<aside className="defense-blockers"><h4>Việc cần hoàn tất trước khi chốt</h4><ul>{slot.blockers.map((text,i)=><li key={i}>{text}</li>)}</ul></aside>}
    {!slot.finalized_at&&["CHAIR","SECRETARY"].includes(slot.role??"")&&<button className="btn btn-primary" disabled={busy||slot.blockers.length>0} onClick={()=>{if(slot.blockers.length)return;if(window.confirm("Chốt điểm và biên bản để xuất bản ký?"))act(endpoint+"/finalize",{},slot.version);}}>Chốt kết quả bảo vệ</button>}
    {slot.finalized_at&&!slot.council.closed_at&&["CHAIR","SECRETARY"].includes(slot.role??"")&&<details className="defense-operation">
      <summary>Sửa bản chưa ký và xuất lại</summary><form className="stack" onSubmit={e=>{
        e.preventDefault();const form=new FormData(e.currentTarget);
        act(endpoint+"/reopen-unsigned",{reason:text(form,"reason"),confirm_unsigned:form.get("unsigned")==="on"},slot.version);
      }}><p>Phiên bản cũ được giữ trong lịch sử. Sau sửa cần chốt lại và in đúng phiên bản mới để ký.</p>
        <label>Lý do điều chỉnh<input className="input" name="reason" minLength={5} maxLength={1000} required/></label>
        <label className="defense-check"><input type="checkbox" name="unsigned" required/>Tôi xác nhận hồ sơ này chưa được ký.</label>
        <button className="btn btn-secondary" disabled={busy}>Mở chỉnh sửa bản chưa ký</button>
      </form></details>}
    {slot.finalized_at&&(slot.can_manage||slot.role)&&<button className="btn btn-secondary" onClick={()=>download(endpoint+"/forms/9",
      `Mau-09-${slot.id}-v${slot.version}.docx`)}>Tải biên bản Mẫu 9</button>}
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
  const act:Act=(path,body,version,method="POST")=>{
    if(busy)return;
    setBusy(true);setError("");setMessage("");
    void request(path,context.user_id,{method,body:JSON.stringify(body),headers:version?{"If-Match":String(version)}:undefined})
      .then(load).then(()=>setMessage("Đã cập nhật hồ sơ.")).catch(e=>{setError(errorMessage(e));void load().catch(()=>undefined);}).finally(()=>setBusy(false));
  };
  const download:Download=(path,name)=>{setError("");void downloadEvaluationFile(path,name).catch(e=>setError(errorMessage(e)));};
  const focused=params.get("slot");
  const slots=data?.slots.filter(s=>(s.id===focused||!filter||s.council.id===filter)&&(s.title+" "+s.room+" "+s.council.name).toLocaleLowerCase("vi").includes(search.toLocaleLowerCase("vi")))??[];
  return <div className="stack defense-page">
    <PageHeader title="Hội đồng và bảo vệ" description="Hội đồng → lịch bảo vệ → điểm danh → chấm Mẫu 6 → biên bản → chốt và xuất bảng điểm.">
      <button className="btn btn-secondary" disabled={busy} onClick={()=>{void load().catch(e=>setError(errorMessage(e)));}}>Làm mới dữ liệu</button>
    </PageHeader>
    {error&&<p role="alert" className="alert alert-danger">{error}</p>}
    {message&&<p role="status" className="alert alert-success">{message}</p>}
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
            <ul>{c.members.map(m=><li key={m.id}>{data.roles[m.role]} · {m.name}</li>)}</ul>
            <button className="btn btn-secondary" onClick={()=>setFilter(c.id)}>Xem lịch hội đồng này</button>
            {c.can_manage&&!c.closed_at&&<button className="btn btn-primary" disabled={busy}
              onClick={()=>{if(window.confirm("Khóa danh sách và điểm của hội đồng để xuất Mẫu 10 và 11?"))act(path+"/close",{});}}>Khóa bảng điểm hội đồng</button>}
            {c.closed_at&&(c.can_manage||["CHAIR","SECRETARY"].includes(ownRole??""))&&<div className="flex gap-3">
              <button className="btn btn-secondary" onClick={()=>download(path+"/forms/10",`Mau-10-${c.id}.docx`)}>Tải Mẫu 10</button>
              <button className="btn btn-secondary" onClick={()=>download(path+"/forms/11",`Mau-11-${c.id}.xlsx`)}>Tải Mẫu 11</button>
            </div>}
          </Card>;
        })}
      </section>}
      <h2>Lịch và kết quả bảo vệ</h2>
      <label>Tìm lịch theo đề tài, hội đồng hoặc phòng<input className="input" value={search} onChange={e=>setSearch(e.target.value)}/></label>
      {filter&&<button className="btn btn-secondary" onClick={()=>setFilter("")}>Hiện tất cả lịch</button>}
      {!slots.length&&<p>Chưa có lịch trong phạm vi của bạn.</p>}
      {[...slots].sort((a,b)=>Number(b.id===focused)-Number(a.id===focused)).map(slot=><SlotCard key={slot.id+":"+slot.version}
        slot={slot} data={data} act={act} download={download} busy={busy}/>)}
    </>}
  </div>;
}
