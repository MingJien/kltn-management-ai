import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { errorMessage } from "../errors";
import { request } from "../api";
import PasswordInput from "../components/ui/PasswordInput";

type Mode = "activation-request" | "forgot-password" | "activate" | "reset-password";

export default function AccountAccessPage({signedInAs, onPasswordUpdated}: {
  signedInAs: string | null; onPasswordUpdated?: () => Promise<void>;
}) {
  const location = useLocation();
  const mode = location.pathname.split("/").at(-1) as Mode;
  const [token] = useState(() => new URLSearchParams(location.search).get("token") || "");
  const [identifier, setIdentifier] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const settingPassword = mode === "activate" || mode === "reset-password";
  const title = ({"activation-request":"Kích hoạt tài khoản", "forgot-password":"Quên mật khẩu",
    "activate":"Tạo mật khẩu", "reset-password":"Đặt lại mật khẩu"})[mode] || "Tài khoản";

  useEffect(() => {
    document.title = `${title} · KLTN`;
    if (settingPassword && location.search) window.history.replaceState({}, "", location.pathname);
  }, [title, settingPassword, location.pathname, location.search]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (settingPassword && password !== confirm) { setError("Hai mật khẩu không khớp."); return; }
    setBusy(true); setError(""); setNotice("");
    try {
      if (mode === "activation-request") {
        await request("/account/activation-request", "", {method:"POST", body:JSON.stringify({identifier, email})});
      } else if (mode === "forgot-password") {
        await request("/account/password-reset-request", "", {method:"POST", body:JSON.stringify({email})});
      } else {
        await request(mode === "activate" ? "/account/activate" : "/account/password-reset", "",
          {method:"POST", body:JSON.stringify({token, password})});
        setPassword(""); setConfirm("");
        if (onPasswordUpdated) await onPasswordUpdated();
      }
      setNotice(settingPassword ? "Đã cập nhật mật khẩu. Bạn có thể đăng nhập." :
        "Nếu thông tin hợp lệ, hướng dẫn sẽ được gửi tới email đã đăng ký.");
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }

  return <div className="account-entry"><div className="card account-entry__card"><div className="card-body stack">
    <div className="sidebar__brand-mark" aria-hidden="true">K</div>
    <h1>{title}</h1>
    <p className="text-muted">{settingPassword ? "Liên kết chỉ có hiệu lực một lần. Mật khẩu cần ít nhất 12 ký tự." :
      mode === "activation-request" ? "Chỉ tài khoản trong danh sách đã được Khoa xác nhận mới được kích hoạt." :
        "Nhập email đã đăng ký để nhận hướng dẫn đặt lại mật khẩu."}</p>
    {settingPassword && signedInAs ? <p className="alert">Bạn đang đăng nhập với tài khoản {signedInAs}. Sau khi lưu mật khẩu, hệ thống sẽ đăng xuất tài khoản này để bạn đăng nhập tài khoản vừa kích hoạt.</p> : null}
    <form onSubmit={(event) => void submit(event)} className="stack">
      {mode === "activation-request" ? <label className="input-group">MSSV hoặc mã giảng viên
        <input className="input" required maxLength={32} value={identifier} onChange={e=>setIdentifier(e.target.value)} />
      </label> : null}
      {!settingPassword ? <label className="input-group">Email đã đăng ký
        <input className="input" type="email" required autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} />
      </label> : null}
      {settingPassword ? <>
        <div className="input-group"><label htmlFor="account-access-password">Mật khẩu mới</label>
          <PasswordInput id="account-access-password" label="Mật khẩu mới" minLength={12} required autoComplete="new-password"
            value={password} onChange={e=>setPassword(e.target.value)} disabled={busy} />
        </div>
        <div className="input-group"><label htmlFor="account-access-confirm">Nhập lại mật khẩu</label>
          <PasswordInput id="account-access-confirm" label="Nhập lại mật khẩu" minLength={12} required autoComplete="new-password"
            value={confirm} onChange={e=>setConfirm(e.target.value)} disabled={busy} />
        </div>
      </> : null}
      {settingPassword && !token ? <p role="alert" className="alert alert-danger">Liên kết không hợp lệ hoặc đã được sử dụng.</p> : null}
      <button className="btn btn-primary" disabled={busy || (settingPassword && !token)}>
        {busy ? "Đang xử lý…" : settingPassword ? "Lưu mật khẩu" : "Gửi hướng dẫn"}
      </button>
    </form>
    {notice ? <p role="status" className="alert alert-success">{notice}</p> : null}
    {error ? <p role="alert" className="alert alert-danger">{error}</p> : null}
    <Link to="/">Quay lại đăng nhập</Link>
  </div></div></div>;
}
