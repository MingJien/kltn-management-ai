import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { request } from "../../api";
import { errorMessage } from "../../errors";
import type { Notice, NoticeSummary } from "../../notifications";

export default function NotificationsBell({userId}: {userId: string}) {
  const navigate = useNavigate();
  const root = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [summary, setSummary] = useState<NoticeSummary>({unread_count:0, items:[]});
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");
  const refresh = useCallback(async () => {
    setSummary(await request<NoticeSummary>("/notifications?unread_only=true&limit=5", userId));
  }, [userId]);

  useEffect(() => {
    void refresh().catch(() => undefined);
    const timer = window.setInterval(() => void refresh().catch(() => undefined), 30000);
    const onFocus = () => void refresh().catch(() => undefined);
    window.addEventListener("focus", onFocus);
    window.addEventListener("kltn:notifications-changed", onFocus);
    return () => {window.clearInterval(timer); window.removeEventListener("focus", onFocus);
      window.removeEventListener("kltn:notifications-changed", onFocus);};
  }, [refresh]);
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {if (event.key === "Escape") setOpen(false);};
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {document.removeEventListener("pointerdown", onPointer); document.removeEventListener("keydown", onKey);};
  }, [open]);

  async function view(notice: Notice) {
    if (busyId) return;
    setBusyId(notice.id); setError("");
    try {
      if (!notice.read_at) {
        await request<void>(`/notifications/${notice.id}/read`, userId, {method:"POST"});
        setSummary((current) => ({unread_count:Math.max(0,current.unread_count-1),
          items:current.items.filter((item) => item.id !== notice.id)}));
        window.dispatchEvent(new Event("kltn:notifications-changed"));
      }
      setOpen(false);
      navigate(notice.url,{state:{noticeId:notice.id}});
    } catch (cause) {setError(errorMessage(cause));}
    finally {setBusyId("");}
  }

  return <div className="notifications" ref={root}>
    <button type="button" className="notifications__trigger" aria-label={`Thông báo, ${summary.unread_count} chưa xem`}
      aria-expanded={open} aria-haspopup="dialog"
      onClick={() => {setOpen((value) => !value); setError(""); void refresh().catch((cause) => setError(errorMessage(cause)));}}>
      <Bell size={19} aria-hidden="true" />
      {summary.unread_count > 0 ? <span className="notifications__badge" aria-hidden="true">
        {summary.unread_count > 99 ? "99+" : summary.unread_count}</span> : null}
    </button>
    {open ? <section className="notifications__panel" role="dialog" aria-label="Thông báo">
      <div className="notifications__header"><strong>Thông báo</strong><span>{summary.unread_count} chưa xem</span></div>
      {error ? <p className="alert alert-danger" role="alert">{error}</p> : null}
      {summary.items.length ? <ul className="notifications__list">{summary.items.map((item) =>
        <li key={item.id}><button type="button" className="notifications__item notifications__item--unread"
          disabled={!!busyId} onClick={() => void view(item)}>
          <span className="notifications__message">{item.message}</span>
          <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString("vi-VN")}</time>
        </button></li>)}</ul> : <p className="notifications__empty">Không có thông báo chưa xem.</p>}
      <Link className="notifications__all" to="/notifications" onClick={() => setOpen(false)}>Xem tất cả</Link>
    </section> : null}
  </div>;
}
