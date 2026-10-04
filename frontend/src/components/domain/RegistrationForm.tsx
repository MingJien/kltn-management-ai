import { useEffect, useState } from "react";
import type { Context, EligibleStudent } from "../../api";
import { request } from "../../api";
export default function RegistrationForm({context, userId, roundId, capacity, busy, disabled = false, onSubmit}: {
  context: Context; userId: string; roundId: string; capacity: number; busy: boolean;
  onSubmit: (members: string[]) => Promise<void>;
  disabled?: boolean;
}) {
  const [mode, setMode] = useState("individual");
  const [students, setStudents] = useState<EligibleStudent[]>([]);
  const [members, setMembers] = useState<string[]>(context.student_id ? [context.student_id] : []);
  const [consent, setConsent] = useState(false);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    request<EligibleStudent[]>(`/eligible-students?round_id=${roundId}`, userId).then((rows) => {if (alive) setStudents(rows);}).catch((e) => {if (alive) setError(String(e));});
    return () => {alive = false;};
  }, [roundId, userId]);
  const me = students.find((s) => s.id === context.student_id);
  return <fieldset className="registration-fieldset stack"><legend>Thông tin đăng ký</legend>
    <div className="flex gap-3"><label><input type="radio" checked={mode === "individual"} name="registration-mode" onChange={() => {setMode("individual"); setMembers(context.student_id ? [context.student_id] : []);}}/> Cá nhân</label>
      {capacity > 1 ? <label><input type="radio" checked={mode === "group"} name="registration-mode" onChange={() => setMode("group")}/> Nhóm ({capacity === 2 ? "2" : "2–3"} SV)</label> : null}</div>
    <div className="grid grid-auto"><label>Họ tên<input className="input" readOnly value={context.display_name}/></label><label>MSSV<input className="input" readOnly value={context.student_code || ""}/></label><label>Email<input className="input" readOnly value={context.email || ""}/></label></div>
    <p className="text-body-sm">Thông tin lấy từ hồ sơ. {mode === "group" ? "Bạn là đại diện lập nhóm; từng bạn được mời phải đăng nhập tài khoản riêng để xác nhận." : "Đăng ký cho chính tài khoản của bạn."}</p>
    {mode === "group" ? <><label>Tìm thành viên theo tên hoặc MSSV<input className="input" value={filter} onChange={(e) => setFilter(e.target.value)}/></label><p>Đã chọn {members.length}/{capacity} sinh viên</p>
      <div className="member-picker">{students.filter((s) => s.id !== context.student_id && (!filter || `${s.display_name} ${s.student_code}`.toLocaleLowerCase().includes(filter.toLocaleLowerCase()) || members.includes(s.id))).map((s) => <label key={s.id}>
        <input type="checkbox" checked={members.includes(s.id)} disabled={busy || (!members.includes(s.id) && members.length >= capacity)} onChange={(e) => setMembers(e.target.checked ? [...members, s.id] : members.filter((id) => id !== s.id))}/>
        {s.display_name} <span className="text-caption">{s.student_code}</span></label>)}</div></> : null}
    <label className="consent-label"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)}/> Tôi xác nhận tham gia đề tài và thông tin đăng ký của mình.</label>
    {!me && !error ? <p className="alert alert-warning">Tài khoản chưa có xác nhận đủ điều kiện ở đợt này.</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    <p className="text-caption">Lập đăng ký xong, tải minh chứng PDF/ảnh ở trang Đăng ký trước khi gửi chính thức.</p>
    <button type="button" className="btn btn-primary" disabled={busy || disabled || !consent || !me || (mode === "group" && members.length < 2)} onClick={() => void onSubmit(members)}>{busy ? "Đang lưu…" : mode === "group" ? "Lập đăng ký nhóm" : "Lập đăng ký cá nhân"}</button>
  </fieldset>;
}
