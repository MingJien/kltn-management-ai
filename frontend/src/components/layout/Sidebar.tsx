import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { BookOpen, Bot, CalendarDays, ChevronDown, ClipboardList, FileText, FolderOpen, GraduationCap, LayoutDashboard, UserRound, UsersRound, ShieldCheck } from "lucide-react";
import type { Context } from "../../api";
import { plannedPages, type PlannedPageId } from "../../plannedPages";
import { roleLabel } from "./roleLabel";

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
function PlannedLink({id, icon, onClose}: {id: PlannedPageId; icon: ReactNode; onClose: () => void}) {
  return <NavLink to={`/planned/${id}`} className={({isActive}) => `sidebar__item sidebar__item--planned ${isActive ? "sidebar__item--active" : ""}`}
    onClick={onClose}>
    {icon}<span className="sidebar__item-copy"><span>{plannedPages[id].title}</span><small>Đang phát triển</small></span>
  </NavLink>;
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
          <img className="sidebar__brand-mark" src="/assets/dthu-logo.png" alt="Đại học Đồng Tháp" />
          <span className="sidebar__brand-eyebrow">HỆ THỐNG QUẢN LÝ</span>
          <strong className="sidebar__brand-title">Khóa luận Tốt nghiệp</strong>
          <span className="sidebar__brand-faculty">Khoa Công nghệ và Kỹ thuật</span>
        </div>
        <nav className="sidebar__nav" aria-label="Chức năng">
          <SidebarGroup label="TỔNG QUAN" active={pathname === "/" || pathname === "/planned/reports"}>
            <NavLink to="/" end className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><LayoutDashboard aria-hidden="true" /><span>Tổng quan</span></NavLink>
            {workflowAccess ? <PlannedLink id="reports" icon={<ClipboardList aria-hidden="true" />} onClose={onClose} /> : null}
          </SidebarGroup>
          {workflowAccess ? <>
            <SidebarGroup label="ĐỀ TÀI VÀ ĐĂNG KÝ" active={["/topics", "/registrations", "/theses", "/proposals", "/progress", "/documents", "/planned/changes"].includes(pathname) || pathname.startsWith("/theses/")}>
              <NavLink to="/topics" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><FileText aria-hidden="true" /><span>{topicLabel}</span></NavLink>
              <NavLink to="/registrations" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><ClipboardList aria-hidden="true" /><span>{context.base_role === "STUDENT" ? "Đăng ký của tôi" : "Hồ sơ đăng ký"}</span></NavLink>
              <NavLink to="/theses" end className={({isActive}) => "sidebar__item " + (isActive || pathname.startsWith("/theses/") ? "sidebar__item--active" : "")}
                onClick={onClose}><GraduationCap aria-hidden="true" /><span>Khóa luận & GVHD</span></NavLink>
              <NavLink to="/proposals" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><BookOpen aria-hidden="true" /><span>Đề cương</span></NavLink>
              <NavLink to="/progress" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><ClipboardList aria-hidden="true" /><span>Tiến độ</span></NavLink>
              <NavLink to="/documents" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><FolderOpen aria-hidden="true" /><span>Tài liệu</span></NavLink>
              <PlannedLink id="changes" icon={<FileText aria-hidden="true" />} onClose={onClose} />
            </SidebarGroup>
            <SidebarGroup label="BẢO VỆ VÀ ĐÁNH GIÁ" active={["council", "defense", "evaluation", "results"].some(id => pathname === `/planned/${id}`)}>
              <PlannedLink id="council" icon={<UsersRound aria-hidden="true" />} onClose={onClose} />
              <PlannedLink id="defense" icon={<CalendarDays aria-hidden="true" />} onClose={onClose} />
              <PlannedLink id="evaluation" icon={<ClipboardList aria-hidden="true" />} onClose={onClose} />
              <PlannedLink id="results" icon={<FileText aria-hidden="true" />} onClose={onClose} />
            </SidebarGroup>
            <SidebarGroup label="THỬ NGHIỆM AI" active={pathname === "/ai" || ["repository", "chatbot", "similarity"].some(id => pathname === `/planned/${id}`)}>
              <NavLink to="/ai" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><Bot aria-hidden="true" /><span>Tra cứu tài liệu</span></NavLink>
              <PlannedLink id="repository" icon={<BookOpen aria-hidden="true" />} onClose={onClose} />
              <PlannedLink id="chatbot" icon={<Bot aria-hidden="true" />} onClose={onClose} />
              <PlannedLink id="similarity" icon={<FileText aria-hidden="true" />} onClose={onClose} />
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
          <SidebarGroup label="TÀI KHOẢN" active={pathname === "/account" || pathname === "/planned/expertise"}>
            <NavLink to="/account" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><UserRound aria-hidden="true" /><span>Thông tin của tôi</span></NavLink>
            {context.base_role === "LECTURER" ? <PlannedLink id="expertise" icon={<BookOpen aria-hidden="true" />} onClose={onClose} /> : null}
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
