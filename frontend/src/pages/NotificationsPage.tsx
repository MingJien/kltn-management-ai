import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, Check, ChevronLeft, ChevronRight } from "lucide-react";
import { request } from "../api";
import { errorMessage } from "../errors";
import type { Notice, NoticeSummary } from "../notifications";
import PageHeader from "../components/layout/PageHeader";
import Tabs from "../components/ui/Tabs";
import Badge from "../components/ui/Badge";
import { SkeletonCard } from "../components/ui/Skeleton";
import EmptyState from "../components/ui/EmptyState";

const PAGE_SIZE = 20;

function dateKey(value: string) {
  const date = new Date(value);
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

function dayLabel(value: string) {
  return new Date(value).toLocaleDateString("vi-VN", {
    weekday: "long", day: "2-digit", month: "2-digit", year: "numeric",
  });
}

function timeLabel(value: string) {
  return new Date(value).toLocaleTimeString("vi-VN", {hour: "2-digit", minute: "2-digit"});
}

export default function NotificationsPage({userId}: {userId: string}) {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [notices, setNotices] = useState<Notice[]>([]);
  const [unreadTotal, setUnreadTotal] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const query = `/notifications?limit=${PAGE_SIZE + 1}&offset=${page * PAGE_SIZE}${filter === "unread" ? "&unread_only=true" : ""}`;
    request<NoticeSummary>(query, userId)
      .then((result) => {
        if (!active) return;
        setNotices(result.items.slice(0, PAGE_SIZE));
        setHasNext(result.items.length > PAGE_SIZE);
        setUnreadTotal(result.unread_count);
      })
      .catch((cause) => {if (active) setError(errorMessage(cause));})
      .finally(() => {if (active) setLoading(false);});
    return () => {active = false;};
  }, [page, filter, userId]);

  async function view(notice: Notice) {
    if (busyId) return;
    setBusyId(notice.id);
    setError("");
    try {
      if (!notice.read_at) {
        await request<void>(`/notifications/${notice.id}/read`, userId, {method: "POST"});
        setNotices((current) => current.map((item) => item.id === notice.id
          ? {...item, read_at: new Date().toISOString()} : item));
        setUnreadTotal((c) => Math.max(0, c - 1));
        window.dispatchEvent(new Event("kltn:notifications-changed"));
      }
      navigate(notice.url,{state:{noticeId:notice.id}});
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusyId("");
    }
  }

  const displayedNotices = notices;
  const groups: {key: string; label: string; items: Notice[]}[] = [];
  for (const notice of displayedNotices) {
    const key = dateKey(notice.created_at);
    if (groups.at(-1)?.key !== key) groups.push({key, label: dayLabel(notice.created_at), items: []});
    groups[groups.length - 1].items.push(notice);
  }

  return <>
    <PageHeader title="Tất cả thông báo" description="Xem lại các thông báo theo ngày và thời điểm gửi." />
    <div className="notification-history">
      {!loading && (notices.length > 0 || unreadTotal > 0 || filter === "unread") && (
        <div className="mb-4">
          <Tabs
            asButtons
            variant="underline"
            idPrefix="notifications-filter"
            ariaLabel="Lọc thông báo"
            items={[
              { id: "all", label: "Tất cả" },
              { id: "unread", label: "Chưa xem", count: unreadTotal },
            ]}
            activeId={filter}
            onChange={(next) => { setFilter(next as "all" | "unread"); setPage(0); }}
          />
        </div>
      )}
      {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
      {loading ? <div className="stack" role="status" aria-label="Đang tải thông báo"><SkeletonCard /><SkeletonCard /></div> : groups.length ? groups.map((group) =>
        <section className="notification-history__day" key={group.key}>
          <h2>{group.label}</h2>
          <ul>{group.items.map((notice) =>
            <li key={notice.id}>
              <button type="button" className={"notification-history__item" + (!notice.read_at ? " notification-history__item--unread" : "")}
                disabled={!!busyId} onClick={() => void view(notice)}>
                <span className="notification-history__icon" aria-hidden="true">{notice.read_at ? <Check size={18} /> : <Bell size={18} />}</span>
                <span className="notification-history__content">
                  <span>{notice.message}</span>
                  <span className="notification-history__meta">
                    <time dateTime={notice.created_at}>{timeLabel(notice.created_at)}</time>
                    <span aria-hidden="true">·</span>
                    <Badge variant={notice.read_at ? "neutral" : "info"} dot>{notice.read_at ? "Đã xem" : "Chưa xem"}</Badge>
                  </span>
                </span>
              </button>
            </li>)}</ul>
        </section>) : !error ? <EmptyState icon={<Bell aria-hidden="true" />} title={filter === "unread" ? "Không có thông báo chưa xem trên trang này" : "Chưa có thông báo"} description={filter === "unread" ? "Chuyển sang Tất cả hoặc sang trang khác để xem lại các thông báo cũ." : "Các thông báo hệ thống sẽ xuất hiện tại đây khi có cập nhật."}>
          {filter === "unread" ? <button type="button" className="btn btn-secondary btn-sm" onClick={() => setFilter("all")}>Xem tất cả trên trang</button> : null}
        </EmptyState> : null}
      <nav className="pagination" aria-label="Phân trang thông báo">
        <button type="button" className="btn btn-secondary" disabled={page === 0 || loading || !!busyId} onClick={() => setPage((value) => value - 1)}><ChevronLeft size={15} aria-hidden="true" />Trang trước</button>
        <span>Trang {page + 1}</span>
        <button type="button" className="btn btn-secondary" disabled={!hasNext || loading || !!busyId} onClick={() => setPage((value) => value + 1)}>Trang sau<ChevronRight size={15} aria-hidden="true" /></button>
      </nav>
    </div>
  </>;
}
