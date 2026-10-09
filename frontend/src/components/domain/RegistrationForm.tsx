import { useEffect, useState } from "react";
import type { Context } from "../../api";
import { request } from "../../api";
import { errorMessage } from "../../errors";

export default function RegistrationForm({ context, userId, roundId, busy, disabled = false, onSubmit, joining = false }: {
  context: Context; userId: string; roundId: string; capacity?: number; busy: boolean;
  onSubmit: () => Promise<void>; disabled?: boolean; joining?: boolean;
}) {
  const [consent, setConsent] = useState(false);
  const [eligibility, setEligibility] = useState<{eligible: boolean; has_active_registration: boolean} | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    request<typeof eligibility>("/me/eligibility?round_id=" + roundId, userId)
      .then((result) => { if (alive) setEligibility(result); })
      .catch((cause) => { if (alive) setError(errorMessage(cause)); });
    return () => { alive = false; };
  }, [roundId, userId]);
  return <fieldset className="registration-fieldset stack" disabled={busy}>
    <legend>Thông tin đăng ký của tôi</legend>
    <div className="grid grid-auto">
      <label>Họ tên<input className="input" readOnly value={context.display_name} /></label>
      <label>MSSV<input className="input" readOnly value={context.student_code || ""} /></label>
      <label>Email<input className="input" readOnly value={context.email || ""} /></label>
    </div>
    <p className="text-body-sm">Bạn tự đăng ký bằng tài khoản của mình. Các bạn khác cũng tự đăng nhập và tham gia khi đề tài còn chỗ.</p>
    <label className="consent-label"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> Tôi xác nhận tham gia đề tài và thông tin đăng ký của mình.</label>
    {!eligibility && !error ? <p role="status">Đang kiểm tra điều kiện đăng ký…</p> : null}
    {eligibility && !eligibility.eligible ? <p className="alert alert-warning">Bạn chưa được xác nhận đủ điều kiện ở đợt này. Liên hệ người phụ trách của Khoa.</p> : null}
    {eligibility?.has_active_registration ? <p className="alert alert-warning">Bạn đã có đăng ký đang hoạt động trong đợt. Mở mục Đăng ký để xem.</p> : null}
    {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
    <p className="text-caption">Có thể bổ sung minh chứng PDF/ảnh tại mục Đăng ký trước khi gửi cho GV. GV xét mức phù hợp; không bắt buộc đủ số SV tối đa.</p>
    <button type="button" className="btn btn-primary"
      disabled={busy || disabled || !consent || !eligibility?.eligible || eligibility.has_active_registration}
      onClick={() => void onSubmit()}>{busy ? "Đang lưu…" : joining ? "Tham gia đề tài" : "Lập đăng ký của tôi"}</button>
  </fieldset>;
}
