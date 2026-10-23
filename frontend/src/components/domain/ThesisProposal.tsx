import { useState } from "react";
import { X } from "lucide-react";
import type { DocumentDeadline, Lecturer, Proposal, Thesis } from "../../api";
import { downloadProposal, downloadProposalTemplate, request, uploadProposal } from "../../api";
import { scanLabel } from "./ThesisDocuments";
import type { CoreRun } from "./ThesisDocuments";
import { formatDate, ReviewForm, Reviews, Status } from "./CoreForms";

export default function ThesisProposal({thesis, proposal, deadline, lecturers, userId, busy, run}: {
  thesis: Thesis; proposal: Proposal; deadline?: DocumentDeadline; lecturers: Lecturer[]; userId: string; busy: boolean; run: CoreRun;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [reviewerId, setReviewerId] = useState("");
  const [reason, setReason] = useState("");
  const [officialRef, setOfficialRef] = useState("");
  const [downloadError, setDownloadError] = useState("");
  const [printNotice, setPrintNotice] = useState("");
  const [downloading, setDownloading] = useState(false);
  const active = ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state);
  const latest = proposal.versions[0];
  const beforeDue = deadline?.state === "OPEN" && Date.now() <= new Date(deadline.due_at).getTime();
  const canSubmit = active && thesis.actions.includes("proposal:submit") && !!deadline && (
    proposal.state === "REVISION_REQUIRED" ||
    (deadline.state === "OPEN" && !latest && proposal.state === "DRAFT") ||
    (beforeDue && !!latest && ["SUBMITTED", "UNDER_REVIEW"].includes(proposal.state) && latest.reviews.length === 0));
  const canReview = active && thesis.actions.includes("proposal:review") && ["SUBMITTED", "UNDER_REVIEW"].includes(proposal.state);
  const canComment = active && !canReview && thesis.actions.includes("proposal:comment") && ["SUBMITTED", "UNDER_REVIEW", "ADVISOR_CONFIRMED"].includes(proposal.state);

  return <section className="stack">
    <div className="card"><div className="card-body stack">
      <h2>Đề cương khóa luận</h2>
      <p className="text-body-sm text-muted">Soạn nội dung trên mẫu đề cương chính thức của Khoa, rồi nộp bản PDF/DOCX đã điền. Mỗi lần sửa và nộp lại tạo một phiên bản riêng. GVHD nhận xét, Trưởng bộ môn chốt. Hệ thống chỉ đọc mẫu gốc, không tự dựng mẫu thay thế.</p>
      <p className="text-body-sm"><strong>Hạn đề cương:</strong> {deadline ? `${formatDate(deadline.due_at)} · ${deadline.state === "OPEN" ? "đang nhận" : "đã đóng"}` : "Khoa chưa thiết lập — chưa nhận tệp"}</p>
      <p className="text-caption">Có thể tự nộp bản sửa trước hạn khi GVHD chưa phản hồi; bản cũ vẫn lưu. Sau hạn hoặc khi đóng, chỉ nộp bản mới khi GVHD yêu cầu sửa.</p>
      <button type="button" className="btn btn-secondary" disabled={downloading} onClick={async () => {
        setDownloadError(""); setDownloading(true);
        try {await downloadProposalTemplate();} catch (cause) {setDownloadError(String(cause));}
        finally {setDownloading(false);}
      }}>Tải mẫu chính thức Mẫu 3</button>
      {downloadError && <p role="alert" className="alert alert-danger">{downloadError}</p>}
      <div><Status value={proposal.state} />{proposal.current_version_no && <span className="text-muted"> · Bản hiện hành v{proposal.current_version_no}</span>}</div>
      <p className="text-body-sm text-muted">Sau khi Trưởng bộ môn chốt, có thể xuất đúng phiên bản PDF/DOCX hiện hành đã duyệt và quét sạch. Bản in ghi “Xuất tại”, địa chỉ hệ thống, mã số và thời gian ở góc dưới bên trái; tệp nộp gốc được giữ nguyên.</p>
      {printNotice && <p role="status" className="alert alert-success">{printNotice}</p>}
      {canSubmit && <form className="core-form" onSubmit={async event => {
        event.preventDefault();
        const form = event.currentTarget;
        if (file && await run(() => uploadProposal(thesis.id, proposal, userId, file), "Đã nộp đề cương theo phiên bản mới.")) {
          setFile(null); form.reset();
        }
      }}>
        <label htmlFor="proposal-file">Nộp đề cương PDF hoặc DOCX (tối đa 10 MB)</label>
        <input className="input" id="proposal-file" type="file" accept=".pdf,.docx" required disabled={busy}
          onChange={event => setFile(event.target.files?.[0] || null)} />
        {file && <div className="flex items-center gap-2" style={{margin: "var(--space-1) 0"}}>
          <span className="text-body-sm font-semibold">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
          <button type="button" className="btn btn-ghost btn-sm" title="Hủy chọn tệp" onClick={() => {
            setFile(null);
            const el = document.getElementById("proposal-file") as HTMLInputElement | null;
            if (el) el.value = "";
          }}><X size={14} aria-hidden="true" style={{marginRight: 4}} /> Xóa tệp đã chọn</button>
        </div>}
        <button className="btn btn-primary" disabled={busy || !file || file.size > 10*1024*1024}>{busy ? "Đang tải lên và quét an toàn…" : "Nộp đề cương"}</button>
        {file && file.size > 10*1024*1024 && <p role="alert">Tệp vượt quá 10 MB.</p>}
      </form>}
      {proposal.versions.length === 0 && <p className="text-muted">Chưa có bản đề cương.</p>}
    </div></div>

    {proposal.versions.map((version, index) => {
      const clean = version.scan_state === "CLEAN";
      const isCurrent = version.version_no === proposal.current_version_no;
      const suffix = version.file_name.slice(version.file_name.lastIndexOf(".")).toLowerCase();
      const canPrint = isCurrent && clean && [".pdf", ".docx"].includes(suffix) &&
        ["DEPARTMENT_FINALIZED", "DEAN_CONFIRMED", "PRINT_READY"].includes(proposal.state);
      return <article className="card" key={version.id}><div className="card-body stack">
      <div className="flex justify-between gap-3"><strong>Phiên bản {version.version_no} · {version.file_name}</strong>{index === 0 && <Status value={proposal.state} />}</div>
      <p className="text-body-sm text-muted">{version.submitted_by_name} · {formatDate(version.submitted_at)} · {(version.byte_size/1024).toFixed(1)} KB</p>
      {version.late && <strong className="late-badge" aria-label="Nộp trễ">! Nộp trễ</strong>}
      {version.due_at_at_submission && <p className="text-caption">Hạn áp dụng lúc nộp: {formatDate(version.due_at_at_submission)}</p>}
      <p className={`text-body-sm ${clean ? "text-muted" : "alert alert-warning"}`}>{scanLabel(version.scan_state)}{!clean ? " — bản này chưa thể tải xuống hoặc dùng để duyệt." : ""}</p>
      {["QUARANTINED", "FAILED"].includes(version.scan_state) && <button type="button" className="btn btn-secondary btn-sm" disabled={busy}
        onClick={() => run(() => request(`/theses/${thesis.id}/proposal/versions/${version.id}/scan`, userId, {method:"POST"}),
          "Đã quét lại đề cương bằng ClamAV; xem trạng thái mới của phiên bản.")}>Quét lại tệp bằng ClamAV</button>}
      <button type="button" className="btn btn-secondary" disabled={downloading || !clean} title={!clean ? "Chưa thể tải khi tệp chưa được quét an toàn" : undefined} onClick={async () => {
        setDownloadError(""); setDownloading(true);
        try {await downloadProposal(thesis.id, version, userId);} catch (cause) {setDownloadError(String(cause));}
        finally {setDownloading(false);}
      }}>Tải phiên bản {version.version_no}</button>
      {canPrint && <button type="button" className="btn btn-secondary" disabled={downloading || busy} onClick={async () => {
        setDownloadError(""); setPrintNotice(""); setDownloading(true);
        try {
          await downloadProposal(thesis.id, version, userId, true);
          setPrintNotice("Đã tải bản PDF/DOCX để ký ngoài. Bản in có địa chỉ hệ thống, mã số và thời gian ở góc dưới bên trái; mã cũng có trong tên tệp. Bản nộp gốc không đổi.");
        } catch (cause) {setDownloadError(String(cause));}
        finally {setDownloading(false);}
      }}>Xuất bản để ký ngoài (địa chỉ + mã số + giờ xuất)</button>}
      <Reviews items={version.reviews} />
      {index === 0 && (canReview || canComment) && !clean &&
        <p className="alert alert-warning">Chưa thể nhận xét: tệp đang cách ly – chưa quét an toàn. Cần máy quét tệp thật để chuyển trạng thái.</p>}
      {index === 0 && (canReview || canComment) && clean && <ReviewForm disabled={busy}
        choices={canReview ? [{value: "CONFIRM", label: "Xác nhận đề cương"}, {value: "REVISION_REQUIRED", label: "Yêu cầu chỉnh sửa"}] : [{value: "COMMENT", label: "Góp ý chéo"}]}
        onSubmit={(decision, comment) => run(() => request(`/theses/${thesis.id}/proposal/reviews`, userId, {
          method: "POST", headers: {"If-Match": String(proposal.row_version)}, body: JSON.stringify({decision, comment}),
        }), "Đã lưu nhận xét đề cương.")} />}
    </div></article>;
    })}

    {active && thesis.actions.includes("proposal:assign_reviewer") && proposal.id && !["DEPARTMENT_FINALIZED", "DEAN_CONFIRMED"].includes(proposal.state) && <div className="card"><div className="card-body stack">
      <h3>Phân công giảng viên góp ý</h3>
      {proposal.reviewers.map(item => <p key={item.lecturer_id}>{item.display_name}</p>)}
      <form className="core-form" onSubmit={async event => {
        event.preventDefault();
        if (await run(() => request(`/theses/${thesis.id}/proposal/reviewers`, userId, {
          method: "POST", headers: {"If-Match": String(proposal.row_version)},
          body: JSON.stringify({lecturer_id: reviewerId, reason}),
        }), "Đã phân công góp ý đề cương.")) setReason("");
      }}>
        <label htmlFor="proposal-reviewer">Giảng viên khác GVHD chính</label>
        <select className="input" id="proposal-reviewer" value={reviewerId} onChange={event => setReviewerId(event.target.value)} required disabled={busy}>
          <option value="">Chọn giảng viên cùng bộ môn</option>
          {lecturers.filter(item => item.id !== thesis.advisor_lecturer_id && !proposal.reviewers.some(row => row.lecturer_id === item.id)).map(item => <option key={item.id} value={item.id}>{item.display_name}</option>)}
        </select>
        <label htmlFor="proposal-reviewer-reason">Căn cứ phân công</label>
        <textarea className="input" id="proposal-reviewer-reason" value={reason} onChange={event => setReason(event.target.value)} minLength={3} maxLength={2000} required disabled={busy} />
        <button className="btn btn-primary" disabled={busy || !reviewerId || reason.trim().length < 3}>Phân công góp ý</button>
      </form>
    </div></div>}

    {active && thesis.actions.includes("proposal:finalize") && proposal.state === "ADVISOR_CONFIRMED" && <div className="card"><div className="card-body stack">
      <h3>Trưởng bộ môn chốt đề cương</h3>
      <ReviewForm disabled={busy} choices={[{value: "FINALIZE", label: "Chốt bản hiện hành"}]} onSubmit={(_, comment) =>
        run(() => request(`/theses/${thesis.id}/proposal/department-finalization`, userId, {
          method: "POST", headers: {"If-Match": String(proposal.row_version)}, body: JSON.stringify({reason: comment}),
        }), "Đã chốt đề cương.")} />
    </div></div>}

    {active && thesis.actions.includes("proposal:dean_confirm") && proposal.state === "DEPARTMENT_FINALIZED" && <div className="card"><div className="card-body stack">
      <h3>Ghi nhận bản giấy đã ký</h3>
      <p className="text-body-sm text-muted">Chỉ nhập số/vị trí lưu bản giấy đã có chữ ký Trưởng khoa. Thao tác này không tạo chữ ký điện tử.</p>
      <form className="core-form" onSubmit={async event => {
        event.preventDefault();
        if (await run(() => request(`/theses/${thesis.id}/proposal/dean-signed-copy`, userId, {
          method: "POST", headers: {"If-Match": String(proposal.row_version)}, body: JSON.stringify({official_ref: officialRef}),
        }), "Đã ghi nhận bản giấy có chữ ký.")) setOfficialRef("");
      }}>
        <label htmlFor="proposal-official-ref">Số hoặc vị trí lưu bản giấy đã ký</label>
        <input className="input" id="proposal-official-ref" value={officialRef} onChange={event => setOfficialRef(event.target.value)} required maxLength={255} disabled={busy} />
        <button className="btn btn-primary" disabled={busy || !officialRef.trim()}>Ghi nhận bản ký</button>
      </form>
    </div></div>}
  </section>;
}
