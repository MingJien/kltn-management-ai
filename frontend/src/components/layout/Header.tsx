import { Link, useLocation } from "react-router-dom";
import type { Ref } from "react";
import { Menu, LogOut } from "lucide-react";
import type { Context } from "../../api";
import { getBreadcrumbs } from "../../routes";
import { roleLabel } from "./roleLabel";
import NotificationsBell from "./NotificationsBell";
import ProfilePopup from "./ProfilePopup";

interface HeaderProps {
  menuButton: Ref<HTMLButtonElement>;
  menuOpen: boolean;
  context: Context;
  onToggleSidebar: () => void;
  onLogout: () => void;
}

export default function Header({ context, menuButton, menuOpen, onToggleSidebar, onLogout }: HeaderProps) {
  const location = useLocation();
  const crumbs = getBreadcrumbs(location.pathname, location.search);

  return (
    <header className="app-shell__header">
      <div className="header">
        <div className="header__left">
          <button
            className="header__toggle"
            ref={menuButton}
            aria-controls="main-sidebar"
            aria-expanded={menuOpen}
            onClick={onToggleSidebar}
            aria-label="Mở hoặc đóng menu"
          >
            <Menu size={20} aria-hidden="true" />
          </button>
          <nav className="header__breadcrumb" aria-label="Vị trí trang">
            {crumbs.map((crumb, index) => {
              const isLast = index === crumbs.length - 1;
              return (
                <span key={`${crumb.label}-${index}`} className="flex items-center gap-2">
                  {index > 0 && <span className="header__breadcrumb-sep" aria-hidden="true">/</span>}
                  {crumb.to && !isLast ? (
                    <Link className="header__breadcrumb-link" to={crumb.to}>
                      {crumb.label}
                    </Link>
                  ) : (
                    <span
                      className={index === 0 && crumbs.length > 1 ? "header__breadcrumb-root" : undefined}
                      aria-current={isLast ? "page" : undefined}
                    >
                      {crumb.label}
                    </span>
                  )}
                </span>
              );
            })}
          </nav>
        </div>
        <div className="header__right">
          <span className="header__duty-pill" title="Vai trò làm việc hiện tại">
            {roleLabel(context)}
          </span>
          <NotificationsBell userId={context.user_id} />
          <ProfilePopup context={context} onLogout={onLogout} />
          <button className="btn btn-ghost btn-sm header__logout-standalone" onClick={onLogout} aria-label="Đăng xuất">
            <LogOut size={18} aria-hidden="true" /> <span>Đăng xuất</span>
          </button>
        </div>
      </div>
    </header>
  );
}
