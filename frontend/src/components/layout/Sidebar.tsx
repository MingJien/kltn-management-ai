import { NavLink } from "react-router-dom";
import { Bot, ClipboardList, FileText, LayoutDashboard, UserRound, UsersRound, ShieldCheck } from "lucide-react";
import type { Context } from "../../api";
export function roleLabel(context: Context) {
  return context.actions.includes("topic:department_decide") ? "Trưởng bộ môn"
    : context.base_role === "STUDENT" ? "Sinh viên"
    : context.base_role === "LECTURER" ? "Giảng viên" : "Quản trị";
}
export default function Sidebar({context, isOpen, onClose}: {
  context: Context; isOpen: boolean; onClose: () => void;
}) {
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
          <div className="sidebar__group">
            <div className="sidebar__group-label">TỔNG QUAN</div>
            <NavLink to="/" end className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><LayoutDashboard aria-hidden="true" /><span>Tổng quan</span></NavLink>
          </div>
          {workflowAccess ? <>
            <div className="sidebar__group">
              <div className="sidebar__group-label">ĐỀ TÀI VÀ ĐĂNG KÝ</div>
              <NavLink to="/topics" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><FileText aria-hidden="true" /><span>{topicLabel}</span></NavLink>
              <NavLink to="/registrations" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><ClipboardList aria-hidden="true" /><span>{context.base_role === "STUDENT" ? "Đăng ký của tôi" : "Hồ sơ đăng ký"}</span></NavLink>
            </div>
            <div className="sidebar__group">
              <div className="sidebar__group-label">THỬ NGHIỆM AI</div>
              <NavLink to="/ai" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
                onClick={onClose}><Bot aria-hidden="true" /><span>Tra cứu tài liệu</span></NavLink>
            </div>
          </> : null}
          {context.actions.includes("account:manage") ? <div className="sidebar__group">
            <div className="sidebar__group-label">QUẢN TRỊ</div>
            <NavLink to="/administration" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><UsersRound aria-hidden="true" /><span>Tài khoản và phân công</span></NavLink>
          </div> : null}
          {context.actions.some(a=>a.startsWith("eligibility:")) ? <div className="sidebar__group">
            <div className="sidebar__group-label">ĐIỀU KIỆN THEO ĐỢT</div>
            <NavLink to="/roster" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><ShieldCheck aria-hidden="true" /><span>Danh sách sinh viên</span></NavLink>
          </div> : null}
          <div className="sidebar__group">
            <div className="sidebar__group-label">TÀI KHOẢN</div>
            <NavLink to="/account" className={({isActive}) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")}
              onClick={onClose}><UserRound aria-hidden="true" /><span>Thông tin của tôi</span></NavLink>
          </div>
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
