import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Context, emailLogin, logout, request, setDevelopmentAuthEnabled } from "./api";
import AppShell from "./components/layout/AppShell";
import WorkspacePage from "./pages/WorkspacePage";
import TopicsPage from "./pages/TopicsPage";
import RegistrationsPage from "./pages/RegistrationsPage";
import ThesisViewPage from "./pages/ThesisViewPage";
import AIPage from "./pages/AIPage";
import PlaceholderPage from "./pages/PlaceholderPage";
import { LogIn } from "lucide-react";

function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [context, setContext] = useState<Context | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const restore = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const result = await request<Context>("/me/context", "");
      setContext(result);
    } catch (cause) {
      setContext(null);
      if (/Sign in required|Missing development identity|401/.test(String(cause))) setError("");
      else setError(String(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setDevelopmentAuthEnabled(false);
    void restore();
  }, []); // initial session restore only

  async function signIn() {
    setError("");
    setLoading(true);
    try {
      await emailLogin(email, password);
      setPassword("");
      setContext(await request<Context>("/me/context", ""));
    } catch (cause) {
      setError(String(cause));
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    try { await logout(); } finally { setContext(null); }
  }

  // Not connected — show login card
  if (!context) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ minHeight: "100dvh", background: "var(--neutral-50)" }}
      >
        <div style={{ width: "100%", maxWidth: 420, padding: "var(--space-4)" }}>
          {/* Brand */}
          <div
            className="flex items-center justify-center gap-3"
            style={{ marginBottom: "var(--space-8)" }}
          >
            <div
              className="sidebar__brand-mark"
              style={{ width: 48, height: 48, fontSize: 24 }}
            >
              K
            </div>
            <div>
              <div style={{ font: "var(--text-h1)", color: "var(--neutral-900)" }}>
                KLTN
              </div>
              <div className="text-body-sm text-muted">
                Hệ thống Quản lý Khóa luận
              </div>
            </div>
          </div>

          {/* Login card */}
          <div className="card">
            <div className="card-body">
              <h2 style={{ marginBottom: "var(--space-1)" }}>Đăng nhập</h2>
              <p
                className="text-body-sm text-muted"
                style={{ marginBottom: "var(--space-5)" }}
              >
                Dùng tài khoản đã được cấp. Bản thử nghiệm dùng email giả lập trong kltn_dev.
              </p>

              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void signIn();
                }}
              >
                <div
                  className="input-group"
                  style={{ marginBottom: "var(--space-4)" }}
                >
                  <label htmlFor="login-email">Email</label>
                  <input
                    id="login-email"
                    className="input"
                    type="email"
                    autoComplete="username"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="sv1@demo.test"
                    autoFocus
                  />
                </div>
                <div className="input-group" style={{ marginBottom: "var(--space-4)" }}>
                  <label htmlFor="login-password">Mật khẩu</label>
                  <input id="login-password" className="input" type="password"
                    autoComplete="current-password" value={password}
                    onChange={(event) => setPassword(event.target.value)} />
                </div>
                <button
                  className="btn btn-primary"
                  disabled={loading || !email.trim() || !password}
                  style={{ width: "100%" }}
                >
                  <LogIn size={16} />
                  {loading ? "Đang đăng nhập…" : "Đăng nhập"}
                </button>
              </form>

              {error && (
                <div
                  className="alert alert-danger"
                  role="alert"
                  style={{ marginTop: "var(--space-4)" }}
                >
                  {error}
                </div>
              )}
            </div>
          </div>

          <p
            className="text-caption text-muted"
            style={{ textAlign: "center", marginTop: "var(--space-4)" }}
          >
            Giao diện thử nghiệm · Chỉ dùng tài khoản giả lập trong môi trường phát triển.
          </p>
        </div>
      </div>
    );
  }

  // Connected — show app shell with routes
  return (
    <AppShell context={context} onLogout={() => void signOut()}>
      <Routes>
        <Route
          path="/"
          element={<WorkspacePage context={context} />}
        />
        <Route
          path="/topics"
          element={
            <TopicsPage userId={context.user_id} context={context} />
          }
        />
        <Route
          path="/registrations"
          element={
            <RegistrationsPage userId={context.user_id} context={context} />
          }
        />
        <Route
          path="/ai"
          element={<AIPage userId={context.user_id} />}
        />
        <Route
          path="/theses/:thesisId"
          element={<ThesisViewPage userId={context.user_id} />}
        />

        {/* Placeholder routes — Phase 2+ */}
        <Route path="/rounds" element={<PlaceholderPage title="Đợt & Năm học" description="Quản lý đợt KLTN và policy theo năm học" />} />
        <Route path="/eligibility" element={<PlaceholderPage title="Điều kiện SV" description="Snapshot tín chỉ/GPA và xác nhận theo đợt" />} />
        <Route path="/proposals" element={<PlaceholderPage title="Đề cương" description="Timeline version/review đề cương" />} />
        <Route path="/progress" element={<PlaceholderPage title="Tiến độ" description="Milestone, report/review, thay đổi" />} />
        <Route path="/documents" element={<PlaceholderPage title="Tài liệu" description="Upload tài liệu, version history, kiểm tra tương đồng" />} />
        <Route path="/councils" element={<PlaceholderPage title="Hội đồng & Phiên" description="Hội đồng bảo vệ và phiên chấm" />} />
        <Route path="/reviews" element={<PlaceholderPage title="Nhận xét" description="Nhận xét GVHD/GVPB theo Mẫu 7/8" />} />
        <Route path="/scoring" element={<PlaceholderPage title="Chấm điểm" description="Rubric theo Mẫu 6, điểm cá nhân" />} />
        <Route path="/minutes" element={<PlaceholderPage title="Biên bản" description="Biên bản bảo vệ Mẫu 9" />} />
        <Route path="/archive" element={<PlaceholderPage title="Kho & Báo cáo" description="Tìm kiếm và tra cứu tài liệu kho" />} />
        <Route path="/similarity" element={<PlaceholderPage title="Tìm tương đồng" description="Tìm đề tài tương đồng trong kho" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

export default App;
