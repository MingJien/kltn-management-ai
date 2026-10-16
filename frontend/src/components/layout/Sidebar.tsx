import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Bot, CalendarDays, ChevronDown, ClipboardList, FileText, LayoutDashboard, UserRound, UsersRound, ShieldCheck } from "lucide-react";
import type { Context } from "../../api";

function SidebarGroup({label, active, children}: {label: string; active: boolean; children: ReactNode}) {
  const [expanded, setExpanded] = useState(true);
  const id = `sidebar-group-${label.toLocaleLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  useEffect(() => { if (active) setExpanded(true); }, [active]);
  return <div className="sidebar__group">
    <button type="button" className="sidebar__group-label" aria-expanded={expanded} aria-controls={id}
      onClick={() => setExpanded(value => !value)}>
      <span>{label}</span><ChevronDown size={14} aria-hidden="true" />
    </button>
    <div id={id} className="sidebar__group-items" hidden={!expanded}>{children}</div>
  </div>;
}
export function roleLabel(context: Context) {
  return context.actions.includes("topic:department_decide") ? "Trưởng bộ môn"
    : context.base_role === "STUDENT" ? "Sinh viên"
    : context.base_role === "LECTURER" ? "Giảng viên" : "Quản trị";
}
export default function Sidebar({context, isOpen, onClose}: {
  context: Context; isOpen: boolean; onClose: () => void;
}) {
  const {pathname} = useLocation();
  const workflowAccess = context.base_role === "STUDENT" || context.base_role === "LECTURER";
  const topicLabel = context.actions.includes("topic:department_decide") ? "Đề tài và duyệt"
    : context.base_role === "STUDENT" ? "Chọn đề tài" : "Đề tài của tôi";
  return <>
    <div className={"sidebar-overlay " + (isOpen ? "sidebar-overlay--visible" : "")} onClick={onClose} aria-hidden="true" />
    <aside className={"app-shell__sidebar " + (isOpen ? "sidebar--open" : "")} aria-label="Điều hướng chính">
      <div className="sidebar">
        <div className="sidebar__brand">
          <div className="sidebar__brand-mark">K</div>
          <div className="sidebar__brand-text"><strong>KLTN</strong><span>Quản lý Khóa luận</span></div>
        </div>
        <nav className="sidebar__nav" aria-label="Chức năng">
          <SidebarGroup label="TỔNG QUAN" active={pathname === "/"}>
            <NavLink to="/" end className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><LayoutDashboard aria-hidden="true" /><span>Tổng quan</span></NavLink>
          </SidebarGroup>
          {workflowAccess ? <>
            <SidebarGroup label="ĐỀ TÀI VÀ ĐĂNG KÝ" active={["/topics", "/registrations", "/theses"].includes(pathname)}>
              <NavLink to="/topics" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><FileText aria-hidden="true" /><span>{topicLabel}</span></NavLink>
              <NavLink to="/registrations" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><ClipboardList aria-hidden="true" /><span>{context.base_role === "STUDENT" ? "Đăng ký của tôi" : "Hồ sơ đăng ký"}</span></NavLink>
              <NavLink to="/theses" className={({isActive}) => "sidebar__item " + (isActive || pathname.startsWith("/theses/") ? "sidebar__item--active" : "")}
                onClick={onClose}><FileText aria-hidden="true" /><span>Khóa luận, GVHD & tiến độ</span></NavLink>
            </SidebarGroup>
            <SidebarGroup label="THỬ NGHIỆM AI" active={pathname === "/ai"}>
              <NavLink to="/ai" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><Bot aria-hidden="true" /><span>Tra cứu tài liệu</span></NavLink>
            </SidebarGroup>
          </> : null}
          {context.actions.includes("account:manage") ? <SidebarGroup label="QUẢN TRỊ" active={["/administration", "/rounds"].includes(pathname)}>
            <NavLink to="/administration" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><UsersRound aria-hidden="true" /><span>Tài khoản và phân công</span></NavLink>
            <NavLink to="/rounds" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><CalendarDays aria-hidden="true" /><span>Đợt KLTN</span></NavLink>
          </SidebarGroup> : null}
          {context.actions.some(a=>a.startsWith("eligibility:")) ? <SidebarGroup label="ĐIỀU KIỆN THEO ĐỢT" active={pathname === "/roster"}>
            <NavLink to="/roster" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><ShieldCheck aria-hidden="true" /><span>Danh sách sinh viên</span></NavLink>
          </SidebarGroup> : null}
          <SidebarGroup label="TÀI KHOẢN" active={pathname === "/account"}>
            <NavLink to="/account" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><UserRound aria-hidden="true" /><span>Thông tin của tôi</span></NavLink>
          </SidebarGroup>
        </nav>
        <div className="sidebar__footer"><div className="sidebar__user">
          <div className="sidebar__avatar" aria-hidden="true">{context.display_name.charAt(0).toUpperCase()}</div>
          <div className="sidebar__user-info"><span className="sidebar__user-name">{context.display_name}</span>
            <span className="sidebar__user-role">{roleLabel(context)}</span></div>
        </div></div>
      </div>
    </aside>
  </>;
}
