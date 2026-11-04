import LecturerProfileLink from "../components/domain/LecturerProfileDialog";
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";
import { ClipboardList, FolderOpen, GraduationCap, RefreshCw } from "lucide-react";
import { errorMessage } from "../errors";
import type { AuditEvent, Context, DocumentDeadline, Lecturer, Milestone, ProgressReport, Proposal, Thesis, ThesisDocument, WorkAssignment } from "../api";
import { request } from "../api";
import PageHeader from "../components/layout/PageHeader";
import { formatDate, ReviewForm, Status } from "../components/domain/CoreForms";
import ThesisSubmissions from "../components/domain/ThesisSubmissions";
import ThesisProgress from "../components/domain/ThesisProgress";
import ThesisWork from "../components/domain/ThesisWork";

type Data = {thesis: Thesis; milestones: Milestone[]; deadlines: DocumentDeadline[]; deadlineHistory:AuditEvent[]; reports: ProgressReport[]; docs: ThesisDocument[]; work: WorkAssignment[]; lecturers: Lecturer[]; audit: AuditEvent[]; milestoneHistory: AuditEvent[]; proposal: Proposal | null};

export default function ThesisViewPage({context}: {context: Context}) {
  const {thesisId} = useParams();
  return <ThesisWorkspace key={`${context.user_id}:${thesisId}`} context={context} />;
}

function ThesisWorkspace({context}: {context: Context}) {
  const {thesisId} = useParams();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [lecturerId, setLecturerId] = useState("");
  const [reason, setReason] = useState("");
  const load = useCallback(async (signal?: AbortSignal) => {
    const path = `/theses/${thesisId}`;
    const thesis = await request<Thesis>(path, context.user_id, {signal});
    const get = <T,>(suffix: string, action?: string): Promise<T[]> => !action || thesis.actions.includes(action)
      ? request<T[]>(path+suffix, context.user_id, {signal}) : Promise.resolve([]);
    const [milestones, deadlines, reports, docs, work, lecturers, audit, milestoneHistory, proposal, deadlineHistory] = await Promise.all([
      get<Milestone>("/milestones"), get<DocumentDeadline>("/document-deadlines"), get<ProgressReport>("/progress-reports", "progress:view"),
      get<ThesisDocument>("/documents", "document:view"), get<WorkAssignment>("/work-assignments", "work:view"),
      thesis.actions.includes("progress:assign_reviewer") || thesis.actions.includes("proposal:assign_reviewer") ? request<Lecturer[]>("/lecturers", context.user_id, {signal}) : Promise.resolve([]),
      get<AuditEvent>("/audit", "audit:view"),
      get<AuditEvent>("/milestone-history"),
      thesis.actions.includes("proposal:view") ? request<Proposal>(path+"/proposal", context.user_id, {signal}) : Promise.resolve(null),
      get<AuditEvent>("/document-deadline-history"),
    ]);
    if (!signal?.aborted) {
      setData({thesis, milestones, deadlines, deadlineHistory, reports, docs, work, lecturers, audit, milestoneHistory, proposal});
      setUpdatedAt(new Date());
    }
  }, [thesisId, context.user_id, location.key]);

  useEffect(() => {
    if (thesisId && typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(`kltn_active_thesis_id_${context.user_id}`, thesisId);
    }
  }, [thesisId, context.user_id]);

  useEffect(() => {
    const controller = new AbortController();
    setError(""); setMessage("");
    // Keep the previous render while a bell link or tab change reloads the same
    // thesis; a new thesis remounts this component through its route key.
    void load(controller.signal).catch(cause => {if (!controller.signal.aborted) setError(errorMessage(cause));});
    return () => controller.abort();
  }, [load]);

  async function run(action: () => Promise<unknown>, success: string) {
    if (busy) return false;
    setBusy(true); setError(""); setMessage("");
    try {await action(); await load(); setMessage(success); return true;}
    catch (cause) {setError(errorMessage(cause)); await load().catch(() => undefined); return false;}
    finally {setBusy(false);}
  }
  async function refresh() {
    if (busy) return;
    setRefreshing(true);
    try {await run(async () => {}, "Đã làm mới dữ liệu hồ sơ khóa luận.");}
    finally {setRefreshing(false);}
  }

  if (!data) return <><Link to="/theses">Quay lại khóa luận</Link>{error ? <div className="alert alert-danger" role="alert">{error} <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void refresh()}>Thử tải lại hồ sơ</button></div> : <p role="status">Đang tải hồ sơ khóa luận…</p>}</>;
  const {thesis, docs, milestones, deadlines, deadlineHistory, reports, work, lecturers, audit, milestoneHistory, proposal} = data;
  const tabs = ["overview", ...(proposal || thesis.actions.includes("document:view") ? ["submissions"] : []),
    ...(thesis.actions.includes("progress:view") || thesis.actions.includes("milestone:manage") ? ["progress"] : [])];
  const requested = params.get("section") || "overview";
  const normalized = ["proposal", "documents"].includes(requested) ? "submissions" : requested;
  const section = tabs.includes(normalized) ? normalized : "overview";
  const submissionKind = params.get("kind") || (requested === "proposal" ? "PROPOSAL" : "PLAN");
  const active = ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state);
  return <>
    <Link to="/theses" className="workspace-back-link">
      <span>←</span> Danh sách khóa luận
    </Link>
    <PageHeader title={{overview:"Khóa luận & GVHD",submissions:"Hồ sơ nộp & xét duyệt",progress:"Báo cáo tiến độ"}[section] || "Hồ sơ khóa luận"} description={`${thesis.title} · ${thesis.round_label}`}>
      <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={()=>void refresh()}><RefreshCw size={14} aria-hidden="true" />{refreshing ? "Đang làm mới…" : "Làm mới dữ liệu"}</button>
    </PageHeader>
    {active && <Link className="btn btn-secondary" to={`/withdrawals?thesis=${thesis.id}`}>Đơn xin thôi thực hiện KLTN</Link>}
    {active && <Link className="btn btn-secondary" to={`/changes?thesis=${thesis.id}`}>Đổi đề tài &amp; gia hạn</Link>}
    {thesis.actions.includes("evaluation:view") && <Link className="btn btn-secondary" to={`/evaluation/${thesis.id}`}>Phản biện & điều kiện dự bảo vệ</Link>}
    {context.base_role === "STUDENT" && active && !thesis.actions.includes("document:submit") && <p className="alert alert-warning" role="status">Quyền tham gia đợt của bạn đã bị thu hồi. Bạn vẫn xem được hồ sơ; các thao tác nộp/sửa được tạm dừng. Liên hệ Khoa nếu cần khôi phục.</p>}
    {updatedAt && <p className="text-caption" style={{margin: "0 0 var(--space-2)"}}>Dữ liệu cập nhật lúc {formatDate(updatedAt.toISOString())}.</p>}
    <div className="core-toolbar">
      <div className="core-toolbar__tabs" role="tablist" aria-label="Phân hệ hồ sơ khóa luận">
        {tabs.map(tab => (
          <button
            type="button"
            key={tab}
            role="tab"
            aria-selected={section === tab}
            className={`core-tab-btn ${section === tab ? "core-tab-btn--active btn btn-primary" : "btn btn-secondary"}`}
            onClick={() => setParams({section: tab})}
          >
            {tab === "overview" && <GraduationCap size={15} aria-hidden="true" />}
            {tab === "progress" && <ClipboardList size={15} aria-hidden="true" />}
            {tab === "submissions" && <FolderOpen size={15} aria-hidden="true" />}
            <span>{tab === "overview" ? "Tổng quan & GVHD" : tab === "progress" ? "Báo cáo tiến độ" : "Hồ sơ nộp & xét duyệt"}</span>
          </button>
        ))}
      </div>
      <div className="core-toolbar__status">
        <span className="core-toolbar__status-label">Trạng thái:</span>
        <Status value={thesis.state} />
      </div>
    </div>

    {section !== "submissions" && <div className="workspace-tab-banner">
      {section === "overview" && (
        <div className="workspace-tab-banner__content">
          <GraduationCap className="workspace-tab-banner__icon" size={20} aria-hidden="true" />
          <div>
            <strong>Tổng quan khóa luận & Giảng viên hướng dẫn</strong>
            <p>Theo dõi thông tin đề tài, danh sách thành viên nhóm, phân công GVHD chính thức và giảng viên góp ý chéo.</p>
          </div>
        </div>
      )}
      {section === "progress" && (
        <div className="workspace-tab-banner__content">
          <ClipboardList className="workspace-tab-banner__icon" size={20} aria-hidden="true" />
          <div>
            <strong>Tiến độ thực hiện & Báo cáo định kỳ</strong>
            <p>Chỉ dành cho báo cáo định kỳ và minh chứng của báo cáo. Mẫu 1–2–3 và các bản tài liệu nộp tại Hồ sơ nộp & xét duyệt.</p>
          </div>
        </div>
      )}
    </div>}
    {error && <div className="alert alert-danger" role="alert">{error} <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void run(async () => {}, "Đã tải dữ liệu mới.")}>Tải lại dữ liệu</button></div>}
    {message && <div className="alert alert-success" role="status">{message}</div>}
    {busy && <p role="status">{refreshing ? "Đang tải dữ liệu mới…" : "Đang lưu và cập nhật hồ sơ…"}</p>}
    {section === "overview" && <div className="stack">
      <section className="thesis-identity card"><div className="card-body"><span className="section-eyebrow">HỒ SƠ ĐANG LÀM VIỆC</span><h2>{thesis.title}</h2><p>{thesis.round_label}</p><div className="flex gap-3" style={{flexWrap:"wrap"}}><span>{thesis.members.length} sinh viên</span><span>GVHD: <strong><LecturerProfileLink userId={context.user_id} lecturerId={thesis.advisor_lecturer_id} name={thesis.advisor_name}/></strong></span><Status value={thesis.state}/></div></div></section><div className="workspace-overview-grid">
        <div className="card">
          <div className="card-body stack">
            <h2 style={{margin: 0, fontSize: "16px", fontWeight: 650}}>Nhóm sinh viên thực hiện</h2>
            <div className="workspace-members-list">
              {thesis.members.map(member => (
                <div key={member.student_id} className="workspace-member-item">
                  <div className="workspace-member-item__info">
                    <strong>{member.display_name}</strong>
                    <span className="text-muted text-caption">{member.student_code}</span>
                  </div>
                  {member.is_coordinator && <span className="badge badge-primary">Nhóm trưởng</span>}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body stack">
            <h2 style={{margin: 0, fontSize: "16px", fontWeight: 650}}>Giảng viên hướng dẫn chính thức</h2>
            {thesis.advisor_history.map(item => (
              <div className="core-review" key={item.id}>
                <strong><LecturerProfileLink userId={context.user_id} lecturerId={item.lecturer_id} name={item.display_name}/></strong> · <Status value={item.state} label={item.state === "ACTIVE" ? "Đang hướng dẫn" : undefined} />
                <p className="text-body-sm text-muted" style={{margin: "4px 0 0"}}>Từ {formatDate(item.effective_from)}{item.effective_to ? ` đến ${formatDate(item.effective_to)}` : ""}</p>
              </div>
            ))}
            {(thesis.cross_reviewers || []).map(item => (
              <div className="core-review" key={item.lecturer_id}>
                <strong>Góp ý chéo: {item.display_name}</strong>
                {thesis.actions.includes("progress:assign_reviewer") && active && (
                  <details style={{marginTop: "6px"}}><summary>Thu hồi phân công góp ý chéo</summary>
                    <ReviewForm disabled={busy} choices={[{value: "REVOKE", label: "Thu hồi quyền góp ý"}]} onSubmit={(_, revokeReason) => run(() => request(`/theses/${thesis.id}/progress-reviewers/${item.lecturer_id}/revoke`, context.user_id, {
                      method: "POST", headers: {"If-Match": String(thesis.row_version)}, body: JSON.stringify({reason: revokeReason}),
                    }), "Đã thu hồi phân công góp ý chéo.")} />
                  </details>
                )}
              </div>
            ))}
            {thesis.actions.includes("progress:assign_reviewer") && active && (
              <form className="core-form" onSubmit={async event => {
                event.preventDefault();
                if (await run(() => request(`/theses/${thesis.id}/progress-reviewers`, context.user_id, {method: "POST", headers: {"If-Match": String(thesis.row_version)}, body: JSON.stringify({lecturer_id: lecturerId, reason})}), "Đã phân công giảng viên góp ý chéo tiến độ.")) {setReason(""); setLecturerId("");}
              }}>
                <h3 style={{fontSize: "14px", margin: "6px 0 2px"}}>Phân công giảng viên góp ý chéo</h3>
                <div className="input-group"><label htmlFor="reviewer-lecturer">Giảng viên</label><select className="input" id="reviewer-lecturer" value={lecturerId} onChange={event => setLecturerId(event.target.value)} required disabled={busy}><option value="">Chọn giảng viên cùng bộ môn</option>{lecturers.filter(item => item.id !== thesis.advisor_lecturer_id && !(thesis.cross_reviewers || []).some(reviewer => reviewer.lecturer_id === item.id)).map(item => <option key={item.id} value={item.id}>{item.display_name} · {item.lecturer_code}</option>)}</select></div>
                <div className="input-group"><label htmlFor="reviewer-reason">Lý do phân công</label><textarea className="input" id="reviewer-reason" value={reason} onChange={event => setReason(event.target.value)} minLength={3} maxLength={2000} required disabled={busy} /></div>
                <button className="btn btn-primary btn-sm" disabled={busy || !lecturerId || reason.trim().length < 3}>Giao góp ý chéo</button>
              </form>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-body stack">
          <div className="flex justify-between items-center gap-3" style={{flexWrap: "wrap"}}>
            <div>
              <h2 style={{margin: 0, fontSize: "15px", fontWeight: 650}}>Thao tác đề cương, tiến độ và tài liệu</h2>
              <p className="text-body-sm text-muted" style={{margin: "2px 0 0"}}>Chuyển nhanh tới phân hệ để nộp và kiểm tra hồ sơ</p>
            </div>
            <div className="flex gap-2" style={{flexWrap: "wrap"}}>
              {proposal || thesis.actions.includes("document:view") ? <Link className="btn btn-secondary btn-sm" to={"/theses/" + thesis.id + "?section=submissions"}>Mở hồ sơ nộp & xét duyệt</Link> : null}
              {thesis.actions.includes("progress:view") || thesis.actions.includes("milestone:manage") ? <Link className="btn btn-secondary btn-sm" to={`/theses/${thesis.id}?section=progress`}>Mở mốc và báo cáo tiến độ</Link> : null}

            </div>
          </div>
        </div>
      </div>
      {thesis.actions.includes("work:view") && <div className="card"><div className="card-body"><ThesisWork thesis={thesis} assignments={work} context={context} busy={busy} run={run} /></div></div>}
      {thesis.actions.includes("audit:view") && <details className="card"><summary className="card-body">Lịch sử thao tác nghiệp vụ</summary><div className="card-body stack">{audit.map((event, index) => <p key={`${event.occurred_at}-${index}`}><strong>{event.actor_name}</strong> · {event.action} · {formatDate(event.occurred_at)}<br />{event.reason}</p>)}</div></details>}
    </div>}
    {section === "progress" && <div className="stack"><ThesisProgress thesis={thesis} milestones={milestones} reports={reports} docs={docs} milestoneHistory={milestoneHistory} userId={context.user_id} studentId={context.student_id} busy={busy} run={run} /></div>}
    {section === "submissions" && <ThesisSubmissions thesis={thesis} proposal={proposal} docs={docs} deadlines={deadlines} history={deadlineHistory} lecturers={lecturers} reports={reports} userId={context.user_id} busy={busy} run={run} kind={submissionKind} />}
  </>;
}
