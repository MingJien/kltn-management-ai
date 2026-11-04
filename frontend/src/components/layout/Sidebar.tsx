import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { BookOpen, Bot, CalendarDays, ChevronsLeft, ChevronsRight, ChevronDown, ClipboardList, FileText, FolderOpen, GraduationCap, History, LayoutDashboard, UserRound, UsersRound, ShieldCheck } from "lucide-react";
import type { Context, Thesis } from "../../api";
import { request } from "../../api";
import { plannedPages, type PlannedPageId } from "../../plannedPages";
import { roleLabel } from "./roleLabel";
import { initialsOf } from "./initials";
import LecturerAvatar from "../domain/LecturerAvatar";

function SidebarGroup({label, active, collapsed, defaultOpen = true, children}: {label: string; active: boolean; collapsed: boolean; defaultOpen?: boolean; children: ReactNode}) {
  const [open, setOpen] = useState(active ? true : defaultOpen);
  const id = `sidebar-group-${label.toLocaleLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  useEffect(() => { if (active) setOpen(true); }, [active]);
  const expanded = collapsed ? true : open;
  return <div className="sidebar__group">
    {collapsed ? null : (
      <button type="button" className="sidebar__group-label" aria-expanded={open} aria-controls={id}
        onClick={() => setOpen(value => !value)}>
        <span>{label}</span><ChevronDown size={14} aria-hidden="true" />
      </button>
    )}
    <div id={id} className="sidebar__group-items" hidden={!expanded}>{children}</div>
  </div>;
}
function PlannedLink({id, icon, onClose, collapsed}: {id: PlannedPageId; icon: ReactNode; onClose: () => void; collapsed: boolean}) {
  return <NavLink to={`/planned/${id}`} className={({isActive}) => `sidebar__item sidebar__item--planned ${isActive ? "sidebar__item--active" : ""}`}
    title={collapsed ? plannedPages[id].title : undefined}
    onClick={onClose}>
    {icon}<span className="sidebar__item-copy"><span>{plannedPages[id].title}</span><small>Đang phát triển</small></span>
  </NavLink>;
}
export default function Sidebar({context, isOpen, collapsed, onToggleCollapsed, onClose}: {
  context: Context; isOpen: boolean; collapsed: boolean; onToggleCollapsed: () => void; onClose: () => void;
}) {
  const location = useLocation();
  const pathname = location.pathname;
  const searchParams = new URLSearchParams(location.search);
  const currentSection = searchParams.get("section") || "overview";
  const isThesisDetail = pathname.startsWith("/theses/");
  const thesisIdMatch = pathname.match(/^\/theses\/([a-zA-Z0-9-]+)/);
  const detailThesisId = thesisIdMatch ? thesisIdMatch[1] : null;
  const storageKey = `kltn_active_thesis_id_${context.user_id}`;
  const [activeThesisId, setActiveThesisId] = useState<string | null>(() => {
    return detailThesisId || (typeof sessionStorage !== "undefined" ? sessionStorage.getItem(storageKey) : null);
  });

  const workflowAccess = context.base_role === "STUDENT" || context.base_role === "LECTURER";

  useEffect(() => {
    if (detailThesisId) {
      setActiveThesisId(detailThesisId);
      if (typeof sessionStorage !== "undefined") {
        sessionStorage.setItem(storageKey, detailThesisId);
      }
    }
  }, [detailThesisId, storageKey]);

  useEffect(() => {
    if (workflowAccess && !activeThesisId && context.user_id) {
      const controller = new AbortController();
      request<Thesis[]>("/theses", context.user_id, {signal: controller.signal})
        .then(rows => {
          if (rows.length === 1) {
            setActiveThesisId(rows[0].id);
            if (typeof sessionStorage !== "undefined") {
              sessionStorage.setItem(storageKey, rows[0].id);
            }
          }
        })
        .catch(() => {});
      return () => controller.abort();
    }
  }, [workflowAccess, activeThesisId, context.user_id, storageKey]);

  const topicLabel = context.actions.includes("topic:department_decide") ? "Đề tài và duyệt"
    : context.base_role === "STUDENT" ? "Chọn đề tài" : "Đề tài của tôi";
  const collapseTitle = collapsed ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng";

  const isThesesActive = pathname === "/theses" || (isThesisDetail && currentSection === "overview");
  const isProgressActive = pathname === "/progress" || (isThesisDetail && currentSection === "progress");
  const isSubmissionsActive = ["/submissions", "/proposals", "/documents"].includes(pathname) || (isThesisDetail && ["submissions", "proposal", "documents"].includes(currentSection));

  const progressLabel = context.actions.includes("progress:coordinate") ? "Mốc & báo cáo tiến độ" : "Báo cáo tiến độ";
  const progressPath = context.base_role === "STUDENT" && activeThesisId ? `/theses/${activeThesisId}?section=progress` : "/progress";

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
          <SidebarGroup label="TỔNG QUAN" active={pathname === "/" || pathname === "/activity" || pathname === "/planned/reports"} collapsed={collapsed}>
            <NavLink to="/" end title={collapsed ? "Tổng quan" : undefined} className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><LayoutDashboard aria-hidden="true" /><span>Tổng quan</span></NavLink>
            {workflowAccess ? <PlannedLink id="reports" collapsed={collapsed} icon={<ClipboardList aria-hidden="true" />} onClose={onClose} /> : null}
            <NavLink to="/activity" title={collapsed ? "Nhật ký hoạt động" : undefined} className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><History aria-hidden="true" /><span>{context.base_role === "ADMIN" ? "Nhật ký hệ thống" : "Lịch sử hoạt động"}</span></NavLink>
          </SidebarGroup>
          {context.base_role === "ADMIN" && <SidebarGroup label="DANH SÁCH ĐỀ TÀI" active={pathname === "/topics"} collapsed={collapsed}><NavLink to="/topics" className={({isActive})=>"sidebar__item "+(isActive?"sidebar__item--active":"")} onClick={onClose}><FileText aria-hidden="true"/><span>Đề tài đã công bố</span></NavLink></SidebarGroup>}
          {workflowAccess ? <>
            <SidebarGroup label="ĐỀ TÀI VÀ ĐĂNG KÝ" active={["/topics", "/registrations", "/withdrawals", "/planned/changes"].includes(pathname)} collapsed={collapsed}>
              <NavLink to="/lecturers" className={({isActive})=>"sidebar__item "+(isActive?"sidebar__item--active":"")} onClick={onClose}><UsersRound aria-hidden="true"/><span>Danh sách giảng viên</span></NavLink>
              <NavLink to="/topics" title={collapsed ? topicLabel : undefined} className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><FileText aria-hidden="true" /><span>{topicLabel}</span></NavLink>
              <NavLink to="/registrations" title={collapsed ? "Đăng ký" : undefined} className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><ClipboardList aria-hidden="true" /><span>{context.base_role === "STUDENT" ? "Đăng ký của tôi" : "Hồ sơ đăng ký"}</span></NavLink>
              <NavLink to="/withdrawals" className={({isActive})=>"sidebar__item "+(isActive?"sidebar__item--active":"")} onClick={onClose}><FileText aria-hidden="true"/><span>Xin thôi KLTN</span></NavLink>
              <PlannedLink id="changes" collapsed={collapsed} icon={<FileText aria-hidden="true" />} onClose={onClose} />
            </SidebarGroup>
            <SidebarGroup label="HỒ SƠ KHÓA LUẬN" active={["/theses", "/submissions", "/proposals", "/progress", "/documents"].includes(pathname) || isThesisDetail} collapsed={collapsed}>
              <NavLink to="/theses" end title={collapsed ? "Khóa luận & GVHD" : undefined} className={() => "sidebar__item " + (isThesesActive ? "sidebar__item--active" : "")}
                onClick={onClose}><GraduationCap aria-hidden="true" /><span>Khóa luận & GVHD</span></NavLink>
              <NavLink to="/submissions" title={collapsed ? "Hồ sơ nộp & xét duyệt" : undefined} className={() => "sidebar__item " + (isSubmissionsActive ? "sidebar__item--active" : "")}
                onClick={onClose}><FolderOpen aria-hidden="true" /><span>Hồ sơ nộp & xét duyệt</span></NavLink>
              <NavLink to={progressPath} title={collapsed ? progressLabel : undefined} className={() => "sidebar__item " + (isProgressActive ? "sidebar__item--active" : "")}
                onClick={onClose}><ClipboardList aria-hidden="true" /><span>{progressLabel}</span></NavLink>
            </SidebarGroup>
            <SidebarGroup label="BẢO VỆ VÀ ĐÁNH GIÁ" active={pathname.startsWith("/evaluation") || pathname==="/review-records" || pathname==="/defense"} collapsed={collapsed} defaultOpen={true}>
              {context.actions.includes("evaluation:record") && <NavLink to="/review-records" className={({isActive})=>"sidebar__item "+(isActive?"sidebar__item--active":"")} onClick={onClose}><ClipboardList aria-hidden="true"/><span>Tiếp nhận hồ sơ phản biện</span></NavLink>}
              <NavLink to="/evaluation" title={collapsed ? "Phản biện & điều kiện bảo vệ" : undefined} className={({isActive})=>"sidebar__item "+(isActive?"sidebar__item--active":"")} onClick={onClose}><ClipboardList aria-hidden="true"/><span>Phản biện & điều kiện bảo vệ</span></NavLink>
              <NavLink to="/defense" title={collapsed ? "Hội đồng và bảo vệ" : undefined} className={({isActive})=>"sidebar__item "+(isActive?"sidebar__item--active":"")} onClick={onClose}><CalendarDays aria-hidden="true"/><span>Hội đồng và bảo vệ</span></NavLink>
            </SidebarGroup>
            <SidebarGroup label="THỬ NGHIỆM AI" active={pathname === "/ai" || ["repository", "chatbot", "similarity"].some(id => pathname === `/planned/${id}`)} collapsed={collapsed}>
              <NavLink to="/ai" title={collapsed ? "Tra cứu tài liệu" : undefined} className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><Bot aria-hidden="true" /><span>Tra cứu tài liệu</span></NavLink>
              <PlannedLink id="repository" collapsed={collapsed} icon={<BookOpen aria-hidden="true" />} onClose={onClose} />
              <PlannedLink id="chatbot" collapsed={collapsed} icon={<Bot aria-hidden="true" />} onClose={onClose} />
              <PlannedLink id="similarity" collapsed={collapsed} icon={<FileText aria-hidden="true" />} onClose={onClose} />
            </SidebarGroup>
          </> : null}
          <SidebarGroup label="TÀI LIỆU KHOA" active={pathname === "/forms"} collapsed={collapsed}>
            <NavLink to="/forms" title={collapsed ? "Kho biểu mẫu & tài liệu Khoa" : undefined} className={({isActive})=>"sidebar__item "+(isActive?"sidebar__item--active":"")} onClick={onClose}><FolderOpen aria-hidden="true"/><span>{context.actions.includes("forms:manage")?"Quản lý kho biểu mẫu Khoa":"Kho biểu mẫu & tài liệu Khoa"}</span></NavLink>
          </SidebarGroup>
          {context.actions.includes("account:manage") ? <SidebarGroup label="QUẢN TRỊ" active={["/administration", "/administration/assignments", "/rounds", "/lecturers", "/positions"].includes(pathname)} collapsed={collapsed}>
            <NavLink to="/administration" end title={collapsed ? "Tài khoản" : undefined} className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><UsersRound aria-hidden="true" /><span>Tài khoản</span></NavLink>
            {context.base_role === "ADMIN" && <NavLink to="/administration/assignments" title={collapsed ? "Phân công" : undefined} className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><ClipboardList aria-hidden="true" /><span>Phân công theo đợt</span></NavLink>}
            {context.base_role === "ADMIN" && <NavLink to="/positions" className={({isActive})=>"sidebar__item "+(isActive?"sidebar__item--active":"")} onClick={onClose}><ShieldCheck aria-hidden="true"/><span>Chức vụ và phạm vi</span></NavLink>}
            {context.base_role === "ADMIN" ? <NavLink to="/rounds" title={collapsed ? "Đợt KLTN" : undefined} className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><CalendarDays aria-hidden="true" /><span>Đợt KLTN</span></NavLink> : null}
            {context.base_role === "ADMIN" && <NavLink to="/lecturers" className={({isActive})=>"sidebar__item "+(isActive?"sidebar__item--active":"")} onClick={onClose}><GraduationCap aria-hidden="true"/><span>Danh sách giảng viên</span></NavLink>}
          </SidebarGroup> : null}
          {context.actions.some(a=>a.startsWith("eligibility:")) ? <SidebarGroup label="ĐIỀU KIỆN THEO ĐỢT" active={pathname === "/roster"} collapsed={collapsed}>
            <NavLink to="/roster" title={collapsed ? "Danh sách sinh viên" : undefined} className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><ShieldCheck aria-hidden="true" /><span>Danh sách sinh viên</span></NavLink>
          </SidebarGroup> : null}
          <SidebarGroup label="TÀI KHOẢN" active={pathname === "/account" || pathname === "/planned/expertise"} collapsed={collapsed}>
            {context.actions.includes("lecturer:profile_review")&&<NavLink to="/lecturer-profile-reviews" className={({isActive})=>"sidebar__item "+(isActive?"sidebar__item--active":"")} onClick={onClose}><ShieldCheck aria-hidden="true"/><span>Duyệt hồ sơ giảng viên</span></NavLink>}
            <NavLink to="/account" title={collapsed ? "Thông tin của tôi" : undefined} className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><UserRound aria-hidden="true" /><span>Thông tin của tôi</span></NavLink>
            {context.base_role === "LECTURER" ? <NavLink to="/account?section=lecturer-profile" className="sidebar__item" onClick={onClose}><BookOpen aria-hidden="true"/><span>Hồ sơ chuyên môn của tôi</span></NavLink> : null}
          </SidebarGroup>
        </nav>
        <div className="sidebar__footer">
          <Link to="/account" className="sidebar__user" aria-label="Quản lý tài khoản" title="Quản lý tài khoản" onClick={onClose}>
            <span className="sidebar__avatar" aria-hidden="true">{context.base_role==="LECTURER"?<LecturerAvatar url={context.avatar_url} name={context.display_name} size="sm"/>:initialsOf(context.display_name)}</span>
            <span className="sidebar__user-info"><span className="sidebar__user-name">{context.display_name}</span>
              <span className="sidebar__user-role">{roleLabel(context)}</span></span>
          </Link>
          <button type="button" className="sidebar__collapse" onClick={onToggleCollapsed}
            aria-label={collapseTitle} aria-pressed={collapsed} title={collapseTitle}>
            {collapsed ? <ChevronsRight size={16} aria-hidden="true" /> : <ChevronsLeft size={16} aria-hidden="true" />}
          </button>
        </div>
      </div>
    </aside>
  </>;
}
