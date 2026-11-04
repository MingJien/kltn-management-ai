import { useState } from "react";
import type { AuditEvent, DocumentDeadline, Thesis } from "../../api";
import { request } from "../../api";
import type { CoreRun } from "./ThesisDocuments";
import { formatDate } from "./CoreForms";

const names = {PROPOSAL:"Đề cương (Mẫu 3)", PLAN:"Kế hoạch thực hiện (Mẫu 2)", REPORT:"Cuốn báo cáo KLTN", SUPPORTING:"Tài liệu hỗ trợ"};
type Kind = keyof typeof names;

export default function DocumentDeadlines({thesis,deadlines,history,userId,busy,run,kinds=["PROPOSAL","PLAN","REPORT"]}: {
  thesis:Thesis; deadlines:DocumentDeadline[]; history:AuditEvent[]; userId:string; busy:boolean; run:CoreRun; kinds?:Kind[];
}) {
  const [kind,setKind] = useState<Kind>(kinds[0]);
  const [dueAt,setDueAt] = useState("");
  const [reason,setReason] = useState("");
  const [closeReason,setCloseReason] = useState("");
  const selected = deadlines.find(item=>item.document_type === kind);
  const canManage = thesis.actions.includes("milestone:manage");
  const relevantHistory=history.filter(item=>kinds.some(type=>(item.reason || "").startsWith(type+":")));
  const labels:Record<string,string> = {DOCUMENT_DEADLINE_SET:"Thiết lập hạn",DOCUMENT_DEADLINE_EXTENDED:"Gia hạn",DOCUMENT_DEADLINE_REOPENED:"Gia hạn và mở nhận lại",DOCUMENT_DEADLINE_CLOSED:"Đóng nhận"};
  return <section className="card"><div className="card-body stack">
    <h2>{kinds.length===1 && kinds[0]==="PROPOSAL" ? "Lịch nhận đề cương của đợt" : "Lịch nhận tài liệu của đợt"}</h2>
    <p className="text-body-sm text-muted">Áp dụng cho toàn đợt {thesis.round_label}. Cửa nhận còn mở vẫn nhận bài trễ và đánh dấu ! đỏ; gia hạn giữ nguyên hạn đã ghi trên bản nộp cũ.</p>
    {kinds.map(type => {
      const item = deadlines.find(row=>row.document_type===type);
      return <p key={type}><strong>{names[type]}:</strong> {item ? `${formatDate(item.due_at)} · ${item.state === "OPEN" ? "Đang nhận" : "Đã đóng"}` : "Chưa thiết lập — chưa nhận tệp"}</p>;
    })}
    {thesis.extension_until_at && kinds.includes("REPORT") && <p className="alert alert-info">
      Khóa luận này được gia hạn nộp báo cáo đến <strong>{formatDate(thesis.extension_until_at)}</strong>.
      <a href={`/changes?thesis=${thesis.id}`}> Xem quyết định gia hạn</a>
    </p>}
    <p className="text-caption">Chỉ người được giao điều phối đợt được đặt/gia hạn lịch. GVHD có thể yêu cầu sửa từng bản nộp; các báo cáo định kỳ được quản lý ở mục Báo cáo tiến độ.</p>
    {canManage && <form className="core-form" onSubmit={async event=>{
      event.preventDefault();
      if (await run(()=>request(`/theses/${thesis.id}/document-deadlines`,userId,{
        method:"POST", headers:selected ? {"If-Match":String(selected.row_version)} : {},
        body:JSON.stringify({document_type:kind,due_at:new Date(dueAt+"+07:00").toISOString(),reason}),
      }),selected ? "Đã gia hạn loại tài liệu cho toàn đợt." : "Đã thiết lập hạn tài liệu cho toàn đợt.")) {setDueAt("");setReason("");}
    }}>
      <h3>Thiết lập / gia hạn hạn nộp</h3>
      <div className="input-group"><label htmlFor="deadline-kind">Loại tài liệu</label><select id="deadline-kind" className="input" value={kind} onChange={event=>setKind(event.target.value as Kind)} disabled={busy}>
        {kinds.map(type=><option value={type} key={type}>{names[type]}</option>)}
      </select></div>
      <div className="input-group"><label htmlFor="deadline-due">Hạn mới (giờ Việt Nam)</label><input id="deadline-due" className="input" type="datetime-local" required value={dueAt} onChange={event=>setDueAt(event.target.value)} disabled={busy} /></div>
      <div className="input-group"><label htmlFor="deadline-reason">Căn cứ / lý do</label><textarea id="deadline-reason" className="input" required minLength={3} maxLength={2000} value={reason} onChange={event=>setReason(event.target.value)} disabled={busy} /></div>
      <button className="btn btn-primary" disabled={busy || !dueAt || reason.trim().length<3}>{selected?.state === "CLOSED" ? "Gia hạn và mở nhận lại cả đợt" : selected ? "Gia hạn cho cả đợt" : "Thiết lập cho cả đợt"}</button>
    </form>}
    {canManage && selected?.state === "OPEN" && <details><summary>Đóng nhận {names[kind]} cho cả đợt</summary><form className="core-form" onSubmit={async event=>{
      event.preventDefault();
      if (await run(()=>request(`/theses/${thesis.id}/document-deadlines/${kind}/close`,userId,{
        method:"POST",headers:{"If-Match":String(selected.row_version)},body:JSON.stringify({reason:closeReason}),
      }),"Đã đóng nhận tài liệu này cho toàn đợt; GVHD vẫn có thể yêu cầu sửa từng bản.")) setCloseReason("");
    }}><label htmlFor="deadline-close-reason">Lý do đóng</label><textarea id="deadline-close-reason" className="input" required minLength={3} maxLength={2000} value={closeReason} onChange={event=>setCloseReason(event.target.value)} disabled={busy} />
      <button className="btn btn-secondary" disabled={busy || closeReason.trim().length<3}>Đóng nhận cho cả đợt</button></form></details>}
    <details><summary>Lịch sử hạn nộp tài liệu của đợt</summary><div className="stack">
      {relevantHistory.length ? relevantHistory.map((item,index)=><p key={`${item.occurred_at}-${index}`}><strong>{item.actor_name}</strong> · {labels[item.action] || item.action} · {formatDate(item.occurred_at)}<br />{item.reason}</p>) : <p>Chưa có thay đổi hạn nộp.</p>}
    </div></details>
  </div></section>;
}
