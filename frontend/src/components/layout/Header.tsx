import { useLocation } from "react-router-dom";
import { Menu, LogOut } from "lucide-react";
import { plannedPages, type PlannedPageId } from "../../plannedPages";
import type { Context } from "../../api";
import NotificationsBell from "./NotificationsBell";
import ProfilePopup from "./ProfilePopup";

/**
 * Route path → breadcrumb label mapping.
 * Only includes paths that are statically known.
 */
const BREADCRUMB_MAP: Record<string, string> = {
  "/": "Tổng quan",
  "/topics": "Đề tài",
  "/registrations": "Đăng ký",
  "/theses": "Khóa luận & GVHD",
  "/proposals": "Đề cương",
  "/progress": "Tiến độ",
  "/documents": "Tài liệu",
  "/forms": "Biểu mẫu và tài liệu Khoa",
  "/account": "Tài khoản",
  "/administration": "Quản trị",
  "/rounds": "Đợt KLTN",
  "/roster": "Danh sách sinh viên",
  "/ai": "Tra cứu thử nghiệm",
  "/notifications": "Thông báo",
  "/activity": "Nhật ký hoạt động",
};

interface HeaderProps {
  context: Context;
  onToggleSidebar: () => void;
  onLogout: () => void;
}

export default function Header({ context, onToggleSidebar, onLogout }: HeaderProps) {
  const location = useLocation();
  const plannedId = location.pathname.startsWith("/planned/") ? location.pathname.slice("/planned/".length) : "";
  const currentLabel = plannedId && Object.hasOwn(plannedPages, plannedId)
    ? plannedPages[plannedId as PlannedPageId].title
    : BREADCRUMB_MAP[location.pathname] || (location.pathname.startsWith("/theses/") ? "Khóa luận" : "Trang");

  return (
    <header className="app-shell__header">
      <div className="header">
        <div className="header__left">
          <button
            className="header__toggle"
            onClick={onToggleSidebar}
            aria-label="Mở hoặc đóng menu"
          >
            <Menu size={20} />
          </button>
          <nav className="header__breadcrumb" aria-label="Vị trí trang">
            <span className="header__breadcrumb-root">KLTN</span>
            <span className="header__breadcrumb-sep" aria-hidden="true">/</span>
            <span>{currentLabel}</span>
          </nav>
        </div>
        <div className="header__right">
          <NotificationsBell userId={context.user_id} />
          <ProfilePopup context={context} onLogout={onLogout} />
          <button className="btn btn-ghost btn-sm" onClick={onLogout} aria-label="Đăng xuất">
            <LogOut size={18} /> Đăng xuất
          </button>
        </div>
      </div>
    </header>
  );
}
