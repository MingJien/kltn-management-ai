import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, Check } from "lucide-react";
import { request } from "../api";
import { errorMessage } from "../errors";
import type { Notice, NoticeSummary } from "../notifications";
import PageHeader from "../components/layout/PageHeader";

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
  const [notices, setNotices] = useState<Notice[]>([]);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    request<NoticeSummary>(`/notifications?limit=${PAGE_SIZE + 1}&offset=${page * PAGE_SIZE}`, userId)
      .then((result) => {
        if (!active) return;
        setNotices(result.items.slice(0, PAGE_SIZE));
        setHasNext(result.items.length > PAGE_SIZE);
      })
      .catch((cause) => {if (active) setError(errorMessage(cause));})
      .finally(() => {if (active) setLoading(false);});
    return () => {active = false;};
  }, [page, userId]);

  async function view(notice: Notice) {
    if (busyId) return;
    setBusyId(notice.id);
    setError("");
    try {
      if (!notice.read_at) {
        await request<void>(`/notifications/${notice.id}/read`, userId, {method: "POST"});
        setNotices((current) => current.map((item) => item.id === notice.id
          ? {...item, read_at: new Date().toISOString()} : item));
        window.dispatchEvent(new Event("kltn:notifications-changed"));
      }
      navigate(notice.url,{state:{noticeId:notice.id}});
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusyId("");
    }
  }

  const groups: {key: string; label: string; items: Notice[]}[] = [];
  for (const notice of notices) {
    const key = dateKey(notice.created_at);
    if (groups.at(-1)?.key !== key) groups.push({key, label: dayLabel(notice.created_at), items: []});
    groups[groups.length - 1].items.push(notice);
  }

  return <>
    <PageHeader title="Tất cả thông báo" description="Xem lại các thông báo theo ngày và thời điểm gửi." />
    <div className="notification-history">
      {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
      {loading ? <p role="status">Đang tải thông báo…</p> : groups.length ? groups.map((group) =>
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
                    <span>{notice.read_at ? "Đã xem" : "Chưa xem"}</span>
                  </span>
                </span>
              </button>
            </li>)}</ul>
        </section>) : !error ? <div className="card notification-history__empty"><Bell size={28} aria-hidden="true" /><p>Chưa có thông báo.</p></div> : null}
      <nav className="pagination" aria-label="Phân trang thông báo">
        <button className="btn btn-secondary" disabled={page === 0 || loading || !!busyId} onClick={() => setPage((value) => value - 1)}>Trang trước</button>
        <span>Trang {page + 1}</span>
        <button className="btn btn-secondary" disabled={!hasNext || loading || !!busyId} onClick={() => setPage((value) => value + 1)}>Trang sau</button>
      </nav>
    </div>
  </>;
}
