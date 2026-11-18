import {useCallback, useEffect, useState, type FormEvent} from "react";
import {Link, useSearchParams} from "react-router-dom";
import {request, type Context} from "../api";
import {errorMessage} from "../errors";
import PageHeader from "../components/layout/PageHeader";
import WorkflowSteps from "../components/domain/WorkflowSteps";
import "../styles/withdrawals.css";

type Withdrawal = {id:string; code:string; title:string; student_name:string; student_code:string; advisor_name?:string|null;
  reason:string; state:string; submitted_at:string; row_version:number; outcome_note:string|null;
  effective_on:string|null; can_cancel:boolean; can_record:boolean; history:{action:string;at:string;actor:string}[]};
type Round = {id:string; code:string; starts_on:string|null; reference:string|null; row_version:number; can_edit:boolean};
type Thesis = {id:string; title:string; student_name?:string; advisor_name?:string|null; round_code:string; starts_on:string|null; last_request_on:string|null; can_submit:boolean; message:string};
type Workspace = {requests:Withdrawal[]; rounds:Round[]; theses:Thesis[]};
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
      "Đã gửi yêu cầu đến điều phối đợt. Bạn vẫn tiếp tục tham gia KLTN trong lúc chờ kết quả.");
    if(ok){setReason("");setConfirm(false);}
  }
  return <section className="card" id={`withdrawal-thesis-${thesis.id}`}><div className="card-body stack"><h2>{thesis.title}</h2><p>SV · {thesis.student_name} · GVHD · {thesis.advisor_name||"Chưa ghi nhận"}</p><WorkflowSteps steps={["Gửi yêu cầu","Điều phối xử lý","Nhận kết quả"]} current={0}/>
    <p>{thesis.round_code} · Bắt đầu: <strong>{date(thesis.starts_on)}</strong> · Hạn gửi đơn: <strong>{thesis.last_request_on?`hết ngày ${date(thesis.last_request_on)}`:"Chưa thiết lập"}</strong></p>
    <Link to={`/theses/${thesis.id}`}>Mở hồ sơ khóa luận</Link>
    {thesis.can_submit ? <details open={focused}><summary>Lập yêu cầu xin thôi KLTN</summary><form className="stack" onSubmit={e=>void submit(e)} style={{marginTop:16}}>
      <label>Lý do xin thôi<textarea className="input" rows={4} required minLength={10} maxLength={3000} value={reason} onChange={e=>setReason(e.target.value)}/></label>
      <label><input type="checkbox" checked={confirm} onChange={e=>setConfirm(e.target.checked)} required/> Tôi đề nghị chuyển sang học phần thay thế và đã đọc hệ quả không được đăng ký lại KLTN sau khi hủy đăng ký chính thức (Điều 4 khoản 6, QĐ2919).</label>
      <p className="text-muted">Đơn chỉ áp dụng cho bạn. Gửi đơn chưa có nghĩa đã được giải quyết cho thôi KLTN.</p>
      <button className="btn btn-primary" disabled={busy||!confirm||reason.trim().length<10}>Gửi đơn đến điều phối đợt</button>
    </form></details> : <p className="alert alert-info">{thesis.message}</p>}
  </div></section>;
}

const pending = (state:string) => ["SUBMITTED","ADVISOR_CONFIRMED"].includes(state);
const status = (state:string) => pending(state) ? "Chờ điều phối xử lý" :
  ({RECORDED:"Đã chấp thuận",NOT_GRANTED:"Không chấp thuận",CANCELLED:"Đã hủy",RETURNED:"Đã trả lại"}[state] ?? state);

function RequestCard({row,run,userId,busy}:{row:Withdrawal;run:Run;userId:string;busy:boolean}) {
  const [note,setNote]=useState("");
  const [decision,setDecision]=useState("WITHDRAWN");
  function send(path:string, payload:unknown, success:string) {
    return run(()=>request(`/withdrawals/${row.id}/${path}`,userId,{
      method:"POST",headers:{"If-Match":String(row.row_version)},body:JSON.stringify(payload)
    }),success);
  }
  return <article className="card" id={`withdrawal-${row.id}`}><div className="card-body stack">
    <h3>{row.title}</h3><p><strong>{row.student_name}</strong> · {row.student_code} · GVHD · {row.advisor_name||"Chưa ghi nhận"} · <span>{status(row.state)}</span></p>
    <p className="text-muted">{row.code} · Gửi lúc {new Date(row.submitted_at).toLocaleString("vi-VN")}</p>
    <p style={{whiteSpace:"pre-wrap"}}>{row.reason}</p>
    {row.outcome_note && <p><strong>Kết quả ngày {date(row.effective_on)}</strong> · {row.outcome_note}</p>}
    {row.can_cancel && <button className="btn btn-secondary" disabled={busy}
      onClick={()=>{if(window.confirm("Hủy yêu cầu và tiếp tục thực hiện KLTN?")) void send("cancel",{},"Đã hủy yêu cầu.");}}>Hủy yêu cầu</button>}
    {row.can_record && <form className="stack" onSubmit={e=>{
      e.preventDefault();
      if(window.confirm(decision==="WITHDRAWN"?"Chấp thuận và cập nhật hồ sơ KLTN ngay?":"Xác nhận không chấp thuận?"))
        void send("outcome",{outcome:decision,note},"Đã cập nhật kết quả xử lý.");
    }}>
      <label>Kết quả<select className="input" value={decision} onChange={e=>setDecision(e.target.value)}>
        <option value="WITHDRAWN">Chấp thuận cho thôi</option><option value="NOT_GRANTED">Không chấp thuận</option>
      </select></label>
      <label>Lý do xử lý<textarea className="input" value={note} onChange={e=>setNote(e.target.value)} required minLength={5} maxLength={3000}/></label>
      <button className="btn btn-primary" disabled={busy||note.trim().length<5}>Xác nhận kết quả</button>
    </form>}
    <details><summary>Lịch sử xử lý</summary><ul>{row.history.map((event,i)=>
      <li key={i}>{new Date(event.at).toLocaleString("vi-VN")} · {event.actor} · {
        ({WITHDRAWAL_SUBMITTED:"Gửi yêu cầu",WITHDRAWAL_RECORDED:"Chấp thuận",WITHDRAWAL_NOT_GRANTED:"Không chấp thuận",WITHDRAWAL_CANCELLED:"Hủy yêu cầu"} as Record<string,string>)[event.action] ?? "Cập nhật hồ sơ"
      }</li>)}</ul></details>
  </div></article>;
}

export default function WithdrawalsPage({context}:{context:Context}) {
  const [params]=useSearchParams();
  const [data,setData]=useState<Workspace>();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");
  const [all,setAll]=useState(false);
  const load=useCallback(async()=>setData(await request<Workspace>("/withdrawals",context.user_id)),[context.user_id]);
  useEffect(()=>{void load().catch(e=>setError(errorMessage(e)));},[load]);
  const focus=params.get("focus");
  useEffect(()=>{if(focus&&data)document.getElementById(`withdrawal-${focus}`)?.scrollIntoView({block:"start"});},[focus,data]);
  const run:Run=async(action,success)=>{
    setBusy(true);setError("");setMessage("");
    try {await action();await load();setMessage(success);return true;}
    catch(e){setError(errorMessage(e));await load().catch(()=>undefined);return false;}
    finally{setBusy(false);}
  };
  const rows=data?.requests.filter(row=>all||pending(row.state)||row.id===focus)??[];
  return <div className="withdrawal-page">
    <PageHeader title="Xin thôi thực hiện KLTN" description="Sinh viên gửi yêu cầu, điều phối đợt xử lý và thông báo kết quả trên hệ thống."/>
    <div className="stack">
      {error&&<p className="alert alert-danger" role="alert">{error}</p>}
      {message&&<p className="alert alert-success" role="status">{message}</p>}
      <p className="alert alert-info">Gửi trong 02 tuần đầu kể từ ngày bắt đầu thực hiện. Sinh viên tiếp tục làm KLTN trong khi chờ xử lý. Nếu nhóm còn thành viên sau khi chấp thuận, nhóm giữ đề tài và nộp lại Mẫu 1–3 theo thành viên hiện tại.</p>
      {!data&&!error&&<p role="status">Đang tải…</p>}
      {!!data?.rounds.length&&<section className="stack"><h2>Ngày bắt đầu thực hiện</h2>{data.rounds.map(row=>
        <RoundStart key={row.id+row.row_version} row={row} run={run} userId={context.user_id} busy={busy}/>)}</section>}
      {data?.theses.map(thesis=><CreateRequest key={thesis.id} thesis={thesis} focused={params.get("thesis")===thesis.id}
        run={run} userId={context.user_id} busy={busy}/>)}
      {data&&<section className="stack"><h2>Yêu cầu xin thôi</h2><label><input type="checkbox" checked={all} onChange={e=>setAll(e.target.checked)}/> Hiện cả yêu cầu đã xử lý</label>
        {!rows.length&&<p>Không có yêu cầu trong bộ lọc này.</p>}
        {rows.map(row=><RequestCard key={row.id+row.row_version} row={row} run={run} userId={context.user_id} busy={busy}/>)}
      </section>}
    </div>
  </div>;
}
