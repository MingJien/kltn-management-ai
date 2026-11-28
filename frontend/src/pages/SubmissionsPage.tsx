import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, ChevronLeft, ChevronRight, FolderOpen, RefreshCw } from "lucide-react";
import type { Context, Registration, Thesis } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";
import EmptyState from "../components/ui/EmptyState";
import { SkeletonCard } from "../components/ui/Skeleton";
import RegistrationSubmission from "../components/domain/RegistrationSubmission";
import { Status } from "../components/domain/CoreForms";

const PAGE_SIZE = 24;
export default function SubmissionsPage({context}: {context: Context}) {
  const [params, setParams] = useSearchParams();
  const registrationId = params.get("registration");
  const roundId = params.get("round_id");
  const kind = params.get("kind");
  const openThesis = (id: string) => `/theses/${id}?section=submissions${kind ? `&kind=${encodeURIComponent(kind)}` : ""}`;
  const page = Math.max(0, Number(params.get("page")) || 0);
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async (signal?: AbortSignal) => {
    const [thesisRows, registrationRows] = await Promise.all([
      request<Thesis[]>("/theses", context.user_id, {signal}),
      request<Registration[]>("/topic-registrations?limit=" + PAGE_SIZE + "&offset=" + page * PAGE_SIZE, context.user_id, {signal}),
    ]);
    if (!signal?.aborted) {setTheses(thesisRows); setRegistrations(registrationRows); setError("");}
  }, [context.user_id, page]);
  useEffect(() => {
    if (registrationId) {setLoading(false); return;}
    const controller = new AbortController(); setLoading(true);
    void load(controller.signal).catch(cause => {if (!controller.signal.aborted) setError(errorMessage(cause));})
      .finally(() => {if (!controller.signal.aborted) setLoading(false);});
    return () => controller.abort();
  }, [load, registrationId]);
  const pending = !kind || kind === "REGISTRATION" ? registrations.filter(row => (!roundId || row.round_id === roundId) && !row.thesis_id && !["CANCELLED","WITHDRAWN"].includes(row.state)) : [];
  const canPageRegistrations = (!kind || kind === "REGISTRATION") && (page > 0 || registrations.length === PAGE_SIZE);
  function goToPage(next: number) {
    const nextParams = new URLSearchParams(params);
    nextParams.set("page", String(next));
    setParams(nextParams);
  }
  const visibleTheses = theses.filter(row => (!roundId || row.round_id === roundId) &&
    row.actions.some(action => ["document:view", "proposal:view", "milestone:manage"].includes(action)));
  if (!registrationId && !loading && !error && page === 0 && visibleTheses.length === 1 && pending.length === 0 && context.base_role === "STUDENT") {
    return <Navigate replace to={openThesis(visibleTheses[0].id)} />;
  }
  return <>
    <PageHeader title="Hồ sơ nộp & xét duyệt" description={context.base_role === "STUDENT"
      ? "Chọn hồ sơ để nộp Mẫu 1–2–3, cuốn báo cáo KLTN và minh chứng."
      : "Chọn đăng ký hoặc khóa luận để xem bản nộp và xử lý theo quyền."} />
    {registrationId ? <div className="stack">
      <Link className="workspace-back-link" to="/submissions"><ArrowLeft size={15} aria-hidden="true" />Danh sách hồ sơ</Link>
      <RegistrationSubmission key={registrationId + context.user_id} registrationId={registrationId} userId={context.user_id} redirectToThesis />
      <p className="alert alert-info">Kế hoạch Mẫu 2, Đề cương Mẫu 3 và các tài liệu khóa luận sẽ mở sau khi GV chấp nhận đăng ký, tạo hồ sơ khóa luận và trở thành GVHD chính thức.</p>
    </div> : <div className="stack">
      {error && <p role="alert" className="alert alert-danger">{error} <button type="button" className="btn btn-secondary" onClick={() => void load().catch(cause => setError(errorMessage(cause)))}><RefreshCw size={15} aria-hidden="true" />Thử lại</button></p>}
      {loading ? <div className="stack" role="status" aria-label="Đang tải danh sách hồ sơ"><SkeletonCard /><SkeletonCard /></div> : <>
        {pending.length > 0 && <section className="stack"><h2>Đơn đăng ký trước tiếp nhận · Mẫu 1a/1b</h2>
          {pending.map(row => <article className="card" key={row.id}><div className="card-body submission-list-row">
            <div><h3>{row.topic_title}</h3><p>{row.topic_code} · {row.members.filter(member => member.active).map(member => member.display_name).join(", ")}</p><Status value={row.state}/></div>
            <Link className="btn btn-primary" to={"/submissions?registration=" + row.id}>Mở đơn đăng ký<ArrowRight size={15} aria-hidden="true" /></Link>
          </div></article>)}
        </section>}
        {canPageRegistrations && <nav className="pagination" aria-label="Phân trang đơn đăng ký"><button type="button" className="btn btn-secondary" disabled={page === 0} onClick={() => goToPage(page - 1)}><ChevronLeft size={15} aria-hidden="true" />Đơn đăng ký trước</button><span>Trang đơn đăng ký {page + 1}</span><button type="button" className="btn btn-secondary" disabled={registrations.length < PAGE_SIZE} onClick={() => goToPage(page + 1)}>Đơn đăng ký tiếp<ChevronRight size={15} aria-hidden="true" /></button></nav>}
        {visibleTheses.length > 0 && <section className="stack"><h2>{context.base_role === "STUDENT" ? "Hồ sơ khóa luận của tôi" : "Hồ sơ khóa luận trong phạm vi phụ trách"}</h2>
          {visibleTheses.map(row => <article className="card" key={row.id}><div className="card-body submission-list-row">
            <div><h3>{row.title}</h3><p>{row.round_label} · GVHD: {row.advisor_name || "Chưa phân công"}</p><p>{row.members.map(member => member.display_name).join(", ")}</p><Status value={row.state}/></div>
            <Link className="btn btn-primary" to={openThesis(row.id)}>Mở hồ sơ nộp &amp; xét duyệt<ArrowRight size={15} aria-hidden="true" /></Link>
          </div></article>)}
        </section>}
        {!error && pending.length === 0 && visibleTheses.length === 0 && (
          <EmptyState
            icon={<FolderOpen aria-hidden="true" />}
            title="Chưa có hồ sơ để nộp"
            description="Lập hồ sơ đăng ký đề tài trước để nộp đơn Mẫu 1a/1b. Các mẫu sau mở khi GV tiếp nhận."
          >
            <Link className="btn btn-primary" to="/registrations">Mở đăng ký đề tài<ArrowRight size={15} aria-hidden="true" /></Link>
          </EmptyState>
        )}
      </>}
      <div><Link className="btn btn-secondary" to="/forms"><FolderOpen size={15} aria-hidden="true" />Tài liệu Khoa công bố</Link></div>
    </div>}
  </>;
}
