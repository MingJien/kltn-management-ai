import { useCallback, useEffect, useState } from "react";
import { LayoutDashboard, BookOpen, ClipboardList } from "lucide-react";
import type { Context } from "../api";
import PageHeader from "../components/layout/PageHeader";

interface WorkspacePageProps {
  context: Context;
}

export default function WorkspacePage({ context }: WorkspacePageProps) {
  return (
    <>
      <PageHeader
        title={`Xin chào`}
        description="Tổng quan hoạt động và công việc cần xử lý"
      />

      {/* Role info */}
      <div className="flex gap-2 items-center" style={{ marginBottom: "var(--space-6)" }}>
        <span className="badge badge-primary">{context.base_role}</span>
        <span className="text-body-sm">
          {context.actions.length > 0
            ? `${context.actions.length} quyền hệ thống`
            : "Chỉ xem"}
        </span>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-3" style={{ marginBottom: "var(--space-8)" }}>
        <div className="card metric-card">
          <div className="metric-card__label">
            <LayoutDashboard size={14} style={{ display: "inline", verticalAlign: "-2px", marginRight: 4 }} />
            Vai trò
          </div>
          <div className="metric-card__value">{context.base_role}</div>
          <div className="metric-card__desc">
            {context.student_id ? "Sinh viên" : context.lecturer_id ? "Giảng viên" : "Quản trị"}
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-card__label">
            <BookOpen size={14} style={{ display: "inline", verticalAlign: "-2px", marginRight: 4 }} />
            Quyền hạn
          </div>
          <div className="metric-card__value">{context.actions.length}</div>
          <div className="metric-card__desc">
            {context.actions.length > 0 ? context.actions.slice(0, 3).join(", ") : "Chỉ xem"}
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-card__label">
            <ClipboardList size={14} style={{ display: "inline", verticalAlign: "-2px", marginRight: 4 }} />
            Mã định danh
          </div>
          <div className="metric-card__value" style={{ fontSize: 14, fontFamily: "var(--font-mono)" }}>
            {context.user_id.slice(0, 8)}…
          </div>
          <div className="metric-card__desc">User ID</div>
        </div>
      </div>

      {/* Work queue placeholder */}
      <div className="card">
        <div className="card-body">
          <h2 style={{ marginBottom: "var(--space-4)" }}>Công việc cần xử lý</h2>
          <div className="empty-state">
            <ClipboardList />
            <h3>Chưa có công việc</h3>
            <p>Hàng đợi công việc sẽ hiển thị khi có đăng ký, đề cương, hoặc phiên bảo vệ cần xử lý.</p>
          </div>
        </div>
      </div>
    </>
  );
}
