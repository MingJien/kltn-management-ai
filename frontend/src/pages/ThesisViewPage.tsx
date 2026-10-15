import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { AuditEvent, Context, Lecturer, Milestone, ProgressReport, Thesis, ThesisDocument, WorkAssignment } from "../api";
import { request } from "../api";
import PageHeader from "../components/layout/PageHeader";
import { formatDate, ReviewForm, Status } from "../components/domain/CoreForms";
import ThesisDocuments from "../components/domain/ThesisDocuments";
import ThesisProgress from "../components/domain/ThesisProgress";
import ThesisWork from "../components/domain/ThesisWork";

type Data = {thesis: Thesis; milestones: Milestone[]; reports: ProgressReport[]; docs: ThesisDocument[]; work: WorkAssignment[]; lecturers: Lecturer[]; audit: AuditEvent[]};

export default function ThesisViewPage({context}: {context: Context}) {
  const {thesisId} = useParams();
  return <ThesisWorkspace key={`${context.user_id}:${thesisId}`} context={context} />;
}

function ThesisWorkspace({context}: {context: Context}) {
  const {thesisId} = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [lecturerId, setLecturerId] = useState("");
  const [reason, setReason] = useState("");
  const [assignmentType, setAssignmentType] = useState("advisor-nomination");
  const load = useCallback(async (signal?: AbortSignal) => {
    const path = `/theses/${thesisId}`;
    const thesis = await request<Thesis>(path, context.user_id, {signal});
    const get = <T,>(suffix: string, action?: string): Promise<T[]> => !action || thesis.actions.includes(action)
      ? request<T[]>(path+suffix, context.user_id, {signal}) : Promise.resolve([]);
    const [milestones, reports, docs, work, lecturers, audit] = await Promise.all([
      get<Milestone>("/milestones"), get<ProgressReport>("/progress-reports", "progress:view"),
      get<ThesisDocument>("/documents", "document:view"), get<WorkAssignment>("/work-assignments", "work:view"),
      thesis.actions.includes("advisor:nominate") ? request<Lecturer[]>("/lecturers", context.user_id, {signal}) : Promise.resolve([]),
      get<AuditEvent>("/audit", "audit:view"),
    ]);
    if (!signal?.aborted) setData({thesis, milestones, reports, docs, work, lecturers, audit});
  }, [thesisId, context.user_id]);

  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(""); setMessage("");
    void load(controller.signal).catch(cause => {if (!controller.signal.aborted) setError(String(cause));});
    return () => controller.abort();
  }, [load]);

  async function run(action: () => Promise<unknown>, success: string) {
    if (busy) return false;
    setBusy(true); setError(""); setMessage("");
    try {await action(); await load(); setMessage(success); return true;}
    catch (cause) {setError(String(cause)); return false;}
    finally {setBusy(false);}
  }

  if (!data) return <><Link to="/theses">Quay lại khóa luận</Link>{error ? <div className="alert alert-danger" role="alert">{error}</div> : <p role="status">Đang tải hồ sơ khóa luận…</p>}</>;
  const {thesis, docs, milestones, reports, work, lecturers, audit} = data;
  const tabs = ["overview", ...(thesis.actions.includes("progress:view") || thesis.actions.includes("milestone:manage") ? ["progress"] : []),
    ...(thesis.actions.includes("document:view") ? ["documents"] : [])];
  const section = tabs.includes(params.get("section") || "") ? params.get("section")! : "overview";
  const active = ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state);
  return <>
    <Link to="/theses">← Danh sách khóa luận</Link>
    <PageHeader title={thesis.title} description={`${thesis.round_label} · GVHD: ${thesis.advisor_name || "Chưa có"}`} />
    <div className="core-toolbar"><Status value={thesis.state} />{tabs.map(tab => <button type="button" key={tab} className={`btn ${section === tab ? "btn-primary" : "btn-secondary"}`} aria-pressed={section === tab} onClick={() => setParams({section: tab})}>{tab === "overview" ? "Tổng quan & GVHD" : tab === "progress" ? "Tiến độ" : "Tài liệu"}</button>)}</div>
    {error && <div className="alert alert-danger" role="alert">{error} <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void run(async () => {}, "Đã tải dữ liệu mới.")}>Tải lại dữ liệu</button></div>}
    {message && <div className="alert alert-success" role="status">{message}</div>}
    {busy && <p role="status">Đang lưu và cập nhật hồ sơ…</p>}
    {section === "overview" && <div className="stack">
      <div className="card"><div className="card-body stack"><h2>Thành viên</h2>{thesis.members.map(member => <p key={member.student_id}><strong>{member.display_name}</strong> · {member.student_code}{member.is_coordinator ? " · Nhóm trưởng điều phối" : ""}</p>)}</div></div>
      <div className="card"><div className="card-body stack"><h2>Phân công GVHD</h2>
        {thesis.pending_advisor && <p>Chờ {thesis.pending_advisor.display_name} đồng ý. GVHD hiện tại tiếp tục hướng dẫn đến khi người mới nhận phân công.</p>}
        {thesis.actions.includes("advisor:respond") && active && <ReviewForm disabled={busy} choices={[{value: "ACCEPT", label: "Đồng ý nhận hướng dẫn"}, {value: "DECLINE", label: "Từ chối phân công"}]} onSubmit={async (decision, responseReason) => {
          if (decision === "ACCEPT") return run(() => request(`/theses/${thesis.id}/advisor-response`, context.user_id, {method: "POST", headers: {"If-Match": String(thesis.row_version)}, body: JSON.stringify({decision, reason: responseReason})}), "Đã nhận hướng dẫn khóa luận.");
          setBusy(true); setError("");
          try {await request(`/theses/${thesis.id}/advisor-response`, context.user_id, {method: "POST", headers: {"If-Match": String(thesis.row_version)}, body: JSON.stringify({decision, reason: responseReason})}); navigate("/theses"); return true;}
          catch (cause) {setError(String(cause)); return false;} finally {setBusy(false);}
        }} />}
        {thesis.advisor_history.map(item => <div className="core-review" key={item.id}><strong>{item.display_name}</strong> · <Status value={item.state} label={item.state === "ACTIVE" ? "Đang hướng dẫn" : undefined} /><p className="text-body-sm text-muted">Từ {formatDate(item.effective_from)}{item.effective_to ? ` đến ${formatDate(item.effective_to)}` : ""}</p></div>)}
        {(thesis.cross_reviewers || []).map(item => <div className="core-review" key={item.lecturer_id}><strong>Góp ý chéo: {item.display_name}</strong>
          {thesis.actions.includes("progress:assign_reviewer") && active && <details><summary>Thu hồi phân công góp ý chéo</summary><ReviewForm disabled={busy} choices={[{value: "REVOKE", label: "Thu hồi quyền góp ý"}]} onSubmit={(_, revokeReason) => run(() => request(`/theses/${thesis.id}/progress-reviewers/${item.lecturer_id}/revoke`, context.user_id, {
            method: "POST", headers: {"If-Match": String(thesis.row_version)}, body: JSON.stringify({reason: revokeReason}),
          }), "Đã thu hồi phân công góp ý chéo.")} /></details>}
        </div>)}
        {thesis.actions.includes("advisor:nominate") && active && <form className="core-form" onSubmit={async event => {
          event.preventDefault();
          if (await run(() => request(`/theses/${thesis.id}/${assignmentType}`, context.user_id, {method: "POST", headers: {"If-Match": String(thesis.row_version)}, body: JSON.stringify({lecturer_id: lecturerId, reason})}), assignmentType === "advisor-nomination" ? "Đã gửi phân công, chờ GVHD mới đồng ý." : "Đã phân công góp ý chéo.")) setReason("");
        }}>
          <div className="input-group"><label htmlFor="advisor-type">Phân công</label><select className="input" id="advisor-type" value={assignmentType} onChange={event => setAssignmentType(event.target.value)} disabled={busy}><option value="advisor-nomination">GVHD chính mới (cần đồng ý)</option><option value="progress-reviewers">Giảng viên góp ý chéo tiến độ</option></select></div>
          <div className="input-group"><label htmlFor="advisor-lecturer">Giảng viên</label><select className="input" id="advisor-lecturer" value={lecturerId} onChange={event => setLecturerId(event.target.value)} required disabled={busy}><option value="">Chọn giảng viên cùng bộ môn</option>{lecturers.filter(item => item.id !== thesis.advisor_lecturer_id).map(item => <option key={item.id} value={item.id}>{item.display_name} · {item.lecturer_code}</option>)}</select></div>
          <div className="input-group"><label htmlFor="advisor-reason">Căn cứ / lý do phân công</label><textarea className="input" id="advisor-reason" value={reason} onChange={event => setReason(event.target.value)} minLength={3} maxLength={2000} required disabled={busy} /></div>
          <button className="btn btn-primary" disabled={busy || !lecturerId || reason.trim().length < 3}>Gửi phân công</button>
        </form>}
      </div></div>
      {thesis.actions.includes("work:view") && <div className="card"><div className="card-body"><ThesisWork thesis={thesis} assignments={work} context={context} busy={busy} run={run} /></div></div>}
      {thesis.actions.includes("audit:view") && <details className="card"><summary className="card-body">Lịch sử thao tác nghiệp vụ</summary><div className="card-body stack">{audit.map((event, index) => <p key={`${event.occurred_at}-${index}`}><strong>{event.actor_name}</strong> · {event.action} · {formatDate(event.occurred_at)}<br />{event.reason}</p>)}</div></details>}
    </div>}
    {section === "progress" && <ThesisProgress thesis={thesis} milestones={milestones} reports={reports} docs={docs} userId={context.user_id} busy={busy} run={run} />}
    {section === "documents" && <ThesisDocuments thesis={thesis} docs={docs} userId={context.user_id} busy={busy} run={run} />}
  </>;
}
