import {useCallback,useEffect,useState,type FormEvent} from "react";
import {Link,useSearchParams} from "react-router-dom";
import {ArrowRight,CalendarClock,Check,CheckCircle2,ChevronRight,Clock3,FilePenLine,History,RefreshCw,Search,Users} from "lucide-react";
import {request,type Context} from "../api";
import {errorMessage} from "../errors";
import {downloadEvaluationFile,when} from "../evaluation";
import PageHeader from "../components/layout/PageHeader";
import Dialog from "../components/ui/Dialog";
import Tabs from "../components/ui/Tabs";
import EmptyState from "../components/ui/EmptyState";
import {SkeletonCard} from "../components/ui/Skeleton";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import ThesisExtensionRequests,{type ExtensionRequest} from "../components/domain/ThesisExtensionRequests";
import "../styles/thesis-changes.css";
import "../styles/assignment-tabs.css";

type Consent={decision:string;at:string};
type Change={scope:"GROUP"|"INDIVIDUAL";requested_by:string;result_thesis_id:string|null;id:string;code:string;thesis_id:string;kind:string;state:string;reason:string;proposed_title:string;
  proposed_description:string;row_version:number;submitted_at:string;decided_at:string|null;decided_by:string|null;
  decision_reason:string|null;consents:Record<string,Consent>;reviews:Record<string,Consent&{reason:string}>;
  advisor_name?:string|null; snapshot:{title:string;description:string;target_advisor_name?:string;members:{user_id:string;name:string}[]};
  can_consent:boolean;can_cancel:boolean;review_roles:string[];can_decide:boolean;ready:boolean};
type Extension={extension_starts_at:string|null;until_at:string;original_due_at:string;decision_on:string;reference:string;reason:string;recorded_by:string;recorded_at:string;
  file:{id:string;name:string;scan_state:string}|null};
type Thesis={advisor_name?:string|null;student_names?:string[];can_request_extension:boolean;extension_request_blocker:string;id:string;title:string;description:string;state:string;row_version:number;round_label:string;round_id:string;
  round_version:number;starts_on:string|null;cutoff:string|null;can_request:boolean;message:string;can_extend:boolean;
  extension_blocker:string;can_set_start:boolean;baseline_due:string|null;extension_max:string|null;extension:Extension|null;
  member_count:number;candidates:{group_available:boolean;individual_available:boolean;id:string;code:string;title:string;description:string;advisor:string;capacity:number}[];
  evidence:{id:string;name:string;scan_state:string}[]};
type Workspace={theses:Thesis[];requests:Change[];extension_requests:ExtensionRequest[]};
type Operation={kind:"create"|"start";thesis:Thesis}|{kind:"consent"|"review"|"decision"|"cancel";item:Change;role?:string};
const labels:Record<string,string>={SUBMITTED:"Đang lấy ý kiến",ADVISOR_REVIEWED:"Chờ bộ môn duyệt",APPROVED:"Đã chấp thuận",
  REJECTED:"Không chấp thuận",CANCELLED:"Đã hủy",CURRENT_ADVISOR:"GVHD hiện tại",NEW_ADVISOR:"GVHD tiếp nhận đề tài mới"};
const pending=(item:Change)=>["SUBMITTED","ADVISOR_REVIEWED"].includes(item.state);
const shortDate=(value:string)=>new Date(value).toLocaleDateString("vi-VN",{timeZone:"Asia/Ho_Chi_Minh"});
const formText=(form:FormData,key:string)=>String(form.get(key)??"");

function ChangeCard({item,userId,open}:{item:Change;userId:string;open:(op:Operation)=>void}) {
  const groupReady=item.scope==="INDIVIDUAL" ? item.consents[item.requested_by]?.decision==="AGREE" : item.snapshot.members.every(m=>item.consents[m.user_id]?.decision==="AGREE");
  const current=pending(item)?item.ready?2:groupReady?1:0:3;
  const completed=[groupReady,item.ready,item.state==="APPROVED",!pending(item)];
  return <article className="change-card card" id={"change-"+item.id}><div className="card-body stack">
    <div className="change-card__heading"><div><p className="change-eyebrow">{item.code} · {item.scope==="INDIVIDUAL"?"Tách cá nhân · ":""}{item.kind==="REPLACEMENT"?"Chuyển sang đề tài khác":"Điều chỉnh tên và phạm vi"}</p>
      <h3>{item.proposed_title}</h3></div><ThesisStatusBadge className="change-status" state={item.state} label={labels[item.state]}/></div>
    <p>SV · {item.snapshot.members.map(m=>m.name).join(", ")} · GVHD · {item.advisor_name||"Chưa ghi nhận"}</p>
    <ol className="change-steps" aria-label="Tiến trình xét duyệt">
      {[item.scope==="INDIVIDUAL"?"Người đề nghị xác nhận":"Thành viên đồng ý","GVHD xem xét","Bộ môn quyết định","Kết quả"].map((text,index)=><li key={text} aria-current={pending(item)&&index===current?"step":undefined}
        className={completed[index]?"is-done":pending(item)&&index===current?"is-current":""}><span>{completed[index]?<Check size={14} aria-hidden="true"/>:index+1}</span>{text}</li>)}
    </ol>
    <div className="change-compare"><div><span>Đề tài khi gửi</span><p>{item.snapshot.title}</p></div>
      <ArrowRight aria-hidden="true"/><div><span>Nội dung đề nghị</span><p>{item.proposed_title}</p></div></div>
    <p className="change-prose">{item.reason}</p>
    <details className="change-details"><summary>Phạm vi và ý kiến của các bên</summary><div className="stack">
      <p className="change-prose">{item.proposed_description||"Theo mô tả đề tài đã công bố."}</p>
      {item.snapshot.target_advisor_name&&<p>GVHD tiếp nhận · <strong>{item.snapshot.target_advisor_name}</strong></p>}
      <ul className="change-people">{item.snapshot.members.map(m=><li key={m.user_id}><Users size={16} aria-hidden="true"/>
        <span>{m.name}{m.user_id===userId?" (bạn)":""}</span><span>{item.scope==="INDIVIDUAL" && m.user_id!==item.requested_by?"Được thông báo":item.consents[m.user_id]?.decision==="AGREE"?"Đã đồng ý":
          item.consents[m.user_id]?.decision==="DECLINE"?"Không đồng ý":"Chờ xác nhận"}</span></li>)}</ul>
      {Object.entries(item.reviews).map(([role,r])=><div key={role} className="change-review">
        <strong>{labels[role]} · {r.decision==="AGREE"?"Đồng ý":"Từ chối"}</strong><p className="change-prose">{r.reason}</p><small>{when(r.at)}</small></div>)}
    </div></details>
    {pending(item)&&<p className="change-next"><Clock3 size={17} aria-hidden="true"/>{!groupReady?
      "Chờ mọi thành viên nhóm xác nhận.":!item.ready?"Chờ GVHD hiện tại và GVHD tiếp nhận (nếu thay đổi) xem xét.":
      "Đã đủ ý kiến. Trưởng bộ môn xem nội dung và quyết định."}</p>}
    {item.decision_reason&&<div className="change-result"><strong>{item.decided_by} · {when(item.decided_at)}</strong><p className="change-prose">{item.decision_reason}</p></div>}
    <div className="change-actions">
      {item.can_consent&&<button className="btn btn-primary" onClick={()=>open({kind:"consent",item})}>Xác nhận nguyện vọng</button>}
      {item.review_roles.map(role=><button key={role} className="btn btn-primary" disabled={!groupReady} onClick={()=>open({kind:"review",item,role})}>{labels[role]} xem xét</button>)}
      {item.can_decide&&<button className="btn btn-primary" onClick={()=>open({kind:"decision",item})}>Bộ môn xét duyệt</button>}
      {item.can_cancel&&<button className="btn btn-secondary" onClick={()=>open({kind:"cancel",item})}>Hủy yêu cầu</button>}
      {item.state==="APPROVED"&&<Link to={`/theses/${item.scope==="INDIVIDUAL"&&item.requested_by===userId?item.result_thesis_id:item.thesis_id}?section=submissions`} className="btn btn-primary">Cập nhật hồ sơ <ChevronRight size={16} aria-hidden="true"/></Link>}
    </div><p className="change-meta">Gửi lúc {when(item.submitted_at)} · Phiên bản {item.row_version}</p>
  </div></article>;
}

function OperationDialog({operation,busy,error,close,submit}:{operation:Operation;busy:boolean;error:string;close:()=>void;
  submit:(path:string,data:unknown,version:number,method?:string)=>Promise<void>}) {
  const op=operation;
  const [kind,setKind]=useState("ADJUSTMENT");
  const [scope,setScope]=useState("GROUP");
  const [target,setTarget]=useState("");
  const [answer,setAnswer]=useState(op.kind==="decision"?"APPROVE":"AGREE");
  const [confirmed,setConfirmed]=useState(false);
  const t="thesis" in op?op.thesis:null;
  const item="item" in op?op.item:null;
  const visibleCandidates = t ? t.candidates.filter(c => scope === "INDIVIDUAL" ? c.individual_available : c.group_available) : [];
  const candidate = visibleCandidates.find(c => c.id === target);
  const titles={create:"Đề nghị đổi đề tài",start:"Thiết lập ngày bắt đầu",
    consent:"Xác nhận của thành viên",review:"Ý kiến của giảng viên",decision:"Quyết định của bộ môn",cancel:"Hủy yêu cầu đổi đề tài"};
  async function save(e:FormEvent<HTMLFormElement>) {
    e.preventDefault();const f=new FormData(e.currentTarget);const reason=formText(f,"reason");
    if(op.kind==="create"&&t)await submit(`/theses/${t.id}/change-requests`,{kind,scope,reason,confirm_consequences:confirmed,
      proposed_title:kind==="ADJUSTMENT"?formText(f,"title"):"",proposed_description:kind==="ADJUSTMENT"?formText(f,"description"):"",
      target_topic_id:kind==="REPLACEMENT"?target:null},t.row_version);
    if(op.kind==="start"&&t)await submit(`/withdrawal-rounds/${t.round_id}/start`,{starts_on:formText(f,"day"),reference:formText(f,"reference")},t.round_version,"PUT");
    if(op.kind==="consent"&&item)await submit(`/thesis-changes/${item.id}/consent`,{decision:answer},item.row_version);
    if(op.kind==="review"&&item)await submit(`/thesis-changes/${item.id}/advisor-review`,{role:op.role,decision:answer,reason},item.row_version);
    if(op.kind==="decision"&&item)await submit(`/thesis-changes/${item.id}/decision`,{decision:answer,reason},item.row_version);
    if(op.kind==="cancel"&&item)await submit(`/thesis-changes/${item.id}/cancel`,{},item.row_version);
  }
  return <Dialog open title={titles[op.kind]} onClose={close} size="lg" busy={busy} footer={<>
    <button type="button" className="btn btn-secondary" disabled={busy} onClick={close}>Quay lại</button>
    <button className="btn btn-primary" form="thesis-change-operation" type="submit" disabled={busy||(
      op.kind==="create"&&!confirmed)||(op.kind==="decision"&&answer==="APPROVE"&&!item?.ready)}>
      {busy?"Đang xử lý…":op.kind==="create"?"Gửi yêu cầu":"Xác nhận"}</button></>}>
    <form id="thesis-change-operation" className="change-form" onSubmit={e=>void save(e)}>
      {error&&<p role="alert" className="alert alert-danger">{error}</p>}
      <fieldset disabled={busy} className="change-fieldset">
      {t&&<p className="change-context"><strong>{t.title}</strong><span>{t.round_label} · SV · {t.student_names?.join(", ")||"Chưa ghi nhận"}</span><span>GVHD · {t.advisor_name||"Chưa ghi nhận"}</span></p>}
      {op.kind==="create"&&t&&<>
        {t.member_count>1&&<label>Phạm vi thay đổi<select aria-label="Phạm vi thay đổi" className="input" value={scope} onChange={e=>{setScope(e.target.value);setTarget("");if(e.target.value==="INDIVIDUAL")setKind("REPLACEMENT");}}><option value="GROUP">Cả nhóm cùng thay đổi đề tài</option><option value="INDIVIDUAL">Tôi chuyển sang đề tài khác, nhóm còn lại tiếp tục</option></select></label>}
        {scope==="INDIVIDUAL"&&<p className="alert alert-info">Bạn vẫn thuộc nhóm hiện tại khi chờ xét. Chỉ khi TBM duyệt, hệ thống mới tạo hồ sơ riêng; nhóm còn lại giữ đề tài và GVHD cũ. Hai bên cần cập nhật Mẫu 1–3.</p>}
        <div className="change-type-options">
          <label className={kind==="ADJUSTMENT"?"is-selected":""}><input type="radio" name="kind" disabled={scope==="INDIVIDUAL"} checked={kind==="ADJUSTMENT"} onChange={()=>setKind("ADJUSTMENT")}/>
            <span><strong>Điều chỉnh đề tài đang làm</strong><small>Đổi tên, mục tiêu hoặc phạm vi với GVHD hiện tại.</small></span></label>
          <label className={kind==="REPLACEMENT"?"is-selected":""}><input type="radio" name="kind" checked={kind==="REPLACEMENT"} onChange={()=>setKind("REPLACEMENT")}/>
            <span><strong>Chuyển sang đề tài khác</strong><small>Chọn đề tài còn trống trong cùng đợt, cùng bộ môn.</small></span></label>
        </div>
        {kind==="ADJUSTMENT"?<>
          <label>Tên đề tài đề nghị<input name="title" className="input" required minLength={10} maxLength={500} defaultValue={t.title}/></label>
          <label htmlFor="change-description">Mục tiêu và phạm vi mới</label>
          <textarea id="change-description" name="description" className="input" required minLength={20} maxLength={10000} rows={5} defaultValue={t.description}/>
        </>:<>
          <label>Đề tài mới<select aria-label="Đề tài mới" className="input" required value={target} onChange={e=>setTarget(e.target.value)}><option value="">Chọn đề tài</option>
            {visibleCandidates.map(c=><option key={c.id} value={c.id}>{c.code} · {c.title}</option>)}</select></label>
          {!visibleCandidates.length&&<p className="alert alert-warning">Chưa có đề tài trống phù hợp. Liên hệ bộ môn để được hướng dẫn.</p>}
          {candidate&&<div className="change-target"><strong>{candidate.title}</strong><p>GVHD · {candidate.advisor} · Tối đa {candidate.capacity} sinh viên</p><p className="change-prose">{candidate.description}</p></div>}
        </>}
        <label>Lý do thay đổi<textarea name="reason" className="input" required minLength={10} maxLength={3000} rows={3}/></label>
        <p className="change-note">Sau khi được duyệt, nhóm cập nhật Mẫu 1–3 và báo cáo theo đề tài mới. GVHD liên quan cần đồng ý trước khi bộ môn xét duyệt; nếu thay đổi cả nhóm, từng thành viên cần đồng ý.</p>
        <label className="change-checkbox"><input type="checkbox" required checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/><span>Tôi đồng ý nội dung đề nghị và việc cập nhật hồ sơ sau khi được duyệt.</span></label>
      </>}
      {op.kind==="start"&&<>
        <p>Mốc của cả đợt dùng tính 14 ngày đổi đề tài và xin thôi. Khi đã có yêu cầu, hệ thống khóa mốc để giữ đúng hạn.</p>
        <label>Ngày bắt đầu thực hiện<input name="day" type="date" className="input" required/></label>
        <label>Căn cứ kế hoạch<input name="reference" className="input" minLength={5} maxLength={500} required/></label>
      </>}
      {item&&<>
        <div className="change-context"><strong>{item.proposed_title}</strong><span>{item.code} · SV · {item.snapshot.members.map(m=>m.name).join(", ")}</span><span>GVHD khi gửi · {item.advisor_name||"Chưa ghi nhận"}</span></div>
        {op.kind==="cancel"?<p>Hủy yêu cầu còn chờ này để tiếp tục hồ sơ hiện tại. Nếu cần thay nội dung, bạn có thể lập lại trong thời hạn.</p>:<>
          <label>Kết quả<select className="input" value={answer} onChange={e=>setAnswer(e.target.value)}>
            {op.kind==="decision"?<><option value="APPROVE">Chấp thuận</option><option value="REJECT">Không chấp thuận</option></>:
              <><option value="AGREE">Đồng ý</option><option value={op.kind==="consent"?"DECLINE":"REJECT"}>Không đồng ý</option></>}
          </select></label>
          {op.kind==="decision"&&!item.ready&&<p className="alert alert-warning">Chưa đủ xác nhận để chấp thuận. Bạn có thể từ chối kèm lý do hoặc quay lại chờ ý kiến.</p>}
          {op.kind!=="consent"&&<label>Ý kiến và căn cứ<textarea name="reason" className="input" required minLength={5} maxLength={3000} rows={4}/></label>}
          {op.kind==="consent"&&<p>Nếu một thành viên không đồng ý, yêu cầu kết thúc để cả nhóm thống nhất lại nội dung.</p>}
        </>}
      </>}
      </fieldset>
    </form>
  </Dialog>;
}

export default function ThesisChangesPage({context}:{context:Context}) {
  const [params,setParams]=useSearchParams();
  const [data,setData]=useState<Workspace>();
  const [view,setView]=useState<"CHANGE"|"EXTENSION">(params.has("extension")?"EXTENSION":"CHANGE");
  useEffect(()=>{if(params.has("extension"))setView("EXTENSION");},[params]);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [busy,setBusy]=useState(false);
  const [query,setQuery]=useState("");
  const [filter,setFilter]=useState("OPEN");
  const [operation,setOperation]=useState<Operation|null>(null);
  const [dialogError,setDialogError]=useState("");
  const load=useCallback(async()=>setData(await request<Workspace>("/thesis-changes",context.user_id)),[context.user_id]);
  const focus=params.get("focus");
  useEffect(()=>{const controller=new AbortController();
    void request<Workspace>("/thesis-changes",context.user_id,{signal:controller.signal}).then(setData)
      .catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));});
    return ()=>controller.abort();
  },[context.user_id,focus]);
  const selectedId=params.get("thesis")||(context.base_role==="STUDENT"&&data?.theses.length===1?data.theses[0].id:"");
  const selected=data?.theses.find(t=>t.id===selectedId);
  const requests=(data?.requests??[]).filter(item=>(!selectedId||item.thesis_id===selectedId)&&(filter==="ALL"||pending(item)||item.id===focus)&&
    (item.proposed_title+" "+item.snapshot.title+" "+item.code).toLocaleLowerCase("vi").includes(query.toLocaleLowerCase("vi")));
  useEffect(()=>{if(data&&focus)document.getElementById("change-"+focus)?.scrollIntoView({block:"start",behavior:"smooth"});},[data,focus]);
  function open(op:Operation) {setDialogError("");setOperation(op);}
  async function submit(path:string,payload:unknown,version:number,method="POST") {
    if(busy)return;setBusy(true);setDialogError("");setError("");setNotice("");
    try {
      await request(path,context.user_id,{method,headers:{"If-Match":String(version)},body:JSON.stringify(payload)});
      await load();
      if(operation&&["decision","cancel","consent"].includes(operation.kind))setFilter("ALL");
      setOperation(null);setNotice("Đã lưu và thông báo đến các tài khoản liên quan.");
    } catch(cause){setDialogError(errorMessage(cause));await load().catch(()=>undefined);}
    finally{setBusy(false);}
  }
  const counts=(data?.requests??[]).filter(pending).length;
  return <div className="changes-page">
    <PageHeader title="Đổi đề tài & gia hạn" description="Theo dõi thay đổi của nhóm, ý kiến giảng viên và quyết định theo từng khóa luận.">
      <button className="btn btn-secondary" disabled={busy} onClick={()=>{setError("");void load().catch(cause=>setError(errorMessage(cause)));}}><RefreshCw size={16} aria-hidden="true"/>Làm mới</button>
    </PageHeader>
    {error&&<p className="alert alert-danger" role="alert">{error}</p>}{notice&&<p className="alert alert-success" role="status">{notice}</p>}
    {!data&&!error&&<div className="stack" role="status" aria-label="Đang tải hồ sơ"><SkeletonCard /><SkeletonCard /></div>}
    {data&&<>
      <div className="changes-intro"><div className="changes-intro__icon"><FilePenLine aria-hidden="true"/></div>
        <div><strong>Theo dõi việc điều chỉnh KLTN</strong><p>Đề nghị trong 14 ngày đầu. Các bên xác nhận đúng nội dung trước khi bộ môn quyết định.</p></div>
        <span className="changes-count">{counts} yêu cầu đang xử lý</span></div>
      {context.base_role==="ADMIN"&&<Link to="/rounds" className="change-link">Quản lý thời gian mở đợt đăng ký <ChevronRight size={15} aria-hidden="true"/></Link>}
      {!data.theses.length&&!data.requests.length?<EmptyState icon={<FilePenLine aria-hidden="true"/>} title="Chưa có hồ sơ trong phạm vi của bạn" description="Hồ sơ xuất hiện sau khi đăng ký được giảng viên tiếp nhận."><Link to="/registrations" className="btn btn-secondary">Mở hồ sơ đăng ký</Link></EmptyState>:<div className="changes-layout">
        <aside className="changes-sidebar">
          {!!data.theses.length&&<section className="card"><div className="card-body stack"><h2>Khóa luận</h2>
            <label>Chọn hồ sơ<select className="input" value={selectedId} onChange={e=>{setParams({thesis:e.target.value});setNotice("");}}>
              <option value="">Tất cả hồ sơ</option>
              {!selected&&selectedId&&<option value={selectedId}>Hồ sơ từ thông báo</option>}
              {data.theses.map(t=><option key={t.id} value={t.id}>{t.title} · {t.round_label}</option>)}</select></label>
            {selected&&<>
              <p>SV · {selected.student_names?.join(", ")||"Chưa ghi nhận"} · GVHD · {selected.advisor_name||"Chưa ghi nhận"}</p>
              <p className="change-prose">{selected.description||"Xem chi tiết trong hồ sơ khóa luận."}</p>
              <Link className="change-link" to={"/theses/"+selected.id}>Mở hồ sơ khóa luận <ChevronRight size={15} aria-hidden="true"/></Link>
              <div className="changes-deadline"><CalendarClock size={19} aria-hidden="true"/><div><span>Hạn gửi đổi đề tài</span>
                <strong>{selected.cutoff?"Hết ngày "+shortDate(new Date(Date.parse(selected.cutoff)-1).toISOString()):"Chưa có ngày bắt đầu"}</strong></div></div>
              {selected.message&&<p className="change-note">{selected.message}</p>}
              {selected.can_request&&<button className="btn btn-primary" onClick={()=>open({kind:"create",thesis:selected})}><FilePenLine size={17} aria-hidden="true"/>Đề nghị đổi đề tài</button>}
              {selected.can_set_start&&!selected.starts_on&&<button className="btn btn-secondary" onClick={()=>open({kind:"start",thesis:selected})}>Thiết lập ngày bắt đầu</button>}
            </>}
          </div></section>}
          {selected&&<section className="card"><div className="card-body stack"><h2><CalendarClock size={19} aria-hidden="true"/> Gia hạn thực hiện</h2>
            {selected.extension?<div className="extension-receipt"><ThesisStatusBadge className="change-status" state="APPROVED" label="Đã ghi nhận một lần"/>
              <p>Hạn được gia hạn<strong>{when(selected.extension.until_at)}</strong></p>
              <details><summary>Xem quyết định</summary><dl><dt>Số / căn cứ</dt><dd>{selected.extension.reference}</dd><dt>Ngày quyết định</dt><dd>{shortDate(selected.extension.decision_on)}</dd>
                <dt>Bắt đầu theo quyết định</dt><dd>{when(selected.extension.extension_starts_at)}</dd><dt>Lý do</dt><dd>{selected.extension.reason}</dd><dt>Người ghi nhận</dt><dd>{selected.extension.recorded_by}</dd><dt>Thời điểm</dt><dd>{when(selected.extension.recorded_at)}</dd>
                <dt>Minh chứng</dt><dd>{selected.extension.file?<button type="button" className="btn btn-secondary btn-sm" onClick={()=>{
                  void downloadEvaluationFile(`/theses/${selected.id}/extension/evidence`,selected.extension!.file!.name).catch(cause=>setError(errorMessage(cause)));
                }}>Tải {selected.extension.file.name}</button>:"Chưa đính kèm"}</dd></dl></details></div>:<>
              <p className="text-muted">Theo dõi nguyện vọng gia hạn và kết quả xử lý. Chỉ ghi nhận một lần; ngày bắt đầu gia hạn phải theo quyết định đã đối chiếu.</p>
              <button className="btn btn-secondary" onClick={()=>setView("EXTENSION")}>{selected.can_request_extension?"Xin gia hạn / theo dõi":"Theo dõi yêu cầu gia hạn"}</button>
              <p className="change-note">{selected.extension_request_blocker||"SV gửi yêu cầu; nhóm đồng thuận, GVHD cho ý kiến rồi TBM xét theo căn cứ quyết định."}</p>
            </>}
          </div></section>}
        </aside>
        <section className="changes-main">
          <Tabs
            asButtons
            variant="underline"
            idPrefix="changes-mode"
            ariaLabel="Nghiệp vụ thay đổi"
            items={[
              {id:"CHANGE",label:"Đổi / tách đề tài"},
              {id:"EXTENSION",label:"Xin gia hạn KLTN"},
            ]}
            activeId={view}
            onChange={(next)=>setView(next as "CHANGE"|"EXTENSION")}
          />
          {view==="EXTENSION"?<ThesisExtensionRequests userId={context.user_id} thesis={selected} items={data.extension_requests||[]} reload={load} focusExtensionId={params.get("extension") || ""}/>:<>
          <div className="changes-toolbar"><h2><History size={19} aria-hidden="true"/>Yêu cầu đổi đề tài</h2><div className="changes-tools">
            <label className="changes-search"><span className="sr-only">Tìm yêu cầu</span><Search size={16} aria-hidden="true"/><input className="input" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Tìm đề tài hoặc mã…"/></label>
            <label><span className="sr-only">Trạng thái yêu cầu</span><select className="input" value={filter} onChange={e=>setFilter(e.target.value)}><option value="OPEN">Đang xử lý</option><option value="ALL">Tất cả và lịch sử</option></select></label>
          </div></div>
          {!requests.length?<EmptyState compact icon={<CheckCircle2 aria-hidden="true"/>} title="Không có yêu cầu trong bộ lọc" description="Yêu cầu mới và tiến trình xét duyệt sẽ hiển thị ở đây." />:
            requests.map(item=><ChangeCard key={item.id+":"+item.row_version} item={item} userId={context.user_id} open={open}/>)}
          </>}
        </section>
      </div>}
    </>}
    {operation&&<OperationDialog key={operation.kind+("item" in operation?operation.item.id:"")} operation={operation} busy={busy} error={dialogError}
      close={()=>{if(!busy)setOperation(null);}} submit={submit}/>}
  </div>;
}
