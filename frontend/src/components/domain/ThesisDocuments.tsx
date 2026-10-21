import { useEffect, useState } from "react";
import type { OfficialFormTemplate, ProgressReport, Thesis, ThesisDocument } from "../../api";
import { downloadDocument, downloadOfficialTemplate, downloadPlanTemplate, listFormTemplates, request, uploadDocument } from "../../api";
import { formatDate, ReviewForm, Reviews, Status } from "./CoreForms";

export type CoreRun = (action: () => Promise<unknown>, message: string) => Promise<boolean>;

export function scanLabel(state: string) {
  if (state === "CLEAN") return "Đã quét an toàn";
  if (state === "QUARANTINED") return "Đang cách ly – chưa quét";
  if (state === "INFECTED") return "Phát hiện mã độc – không sử dụng";
  return "Quét lỗi – không sử dụng";
}

function DocumentCard({doc, thesis, progressEvidenceIds, userId, busy, run}: {
  doc: ThesisDocument; thesis: Thesis; progressEvidenceIds: Set<string>; userId: string; busy: boolean; run: CoreRun;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [withdrawReason, setWithdrawReason] = useState("");
  const [downloadError, setDownloadError] = useState("");
  const [printNotice, setPrintNotice] = useState("");
  const [downloading, setDownloading] = useState(false);
  const canSubmit = !["REPORT", "PROPOSAL"].includes(doc.document_type) && thesis.actions.includes("document:submit") && ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state);
  const canWithdraw = thesis.actions.includes("document:submit") && ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state) && doc.document_type !== "PROPOSAL" && doc.versions.every(version =>
    version.state === "SUBMITTED" && version.reviews.length === 0 && !progressEvidenceIds.has(version.id));
  const latestAccepted = doc.versions.filter(version => ["ACCEPTED", "FINAL"].includes(version.state))
    .sort((a, b) => b.version_no - a.version_no)[0];
  return <article className="card"><div className="card-body stack">
    <div><h3>{doc.title}</h3><p className="text-muted">{doc.document_type === "PLAN" ? "Kế hoạch thực hiện · Mẫu 2" : doc.document_type === "REPORT" ? "Báo cáo khóa luận đã tạo trước đây" : "Tài liệu hỗ trợ"} · Chia sẻ trong phạm vi được phân công</p></div>
    {doc.document_type === "PLAN" && <p className="text-body-sm text-muted">Điền nội dung vào Mẫu 2 chính thức của Khoa trên Word, nộp bản PDF/DOCX tại đây. Nếu GVHD yêu cầu sửa, nộp một phiên bản mới; bản đã tiếp nhận được dùng làm bản chính thức trong hồ sơ.</p>}
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
    {canSubmit && doc.versions[0]?.state !== "FINAL" && <form className="core-form" onSubmit={async event => {
      event.preventDefault();
      const form = event.currentTarget;
      if (file && await run(() => uploadDocument(thesis.id, doc, userId, file), "Đã lưu phiên bản mới.")) {
        setFile(null);
        form.reset();
      }
    }}>
      <label htmlFor={`file-${doc.id}`}>Nộp phiên bản mới (PDF, DOCX, TXT; tối đa 10 MB)</label>
      <input className="input" id={`file-${doc.id}`} type="file" accept=".pdf,.docx,.txt" required disabled={busy}
        onChange={event => setFile(event.target.files?.[0] || null)} />
      <button className="btn btn-primary" disabled={busy || !file || file.size > 10*1024*1024}>Nộp tài liệu</button>
      {file && file.size > 10*1024*1024 && <p role="alert">Tệp vượt quá 10 MB.</p>}
    </form>}
    {downloadError && <div role="alert" className="alert alert-danger">{downloadError}</div>}
    {printNotice && <p role="status" className="alert alert-success">{printNotice}</p>}
    {doc.versions.length === 0 && <p className="text-muted">Chưa có tệp; hãy nộp phiên bản đầu tiên.</p>}
    {doc.versions.map((version, index) => {
      const clean = version.scan_state === "CLEAN";
      const suffix = version.file_name.slice(version.file_name.lastIndexOf(".")).toLowerCase();
      const canPrint = ["PLAN", "REPORT"].includes(doc.document_type) && version.id === latestAccepted?.id &&
        clean && [".pdf", ".docx"].includes(suffix);
      return <section className="core-version stack" key={version.id}>
        <div className="flex justify-between gap-3"><strong>Phiên bản {version.version_no} · {version.file_name}</strong><Status value={version.state} /></div>
        <p className="text-body-sm text-muted">{version.submitted_by_name} · {formatDate(version.submitted_at)} · {(version.byte_size/1024).toFixed(1)} KB</p>
        <p className={`text-body-sm ${clean ? "text-muted" : "alert alert-warning"}`}>{scanLabel(version.scan_state)}{!clean ? " — bản này chưa thể tải xuống hoặc dùng để duyệt." : ""}</p>
        <button type="button" className="btn btn-secondary" disabled={downloading || !clean} title={!clean ? "Chưa thể tải khi tệp chưa được quét an toàn" : undefined} onClick={async () => {
          setDownloadError(""); setDownloading(true);
          try {await downloadDocument(thesis.id, doc, version, userId);} catch (cause) {setDownloadError(String(cause));}
          finally {setDownloading(false);}
        }}>Tải phiên bản {version.version_no}</button>
        {canPrint && <button type="button" className="btn btn-secondary" disabled={downloading || busy} onClick={async () => {
          setDownloadError(""); setPrintNotice(""); setDownloading(true);
          try {
            await downloadDocument(thesis.id, doc, version, userId, true);
            setPrintNotice("Đã tải bản in PDF/DOCX có footer 3 dòng góc dưới bên trái (Xuất từ, Mã hồ sơ ổn định, Thời điểm xuất). Bản nộp gốc được giữ nguyên.");
          } catch (cause) {setDownloadError(String(cause));}
          finally {setDownloading(false);}
        }}>Xuất bản đã duyệt để ký ngoài (footer 3 dòng: nguồn · mã hồ sơ · giờ xuất)</button>}
        <Reviews items={version.reviews} />
        {index === 0 && version.state === "SUBMITTED" && thesis.actions.includes("document:review") && doc.document_type !== "PROPOSAL" && ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state) && <>
          {!clean && <p className="alert alert-warning">Tệp chưa được quét: GVHD có thể yêu cầu nộp lại theo tên tệp/trạng thái, nhưng chưa thể xem nội dung hoặc tiếp nhận. Cần bộ quét hoạt động để tải và duyệt.</p>}
          <ReviewForm disabled={busy} choices={clean
            ? [{value: "ACCEPT", label: "Tiếp nhận bản này"}, {value: "REVISION_REQUIRED", label: "Yêu cầu chỉnh sửa"}]
            : [{value: "REVISION_REQUIRED", label: "Yêu cầu nộp lại (chưa xem tệp)"}]} onSubmit={(decision, comment) =>
            run(() => request(`/theses/${thesis.id}/documents/${doc.id}/versions/${version.id}/review`, userId, {
              method: "POST", headers: {"If-Match": String(version.row_version)}, body: JSON.stringify({decision, comment}),
            }), "Đã lưu nhận xét tài liệu.")} />
        </>}
      </section>;
    })}
  </div></article>;
}

export default function ThesisDocuments({thesis, docs, reports, userId, busy, run}: {
  thesis: Thesis; docs: ThesisDocument[]; reports: ProgressReport[]; userId: string; busy: boolean; run: CoreRun;
}) {
  const [title, setTitle] = useState("");
  const [type, setType] = useState("PLAN");
  const [templateError, setTemplateError] = useState("");
  const [templates, setTemplates] = useState<OfficialFormTemplate[]>([]);
  const [downloadingTmpl, setDownloadingTmpl] = useState<string | null>(null);
  const progressEvidenceIds = new Set(reports.map(report => report.evidence_document_version_id).filter((id): id is string => !!id));
  const visibleDocs = docs.filter(doc => !(doc.document_type === "SUPPORTING" && doc.title.startsWith("Minh chứng tiến độ ") && doc.versions.some(version => progressEvidenceIds.has(version.id))));

  useEffect(() => {
    let alive = true;
    void listFormTemplates(userId).then(items => { if (alive) setTemplates(items); }).catch(() => undefined);
    return () => { alive = false; };
  }, [userId]);

  return <div className="stack">
    <div className="card"><div className="card-body stack">
      <h2>Biểu mẫu chính thức từ Khoa</h2>
      <p className="text-body-sm text-muted">Tải biểu mẫu chính thức do Khoa ban hành, điền thông tin theo quy định rồi nộp vào hồ sơ tương ứng. Hệ thống sử dụng trực tiếp tệp gốc từ Khoa, không tự dựng mẫu thay thế.</p>
      <p className="text-body-sm text-muted">Sinh viên xem và tải Mẫu 1a, 1b, 2–5; giảng viên xem toàn bộ 12 tệp biểu mẫu hiện có.</p>
      <div className="flex gap-2" style={{flexWrap: "wrap", marginTop: "var(--space-2)"}}>
        <button type="button" className="btn btn-primary" onClick={async () => {
          setTemplateError("");
          try {await downloadPlanTemplate();} catch (cause) {setTemplateError(String(cause));}
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
                  await downloadOfficialTemplate(tmpl.id, tmpl.filename);
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
      if (await run(() => request(`/theses/${thesis.id}/documents`, userId, {method: "POST", body: JSON.stringify({title, document_type: type})}), "Đã tạo hồ sơ tài liệu; chọn tệp để nộp.")) setTitle("");
    }}><div className="card-body core-form">
      <h3>Thêm tài liệu khác vào hồ sơ khóa luận</h3>
      <p className="text-body-sm text-muted">Chỉ dùng cho kế hoạch thực hiện (Mẫu 2) và tài liệu hỗ trợ của khóa luận. Báo cáo tiến độ cùng tệp minh chứng được nộp, xem và nhận xét tại mục Tiến độ. Biểu mẫu gốc của Khoa chỉ được tải về, không tạo hoặc tải lên tại đây.</p>
      <div className="input-group"><label htmlFor="document-title">Tên tài liệu</label><input className="input" id="document-title" value={title} onChange={event => setTitle(event.target.value)} required maxLength={255} disabled={busy} /></div>
      <div className="input-group"><label htmlFor="document-type">Loại tài liệu</label><select className="input" id="document-type" value={type} onChange={event => setType(event.target.value)} disabled={busy}>
        <option value="PLAN">Kế hoạch thực hiện (Mẫu 2)</option><option value="SUPPORTING">Tài liệu hỗ trợ khóa luận</option>
      </select></div>
      <button className="btn btn-primary" disabled={busy || !title.trim()}>Tạo hồ sơ tài liệu</button>
    </div></form>}
    {visibleDocs.map(doc => <DocumentCard key={doc.id} doc={doc} thesis={thesis} progressEvidenceIds={progressEvidenceIds} userId={userId} busy={busy} run={run} />)}
    {visibleDocs.length === 0 && <div className="card"><div className="card-body">
      <h3>Chưa có tài liệu nào trong hồ sơ</h3>
      <p className="text-muted">
        {thesis.actions.includes("document:submit")
          ? "Sinh viên trong nhóm hãy sử dụng form bên trên để tạo hồ sơ tài liệu (Kế hoạch thực hiện Mẫu 2 hoặc tài liệu hỗ trợ khóa luận) và tải phiên bản đầu tiên lên."
          : "Báo cáo tiến độ và minh chứng nằm tại mục Tiến độ. Tại đây chỉ hiển thị kế hoạch thực hiện và tài liệu hỗ trợ khóa luận được giao."}
      </p>
    </div></div>}
  </div>;
}
