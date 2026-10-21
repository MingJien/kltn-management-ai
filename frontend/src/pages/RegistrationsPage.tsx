import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ClipboardList, Info } from "lucide-react";
import type { Context, Registration } from "../api";
import { evidenceUrl, request, uploadEvidence } from "../api";
import { errorMessage } from "../errors";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import Dialog from "../components/ui/Dialog";
import PageHeader from "../components/layout/PageHeader";

const PAGE_SIZE = 24;
export default function RegistrationsPage({userId, context}: {userId: string; context: Context}) {
  const location = useLocation();
  const navigate = useNavigate();
  const focusedRegistrationId = new URLSearchParams(location.search).get("focus");
  const [rows, setRows] = useState<Registration[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState(0);
  const [rejectTarget, setRejectTarget] = useState<Registration | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [withdrawTarget, setWithdrawTarget] = useState<Registration | null>(null);
  useEffect(() => {
    const notice = (location.state as {notice?: string} | null)?.notice;
    if (!notice) return;
    setMessage(notice);
    navigate(location.pathname + location.search, {replace:true, state:null});
  }, [location.pathname, location.search, location.state, navigate]);
  const reload = useCallback(async () => {
    const data = focusedRegistrationId
      ? [await request<Registration>("/topic-registrations/" + focusedRegistrationId, userId)]
      : await request<Registration[]>("/topic-registrations?limit=" + PAGE_SIZE + "&offset=" + page * PAGE_SIZE, userId);
    setRows(data);
  }, [userId,page,focusedRegistrationId]);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    (focusedRegistrationId
      ? request<Registration>("/topic-registrations/" + focusedRegistrationId, userId).then((row) => [row])
      : request<Registration[]>("/topic-registrations?limit=" + PAGE_SIZE + "&offset=" + page * PAGE_SIZE, userId))
      .then((data) => {if (alive) setRows(data);})
      .catch((cause) => {if (alive) setError(errorMessage(cause));})
      .finally(() => {if (alive) setLoading(false);});
    return () => {alive = false;};
  }, [userId,page,focusedRegistrationId]);

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
  async function groupAction(row: Registration, action: "confirm" | "submit") {
    return operate(() => request<Registration>("/topic-registrations/" + row.id + "/" + (action === "confirm" ? "member-response" : action),userId,{
      method:"POST",body:action === "confirm" ? JSON.stringify({consent_status:"ACCEPTED"}) : undefined,
    }), action === "submit" ? "Đã gửi đăng ký. Vui lòng theo dõi kết quả xét duyệt." : "Đã xác nhận đăng ký cũ của bạn.");
  }
  async function withdraw(row: Registration) {
    return operate(() => request<Registration>(`/topic-registrations/${row.id}/withdraw`, userId, {method:"POST"}),
      "Bạn đã rút khỏi đăng ký. Bạn có thể chọn đề tài khác nếu đợt còn mở.");
  }
  async function decide(row: Registration, decision: "ACCEPT" | "REJECT", reason?: string) {
    return operate(() => request<Registration>("/topic-registrations/" + row.id + "/lecturer-decision",userId,{
      method:"POST",headers:{"If-Match":String(row.row_version)},body:JSON.stringify({decision,reason}),
    }),decision === "ACCEPT" ? "Đã chấp nhận chính thức; khóa luận và GVHD chính đã được tạo." : "Đã từ chối và lưu lý do. SV có thể đăng ký lại.");
  }
  return <>
    <PageHeader title="Đăng ký đề tài" description={context.base_role === "STUDENT"
      ? "Bổ sung minh chứng, gửi đăng ký và theo dõi kết quả xét duyệt." : "Xem hồ sơ đã gửi và quyết định tiếp nhận trong phạm vi được giao."} />
    <div className="flex gap-2" style={{marginBottom:"var(--space-4)"}}>
      <button className="btn btn-secondary" disabled={busy || loading}
        onClick={() => void reload().catch((cause) => setError(errorMessage(cause)))}>Làm mới</button>
      {context.base_role === "STUDENT" ? <Link className="btn btn-primary" to="/topics">Chọn đề tài</Link> : null}
      {focusedRegistrationId ? <Link className="btn btn-secondary" to="/registrations">Xem tất cả đăng ký</Link> : null}
    </div>
    {message ? <p className="alert alert-info" role="status">{message}</p> : null}
    {error && !rejectTarget && !withdrawTarget ? <p className="alert alert-danger" role="alert">{error}</p> : null}
    {loading ? <p role="status">Đang tải đăng ký…</p> : !rows.length ?
      <div className="card empty-state"><ClipboardList aria-hidden="true" /><h2>Chưa có đăng ký</h2><p>Chưa có đăng ký trong phạm vi của bạn.</p></div> :
      <div className="stack">{rows.map((row) => {
        const me = row.members.find((member) => member.student_id === context.student_id);
        const activeCount = row.members.filter((member) => member.active).length;
        const draft = ["DRAFT","RETURNED"].includes(row.state);
        return <article className="card registration-card" key={row.id}><div className="card-body stack">
          <div className="registration-card__heading"><div><span className="topic-code">{row.topic_code}</span>
            <h2 className="topic-card-title">{row.topic_title}</h2></div>
            {row.proposer_type === "STUDENT" && row.state === "SUBMITTED"
              ? <span className="badge badge-warning">{row.topic_state === "APPROVED" ? "Chờ GV tiếp nhận" : "Chờ bộ môn duyệt"}</span>
              : <ThesisStatusBadge state={row.state} />}</div>
          <div className="registration-card__origin">
            <span className={"topic-card__proposer " + (row.proposer_type === "STUDENT" ? "topic-card__proposer--student" : "topic-card__proposer--lecturer")}>
              {row.proposer_type === "STUDENT" ? "Sinh viên đề xuất" : "Giảng viên đề xuất"}
            </span>
            {(row.topic_state !== "DRAFT" || row.topic_proposer_user_id === context.user_id || context.base_role === "STUDENT") ?
              <Link to={`/topics?focus=${row.topic_id}`}>Xem mô tả và yêu cầu đề tài</Link> : null}
          </div>
          {me && !me.active ? <p className="alert alert-info">Bạn đã rút khỏi đăng ký này. Hồ sơ được giữ để đối chiếu lịch sử.</p> : null}
          <dl className="registration-summary">
            <dt>{row.proposer_type === "STUDENT" && row.topic_state !== "APPROVED" ? "GV được SV đề xuất" : "GV tiếp nhận"}</dt>
            <dd>{row.receiving_lecturer_name || "Chờ bộ môn chọn"}</dd>
            <dt>Thành viên</dt><dd>{activeCount}/{row.expected_member_count} SV</dd>
            {row.submitted_at ? <><dt>Đã gửi</dt><dd>{new Date(row.submitted_at).toLocaleString("vi-VN")}</dd></> : null}
            {row.lecturer_decided_at ? <><dt>GV xét</dt><dd>{new Date(row.lecturer_decided_at).toLocaleString("vi-VN")}</dd></> : null}
          </dl>
          <div><h3>Thành viên đăng ký</h3><ul className="requirement-list">{row.members.map((member) =>
            <li key={member.student_id}>{member.display_name} ({member.student_code})
              {member.is_coordinator ? " · đại diện" : ""}{!member.active ? " · đã kết thúc đăng ký" : ""}
              {member.active && member.consent_status !== "ACCEPTED" ? <ThesisStatusBadge state={member.consent_status} /> : null}
              {member.evidence_file_name && (context.base_role !== "STUDENT" || me?.active || member.student_id === context.student_id) ?
                <div><a href={evidenceUrl(row.id,member.student_id)}>Tải minh chứng: {member.evidence_file_name}</a></div> : null}
            </li>)}</ul></div>
          {row.lecturer_reason ? <p className="alert alert-warning">Lý do của GV: {row.lecturer_reason}</p> : null}
          {row.proposer_type === "STUDENT" && row.state === "SUBMITTED" && row.topic_state !== "APPROVED" ?
            <p className="registration-card__stage" role="status"><strong>Chờ bộ môn duyệt đề tài</strong>
              <span>GV được đề xuất có thể xem hồ sơ, chưa cần quyết định tiếp nhận. Bộ môn có thể xác nhận hoặc chọn GV khác.</span></p> : null}
          {row.proposer_type === "STUDENT" && row.state === "SUBMITTED" && row.topic_state === "APPROVED" ?
            <p className="registration-card__stage" role="status"><strong>Bộ môn đã duyệt đề tài</strong>
              <span>Đăng ký đang chờ GV tiếp nhận chấp nhận hoặc từ chối. Chưa phân công GVHD chính thức.</span></p> : null}
          {(row.state === "FINALIZED" || row.state === "LECTURER_ACCEPTED") ? <p className="alert alert-success">GV đã chấp nhận chính thức. Khóa luận và phân công GVHD chính đã được tạo; nhóm có thể mở hồ sơ để nộp đề cương, tiến độ và tài liệu.</p> : null}
          {me?.active && activeCount < row.expected_member_count && row.topic_state === "APPROVED" && row.state !== "FINALIZED" && row.state !== "LECTURER_ACCEPTED" ?
            <p className="text-caption">Các SV khác có thể tự tham gia từ danh sách đề tài khi còn hạn đăng ký. Nếu thêm thành viên, nhóm sẽ chờ GV xét lại.</p> : null}
          {me?.can_upload_evidence && context.base_role === "STUDENT" ? <label className="evidence-upload">
            Minh chứng của tôi (tùy chọn) — PDF, PNG, JPEG, tối đa 5 MB
            <input type="file" accept=".pdf,.png,.jpg,.jpeg" disabled={busy}
              onChange={(event) => {void upload(row,event.target.files?.[0]); event.target.value = "";}} />
            <span className="text-caption">{draft ? "Tệp mới thay minh chứng đang gắn. Sau gửi hồ sơ, minh chứng được khóa."
              : "Bạn vừa tham gia nhóm đã gửi: có thể bổ sung minh chứng lần đầu trước khi GV xét."}</span>
          </label> : null}
          <div className="registration-card__actions">
            {draft && me?.active ? <>
              {me.consent_status === "PENDING" ? <button className="btn btn-secondary" disabled={busy}
                onClick={() => void groupAction(row,"confirm")}>Xác nhận đăng ký cũ của tôi</button> : null}
              {me.is_coordinator ? <>
                <button className="btn btn-primary" disabled={busy || !row.members.filter((member) => member.active).every((member) => member.consent_status === "ACCEPTED")}
                  onClick={() => void groupAction(row,"submit")}>{row.proposer_type === "STUDENT" ? "Gửi đề xuất cho bộ môn" : "Gửi đăng ký cho GV"}</button>
              </> : <p className="text-caption">Đại diện sẽ gửi đăng ký sau khi nhóm kiểm tra thông tin.</p>}
            </> : null}
            {row.state === "SUBMITTED" && row.topic_state === "APPROVED" && row.receiving_lecturer_user_id === context.user_id ? <>
              <button className="btn btn-primary" disabled={busy} onClick={() => void decide(row,"ACCEPT")}>Chấp nhận chính thức và tạo khóa luận</button>
              <button className="btn btn-destructive" disabled={busy} onClick={() => {setRejectTarget(row); setRejectReason(""); setError("");}}>Từ chối</button>
            </> : null}
            {row.thesis_id ? <Link className="btn btn-primary" to={"/theses/" + row.thesis_id}>Mở hồ sơ khóa luận · đề cương · tiến độ · tài liệu</Link> : null}
            {me?.can_withdraw ? <>
              <p className="registration-card__hint"><Info size={15} aria-hidden="true" />
                {row.state === "SUBMITTED" ? "GV chưa chấp nhận — có thể rút để chọn đề tài khác khi đợt còn mở."
                  : "Có thể rút trước khi GV chấp nhận."}</p>
              <button className="btn btn-secondary" disabled={busy} onClick={() => {setWithdrawTarget(row); setError("");}}>Rút đăng ký</button>
            </> : null}
          </div>
        </div></article>;
      })}</div>}
    {!focusedRegistrationId ? <nav className="pagination" aria-label="Phân trang đăng ký">
      <button className="btn btn-secondary" disabled={!page || loading || busy} onClick={() => setPage(page - 1)}>Trang trước</button>
      <span>Trang {page + 1}</span>
      <button className="btn btn-secondary" disabled={rows.length < PAGE_SIZE || loading || busy} onClick={() => setPage(page + 1)}>Trang sau</button>
    </nav> : null}
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
    <Dialog open={!!withdrawTarget} busy={busy} onClose={() => setWithdrawTarget(null)} title="Rút khỏi đăng ký" footer={<>
      <button className="btn btn-secondary" disabled={busy} onClick={() => setWithdrawTarget(null)}>Giữ đăng ký</button>
      <button className="btn btn-destructive" disabled={busy} onClick={() => {
        if (withdrawTarget) void withdraw(withdrawTarget).then((ok) => {if (ok) setWithdrawTarget(null);});
      }}>Xác nhận rút</button>
    </>}>
      <p>Rút khỏi đề tài “{withdrawTarget?.topic_title}” sẽ chỉ kết thúc phần đăng ký của bạn. {withdrawTarget?.members.filter((member) => member.active).length === 1
        ? "Vì bạn là thành viên cuối, hồ sơ đăng ký sẽ chuyển sang Đã hủy."
        : "Các thành viên còn lại tiếp tục ở trong nhóm; nếu bạn là đại diện, hệ thống chuyển quyền cho thành viên còn lại."} Sau khi GV chấp nhận, bạn không thể tự rút.</p>
      <p className="text-caption">Hồ sơ cũ vẫn được lưu. Bạn chỉ có thể đăng ký đề tài khác khi đợt đăng ký còn mở.</p>
      {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
    </Dialog>
  </>;
}
