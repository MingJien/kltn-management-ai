import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import type { Lecturer } from "../api";
import { request } from "../api";
import PageHeader from "../components/layout/PageHeader";
import { errorMessage } from "../errors";

export default function LecturerProfilePage({userId}: {userId: string}) {
  const {lecturerId} = useParams();
  const [lecturer, setLecturer] = useState<Lecturer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setLecturer(null); setError("");
    request<Lecturer[]>("/lecturers", userId, {signal:controller.signal}).then(rows => {
      if (!controller.signal.aborted) {
        const row = rows.find(item => item.id === lecturerId);
        setLecturer(row || null);
        if (!row) setError("Không tìm thấy giảng viên đang hoạt động trong bộ môn của bạn.");
      }
    }).catch(cause => {if (!controller.signal.aborted) setError(errorMessage(cause));})
      .finally(() => {if (!controller.signal.aborted) setLoading(false);});
    return () => controller.abort();
  }, [lecturerId, userId]);
  return <>
    <PageHeader title="Hồ sơ giảng viên" description="Thông tin hồ sơ giảng viên trong bộ môn của bạn." />
    {loading && <p role="status">Đang tải hồ sơ giảng viên…</p>}
    {error && <p className="alert alert-danger" role="alert">{error}</p>}
    {lecturer && <section className="card"><div className="card-body stack">
      <h2>{lecturer.display_name}</h2>
      <dl className="registration-summary">
        <dt>Mã giảng viên</dt><dd>{lecturer.lecturer_code}</dd>
        <dt>Bộ môn</dt><dd>{lecturer.department_name || "Chưa cập nhật"}</dd>
        <dt>Khoa</dt><dd>{lecturer.faculty_name || "Chưa cập nhật"}</dd>
      </dl>
    </div></section>}
    <Link className="btn btn-secondary" to="/topics"><ArrowLeft size={16} aria-hidden="true" />Quay lại danh sách đề tài</Link>
  </>;
}
