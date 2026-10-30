import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { History, RefreshCw, Search } from "lucide-react";
import { request, type Context } from "../api";
import { actionLabel, resourceLabel, type ActivityResult } from "../activity";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";

const SIZE = 25;
const empty: ActivityResult = {items: [], total: 0, actions: [], scope: ""};

export default function ActivityPage({context}: {context: Context}) {
  const [params] = useSearchParams();
  const resourceType = params.get("resource_type") || "";
  const resourceId = params.get("resource_id") || "";
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [filters, setFilters] = useState({search: "", action: "", from: "", to: ""});
  const [page, setPage] = useState(0);
  const [revision, setRevision] = useState(0);
  const [data, setData] = useState<ActivityResult>(empty);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {setPage(0); setData(empty);}, [resourceType, resourceId, context.user_id]);
  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({limit: String(SIZE), offset: String(page * SIZE)});
    if (filters.search) query.set("search", filters.search);
    if (filters.action) query.set("action", filters.action);
    if (filters.from) query.set("date_from", filters.from);
    if (filters.to) query.set("date_to", filters.to);
    if (resourceType) query.set("resource_type", resourceType);
    if (resourceId) query.set("resource_id", resourceId);
    setLoading(true); setError("");
    request<ActivityResult>(`/activity?${query}`, context.user_id, {signal: controller.signal})
      .then((result) => {if (!controller.signal.aborted) setData(result);})
      .catch((cause) => {if (!controller.signal.aborted) {setData(empty); setError(errorMessage(cause));}})
      .finally(() => {if (!controller.signal.aborted) setLoading(false);});
    return () => controller.abort();
  }, [context.user_id, filters, page, revision, resourceType, resourceId]);
  return <div className="stack">
    <PageHeader title={context.base_role === "ADMIN" ? "Nhật ký hệ thống" : "Lịch sử hoạt động"}
      description={context.base_role === "ADMIN" ? "Tra cứu thao tác quản trị và nghiệp vụ, lý do và căn cứ đã ghi nhận." : "Xem lại thao tác trên tài khoản và các hồ sơ trong phạm vi được giao."} />
    <form className="card" onSubmit={(event) => {event.preventDefault(); setPage(0); setFilters({search: search.trim(), action, from, to});}}>
      <div className="card-body stack">
        <div className="activity-filters">
          <div className="input-group"><label htmlFor="activity-search">Người thao tác, lý do, căn cứ hoặc mã hồ sơ</label>
            <input className="input" id="activity-search" value={search} maxLength={200} onChange={e => setSearch(e.target.value)} placeholder="Ví dụ: đính chính email, số văn bản…" /></div>
          <div className="input-group"><label htmlFor="activity-action">Thao tác</label><select className="input" id="activity-action" value={action} onChange={e => setAction(e.target.value)}>
            <option value="">Tất cả thao tác</option>{data.actions.map(value => <option key={value} value={value}>{actionLabel(value)}</option>)}
          </select></div>
          <div className="input-group"><label htmlFor="activity-from">Từ ngày</label><input className="input" type="date" id="activity-from" value={from} max={to || undefined} onChange={e => setFrom(e.target.value)} /></div>
          <div className="input-group"><label htmlFor="activity-to">Đến ngày</label><input className="input" type="date" id="activity-to" value={to} min={from || undefined} onChange={e => setTo(e.target.value)} /></div>
        </div>
        <div className="flex gap-2" style={{flexWrap: "wrap"}}>
          <button className="btn btn-primary" disabled={loading}><Search size={16} aria-hidden="true" />Tra cứu</button>
          <button type="button" className="btn btn-secondary" disabled={loading} onClick={() => setRevision(value => value + 1)}><RefreshCw size={16} aria-hidden="true" />Làm mới</button>
          <button type="button" className="btn btn-ghost" disabled={loading} onClick={() => {setSearch(""); setAction(""); setFrom(""); setTo(""); setPage(0); setFilters({search:"",action:"",from:"",to:""});}}>Xóa bộ lọc</button>
          {(resourceType || resourceId) && <Link className="btn btn-secondary" to="/activity">Xem toàn bộ phạm vi của tôi</Link>}
        </div>
      </div>
    </form>
    {error && <p className="alert alert-danger" role="alert">{error}</p>}
    <p className="text-muted" aria-live="polite">{loading ? "Đang tải nhật ký…" : `${data.total} sự kiện · ${data.scope}`}</p>
    {!loading && !error && !data.items.length && <div className="card"><div className="card-body"><p>Chưa có sự kiện phù hợp với phạm vi và bộ lọc đã chọn.</p></div></div>}
    <div className="activity-list" aria-busy={loading}>
      {!loading && data.items.map(item => <article className="card" key={item.id}>
        <div className="card-body stack">
          <div className="activity-item__header"><h2><History size={18} aria-hidden="true" />{actionLabel(item.action)}</h2>
            <time dateTime={item.occurred_at}>{new Date(item.occurred_at).toLocaleString("vi-VN", {timeZone: "Asia/Ho_Chi_Minh"})}</time></div>
          <div><strong>{item.actor_name}</strong><span className="text-muted"> · {resourceLabel(item.resource_type)}</span></div>
          {item.resource_label !== item.resource_type && <p>{item.resource_label}</p>}
          {item.reason && <p className="activity-item__text"><strong>Lý do / nội dung: </strong>{item.reason}</p>}
          {item.source_reference && <p className="activity-item__text"><strong>Căn cứ / số văn bản: </strong>{item.source_reference}</p>}
          <details className="text-caption text-muted"><summary>Mã tra cứu</summary><p>Mã nhật ký: {item.id}<br />Mã hồ sơ: {item.resource_id}</p></details>
        </div>
      </article>)}
    </div>
    <nav className="pagination" aria-label="Phân trang nhật ký">
      <button className="btn btn-secondary" disabled={loading || page === 0} onClick={() => setPage(value => value - 1)}>Trang trước</button>
      <span>Trang {page + 1}{data.total ? ` / ${Math.ceil(data.total / SIZE)}` : ""}</span>
      <button className="btn btn-secondary" disabled={loading || (page + 1) * SIZE >= data.total} onClick={() => setPage(value => value + 1)}>Trang sau</button>
    </nav>
  </div>;
}
