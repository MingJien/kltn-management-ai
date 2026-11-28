import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { BookOpen, FileText, GraduationCap, LogIn, ShieldCheck } from "lucide-react";
import { listDemoAccounts, type DemoAccount } from "../api";
import PasswordField from "../components/ui/PasswordField";
import { LoginCampusArt } from "../components/ui/CampusArtwork";
import "../styles/login.css";

interface LoginPageProps {
  email: string;
  password: string;
  loading: boolean;
  error: string;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: () => void;
  onDemoSignIn: (key: string) => void;
}

const FEATURES = [
  { icon: GraduationCap, title: "Quản lý đề tài", description: "Đăng ký, xét duyệt và phân công hướng dẫn" },
  { icon: BookOpen, title: "Theo dõi tiến độ", description: "Đề cương, bản thảo và nhận xét theo phiên bản" },
  { icon: FileText, title: "Hồ sơ & bảo vệ", description: "Phản biện, hội đồng, điểm số và kho lưu trữ nội bộ" },
  { icon: ShieldCheck, title: "Minh bạch & Truy vết", description: "Lịch sử thao tác, phân quyền theo vai trò và đợt" },
];

export default function LoginPage({
  email, password, loading, error, onEmailChange, onPasswordChange, onSubmit, onDemoSignIn,
}: LoginPageProps) {
  const [demoAccounts, setDemoAccounts] = useState<DemoAccount[]>([]);
  const [demoKey, setDemoKey] = useState("");

  useEffect(() => {
    let mounted = true;
    void listDemoAccounts().then((accounts) => {
      if (!mounted) return;
      setDemoAccounts(accounts);
      setDemoKey(accounts[0]?.key ?? "");
    }).catch(() => { /* Demo mode is optional; normal email sign-in remains available. */ });
    return () => { mounted = false; };
  }, []);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <main className="login-page">
      <section className="login-page__left" aria-label="Giới thiệu hệ thống">
        <div className="login-brand">
          <LoginCampusArt className="login-brand__artwork" />

          <div className="login-brand__content">
            <div className="login-brand__crest-row">
              <img className="login-brand__logo" src="/assets/dthu-logo.png" alt="" />
              <div className="login-brand__university">
                <span>Trường Đại học Đồng Tháp</span>
                <strong>Khoa Công nghệ và Kỹ thuật</strong>
              </div>
            </div>
            <h2 className="login-brand__title">Hệ thống Quản lý<br />Khóa luận Tốt nghiệp</h2>
            <p className="login-brand__subtitle">Nền tảng điều phối học thuật và lưu trữ hồ sơ khóa luận thống nhất theo từng đợt.</p>

            <div className="login-brand__features">
              {FEATURES.map(({ icon: Icon, title, description }) => (
                <div className="login-brand__feature" key={title}>
                  <div className="login-brand__feature-icon"><Icon size={18} aria-hidden="true" /></div>
                  <div><strong>{title}</strong><span>{description}</span></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="login-page__right" aria-label="Đăng nhập">
        <div className="login-card-wrapper">
          <div className="login-card">
            <div className="login-card__header">
              <div className="login-card__emblem-row">
                <img className="login-card__logo" src="/assets/dthu-logo.png" alt="Logo Đại học Đồng Tháp" />
                <div className="login-card__school">
                  <span>DThU · KLTN</span>
                  <small>Khoa Công nghệ và Kỹ thuật</small>
                </div>
              </div>
              <h1>Đăng nhập hệ thống</h1>
              <p>Sử dụng tài khoản được cấp để truy cập</p>
            </div>

            <form className="login-card__form" onSubmit={submit}>
              <div className="input-group">
                <label htmlFor="login-email">Email</label>
                <input id="login-email" className="input input--lg" type="email" required
                  autoComplete="username" value={email}
                  onChange={(event) => onEmailChange(event.target.value)}
                  placeholder="email@dthu.edu.vn" autoFocus />
              </div>
              <div className="input-group">
                <label htmlFor="login-password">Mật khẩu</label>
                <PasswordField
                  id="login-password"
                  className="input input--lg"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => onPasswordChange(event.target.value)}
                  placeholder="Nhập mật khẩu"
                />
              </div>
              <button className="btn btn-primary login-card__submit"
                disabled={loading || !email.trim() || !password}>
                {loading ? <><span className="login-spinner login-spinner--sm" />Đang đăng nhập…</>
                  : <><LogIn size={16} aria-hidden="true" />Đăng nhập</>}
              </button>
            </form>

            <div className="account-entry__links">
              <Link to="/account/activation-request">Kích hoạt tài khoản</Link>
              <Link to="/account/forgot-password">Quên mật khẩu?</Link>
            </div>

            {error && <div className="alert alert-danger mt-4" role="alert">{error}</div>}

            {demoAccounts.length > 0 && <section className="login-demo" aria-labelledby="login-demo-heading">
              <span className="login-demo__kicker">Môi trường thử nghiệm</span>
              <h3 id="login-demo-heading">Dùng tài khoản demo</h3>
              <p>Chọn vai trò giả lập để thử chức năng trên máy này.</p>
              <label htmlFor="login-demo-account">Tài khoản thử nghiệm</label>
              <select id="login-demo-account" className="input" value={demoKey}
                onChange={(event) => setDemoKey(event.target.value)}>
                {demoAccounts.map((account) => <option key={account.key} value={account.key}>
                  {account.label} · {account.email}
                </option>)}
              </select>
              <button type="button" className="btn btn-soft login-demo__submit"
                disabled={loading || !demoKey} onClick={() => onDemoSignIn(demoKey)}>
                <LogIn size={15} aria-hidden="true" />
                {loading ? "Đang mở…" : "Vào bản demo"}
              </button>
            </section>}
          </div>

          <footer className="login-footer">
            <p>© 2026 Khoa Công nghệ và Kỹ thuật — Trường Đại học Đồng Tháp</p>
          </footer>
        </div>
      </section>
    </main>
  );
}
