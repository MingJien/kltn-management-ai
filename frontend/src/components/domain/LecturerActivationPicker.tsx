import { useEffect, useState } from "react";
import { RefreshCw, Send } from "lucide-react";
import { request } from "../../api";
import { errorMessage } from "../../errors";

type Lecturer = { user_id: string; lecturer_code: string; display_name: string; email: string; can_send: boolean };
type Directory = { items: Lecturer[]; mail_ready: boolean };
const fold = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[đĐ]/g, "d").toLowerCase().trim();

export default function LecturerActivationPicker({ userId }: { userId: string }) {
  const [directory, setDirectory] = useState<Directory | null>(null);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    setBusy(true); setError("");
    try {
      const result = await request<Directory>("/admin/lecturers", userId);
      setDirectory(result);
      setSelectedId(id => result.items.some(row => row.user_id === id && row.can_send) ? id : "");
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, [userId]);

  const matches = (directory?.items || []).filter(row => row.can_send && fold(`${row.display_name} ${row.lecturer_code} ${row.email}`).includes(fold(query)));
  const selected = matches.find(row => row.user_id === selectedId);

  async function send() {
    if (!selected || busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await request<{sent: boolean; delivery_mode: string}>(`/admin/lecturers/${selected.user_id}/activation-link`, userId, {method: "POST"});
      setSelectedId("");
      if (!result.sent) setError("Chưa gửi được liên kết. Vui lòng kiểm tra dịch vụ thư và thử lại sau 60 giây.");
      else if (result.delivery_mode === "smtp") setNotice(`Máy chủ thư đã tiếp nhận liên kết kích hoạt gửi cho ${selected.display_name} qua ${selected.email}.`);
      else setNotice("Đã lưu liên kết vào hộp thư thử nghiệm; chưa gửi đến email thật.");
      try { setDirectory(await request<Directory>("/admin/lecturers", userId)); }
      catch { setError("Đã xử lý yêu cầu gửi nhưng chưa làm mới được danh sách. Vui lòng bấm Làm mới."); }
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }

  return <form className="stack" onSubmit={event => {event.preventDefault(); void send();}}>
    <p className="text-caption">Chọn giảng viên đã có tài khoản và đang chờ kích hoạt. Để tạo tài khoản mới, chọn tab bên cạnh.</p>
    <div className="input-group">
      <span id="invite-existing-label">Giảng viên nhận liên kết</span>
      <div className="roster-student-picker__controls staff-picker" role="group" aria-labelledby="invite-existing-label">
        <input className="input" aria-label="Tìm giảng viên theo tên hoặc mã" placeholder="Nhập tên hoặc mã GV" value={query} maxLength={100} disabled={busy} onChange={event => {setQuery(event.target.value); setSelectedId("");}} />
        <select className="input" aria-label="Chọn email giảng viên" value={selectedId} required disabled={busy || !matches.length} onChange={event => setSelectedId(event.target.value)}>
          <option value="">{matches.length ? "Chọn email phù hợp" : "Không có tài khoản phù hợp"}</option>
          {matches.map(row => <option key={row.user_id} value={row.user_id}>{row.email} · {row.lecturer_code} · {row.display_name}</option>)}
        </select>
      </div>
      <span className="text-caption">{matches.length} tài khoản có thể gửi. Người vừa được gửi cần chờ 60 giây; tài khoản đã kích hoạt hoặc bị khóa không có trong danh sách.</span>
    </div>
    {selected && <p className="text-caption">Người nhận: <strong>{selected.display_name}</strong> · {selected.email}</p>}
    {directory && !directory.mail_ready && <p className="alert alert-warning">Dịch vụ gửi thư chưa sẵn sàng.</p>}
    {error && <p role="alert" className="alert alert-danger">{error}</p>}
    {notice && <p role="status" className="alert alert-success">{notice}</p>}
    <div className="lecturer-invite-actions">
      <button className="btn btn-secondary" type="button" disabled={busy} onClick={() => void load()}><RefreshCw size={16} aria-hidden="true" /> Làm mới</button>
      <button className="btn btn-primary" type="submit" disabled={busy || !selected || !directory?.mail_ready}><Send size={16} aria-hidden="true" /> Gửi liên kết kích hoạt</button>
    </div>
  </form>;
}
