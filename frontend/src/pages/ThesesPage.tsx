import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
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
    request<Thesis[]>("/theses", context.user_id, {signal: controller.signal}).then(setRows)
      .catch(cause => {if (!controller.signal.aborted) setError(String(cause));})
      .finally(() => {if (!controller.signal.aborted) setLoading(false);});
    return () => controller.abort();
  }, [context.user_id]);
  const title = section === "proposal" ? "Đề cương khóa luận" : section === "progress" ? "Tiến độ khóa luận" : section === "documents" ? "Tài liệu khóa luận" : "Khóa luận & GVHD";
  return <>
    <PageHeader title={title} description="Khóa luận thuộc phạm vi của bạn; mở hồ sơ để xử lý công việc." />
    {error && <div className="alert alert-danger" role="alert">{error}</div>}
    {loading ? <p role="status">Đang tải khóa luận…</p> : rows.length === 0 ? <div className="card"><div className="card-body">
      <h2>Chưa có khóa luận trong phạm vi của bạn</h2>
      <p>Khóa luận được tạo sau khi giảng viên tiếp nhận nhóm và TBM chốt đăng ký.</p>
      {context.base_role === "STUDENT" && <Link to="/registrations">Xem đăng ký của tôi</Link>}
    </div></div> : <div className="stack">{rows.map(row => <article className="card" key={row.id}><div className="card-body">
      <div className="flex justify-between gap-3"><h2><Link className="core-thesis-link" to={`/theses/${row.id}?section=${section}`}>{row.title}</Link></h2><Status value={row.state} /></div>
      <p className="text-muted">{row.round_label} · GVHD: {row.advisor_name || "Chưa có"}</p>
      <p>{row.members.map(member => member.display_name).join(", ")}</p>
      {row.pending_advisor && <p>Chờ {row.pending_advisor.display_name} phản hồi phân công GVHD.</p>}
    </div></article>)}</div>}
  </>;
}
