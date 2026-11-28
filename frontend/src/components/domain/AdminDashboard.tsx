import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CalendarRange, ClipboardList, FileText, GraduationCap, Lightbulb, RefreshCw, UsersRound } from "lucide-react";
import { request } from "../../api";
import { errorMessage } from "../../errors";
import { Status } from "./CoreForms";
import { SkeletonCard } from "../ui/Skeleton";

type Summary = {
  generated_at: string;
  accounts: Record<string, number>;
  account_status: Record<string, number>;
  rounds: Record<string, number>;
  topics: Record<string, number>;
  registrations: Record<string, number>;
  theses: Record<string, number>;
  documents: Record<string, number>;
  reports: Record<string, number>;
};

const total = (rows: Record<string, number>) => Object.values(rows).reduce((a, b) => a + b, 0);

export default function AdminDashboard({ userId }: { userId: string }) {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      try {
        const result = await request<Summary>("/admin/dashboard", userId, { signal });
        if (!signal?.aborted) {
          setData(result);
          setError("");
        }
      } catch (e) {
        if (!signal?.aborted) setError(errorMessage(e));
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [userId]
  );

  useEffect(() => {
    const c = new AbortController();
    void load(c.signal);
    return () => c.abort();
  }, [load]);

  return (
    <section className="stack" aria-label="Thống kê quản trị">
      <div className="workspace-section-head">
        <div>
          <span className="workspace-section-kicker">VẬN HÀNH HỆ THỐNG</span>
          <h2>Thống kê hiện tại</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="btn btn-soft btn-sm" to="/administration/assignments">
            <ClipboardList size={14} aria-hidden="true" />
            Phân công theo đợt
          </Link>
          <Link className="btn btn-secondary btn-sm" to="/forms">
            <FileText size={14} aria-hidden="true" />
            Biểu mẫu Khoa
          </Link>
          <button className="btn btn-secondary btn-sm" disabled={loading} onClick={() => void load()}>
            <RefreshCw size={14} aria-hidden="true" />
            Làm mới thống kê
          </button>
        </div>
      </div>

      {error && (
        <p className="alert alert-danger" role="alert">
          {error}
        </p>
      )}

      {loading && !data && (
        <div className="dashboard-metrics" role="status" aria-label="Đang tổng hợp dữ liệu">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {data && (
        <>
          <div className="dashboard-metrics">
            {[
              { label: "Sinh viên", count: data.accounts.STUDENT || 0, to: "/roster", icon: UsersRound },
              { label: "Giảng viên", count: data.accounts.LECTURER || 0, to: "/lecturers", icon: GraduationCap },
              { label: "Đề tài", count: total(data.topics), to: "/topics", icon: Lightbulb },
              { label: "Khóa luận", count: total(data.theses), to: "/rounds", icon: CalendarRange },
            ].map(({ label, count, to, icon: Icon }) => (
              <div className="card metric-card" key={label}>
                <span className="flex items-center justify-between gap-2">
                  {label}
                  <Icon size={16} className="metric-card__icon" aria-hidden="true" />
                </span>
                <strong>{count}</strong>
                {label !== "Khóa luận" ? (
                  <Link className="inline-flex items-center gap-1" to={to}>
                    Xem danh sách <ArrowRight size={13} aria-hidden="true" />
                  </Link>
                ) : (
                  <Link className="inline-flex items-center gap-1" to={to}>
                    Quản lý đợt <ArrowRight size={13} aria-hidden="true" />
                  </Link>
                )}
              </div>
            ))}
          </div>

          <div className="dashboard-breakdown">
            {(
              [
                ["Tài khoản", data.account_status],
                ["Đợt KLTN", data.rounds],
                ["Đề tài", data.topics],
                ["Hồ sơ đăng ký", data.registrations],
                ["Khóa luận", data.theses],
                ["Phiên bản tài liệu", data.documents],
                ["Lần nộp báo cáo tiến độ", data.reports],
              ] as [string, Record<string, number>][]
            ).map(([label, rows]) => (
              <article className="card" key={label}>
                <div className="card-body">
                  <h3>
                    {label} <span className="text-muted">({total(rows)})</span>
                  </h3>
                  <ul className="dashboard-status-list">
                    {Object.entries(rows).map(([status, count]) => (
                      <li key={status}>
                        <Status
                          value={status}
                          label={
                            label === "Tài khoản" && status === "ACTIVE"
                              ? "Đang hoạt động"
                              : status === "PENDING_ACTIVATION"
                                ? "Chờ kích hoạt"
                                : label === "Đề tài" && status === "ARCHIVED"
                                  ? "Ngừng sử dụng"
                                  : undefined
                          }
                        />
                        <strong>{count}</strong>
                      </li>
                    ))}
                    {!Object.keys(rows).length && <li className="text-muted">Chưa có dữ liệu</li>}
                  </ul>
                </div>
              </article>
            ))}
          </div>

          <p className="text-caption">
            Cập nhật: {new Date(data.generated_at).toLocaleString("vi-VN")}. Đếm toàn hệ thống, bao gồm dữ liệu DEMO đang
            lưu. Báo cáo tiến độ/tài liệu tính theo từng lần nộp.
          </p>
        </>
      )}
    </section>
  );
}
