import { useEffect, useState, type ReactNode, type Ref } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  ArrowLeftRight,
  Award,
  BadgeCheck,
  BookOpen,
  Bot,
  Briefcase,
  CalendarDays,
  CalendarRange,
  ChartColumn,
  ChevronsLeft,
  ChevronsRight,
  ChevronDown,
  ClipboardList,
  FileX,
  FolderOpen,
  GraduationCap,
  History,
  Inbox,
  LayoutDashboard,
  Lightbulb,
  ListChecks,
  Scale,
  ShieldCheck,
  UserCog,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import type { Context, Thesis } from "../../api";
import { request } from "../../api";
import { roleLabel } from "./roleLabel";
import { initialsOf } from "./initials";
import LecturerAvatar from "../domain/LecturerAvatar";
import { SidebarLotusArt } from "../ui/CampusArtwork";

function SidebarGroup({
  label,
  active,
  collapsed,
  defaultOpen = true,
  children,
}: {
  label: string;
  active: boolean;
  collapsed: boolean;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(active ? true : defaultOpen);
  const id = `sidebar-group-${label.toLocaleLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  useEffect(() => {
    if (active) setOpen(true);
  }, [active]);
  const expanded = collapsed ? true : open;
  return (
    <div className="sidebar__group">
      {collapsed ? null : (
        <button
          type="button"
          className="sidebar__group-label"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((value) => !value)}
        >
          <span>{label}</span>
          <ChevronDown size={14} aria-hidden="true" />
        </button>
      )}
      <div id={id} className="sidebar__group-items" hidden={!expanded}>
        {children}
      </div>
    </div>
  );
}

export default function Sidebar({
  context,
  isOpen,
  collapsed,
  closeButton,
  onToggleCollapsed,
  onClose,
}: {
  closeButton: Ref<HTMLButtonElement>;
  context: Context;
  isOpen: boolean;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onClose: () => void;
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

  const isStudent = context.base_role === "STUDENT";
  const isLecturer = context.base_role === "LECTURER";
  const isAdmin = context.base_role === "ADMIN";
  const workflowAccess = isStudent || isLecturer;

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
      request<Thesis[]>("/theses", context.user_id, { signal: controller.signal })
        .then((rows) => {
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

  const topicLabel = context.actions.includes("topic:department_decide")
    ? "Đề tài & duyệt"
    : isStudent
      ? "Chọn đề tài"
      : "Đề tài của tôi";
  const collapseTitle = collapsed ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng";

  const isThesesActive = pathname === "/theses" || (isThesisDetail && currentSection === "overview");
  const isProgressActive = pathname === "/progress" || (isThesisDetail && currentSection === "progress");
  const isSubmissionsActive =
    ["/submissions", "/proposals", "/documents"].includes(pathname) ||
    (isThesisDetail && ["submissions", "proposal", "documents"].includes(currentSection));

  const isLecturerProfileActive = pathname === "/account" && currentSection === "lecturer-profile";
  const progressLabel = context.actions.includes("progress:coordinate") ? "Mốc & báo cáo tiến độ" : "Báo cáo tiến độ";
  const progressPath = isStudent && activeThesisId ? `/theses/${activeThesisId}?section=progress` : "/progress";
  const submissionsPath = isStudent && activeThesisId ? `/theses/${activeThesisId}?section=submissions` : "/submissions";
  const thesisHomePath = isStudent && activeThesisId ? `/theses/${activeThesisId}` : "/theses";

  return (
    <>
      <div className={"sidebar-overlay " + (isOpen ? "sidebar-overlay--visible" : "")} onClick={onClose} aria-hidden="true" />
      <aside id="main-sidebar" className={"app-shell__sidebar " + (isOpen ? "sidebar--open" : "")} aria-label="Điều hướng chính">
        <div className="sidebar">
          <button type="button" className="sidebar__mobile-close" ref={closeButton} aria-label="Đóng menu điều hướng" onClick={onClose}>
            <X size={20} aria-hidden="true" />
          </button>
          <div className="sidebar__brand">
            <span className="sidebar__brand-mark-wrap">
              <img className="sidebar__brand-mark" src="/assets/dthu-logo.png" alt="Đại học Đồng Tháp" />
            </span>
            <span className="sidebar__brand-eyebrow">ĐẠI HỌC ĐỒNG THÁP</span>
            <strong className="sidebar__brand-title">Khóa luận Tốt nghiệp</strong>
            <span className="sidebar__brand-faculty">Khoa Công nghệ và Kỹ thuật</span>
          </div>

          <nav className="sidebar__nav" aria-label="Chức năng">
            {/* ── SINH VIÊN: Hành trình cá nhân & Không gian khóa luận ── */}
            {isStudent && (
              <>
                <SidebarGroup
                  label="KHÔNG GIAN HỌC TẬP"
                  active={["/", "/theses", "/submissions", "/proposals", "/progress", "/documents"].includes(pathname) || isThesisDetail}
                  collapsed={collapsed}
                >
                  <NavLink to="/" end title={collapsed ? "Tổng quan" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <LayoutDashboard aria-hidden="true" />
                    <span>Tổng quan</span>
                  </NavLink>
                  <NavLink to={thesisHomePath} end title={collapsed ? "Khóa luận & GVHD" : undefined} className={() => "sidebar__item " + (isThesesActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <GraduationCap aria-hidden="true" />
                    <span>Khóa luận &amp; GVHD</span>
                  </NavLink>
                  <NavLink to={submissionsPath} title={collapsed ? "Hồ sơ nộp & xét duyệt" : undefined} className={() => "sidebar__item " + (isSubmissionsActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <FolderOpen aria-hidden="true" />
                    <span>Hồ sơ nộp &amp; xét duyệt</span>
                  </NavLink>
                  <NavLink to={progressPath} title={collapsed ? progressLabel : undefined} className={() => "sidebar__item " + (isProgressActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <ListChecks aria-hidden="true" />
                    <span>{progressLabel}</span>
                  </NavLink>
                </SidebarGroup>

                <SidebarGroup
                  label="ĐỀ TÀI VÀ ĐĂNG KÝ"
                  active={["/topics", "/registrations", "/changes", "/withdrawals"].includes(pathname)}
                  collapsed={collapsed}
                >
                  <NavLink to="/topics" title={collapsed ? topicLabel : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <Lightbulb aria-hidden="true" />
                    <span>{topicLabel}</span>
                  </NavLink>
                  <NavLink to="/registrations" title={collapsed ? "Đăng ký của tôi" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <ClipboardList aria-hidden="true" />
                    <span>Đăng ký của tôi</span>
                  </NavLink>
                  <NavLink to="/changes" title={collapsed ? "Đổi đề tài & gia hạn" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <ArrowLeftRight aria-hidden="true" />
                    <span>Đổi đề tài &amp; gia hạn</span>
                  </NavLink>
                  <NavLink to="/withdrawals" title={collapsed ? "Xin thôi KLTN" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <FileX aria-hidden="true" />
                    <span>Xin thôi KLTN</span>
                  </NavLink>
                </SidebarGroup>

                <SidebarGroup
                  label="BẢO VỆ VÀ LƯU TRỮ"
                  active={pathname.startsWith("/evaluation") || pathname === "/defense" || pathname === "/repository"}
                  collapsed={collapsed}
                >
                  <NavLink to="/evaluation" title={collapsed ? "Phản biện & điều kiện bảo vệ" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <Scale aria-hidden="true" />
                    <span>Phản biện &amp; điều kiện bảo vệ</span>
                  </NavLink>
                  <NavLink to="/defense" title={collapsed ? "Hội đồng và bảo vệ" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <CalendarDays aria-hidden="true" />
                    <span>Hội đồng và bảo vệ</span>
                  </NavLink>
                  <NavLink to="/repository" title={collapsed ? "Kho khóa luận nội bộ" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <BookOpen aria-hidden="true" />
                    <span>Kho khóa luận nội bộ</span>
                  </NavLink>
                </SidebarGroup>

                <SidebarGroup
                  label="TRA CỨU VÀ CÁ NHÂN"
                  active={["/ai", "/forms", "/activity", "/account"].includes(pathname) || pathname.startsWith("/lecturers")}
                  collapsed={collapsed}
                >
                  <NavLink to="/ai" title={collapsed ? "Tra cứu AI" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <Bot aria-hidden="true" />
                    <span>Tra cứu AI</span>
                  </NavLink>
                  <NavLink to="/forms" title={collapsed ? "Tài liệu Khoa công bố" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <FolderOpen aria-hidden="true" />
                    <span>Tài liệu Khoa công bố</span>
                  </NavLink>
                  <NavLink to="/lecturers" title={collapsed ? "Danh sách giảng viên" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <UsersRound aria-hidden="true" />
                    <span>Danh sách giảng viên</span>
                  </NavLink>
                  <NavLink to="/activity" title={collapsed ? "Lịch sử hoạt động" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <History aria-hidden="true" />
                    <span>Lịch sử hoạt động</span>
                  </NavLink>
                  <NavLink to="/account" title={collapsed ? "Thông tin của tôi" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <UserRound aria-hidden="true" />
                    <span>Thông tin của tôi</span>
                  </NavLink>
                </SidebarGroup>
              </>
            )}

            {/* ── GIẢNG VIÊN / TRƯỞNG BỘ MÔN / LÃNH ĐẠO KHOA ── */}
            {isLecturer && (
              <>
                <SidebarGroup label="ĐIỀU PHỐI & TỔNG QUAN" active={["/", "/reports", "/activity"].includes(pathname)} collapsed={collapsed}>
                  <NavLink to="/" end title={collapsed ? "Tổng quan" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <LayoutDashboard aria-hidden="true" />
                    <span>Tổng quan</span>
                  </NavLink>
                  <NavLink to="/reports" title={collapsed ? "Báo cáo và thống kê" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <ChartColumn aria-hidden="true" />
                    <span>Báo cáo và thống kê</span>
                  </NavLink>
                  <NavLink to="/activity" title={collapsed ? "Lịch sử hoạt động" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <History aria-hidden="true" />
                    <span>Lịch sử hoạt động</span>
                  </NavLink>
                </SidebarGroup>

                <SidebarGroup label="ĐỀ TÀI VÀ ĐĂNG KÝ" active={["/topics", "/registrations", "/changes", "/withdrawals"].includes(pathname)} collapsed={collapsed}>
                  <NavLink to="/topics" title={collapsed ? topicLabel : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <Lightbulb aria-hidden="true" />
                    <span>{topicLabel}</span>
                  </NavLink>
                  <NavLink to="/registrations" title={collapsed ? "Hồ sơ đăng ký" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <ClipboardList aria-hidden="true" />
                    <span>Hồ sơ đăng ký</span>
                  </NavLink>
                  <NavLink to="/changes" title={collapsed ? "Đổi đề tài & gia hạn" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <ArrowLeftRight aria-hidden="true" />
                    <span>Đổi đề tài &amp; gia hạn</span>
                  </NavLink>
                  <NavLink to="/withdrawals" title={collapsed ? "Xin thôi KLTN" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <FileX aria-hidden="true" />
                    <span>Xin thôi KLTN</span>
                  </NavLink>
                </SidebarGroup>

                <SidebarGroup label="HƯỚNG DẪN KHÓA LUẬN" active={["/theses", "/submissions", "/proposals", "/progress", "/documents"].includes(pathname) || isThesisDetail} collapsed={collapsed}>
                  <NavLink to="/theses" end title={collapsed ? "Khóa luận & GVHD" : undefined} className={() => "sidebar__item " + (isThesesActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <GraduationCap aria-hidden="true" />
                    <span>Khóa luận &amp; GVHD</span>
                  </NavLink>
                  <NavLink to="/submissions" title={collapsed ? "Hồ sơ nộp & xét duyệt" : undefined} className={() => "sidebar__item " + (isSubmissionsActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <FolderOpen aria-hidden="true" />
                    <span>Hồ sơ nộp &amp; xét duyệt</span>
                  </NavLink>
                  <NavLink to="/progress" title={collapsed ? progressLabel : undefined} className={() => "sidebar__item " + (isProgressActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <ListChecks aria-hidden="true" />
                    <span>{progressLabel}</span>
                  </NavLink>
                </SidebarGroup>

                <SidebarGroup label="PHẢN BIỆN & HỘI ĐỒNG" active={pathname.startsWith("/evaluation") || ["/review-records", "/defense", "/repository"].includes(pathname)} collapsed={collapsed}>
                  {context.actions.includes("evaluation:record") && (
                    <NavLink to="/review-records" title={collapsed ? "Tiếp nhận hồ sơ phản biện" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                      <Inbox aria-hidden="true" />
                      <span>Tiếp nhận hồ sơ phản biện</span>
                    </NavLink>
                  )}
                  <NavLink to="/evaluation" title={collapsed ? "Phản biện & điều kiện bảo vệ" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <Scale aria-hidden="true" />
                    <span>Phản biện &amp; điều kiện bảo vệ</span>
                  </NavLink>
                  <NavLink to="/defense" title={collapsed ? "Hội đồng và bảo vệ" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <CalendarDays aria-hidden="true" />
                    <span>Hội đồng và bảo vệ</span>
                  </NavLink>
                  <NavLink to="/repository" title={collapsed ? "Kho khóa luận nội bộ" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <BookOpen aria-hidden="true" />
                    <span>Kho khóa luận nội bộ</span>
                  </NavLink>
                </SidebarGroup>

                {(context.actions.some((a) => a.startsWith("eligibility:")) || context.actions.includes("account:manage")) && (
                  <SidebarGroup label="PHÂN CÔNG THEO ĐỢT" active={["/roster", "/administration"].includes(pathname)} collapsed={collapsed}>
                    {context.actions.some((a) => a.startsWith("eligibility:")) && (
                      <NavLink to="/roster" title={collapsed ? "Danh sách sinh viên" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                        <ShieldCheck aria-hidden="true" />
                        <span>Danh sách sinh viên</span>
                      </NavLink>
                    )}
                    {context.actions.includes("account:manage") && (
                      <NavLink to="/administration" end title={collapsed ? "Quản lý tài khoản" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                        <UserCog aria-hidden="true" />
                        <span>Quản lý tài khoản</span>
                      </NavLink>
                    )}
                  </SidebarGroup>
                )}

                <SidebarGroup
                  label="TRA CỨU VÀ TÀI KHOẢN"
                  active={["/ai", "/forms", "/account", "/lecturer-profile-reviews"].includes(pathname) || pathname.startsWith("/lecturers")}
                  collapsed={collapsed}
                >
                  <NavLink to="/ai" title={collapsed ? "Tra cứu AI" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <Bot aria-hidden="true" />
                    <span>Tra cứu AI</span>
                  </NavLink>
                  <NavLink to="/forms" title={collapsed ? (context.actions.includes("forms:manage") ? "Quản lý kho biểu mẫu Khoa" : "Tài liệu Khoa công bố") : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <FolderOpen aria-hidden="true" />
                    <span>{context.actions.includes("forms:manage") ? "Quản lý kho biểu mẫu Khoa" : "Tài liệu Khoa công bố"}</span>
                  </NavLink>
                  <NavLink to="/lecturers" title={collapsed ? "Danh sách giảng viên" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <UsersRound aria-hidden="true" />
                    <span>Danh sách giảng viên</span>
                  </NavLink>
                  {context.actions.includes("lecturer:profile_review") && (
                    <NavLink to="/lecturer-profile-reviews" title={collapsed ? "Duyệt hồ sơ giảng viên" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                      <BadgeCheck aria-hidden="true" />
                      <span>Duyệt hồ sơ giảng viên</span>
                    </NavLink>
                  )}
                  <NavLink to="/account" title={collapsed ? "Thông tin của tôi" : undefined} className={({ isActive }) => "sidebar__item " + (isActive && !isLecturerProfileActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <UserRound aria-hidden="true" />
                    <span>Thông tin của tôi</span>
                  </NavLink>
                  <NavLink to="/account?section=lecturer-profile" title={collapsed ? "Hồ sơ chuyên môn của tôi" : undefined} className={() => "sidebar__item " + (isLecturerProfileActive ? "sidebar__item--active" : "")} aria-current={isLecturerProfileActive ? "page" : undefined} onClick={onClose}>
                    <Award aria-hidden="true" />
                    <span>Hồ sơ chuyên môn của tôi</span>
                  </NavLink>
                </SidebarGroup>
              </>
            )}

            {/* ── QUẢN TRỊ VIÊN ── */}
            {isAdmin && (
              <>
                <SidebarGroup label="VẬN HÀNH HỆ THỐNG" active={["/", "/rounds", "/administration", "/administration/assignments", "/positions"].includes(pathname)} collapsed={collapsed}>
                  <NavLink to="/" end title={collapsed ? "Tổng quan" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <LayoutDashboard aria-hidden="true" />
                    <span>Tổng quan</span>
                  </NavLink>
                  <NavLink to="/rounds" title={collapsed ? "Đợt KLTN" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <CalendarRange aria-hidden="true" />
                    <span>Đợt KLTN</span>
                  </NavLink>
                  <NavLink to="/administration" end title={collapsed ? "Quản lý tài khoản" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <UserCog aria-hidden="true" />
                    <span>Quản lý tài khoản</span>
                  </NavLink>
                  <NavLink to="/administration/assignments" title={collapsed ? "Phân công và chức vụ" : undefined} className={({ isActive }) => "sidebar__item " + (isActive || pathname === "/positions" ? "sidebar__item--active" : "")} onClick={onClose}>
                    <Briefcase aria-hidden="true" />
                    <span>Phân công và chức vụ</span>
                  </NavLink>
                </SidebarGroup>

                <SidebarGroup label="DANH MỤC & BIỂU MẪU" active={["/roster", "/topics", "/forms"].includes(pathname) || pathname.startsWith("/lecturers")} collapsed={collapsed}>
                  {context.actions.some((a) => a.startsWith("eligibility:")) && (
                    <NavLink to="/roster" title={collapsed ? "Danh sách sinh viên" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                      <ShieldCheck aria-hidden="true" />
                      <span>Danh sách sinh viên</span>
                    </NavLink>
                  )}
                  <NavLink to="/lecturers" title={collapsed ? "Danh sách giảng viên" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <UsersRound aria-hidden="true" />
                    <span>Danh sách giảng viên</span>
                  </NavLink>
                  <NavLink to="/topics" title={collapsed ? "Đề tài đã công bố" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <Lightbulb aria-hidden="true" />
                    <span>Đề tài đã công bố</span>
                  </NavLink>
                  <NavLink to="/forms" title={collapsed ? (context.actions.includes("forms:manage") ? "Quản lý kho biểu mẫu Khoa" : "Tài liệu Khoa công bố") : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <FolderOpen aria-hidden="true" />
                    <span>{context.actions.includes("forms:manage") ? "Quản lý kho biểu mẫu Khoa" : "Tài liệu Khoa công bố"}</span>
                  </NavLink>
                </SidebarGroup>

                <SidebarGroup label="GIÁM SÁT & TÀI KHOẢN" active={["/reports", "/activity", "/account"].includes(pathname)} collapsed={collapsed}>
                  <NavLink to="/reports" title={collapsed ? "Báo cáo và thống kê" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <ChartColumn aria-hidden="true" />
                    <span>Báo cáo và thống kê</span>
                  </NavLink>
                  <NavLink to="/activity" title={collapsed ? "Nhật ký hệ thống" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <History aria-hidden="true" />
                    <span>Nhật ký hệ thống</span>
                  </NavLink>
                  <NavLink to="/account" title={collapsed ? "Thông tin của tôi" : undefined} className={({ isActive }) => "sidebar__item " + (isActive ? "sidebar__item--active" : "")} onClick={onClose}>
                    <UserRound aria-hidden="true" />
                    <span>Thông tin của tôi</span>
                  </NavLink>
                </SidebarGroup>
              </>
            )}
          </nav>

          <div className="sidebar__art-dock" aria-hidden="true">
            <SidebarLotusArt className="sidebar__artwork" />
          </div>

          <div className="sidebar__footer">
            <Link to="/account" className="sidebar__user" aria-label="Quản lý tài khoản" title="Quản lý tài khoản" onClick={onClose}>
              <span className="sidebar__avatar" aria-hidden="true">
                {isLecturer ? <LecturerAvatar url={context.avatar_url} name={context.display_name} size="sm" /> : initialsOf(context.display_name)}
              </span>
              <span className="sidebar__user-info">
                <span className="sidebar__user-name">{context.display_name}</span>
                <span className="sidebar__user-role">{roleLabel(context)}</span>
              </span>
            </Link>
            <button
              type="button"
              className="sidebar__collapse"
              onClick={onToggleCollapsed}
              aria-label={collapseTitle}
              aria-pressed={collapsed}
              title={collapseTitle}
            >
              {collapsed ? <ChevronsRight size={16} aria-hidden="true" /> : <ChevronsLeft size={16} aria-hidden="true" />}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
