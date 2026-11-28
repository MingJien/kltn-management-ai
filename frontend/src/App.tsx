import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { ApiError, errorMessage } from "./errors";
import { Context, demoLogin, emailLogin, logout, request, setSessionCsrfToken } from "./api";
import AppShell from "./components/layout/AppShell";
import WorkspacePage from "./pages/WorkspacePage";
import WithdrawalsPage from "./pages/WithdrawalsPage";
import LoginPage from "./pages/LoginPage";
import { SkeletonCard } from "./components/ui/Skeleton";
import { plannedPages, type PlannedPageId } from "./plannedPages";
import { getPageTitle } from "./routes";

const TopicsPage = lazy(() => import("./pages/TopicsPage"));
const RegistrationsPage = lazy(() => import("./pages/RegistrationsPage"));
const ThesisViewPage = lazy(() => import("./pages/ThesisViewPage"));
const AccountAccessPage = lazy(() => import("./pages/AccountAccessPage"));
const AccountPage = lazy(() => import("./pages/AccountPage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));
const ActivityPage = lazy(() => import("./pages/ActivityPage"));
const SchoolFormsPage = lazy(() => import("./pages/SchoolFormsPage"));
const AdministrationPage = lazy(() => import("./pages/AdministrationPage"));
const LecturersPage = lazy(() => import("./pages/LecturersPage"));
const RosterPage = lazy(() => import("./pages/RosterPage"));
const RoundsPage = lazy(() => import("./pages/RoundsPage"));
const PositionsPage = lazy(() => import("./pages/PositionsPage"));
const LecturerProfilePage = lazy(() => import("./pages/LecturerProfilePage"));
const LecturerProfileReviewsPage = lazy(() => import("./pages/LecturerProfileReviewsPage"));
const ThesesPage = lazy(() => import("./pages/ThesesPage"));
const SubmissionsPage = lazy(() => import("./pages/SubmissionsPage"));
const ComingSoonPage = lazy(() => import("./pages/ComingSoonPage"));
const EvaluationsPage = lazy(() => import("./pages/EvaluationsPage"));
const EvaluationPage = lazy(() => import("./pages/EvaluationPage"));
const DefensePage = lazy(() => import("./pages/DefensePage"));
const Nv6ReportsPage = lazy(() => import("./pages/Nv6ReportsPage"));
const ThesisArchivePage = lazy(() => import("./pages/ThesisArchivePage"));
const ThesisChangesPage = lazy(() => import("./pages/ThesisChangesPage"));
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
    const page = getPageTitle(location.pathname, location.search);
    document.title = `${context ? page : "Đăng nhập"} · KLTN`;
  }, [location.pathname, location.search, context]);

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

  // Refresh only the permission context; keep the current page and unsaved form state.
  useEffect(() => {
    if (!context?.user_id) return;
    const controller = new AbortController();
    let pending = false;
    const refreshPermissions = async () => {
      if (pending || document.visibilityState !== "visible") return;
      pending = true;
      try {
        const next = await request<Context>("/me/context", "", {signal: controller.signal});
        if (!controller.signal.aborted) {
          setSessionCsrfToken(next.csrf_token);
          setContext(previous => previous?.user_id === next.user_id ? next : previous);
        }
      } catch (cause) {
        if (!controller.signal.aborted && cause instanceof ApiError && cause.status === 401) {
          setSessionCsrfToken(null);
          setContext(null);
          setPassword("");
          setError("Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.");
        }
      } finally { pending = false; }
    };
    const refresh = () => { void refreshPermissions(); };
    const timer = window.setInterval(refresh, 20000);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => { controller.abort(); window.clearInterval(timer); window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", refresh); };
  }, [context?.user_id]);

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
      <Suspense fallback={<div className="stack" role="status" aria-busy="true"><SkeletonCard /><SkeletonCard /></div>}><Routes key={noticeRevision}>
        <Route
          path="/"
          element={<WorkspacePage context={context} />}
        />
        <Route path="/account" element={<AccountPage context={context} onProfileChanged={restore} onPasswordChanged={() => {
          setSessionCsrfToken(null); setContext(null); setError("Mật khẩu đã đổi. Vui lòng đăng nhập lại."); navigate("/");
        }} />} />
        <Route path="/notifications" element={<NotificationsPage userId={context.user_id} />} />
        <Route path="/activity" element={<ActivityPage context={context} />} />
        <Route path="/administration" element={context.actions.includes("account:manage") ?
          <AdministrationPage context={context} onPermissionsChanged={restore} section="accounts" /> : <Navigate to="/" replace />} />
        <Route path="/administration/assignments" element={context.base_role === "ADMIN" && context.actions.includes("account:manage") ?
          <AdministrationPage context={context} onPermissionsChanged={restore} section="assignments" /> : <Navigate to="/" replace />} />
        <Route path="/lecturers" element={<LecturersPage context={context}/>}/>
        <Route path="/lecturer-profile-reviews" element={context.actions.includes("lecturer:profile_review") ? <LecturerProfileReviewsPage context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/positions" element={context.base_role === "ADMIN" ? <PositionsPage context={context}/> : <Navigate to="/" replace/>}/>
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
        <Route path="/review-records" element={context.actions.includes("evaluation:record") ? <EvaluationsPage context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/evaluation" element={workflowAccess ? <EvaluationsPage context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/evaluation/:thesisId" element={workflowAccess ? <EvaluationPage context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/defense" element={workflowAccess ? <DefensePage context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/reports" element={context.base_role!=="STUDENT" ? <Nv6ReportsPage key={context.user_id} context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/repository" element={workflowAccess ? <ThesisArchivePage key={context.user_id} context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/planned/reports" element={<Navigate to="/reports" replace/>}/>
        <Route path="/planned/repository" element={<Navigate to="/repository" replace/>}/>
        {["council","defense","results"].map(id=><Route key={id} path={`/planned/${id}`} element={<Navigate to="/defense" replace/>}/>)}
        <Route path="/planned/evaluation" element={<Navigate to="/evaluation" replace/>}/>
        <Route path="/changes" element={workflowAccess ? <ThesisChangesPage key={context.user_id} context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/planned/changes" element={<Navigate to="/changes" replace/>}/>
        <Route path="/withdrawals" element={workflowAccess ? <WithdrawalsPage key={context.user_id} context={context}/> : <Navigate to="/" replace/>}/>
        <Route path="/planned/:feature" element={workflowAccess ? <ComingSoonPage /> : <Navigate to="/" replace />} />
        <Route path="/lecturers/:lecturerId" element={<LecturerProfilePage userId={context.user_id} />} />
        <Route
          path="/ai"
          element={workflowAccess ? <AIPage userId={context.user_id} canCompareReports={context.base_role === "LECTURER"} /> : <Navigate to="/" replace />}
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
