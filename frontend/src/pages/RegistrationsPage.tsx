import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Context, Registration } from "../api";
import { evidenceUrl, request, uploadEvidence } from "../api";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import Dialog from "../components/ui/Dialog";
import PageHeader from "../components/layout/PageHeader";
import { ClipboardList, ExternalLink } from "lucide-react";

interface RegistrationsPageProps {
  userId: string;
  context: Context;
}

export default function RegistrationsPage({ userId, context }: RegistrationsPageProps) {
  const [rows, setRows] = useState<Registration[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function upload(row: Registration, file?: File) {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {setMessage("Minh chứng tối đa 5 MB."); return;}
    setBusy(true);
    try {await uploadEvidence(row.id, userId, file); setMessage("Đã lưu minh chứng riêng của bạn."); reload();}
    catch (e) {setMessage(String(e));} finally {setBusy(false);}
  }

  // Reject dialog state
  const [rejectTarget, setRejectTarget] = useState<Registration | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const reload = useCallback(() => {
    setLoading(true);
    request<Registration[]>("/topic-registrations", userId)
      .then(setRows)
      .catch((error) => setMessage(String(error)))
      .finally(() => setLoading(false));
  }, [userId]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function act(row: Registration, action: "accept" | "reject" | "finalize", reason?: string) {
    setMessage("");
    const path =
      action === "finalize" ? "department-finalization" : "lecturer-decision";
    try {
      await request<Registration>(
        `/topic-registrations/${row.id}/${path}`,
        userId,
        {
          method: "POST",
          headers: { "If-Match": String(row.row_version) },
          body:
            action === "finalize"
              ? undefined
              : JSON.stringify({
                  decision: action === "accept" ? "ACCEPT" : "REJECT",
                  reason: action === "reject" ? reason : undefined,
                }),
        }
      );
      setMessage("Đã cập nhật. Trạng thái được đọc lại từ server.");
      reload();
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function groupAction(row: Registration, action: "confirm" | "decline" | "submit" | "cancel") {
    setMessage("");
    const path = action === "confirm" || action === "decline" ? "member-response" : action;
    try {
      await request<Registration>(`/topic-registrations/${row.id}/${path}`, userId, {
        method: "POST",
        body: action === "confirm" || action === "decline"
          ? JSON.stringify({ consent_status: action === "confirm" ? "ACCEPTED" : "DECLINED" })
          : undefined,
      });
      setMessage("Đã cập nhật. Trạng thái được đọc lại từ server.");
      reload();
    } catch (error) { setMessage(String(error)); }
  }

  function handleRejectConfirm() {
    if (!rejectTarget) return;
    void act(rejectTarget, "reject", rejectReason);
    setRejectTarget(null);
    setRejectReason("");
  }

  return (
    <>
      <PageHeader
        title="Đăng ký và Khóa luận"
        description="Xác nhận thành viên, bổ sung minh chứng và theo dõi kết quả tiếp nhận."
      />

      {loading ? (
        <div className="stack">
          {[1, 2, 3].map((i) => (
            <div className="card" key={i}>
              <div className="card-body">
                <div className="skeleton skeleton-line" style={{ width: "40%" }} />
                <div className="skeleton skeleton-line" style={{ width: "70%" }} />
                <div className="skeleton skeleton-line" style={{ width: "55%" }} />
              </div>
            </div>
          ))}
        </div>
      ) : rows.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <ClipboardList />
            <h3>Chưa có đăng ký</h3>
            <p>Chưa có đăng ký trong phạm vi của bạn.</p>
          </div>
        </div>
      ) : (
        <div className="stack">
          {rows.map((row) => (
            <article className="card" key={row.id}>
              <div className="card-body">
                <div className="flex justify-between items-center" style={{ marginBottom: "var(--space-3)" }}>
                  <h3>{row.topic_title}</h3>
                  <ThesisStatusBadge state={row.state} />
                </div>

                <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "var(--space-2) var(--space-4)", marginBottom: "var(--space-4)" }}>
                  <dt className="text-caption" style={{ color: "var(--neutral-500)" }}>Đề tài</dt>
                  <dd className="text-body-sm">{row.topic_code} · {row.topic_title}</dd>
                  <dt className="text-caption">GV tiếp nhận</dt><dd>{row.receiving_lecturer_name || "Chờ bộ môn chọn"}</dd>

                  <dt className="text-caption" style={{ color: "var(--neutral-500)" }}>Thành viên</dt>
                  <dd className="text-body-sm">{row.member_student_ids.length} sinh viên</dd>

                  {row.thesis_id && (
                    <>
                      <dt className="text-caption" style={{ color: "var(--neutral-500)" }}>Khóa luận</dt>
                      <dd>
                        <Link
                          to={`/theses/${row.thesis_id}`}
                          className="flex items-center gap-1 text-body-sm"
                        >
                          {row.thesis_id.slice(0, 8)}…
                          <ExternalLink size={12} />
                        </Link>
                      </dd>
                    </>
                  )}
                </dl>

                <div style={{ marginBottom: "var(--space-4)" }}>
                  <strong>Thành viên và xác nhận</strong>
                  <ul className="requirement-list">{row.members.map((member) =>
                    <li key={member.student_id}>{member.display_name} ({member.student_code}) — <ThesisStatusBadge state={member.consent_status}/>
                      {member.is_coordinator ? " · đại diện" : ""}{!member.active ? " · đã kết thúc đăng ký" : ""}
                      {member.evidence_file_name ? <div><a href={evidenceUrl(row.id, member.student_id)} className="btn btn-link">Tải minh chứng: {member.evidence_file_name}</a></div> : null}
                    </li>
                  )}</ul>
                </div>
                {row.lecturer_reason ? <p className="alert alert-warning">Lý do của GV: {row.lecturer_reason}</p> : null}
                {row.proposer_type === "STUDENT" && row.state === "SUBMITTED" && row.topic_state !== "APPROVED" ? <p className="alert alert-info">Đề xuất đã gửi, chờ bộ môn duyệt tên và xác nhận GV tiếp nhận.</p> : null}
                {context.base_role === "STUDENT" && ["DRAFT", "RETURNED"].includes(row.state) && row.members.some((m) => m.active && m.student_id === context.student_id) ?
                  <label className="evidence-upload">Minh chứng của tôi (tùy chọn) — PDF, PNG, JPEG, tối đa 5 MB<input type="file" accept=".pdf,.png,.jpg,.jpeg" disabled={busy}
                    onChange={(e) => {void upload(row,e.target.files?.[0]); e.target.value = "";}}/><span className="text-caption">Chỉ gửi thông tin cần để GV xem xét. Tệp mới thay tệp đang gắn; sau gửi đăng ký không thể thay.</span></label> : null}

                <div className="flex gap-3">
                  {["DRAFT", "RETURNED"].includes(row.state) && context.base_role === "STUDENT" && (() => {
                    const me = row.members.find((member) => member.student_id === context.student_id && member.active);
                    if (!me) return null;
                    return <>
                      {me.consent_status === "PENDING" && <>
                        <button className="btn btn-primary btn-sm" onClick={() => void groupAction(row, "confirm")}>Tôi xác nhận tham gia</button>
                        <button className="btn btn-secondary btn-sm" onClick={() => void groupAction(row, "decline")}>Từ chối tham gia</button>
                      </>}
                      {me.is_coordinator && <>
                        <button className="btn btn-primary btn-sm"
                          disabled={!row.members.filter((member) => member.active).every((member) => member.consent_status === "ACCEPTED")}
                          onClick={() => void groupAction(row, "submit")}>{row.proposer_type === "STUDENT" ? "Gửi đề xuất cho bộ môn" : "Gửi đăng ký cho GV"}</button>
                        <button className="btn btn-secondary btn-sm" onClick={() => void groupAction(row, "cancel")}>Hủy bản nháp</button>
                      </>}
                    </>;
                  })()}
                  {row.state === "SUBMITTED" &&
                    row.topic_state === "APPROVED" && row.receiving_lecturer_user_id === context.user_id && (
                      <>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => void act(row, "accept")}
                        >
                          Chấp nhận
                        </button>
                        <button
                          className="btn btn-destructive btn-sm"
                          onClick={() => {
                            setRejectTarget(row);
                            setRejectReason("");
                          }}
                        >
                          Từ chối
                        </button>
                      </>
                    )}
                  {row.state === "LECTURER_ACCEPTED" &&
                    context.actions.includes("registration:department_finalize") && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => void act(row, "finalize")}
                      >
                        TBM chốt đăng ký
                      </button>
                    )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Feedback message */}
      {message && (
        <div
          className="alert alert-info"
          role="status"
          style={{ marginTop: "var(--space-4)" }}
        >
          {message}
        </div>
      )}

      {/* Reject dialog — replaces window.prompt() */}
      <Dialog
        open={rejectTarget !== null}
        onClose={() => { setRejectTarget(null); setRejectReason(""); }}
        title="Từ chối đăng ký"
        size="sm"
        footer={
          <>
            <button
              className="btn btn-secondary"
              onClick={() => { setRejectTarget(null); setRejectReason(""); }}
            >
              Hủy
            </button>
            <button
              className="btn btn-destructive"
              onClick={handleRejectConfirm}
              disabled={rejectReason.trim().length === 0}
            >
              Xác nhận từ chối
            </button>
          </>
        }
      >
        <div className="input-group">
          <label htmlFor="reject-reason">Lý do từ chối *</label>
          <textarea
            id="reject-reason"
            className="input"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Nhập lý do từ chối đăng ký..."
            rows={3}
          />
        </div>
      </Dialog>
    </>
  );
}
