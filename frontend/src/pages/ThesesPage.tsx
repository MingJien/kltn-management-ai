import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ArrowRight, GraduationCap, UsersRound } from "lucide-react";
import type { Context, Thesis } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";
import EmptyState from "../components/ui/EmptyState";
import FilterBar from "../components/ui/FilterBar";
import { SkeletonCard } from "../components/ui/Skeleton";
import { Status } from "../components/domain/CoreForms";
import { stateLabel } from "../components/domain/stateLabels";

type ThesisSection = "overview" | "proposal" | "progress" | "documents";

export default function ThesesPage({context, section = "overview"}: {context: Context; section?: ThesisSection}) {
  const [rows, setRows] = useState<Thesis[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    request<Thesis[]>("/theses", context.user_id, {signal: controller.signal}).then(data => {
      setRows(data);
      if (data.length === 1 && typeof sessionStorage !== "undefined") {
        sessionStorage.setItem(`kltn_active_thesis_id_${context.user_id}`, data[0].id);
      }
    })
      .catch(cause => {if (!controller.signal.aborted) setError(errorMessage(cause));})
      .finally(() => {if (!controller.signal.aborted) setLoading(false);});
    return () => controller.abort();
  }, [context.user_id]);
  const title = section === "proposal" ? "Đề cương khóa luận" : section === "progress" ? "Tiến độ khóa luận" : section === "documents" ? "Tài liệu khóa luận" : "Khóa luận & GVHD";

  const visibleRows = rows.filter(row => section === "overview" || row.actions.includes(
    section === "proposal" ? "proposal:view" : section === "documents" ? "document:view" : "progress:view")
    || (section === "progress" && row.actions.includes("milestone:manage")));
  if (!loading && visibleRows.length === 1) {
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(`kltn_active_thesis_id_${context.user_id}`, visibleRows[0].id);
    }
    return <Navigate to={`/theses/${visibleRows[0].id}?section=${section}`} replace />;
  }

  const qNorm = search.trim().toLocaleLowerCase("vi");
  const filteredRows = visibleRows.filter(row => {
    if (stateFilter && row.state !== stateFilter) return false;
    if (!qNorm) return true;
    const hay = `${row.title} ${row.round_label} ${row.advisor_name || ""} ${row.members.map(m => `${m.display_name} ${m.student_code}`).join(" ")}`.toLocaleLowerCase("vi");
    return hay.includes(qNorm);
  });
  const states = Array.from(new Set(visibleRows.map(r => r.state)));

  return <>
    <PageHeader title={title} description={section === "progress"
      ? "Mở khóa luận để theo dõi mốc, nộp báo cáo tiến độ hoặc gia hạn."
      : section === "documents" ? "Mở hồ sơ để nộp, nhận xét và tải các phiên bản tài liệu khóa luận."
      : "Theo dõi đề tài, nhóm thực hiện và giảng viên hướng dẫn chính thức."} />
    {error && <div className="alert alert-danger" role="alert">{error}</div>}
    {!loading && visibleRows.length > 0 && (
      <FilterBar
        search={{
          value: search,
          onChange: setSearch,
          placeholder: "Tìm theo tên đề tài, sinh viên, MSSV hoặc GVHD…",
          ariaLabel: "Tìm khóa luận",
        }}
        chips={[
          ...(search.trim() ? [{ key: "q", label: `Từ khóa: "${search.trim()}"`, onRemove: () => setSearch("") }] : []),
          ...(stateFilter ? [{ key: "state", label: `Trạng thái: ${stateLabel[stateFilter] || stateFilter}`, onRemove: () => setStateFilter("") }] : []),
        ]}
        onClearAll={() => { setSearch(""); setStateFilter(""); }}
        summary={`${filteredRows.length}/${visibleRows.length} khóa luận`}
      >
        <select aria-label="Lọc trạng thái khóa luận" className="input" value={stateFilter} onChange={e => setStateFilter(e.target.value)}>
          <option value="">Tất cả trạng thái</option>
          {states.map(s => <option key={s} value={s}>{stateLabel[s] || s}</option>)}
        </select>
      </FilterBar>
    )}
    {loading ? <div className="stack" role="status" aria-label="Đang tải khóa luận"><SkeletonCard /><SkeletonCard /></div> : visibleRows.length === 0 ?
      <EmptyState icon={<GraduationCap aria-hidden="true" />} title="Chưa có khóa luận trong phạm vi của bạn" description={section === "progress" ? "Các mốc và báo cáo tiến độ xuất hiện trong hồ sơ sau khi GV chấp nhận đăng ký." : section === "documents" ? "Tài liệu được nộp trong hồ sơ sau khi GV chấp nhận đăng ký." : "Khi giảng viên chấp nhận đăng ký, hệ thống tạo khóa luận, ghi nhận nhóm và gán GV đó làm GVHD chính."}>
        {context.base_role === "STUDENT" && <Link className="btn btn-soft" to="/registrations">Xem đăng ký của tôi</Link>}
        {context.base_role === "LECTURER" && <Link className="btn btn-soft" to="/registrations">Mở hồ sơ đăng ký</Link>}
      </EmptyState> : filteredRows.length === 0 ?
      <EmptyState icon={<GraduationCap aria-hidden="true" />} title="Không tìm thấy khóa luận phù hợp" description="Thử xóa bộ lọc hoặc nhập từ khóa khác." /> : <div className="stack">{filteredRows.map(row => <article className="card" key={row.id}><div className="card-body stack">
      <div className="flex justify-between items-start gap-3">
        <div>
          <span className="text-caption">{row.round_label}</span>
          <h2 className="mt-1"><Link className="core-thesis-link" to={`/theses/${row.id}?section=${section}`}>{row.title}</Link></h2>
        </div>
        <Status value={row.state} />
      </div>
      <div className="flex flex-wrap gap-4 text-body-sm text-muted">
        <span>GVHD chính thức: <strong className="advisor-name-strong">{row.advisor_name || "Chưa có"}</strong></span>
        <span className="inline-flex items-center gap-1"><UsersRound size={14} aria-hidden="true" /> {row.members.map(member => `${member.display_name} (${member.student_code})`).join(", ")}</span>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
        <span className="text-caption">{row.members.length} sinh viên · {row.advisor_history.filter(item=>item.state==="ACTIVE").length} GVHD đang phụ trách</span>
        <Link className="btn btn-primary btn-sm" to={`/theses/${row.id}?section=${section}`}>
          {section === "overview" ? "Xem hồ sơ & GVHD" : section === "proposal" ? "Xử lý đề cương Mẫu 3" : section === "progress" ? "Xem mốc & báo cáo định kỳ" : "Xem tài liệu & phiên bản"}
          <ArrowRight size={14} aria-hidden="true" />
        </Link>
      </div>
    </div></article>)}</div>}
  </>;
}
