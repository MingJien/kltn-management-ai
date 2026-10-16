import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ArrowLeft, UserRound } from "lucide-react";
import type { Lecturer } from "../api";
import { request } from "../api";
import PageHeader from "../components/layout/PageHeader";

export default function LecturerProfilePage({userId}: {userId: string}) {
  const {lecturerId} = useParams();
  const location = useLocation();
  const [name, setName] = useState((location.state as {name?: string} | null)?.name || "");
  useEffect(() => {
    if (!lecturerId) return;
    let alive = true;
    request<Lecturer[]>("/lecturers", userId).then((rows) => {
      const lecturer = rows.find((row) => row.id === lecturerId);
      if (alive && lecturer) setName(lecturer.display_name);
    }).catch(() => undefined);
    return () => {alive = false;};
  }, [lecturerId, userId]);
  return <>
    <PageHeader title="Hồ sơ giảng viên" description="Thông tin giảng viên phụ trách đề tài." />
    <section className="card lecturer-profile-placeholder">
      <div className="card-body">
        <div className="lecturer-profile-placeholder__icon"><UserRound size={28} aria-hidden="true" /></div>
        <div>
          <p className="lecturer-profile-placeholder__eyebrow">Hồ sơ giảng viên</p>
          <h2>{name || "Giảng viên"}</h2>
          <p>Trang hồ sơ đang phát triển. Thông tin chuyên môn và liên hệ sẽ được hiển thị tại đây khi chức năng hoàn thành.</p>
          {lecturerId ? <Link className="btn btn-secondary" to="/topics"><ArrowLeft size={16} aria-hidden="true" />Quay lại danh sách đề tài</Link> : null}
        </div>
      </div>
    </section>
  </>;
}
