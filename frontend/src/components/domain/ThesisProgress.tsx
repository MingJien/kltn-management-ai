import EmptyState from "../ui/EmptyState";
import { lazy, Suspense, useState } from "react";
import { MessageSquare, X } from "lucide-react";
import type { AuditEvent, Milestone, ProgressReport, Thesis, ThesisDocument } from "../../api";
import { downloadProgressEvidence, request, uploadProgressEvidence, submitProgress } from "../../api";
import { scanLabel, type CoreRun } from "./ThesisDocuments";
import { formatDate, ReviewForm, Reviews, Status } from "./CoreForms";

const ProgressReviewWorkspace = lazy(() => import("./ProgressReviewWorkspace"));

function ExtendForm({thesis, milestone, userId, busy, run}: {
  thesis: Thesis; milestone: Milestone; userId: string; busy: boolean; run: CoreRun;
}) {
  const [dueAt, setDueAt] = useState("");
  const [reason, setReason] = useState("");
  return <details><summary>{milestone.scope==="THESIS"?"Gia hạn mốc nội bộ":milestone.state === "CLOSED" ? "Gia hạn và mở lại toàn đợt" : "Gia hạn cho toàn đợt"}</summary><form className="core-form" onSubmit={async event => {
    event.preventDefault();
    if (await run(() => request(`/theses/${thesis.id}/milestones/${milestone.id}/extend`, userId, {
      method: "POST", headers: {"If-Match": String(milestone.row_version)},
      body: JSON.stringify({due_at: new Date(dueAt + "+07:00").toISOString(), reason}),
    }), "Đã gia hạn mốc đúng phạm vi; báo cáo cũ giữ nguyên nhãn đúng/trễ.")) {setDueAt(""); setReason("");}
  }}>
    <label htmlFor={`extend-due-${milestone.id}`}>Hạn mới (giờ Việt Nam)</label>
    <input className="input" id={`extend-due-${milestone.id}`} type="datetime-local" value={dueAt}
      onChange={event => setDueAt(event.target.value)} required disabled={busy} />
    <label htmlFor={`extend-reason-${milestone.id}`}>Lý do gia hạn</label>
    <textarea className="input" id={`extend-reason-${milestone.id}`} value={reason}
      onChange={event => setReason(event.target.value)} required minLength={3} maxLength={2000} disabled={busy} />
    <button className="btn btn-secondary" disabled={busy || !dueAt || reason.trim().length < 3}>{milestone.state === "CLOSED" ? "Gia hạn và mở lại mốc" : "Lưu gia hạn"}</button>
  </form></details>;
}

function ProgressEvidence({report, thesis, userId, busy, run, readOnly = false}: {
  report: ProgressReport; thesis: Thesis; userId: string; busy:boolean; run:CoreRun; readOnly?: boolean;
}) {
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [viewing, setViewing] = useState(false);
  const clean = report.evidence_scan_state === "CLEAN";
  return <div className="stack">
    <div className="progress-evidence-row">
      <p className="text-body-sm" style={{margin: 0}}>Minh chứng của báo cáo: <strong>{report.evidence_file_name}</strong> · {scanLabel(report.evidence_scan_state || "QUARANTINED")}.</p>
      <div className="progress-evidence-actions" style={{flexWrap: "wrap", flexShrink: 1, minWidth: 0}}>
        {clean && <button type="button" className="btn btn-primary btn-sm" style={{whiteSpace: "normal", maxWidth: "100%"}} onClick={() => setViewing(true)}><MessageSquare size={16} /> {readOnly || !thesis.actions.some(action => ["progress:review", "progress:comment"].includes(action)) ? "Xem tệp & nhận xét" : "Mở tệp và phản hồi theo vị trí"}</button>}
        {viewing && <Suspense fallback={<p role="status">Đang mở không gian nhận xét…</p>}><ProgressReviewWorkspace thesis={thesis} report={report} userId={userId} run={run} onClose={() => setViewing(false)} /></Suspense>}
        <button type="button" className="btn btn-secondary btn-sm" disabled={!clean || downloading}
          title={!clean ? "Tệp chưa được quét an toàn" : undefined} onClick={async () => {
            setError(""); setDownloading(true);
            try {await downloadProgressEvidence(thesis.id, report);} catch (cause) {setError(String(cause));}
            finally {setDownloading(false);}
          }}>Tải minh chứng của báo cáo</button>
        {!readOnly && ["QUARANTINED","FAILED"].includes(report.evidence_scan_state || "") && <button type="button" className="btn btn-secondary btn-sm" disabled={busy}
          onClick={()=>run(()=>request(`/theses/${thesis.id}/progress-reports/${report.id}/evidence/scan`,userId,{method:"POST"}),"Đã quét lại minh chứng; xem trạng thái tệp.")}>Quét lại minh chứng</button>}
      </div>
    </div>
    {error && <p role="alert" className="alert alert-danger">{error}</p>}
  </div>;
}

export default function ThesisProgress({thesis, milestones, reports, docs, milestoneHistory, userId, studentId, busy, run}: {
  thesis: Thesis; milestones: Milestone[]; reports: ProgressReport[]; docs: ThesisDocument[];
  milestoneHistory: AuditEvent[]; userId: string; studentId: string | null; busy: boolean; run: CoreRun;
}) {
  const [code, setCode] = useState("");
  const [scope,setScope] = useState<"THESIS"|"ROUND">(thesis.actions.includes("milestone:manage_own")?"THESIS":"ROUND");
  const canManageMilestone=(item:Milestone)=>thesis.actions.includes(item.scope==="THESIS"?"milestone:manage_own":"milestone:manage");
  const [title, setTitle] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [expectedRatio, setExpectedRatio] = useState("");
  const [milestoneId, setMilestoneId] = useState("");
  const [summary, setSummary] = useState("");
  const [ratio, setRatio] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidenceNotice, setEvidenceNotice] = useState("");
  const active = ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state);
  const latest = new Map<string, ProgressReport>();
  for (const report of reports) {
    if ((latest.get(report.milestone_id)?.version_no || 0) < report.version_no) latest.set(report.milestone_id, report);
  }
  const available = milestones.filter(item => {
    const previous = latest.get(item.id);
    if (previous?.state === "REVISION_REQUIRED") return true;
    if (item.state !== "OPEN") return false;
    if (!previous) return true; // An initial report may still be accepted late while the round milestone is open.
    return previous.submitted_by_student_id === studentId && previous.state === "SUBMITTED" && previous.reviews.length === 0 && !!item.due_at
      && Date.now() <= new Date(item.due_at).getTime();
  });
  const selected = available.some(item => item.id === milestoneId) ? milestoneId : "";
  const milestoneAudit = milestoneHistory;
  const milestoneAction: Record<string, string> = {MILESTONE_OPENED: "Mở mốc", MILESTONE_EXTENDED: "Gia hạn mốc", MILESTONE_REOPENED: "Gia hạn và mở lại mốc", MILESTONE_CLOSED: "Đóng mốc"};
  const renderReportDetails = (report: ProgressReport, isCurrent: boolean) => <>
      <p className="text-body-sm text-muted">{report.submitted_by_name} · {formatDate(report.submitted_at)} · Tự báo cáo {report.reported_ratio}% {report.late && <strong className="late-badge" aria-label="Nộp trễ">Nộp trễ</strong>}</p>
      <p className="text-body-sm text-muted">Hạn áp dụng lúc nộp: {formatDate(report.due_at_at_submission)}</p>
      <p className="core-prewrap">{report.summary}</p>
      {report.evidence_document_version_id && <ProgressEvidence report={report} thesis={thesis} userId={userId} busy={busy} run={run} readOnly={!isCurrent} />}
      {report.state === "SUBMITTED" && !report.evidence_document_version_id && report.submitted_by_student_id === studentId && report.reviews.length === 0 && isCurrent && milestones.some(item => item.id === report.milestone_id && item.state === "OPEN" && !!item.due_at && Date.now() <= new Date(item.due_at).getTime()) &&
        <div className="input-group"><label htmlFor={`retry-evidence-${report.id}`}>Bổ sung minh chứng từ máy cho báo cáo này (không bắt buộc)</label>
          <input className="input" id={`retry-evidence-${report.id}`} type="file" accept=".pdf,.docx,.txt" disabled={busy}
            onChange={async event => {
              const file = event.target.files?.[0];
              if (!file) return;
              if (file.size > 10*1024*1024) {setEvidenceNotice("Tệp vượt quá 10 MB."); return;}
              if (await run(() => uploadProgressEvidence(thesis.id, report, userId, file), "Đã lưu minh chứng, chờ quét an toàn.")) {
                setEvidenceNotice(""); event.target.value = "";
              }
            }} />
        </div>}
      <Reviews items={report.reviews} />
      {active && report.state === "SUBMITTED" && isCurrent && !(report.evidence_document_version_id && report.evidence_scan_state === "CLEAN") &&
        ((thesis.actions.includes("progress:review") || thesis.actions.includes("progress:comment"))) &&
        <ReviewForm key={report.id} disabled={busy} choices={thesis.actions.includes("progress:review") ? (report.evidence_document_version_id && report.evidence_scan_state !== "CLEAN"
          ? [{value: "REVISION_REQUIRED", label: "Yêu cầu nộp lại (chưa xem tệp)"}]
          : [{value: "CONFIRM", label: "Xác nhận tiến độ"}, {value: "REVISION_REQUIRED", label: "Yêu cầu sửa và nộp lại"}])
          : [{value: "COMMENT_ONLY", label: "Góp ý chéo (không chốt tiến độ)"}]} onSubmit={(decision, comment) => run(() => request(`/theses/${thesis.id}/progress-reports/${report.id}/review`, userId, {
          method: "POST", headers: {"If-Match": String(report.row_version)}, body: JSON.stringify({decision, comment}),
        }), "Đã lưu nhận xét tiến độ.")} />}
  </>;
  return <div className="stack">
    {(thesis.actions.includes("milestone:manage") || thesis.actions.includes("milestone:manage_own")) && active && <form className="card" onSubmit={async event => {
      event.preventDefault();
      if (await run(() => request(`/theses/${thesis.id}/milestones`, userId, {method: "POST", body: JSON.stringify({
        scope, code, title, due_at: new Date(dueAt+"+07:00").toISOString(), expected_ratio: expectedRatio === "" ? null : Number(expectedRatio),
      })}), scope==="THESIS"?"Đã mở mốc riêng cho khóa luận này.":"Đã mở mốc cho toàn đợt.")) {setCode(""); setTitle("");}
    }}><div className="card-body core-form">
      <h3>{scope==="THESIS"?"Tạo mốc nội bộ của khóa luận":"Mở mốc theo kế hoạch đợt"}</h3>
      {thesis.actions.includes("milestone:manage")&&thesis.actions.includes("milestone:manage_own")&&<label>Phạm vi mốc<select className="input" value={scope} onChange={e=>setScope(e.target.value as "THESIS"|"ROUND")}><option value="THESIS">Riêng khóa luận này</option><option value="ROUND">Toàn đợt</option></select></label>}
      <p className="text-body-sm text-muted">{scope==="THESIS"?"GVHD quản lý mốc riêng. Chỉ nhóm SV và GVHD xem và nhận thông báo.":`Áp dụng cho mọi khóa luận trong ${thesis.round_label}.`} Đóng mốc trước khi ban hành phiên bản mới cùng mã.</p>
      <p className="text-body-sm text-muted">Mốc này dùng cho báo cáo tiến độ định kỳ. Hạn nộp từng loại tài liệu (Đề cương, Kế hoạch, Cuốn báo cáo KLTN) được đặt riêng ở mục “Hạn nộp tài liệu theo đợt” phía trên, không phải ở đây.</p>
      <div className="core-fields">
        <div className="input-group"><label htmlFor="milestone-code">Mã mốc</label><input className="input" id="milestone-code" value={code} onChange={event => setCode(event.target.value.toUpperCase())} pattern="(?:[A-Z0-9_]|-){1,50}" maxLength={50} placeholder="NOI_BO_1" required disabled={busy} /></div>
        <div className="input-group"><label htmlFor="milestone-title">Tên mốc</label><input className="input" id="milestone-title" value={title} onChange={event => setTitle(event.target.value)} required maxLength={255} disabled={busy} /></div>
        <div className="input-group"><label htmlFor="milestone-due">Hạn nộp (giờ Việt Nam)</label><input className="input" id="milestone-due" type="datetime-local" value={dueAt} onChange={event => setDueAt(event.target.value)} required disabled={busy} /></div>
        <div className="input-group"><label htmlFor="milestone-ratio">Tiến độ dự kiến (%)</label><input className="input" id="milestone-ratio" type="number" min={0} max={100} step="0.01" value={expectedRatio} onChange={event => setExpectedRatio(event.target.value)} disabled={busy} /></div>
      </div>
      <button className="btn btn-primary" disabled={busy || !title.trim() || !code || !dueAt}>{scope==="THESIS"?"Tạo mốc nội bộ":"Mở mốc cho đợt"}</button>
    </div></form>}
    {milestones.map(milestone => <article className="card" key={milestone.id}><div className="card-body stack">
      <div className="flex justify-between gap-3"><h3>{milestone.title} · v{milestone.version_no}</h3><Status value={milestone.state} /></div>
      <p className="text-muted">{milestone.scope==="THESIS"?"Nội bộ khóa luận":"Mốc chung của đợt"} · {milestone.code} · Hạn: {formatDate(milestone.due_at)}{milestone.expected_ratio !== null ? ` · Dự kiến ${milestone.expected_ratio}%` : ""}</p>
      {canManageMilestone(milestone) && milestone.due_at && active &&
        <ExtendForm thesis={thesis} milestone={milestone} userId={userId} busy={busy} run={run} />}
      {canManageMilestone(milestone) && milestone.state === "OPEN" && active && <details><summary>{milestone.scope==="THESIS"?"Đóng mốc nội bộ":"Đóng mốc cho toàn đợt"}</summary>
        <ReviewForm disabled={busy} choices={[{value: "CLOSE", label: "Đóng mốc, ngừng nhận báo cáo mới"}]} onSubmit={(_, reason) => run(() => request(`/theses/${thesis.id}/milestones/${milestone.id}/close`, userId, {
          method: "POST", headers: {"If-Match": String(milestone.row_version)}, body: JSON.stringify({reason}),
        }), "Đã đóng mốc trong đúng phạm vi.")} />
      </details>}
    </div></article>)}
    {milestones.length === 0 && <div className="card"><div className="card-body">
      <h3>Chưa có mốc tiến độ trong hồ sơ này</h3>
      <p className="text-muted">
        {thesis.actions.includes("milestone:manage_own")?"GVHD sử dụng biểu mẫu phía trên để đặt mốc báo cáo cho khóa luận này.":"GVHD chưa mở mốc nội bộ cho khóa luận này. Mốc chung của đợt (nếu có) hiển thị riêng."}
      </p>
    </div></div>}
    <div className="card"><div className="card-body stack"><h2>Lịch sử mốc trong phạm vi của bạn</h2>
      <p className="text-body-sm text-muted">Người thực hiện, thời điểm và lý do mở, gia hạn hoặc đóng mốc. Mốc nội bộ chỉ áp dụng cho khóa luận này; mốc chung áp dụng cho toàn đợt. Báo cáo cũ giữ nguyên hạn tại thời điểm nộp.</p>
      {milestoneAudit.length
        ? milestoneAudit.map((event, index) => <p key={`${event.occurred_at}-${index}`} className="text-body-sm">
            <strong>{event.actor_name}</strong> · {milestoneAction[event.action] || event.action} · {formatDate(event.occurred_at)}
            {event.reason ? <><br /><span className="text-muted">{event.reason}</span></> : null}
          </p>)
        : <p className="text-muted">Chưa có thay đổi mốc nào được ghi nhận.</p>}
    </div></div>
    {thesis.actions.includes("progress:submit") && active && available.length === 0 && milestones.length > 0 && (
      <div className="card"><div className="card-body">
        <h3>Không có mốc nào đang mở nhận báo cáo</h3>
        <p className="text-muted">
          Các mốc đã đóng, báo cáo đã được phản hồi hoặc đã hết hạn tự sửa. Nếu GVHD yêu cầu sửa, bạn sẽ nộp được phiên bản mới kể cả sau khi mốc đóng. GVHD quản lý hạn mốc nội bộ; người điều phối quản lý hạn mốc chung của đợt.
        </p>
      </div></div>
    )}
    {thesis.actions.includes("progress:comment") && !thesis.actions.includes("progress:review") && (
      <p className="alert alert-info">
        Bạn được phân công góp ý chéo cho khóa luận này. Bạn có thể ghi nhận xét góp ý trên các báo cáo của nhóm, nhưng quyền xác nhận tiến độ hoặc yêu cầu sửa chính thức thuộc về GVHD chính ({thesis.advisor_name || "GVHD"}).
      </p>
    )}
    {!thesis.actions.includes("progress:submit") && !thesis.actions.includes("progress:review") && !thesis.actions.includes("progress:comment") && !thesis.actions.includes("milestone:manage") && (
      <div className="card"><div className="card-body">
        <p className="text-body-sm text-muted">
          Bạn đang xem tiến độ với quyền theo dõi. Thao tác nộp báo cáo do sinh viên trong nhóm thực hiện; xác nhận hoặc yêu cầu sửa do GVHD chính ({thesis.advisor_name || "GVHD"}) thực hiện; người góp ý chéo chỉ nhận xét; quản lý mốc do người điều phối đợt phụ trách.
        </p>
      </div></div>
    )}
    {thesis.actions.includes("progress:submit") && active && <form className="card" onSubmit={async event => {
      event.preventDefault();
      const form = event.currentTarget;
      const sent = await run(() => submitProgress(thesis.id, userId, {
        milestone_id: selected, summary, reported_ratio: ratio === "" ? 0 : Number(ratio), document_version_id: null,
      }, evidenceFile), "Đã gửi báo cáo tiến độ cho GVHD.");
      if (sent) {
        setSummary(""); setMilestoneId(""); setEvidenceFile(null); setEvidenceNotice(""); form.reset();
      }
    }}><div className="card-body core-form">
      <h3>Nộp báo cáo tiến độ</h3>
      <p className="text-body-sm text-muted">Có thể nộp trễ lần đầu khi mốc còn mở. Trước hạn, bạn có thể tự nộp bản sửa nếu GVHD chưa phản hồi; bản cũ vẫn lưu. Sau hạn hoặc khi mốc đóng, chỉ nộp bản mới khi GVHD yêu cầu sửa.</p>
      <div className="input-group"><label htmlFor="report-milestone">Mốc báo cáo</label><select className="input" id="report-milestone" value={selected} onChange={event => setMilestoneId(event.target.value)} required disabled={busy}>
        <option value="">Chọn mốc có thể nộp</option>{available.map(item => <option key={item.id} value={item.id}>{item.title} · v{item.version_no}{latest.has(item.id) ? " · nộp phiên bản mới" : ""}</option>)}
      </select></div>
      <div className="input-group"><label htmlFor="report-summary">Kết quả, khó khăn và kế hoạch</label><textarea className="input" id="report-summary" value={summary} onChange={event => setSummary(event.target.value)} required maxLength={10000} disabled={busy} /></div>
      <div className="progress-form-row">
        <div className="input-group"><label htmlFor="report-ratio">Tiến độ tự báo cáo (%)</label><input className="input" id="report-ratio" type="number" min={0} max={100} step="0.01" placeholder="0" value={ratio} onChange={event => setRatio(event.target.value)} required disabled={busy} /></div>
        <div className="input-group"><label htmlFor="report-evidence-file">Minh chứng tiến độ từ máy (không bắt buộc; PDF, DOCX, TXT; tối đa 10 MB)</label>
          <input className="input" id="report-evidence-file" type="file" accept=".pdf,.docx,.txt" disabled={busy}
            onChange={event => setEvidenceFile(event.target.files?.[0] || null)} />
          {evidenceFile && <div className="flex items-center gap-2" style={{margin: "var(--space-1) 0"}}>
            <span className="text-body-sm font-semibold">{evidenceFile.name} ({(evidenceFile.size / 1024).toFixed(1)} KB)</span>
            <button type="button" className="btn btn-ghost btn-sm" title="Hủy chọn tệp" onClick={() => {
              setEvidenceFile(null);
              const el = document.getElementById("report-evidence-file") as HTMLInputElement | null;
              if (el) el.value = "";
            }}><X size={14} aria-hidden="true" style={{marginRight: 4}} /> Xóa tệp đã chọn</button>
          </div>}
          <p className="text-caption">Có thể để trống. Tệp gắn trực tiếp với báo cáo ở dưới. Khi còn cách ly, GVHD có thể yêu cầu nộp lại nhưng chưa thể tải hoặc xác nhận.</p>
          {evidenceFile && evidenceFile.size > 10*1024*1024 && <p role="alert">Tệp vượt quá 10 MB.</p>}
        </div>
      </div>
      {evidenceNotice && <p role="status" className="alert alert-info">{evidenceNotice}</p>}
      <button className="btn btn-primary" disabled={busy || !selected || !summary.trim() || !!(evidenceFile && evidenceFile.size > 10*1024*1024)}>Gửi báo cáo</button>
    </div></form>}
    {thesis.actions.includes("progress:view") ? <>
    <h2>Báo cáo tiến độ và nhận xét</h2>
    {Array.from(latest.values()).sort((a, b) => Date.parse(b.submitted_at) - Date.parse(a.submitted_at)).map(report => {
      const previousVersions = reports.filter(item => item.milestone_id === report.milestone_id && item.id !== report.id)
        .sort((a, b) => b.version_no - a.version_no);
      return <article className="card progress-report" key={report.milestone_id}><div className="card-body stack">
        <div className="flex justify-between gap-3"><h3>{milestones.find(item => item.id === report.milestone_id)?.title || "Báo cáo"}</h3><Status value={report.state} /></div>
        <p className="text-body-sm font-semibold">Bản mới nhất · lần nộp {report.version_no}</p>
        {renderReportDetails(report, true)}
        {previousVersions.length > 0 && <details className="progress-report-history">
          <summary>Lịch sử cập nhật ({previousVersions.length} bản trước)</summary>
          <p className="text-body-sm text-muted">Các bản trước được giữ để đối chiếu nội dung và nhận xét. GVHD xử lý bản mới nhất ở phía trên.</p>
          <div className="progress-report-history__list">{previousVersions.map(previous => <details className="progress-report-history__version" key={previous.id}>
            <summary><span>Lần nộp {previous.version_no} · {formatDate(previous.submitted_at)} · {previous.submitted_by_name}</span>
              {previous.late && <strong className="late-badge" aria-label="Nộp trễ">Nộp trễ</strong>}
              {previous.reviews.length > 0 && <span className="badge">{previous.reviews.length} nhận xét</span>}
            </summary>
            <div className="stack progress-report-history__content">{renderReportDetails(previous, false)}</div>
          </details>)}</div>
        </details>}
      </div></article>;
    })}
    {reports.length === 0 && <EmptyState title="Chưa có báo cáo tiến độ." />}
    </> : <p className="alert alert-info">Bạn quản lý mốc chung. Nội dung báo cáo, minh chứng và nhận xét riêng chỉ nhóm SV và GVHD được xem.</p>}
  </div>;
}
