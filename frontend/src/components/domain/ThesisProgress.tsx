import { useState } from "react";
import type { AuditEvent, Milestone, ProgressReport, Thesis, ThesisDocument } from "../../api";
import { request } from "../../api";
import type { CoreRun } from "./ThesisDocuments";
import { formatDate, ReviewForm, Reviews, Status } from "./CoreForms";

function ExtendForm({thesis, milestone, userId, busy, run}: {
  thesis: Thesis; milestone: Milestone; userId: string; busy: boolean; run: CoreRun;
}) {
  const [dueAt, setDueAt] = useState("");
  const [reason, setReason] = useState("");
  return <details><summary>Gia hạn cho toàn đợt</summary><form className="core-form" onSubmit={async event => {
    event.preventDefault();
    if (await run(() => request(`/theses/${thesis.id}/milestones/${milestone.id}/extend`, userId, {
      method: "POST", headers: {"If-Match": String(milestone.row_version)},
      body: JSON.stringify({due_at: new Date(dueAt + "+07:00").toISOString(), reason}),
    }), "Đã gia hạn mốc cho toàn đợt; báo cáo cũ giữ nguyên nhãn đúng/trễ.")) {setDueAt(""); setReason("");}
  }}>
    <label htmlFor={`extend-due-${milestone.id}`}>Hạn mới (giờ Việt Nam)</label>
    <input className="input" id={`extend-due-${milestone.id}`} type="datetime-local" value={dueAt}
      onChange={event => setDueAt(event.target.value)} required disabled={busy} />
    <label htmlFor={`extend-reason-${milestone.id}`}>Lý do gia hạn</label>
    <textarea className="input" id={`extend-reason-${milestone.id}`} value={reason}
      onChange={event => setReason(event.target.value)} required minLength={3} maxLength={2000} disabled={busy} />
    <button className="btn btn-secondary" disabled={busy || !dueAt || reason.trim().length < 3}>Lưu gia hạn</button>
  </form></details>;
}

export default function ThesisProgress({thesis, milestones, reports, docs, milestoneHistory, userId, busy, run}: {
  thesis: Thesis; milestones: Milestone[]; reports: ProgressReport[]; docs: ThesisDocument[];
  milestoneHistory: AuditEvent[]; userId: string; busy: boolean; run: CoreRun;
}) {
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [expectedRatio, setExpectedRatio] = useState("");
  const [milestoneId, setMilestoneId] = useState("");
  const [summary, setSummary] = useState("");
  const [ratio, setRatio] = useState(0);
  const [evidence, setEvidence] = useState("");
  const active = ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state);
  const latest = new Map<string, ProgressReport>();
  for (const report of reports) {
    if ((latest.get(report.milestone_id)?.version_no || 0) < report.version_no) latest.set(report.milestone_id, report);
  }
  const available = milestones.filter(item => item.state === "OPEN" && (!latest.has(item.id) || latest.get(item.id)?.state === "REVISION_REQUIRED"));
  const selected = available.some(item => item.id === milestoneId) ? milestoneId : "";
  const cleanDocs = docs.flatMap(doc => doc.versions.filter(version => version.scan_state === "CLEAN")
    .map(version => ({doc, version})));
  const milestoneAudit = milestoneHistory;
  const milestoneAction: Record<string, string> = {MILESTONE_OPENED: "Mở mốc", MILESTONE_EXTENDED: "Gia hạn mốc", MILESTONE_CLOSED: "Đóng mốc"};
  return <div className="stack">
    {thesis.actions.includes("milestone:manage") && active && <form className="card" onSubmit={async event => {
      event.preventDefault();
      if (await run(() => request(`/theses/${thesis.id}/milestones`, userId, {method: "POST", body: JSON.stringify({
        code, title, due_at: new Date(dueAt+"+07:00").toISOString(), expected_ratio: expectedRatio === "" ? null : Number(expectedRatio),
      })}), "Đã mở mốc cho toàn đợt.")) {setCode(""); setTitle("");}
    }}><div className="card-body core-form">
      <h3>Mở mốc theo kế hoạch đợt</h3>
      <p className="text-body-sm text-muted">Áp dụng cho mọi khóa luận trong {thesis.round_label}. Mốc đã mở giữ nguyên; đóng trước khi ban hành phiên bản mới cùng mã.</p>
      <div className="core-fields">
        <div className="input-group"><label htmlFor="milestone-code">Mã mốc</label><input className="input" id="milestone-code" value={code} onChange={event => setCode(event.target.value.toUpperCase())} pattern="[A-Z0-9_-]{1,50}" maxLength={50} placeholder="NOI_BO_1" required disabled={busy} /></div>
        <div className="input-group"><label htmlFor="milestone-title">Tên mốc</label><input className="input" id="milestone-title" value={title} onChange={event => setTitle(event.target.value)} required maxLength={255} disabled={busy} /></div>
        <div className="input-group"><label htmlFor="milestone-due">Hạn nộp (giờ Việt Nam)</label><input className="input" id="milestone-due" type="datetime-local" value={dueAt} onChange={event => setDueAt(event.target.value)} required disabled={busy} /></div>
        <div className="input-group"><label htmlFor="milestone-ratio">Tiến độ dự kiến (%)</label><input className="input" id="milestone-ratio" type="number" min={0} max={100} step="0.01" value={expectedRatio} onChange={event => setExpectedRatio(event.target.value)} disabled={busy} /></div>
      </div>
      <button className="btn btn-primary" disabled={busy || !title.trim() || !code || !dueAt}>Mở mốc cho đợt</button>
    </div></form>}
    {milestones.map(milestone => <article className="card" key={milestone.id}><div className="card-body stack">
      <div className="flex justify-between gap-3"><h3>{milestone.title} · v{milestone.version_no}</h3><Status value={milestone.state} /></div>
      <p className="text-muted">{milestone.code} · Hạn: {formatDate(milestone.due_at)}{milestone.expected_ratio !== null ? ` · Dự kiến ${milestone.expected_ratio}%` : ""}</p>
      {thesis.actions.includes("milestone:manage") && milestone.state === "OPEN" && milestone.due_at && active &&
        <ExtendForm thesis={thesis} milestone={milestone} userId={userId} busy={busy} run={run} />}
      {thesis.actions.includes("milestone:manage") && milestone.state === "OPEN" && active && <details><summary>Đóng mốc cho toàn đợt</summary>
        <ReviewForm disabled={busy} choices={[{value: "CLOSE", label: "Đóng mốc, ngừng nhận báo cáo mới"}]} onSubmit={(_, reason) => run(() => request(`/theses/${thesis.id}/milestones/${milestone.id}/close`, userId, {
          method: "POST", headers: {"If-Match": String(milestone.row_version)}, body: JSON.stringify({reason}),
        }), "Đã đóng mốc cho đợt.")} />
      </details>}
    </div></article>)}
    {milestones.length === 0 && <div className="card"><div className="card-body">
      <h3>Chưa có mốc tiến độ cho đợt {thesis.round_label}</h3>
      <p className="text-muted">
        {thesis.actions.includes("milestone:manage")
          ? "Bạn được giao quyền điều phối đợt (KLTN_COORDINATOR): hãy sử dụng biểu mẫu phía trên để mở mốc đầu tiên theo kế hoạch đợt (kèm hạn nộp và tỷ lệ hoàn thành dự kiến)."
          : thesis.actions.includes("progress:submit")
          ? "Đợt này chưa có mốc tiến độ nào được mở. Người được giao điều phối đợt (KLTN_COORDINATOR) cần tạo và mở mốc theo kế hoạch. Sau khi mốc được mở, sinh viên trong nhóm mới có thể nộp báo cáo."
          : `Đợt này chưa có mốc tiến độ nào được mở. Người điều phối đợt cần thiết lập mốc tiến độ để sinh viên nộp báo cáo và GVHD chính (${thesis.advisor_name || "GVHD"}) theo dõi, đánh giá.`}
      </p>
    </div></div>}
    <div className="card"><div className="card-body stack"><h2>Lịch sử mốc của đợt</h2>
      <p className="text-body-sm text-muted">Người thực hiện, thời điểm và lý do mở, gia hạn hoặc đóng mốc. Gia hạn luôn áp dụng cho toàn đợt, không riêng từng đề tài hay sinh viên.</p>
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
          Tất cả các mốc hiện tại đã đóng hoặc nhóm bạn đã được xác nhận tiến độ. Nếu cần nộp bổ sung hoặc gia hạn, liên hệ người điều phối đợt ({thesis.round_label}) để gia hạn hoặc mở mốc tiếp theo.
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
      if (await run(() => request(`/theses/${thesis.id}/progress-reports`, userId, {method: "POST", body: JSON.stringify({
        milestone_id: selected, summary, reported_ratio: ratio, document_version_id: evidence || null,
      })}), "Đã gửi báo cáo tiến độ cho GVHD.")) {setSummary(""); setMilestoneId(""); setEvidence("");}
    }}><div className="card-body core-form">
      <h3>Nộp báo cáo tiến độ</h3>
      <p className="text-body-sm text-muted">Nêu kết quả đã làm, phần còn thiếu và kế hoạch tiếp theo. Có thể nộp trễ khi mốc còn mở; hệ thống ghi rõ thời điểm.</p>
      <div className="input-group"><label htmlFor="report-milestone">Mốc báo cáo</label><select className="input" id="report-milestone" value={selected} onChange={event => setMilestoneId(event.target.value)} required disabled={busy}>
        <option value="">Chọn mốc đang mở / được yêu cầu sửa</option>{available.map(item => <option key={item.id} value={item.id}>{item.title} · v{item.version_no}</option>)}
      </select></div>
      <div className="input-group"><label htmlFor="report-summary">Kết quả, khó khăn và kế hoạch</label><textarea className="input" id="report-summary" value={summary} onChange={event => setSummary(event.target.value)} required maxLength={10000} disabled={busy} /></div>
      <div className="input-group"><label htmlFor="report-ratio">Tiến độ tự báo cáo (%)</label><input className="input" id="report-ratio" type="number" min={0} max={100} step="0.01" value={ratio} onChange={event => setRatio(Number(event.target.value))} required disabled={busy} /></div>
      <div className="input-group"><label htmlFor="report-evidence">Tài liệu minh chứng (không bắt buộc)</label><select className="input" id="report-evidence" value={evidence} onChange={event => setEvidence(event.target.value)} disabled={busy}>
        <option value="">Không đính kèm</option>{cleanDocs.map(({doc, version}) => <option key={version.id} value={version.id}>{doc.title} · v{version.version_no}</option>)}
      </select>
      {cleanDocs.length === 0 && <p className="text-caption">Chưa có tệp nào được quét an toàn. Tệp mới ở trạng thái “Đang cách ly – chưa quét” nên chưa dùng làm minh chứng được; có thể nộp báo cáo không kèm tệp.</p>}</div>
      <button className="btn btn-primary" disabled={busy || !selected || !summary.trim()}>Gửi báo cáo</button>
    </div></form>}
    <h2>Lịch sử báo cáo và nhận xét</h2>
    {reports.map(report => <article className="card" key={report.id}><div className="card-body stack">
      <div className="flex justify-between gap-3"><h3>{milestones.find(item => item.id === report.milestone_id)?.title || "Báo cáo"} · lần nộp {report.version_no}</h3><Status value={report.state} /></div>
      <p className="text-body-sm text-muted">{report.submitted_by_name} · {formatDate(report.submitted_at)} · Tự báo cáo {report.reported_ratio}% {report.late && <strong className="late-badge" aria-label="Nộp trễ">! Nộp trễ</strong>}</p>
      <p className="text-body-sm text-muted">Hạn áp dụng lúc nộp: {formatDate(report.due_at_at_submission)}</p>
      <p className="core-prewrap">{report.summary}</p>
      {report.evidence_document_version_id && <p className="text-body-sm">Có tài liệu minh chứng trong tab Tài liệu.</p>}
      <Reviews items={report.reviews} />
      {active && report.state === "SUBMITTED" && latest.get(report.milestone_id)?.id === report.id &&
        ((thesis.actions.includes("progress:review") || thesis.actions.includes("progress:comment"))) &&
        <ReviewForm disabled={busy} choices={thesis.actions.includes("progress:review") ? [{value: "CONFIRM", label: "Xác nhận tiến độ"}, {value: "REVISION_REQUIRED", label: "Yêu cầu sửa và nộp lại"}] : [{value: "COMMENT_ONLY", label: "Góp ý chéo (không chốt tiến độ)"}]} onSubmit={(decision, comment) => run(() => request(`/theses/${thesis.id}/progress-reports/${report.id}/review`, userId, {
          method: "POST", headers: {"If-Match": String(report.row_version)}, body: JSON.stringify({decision, comment}),
        }), "Đã lưu nhận xét tiến độ.")} />}
    </div></article>)}
    {reports.length === 0 && <p className="text-muted">Chưa có báo cáo tiến độ.</p>}
  </div>;
}
