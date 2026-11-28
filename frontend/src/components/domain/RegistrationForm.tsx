import { useEffect, useState } from "react";
import { X } from "lucide-react";
import type { Context } from "../../api";
import { request } from "../../api";
import { errorMessage } from "../../errors";

export default function RegistrationForm({ context, userId, roundId, busy, disabled = false, onSubmit, joining = false }: {
  context: Context; userId: string; roundId: string; capacity?: number; busy: boolean;
  onSubmit: (evidence?: File) => Promise<void>; disabled?: boolean; joining?: boolean;
}) {
  const [consent, setConsent] = useState(false);
  const [evidence, setEvidence] = useState<File | null>(null);
  const [evidenceError, setEvidenceError] = useState("");
  const [eligibility, setEligibility] = useState<{eligible: boolean; has_active_registration: boolean} | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    request<typeof eligibility>("/me/eligibility?round_id=" + roundId, userId)
      .then((result) => { if (alive) setEligibility(result); })
      .catch((cause) => { if (alive) setError(errorMessage(cause)); });
    return () => { alive = false; };
  }, [roundId, userId]);
  function chooseEvidence(file?: File) {
    if (!file) return;
    if (file.size === 0) { setEvidence(null); setEvidenceError("Tệp minh chứng đang rỗng (0 byte). Vui lòng chọn tệp có nội dung hợp lệ."); return; }
    if (file.size > 5 * 1024 * 1024) { setEvidence(null); setEvidenceError("Tệp minh chứng tối đa 5 MB."); return; }
    if (!/\.(pdf|png|jpe?g)$/i.test(file.name)) {
      setEvidence(null); setEvidenceError("Chỉ nhận tệp PDF, PNG hoặc JPEG."); return;
    }
    setEvidence(file); setEvidenceError("");
  }
  return <fieldset className="registration-fieldset stack" disabled={busy}>
    <legend>Thông tin đăng ký của tôi</legend>
    <div className="input-row input-row--thirds">
      <div className="input-group">
        <label htmlFor="reg-name">Họ tên</label>
        <input id="reg-name" className="input" readOnly value={context.display_name} />
      </div>
      <div className="input-group">
        <label htmlFor="reg-code">MSSV</label>
        <input id="reg-code" className="input" readOnly value={context.student_code || ""} />
      </div>
      <div className="input-group">
        <label htmlFor="reg-email">Email</label>
        <input id="reg-email" className="input" readOnly value={context.email || ""} />
      </div>
    </div>
    <p className="text-body-sm text-muted">Bạn tự đăng ký bằng tài khoản của mình. Các bạn khác cũng tự đăng nhập và tham gia khi đề tài còn chỗ.</p>
    <label className="consent-label"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> Tôi xác nhận tham gia đề tài và thông tin đăng ký của mình.</label>
    {!eligibility && !error ? <p role="status">Đang kiểm tra điều kiện đăng ký…</p> : null}
    {eligibility && !eligibility.eligible ? <p className="alert alert-warning">Bạn chưa được xác nhận đủ điều kiện ở đợt này. Liên hệ người phụ trách của Khoa.</p> : null}
    {eligibility?.has_active_registration ? <p className="alert alert-warning">Bạn đã có đăng ký đang hoạt động trong đợt. Mở mục Đăng ký để xem.</p> : null}
    {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
    <section className="registration-evidence" aria-labelledby="registration-evidence-title">
      <div className="registration-evidence__head"><div>
        <h3 id="registration-evidence-title">Minh chứng theo yêu cầu của giảng viên</h3>
        <p>Ví dụ: bảng điểm hoặc chứng chỉ. Không bắt buộc nếu đề tài không yêu cầu.</p>
      </div><span className="registration-evidence__optional">Tùy chọn</span></div>
      <label className="input-group" htmlFor="registration-evidence-file">Tệp minh chứng
        <input id="registration-evidence-file" className="input" type="file" accept=".pdf,.png,.jpg,.jpeg"
          disabled={busy} onChange={(event) => {chooseEvidence(event.target.files?.[0]); event.target.value = "";}} />
      </label>
      {evidence ? <div className="registration-evidence__selected"><span>{evidence.name}</span>
        <button className="btn btn-secondary btn-sm" type="button" disabled={busy} onClick={() => {setEvidence(null); setEvidenceError("");}}>
          <X size={14} aria-hidden="true" /> Xóa tệp đã chọn
        </button></div> : null}
      {evidenceError ? <p className="alert alert-danger" role="alert">{evidenceError}</p> : null}
      <p className="text-caption text-muted">PDF, PNG hoặc JPEG, tối đa 5 MB. Nếu có nhiều giấy tờ, gộp thành một tệp PDF.</p>
    </section>
    <div className="registration-fieldset__actions">
      <button type="button" className="btn btn-primary registration-fieldset__submit"
        disabled={busy || disabled || !!evidenceError || !consent || !eligibility?.eligible || eligibility.has_active_registration}
        onClick={() => void onSubmit(evidence || undefined)}>{busy ? "Đang lưu…" : joining ? "Tham gia đề tài" : "Lập đăng ký của tôi"}</button>
    </div>
  </fieldset>;
}
