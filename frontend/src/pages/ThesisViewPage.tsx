import LecturerProfileLink from "../components/domain/LecturerProfileDialog";
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, ArrowLeftRight, BookOpen, ClipboardList, FileX, FolderOpen, GraduationCap, History, RefreshCw, Scale } from "lucide-react";
import { ApiError, errorMessage } from "../errors";
import type { AuditEvent, Context, DocumentDeadline, Lecturer, Milestone, ProgressReport, Proposal, Thesis, ThesisDocument, WorkAssignment } from "../api";
import { request } from "../api";
import { actionLabel } from "../activity";
import PageHeader from "../components/layout/PageHeader";
import Tabs from "../components/ui/Tabs";
import { ActivityTimeline, ThesisJourney, inferTimelineTone, type JourneyStage } from "../components/ui/Timeline";
import { CampusBannerArt } from "../components/ui/CampusArtwork";
import { SkeletonCard } from "../components/ui/Skeleton";
import { formatDate, ReviewForm, Status } from "../components/domain/CoreForms";
import ThesisSubmissions from "../components/domain/ThesisSubmissions";
import ThesisProgress from "../components/domain/ThesisProgress";
import ThesisWork from "../components/domain/ThesisWork";

type Data = {thesis: Thesis; milestones: Milestone[]; deadlines: DocumentDeadline[]; deadlineHistory:AuditEvent[]; reports: ProgressReport[]; docs: ThesisDocument[]; work: WorkAssignment[]; lecturers: Lecturer[]; audit: AuditEvent[]; milestoneHistory: AuditEvent[]; proposal: Proposal | null};

function buildWorkspaceJourney(thesis: Thesis, proposal: Proposal | null): JourneyStage[] {
  const st = thesis.state;
  if (st === "WITHDRAWN") {
    return [
      { id: "reg", title: "Đăng ký", statusText: "Đã thôi thực hiện", state: "done", to: "/withdrawals" },
      { id: "proposal", title: "Đề cương", statusText: "Đã kết thúc", state: "upcoming" },
      { id: "progress", title: "Tiến độ", statusText: "Đã kết thúc", state: "upcoming" },
      { id: "eval", title: "Phản biện", statusText: "Đã kết thúc", state: "upcoming" },
      { id: "defense", title: "Bảo vệ", statusText: "Đã kết thúc", state: "upcoming" },
    ];
  }
  const proposalApproved = ["DEPARTMENT_FINALIZED", "DEAN_CONFIRMED", "PRINT_READY"].includes(proposal?.state || "") ||
    ["PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED", "READY_FOR_DEFENSE", "DEFENDED", "COMPLETED", "ARCHIVED"].includes(st);
  const progressDone = ["READY_FOR_DEFENSE", "DEFENDED", "COMPLETED", "ARCHIVED"].includes(st);
  const defenseDone = ["DEFENDED", "COMPLETED", "ARCHIVED"].includes(st);
  return [
    { id: "reg", title: "Đăng ký", statusText: "Đã tiếp nhận", state: "done" },
    { id: "proposal", title: "Đề cương", statusText: proposalApproved ? "Đã duyệt" : "Đang thực hiện", state: proposalApproved ? "done" : "current", to: `/theses/${thesis.id}?section=submissions&kind=PROPOSAL` },
    { id: "progress", title: "Tiến độ", statusText: progressDone ? "Hoàn tất" : proposalApproved ? "Đang thực hiện" : "Chờ đề cương", state: progressDone ? "done" : proposalApproved ? "current" : "upcoming", to: `/theses/${thesis.id}?section=progress` },
    { id: "eval", title: "Phản biện", statusText: defenseDone ? "Hoàn tất" : st === "READY_FOR_DEFENSE" ? "Đủ điều kiện" : "Chưa đến", state: defenseDone ? "done" : st === "READY_FOR_DEFENSE" ? "current" : "upcoming", to: thesis.actions.includes("evaluation:view") ? `/evaluation/${thesis.id}` : undefined },
    { id: "defense", title: "Bảo vệ", statusText: st === "COMPLETED" || st === "ARCHIVED" ? "Hoàn thành" : st === "DEFENDED" ? "Đã bảo vệ" : "Chưa đến", state: defenseDone ? "done" : "upcoming", to: "/defense" },
  ];
}

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
    const thesis = await request<Thesis>(path, context.user_id, {signal}).catch(cause => {
      if (!signal?.aborted && cause instanceof ApiError && [403, 404].includes(cause.status)) {
        setData(null);
        setUpdatedAt(null);
      }
      throw cause;
    });
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
    void load(controller.signal).catch(cause => {if (!controller.signal.aborted) setError(errorMessage(cause));});
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    if (data && location.hash === "#work-assignments") {
      document.getElementById("work-assignments")?.scrollIntoView({block: "start"});
    }
  }, [data, location.hash]);

  async function run(action: () => Promise<unknown>, success: string, onConflict?: () => void) {
    if (busy) return false;
    setBusy(true); setError(""); setMessage("");
    try {await action(); await load(); setMessage(success); return true;}
    catch (cause) {
      if (onConflict && cause instanceof ApiError && cause.status === 409) {
        onConflict();
      } else {
        setError(errorMessage(cause));
        await load().catch(() => undefined);
      }
      return false;
    }
    finally {setBusy(false);}
  }
  async function refresh() {
    if (busy) return;
    setRefreshing(true);
    try {await run(async () => {}, "Đã làm mới dữ liệu hồ sơ khóa luận.");}
    finally {setRefreshing(false);}
  }

  if (!data) return <><Link className="workspace-back-link" to="/theses"><ArrowLeft size={15} aria-hidden="true" />Danh sách khóa luận</Link>{error ? <div className="alert alert-danger" role="alert">{error} <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void refresh()}>Thử tải lại hồ sơ</button></div> : <div className="stack mt-4" role="status" aria-label="Đang tải hồ sơ khóa luận"><SkeletonCard /><SkeletonCard /></div>}</>;
  const {thesis, docs, milestones, deadlines, deadlineHistory, reports, work, lecturers, audit, milestoneHistory, proposal} = data;
  const tabs = ["overview", ...(proposal || thesis.actions.includes("document:view") || thesis.actions.includes("milestone:manage") ? ["submissions"] : []),
    ...(thesis.actions.includes("progress:view") || thesis.actions.includes("milestone:manage") ? ["progress"] : [])];
  const requested = params.get("section") || "overview";
  const normalized = ["proposal", "documents"].includes(requested) ? "submissions" : requested;
  const section = tabs.includes(normalized) ? normalized : "overview";
  const submissionKind = params.get("kind") || (requested === "proposal" ? "PROPOSAL" : "PLAN");
  const active = ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state);
  const canRequestWithdrawal = active;
  const canRequestChangeOrExtension = active || thesis.state === "READY_FOR_DEFENSE";
  const sectionTabs = tabs.map(tab => ({
    id: tab,
    label: tab === "overview" ? "Tổng quan & GVHD" : tab === "progress" ? "Báo cáo tiến độ" : "Hồ sơ nộp & xét duyệt",
    icon: tab === "overview" ? <GraduationCap size={15} /> : tab === "progress" ? <ClipboardList size={15} /> : <FolderOpen size={15} />,
  }));
  const auditItems = audit.map((event, index) => ({
    id: `${event.occurred_at}-${index}`,
    title: actionLabel(event.action),
    actor: event.actor_name,
    timestamp: formatDate(event.occurred_at),
    note: event.reason || undefined,
    tone: inferTimelineTone(event.action),
  }));

  return <>
    <Link to="/theses" className="workspace-back-link">
      <ArrowLeft size={15} aria-hidden="true" /> Danh sách khóa luận
    </Link>
    <PageHeader title={{overview:"Khóa luận & GVHD",submissions:"Hồ sơ nộp & xét duyệt",progress:"Báo cáo tiến độ"}[section] || "Hồ sơ khóa luận"} description={`${thesis.title} · ${thesis.round_label} · GVHD: ${thesis.advisor_name || "Chưa gán"}`}>
      <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={()=>void refresh()}><RefreshCw size={14} aria-hidden="true" />{refreshing ? "Đang làm mới…" : "Làm mới dữ liệu"}</button>
    </PageHeader>
    {(canRequestWithdrawal || canRequestChangeOrExtension || thesis.actions.includes("archive:view") || thesis.actions.includes("evaluation:view")) && <nav className="flex flex-wrap gap-2 mb-3" aria-label="Quy trình liên quan">
      {thesis.actions.includes("archive:view") && <Link className="btn btn-primary btn-sm" to={`/repository?mode=work&focus=${thesis.id}`}><BookOpen size={14} aria-hidden="true" />Hồ sơ nộp lưu sau bảo vệ</Link>}
      {canRequestWithdrawal && <Link className="btn btn-secondary btn-sm" to={`/withdrawals?thesis=${thesis.id}`}><FileX size={14} aria-hidden="true" />Xin thôi thực hiện KLTN</Link>}
      {canRequestChangeOrExtension && <Link className="btn btn-secondary btn-sm" to={`/changes?thesis=${thesis.id}`}><ArrowLeftRight size={14} aria-hidden="true" />Đổi đề tài &amp; gia hạn</Link>}
      {thesis.actions.includes("evaluation:view") && <Link className="btn btn-soft btn-sm" to={`/evaluation/${thesis.id}`}><Scale size={14} aria-hidden="true" />Phản biện &amp; điều kiện dự bảo vệ</Link>}
    </nav>}
    {context.base_role === "STUDENT" && active && !thesis.actions.includes("document:submit") && <p className="alert alert-warning" role="status">Quyền tham gia đợt của bạn đã bị thu hồi. Bạn vẫn xem được hồ sơ; các thao tác nộp/sửa được tạm dừng. Liên hệ Khoa nếu cần khôi phục.</p>}
    {updatedAt && <p className="text-caption mb-2">Dữ liệu cập nhật lúc {formatDate(updatedAt.toISOString())}.</p>}
    <div className="core-toolbar">
      <Tabs variant="underline" idPrefix="thesis-section" ariaLabel="Phân hệ hồ sơ khóa luận" items={sectionTabs} activeId={section} onChange={(next) => setParams({section: next})} />
      <div className="core-toolbar__status">
        <span className="core-toolbar__status-label">Trạng thái:</span>
        <Status value={thesis.state} />
      </div>
    </div>

    {error && <div className="alert alert-danger" role="alert">{error} <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void run(async () => {}, "Đã tải dữ liệu mới.")}>Tải lại dữ liệu</button></div>}
    {message && <div className="alert alert-success" role="status">{message}</div>}
    {busy && <p role="status">{refreshing ? "Đang tải dữ liệu mới…" : "Đang lưu và cập nhật hồ sơ…"}</p>}
    {section === "overview" && <div className="stack">
      <section className="thesis-identity card">
        <CampusBannerArt className="thesis-hero__art" />
        <div className="card-body stack">
          <div>
            <div className="thesis-hero__header">
              <span className="section-eyebrow m-0">HỒ SƠ ĐANG LÀM VIỆC</span>
              <span className="thesis-hero__round">{thesis.round_label}</span>
            </div>
            <h2>{thesis.title}</h2>
            <p className="text-body-sm text-muted">
              {thesis.members.length} sinh viên · GVHD:{" "}
              <strong>
                <LecturerProfileLink userId={context.user_id} lecturerId={thesis.advisor_lecturer_id} name={thesis.advisor_name} />
              </strong>
            </p>
          </div>
          <ThesisJourney compact stages={buildWorkspaceJourney(thesis, proposal)} ariaLabel="Tiến trình khóa luận" />
        </div>
      </section>

      <div className="workspace-overview-grid">
        <div className="stack workspace-main-col">
          <div className="card">
            <div className="card-body stack">
              <div className="flex flex-wrap justify-between items-center gap-3">
                <div>
                  <h2 className="section-heading-sm">Thao tác đề cương, tiến độ và tài liệu</h2>
                  <p className="text-body-sm text-muted mt-1">Chuyển nhanh tới phân hệ để nộp và kiểm tra hồ sơ</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {thesis.actions.includes("archive:view") && ["DEFENDED", "COMPLETED"].includes(thesis.state) ? (
                    <Link className="btn btn-primary btn-sm" to={`/repository?mode=work&focus=${thesis.id}`}>
                      <BookOpen size={14} aria-hidden="true" />Mở hồ sơ nộp lưu
                    </Link>
                  ) : null}
                  {proposal || thesis.actions.includes("document:view") || thesis.actions.includes("milestone:manage") ? (
                    <Link className="btn btn-soft btn-sm" to={"/theses/" + thesis.id + "?section=submissions"}>
                      <FolderOpen size={14} aria-hidden="true" />Mở hồ sơ nộp &amp; xét duyệt
                    </Link>
                  ) : null}
                  {thesis.actions.includes("progress:view") || thesis.actions.includes("milestone:manage") ? (
                    <Link className="btn btn-secondary btn-sm" to={`/theses/${thesis.id}?section=progress`}>
                      <ClipboardList size={14} aria-hidden="true" />Mở mốc và báo cáo tiến độ
                    </Link>
                  ) : null}
                </div>
              </div>
            </div>
          </div>

          {thesis.actions.includes("work:view") && (
            <div className="card" id="work-assignments">
              <div className="card-body">
                <ThesisWork thesis={thesis} assignments={work} context={context} busy={busy} run={run} />
              </div>
            </div>
          )}

          {thesis.actions.includes("audit:view") && (
            <details className="card">
              <summary className="card-body flex items-center gap-2">
                <History size={16} aria-hidden="true" />
                Lịch sử thao tác nghiệp vụ ({auditItems.length})
              </summary>
              <div className="card-body">
                <ActivityTimeline items={auditItems} initialLimit={6} ariaLabel="Lịch sử thao tác nghiệp vụ" />
              </div>
            </details>
          )}
        </div>

        <aside className="stack workspace-side-col" aria-label="Thành viên và giảng viên hướng dẫn">
          <div className="card">
            <div className="card-body stack">
              <h2 className="section-heading-sm">Nhóm sinh viên thực hiện</h2>
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
              <h2 className="section-heading-sm">Giảng viên hướng dẫn chính thức</h2>
              {thesis.advisor_history.map(item => (
                <div className="core-review" key={item.id}>
                  <strong><LecturerProfileLink userId={context.user_id} lecturerId={item.lecturer_id} name={item.display_name}/></strong> · <Status value={item.state} label={item.state === "ACTIVE" ? "Đang hướng dẫn" : undefined} />
                  <p className="text-body-sm text-muted mt-1">Từ {formatDate(item.effective_from)}{item.effective_to ? ` đến ${formatDate(item.effective_to)}` : ""}</p>
                </div>
              ))}
              {(thesis.cross_reviewers || []).map(item => (
                <div className="core-review" key={item.lecturer_id}>
                  <strong>Góp ý chéo: {item.display_name}</strong>
                  {thesis.actions.includes("progress:assign_reviewer") && active && (
                    <details className="mt-2"><summary>Thu hồi phân công góp ý chéo</summary>
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
                  <h3 className="section-heading-xs">Phân công giảng viên góp ý chéo</h3>
                  <div className="input-group"><label htmlFor="reviewer-lecturer">Giảng viên</label><select className="input" id="reviewer-lecturer" value={lecturerId} onChange={event => setLecturerId(event.target.value)} required disabled={busy}><option value="">Chọn giảng viên cùng bộ môn</option>{lecturers.filter(item => item.id !== thesis.advisor_lecturer_id && !(thesis.cross_reviewers || []).some(reviewer => reviewer.lecturer_id === item.id)).map(item => <option key={item.id} value={item.id}>{item.display_name} · {item.lecturer_code}</option>)}</select></div>
                  <div className="input-group"><label htmlFor="reviewer-reason">Lý do phân công</label><textarea className="input" id="reviewer-reason" value={reason} onChange={event => setReason(event.target.value)} minLength={3} maxLength={2000} required disabled={busy} /></div>
                  <button className="btn btn-primary btn-sm" disabled={busy || !lecturerId || reason.trim().length < 3}>Giao góp ý chéo</button>
                </form>
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>}
    {section === "progress" && <div className="stack"><ThesisProgress thesis={thesis} milestones={milestones} reports={reports} docs={docs} milestoneHistory={milestoneHistory} userId={context.user_id} studentId={context.student_id} busy={busy} run={run} /></div>}
    {section === "submissions" && <ThesisSubmissions thesis={thesis} proposal={proposal} docs={docs} deadlines={deadlines} history={deadlineHistory} lecturers={lecturers} reports={reports} userId={context.user_id} busy={busy} run={run} kind={submissionKind} />}
  </>;
}
