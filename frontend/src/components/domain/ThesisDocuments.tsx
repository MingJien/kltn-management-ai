import EmptyState from "../ui/EmptyState";
import { useState } from "react";
import { X } from "lucide-react";
import type { DocumentDeadline, ProgressReport, Thesis, ThesisDocument } from "../../api";
import { downloadDocument, downloadPlanTemplate, request, uploadDocument } from "../../api";
import { formatDate, ReviewForm, Reviews, Status } from "./CoreForms";
import PrintHistory from "./PrintHistory";
import FileReviewButton from "./FileReviewButton";
import VersionTimeline from "./VersionTimeline";

const documentPresets: Record<string, string> = {
  PLAN: "Kế hoạch thực hiện (Mẫu 2)",
  SUPPORTING_PUBLICATION: "Minh chứng công bố khoa học để xét điểm thưởng",
  SUPPORTING_REFERENCES: "Tài liệu tham khảo",
  SUPPORTING_SURVEY: "Phiếu khảo sát / kết quả khảo sát",
  SUPPORTING_DESIGN: "Đặc tả yêu cầu / tài liệu thiết kế",
  SUPPORTING_GUIDE: "Hướng dẫn sử dụng sản phẩm",
  SUPPORTING: "Tài liệu hỗ trợ khác",
};

export type CoreRun = (action: () => Promise<unknown>, message: string) => Promise<boolean>;

export function scanLabel(state: string) {
  if (state === "CLEAN") return "Đã quét an toàn";
  if (state === "QUARANTINED") return "Đang cách ly – chưa quét";
  if (state === "INFECTED") return "Phát hiện mã độc – không sử dụng";
  return "Quét lỗi – không sử dụng";
}

function DocumentCard({doc, thesis, deadline, progressEvidenceIds, userId, busy, run}: {
  doc: ThesisDocument; thesis: Thesis; deadline?: DocumentDeadline; progressEvidenceIds: Set<string>; userId: string; busy: boolean; run: CoreRun;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [withdrawReason, setWithdrawReason] = useState("");
  const [downloadError, setDownloadError] = useState("");
  const [printNotice, setPrintNotice] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [printRefresh, setPrintRefresh] = useState(0);
  const latest = doc.versions[0];
  const officialFile = ["PLAN", "REPORT"].includes(doc.document_type);
  const validFileType = !file || (officialFile ? /\.(pdf|docx)$/i : /\.(pdf|docx|txt)$/i).test(file.name);
  const beforeDue = deadline?.state === "OPEN" && Date.now() <= new Date(deadline.due_at).getTime();
  const canSubmit = doc.document_type !== "PROPOSAL" && thesis.actions.includes("document:submit") && ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state) && !!deadline && (
    latest?.state === "REVISION_REQUESTED" ||
    (deadline.state === "OPEN" && !latest) ||
    (beforeDue && latest?.state === "SUBMITTED" && latest.reviews.length === 0));
  const canWithdraw = thesis.actions.includes("document:submit") && ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state) && doc.document_type !== "PROPOSAL" && doc.versions.every(version =>
    ["SUBMITTED","SUPERSEDED"].includes(version.state) && version.reviews.length === 0 && !progressEvidenceIds.has(version.id));
  const latestAccepted = doc.versions.filter(version => ["ACCEPTED", "FINAL"].includes(version.state))
    .sort((a, b) => b.version_no - a.version_no)[0];
  return <article className="card" id={`document-${doc.id}`}><div className="card-body stack">
    <p className="text-caption text-muted">Trước hạn được nộp bản cập nhật khi GVHD chưa phản hồi; sau hạn chỉ nộp lại khi GVHD yêu cầu sửa.</p>
    {canWithdraw && <details><summary>Rút hồ sơ tài liệu nộp nhầm</summary><form className="core-form" onSubmit={async event => {
      event.preventDefault();
      if (await run(() => request(`/theses/${thesis.id}/documents/${doc.id}/withdraw`, userId, {
        method: "POST", headers: {"If-Match": String(doc.row_version)}, body: JSON.stringify({reason: withdrawReason.trim()}),
      }), "Đã rút hồ sơ nộp nhầm khỏi danh sách; lịch sử vẫn được lưu.")) setWithdrawReason("");
    }}>
      <p className="text-body-sm text-muted">Chỉ rút được trước khi GVHD nhận xét và khi tệp không dùng làm minh chứng tiến độ. Hồ sơ đã gửi vẫn lưu trong lịch sử để đối chiếu.</p>
      <div className="input-group"><label htmlFor={`withdraw-reason-${doc.id}`}>Lý do rút</label>
        <textarea className="input" id={`withdraw-reason-${doc.id}`} value={withdrawReason}
          onChange={event => setWithdrawReason(event.target.value)} required minLength={3} maxLength={2000} disabled={busy} />
      </div>
      <button className="btn btn-destructive" disabled={busy || withdrawReason.trim().length < 3}>Rút hồ sơ này</button>
    </form></details>}
    {latest?.state === "REVISION_REQUESTED" && thesis.actions.includes("document:submit") && <div className="alert alert-info">
      <strong>Hồ sơ yêu cầu cập nhật bản v{latest.version_no}.</strong> Chọn tệp sửa ngay trong hồ sơ này để tạo bản v{latest.version_no + 1}; bản cũ và nhận xét vẫn được giữ. Không cần tạo hồ sơ tài liệu khác.
    </div>}
    {canSubmit && doc.versions[0]?.state !== "FINAL" && <details className="submission-update" open={!latest || latest.state === "REVISION_REQUESTED"}><summary>{latest?.state === "REVISION_REQUESTED" ? "Nộp bản sửa theo yêu cầu cập nhật" : latest ? "Nộp bản cập nhật mới" : "Nộp phiên bản đầu tiên"}</summary><form className="core-form" aria-labelledby={`document-upload-heading-${doc.id}`} onSubmit={async event => {
      event.preventDefault();
      const form = event.currentTarget;
      if (file && validFileType && await run(() => uploadDocument(thesis.id, doc, userId, file), "Đã lưu phiên bản mới.")) {
        setFile(null);
        form.reset();
      }
    }}>
      <h4 id={`document-upload-heading-${doc.id}`}>{latest?.state === "REVISION_REQUESTED" ? `Nộp bản sửa v${latest.version_no + 1} theo yêu cầu cập nhật` : latest ? `Cập nhật bằng phiên bản v${latest.version_no + 1}` : "Nộp phiên bản đầu tiên"}</h4>
      <label htmlFor={`file-${doc.id}`}>Nộp phiên bản mới ({officialFile ? "PDF, DOCX" : "PDF, DOCX, TXT"}; tối đa 10 MB)</label>
      <input className="input" id={`file-${doc.id}`} type="file" accept={officialFile ? ".pdf,.docx" : ".pdf,.docx,.txt"} required disabled={busy}
        onChange={event => setFile(event.target.files?.[0] || null)} />
      {file && <div className="flex items-center gap-2" style={{margin: "var(--space-1) 0"}}>
        <span className="text-body-sm font-semibold">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
        <button type="button" className="btn btn-ghost btn-sm" title="Hủy chọn tệp" onClick={() => {
          setFile(null);
          const el = document.getElementById(`file-${doc.id}`) as HTMLInputElement | null;
          if (el) el.value = "";
        }}><X size={14} aria-hidden="true" style={{marginRight: 4}} /> Xóa tệp đã chọn</button>
      </div>}
      {!validFileType && <p role="alert">{officialFile ? "Kế hoạch Mẫu 2 và Cuốn báo cáo KLTN chỉ nhận PDF hoặc DOCX để xuất bản có footer." : "Chỉ nhận PDF, DOCX hoặc TXT."}</p>}
      <button className="btn btn-primary" disabled={busy || !file || !validFileType || file.size > 10*1024*1024}>{busy ? "Đang tải lên và quét an toàn…" : "Nộp tài liệu"}</button>
      {file && file.size > 10*1024*1024 && <p role="alert">Tệp vượt quá 10 MB.</p>}
    </form></details>}
    {downloadError && <div role="alert" className="alert alert-danger">{downloadError}</div>}
    {printNotice && <p role="status" className="alert alert-success">{printNotice}</p>}
    {doc.versions.length === 0 && <p className="text-muted">Chưa có tệp; hãy nộp phiên bản đầu tiên.</p>}
    {<VersionTimeline versions={doc.versions} render={(version, index) => {
      const clean = version.scan_state === "CLEAN";
      const suffix = version.file_name.slice(version.file_name.lastIndexOf(".")).toLowerCase();
      const canPrint = ["PLAN", "REPORT"].includes(doc.document_type) && version.id === latestAccepted?.id &&
        clean && [".pdf", ".docx"].includes(suffix);
      return <section className="core-version stack" key={version.id}>
        <div className="flex justify-between gap-3"><strong>Phiên bản {version.version_no} · {version.file_name}</strong><Status value={version.state} /></div>
        <p className="text-body-sm text-muted">{version.submitted_by_name} · {formatDate(version.submitted_at)} · {(version.byte_size/1024).toFixed(1)} KB</p>
        {version.late && <strong className="late-badge" aria-label="Nộp trễ">Nộp trễ</strong>}
        {version.due_at_at_submission && <p className="text-caption">Hạn áp dụng lúc nộp: {formatDate(version.due_at_at_submission)}</p>}
        <p className={`text-body-sm ${clean ? "text-muted" : "alert alert-warning"}`}>{scanLabel(version.scan_state)}{!clean ? " — bản này chưa thể tải xuống hoặc dùng để duyệt." : ""}</p>
        {["QUARANTINED", "FAILED"].includes(version.scan_state) && <button type="button" className="btn btn-secondary btn-sm" disabled={busy}
          onClick={() => run(() => request(`/theses/${thesis.id}/documents/${doc.id}/versions/${version.id}/scan`, userId, {method:"POST"}),
            "Đã quét lại tệp bằng ClamAV; xem trạng thái mới của phiên bản.")}>Quét lại tệp bằng ClamAV</button>}
        <button type="button" className="btn btn-secondary" disabled={downloading || !clean} title={!clean ? "Chưa thể tải khi tệp chưa được quét an toàn" : undefined} onClick={async () => {
          setDownloadError(""); setDownloading(true);
          try {await downloadDocument(thesis.id, doc, version, userId);} catch (cause) {setDownloadError(String(cause));}
          finally {setDownloading(false);}
        }}>Tải bản nộp gốc v{version.version_no}</button>
        {clean && <p className="text-caption">{["PLAN", "REPORT"].includes(doc.document_type) ? "Tải bản gốc giữ nguyên tệp SV đã nộp. Nếu cần in để ký, dùng bản xuất có footer ở dưới." : "Đây là tệp SV đã nộp, được giữ nguyên nội dung. Tài liệu hỗ trợ chưa có quy trình xuất bản chính thức để ký."}</p>}
        {canPrint && <button type="button" className="btn btn-secondary" disabled={downloading || busy} onClick={async () => {
          setDownloadError(""); setPrintNotice(""); setDownloading(true);
          try {
            await downloadDocument(thesis.id, doc, version, userId, true);
            setPrintRefresh(value => value + 1);
            setPrintNotice("Đã tải bản in PDF/DOCX có footer 3 dòng góc dưới bên trái (Xuất tại, Mã số, Thời điểm xuất). Bản nộp gốc được giữ nguyên.");
          } catch (cause) {setDownloadError(String(cause));}
          finally {setDownloading(false);}
        }}>Xuất bản đã duyệt để ký ngoài (footer 3 dòng: nguồn · mã hồ sơ · giờ xuất)</button>}
        {["PLAN", "REPORT"].includes(doc.document_type) && !canPrint && <p className="text-caption">{["ACCEPTED", "FINAL"].includes(version.state) ? "Chỉ bản đã duyệt hiện hành được xuất để ký ngoài." : "Sau khi GVHD tiếp nhận phiên bản này, nút xuất bản đã duyệt có footer để ký sẽ xuất hiện."}</p>}
        {["PLAN", "REPORT"].includes(doc.document_type) && <PrintHistory endpoint={`/theses/${thesis.id}/documents/${doc.id}/versions/${version.id}/print-history`} userId={userId} version={version.version_no} refreshKey={printRefresh} />}
        {clean && <FileReviewButton userId={userId} run={run} disabled={busy} target={{
          versionId: version.id, fileName: version.file_name, versionNo: version.version_no, submittedBy: version.submitted_by_name,
          rowVersion: version.row_version, label: doc.title, reviews: version.reviews,
          annotationsPath: `/theses/${thesis.id}/documents/${doc.id}/versions/${version.id}/annotations`,
          downloadPath: `/theses/${thesis.id}/documents/${doc.id}/versions/${version.id}/download`,
          reviewPath: `/theses/${thesis.id}/documents/${doc.id}/versions/${version.id}/review`,
          choices: [{value:"ACCEPT", label:"Tiếp nhận bản này"}, {value:"REVISION_REQUIRED", label:"Yêu cầu chỉnh sửa"}],
        }} />}
        <Reviews items={version.reviews} />
        {index === 0 && version.state === "SUBMITTED" && thesis.actions.includes("document:review") && doc.document_type !== "PROPOSAL" && ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state) && <>
          {!clean && <p className="alert alert-warning">Tệp chưa được quét: GVHD có thể yêu cầu nộp lại theo tên tệp/trạng thái, nhưng chưa thể xem nội dung hoặc tiếp nhận. Cần bộ quét hoạt động để tải và duyệt.</p>}
          {!clean && <ReviewForm disabled={busy} choices={clean
            ? [{value: "ACCEPT", label: "Tiếp nhận bản này"}, {value: "REVISION_REQUIRED", label: "Yêu cầu chỉnh sửa"}]
            : [{value: "REVISION_REQUIRED", label: "Yêu cầu nộp lại (chưa xem tệp)"}]} onSubmit={(decision, comment) =>
            run(() => request(`/theses/${thesis.id}/documents/${doc.id}/versions/${version.id}/review`, userId, {
              method: "POST", headers: {"If-Match": String(version.row_version)}, body: JSON.stringify({decision, comment}),
            }), "Đã lưu nhận xét tài liệu.")} />}
        </>}
      </section>;
    }} />}
  </div></article>;
}

export default function ThesisDocuments({thesis, docs, deadlines, reports, userId, busy, run, kind = "PLAN", pendingOnly = false, legacyOnly = false}: {
  thesis: Thesis; docs: ThesisDocument[]; deadlines: DocumentDeadline[]; reports: ProgressReport[]; userId: string;
  busy: boolean; run: CoreRun; kind?: "PLAN" | "REPORT" | "SUPPORTING"; pendingOnly?: boolean; legacyOnly?: boolean;
}) {
  const heading = kind === "PLAN" ? "Kế hoạch thực hiện · Mẫu 2" : kind === "REPORT" ? "Cuốn báo cáo KLTN" : "Tài liệu hỗ trợ";
  const [title, setTitle] = useState(kind === "PLAN" ? documentPresets.PLAN : kind === "REPORT" ? "Cuốn báo cáo KLTN" : documentPresets.SUPPORTING_REFERENCES);
  const [preset, setPreset] = useState("SUPPORTING_REFERENCES");
  const [file, setFile] = useState<File | null>(null);
  const [templateError, setTemplateError] = useState("");
  const progressEvidenceIds = new Set(reports.map(report => report.evidence_document_version_id).filter((id): id is string => !!id));
  const visibleDocs = docs.filter(doc => doc.document_type === kind && (!pendingOnly || doc.versions[0]?.state === "SUBMITTED") && !(kind === "SUPPORTING" && doc.title.startsWith("Minh chứng tiến độ ") && doc.versions.some(version => progressEvidenceIds.has(version.id))));
  const active = ["ACTIVE","PROPOSAL_APPROVED","IN_PROGRESS","EXTENDED"].includes(thesis.state);
  const canCreate = !legacyOnly && thesis.actions.includes("document:submit") && active && (kind === "SUPPORTING" || visibleDocs.length === 0);
  const validFile = !!file && file.size > 0 && file.size <= 10*1024*1024 && (kind === "SUPPORTING" ? /\.(pdf|docx|txt)$/i : /\.(pdf|docx)$/i).test(file.name);
  const deadline = deadlines.find(item => item.document_type === kind);
  const canFirstSubmit = deadline?.state === "OPEN";
  return <div className="stack">
    <div className="submission-heading"><div><span className="section-eyebrow">{kind === "PLAN" ? "KẾ HOẠCH CỦA NHÓM" : kind === "REPORT" ? "BẢN BÁO CÁO HOÀN CHỈNH" : "TỆP HỖ TRỢ HỒ SƠ"}</span><h2>{heading}</h2><p>{kind === "PLAN"
      ? "Một kế hoạch chung cho đề tài. Nộp bản đã điền; GVHD nhận xét, yêu cầu sửa hoặc tiếp nhận."
      : kind === "REPORT" ? "Nộp cuốn báo cáo trước bảo vệ. Đây là bản báo cáo hoàn chỉnh, khác với báo cáo tiến độ định kỳ."
      : legacyOnly ? "Các tệp đã nộp trước đây vẫn được giữ để xem lại và đối chiếu." : "Tệp hỗ trợ cho hồ sơ khóa luận."}</p></div>
      {kind === "PLAN" && <button type="button" className="btn btn-secondary" disabled={busy} onClick={async () => {
        setTemplateError(""); try {await downloadPlanTemplate(thesis.round_id);} catch (cause) {setTemplateError(String(cause));}
      }}>Tải mẫu áp dụng · Mẫu 2</button>}
    </div>
    {templateError && <p role="alert" className="alert alert-danger">{templateError}</p>}
    {canCreate && <form className="card" onSubmit={async event => {
      event.preventDefault();
      if (!file || !validFile || !canFirstSubmit) return;
      const form = event.currentTarget;
      if (await run(async () => {
        const created = await request<ThesisDocument>("/theses/" + thesis.id + "/documents", userId, {
          method:"POST", body:JSON.stringify({title:title.trim(), document_type:kind}),
        });
        await uploadDocument(thesis.id, created, userId, file);
      }, "Đã nộp phiên bản đầu; GVHD có thể xem sau khi tệp được quét an toàn.")) {
        setFile(null); form.reset();
      }
    }}><div className="card-body core-form">
      <h3>{kind === "SUPPORTING" ? "Nộp thêm tài liệu bổ sung" : "Nộp bản đầu tiên"}</h3>
      {kind === "SUPPORTING" && <>
        <label htmlFor="supporting-preset">Nội dung tài liệu</label>
        <select id="supporting-preset" className="input" value={preset} disabled={busy} onChange={event => {setPreset(event.target.value); setTitle(documentPresets[event.target.value]);}}>
          {Object.entries(documentPresets).filter(([value]) => value !== "PLAN").map(([value,label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <label htmlFor="supporting-title">Tên tài liệu</label><input id="supporting-title" className="input" value={title} required maxLength={255} disabled={busy} onChange={event => setTitle(event.target.value)} />
      </>}
      <label htmlFor="new-document-file">Tệp cần nộp ({kind === "SUPPORTING" ? "PDF, DOCX, TXT" : "PDF, DOCX"} · tối đa 10 MB)</label>
      <input id="new-document-file" className="input" type="file" required disabled={busy || !canFirstSubmit} accept={kind === "SUPPORTING" ? ".pdf,.docx,.txt" : ".pdf,.docx"} onChange={event => setFile(event.target.files?.[0] || null)} />
      {file && !validFile && <p role="alert" className="alert alert-danger">Tệp phải đúng định dạng, không rỗng và không quá 10 MB.</p>}
      {!canFirstSubmit && <p className="alert alert-info">{deadline ? "Đợt đã đóng nhận loại tài liệu này. Các bản đã nộp vẫn được xem và xử lý." : "Khoa chưa mở nhận loại tài liệu này."}</p>}
      <button className="btn btn-primary" disabled={busy || !validFile || !title.trim() || !canFirstSubmit}>{busy ? "Đang nộp và quét tệp…" : "Nộp " + (kind === "PLAN" ? "kế hoạch Mẫu 2" : kind === "REPORT" ? "cuốn báo cáo" : "tài liệu")}</button>
    </div></form>}
    {visibleDocs.map(doc => kind === "SUPPORTING"
      ? <details className="card submission-attachment" key={doc.id}><summary><strong>{doc.title}</strong><span>{doc.versions.length} phiên bản · {doc.versions[0]?.file_name || "Chưa có tệp"}</span></summary><div className="card-body"><DocumentCard doc={doc} thesis={thesis} deadline={deadline} progressEvidenceIds={progressEvidenceIds} userId={userId} busy={busy} run={run}/></div></details>
      : <DocumentCard key={doc.id} doc={doc} thesis={thesis} deadline={deadline} progressEvidenceIds={progressEvidenceIds} userId={userId} busy={busy} run={run}/>)}
    {visibleDocs.length === 0 && !canCreate && <EmptyState title={"Chưa có " + (kind === "PLAN" ? "kế hoạch được nộp" : kind === "REPORT" ? "cuốn báo cáo được nộp" : "tài liệu bổ sung")} description="Khi nhóm sinh viên nộp tệp, các phiên bản và thao tác xử lý đúng quyền sẽ xuất hiện tại đây."/>}
  </div>;
}
