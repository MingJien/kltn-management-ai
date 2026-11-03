import {useCallback, useEffect, useState, type FormEvent} from "react";
import {Link, useSearchParams} from "react-router-dom";
import {FileDown, RefreshCw} from "lucide-react";
import {request, type Context, downloadWithdrawal} from "../api";
import {errorMessage} from "../errors";
import PageHeader from "../components/layout/PageHeader";
import {formatDate} from "../components/domain/CoreForms";

type Withdrawal = {id:string; code:string; thesis_id:string; title:string; student_name:string; student_code:string;
  reason:string; state:string; submitted_at:string; execution_starts_on:string; row_version:number;
  advisor_comment:string|null; advisor_reviewed_at:string|null; official_reference:string|null; outcome_note:string|null;
  recorded_at:string|null; effective_on:string|null; evidence_name:string|null; scan_state:string|null;
  can_cancel:boolean; can_confirm:boolean; can_record:boolean; can_upload:boolean;
  history:{action:string; reason:string; at:string; actor:string}[]};
type Round = {id:string; code:string; starts_on:string|null; reference:string|null; row_version:number; can_edit:boolean};
type Thesis = {id:string; title:string; round_code:string; starts_on:string|null; last_request_on:string|null; can_submit:boolean; message:string};
type Workspace = {requests:Withdrawal[]; rounds:Round[]; theses:Thesis[]};
const labels:Record<string,string> = {SUBMITTED:"Chờ GVHD xác nhận",ADVISOR_CONFIRMED:"Chờ kết quả xử lý bên ngoài",
  RETURNED:"GVHD trả lại đơn",CANCELLED:"Đã hủy yêu cầu",RECORDED:"Đã ghi nhận thôi KLTN",NOT_GRANTED:"Không chấp thuận xin thôi"};
const eventLabels:Record<string,string> = {WITHDRAWAL_SUBMITTED:"SV gửi đơn",WITHDRAWAL_ADVISOR_CONFIRMED:"GVHD xác nhận",
  WITHDRAWAL_RETURNED:"GVHD trả lại",WITHDRAWAL_CANCELLED:"SV hủy yêu cầu",WITHDRAWAL_SIGNED_COPY_ADDED:"Bổ sung bản có xác nhận",
  WITHDRAWAL_FILE_SCANNED:"Kiểm tra an toàn tệp",WITHDRAWAL_RECORDED:"Ghi nhận kết quả xin thôi",WITHDRAWAL_NOT_GRANTED:"Ghi nhận không chấp thuận",
  WITHDRAWAL_PRINT_EXPORTED:"Xuất phiếu để in"};
const date = (v:string|null) => v ? v.split("-").reverse().join("/") : "Chưa thiết lập";
type Run = (action:()=>Promise<unknown>,success:string)=>Promise<boolean>;

function RoundStart({row,run,userId,busy}:{row:Round;run:Run;userId:string;busy:boolean}) {
  const [start,setStart]=useState(row.starts_on||""); const [reference,setReference]=useState(row.reference||"");
  return <details className="card"><summary className="card-body"><strong>{row.code}</strong> · Bắt đầu: {date(row.starts_on)}</summary>
    <form className="card-body stack" onSubmit={e=>{e.preventDefault();void run(()=>request(`/withdrawal-rounds/${row.id}/start`,userId,
      {method:"PUT",headers:{"If-Match":String(row.row_version)},body:JSON.stringify({starts_on:start,reference})}),"Đã ghi nhận ngày bắt đầu theo kế hoạch Khoa.");}}>
      <p className="text-muted">Ngày bắt đầu dùng tính 02 tuần xin thôi, khác thời gian mở đăng ký. Khi đã có đơn, ngày này được giữ nguyên.</p>
      {row.can_edit ? <><label>Ngày bắt đầu thực hiện<input className="input" type="date" required value={start} onChange={e=>setStart(e.target.value)}/></label>
        <label>Căn cứ kế hoạch Khoa<input className="input" required minLength={5} maxLength={500} value={reference} onChange={e=>setReference(e.target.value)}/></label>
        <button className="btn btn-secondary" disabled={busy||reference.trim().length<5}>Lưu ngày bắt đầu</button></> : <p>Đã khóa ngày bắt đầu. Căn cứ: {row.reference}</p>}
    </form></details>;
}

function CreateRequest({thesis,run,userId,busy,focused}:{thesis:Thesis;run:Run;userId:string;busy:boolean;focused:boolean}) {
  const [reason,setReason]=useState(""); const [confirm,setConfirm]=useState(false);
  async function submit(e:FormEvent) {
    e.preventDefault();
    const ok=await run(()=>request(`/theses/${thesis.id}/withdrawals`,userId,{method:"POST",body:JSON.stringify({reason,confirm_replacement:confirm})}),
      "Đã gửi yêu cầu đến GVHD. Bạn vẫn tiếp tục tham gia KLTN trong lúc chờ kết quả.");
    if(ok){setReason("");setConfirm(false);}
  }
  return <section className="card" id={`withdrawal-thesis-${thesis.id}`}><div className="card-body stack"><h2>{thesis.title}</h2>
    <p>{thesis.round_code} · Bắt đầu: <strong>{date(thesis.starts_on)}</strong> · Hạn gửi đơn: <strong>{thesis.last_request_on?`hết ngày ${date(thesis.last_request_on)}`:"Chưa thiết lập"}</strong></p>
    <Link to={`/theses/${thesis.id}`}>Mở hồ sơ khóa luận</Link>
    {thesis.can_submit ? <details open={focused}><summary>Lập yêu cầu xin thôi KLTN</summary><form className="stack" onSubmit={e=>void submit(e)} style={{marginTop:16}}>
      <label>Lý do xin thôi<textarea className="input" rows={4} required minLength={10} maxLength={3000} value={reason} onChange={e=>setReason(e.target.value)}/></label>
      <label><input type="checkbox" checked={confirm} onChange={e=>setConfirm(e.target.checked)} required/> Tôi đề nghị chuyển sang học phần thay thế và đã đọc hệ quả không được đăng ký lại KLTN sau khi hủy đăng ký chính thức (Điều 4 khoản 6, QĐ2919).</label>
      <p className="text-muted">Đơn chỉ áp dụng cho bạn. Gửi đơn chưa có nghĩa đã được giải quyết cho thôi KLTN.</p>
      <button className="btn btn-primary" disabled={busy||!confirm||reason.trim().length<10}>Gửi đơn đến GVHD</button>
    </form></details> : <p className="alert alert-info">{thesis.message}</p>}
  </div></section>;
}

function RequestCard({row,run,userId,busy,focused}:{row:Withdrawal;run:Run;userId:string;busy:boolean;focused:boolean}) {
  const [comment,setComment]=useState("");const [decision,setDecision]=useState("CONFIRM");
  const [file,setFile]=useState<File|null>(null);const [reference,setReference]=useState("");const [note,setNote]=useState("");
  const [outcome,setOutcome]=useState("WITHDRAWN");const [effective,setEffective]=useState(new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Ho_Chi_Minh"}).format(new Date()));
  const [confirm,setConfirm]=useState(false);
  const call=(suffix:string,body?:object)=>request(`/withdrawals/${row.id}/${suffix}`,userId,{method:"POST",headers:{"If-Match":String(row.row_version)},body:body?JSON.stringify(body):undefined});
  return <article className="card" id={`withdrawal-${row.id}`} style={focused?{outline:"2px solid var(--color-primary, #008a88)"}:undefined}><div className="card-body stack">
    <div className="flex justify-between gap-3" style={{flexWrap:"wrap"}}><div><h2>{row.student_name} · {row.student_code}</h2><p>{row.title}</p></div><strong className="badge">{labels[row.state]}</strong></div>
    <ol className="flex gap-3 text-caption" style={{flexWrap:"wrap",paddingLeft:20}} aria-label="Các bước xử lý"><li>SV gửi đơn</li><li>GVHD xác nhận</li><li>Xử lý bên ngoài và ghi nhận kết quả</li></ol>
    <p className="text-caption">Mã: {row.code} · Gửi lúc: {formatDate(row.submitted_at)}</p>
    <p className="core-prewrap"><strong>Lý do: </strong>{row.reason}</p>
    <div className="flex gap-2" style={{flexWrap:"wrap"}}><button className="btn btn-secondary" disabled={busy} onClick={()=>void run(()=>downloadWithdrawal(row.id,true),"Đã xuất phiếu để in, ký và nộp theo hướng dẫn của Khoa.")}><FileDown size={16}/>Xuất phiếu để in / ký</button>
      {row.can_cancel && <button className="btn btn-secondary" disabled={busy} onClick={()=>{if(window.confirm("Hủy yêu cầu xin thôi này? Bạn vẫn tiếp tục KLTN."))void run(()=>call("cancel"),"Đã hủy yêu cầu; hồ sơ KLTN vẫn được giữ.");}}>Hủy yêu cầu xin thôi</button>}</div>
    {row.advisor_comment && <div className="alert alert-info"><strong>Ý kiến GVHD · {formatDate(row.advisor_reviewed_at)}</strong><p className="core-prewrap">{row.advisor_comment}</p></div>}
    {row.can_confirm && <form className="stack" onSubmit={e=>{e.preventDefault();void run(()=>call("advisor-decision",{decision,comment}),decision==="CONFIRM"?"GVHD đã xác nhận; đơn chuyển sang bước xử lý bên ngoài.":"Đã trả lại đơn kèm ý kiến.");}}>
      <h3>Xác nhận của GVHD</h3><label>Ý kiến xử lý<select className="input" value={decision} onChange={e=>setDecision(e.target.value)}><option value="CONFIRM">Xác nhận đơn xin thôi</option><option value="RETURN">Trả lại để SV đối chiếu</option></select></label>
      <label>Ý kiến / lý do của GVHD<textarea className="input" rows={3} minLength={5} maxLength={3000} required value={comment} onChange={e=>setComment(e.target.value)}/></label>
      <p className="text-muted">Xác nhận của GVHD chưa kết thúc việc tham gia KLTN của sinh viên.</p>
      <button className="btn btn-primary" disabled={busy||comment.trim().length<5}>Gửi xác nhận của GVHD</button>
    </form>}
    {row.state==="ADVISOR_CONFIRMED" && <p className="alert alert-info">In phiếu hoặc dùng mẫu Khoa hướng dẫn → xin chữ ký/xác nhận và nộp đơn bên ngoài → bổ sung bản có xác nhận. Điều phối ghi nhận khi có kết quả xử lý.</p>}
    {row.evidence_name && <div className="card"><div className="card-body stack"><strong>Bản đơn có xác nhận: {row.evidence_name}</strong>
      <p>{row.scan_state==="CLEAN"?"Đã quét an toàn bằng bộ quét tệp của hệ thống.":"Tệp chưa đạt kiểm tra an toàn; chưa thể tải hoặc ghi nhận kết quả."}</p>
      <div className="flex gap-2"><button className="btn btn-secondary" disabled={busy||row.scan_state!=="CLEAN"} onClick={()=>void run(()=>downloadWithdrawal(row.id,false),"Đã tải bản có xác nhận.")}>Tải bản có xác nhận</button>
        {row.can_upload&&row.scan_state!=="CLEAN"&&<button className="btn btn-secondary" disabled={busy} onClick={()=>void run(()=>call("scan"),"Đã kiểm tra lại an toàn tệp.")}>Quét lại tệp</button>}</div>
    </div></div>}
    {row.can_upload && <form className="stack" onSubmit={e=>{e.preventDefault();if(file)void run(()=>request(`/withdrawals/${row.id}/signed-copy`,userId,{method:"POST",headers:{"If-Match":String(row.row_version),"X-File-Name":encodeURIComponent(file.name),"Content-Type":"application/octet-stream"},body:file}),"Đã lưu bản đơn có xác nhận.").then(ok=>{if(ok)setFile(null);});}}>
      <label>{row.evidence_name?"Bổ sung bản có xác nhận thay bản hiện tại":"Nộp bản đơn có xác nhận (PDF/DOCX, tối đa 10 MB)"}<input key={row.row_version} className="input" type="file" accept=".pdf,.docx" required onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
      <button className="btn btn-secondary" disabled={busy||!file}>Lưu bản có xác nhận</button>
    </form>}
    {row.can_record && <details><summary>Ghi nhận kết quả đã xử lý bên ngoài</summary><form className="stack" style={{marginTop:16}} onSubmit={e=>{e.preventDefault();void run(()=>call("outcome",{outcome,reference,note,effective_on:effective,confirm_evidence:confirm}),"Đã ghi nhận kết quả và cập nhật hồ sơ liên quan.");}}>
      <label>Kết quả xử lý<select className="input" value={outcome} onChange={e=>{setOutcome(e.target.value);setConfirm(false);}}><option value="WITHDRAWN">Đã giải quyết cho SV thôi thực hiện KLTN</option><option value="NOT_GRANTED">Không chấp thuận xin thôi; SV tiếp tục thực hiện</option></select></label>
      <label>Số / căn cứ văn bản xử lý<input className="input" required minLength={5} maxLength={500} value={reference} onChange={e=>setReference(e.target.value)}/></label>
      <label>Ngày kết quả có hiệu lực<input className="input" type="date" required min={new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Ho_Chi_Minh"}).format(new Date(row.submitted_at))} max={new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Ho_Chi_Minh"}).format(new Date())} value={effective} onChange={e=>setEffective(e.target.value)}/></label>
      <label>Nội dung ghi nhận<textarea className="input" required minLength={5} maxLength={3000} value={note} onChange={e=>setNote(e.target.value)}/></label>
      {outcome==="WITHDRAWN"&&<p className="alert alert-warning">Khi ghi nhận: SV ngừng tham gia và không được đăng ký lại KLTN; nhóm còn lại tiếp tục cùng đề tài và nộp lại đề cương để duyệt. Nếu không còn thành viên, hồ sơ chuyển Đã rút.</p>}
      <label><input type="checkbox" required checked={confirm} onChange={e=>setConfirm(e.target.checked)}/> Tôi đã đối chiếu bản có xác nhận với kết quả xử lý bên ngoài.</label>
      {row.scan_state!=="CLEAN"&&<p className="text-danger">Cần bổ sung bản đơn có xác nhận đã qua kiểm tra an toàn trước khi ghi nhận.</p>}
      <button className="btn btn-primary" disabled={busy||!confirm||row.scan_state!=="CLEAN"||reference.trim().length<5||note.trim().length<5}>Ghi nhận kết quả bên ngoài</button>
    </form></details>}
    {row.recorded_at&&<div className="alert alert-info"><strong>{labels[row.state]} · {date(row.effective_on)}</strong><p>Căn cứ: {row.official_reference}</p><p className="core-prewrap">{row.outcome_note}</p><small>Ghi nhận lúc {formatDate(row.recorded_at)}</small></div>}
    <details><summary>Lịch sử xử lý ({row.history.length})</summary><ol>{row.history.map((h,i)=><li key={i} style={{marginTop:12}}><strong>{eventLabels[h.action]||h.action}</strong> · {h.actor} · {formatDate(h.at)}<p className="core-prewrap">{h.reason}</p></li>)}</ol></details>
  </div></article>;
}

export default function WithdrawalsPage({context}:{context:Context}) {
  const [data,setData]=useState<Workspace|null>(null);const [error,setError]=useState("");const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);
  const [params]=useSearchParams(); const [filter,setFilter]=useState("ALL");
  const load=useCallback(async()=>{setData(await request<Workspace>("/withdrawals",context.user_id));},[context.user_id]);
  useEffect(()=>{void load().catch(e=>setError(errorMessage(e)));},[load]);
  const run:Run=async(action,success)=>{if(busy)return false;setBusy(true);setError("");setMessage("");try{await action();await load();setMessage(success);return true;}catch(e){setError(errorMessage(e));await load().catch(()=>undefined);return false;}finally{setBusy(false);}};
  const focus=params.get("focus");
  useEffect(()=>{if(focus&&data)document.getElementById(`withdrawal-${focus}`)?.scrollIntoView({block:"start",behavior:"smooth"});},[focus,data]);
  const rows=data?.requests.filter(r=>filter==="ALL"||["SUBMITTED","ADVISOR_CONFIRMED"].includes(r.state)||r.id===focus)||[];
  return <div className="withdrawal-page"><PageHeader title="Xin thôi thực hiện KLTN" description="Theo dõi đơn theo từng sinh viên, xác nhận GVHD và kết quả xử lý bên ngoài."><button className="btn btn-secondary" disabled={busy} onClick={()=>void run(load,"Đã làm mới hồ sơ.")}><RefreshCw size={16}/>Làm mới</button></PageHeader>
    <div className="stack">{error&&<p className="alert alert-danger" role="alert">{error}</p>}{message&&<p className="alert alert-success" role="status">{message}</p>}
      <p className="alert alert-info">Điều 4 QĐ2919: xin thôi trong 02 tuần đầu kể từ ngày bắt đầu thực hiện; có đơn và xác nhận GVHD. Hồ sơ chỉ thay đổi sau khi Khoa ghi nhận kết quả xử lý. Gửi yêu cầu không tự hủy đăng ký.</p>
      <details className="card"><summary className="card-body">Nhóm còn lại tiếp tục đề tài như thế nào?</summary><div className="card-body stack"><ol><li>SV xin rút gửi đơn; GVHD xác nhận; điều phối đợt ghi nhận kết quả đã xử lý theo hồ sơ có xác nhận.</li><li>Trước khi có kết quả cho rút, nhóm và đề cương đang được giữ nguyên.</li><li>Sau khi ghi nhận cho rút, thành viên còn lại giữ đề tài và GVHD; người đại diện nhóm được chuyển nếu cần.</li><li>Mở Hồ sơ nộp &amp; xét duyệt → Đề cương, cập nhật thành viên, phạm vi và phân công; nộp bản mới để GVHD xác nhận và TBM chốt lại.</li><li>Cập nhật cuốn báo cáo, lập Mẫu 7/8 và xét điều kiện theo hồ sơ mới. Không dùng lại xác nhận đề cương hoặc nhận xét gắn báo cáo cũ.</li></ol><p>Không phải chọn đề tài khác chỉ vì nhóm giảm thành viên. Các bản cũ được giữ để đối chiếu; lý do xin rút chỉ người có quyền xử lý được xem.</p></div></details>
      {!data&&!error&&<p role="status">Đang tải hồ sơ…</p>}
      {data&&data.rounds.length>0&&<section className="stack"><h2>Ngày bắt đầu theo kế hoạch Khoa</h2>{data.rounds.map(r=><RoundStart key={r.id+":"+r.row_version} row={r} run={run} userId={context.user_id} busy={busy}/>)}</section>}
      {data&&context.base_role==="STUDENT"&&<section className="stack"><h2>Khóa luận đang thực hiện</h2>{data.theses.length?data.theses.map(t=><CreateRequest key={t.id} thesis={t} focused={params.get("thesis")===t.id} run={run} userId={context.user_id} busy={busy}/>):<p>Chưa có khóa luận đang thực hiện. Các yêu cầu đã gửi vẫn xem được ở lịch sử bên dưới.</p>}</section>}
      {data&&<section className="stack"><div className="flex justify-between gap-3"><h2>Đơn xin thôi trong phạm vi của bạn</h2><label>Hiển thị<select aria-label="Hiển thị" className="input" value={filter} onChange={e=>setFilter(e.target.value)}><option value="OPEN">Đang xử lý</option><option value="ALL">Tất cả và lịch sử</option></select></label></div>
        {!rows.length&&<p>Không có đơn trong bộ lọc này.</p>}{rows.map(r=><RequestCard key={r.id+":"+r.row_version} row={r} run={run} userId={context.user_id} busy={busy} focused={r.id===focus}/>)}</section>}
    </div></div>;
}
