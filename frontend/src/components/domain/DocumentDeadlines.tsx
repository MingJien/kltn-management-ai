import { useState } from "react";
import type { DocumentDeadline, Thesis } from "../../api";
import { request } from "../../api";
import type { CoreRun } from "./ThesisDocuments";
import { formatDate } from "./CoreForms";

const names = {PROPOSAL:"Đề cương (Mẫu 3)", PLAN:"Kế hoạch thực hiện (Mẫu 2)", SUPPORTING:"Tài liệu hỗ trợ"};
type Kind = keyof typeof names;

export default function DocumentDeadlines({thesis,deadlines,userId,busy,run}: {
  thesis:Thesis; deadlines:DocumentDeadline[]; userId:string; busy:boolean; run:CoreRun;
}) {
  const [kind,setKind] = useState<Kind>("PROPOSAL");
  const [dueAt,setDueAt] = useState("");
  const [reason,setReason] = useState("");
  const [closeReason,setCloseReason] = useState("");
  const selected = deadlines.find(item=>item.document_type === kind);
  const canManage = thesis.actions.includes("milestone:manage");
  return <section className="card"><div className="card-body stack">
    <h2>Hạn nộp tài liệu theo đợt</h2>
    <p className="text-body-sm text-muted">Khoa đặt hạn riêng cho từng loại tài liệu, áp dụng cho toàn đợt {thesis.round_label}. Bản nộp sau hạn khi cửa nhận còn mở được đánh dấu ! đỏ. Gia hạn giữ nguyên hạn đã ghi trên các bản nộp cũ.</p>
    {(["PROPOSAL","PLAN","SUPPORTING"] as Kind[]).map(type => {
      const item = deadlines.find(row=>row.document_type===type);
      return <p key={type}><strong>{names[type]}:</strong> {item ? `${formatDate(item.due_at)} · ${item.state === "OPEN" ? "Đang nhận" : "Đã đóng"}` : "Chưa thiết lập — chưa nhận tệp"}</p>;
    })}
    {canManage && <form className="core-form" onSubmit={async event=>{
      event.preventDefault();
      if (await run(()=>request(`/theses/${thesis.id}/document-deadlines`,userId,{
        method:"POST", headers:selected ? {"If-Match":String(selected.row_version)} : {},
        body:JSON.stringify({document_type:kind,due_at:new Date(dueAt+"+07:00").toISOString(),reason}),
      }),selected ? "Đã gia hạn loại tài liệu cho toàn đợt." : "Đã thiết lập hạn tài liệu cho toàn đợt.")) {setDueAt("");setReason("");}
    }}>
      <h3>Thiết lập / gia hạn hạn nộp</h3>
      <div className="input-group"><label htmlFor="deadline-kind">Loại tài liệu</label><select id="deadline-kind" className="input" value={kind} onChange={event=>setKind(event.target.value as Kind)} disabled={busy}>
        {(["PROPOSAL","PLAN","SUPPORTING"] as Kind[]).map(type=><option value={type} key={type}>{names[type]}</option>)}
      </select></div>
      <div className="input-group"><label htmlFor="deadline-due">Hạn mới (giờ Việt Nam)</label><input id="deadline-due" className="input" type="datetime-local" required value={dueAt} onChange={event=>setDueAt(event.target.value)} disabled={busy || selected?.state === "CLOSED"} /></div>
      <div className="input-group"><label htmlFor="deadline-reason">Căn cứ / lý do</label><textarea id="deadline-reason" className="input" required minLength={3} maxLength={2000} value={reason} onChange={event=>setReason(event.target.value)} disabled={busy || selected?.state === "CLOSED"} /></div>
      <button className="btn btn-primary" disabled={busy || selected?.state === "CLOSED" || !dueAt || reason.trim().length<3}>{selected ? "Gia hạn cho cả đợt" : "Thiết lập cho cả đợt"}</button>
    </form>}
    {canManage && selected?.state === "OPEN" && <details><summary>Đóng nhận {names[kind]} cho cả đợt</summary><form className="core-form" onSubmit={async event=>{
      event.preventDefault();
      if (await run(()=>request(`/theses/${thesis.id}/document-deadlines/${kind}/close`,userId,{
        method:"POST",headers:{"If-Match":String(selected.row_version)},body:JSON.stringify({reason:closeReason}),
      }),"Đã đóng nhận tài liệu này cho toàn đợt; GVHD vẫn có thể yêu cầu sửa từng bản.")) setCloseReason("");
    }}><label htmlFor="deadline-close-reason">Lý do đóng</label><textarea id="deadline-close-reason" className="input" required minLength={3} maxLength={2000} value={closeReason} onChange={event=>setCloseReason(event.target.value)} disabled={busy} />
      <button className="btn btn-secondary" disabled={busy || closeReason.trim().length<3}>Đóng nhận cho cả đợt</button></form></details>}
  </div></section>;
}
