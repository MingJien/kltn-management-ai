import { useState } from "react";
import type { Milestone, ProgressReport, Thesis, ThesisDocument } from "../../api";
import { request } from "../../api";
import type { CoreRun } from "./ThesisDocuments";
import { formatDate, ReviewForm, Reviews, Status } from "./CoreForms";

export default function ThesisProgress({thesis, milestones, reports, docs, userId, busy, run}: {
  thesis: Thesis; milestones: Milestone[]; reports: ProgressReport[]; docs: ThesisDocument[];
  userId: string; busy: boolean; run: CoreRun;
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
      {thesis.actions.includes("milestone:manage") && milestone.state === "OPEN" && active && <details><summary>Đóng mốc cho toàn đợt</summary>
        <ReviewForm disabled={busy} choices={[{value: "CLOSE", label: "Đóng mốc, ngừng nhận báo cáo mới"}]} onSubmit={(_, reason) => run(() => request(`/theses/${thesis.id}/milestones/${milestone.id}/close`, userId, {
          method: "POST", headers: {"If-Match": String(milestone.row_version)}, body: JSON.stringify({reason}),
        }), "Đã đóng mốc cho đợt.")} />
      </details>}
    </div></article>)}
    {milestones.length === 0 && <p className="text-muted">Chưa có mốc. Người được giao quản lý đợt cần nhập mốc theo kế hoạch đã xác nhận.</p>}
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
        <option value="">Không đính kèm</option>{docs.flatMap(doc => doc.versions.filter(version => !["INFECTED", "FAILED"].includes(version.scan_state)).map(version => <option key={version.id} value={version.id}>{doc.title} · v{version.version_no}</option>))}
      </select></div>
      <button className="btn btn-primary" disabled={busy || !selected || !summary.trim()}>Gửi báo cáo</button>
    </div></form>}
    <h2>Lịch sử báo cáo và nhận xét</h2>
    {reports.map(report => <article className="card" key={report.id}><div className="card-body stack">
      <div className="flex justify-between gap-3"><h3>{milestones.find(item => item.id === report.milestone_id)?.title || "Báo cáo"} · lần nộp {report.version_no}</h3><Status value={report.state} /></div>
      <p className="text-body-sm text-muted">{report.submitted_by_name} · {formatDate(report.submitted_at)} · Tự báo cáo {report.reported_ratio}%{report.late ? " · Nộp trễ" : ""}</p>
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
