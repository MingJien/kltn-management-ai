import type { Context } from "../../api";

export function roleLabel(context: Context): string {
  if (context.actions.includes("topic:department_decide")) return "Trưởng bộ môn";
  if (
    context.lecturer_duties?.some((d) => d.code === "FACULTY_DEAN") ||
    context.actions.includes("proposal:dean_confirm")
  ) {
    return "Lãnh đạo Khoa";
  }
  if (context.base_role === "STUDENT") return "Sinh viên";
  if (context.base_role === "LECTURER") return "Giảng viên";
  return "Quản trị";
}
