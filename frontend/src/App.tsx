import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { ApiError, errorMessage } from "./errors";
import { Context, demoLogin, emailLogin, logout, request, setSessionCsrfToken } from "./api";
import AppShell from "./components/layout/AppShell";
import WorkspacePage from "./pages/WorkspacePage";
import TopicsPage from "./pages/TopicsPage";
import RegistrationsPage from "./pages/RegistrationsPage";
import ThesisViewPage from "./pages/ThesisViewPage";
import AccountAccessPage from "./pages/AccountAccessPage";
import AccountPage from "./pages/AccountPage";
import NotificationsPage from "./pages/NotificationsPage";
import ActivityPage from "./pages/ActivityPage";
import SchoolFormsPage from "./pages/SchoolFormsPage";
import AdministrationPage from "./pages/AdministrationPage";
import LecturersPage from "./pages/LecturersPage";
import RosterPage from "./pages/RosterPage";
import RoundsPage from "./pages/RoundsPage";
import LecturerProfilePage from "./pages/LecturerProfilePage";
import ThesesPage from "./pages/ThesesPage";
import SubmissionsPage from "./pages/SubmissionsPage";
import ComingSoonPage from "./pages/ComingSoonPage";
import LoginPage from "./pages/LoginPage";
const EvaluationsPage = lazy(() => import("./pages/EvaluationsPage"));
const EvaluationPage = lazy(() => import("./pages/EvaluationPage"));
import { plannedPages, type PlannedPageId } from "./plannedPages";
const AIPage = lazy(() => import("./pages/AIPage"));

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [context, setContext] = useState<Context | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(true);
  const [noticeRevision,setNoticeRevision] = useState("");
  useEffect(() => {
    const labels: Record<string,string> = {"/":"Tổng quan", "/topics":"Đề tài", "/registrations":"Đăng ký", "/theses":"Khóa luận & GVHD", "/proposals":"Đề cương", "/progress":"Tiến độ", "/documents":"Tài liệu", "/ai":"Tra cứu thử nghiệm", "/notifications":"Thông báo"};
    labels["/forms"] = "Kho biểu mẫu & tài liệu Khoa";
    labels["/submissions"] = "Hồ sơ nộp & xét duyệt";
    labels["/activity"] = "Nhật ký hoạt động";
    const plannedId = location.pathname.startsWith("/planned/") ? location.pathname.slice("/planned/".length) : "";
    const page = location.pathname.startsWith("/lecturers/") ? "Hồ sơ giảng viên"
      : plannedId && Object.hasOwn(plannedPages, plannedId) ? plannedPages[plannedId as PlannedPageId].title
      : labels[location.pathname] || "Khóa luận";
    document.title = `${context ? page : "Đăng nhập"} · KLTN`;
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
    void restore();
    const expired = () => {setSessionCsrfToken(null); setContext(null); setPassword(""); setError("Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.");};
    window.addEventListener("kltn:session-expired", expired);
    return () => window.removeEventListener("kltn:session-expired", expired);
  }, [restore]);

  useEffect(() => {
    if (!location.state?.noticeId) return;
    setNoticeRevision(location.key);
    void restore();
  },[location.key,location.state,restore]);

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

  async function signInDemo(key: string) {
    if (loading) return;
    setError("");
    setLoading(true);
    try {
      await demoLogin(key);
      const result = await request<Context>("/me/context", "");
      setSessionCsrfToken(result.csrf_token);
      setContext(result);
    } catch (cause) {
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

  // An email link must work even when this browser still has another user's session.
  if (["/account/activation-request", "/account/forgot-password",
    "/account/activate", "/account/reset-password"].includes(location.pathname)) return <AccountAccessPage
      signedInAs={context?.display_name || null}
      onPasswordUpdated={context ? signOut : undefined} />;

  // Not connected — show the branded login screen.
  if (!context) {
    return <LoginPage email={email} password={password} loading={loading} error={error}
      onEmailChange={setEmail} onPasswordChange={setPassword} onSubmit={() => void signIn()}
      onDemoSignIn={(key) => void signInDemo(key)} />;
  }

  // Connected — show app shell with routes
  const workflowAccess = context.base_role === "STUDENT" || context.base_role === "LECTURER";
  return (
    <AppShell context={context} onLogout={() => void signOut()}>
      {error ? <p role="alert" className="alert alert-danger">{error}</p> : null}
      <Suspense fallback={<p role="status">Đang tải trang…</p>}><Routes key={noticeRevision}>
        <Route
          path="/"
          element={<WorkspacePage context={context} />}
        />
        <Route path="/account" element={<AccountPage context={context} onPasswordChanged={() => {
          setSessionCsrfToken(null); setContext(null); setError("Mật khẩu đã đổi. Vui lòng đăng nhập lại."); navigate("/");
        }} />} />
        <Route path="/notifications" element={<NotificationsPage userId={context.user_id} />} />
        <Route path="/activity" element={<ActivityPage context={context} />} />
        <Route path="/administration" element={context.actions.includes("account:manage") ?
          <AdministrationPage context={context} onPermissionsChanged={restore} /> : <Navigate to="/" replace />} />
        <Route path="/lecturers" element={context.base_role === "ADMIN" ? <LecturersPage context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/rounds" element={context.base_role === "ADMIN" ?
          <RoundsPage context={context} /> : <Navigate to="/" replace />} />
        <Route path="/roster" element={context.actions.some(a=>a.startsWith("eligibility:")) ?
          <RosterPage context={context} /> : <Navigate to="/" replace />} />
        <Route
          path="/topics"
          element={(workflowAccess || context.base_role === "ADMIN") ?
            <TopicsPage userId={context.user_id} context={context} />
            : <Navigate to="/" replace />}
        />
        <Route
          path="/registrations"
          element={workflowAccess ?
            <RegistrationsPage userId={context.user_id} context={context} />
            : <Navigate to="/" replace />}
        />
        <Route path="/theses" element={workflowAccess ? <ThesesPage context={context} /> : <Navigate to="/" replace />} />
        <Route path="/proposals" element={workflowAccess ? <ThesesPage context={context} section="proposal" /> : <Navigate to="/" replace />} />
        <Route path="/progress" element={workflowAccess ? <ThesesPage context={context} section="progress" /> : <Navigate to="/" replace />} />
        <Route path="/submissions" element={workflowAccess ? <SubmissionsPage key={context.user_id} context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/forms" element={<SchoolFormsPage context={context}/>} />
        <Route path="/documents" element={workflowAccess ? <ThesesPage context={context} section="documents" /> : <Navigate to="/" replace />} />
        <Route path="/evaluation" element={workflowAccess ? <EvaluationsPage context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/evaluation/:thesisId" element={workflowAccess ? <EvaluationPage context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/planned/evaluation" element={<Navigate to="/evaluation" replace/>}/>
        <Route path="/planned/:feature" element={workflowAccess ? <ComingSoonPage /> : <Navigate to="/" replace />} />
        <Route path="/lecturers/:lecturerId" element={workflowAccess ?
          <LecturerProfilePage userId={context.user_id} /> : <Navigate to="/" replace />} />
        <Route
          path="/ai"
          element={workflowAccess ? <AIPage userId={context.user_id} /> : <Navigate to="/" replace />}
        />
        <Route
          path="/theses/:thesisId"
          element={workflowAccess ? <ThesisViewPage context={context} /> : <Navigate to="/" replace />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes></Suspense>
    </AppShell>
  );
}

export default App;
