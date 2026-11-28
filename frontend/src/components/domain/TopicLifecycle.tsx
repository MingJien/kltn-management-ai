import { useState } from "react";
import { Archive, ArchiveRestore, Trash2 } from "lucide-react";
import type { Topic, Context } from "../../api";
import { request } from "../../api";
import { errorMessage } from "../../errors";

export default function TopicLifecycle({topic,context,onChanged}:{topic:Topic;context:Context;onChanged:()=>Promise<void>}){
  const [reason,setReason]=useState(""),[confirmed,setConfirmed]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const draft=topic.proposer_user_id===context.user_id && topic.state==="DRAFT" && !topic.has_links;
  const head=context.actions.includes("topic:department_decide") && topic.department_id===context.department_id;
  if(!draft && !head)return null;
  const action=draft?"delete-draft":topic.archived_at?"restore":"archive";
  const label=draft?"Xóa đề tài nháp":topic.archived_at?"Khôi phục hiển thị đề tài":"Ngừng sử dụng đề tài";
  return (
    <details className="card">
      <summary className="card-body flex items-center gap-2">
        {draft ? <Trash2 size={15} aria-hidden="true" /> : topic.archived_at ? <ArchiveRestore size={15} aria-hidden="true" /> : <Archive size={15} aria-hidden="true" />}
        {label}
      </summary>
      <form className="card-body core-form" onSubmit={async e=>{e.preventDefault();if(busy)return;setBusy(true);setError("");try{await request(`/topics/${topic.id}/${action}`,context.user_id,{method:"POST",headers:{"If-Match":String(topic.row_version)},body:JSON.stringify({reason})});await onChanged();}catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}}}>
        <p className="text-body-sm text-muted">{draft?"Chỉ xóa nháp chưa có đăng ký/khóa luận. Thao tác này không khôi phục được; nhật ký và mã đã cấp vẫn được giữ.":"Ngừng sử dụng sẽ ẩn đề tài khỏi danh sách đăng ký mới. Khóa luận, đăng ký đang xử lý, tài liệu và lịch sử được giữ nguyên. Có thể khôi phục hiển thị."}</p>
        <label className="input-group">Lý do<textarea className="input" required minLength={5} maxLength={2000} value={reason} onChange={e=>setReason(e.target.value)}/></label>
        <label className="checkbox-label"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/> Tôi đã kiểm tra đúng đề tài {topic.code} và xác nhận thao tác.</label>
        {error && <p className="alert alert-danger" role="alert">{error}</p>}
        <button className={`btn ${draft || !topic.archived_at ? "btn-destructive" : "btn-soft"}`} disabled={busy || !confirmed || reason.trim().length<5}>
          {busy ? "Đang xử lý…" : label}
        </button>
      </form>
    </details>
  );
}
