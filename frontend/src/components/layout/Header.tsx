import { useLocation } from "react-router-dom";
import { Menu, LogOut } from "lucide-react";

/**
 * Route path → breadcrumb label mapping.
 * Only includes paths that are statically known.
 */
const BREADCRUMB_MAP: Record<string, string> = {
  "/": "Tổng quan",
  "/topics": "Đề tài",
  "/registrations": "Đăng ký",
  "/ai": "Tra cứu thử nghiệm",
};

interface HeaderProps {
  onToggleSidebar: () => void;
  onLogout: () => void;
}

export default function Header({ onToggleSidebar, onLogout }: HeaderProps) {
  const location = useLocation();
  const currentLabel = BREADCRUMB_MAP[location.pathname] || "Trang";

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
            KLTN
            <span className="header__breadcrumb-sep">/</span>
            <span>{currentLabel}</span>
          </nav>
        </div>
        <div className="header__right">
          <button className="btn btn-ghost btn-sm" onClick={onLogout} aria-label="Đăng xuất">
            <LogOut size={18} /> Đăng xuất
          </button>
        </div>
      </div>
    </header>
  );
}
