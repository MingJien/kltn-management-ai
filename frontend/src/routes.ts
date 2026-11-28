import { plannedPages, type PlannedPageId } from "./plannedPages";

export interface BreadcrumbCrumb {
  label: string;
  to?: string;
}

export interface RouteMeta {
  path: string;
  label: string;
  parentPath?: string;
}

/** Single canonical manifest of route labels and hierarchy used by Header, Sidebar, and document.title. */
export const ROUTE_MANIFEST: Record<string, RouteMeta> = {
  "/": { path: "/", label: "Tổng quan" },
  "/reports": { path: "/reports", label: "Báo cáo và thống kê KLTN" },
  "/repository": { path: "/repository", label: "Kho khóa luận nội bộ" },
  "/topics": { path: "/topics", label: "Đề tài" },
  "/registrations": { path: "/registrations", label: "Đăng ký đề tài" },
  "/withdrawals": { path: "/withdrawals", label: "Xin thôi thực hiện KLTN" },
  "/changes": { path: "/changes", label: "Đổi đề tài & gia hạn" },
  "/theses": { path: "/theses", label: "Khóa luận & GVHD" },
  "/proposals": { path: "/proposals", label: "Đề cương khóa luận", parentPath: "/theses" },
  "/progress": { path: "/progress", label: "Tiến độ khóa luận", parentPath: "/theses" },
  "/documents": { path: "/documents", label: "Tài liệu khóa luận", parentPath: "/theses" },
  "/submissions": { path: "/submissions", label: "Hồ sơ nộp & xét duyệt" },
  "/forms": { path: "/forms", label: "Kho biểu mẫu & tài liệu Khoa" },
  "/account": { path: "/account", label: "Tài khoản của tôi" },
  "/administration": { path: "/administration", label: "Quản lý tài khoản" },
  "/administration/assignments": {
    path: "/administration/assignments",
    label: "Phân công theo đợt",
    parentPath: "/administration",
  },
  "/positions": {
    path: "/positions",
    label: "Chức vụ và phạm vi",
    parentPath: "/administration",
  },
  "/rounds": { path: "/rounds", label: "Quản lý đợt KLTN" },
  "/roster": { path: "/roster", label: "Danh sách đủ điều kiện" },
  "/lecturers": { path: "/lecturers", label: "Danh sách giảng viên" },
  "/lecturer-profile-reviews": { path: "/lecturer-profile-reviews", label: "Duyệt hồ sơ giảng viên" },
  "/ai": { path: "/ai", label: "Tra cứu AI" },
  "/notifications": { path: "/notifications", label: "Thông báo" },
  "/activity": { path: "/activity", label: "Lịch sử hoạt động" },
  "/review-records": { path: "/review-records", label: "Tiếp nhận hồ sơ phản biện" },
  "/defense": { path: "/defense", label: "Hội đồng và bảo vệ" },
  "/evaluation": { path: "/evaluation", label: "Phản biện & điều kiện bảo vệ" },
};

export function getBreadcrumbs(pathname: string, search: string): BreadcrumbCrumb[] {
  const params = new URLSearchParams(search);

  if (pathname === "/") {
    return [{ label: "Tổng quan" }];
  }

  if (pathname.startsWith("/planned/")) {
    const id = pathname.slice("/planned/".length) as PlannedPageId;
    const title = Object.hasOwn(plannedPages, id) ? plannedPages[id].title : "Tính năng sắp có";
    return [{ label: "KLTN", to: "/" }, { label: "Sắp có" }, { label: title }];
  }

  if (pathname.startsWith("/theses/")) {
    const section = params.get("section") || "overview";
    const sectionLabel =
      section === "progress"
        ? "Báo cáo tiến độ"
        : section === "proposal"
          ? "Đề cương"
          : ["submissions", "documents"].includes(section)
            ? "Hồ sơ nộp & xét duyệt"
            : "Tổng quan hồ sơ";
    return [
      { label: "KLTN", to: "/" },
      { label: ROUTE_MANIFEST["/theses"].label, to: "/theses" },
      { label: sectionLabel },
    ];
  }

  if (pathname.startsWith("/evaluation/")) {
    return [
      { label: "KLTN", to: "/" },
      { label: ROUTE_MANIFEST["/evaluation"].label, to: "/evaluation" },
      { label: "Chi tiết xét duyệt" },
    ];
  }

  if (pathname.startsWith("/lecturers/")) {
    return [
      { label: "KLTN", to: "/" },
      { label: ROUTE_MANIFEST["/lecturers"].label, to: "/lecturers" },
      { label: "Hồ sơ giảng viên" },
    ];
  }

  if (pathname === "/account" && params.get("section") === "lecturer-profile") {
    return [
      { label: "KLTN", to: "/" },
      { label: ROUTE_MANIFEST["/account"].label, to: "/account" },
      { label: "Hồ sơ chuyên môn" },
    ];
  }

  const meta = ROUTE_MANIFEST[pathname];
  if (meta) {
    const crumbs: BreadcrumbCrumb[] = [{ label: "KLTN", to: "/" }];
    if (meta.parentPath && ROUTE_MANIFEST[meta.parentPath]) {
      crumbs.push({ label: ROUTE_MANIFEST[meta.parentPath].label, to: meta.parentPath });
    }
    crumbs.push({ label: meta.label });
    return crumbs;
  }

  return [{ label: "KLTN", to: "/" }, { label: "Trang" }];
}

export function getPageTitle(pathname: string, search: string): string {
  const crumbs = getBreadcrumbs(pathname, search);
  return crumbs[crumbs.length - 1]?.label || "Hệ thống KLTN";
}
