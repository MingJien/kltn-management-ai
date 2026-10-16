import { useState } from "react";
import type { Context } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";

export default function AccountPage({context, onPasswordChanged}: {context:Context; onPasswordChanged:()=>void}) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function change(event: React.FormEvent) {
    event.preventDefault();
    if (newPassword !== confirm) {setError("Hai mật khẩu không khớp."); return;}
    setBusy(true); setError("");
    try {
      await request("/account/password-change", context.user_id, {method:"POST",
        body:JSON.stringify({current_password:currentPassword, new_password:newPassword})});
      onPasswordChanged();
    } catch (cause) {setError(errorMessage(cause));}
    finally {setBusy(false); setCurrentPassword(""); setNewPassword(""); setConfirm("");}
  }
  return <><PageHeader title="Tài khoản của tôi" description="Thông tin định danh và bảo vệ tài khoản" />
    <div className="grid grid-auto">
      <section className="card"><div className="card-body stack"><h2>Thông tin cá nhân</h2>
        <p><strong>Họ tên:</strong> {context.display_name}</p>
        <p><strong>Email:</strong> {context.email || "Chưa có"}</p>
        {context.student_code ? <p><strong>MSSV:</strong> {context.student_code}</p> : null}
        {context.lecturer_code ? <p><strong>Mã giảng viên:</strong> {context.lecturer_code}</p> : null}
        {context.class_name ? <p><strong>Lớp:</strong> {context.class_name}</p> : null}
        {context.major_code ? <p><strong>Mã ngành:</strong> {context.major_code}</p> : null}
        <p className="text-muted">Thông tin định danh do Khoa cung cấp; nếu sai, liên hệ người quản lý danh sách.</p>
      </div></section>
      {context.can_change_password ? <section className="card"><div className="card-body stack"><h2>Đổi mật khẩu</h2>
        <form onSubmit={(event)=>void change(event)} className="stack">
          <label className="input-group">Mật khẩu hiện tại<input className="input" type="password" required autoComplete="current-password"
            value={currentPassword} onChange={e=>setCurrentPassword(e.target.value)} /></label>
          <label className="input-group">Mật khẩu mới<input className="input" type="password" required minLength={12} autoComplete="new-password"
            value={newPassword} onChange={e=>setNewPassword(e.target.value)} /></label>
          <label className="input-group">Nhập lại mật khẩu mới<input className="input" type="password" required minLength={12} autoComplete="new-password"
            value={confirm} onChange={e=>setConfirm(e.target.value)} /></label>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Đang lưu…" : "Đổi mật khẩu"}</button>
        </form>
        {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
      </div></section> : null}
    </div>
  </>;
}
