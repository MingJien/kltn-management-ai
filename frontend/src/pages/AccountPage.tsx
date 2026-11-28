import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { KeyRound, UserRound } from "lucide-react";
import type { Context } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";
import Badge from "../components/ui/Badge";
import PasswordField from "../components/ui/PasswordField";
import LecturerSelfProfile from "../components/domain/LecturerSelfProfile";

export default function AccountPage({context, onPasswordChanged,onProfileChanged}: {context:Context; onPasswordChanged:()=>void;onProfileChanged?:()=>Promise<void>}) {
  const [params] = useSearchParams();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (params.get("section") === "lecturer-profile") {
      document.getElementById("self-lecturer-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [params]);

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
    {context.base_role==="LECTURER"&&<LecturerSelfProfile context={context} onProfileChanged={onProfileChanged}/>}
    <div className="grid grid-auto">
      <section className="card"><div className="card-body stack">
        <h2 className="flex items-center gap-2"><UserRound size={18} className="metric-card__icon" aria-hidden="true" />Thông tin cá nhân</h2>
        <dl className="account-facts-grid">
          <div><dt>Họ tên</dt><dd>{context.display_name}</dd></div>
          <div><dt>Email</dt><dd>{context.email || "Chưa có"}</dd></div>
          {context.student_code ? <div><dt>MSSV</dt><dd><code>{context.student_code}</code></dd></div> : null}
          {context.lecturer_code ? <div><dt>Mã giảng viên</dt><dd><code>{context.lecturer_code}</code></dd></div> : null}
          {context.class_name ? <div><dt>Lớp</dt><dd>{context.class_name}</dd></div> : null}
          {context.department_code ? <div><dt>Bộ môn</dt><dd>{context.department_code} · {context.department_name}</dd></div> : null}
          {context.major_code ? <div><dt>Ngành</dt><dd>{context.major_code}{context.major_name ? ` · ${context.major_name}` : " · Chưa đối chiếu danh mục"}</dd></div> : null}
        </dl>
        <p className="text-muted m-0">Thông tin định danh do Khoa cung cấp; nếu sai, liên hệ người quản lý danh sách.</p>
        {context.base_role === "LECTURER" ? (
          <div className="stack">
            <h3>Vai trò và phân công hiện tại</h3>
            {context.lecturer_duties.length ? (
              <div className="account-item__duties">
                {context.lecturer_duties.map((duty) => (
                  <Badge variant="info" key={duty.code + "-" + (duty.scope || "")}>
                    {duty.label}{duty.scope ? " · " + duty.scope : ""}
                  </Badge>
                ))}
              </div>
            ) : <p className="text-muted m-0">Chưa có quyền bổ sung hoặc phân công KLTN đang hiệu lực.</p>}
          </div>
        ) : null}
      </div></section>
      {context.can_change_password ? <section className="card"><div className="card-body stack">
        <h2 className="flex items-center gap-2"><KeyRound size={18} className="metric-card__icon" aria-hidden="true" />Đổi mật khẩu</h2>
        <form onSubmit={(event)=>void change(event)} className="stack">
          <div className="input-group">
            <label htmlFor="current-password">Mật khẩu hiện tại</label>
            <PasswordField
              id="current-password"
              required
              autoComplete="current-password"
              value={currentPassword}
              onChange={e=>setCurrentPassword(e.target.value)}
              placeholder="Nhập mật khẩu hiện tại"
            />
          </div>
          <div className="input-group">
            <label htmlFor="new-password">Mật khẩu mới</label>
            <PasswordField
              id="new-password"
              required
              minLength={12}
              autoComplete="new-password"
              value={newPassword}
              onChange={e=>setNewPassword(e.target.value)}
              placeholder="Nhập mật khẩu mới (ít nhất 12 ký tự)"
            />
          </div>
          <div className="input-group">
            <label htmlFor="confirm-new-password">Nhập lại mật khẩu mới</label>
            <PasswordField
              id="confirm-new-password"
              required
              minLength={12}
              autoComplete="new-password"
              value={confirm}
              onChange={e=>setConfirm(e.target.value)}
              placeholder="Nhập lại mật khẩu mới"
            />
          </div>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Đang lưu…" : "Đổi mật khẩu"}</button>
        </form>
        {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
      </div></section> : null}
    </div>
  </>;
}
