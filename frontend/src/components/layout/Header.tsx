import { useLocation } from "react-router-dom";
import { Menu, LogOut } from "lucide-react";

/**
 * Route path → breadcrumb label mapping.
 * Only includes paths that are statically known.
 */
const BREADCRUMB_MAP: Record<string, string> = {
  "/": "Workspace",
  "/rounds": "Đợt & Năm học",
  "/eligibility": "Điều kiện SV",
  "/topics": "Đề tài",
  "/registrations": "Đăng ký",
  "/proposals": "Đề cương",
  "/progress": "Tiến độ",
  "/documents": "Tài liệu",
  "/councils": "Hội đồng & Phiên",
  "/reviews": "Nhận xét",
  "/scoring": "Chấm điểm",
  "/minutes": "Biên bản",
  "/archive": "Kho & Báo cáo",
  "/ai": "Chatbot AI",
  "/similarity": "Tìm tương đồng",
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
            aria-label="Toggle sidebar"
          >
            <Menu size={20} />
          </button>
          <nav className="header__breadcrumb" aria-label="Breadcrumb">
            Workspace
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
