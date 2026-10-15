import { useState } from "react";
import type { Thesis, ThesisDocument } from "../../api";
import { downloadDocument, request, uploadDocument } from "../../api";
import { formatDate, ReviewForm, Reviews, Status } from "./CoreForms";

export type CoreRun = (action: () => Promise<unknown>, message: string) => Promise<boolean>;

function DocumentCard({doc, thesis, userId, busy, run}: {
  doc: ThesisDocument; thesis: Thesis; userId: string; busy: boolean; run: CoreRun;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [downloadError, setDownloadError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const canSubmit = thesis.actions.includes("document:submit") && ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state);
  return <article className="card"><div className="card-body stack">
    <div><h3>{doc.title}</h3><p className="text-muted">{doc.document_type === "PROPOSAL" ? "Tệp đề cương" : doc.document_type === "REPORT" ? "Báo cáo" : "Tài liệu hỗ trợ"} · Chia sẻ trong phạm vi được phân công</p></div>
    {doc.document_type === "PROPOSAL" && <p className="text-body-sm">Lưu tệp đề cương ở đây. Quy trình GVHD → phản biện → TBM → Trưởng khoa sẽ được xử lý riêng.</p>}
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
    {doc.versions.length === 0 && <p className="text-muted">Chưa có tệp; hãy nộp phiên bản đầu tiên.</p>}
    {doc.versions.map((version, index) => <section className="core-version stack" key={version.id}>
      <div className="flex justify-between gap-3"><strong>Phiên bản {version.version_no} · {version.file_name}</strong><Status value={version.state} /></div>
      <p className="text-body-sm text-muted">{version.submitted_by_name} · {formatDate(version.submitted_at)} · {(version.byte_size/1024).toFixed(1)} KB</p>
      <details><summary>Mã kiểm tra SHA-256</summary><code className="core-hash">{version.sha256}</code></details>
      <p className="text-body-sm text-muted">{version.scan_state === "QUARANTINED" ? "Chưa quét virus; chỉ tải tệp về máy." : `Trạng thái quét: ${version.scan_state}`}</p>
      <button type="button" className="btn btn-secondary" disabled={downloading || ["INFECTED", "FAILED"].includes(version.scan_state)} onClick={async () => {
        setDownloadError(""); setDownloading(true);
        try {await downloadDocument(thesis.id, doc, version, userId);} catch (cause) {setDownloadError(String(cause));}
        finally {setDownloading(false);}
      }}>Tải phiên bản {version.version_no}</button>
      <Reviews items={version.reviews} />
      {index === 0 && version.state === "SUBMITTED" && thesis.actions.includes("document:review") && doc.document_type !== "PROPOSAL" && ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state) &&
        <ReviewForm disabled={busy} choices={[{value: "ACCEPT", label: "Tiếp nhận bản này"}, {value: "REVISION_REQUIRED", label: "Yêu cầu chỉnh sửa"}]} onSubmit={(decision, comment) =>
          run(() => request(`/theses/${thesis.id}/documents/${doc.id}/versions/${version.id}/review`, userId, {
            method: "POST", headers: {"If-Match": String(version.row_version)}, body: JSON.stringify({decision, comment}),
          }), "Đã lưu nhận xét tài liệu.")} />}
    </section>)}
  </div></article>;
}

export default function ThesisDocuments({thesis, docs, userId, busy, run}: {
  thesis: Thesis; docs: ThesisDocument[]; userId: string; busy: boolean; run: CoreRun;
}) {
  const [title, setTitle] = useState("");
  const [type, setType] = useState("REPORT");
  return <div className="stack">
    {thesis.actions.includes("document:submit") && ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state) && <form className="card" onSubmit={async event => {
      event.preventDefault();
      if (await run(() => request(`/theses/${thesis.id}/documents`, userId, {method: "POST", body: JSON.stringify({title, document_type: type})}), "Đã tạo hồ sơ tài liệu; chọn tệp để nộp.")) setTitle("");
    }}><div className="card-body core-form">
      <h3>Thêm tài liệu</h3>
      <div className="input-group"><label htmlFor="document-title">Tên tài liệu</label><input className="input" id="document-title" value={title} onChange={event => setTitle(event.target.value)} required maxLength={255} disabled={busy} /></div>
      <div className="input-group"><label htmlFor="document-type">Loại tài liệu</label><select className="input" id="document-type" value={type} onChange={event => setType(event.target.value)} disabled={busy}>
        <option value="REPORT">Báo cáo khóa luận</option><option value="SUPPORTING">Tài liệu hỗ trợ</option>
      </select></div>
      <button className="btn btn-primary" disabled={busy || !title.trim()}>Tạo hồ sơ tài liệu</button>
    </div></form>}
    {docs.map(doc => <DocumentCard key={doc.id} doc={doc} thesis={thesis} userId={userId} busy={busy} run={run} />)}
    {docs.length === 0 && <p className="text-muted">Chưa có tài liệu được nộp.</p>}
  </div>;
}
