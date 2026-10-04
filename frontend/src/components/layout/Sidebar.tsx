import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, BookOpen, Users, FileText, ClipboardList,
  FileCheck, Clock, FolderOpen, Scale, UserCheck, MessageSquare,
  PenTool, FileSpreadsheet, Archive, Bot, Search,
} from "lucide-react";
import type { Context } from "../../api";

const NAV_GROUPS = [
  {
    label: "TỔNG QUAN",
    items: [
      { to: "/", icon: LayoutDashboard, label: "Workspace", end: true },
    ],
  },
  {
    label: "QUẢN LÝ",
    items: [
      { to: "/rounds", icon: BookOpen, label: "Đợt & Năm học" },
      { to: "/eligibility", icon: UserCheck, label: "Điều kiện SV" },
      { to: "/topics", icon: FileText, label: "Đề tài" },
      { to: "/registrations", icon: ClipboardList, label: "Đăng ký" },
    ],
  },
  {
    label: "KHÓA LUẬN",
    items: [
      { to: "/proposals", icon: FileCheck, label: "Đề cương" },
      { to: "/progress", icon: Clock, label: "Tiến độ" },
      { to: "/documents", icon: FolderOpen, label: "Tài liệu" },
    ],
  },
  {
    label: "HỘI ĐỒNG",
    items: [
      { to: "/councils", icon: Scale, label: "Hội đồng & Phiên" },
      { to: "/reviews", icon: MessageSquare, label: "Nhận xét" },
      { to: "/scoring", icon: PenTool, label: "Chấm điểm" },
      { to: "/minutes", icon: FileSpreadsheet, label: "Biên bản" },
    ],
  },
  {
    label: "TRA CỨU",
    items: [
      { to: "/archive", icon: Archive, label: "Kho & Báo cáo" },
      { to: "/ai", icon: Bot, label: "Chatbot AI" },
      { to: "/similarity", icon: Search, label: "Tìm tương đồng" },
    ],
  },
];

interface SidebarProps {
  context: Context | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ context, isOpen, onClose }: SidebarProps) {
  const location = useLocation();

  return (
    <>
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${isOpen ? "sidebar-overlay--visible" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        className={`app-shell__sidebar ${isOpen ? "sidebar--open" : ""}`}
        aria-label="Sidebar navigation"
      >
        <div className="sidebar">
          {/* Brand */}
          <div className="sidebar__brand">
            <div className="sidebar__brand-mark">K</div>
            <div className="sidebar__brand-text">
              <strong>KLTN</strong>
              <span>Quản lý Khóa luận</span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="sidebar__nav">
            {NAV_GROUPS.map((group) => (
              <div className="sidebar__group" key={group.label}>
                <div className="sidebar__group-label">{group.label}</div>
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) =>
                      `sidebar__item ${isActive ? "sidebar__item--active" : ""}`
                    }
                    onClick={onClose}
                  >
                    <item.icon />
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>

          {/* User panel */}
          {context && (
            <div className="sidebar__footer">
              <div className="sidebar__user">
                <div className="sidebar__avatar">
                  {context.display_name.charAt(0).toUpperCase()}
                </div>
                <div className="sidebar__user-info">
                  <span className="sidebar__user-name">{context.display_name}</span>
                  <span className="sidebar__user-role">
                    {context.actions.includes("topic:department_decide") ? "Trưởng bộ môn" : context.base_role === "STUDENT" ? "Sinh viên" : context.base_role === "LECTURER" ? "Giảng viên" : "Quản trị"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
