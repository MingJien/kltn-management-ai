import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList } from "lucide-react";
import type { Context, Registration } from "../api";
import { evidenceUrl, request, uploadEvidence } from "../api";
import { errorMessage } from "../errors";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import Dialog from "../components/ui/Dialog";
import PageHeader from "../components/layout/PageHeader";

const PAGE_SIZE = 24;
export default function RegistrationsPage({userId, context}: {userId: string; context: Context}) {
  const [rows, setRows] = useState<Registration[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState(0);
  const [rejectTarget, setRejectTarget] = useState<Registration | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [cancelTarget, setCancelTarget] = useState<Registration | null>(null);
  const [finalizeTarget, setFinalizeTarget] = useState<Registration | null>(null);
  const reload = useCallback(async () => {
    setRows(await request<Registration[]>("/topic-registrations?limit=" + PAGE_SIZE + "&offset=" + page * PAGE_SIZE, userId));
  }, [userId,page]);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    request<Registration[]>("/topic-registrations?limit=" + PAGE_SIZE + "&offset=" + page * PAGE_SIZE, userId)
      .then((data) => {if (alive) setRows(data);})
      .catch((cause) => {if (alive) setError(errorMessage(cause));})
      .finally(() => {if (alive) setLoading(false);});
    return () => {alive = false;};
  }, [userId,page]);

  async function operate(work: () => Promise<unknown>, success: string): Promise<boolean> {
    if (busy) return false;
    setBusy(true); setMessage(""); setError("");
    try {await work(); await reload(); setMessage(success); return true;}
    catch (cause) {setError(errorMessage(cause)); await reload().catch(() => undefined); return false;}
    finally {setBusy(false);}
  }
  async function upload(row: Registration, file?: File) {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {setError("Minh chứng tối đa 5 MB."); return;}
    await operate(() => uploadEvidence(row.id,userId,file), "Đã lưu minh chứng của bạn.");
  }
  async function groupAction(row: Registration, action: "confirm" | "submit" | "cancel") {
    return operate(() => request<Registration>("/topic-registrations/" + row.id + "/" + (action === "confirm" ? "member-response" : action),userId,{
      method:"POST",body:action === "confirm" ? JSON.stringify({consent_status:"ACCEPTED"}) : undefined,
    }), action === "cancel" ? "Đã hủy bản nháp. Thành viên có thể đăng ký đề tài khác."
      : action === "submit" ? "Đã gửi đăng ký. Vui lòng theo dõi kết quả xét duyệt." : "Đã xác nhận đăng ký cũ của bạn.");
  }
  async function decide(row: Registration, decision: "ACCEPT" | "REJECT", reason?: string) {
    return operate(() => request<Registration>("/topic-registrations/" + row.id + "/lecturer-decision",userId,{
      method:"POST",headers:{"If-Match":String(row.row_version)},body:JSON.stringify({decision,reason}),
    }),decision === "ACCEPT" ? "Đã chấp nhận nhóm đăng ký." : "Đã từ chối và lưu lý do. SV có thể đăng ký lại.");
  }
  async function finalize(row: Registration) {
    return operate(() => request<Registration>("/topic-registrations/" + row.id + "/department-finalization", userId, {
      method: "POST", headers: {"If-Match": String(row.row_version)},
    }), "Đã chốt đăng ký và phân công GVHD chính.");
  }
  return <>
    <PageHeader title="Đăng ký đề tài" description={context.base_role === "STUDENT"
      ? "Bổ sung minh chứng, gửi đăng ký và theo dõi kết quả xét duyệt." : "Xem hồ sơ đã gửi và quyết định tiếp nhận trong phạm vi được giao."} />
    <div className="flex gap-2" style={{marginBottom:"var(--space-4)"}}>
      <button className="btn btn-secondary" disabled={busy || loading}
        onClick={() => void reload().catch((cause) => setError(errorMessage(cause)))}>Làm mới</button>
      {context.base_role === "STUDENT" ? <Link className="btn btn-primary" to="/topics">Chọn đề tài</Link> : null}
    </div>
    {message ? <p className="alert alert-info" role="status">{message}</p> : null}
    {error && !rejectTarget && !cancelTarget && !finalizeTarget ? <p className="alert alert-danger" role="alert">{error}</p> : null}
    {loading ? <p role="status">Đang tải đăng ký…</p> : !rows.length ?
      <div className="card empty-state"><ClipboardList aria-hidden="true" /><h2>Chưa có đăng ký</h2><p>Chưa có đăng ký trong phạm vi của bạn.</p></div> :
      <div className="stack">{rows.map((row) => {
        const me = row.members.find((member) => member.student_id === context.student_id && member.active);
        const activeCount = row.members.filter((member) => member.active).length;
        const draft = ["DRAFT","RETURNED"].includes(row.state);
        return <article className="card" key={row.id}><div className="card-body stack">
          <div className="flex justify-between items-center gap-2"><h2 className="topic-card-title">{row.topic_title}</h2><ThesisStatusBadge state={row.state} /></div>
          <dl className="registration-summary">
            <dt>Mã đề tài</dt><dd>{row.topic_code}</dd>
            <dt>GV tiếp nhận</dt><dd>{row.receiving_lecturer_name || "Chờ bộ môn chọn"}</dd>
            <dt>Thành viên</dt><dd>{activeCount}/{row.expected_member_count} SV</dd>
            {row.submitted_at ? <><dt>Đã gửi</dt><dd>{new Date(row.submitted_at).toLocaleString("vi-VN")}</dd></> : null}
            {row.lecturer_decided_at ? <><dt>GV xét</dt><dd>{new Date(row.lecturer_decided_at).toLocaleString("vi-VN")}</dd></> : null}
          </dl>
          <div><h3>Thành viên đăng ký</h3><ul className="requirement-list">{row.members.map((member) =>
            <li key={member.student_id}>{member.display_name} ({member.student_code})
              {member.is_coordinator ? " · đại diện" : ""}{!member.active ? " · đã kết thúc đăng ký" : ""}
              {member.active && member.consent_status !== "ACCEPTED" ? <ThesisStatusBadge state={member.consent_status} /> : null}
              {member.evidence_file_name ? <div><a href={evidenceUrl(row.id,member.student_id)}>Tải minh chứng: {member.evidence_file_name}</a></div> : null}
            </li>)}</ul></div>
          {row.lecturer_reason ? <p className="alert alert-warning">Lý do của GV: {row.lecturer_reason}</p> : null}
          {row.proposer_type === "STUDENT" && row.state === "SUBMITTED" && row.topic_state !== "APPROVED" ?
            <p className="alert alert-info">Đề xuất đang chờ bộ môn duyệt tên và xác nhận GV tiếp nhận.</p> : null}
          {row.state === "LECTURER_ACCEPTED" ? <p className="alert alert-info">GV đã đồng ý tiếp nhận. Hồ sơ chờ Trưởng bộ môn chốt và xác nhận GVHD chính.</p> : null}
          {me && activeCount < row.expected_member_count && row.topic_state === "APPROVED" && row.state !== "FINALIZED" ?
            <p className="text-caption">Các SV khác có thể tự tham gia từ danh sách đề tài khi còn hạn đăng ký. Nếu thêm thành viên, nhóm sẽ chờ GV xét lại.</p> : null}
          {me?.can_upload_evidence && context.base_role === "STUDENT" ? <label className="evidence-upload">
            Minh chứng của tôi (tùy chọn) — PDF, PNG, JPEG, tối đa 5 MB
            <input type="file" accept=".pdf,.png,.jpg,.jpeg" disabled={busy}
              onChange={(event) => {void upload(row,event.target.files?.[0]); event.target.value = "";}} />
            <span className="text-caption">{draft ? "Tệp mới thay minh chứng đang gắn. Sau gửi hồ sơ, minh chứng được khóa."
              : "Bạn vừa tham gia nhóm đã gửi: có thể bổ sung minh chứng lần đầu trước khi GV xét."}</span>
          </label> : null}
          <div className="flex gap-2">
            {draft && me ? <>
              {me.consent_status === "PENDING" ? <button className="btn btn-secondary" disabled={busy}
                onClick={() => void groupAction(row,"confirm")}>Xác nhận đăng ký cũ của tôi</button> : null}
              {me.is_coordinator ? <>
                <button className="btn btn-primary" disabled={busy || !row.members.filter((member) => member.active).every((member) => member.consent_status === "ACCEPTED")}
                  onClick={() => void groupAction(row,"submit")}>{row.proposer_type === "STUDENT" ? "Gửi đề xuất cho bộ môn" : "Gửi đăng ký cho GV"}</button>
                <button className="btn btn-secondary" disabled={busy} onClick={() => {setCancelTarget(row); setError("");}}>Hủy bản nháp</button>
              </> : <p className="text-caption">Đại diện sẽ gửi đăng ký sau khi nhóm kiểm tra thông tin.</p>}
            </> : null}
            {row.state === "SUBMITTED" && row.topic_state === "APPROVED" && row.receiving_lecturer_user_id === context.user_id ? <>
              <button className="btn btn-primary" disabled={busy} onClick={() => void decide(row,"ACCEPT")}>Chấp nhận</button>
              <button className="btn btn-destructive" disabled={busy} onClick={() => {setRejectTarget(row); setRejectReason(""); setError("");}}>Từ chối</button>
            </> : null}
            {row.state === "LECTURER_ACCEPTED" && context.actions.includes("registration:department_finalize") ?
              <button className="btn btn-primary" disabled={busy} onClick={() => {setFinalizeTarget(row); setError("");}}>
                Chốt đăng ký và GVHD</button> : null}
            {row.thesis_id ? <Link className="btn btn-secondary" to={"/theses/" + row.thesis_id}>Xem khóa luận đã chốt</Link> : null}
          </div>
        </div></article>;
      })}</div>}
    <nav className="pagination" aria-label="Phân trang đăng ký">
      <button className="btn btn-secondary" disabled={!page || loading || busy} onClick={() => setPage(page - 1)}>Trang trước</button>
      <span>Trang {page + 1}</span>
      <button className="btn btn-secondary" disabled={rows.length < PAGE_SIZE || loading || busy} onClick={() => setPage(page + 1)}>Trang sau</button>
    </nav>
    <Dialog open={!!rejectTarget} busy={busy} onClose={() => setRejectTarget(null)} title="Từ chối đăng ký" footer={<>
      <button className="btn btn-secondary" disabled={busy} onClick={() => setRejectTarget(null)}>Quay lại</button>
      <button className="btn btn-destructive" disabled={busy || !rejectReason.trim()} onClick={() => {
        if (rejectTarget) void decide(rejectTarget,"REJECT",rejectReason.trim()).then((ok) => {if (ok) setRejectTarget(null);});
      }}>{busy ? "Đang lưu…" : "Xác nhận từ chối"}</button>
    </>}>
      <p>{rejectTarget?.topic_title}</p>
      <label>Lý do từ chối<textarea className="input" rows={3} maxLength={2000} required value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} /></label>
      {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
    </Dialog>
    <Dialog open={!!cancelTarget} busy={busy} onClose={() => setCancelTarget(null)} title="Hủy bản nháp đăng ký" footer={<>
      <button className="btn btn-secondary" disabled={busy} onClick={() => setCancelTarget(null)}>Giữ đăng ký</button>
      <button className="btn btn-destructive" disabled={busy} onClick={() => {
        if (cancelTarget) void groupAction(cancelTarget,"cancel").then((ok) => {if (ok) setCancelTarget(null);});
      }}>Xác nhận hủy</button>
    </>}>
      <p>Hủy bản nháp của đề tài “{cancelTarget?.topic_title}” sẽ kết thúc đăng ký của tất cả thành viên trong nhóm. Hồ sơ cũ vẫn được lưu.</p>
      {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
    </Dialog>
    <Dialog open={!!finalizeTarget} busy={busy} onClose={() => setFinalizeTarget(null)} title="Chốt đăng ký và phân công GVHD" footer={<>
      <button className="btn btn-secondary" disabled={busy} onClick={() => setFinalizeTarget(null)}>Quay lại</button>
      <button className="btn btn-primary" disabled={busy} onClick={() => {
        if (finalizeTarget) void finalize(finalizeTarget).then(ok => {if (ok) setFinalizeTarget(null);});
      }}>Xác nhận chốt</button>
    </>}>
      <p>Đề tài: <strong>{finalizeTarget?.topic_title}</strong></p>
      <p>GVHD chính: <strong>{finalizeTarget?.receiving_lecturer_name}</strong> (GV đã chấp nhận nhóm).</p>
      <p className="text-caption">Hệ thống sẽ kiểm tra lại điều kiện của từng SV. Sau khi chốt, nhóm không thể bổ sung thành viên qua đăng ký này.</p>
      {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
    </Dialog>
  </>;
}
