import type { Context } from "../../api";

export function roleLabel(context: Context) {
  return context.actions.includes("topic:department_decide") ? "Trưởng bộ môn"
    : context.base_role === "STUDENT" ? "Sinh viên"
    : context.base_role === "LECTURER" ? "Giảng viên" : "Quản trị";
}
