import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import type { Context, Thesis } from "../api";
import { request } from "../api";
import PageHeader from "../components/layout/PageHeader";
import { Status } from "../components/domain/CoreForms";

type ThesisSection = "overview" | "proposal" | "progress" | "documents";

export default function ThesesPage({context, section = "overview"}: {context: Context; section?: ThesisSection}) {
  const [rows, setRows] = useState<Thesis[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
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
      .catch(cause => {if (!controller.signal.aborted) setError(String(cause));})
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

  return <>
    <PageHeader title={title} description={section === "progress"
      ? "Mở một khóa luận để xem mốc của đợt, nộp báo cáo, nhận xét hoặc gia hạn theo quyền được giao."
      : section === "documents" ? "Mở hồ sơ khóa luận để tạo tài liệu, nộp phiên bản, nhận xét và tải bản đã lưu."
      : "Khóa luận chỉ được tạo khi giảng viên chấp nhận đăng ký; GV đó trở thành GVHD chính ngay."} />
    {section === "documents" && <Link className="btn btn-secondary" to="/forms">Mở kho biểu mẫu và tài liệu Khoa (không cần có khóa luận)</Link>}
    {error && <div className="alert alert-danger" role="alert">{error}</div>}
    {loading ? <p role="status">Đang tải khóa luận…</p> : visibleRows.length === 0 ? <div className="card"><div className="card-body">
      <h2>Chưa có khóa luận trong phạm vi của bạn</h2>
      <p>{section === "progress" ? "Các mốc và báo cáo tiến độ xuất hiện trong hồ sơ sau khi GV chấp nhận đăng ký. Người mở, gia hạn hoặc đóng mốc cần được ADMIN giao quyền điều phối đợt." : section === "documents" ? "Tài liệu được nộp trong hồ sơ sau khi GV chấp nhận đăng ký; mở hồ sơ để tạo loại tài liệu và nộp các phiên bản." : "Khi giảng viên chấp nhận đăng ký, hệ thống tạo khóa luận, ghi nhận nhóm và gán GV đó làm GVHD chính trong cùng thao tác."}</p>
      {context.base_role === "STUDENT" && <Link className="btn btn-secondary" to="/registrations">Xem đăng ký của tôi</Link>}
      {context.base_role === "LECTURER" && <Link className="btn btn-secondary" to="/registrations">Mở hồ sơ đăng ký</Link>}
    </div></div> : <div className="stack">{visibleRows.map(row => <article className="card" key={row.id}><div className="card-body">
      <div className="flex justify-between gap-3"><h2><Link className="core-thesis-link" to={`/theses/${row.id}?section=${section}`}>{row.title}</Link></h2><Status value={row.state} /></div>
      <p className="text-muted">{row.round_label} · GVHD chính thức: {row.advisor_name || "Chưa có"}</p>
      <p>{row.members.map(member => member.display_name).join(", ")}</p>
      <div className="flex gap-2" style={{marginTop:"var(--space-3)",flexWrap:"wrap"}}>
        <Link className="btn btn-primary" to={`/theses/${row.id}?section=${section}`}>{section === "overview" ? "Xem hồ sơ & GVHD" : section === "proposal" ? "Xử lý đề cương Mẫu 3" : section === "progress" ? "Xem mốc & báo cáo định kỳ" : "Xem tài liệu & phiên bản"}</Link>
        <span className="text-caption">{row.members.length} sinh viên · {row.advisor_history.filter(item=>item.state==="ACTIVE").length} GVHD đang phụ trách</span>
      </div>
    </div></article>)}</div>}
  </>;
}
