import WorkflowSteps from "./WorkflowSteps";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { AuditEvent, DocumentDeadline, Lecturer, ProgressReport, Proposal, Thesis, ThesisDocument } from "../../api";
import { Status, formatDate } from "./CoreForms";
import DocumentDeadlines from "./DocumentDeadlines";
import RegistrationSubmission from "./RegistrationSubmission";
import ThesisDocuments, { type CoreRun } from "./ThesisDocuments";
import ThesisProposal from "./ThesisProposal";

export type SubmissionKind = "REGISTRATION" | "PLAN" | "PROPOSAL" | "REPORT" | "SUPPORTING";
export default function ThesisSubmissions({thesis, proposal, docs, deadlines, history, lecturers, reports, userId, busy, run, kind}: {
  thesis: Thesis; proposal: Proposal | null; docs: ThesisDocument[]; deadlines: DocumentDeadline[];
  history: AuditEvent[]; lecturers: Lecturer[]; reports: ProgressReport[]; userId: string;
  busy: boolean; run: CoreRun; kind: string;
}) {
  const [pendingOnly, setPendingOnly] = useState(false);
  const canProcess = thesis.actions.some(action => ["document:review","proposal:review","proposal:finalize","proposal:dean_confirm"].includes(action));
  const managesDeadlines = thesis.actions.includes("milestone:manage");
  const canReadDocuments = thesis.actions.includes("document:view");
  const choices = [
    ...(thesis.registration_id && thesis.actions.some(action => ["document:submit","document:review","proposal:finalize","proposal:dean_confirm"].includes(action)) ? [{kind:"REGISTRATION", label:"Đơn đăng ký", code:"Mẫu 1a / 1b", description:"Hồ sơ trước khi GV tiếp nhận", state:null, pending:false}] : []),
    ...((canReadDocuments || managesDeadlines) ? [{kind:"PLAN", label:"Kế hoạch thực hiện", code:"Mẫu 2", description:"GVHD nhận xét và tiếp nhận", state:docs.find(doc => doc.document_type === "PLAN")?.versions[0]?.state || "Chưa nộp", pending:thesis.actions.includes("document:review") && docs.some(doc => doc.document_type === "PLAN" && doc.versions[0]?.state === "SUBMITTED")}] : []),
    ...((proposal || managesDeadlines) ? [{kind:"PROPOSAL", label:"Đề cương", code:"Mẫu 3", description:"GVHD xác nhận · TBM chốt", state:proposal?.state, pending:!!proposal && ((thesis.actions.includes("proposal:review") && ["SUBMITTED","UNDER_REVIEW"].includes(proposal.state)) || (thesis.actions.includes("proposal:finalize") && proposal.state === "ADVISOR_CONFIRMED") || (thesis.actions.includes("proposal:dean_confirm") && proposal.state === "DEPARTMENT_FINALIZED"))}] : []),
    ...((canReadDocuments || managesDeadlines) ? [
      {kind:"REPORT", label:"Cuốn báo cáo KLTN", code:"Báo cáo trước bảo vệ", description:"Bản báo cáo hoàn chỉnh của đề tài", state:docs.find(doc => doc.document_type === "REPORT")?.versions[0]?.state || "Chưa nộp", pending:thesis.actions.includes("document:review") && docs.some(doc => doc.document_type === "REPORT" && doc.versions[0]?.state === "SUBMITTED")},
      {kind:"SUPPORTING", label:"Tài liệu hỗ trợ", code:"Minh chứng", description:"Minh chứng công bố khoa học và tệp bổ sung", state:null, pending:thesis.actions.includes("document:review") && docs.some(doc => doc.document_type === "SUPPORTING" && doc.versions[0]?.state === "SUBMITTED")},
    ] : []),
  ];
  const effectiveDeadlines = deadlines.map(item => item.document_type === "REPORT" && thesis.extension_until_at && Date.parse(thesis.extension_until_at) > Date.parse(item.due_at)
    ? {...item, due_at:thesis.extension_until_at, state:Date.now() <= Date.parse(thesis.extension_until_at) ? "OPEN" : "CLOSED"} as DocumentDeadline : item);
  const displayed = pendingOnly ? choices.filter(item => item.pending) : choices;
  const filter = canProcess && <label className="submission-filter"><input type="checkbox" checked={pendingOnly} onChange={event => setPendingOnly(event.target.checked)}/>Chờ tôi xử lý ({choices.filter(item => item.pending).length} loại hồ sơ)</label>;
  const current = displayed.find(item => item.kind === kind) || displayed.find(item => item.kind === "PLAN") || displayed[0];
  if (!current) return <section className="stack submission-workspace" aria-label="Hồ sơ nộp và xét duyệt">{filter}<div className="card"><div className="card-body stack"><h2>Không có hồ sơ đang chờ bạn xử lý</h2><p>Các bản đã tiếp nhận và lịch sử vẫn được giữ.</p><button className="btn btn-secondary" onClick={() => setPendingOnly(false)}>Xem tất cả hồ sơ</button></div></div></section>;
  const selected = current.kind as SubmissionKind;
  return <section className="stack submission-workspace" aria-label="Hồ sơ nộp và xét duyệt">
    {filter}
    <div className="submission-kinds" aria-label="Chọn loại hồ sơ">
      {displayed.map(item => <Link key={item.kind} aria-current={selected === item.kind ? "page" : undefined}
        className={"submission-kind" + (selected === item.kind ? " submission-kind--active" : "")}
        to={"/theses/" + thesis.id + "?section=submissions&kind=" + item.kind}>
        <span className="section-eyebrow">{item.code}</span><strong>{item.label}</strong><small>{item.description}</small>
        {item.state && <Status value={item.state} />}
      </Link>)}
    </div>
    <div className="submission-panel stack" key={selected}>{["PLAN","PROPOSAL","REPORT"].includes(selected) && <WorkflowSteps steps={selected==="PROPOSAL"?["SV nộp đề cương","GVHD xác nhận","TBM chốt","Hoàn tất hồ sơ"]:["SV nộp tệp","GVHD xem / phản hồi","Tiếp nhận phiên bản"]}
 current={selected==="PROPOSAL"?(["DEPARTMENT_FINALIZED","DEAN_CONFIRMED"].includes(proposal?.state||"")?3:proposal?.state==="ADVISOR_CONFIRMED"?2:["SUBMITTED","UNDER_REVIEW"].includes(proposal?.state||"")?1:0):docs.some(d=>d.document_type===selected && ["ACCEPTED","FINAL"].includes(d.versions[0]?.state||""))?2:docs.some(d=>d.document_type===selected && d.versions.length)?1:0}/> }
      {selected === "REGISTRATION" && (thesis.registration_id
        ? <RegistrationSubmission registrationId={thesis.registration_id} userId={userId} />
        : <p className="alert alert-info">Hồ sơ này chưa có liên kết đơn đăng ký. <Link to="/registrations">Xem hồ sơ đăng ký</Link></p>)}
      {selected === "PROPOSAL" && <>
        <DocumentDeadlines thesis={thesis} deadlines={deadlines} history={history} userId={userId} busy={busy} run={run} kinds={["PROPOSAL"]} />
        {proposal && <ThesisProposal thesis={thesis} proposal={proposal} deadline={deadlines.find(item => item.document_type === "PROPOSAL")} lecturers={lecturers} userId={userId} busy={busy} run={run} />}
      </>}
      {["PLAN","REPORT","SUPPORTING"].includes(selected) && <>
        <DocumentDeadlines thesis={thesis} deadlines={deadlines} history={history} userId={userId} busy={busy} run={run} kinds={[selected as "PLAN" | "REPORT" | "SUPPORTING"]} />
        {selected === "REPORT" && thesis.extension_until_at && <p className="alert alert-info">Hạn hoàn thành riêng đã được gia hạn đến <strong>{formatDate(thesis.extension_until_at)}</strong>. Hạn chung của đợt vẫn giữ nguyên; bản đã được tiếp nhận chỉ nộp lại khi GVHD yêu cầu sửa.</p>}
        {canReadDocuments && <ThesisDocuments thesis={thesis} docs={docs} deadlines={effectiveDeadlines} reports={reports} userId={userId} busy={busy} run={run} kind={selected as "PLAN" | "REPORT" | "SUPPORTING"} pendingOnly={pendingOnly} />}
      </>}
    </div>
    <p className="submission-help text-body-sm text-muted">Cần mẫu trắng hoặc tài liệu Khoa công bố? <Link to={"/forms?round_id=" + thesis.round_id}>Mở kho biểu mẫu & tài liệu Khoa</Link>. Báo cáo định kỳ nộp tại <Link to={"/theses/" + thesis.id + "?section=progress"}>Báo cáo tiến độ</Link>.</p>
  </section>;
}
