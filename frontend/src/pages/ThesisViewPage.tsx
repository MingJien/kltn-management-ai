import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Thesis } from "../api";
import { request } from "../api";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import { ArrowLeft, Users, User } from "lucide-react";

interface ThesisViewPageProps {
  userId: string;
}

export default function ThesisViewPage({ userId }: ThesisViewPageProps) {
  const { thesisId } = useParams();
  const [thesis, setThesis] = useState<Thesis | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (thesisId) {
      request<Thesis>(`/theses/${thesisId}`, userId)
        .then(setThesis)
        .catch((cause) => setError(String(cause)));
    }
  }, [thesisId, userId]);

  if (error) {
    return (
      <div className="alert alert-danger" role="alert">
        {error}
      </div>
    );
  }

  if (!thesis) {
    return (
      <div className="card">
        <div className="card-body stack">
          <div className="skeleton skeleton-line" style={{ width: "50%" }} />
          <div className="skeleton skeleton-line" style={{ width: "70%" }} />
          <div className="skeleton skeleton-line" style={{ width: "40%" }} />
        </div>
      </div>
    );
  }

  return (
    <>
      <Link
        to="/registrations"
        className="flex items-center gap-1 text-body-sm"
        style={{ marginBottom: "var(--space-4)" }}
      >
        <ArrowLeft size={14} />
        Quay lại Đăng ký
      </Link>

      <div className="card">
        <div className="card-body">
          <div className="flex justify-between items-start" style={{ marginBottom: "var(--space-4)" }}>
            <h1>{thesis.title}</h1>
            <ThesisStatusBadge state={thesis.state} />
          </div>

          <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "var(--space-3) var(--space-6)" }}>
            <dt className="text-caption" style={{ color: "var(--neutral-500)" }}>Mã khóa luận</dt>
            <dd><code>{thesis.id.slice(0, 8)}…</code></dd>

            <dt className="text-caption" style={{ color: "var(--neutral-500)" }}>
              <User size={14} style={{ display: "inline", verticalAlign: "-2px", marginRight: 4 }} />
              GVHD chính
            </dt>
            <dd><code>{thesis.advisor_lecturer_id.slice(0, 8)}…</code></dd>
          </dl>

          <div style={{ marginTop: "var(--space-6)" }}>
            <h3 className="flex items-center gap-2" style={{ marginBottom: "var(--space-3)" }}>
              <Users size={16} />
              Thành viên
            </h3>
            <div className="stack" style={{ gap: "var(--space-2)" }}>
              {thesis.member_student_ids.map((id) => (
                <div
                  key={id}
                  className="flex items-center gap-3"
                  style={{
                    padding: "var(--space-2) var(--space-3)",
                    background: "var(--neutral-50)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  <div className="sidebar__avatar" style={{ width: 28, height: 28, fontSize: 11 }}>
                    SV
                  </div>
                  <code className="text-body-sm">{id.slice(0, 8)}…</code>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
