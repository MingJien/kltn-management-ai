import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { ApiError, errorMessage } from "./errors";
import { Context, emailLogin, logout, request, setDevelopmentAuthEnabled, setSessionCsrfToken } from "./api";
import AppShell from "./components/layout/AppShell";
import WorkspacePage from "./pages/WorkspacePage";
import TopicsPage from "./pages/TopicsPage";
import RegistrationsPage from "./pages/RegistrationsPage";
import ThesisViewPage from "./pages/ThesisViewPage";
const AIPage = lazy(() => import("./pages/AIPage"));
import { Eye, EyeOff, LogIn } from "lucide-react";

function App() {
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [context, setContext] = useState<Context | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(true);
  useEffect(() => {
    const labels: Record<string,string> = {"/":"Tổng quan", "/topics":"Đề tài", "/registrations":"Đăng ký", "/ai":"Tra cứu thử nghiệm"};
    document.title = `${context ? labels[location.pathname] || "Khóa luận" : "Đăng nhập"} · KLTN`;
  }, [location.pathname, context]);

  const restore = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const result = await request<Context>("/me/context", "");
      setSessionCsrfToken(result.csrf_token);
      setContext(result);
    } catch (cause) {
      setSessionCsrfToken(null);
      setContext(null);
      if (cause instanceof ApiError && cause.status === 401) setError("");
      else setError(errorMessage(cause));
    } finally {
      setLoading(false);
      setRestoring(false);
    }
  }, []);

  useEffect(() => {
    setDevelopmentAuthEnabled(false);
    void restore();
    const expired = () => {setSessionCsrfToken(null); setContext(null); setPassword(""); setError("Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.");};
    window.addEventListener("kltn:session-expired", expired);
    return () => window.removeEventListener("kltn:session-expired", expired);
  }, [restore]);

  async function signIn() {
    if (loading) return;
    setError("");
    setLoading(true);
    try {
      await emailLogin(email, password);
      setPassword("");
      const result = await request<Context>("/me/context", "");
      setSessionCsrfToken(result.csrf_token);
      setContext(result);
    } catch (cause) {
      setPassword("");
      setError(errorMessage(cause));
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    try { await logout(); setSessionCsrfToken(null); setContext(null); setPassword(""); }
    catch (cause) { setError(errorMessage(cause)); }
  }

  if (restoring) return <div className="session-loading" role="status">Đang kiểm tra phiên đăng nhập…</div>;

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
                Dùng tài khoản KLTN đã được cấp quyền.
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
                    required
                    autoComplete="username"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="Nhập email đăng nhập"
                    autoFocus
                  />
                </div>
                <div className="input-group" style={{ marginBottom: "var(--space-4)" }}>
                  <label htmlFor="login-password">Mật khẩu</label>
                  <div className="login-password-field">
                    <input id="login-password" className="input" type={showPassword ? "text" : "password"} required
                      autoComplete="current-password" value={password}
                      onChange={(event) => setPassword(event.target.value)} />
                    <button type="button" className="login-password-toggle"
                      aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                      aria-pressed={showPassword} onClick={() => setShowPassword((visible) => !visible)}>
                      {showPassword ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
                    </button>
                  </div>
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

          {import.meta.env.DEV ? <p
            className="text-caption text-muted"
            style={{ textAlign: "center", marginTop: "var(--space-4)" }}
          >
            Bản thử nghiệm · Chỉ dùng tài khoản giả lập trong môi trường phát triển.
          </p> : null}
        </div>
      </div>
    );
  }

  // Connected — show app shell with routes
  const workflowAccess = context.base_role === "STUDENT" || context.base_role === "LECTURER";
  return (
    <AppShell context={context} onLogout={() => void signOut()}>
      {error ? <p role="alert" className="alert alert-danger">{error}</p> : null}
      <Suspense fallback={<p role="status">Đang tải trang…</p>}><Routes>
        <Route
          path="/"
          element={<WorkspacePage context={context} />}
        />
        <Route
          path="/topics"
          element={workflowAccess ?
            <TopicsPage userId={context.user_id} context={context} />
            : <Navigate to="/" replace />}
        />
        <Route
          path="/registrations"
          element={workflowAccess ?
            <RegistrationsPage userId={context.user_id} context={context} />
            : <Navigate to="/" replace />}
        />
        <Route
          path="/ai"
          element={workflowAccess ? <AIPage userId={context.user_id} /> : <Navigate to="/" replace />}
        />
        <Route
          path="/theses/:thesisId"
          element={workflowAccess ? <ThesisViewPage userId={context.user_id} /> : <Navigate to="/" replace />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes></Suspense>
    </AppShell>
  );
}

export default App;
