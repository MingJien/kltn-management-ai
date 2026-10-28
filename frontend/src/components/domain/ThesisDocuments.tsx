import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { Link } from "react-router-dom";
import type { DocumentDeadline, OfficialFormTemplate, ProgressReport, Thesis, ThesisDocument } from "../../api";
import { downloadDocument, downloadOfficialTemplate, downloadPlanTemplate, listFormTemplates, request, uploadDocument } from "../../api";
import { formatDate, ReviewForm, Reviews, Status } from "./CoreForms";
import PrintHistory from "./PrintHistory";
import FileReviewButton from "./FileReviewButton";
import VersionTimeline from "./VersionTimeline";

const documentPresets: Record<string, string> = {
  PLAN: "Kế hoạch thực hiện (Mẫu 2)",
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
    <div className="flex justify-between items-start gap-2">
      <div><h3>{doc.title}</h3><p className="text-muted">{doc.document_type === "PLAN" ? "Kế hoạch thực hiện · Mẫu 2" : doc.document_type === "REPORT" ? "Cuốn báo cáo KLTN · bản lưu để đối chiếu tương đồng" : doc.document_type === "PROPOSAL" ? "Đề cương · Mẫu 3" : "Tài liệu hỗ trợ"} · Chia sẻ trong phạm vi được phân công</p></div>
    </div>
    {doc.document_type === "PLAN" && <p className="text-body-sm text-muted">Điền nội dung vào Mẫu 2 chính thức của Khoa trên Word, nộp bản PDF/DOCX tại đây. Nếu GVHD yêu cầu sửa, nộp một phiên bản mới; bản đã tiếp nhận được dùng làm bản chính thức trong hồ sơ.</p>}
    {doc.document_type === "REPORT" && <p className="text-body-sm text-muted">Nộp cuốn báo cáo KLTN hoàn chỉnh trước khi ra hội đồng. Hệ thống giữ nguyên từng phiên bản để đối chiếu tương đồng về sau; kết quả tương đồng chỉ là tham khảo, không tự chặn nộp hay bảo vệ. Báo cáo tiến độ hàng tuần vẫn nộp tại mục Tiến độ theo mốc.</p>}
    {doc.document_type !== "PROPOSAL" && <p className="text-body-sm"><strong>Hạn nộp:</strong> {deadline ? `${formatDate(deadline.due_at)} · ${deadline.state === "OPEN" ? "đang nhận" : "đã đóng"}` : "Khoa chưa thiết lập — chưa nhận tệp"}. Trước hạn được nộp bản mới nếu GVHD chưa phản hồi; sau hạn chỉ nộp lại khi GVHD yêu cầu sửa.</p>}
    {doc.document_type === "PROPOSAL" && <p className="text-body-sm">Lưu tệp đề cương ở đây. Quy trình GVHD → phản biện → TBM → Trưởng khoa sẽ được xử lý riêng.</p>}
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
      <strong>GVHD yêu cầu sửa bản v{latest.version_no}.</strong> Chọn tệp sửa ngay trong hồ sơ này để tạo bản v{latest.version_no + 1}; bản cũ và nhận xét vẫn được giữ. Không cần tạo hồ sơ tài liệu khác.
    </div>}
    {canSubmit && doc.versions[0]?.state !== "FINAL" && <form className="core-form" aria-labelledby={`document-upload-heading-${doc.id}`} onSubmit={async event => {
      event.preventDefault();
      const form = event.currentTarget;
      if (file && validFileType && await run(() => uploadDocument(thesis.id, doc, userId, file), "Đã lưu phiên bản mới.")) {
        setFile(null);
        form.reset();
      }
    }}>
      <h4 id={`document-upload-heading-${doc.id}`}>{latest?.state === "REVISION_REQUESTED" ? `Nộp bản sửa v${latest.version_no + 1} theo yêu cầu GVHD` : latest ? `Cập nhật bằng phiên bản v${latest.version_no + 1}` : "Nộp phiên bản đầu tiên"}</h4>
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
    </form>}
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
        {version.late && <strong className="late-badge" aria-label="Nộp trễ">! Nộp trễ</strong>}
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

export default function ThesisDocuments({thesis, docs, deadlines, reports, userId, busy, run}: {
  thesis: Thesis; docs: ThesisDocument[]; deadlines: DocumentDeadline[]; reports: ProgressReport[]; userId: string; busy: boolean; run: CoreRun;
}) {
  const [title, setTitle] = useState(documentPresets.PLAN);
  const [type, setType] = useState("PLAN");
  const [templateError, setTemplateError] = useState("");
  const [templates, setTemplates] = useState<OfficialFormTemplate[]>([]);
  const [downloadingTmpl, setDownloadingTmpl] = useState<string | null>(null);
  const progressEvidenceIds = new Set(reports.map(report => report.evidence_document_version_id).filter((id): id is string => !!id));
  const visibleDocs = docs.filter(doc => !(doc.document_type === "SUPPORTING" && doc.title.startsWith("Minh chứng tiến độ ") && doc.versions.some(version => progressEvidenceIds.has(version.id))));
  const documentType = type === "PLAN" ? "PLAN" : type === "REPORT" ? "REPORT" : "SUPPORTING";
  const routedType = ["REGISTRATION", "PROPOSAL", "PROGRESS"].includes(type);
  const existingPlan = visibleDocs.find(doc => doc.document_type === "PLAN");
  const existingReport = visibleDocs.find(doc => doc.document_type === "REPORT");

  useEffect(() => {
    let alive = true;
    void listFormTemplates(userId, thesis.round_id).then(items => { if (alive) setTemplates(items); }).catch(() => undefined);
    return () => { alive = false; };
  }, [userId]);

  return <div className="stack">
    <div className="card"><div className="card-body stack">
      <h2>Biểu mẫu chính thức từ Khoa</h2>
      <Link className="btn btn-secondary" to={`/forms?round_id=${thesis.round_id}`}>Mở kho biểu mẫu và tài liệu Khoa theo đợt</Link>
      <p className="text-body-sm text-muted">Tải biểu mẫu chính thức do Khoa ban hành, điền thông tin theo quy định rồi nộp vào hồ sơ tương ứng. Hệ thống sử dụng trực tiếp tệp gốc từ Khoa, không tự dựng mẫu thay thế.</p>
      <p className="text-body-sm text-muted">Sinh viên xem và tải Mẫu 1a, 1b, 2–5; giảng viên xem toàn bộ 12 tệp biểu mẫu hiện có.</p>
      <p className="text-body-sm">Mẫu 1a/1b nằm ở hồ sơ đăng ký; Mẫu 2 và Cuốn báo cáo KLTN nộp tại đây; Mẫu 3 nộp trong mục Đề cương. Mẫu 4 là danh sách tổng hợp, Mẫu 5 hướng dẫn trình bày. Báo cáo tiến độ định kỳ nộp tại mục Tiến độ.</p>
      <div className="flex gap-2" style={{flexWrap: "wrap", marginTop: "var(--space-2)"}}>
        <button type="button" className="btn btn-primary" onClick={async () => {
          setTemplateError("");
          try {await downloadPlanTemplate(thesis.round_id);} catch (cause) {setTemplateError(String(cause));}
        }}>Tải nhanh Mẫu 2 (Kế hoạch)</button>
      </div>
      {templates.length > 0 && <details style={{marginTop: "var(--space-2)"}} open>
        <summary style={{cursor: "pointer", fontWeight: 600}}>Xem toàn bộ biểu mẫu chính thức ({templates.length} biểu mẫu)</summary>
        <div className="stack" style={{marginTop: "var(--space-2)", gap: "var(--space-2)"}}>
          {templates.map(tmpl => (
            <div key={tmpl.id} className="flex justify-between items-center" style={{padding: "var(--space-2)", background: "var(--surface-subtle, #f8fafc)", borderRadius: "var(--radius-sm)"}}>
              <div>
                <strong>{tmpl.title}</strong>
                <span className="text-muted text-body-sm" style={{marginLeft: "var(--space-2)"}}>({tmpl.filename} · {(tmpl.byte_size / 1024).toFixed(1)} KB)</span>
              </div>
              <button type="button" className="btn btn-secondary btn-sm" disabled={downloadingTmpl === tmpl.id} onClick={async () => {
                setTemplateError("");
                setDownloadingTmpl(tmpl.id);
                try {
                  await downloadOfficialTemplate(tmpl.id, tmpl.filename, thesis.round_id);
                } catch (cause) {
                  setTemplateError(String(cause));
                } finally {
                  setDownloadingTmpl(null);
                }
              }}>{downloadingTmpl === tmpl.id ? "Đang tải…" : "Tải mẫu"}</button>
            </div>
          ))}
        </div>
      </details>}
      {templateError && <p role="alert" className="alert alert-danger">{templateError}</p>}

    </div></div>
    {thesis.actions.includes("document:submit") && ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state) && <form className="card" onSubmit={async event => {
      event.preventDefault();
      if (routedType || (type === "PLAN" && existingPlan) || (type === "REPORT" && existingReport)) return;
      if (await run(() => request(`/theses/${thesis.id}/documents`, userId, {method: "POST", body: JSON.stringify({title, document_type: documentType})}), "Đã tạo hồ sơ tài liệu; chọn tệp để nộp.")) setTitle("");
    }}><div className="card-body core-form">
      <h3>Thêm tài liệu khác vào hồ sơ khóa luận</h3>
      <p className="text-body-sm text-muted">Chọn nội dung cần nộp. Các mẫu có quy trình riêng sẽ dẫn về đúng hồ sơ; tài liệu hỗ trợ được đặt tên sẵn và có thể sửa lại cho phù hợp.</p>
      <div className="input-group"><label htmlFor="document-type">Loại tài liệu</label><select className="input" id="document-type" value={type} onChange={event => {
        const next = event.target.value;
        if (next === "REPORT" && (!title.trim() || Object.values(documentPresets).includes(title))) setTitle("Cuốn báo cáo KLTN");
        else if (documentPresets[next] && (!title.trim() || Object.values(documentPresets).includes(title))) setTitle(documentPresets[next]);
        setType(next);
      }} disabled={busy}>
        <optgroup label="Biểu mẫu và báo cáo"><option value="REGISTRATION">Đơn đăng ký (Mẫu 1a/1b) — hồ sơ đăng ký</option><option value="PLAN">Kế hoạch thực hiện (Mẫu 2)</option><option value="PROPOSAL">Đề cương (Mẫu 3) — mục Đề cương</option><option value="PROGRESS">Báo cáo tiến độ — mục Tiến độ</option><option value="REPORT">Cuốn báo cáo KLTN — nộp trước hội đồng</option></optgroup>
        <optgroup label="Tài liệu hỗ trợ">{Object.entries(documentPresets).filter(([value]) => value !== "PLAN").map(([value, label]) => <option key={value} value={value}>{label}</option>)}</optgroup>
      </select></div>
      {type === "REGISTRATION" ? <div className="alert alert-info"><p>Khoa xác nhận danh sách đủ điều kiện và cấp quyền tài khoản; SV đăng nhập, chọn/đề xuất đề tài rồi nộp Mẫu 1a (cá nhân) hoặc 1b (nhóm) trong hồ sơ đăng ký trước khi GV tiếp nhận. Đơn này là hồ sơ xin làm KLTN, không phải đơn xin tài khoản.</p><Link className="btn btn-secondary" to={thesis.registration_id ? `/registrations?focus=${thesis.registration_id}` : "/registrations"}>Mở đơn Mẫu 1a/1b trong hồ sơ đăng ký</Link></div>
        : type === "PROPOSAL" ? <div className="alert alert-info"><p>Đề cương được nộp và xét duyệt theo phiên bản trong mục Đề cương.</p><Link className="btn btn-secondary" to={`/theses/${thesis.id}?section=proposal`}>Mở nơi nộp Đề cương Mẫu 3</Link></div>
        : type === "PROGRESS" ? <div className="alert alert-info"><p>Báo cáo và minh chứng được nộp theo từng mốc của đợt.</p><Link className="btn btn-secondary" to={`/theses/${thesis.id}?section=progress`}>Mở nơi nộp báo cáo tiến độ</Link></div>
        : type === "PLAN" && existingPlan ? <div className="alert alert-info"><p>Đã có hồ sơ Kế hoạch Mẫu 2. Nộp bản đầu hoặc bản sửa trong hồ sơ đó để giữ cùng lịch sử.</p><a className="btn btn-secondary" href={`#document-${existingPlan.id}`}>Đến hồ sơ Kế hoạch Mẫu 2 đã có</a></div>
        : type === "REPORT" && existingReport ? <div className="alert alert-info"><p>Đã có hồ sơ Cuốn báo cáo KLTN. Nộp bản đầu trước hội đồng hoặc bản sửa trong hồ sơ đó để giữ cùng lịch sử và bản đối chiếu tương đồng.</p><a className="btn btn-secondary" href={`#document-${existingReport.id}`}>Đến hồ sơ Cuốn báo cáo KLTN đã có</a></div>
        : <><div className="input-group"><label htmlFor="document-title">Tên tài liệu</label><input className="input" id="document-title" value={title} onChange={event => setTitle(event.target.value)} required maxLength={255} disabled={busy} /></div>
          <p className="text-body-sm text-muted">Hạn {documentType === "PLAN" ? "kế hoạch" : documentType === "REPORT" ? "cuốn báo cáo KLTN" : "tài liệu hỗ trợ"}: {(() => {const item = deadlines.find(deadline => deadline.document_type === documentType); return item ? `${formatDate(item.due_at)} · ${item.state === "OPEN" ? "đang nhận" : "đã đóng"}` : "Khoa chưa thiết lập";})()}</p>
          <button className="btn btn-primary" disabled={busy || !title.trim()}>Tạo hồ sơ tài liệu</button></>}
    </div></form>}
    {visibleDocs.map(doc => <DocumentCard key={doc.id} doc={doc} thesis={thesis} deadline={deadlines.find(item => item.document_type === doc.document_type)} progressEvidenceIds={progressEvidenceIds} userId={userId} busy={busy} run={run} />)}
    {visibleDocs.length === 0 && <div className="card"><div className="card-body">
      <h3>Chưa có tài liệu nào trong hồ sơ</h3>
      <p className="text-muted">
        {thesis.actions.includes("document:submit")
          ? "Sinh viên trong nhóm hãy sử dụng form bên trên để tạo hồ sơ tài liệu (Kế hoạch thực hiện Mẫu 2, Cuốn báo cáo KLTN trước hội đồng hoặc tài liệu hỗ trợ khóa luận) và tải phiên bản đầu tiên lên."
          : "Báo cáo tiến độ và minh chứng nằm tại mục Tiến độ. Tại đây chỉ hiển thị kế hoạch thực hiện, cuốn báo cáo KLTN và tài liệu hỗ trợ khóa luận được giao."}
      </p>
    </div></div>}
  </div>;
}
