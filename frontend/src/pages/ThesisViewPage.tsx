import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { errorMessage } from "../errors";
import type { AuditEvent, Context, DocumentDeadline, Lecturer, Milestone, ProgressReport, Proposal, Thesis, ThesisDocument, WorkAssignment } from "../api";
import { request } from "../api";
import PageHeader from "../components/layout/PageHeader";
import { formatDate, ReviewForm, Status } from "../components/domain/CoreForms";
import ThesisDocuments from "../components/domain/ThesisDocuments";
import ThesisProgress from "../components/domain/ThesisProgress";
import ThesisProposal from "../components/domain/ThesisProposal";
import ThesisWork from "../components/domain/ThesisWork";
import DocumentDeadlines from "../components/domain/DocumentDeadlines";

type Data = {thesis: Thesis; milestones: Milestone[]; deadlines: DocumentDeadline[]; reports: ProgressReport[]; docs: ThesisDocument[]; work: WorkAssignment[]; lecturers: Lecturer[]; audit: AuditEvent[]; milestoneHistory: AuditEvent[]; proposal: Proposal | null};

export default function ThesisViewPage({context}: {context: Context}) {
  const {thesisId} = useParams();
  return <ThesisWorkspace key={`${context.user_id}:${thesisId}`} context={context} />;
}

function ThesisWorkspace({context}: {context: Context}) {
  const {thesisId} = useParams();
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
    const [milestones, deadlines, reports, docs, work, lecturers, audit, milestoneHistory, proposal] = await Promise.all([
      get<Milestone>("/milestones"), get<DocumentDeadline>("/document-deadlines"), get<ProgressReport>("/progress-reports", "progress:view"),
      get<ThesisDocument>("/documents", "document:view"), get<WorkAssignment>("/work-assignments", "work:view"),
      thesis.actions.includes("progress:assign_reviewer") || thesis.actions.includes("proposal:assign_reviewer") ? request<Lecturer[]>("/lecturers", context.user_id, {signal}) : Promise.resolve([]),
      get<AuditEvent>("/audit", "audit:view"),
      get<AuditEvent>("/milestone-history"),
      thesis.actions.includes("proposal:view") ? request<Proposal>(path+"/proposal", context.user_id, {signal}) : Promise.resolve(null),
    ]);
    if (!signal?.aborted) {
      setData({thesis, milestones, deadlines, reports, docs, work, lecturers, audit, milestoneHistory, proposal});
      setUpdatedAt(new Date());
    }
  }, [thesisId, context.user_id]);

  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(""); setMessage("");
    void load(controller.signal).catch(cause => {if (!controller.signal.aborted) setError(errorMessage(cause));});
    return () => controller.abort();
  }, [load]);

  async function run(action: () => Promise<unknown>, success: string) {
    if (busy) return false;
    setBusy(true); setError(""); setMessage("");
    try {await action(); await load(); setMessage(success); return true;}
    catch (cause) {setError(errorMessage(cause)); return false;}
    finally {setBusy(false);}
  }
  async function refresh() {
    if (busy) return;
    setRefreshing(true);
    try {await run(async () => {}, "Đã làm mới dữ liệu hồ sơ khóa luận.");}
    finally {setRefreshing(false);}
  }

  if (!data) return <><Link to="/theses">Quay lại khóa luận</Link>{error ? <div className="alert alert-danger" role="alert">{error} <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void refresh()}>Thử tải lại hồ sơ</button></div> : <p role="status">Đang tải hồ sơ khóa luận…</p>}</>;
  const {thesis, docs, milestones, deadlines, reports, work, lecturers, audit, milestoneHistory, proposal} = data;
  const tabs = ["overview", ...(proposal ? ["proposal"] : []), ...(thesis.actions.includes("progress:view") || thesis.actions.includes("milestone:manage") ? ["progress"] : []),
    ...(thesis.actions.includes("document:view") ? ["documents"] : [])];
  const section = tabs.includes(params.get("section") || "") ? params.get("section")! : "overview";
  const active = ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state);
  return <>
    <Link to="/theses">← Danh sách khóa luận</Link>
    <PageHeader title={thesis.title} description={`${thesis.round_label} · GVHD: ${thesis.advisor_name || "Chưa có"}`}>
      <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void refresh()}><RefreshCw size={16} aria-hidden="true" />{refreshing ? "Đang làm mới…" : "Làm mới dữ liệu"}</button>
    </PageHeader>
    {updatedAt && <p className="text-caption">Dữ liệu cập nhật lúc {formatDate(updatedAt.toISOString())}. Nhấn Làm mới dữ liệu để xem bài nộp hoặc phản hồi mới.</p>}
    <div className="core-toolbar"><Status value={thesis.state} />{tabs.map(tab => <button type="button" key={tab} className={`btn ${section === tab ? "btn-primary" : "btn-secondary"}`} aria-pressed={section === tab} onClick={() => setParams({section: tab})}>{tab === "overview" ? "Tổng quan & GVHD" : tab === "proposal" ? "Đề cương" : tab === "progress" ? "Tiến độ" : "Tài liệu"}</button>)}</div>
    {error && <div className="alert alert-danger" role="alert">{error} <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void run(async () => {}, "Đã tải dữ liệu mới.")}>Tải lại dữ liệu</button></div>}
    {message && <div className="alert alert-success" role="status">{message}</div>}
    {busy && <p role="status">{refreshing ? "Đang tải dữ liệu mới…" : "Đang lưu và cập nhật hồ sơ…"}</p>}
    {section === "overview" && <div className="stack">
      <div className="card"><div className="card-body stack"><h2>Thành viên</h2>{thesis.members.map(member => <p key={member.student_id}><strong>{member.display_name}</strong> · {member.student_code}{member.is_coordinator ? " · Nhóm trưởng điều phối" : ""}</p>)}</div></div>
      <div className="card"><div className="card-body stack"><h2>Thao tác đề cương, tiến độ và tài liệu</h2>
        <p className="text-body-sm text-muted">Mở đề cương để tải mẫu chính thức, nộp bản thảo và theo dõi phê duyệt. Mở tiến độ để xem mốc chung của đợt, nộp báo cáo và phản hồi. Mở tài liệu để tạo hồ sơ, nộp phiên bản, nhận xét và tải bản đã lưu.</p>
        <div className="flex gap-2" style={{flexWrap: "wrap"}}>
          {proposal || thesis.actions.includes("proposal:view") ? <Link className="btn btn-secondary" to={`/theses/${thesis.id}?section=proposal`}>Mở đề cương khóa luận</Link> : null}
          {thesis.actions.includes("progress:view") || thesis.actions.includes("milestone:manage") ? <Link className="btn btn-secondary" to={`/theses/${thesis.id}?section=progress`}>Mở mốc và báo cáo tiến độ</Link> : null}
          {thesis.actions.includes("document:view") ? <Link className="btn btn-secondary" to={`/theses/${thesis.id}?section=documents`}>Mở tài liệu và phiên bản</Link> : null}
        </div>
      </div></div>
      <div className="card"><div className="card-body stack"><h2>GVHD chính thức</h2>
        <p className="text-body-sm text-muted">Giảng viên này được gán ngay khi chấp nhận đăng ký. Việc đổi GVHD không thực hiện trong luồng hiện tại.</p>
        {thesis.advisor_history.map(item => <div className="core-review" key={item.id}><strong>{item.display_name}</strong> · <Status value={item.state} label={item.state === "ACTIVE" ? "Đang hướng dẫn" : undefined} /><p className="text-body-sm text-muted">Từ {formatDate(item.effective_from)}{item.effective_to ? ` đến ${formatDate(item.effective_to)}` : ""}</p></div>)}
        {(thesis.cross_reviewers || []).map(item => <div className="core-review" key={item.lecturer_id}><strong>Góp ý chéo: {item.display_name}</strong>
          {thesis.actions.includes("progress:assign_reviewer") && active && <details><summary>Thu hồi phân công góp ý chéo</summary><ReviewForm disabled={busy} choices={[{value: "REVOKE", label: "Thu hồi quyền góp ý"}]} onSubmit={(_, revokeReason) => run(() => request(`/theses/${thesis.id}/progress-reviewers/${item.lecturer_id}/revoke`, context.user_id, {
            method: "POST", headers: {"If-Match": String(thesis.row_version)}, body: JSON.stringify({reason: revokeReason}),
          }), "Đã thu hồi phân công góp ý chéo.")} /></details>}
        </div>)}
        {thesis.actions.includes("progress:assign_reviewer") && active && <form className="core-form" onSubmit={async event => {
          event.preventDefault();
          if (await run(() => request(`/theses/${thesis.id}/progress-reviewers`, context.user_id, {method: "POST", headers: {"If-Match": String(thesis.row_version)}, body: JSON.stringify({lecturer_id: lecturerId, reason})}), "Đã phân công giảng viên góp ý chéo tiến độ.")) {setReason(""); setLecturerId("");}
        }}>
          <h3>Phân công giảng viên góp ý chéo tiến độ</h3>
          <p className="text-body-sm text-muted">Người góp ý chéo chỉ được gửi nhận xét; chỉ GVHD chính mới được xác nhận hoặc yêu cầu sửa.</p>
          <div className="input-group"><label htmlFor="reviewer-lecturer">Giảng viên</label><select className="input" id="reviewer-lecturer" value={lecturerId} onChange={event => setLecturerId(event.target.value)} required disabled={busy}><option value="">Chọn giảng viên cùng bộ môn</option>{lecturers.filter(item => item.id !== thesis.advisor_lecturer_id && !(thesis.cross_reviewers || []).some(reviewer => reviewer.lecturer_id === item.id)).map(item => <option key={item.id} value={item.id}>{item.display_name} · {item.lecturer_code}</option>)}</select></div>
          <div className="input-group"><label htmlFor="reviewer-reason">Căn cứ / lý do phân công</label><textarea className="input" id="reviewer-reason" value={reason} onChange={event => setReason(event.target.value)} minLength={3} maxLength={2000} required disabled={busy} /></div>
          <button className="btn btn-primary" disabled={busy || !lecturerId || reason.trim().length < 3}>Giao góp ý chéo</button>
        </form>}
      </div></div>
      {thesis.actions.includes("work:view") && <div className="card"><div className="card-body"><ThesisWork thesis={thesis} assignments={work} context={context} busy={busy} run={run} /></div></div>}
      {thesis.actions.includes("audit:view") && <details className="card"><summary className="card-body">Lịch sử thao tác nghiệp vụ</summary><div className="card-body stack">{audit.map((event, index) => <p key={`${event.occurred_at}-${index}`}><strong>{event.actor_name}</strong> · {event.action} · {formatDate(event.occurred_at)}<br />{event.reason}</p>)}</div></details>}
    </div>}
    {section === "progress" && <div className="stack"><DocumentDeadlines thesis={thesis} deadlines={deadlines} userId={context.user_id} busy={busy} run={run} /><ThesisProgress thesis={thesis} milestones={milestones} reports={reports} docs={docs} milestoneHistory={milestoneHistory} userId={context.user_id} studentId={context.student_id} busy={busy} run={run} /></div>}
    {section === "proposal" && proposal && <ThesisProposal thesis={thesis} proposal={proposal} deadline={deadlines.find(item => item.document_type === "PROPOSAL")} lecturers={lecturers} userId={context.user_id} busy={busy} run={run} />}
    {section === "documents" && <ThesisDocuments thesis={thesis} docs={docs} deadlines={deadlines} reports={reports} userId={context.user_id} busy={busy} run={run} />}
  </>;
}
