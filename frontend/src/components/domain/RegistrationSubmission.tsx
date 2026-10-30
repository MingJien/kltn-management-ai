import { useCallback, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import type { Registration } from "../../api";
import { request } from "../../api";
import { errorMessage } from "../../errors";
import { Status } from "./CoreForms";
import RegistrationForms from "./RegistrationForms";

export default function RegistrationSubmission({registrationId, userId, redirectToThesis = false}: {
  registrationId: string; userId: string; redirectToThesis?: boolean;
}) {
  const [row, setRow] = useState<Registration | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async (signal?: AbortSignal) => {
    const result = await request<Registration>("/topic-registrations/" + registrationId, userId, {signal});
    if (!signal?.aborted) {setRow(result); setError("");}
  }, [registrationId, userId]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal).catch(cause => {if (!controller.signal.aborted) setError(errorMessage(cause));});
    return () => controller.abort();
  }, [load]);
  if (error) return <div role="alert" className="alert alert-danger">{error} <button className="btn btn-secondary" onClick={() => void load().catch(cause => setError(errorMessage(cause)))}>Thử lại</button></div>;
  if (!row) return <p role="status">Đang tải đơn đăng ký…</p>;
  if (redirectToThesis && row.thesis_id) return <Navigate replace to={"/theses/" + row.thesis_id + "?section=submissions&kind=REGISTRATION"} />;
  return <div className="stack">
    <div className="submission-context">
      <div><span className="section-eyebrow">MẪU 1a / 1b · HỒ SƠ ĐĂNG KÝ</span><h2>{row.topic_title}</h2><p>{row.topic_code} · {row.members.filter(member => member.active).map(member => member.display_name).join(", ")}</p></div>
      <Status value={row.state} />
    </div>
    <p className="text-body-sm text-muted">Đơn đi cùng hồ sơ đăng ký. Quyết định tiếp nhận hoặc từ chối được thực hiện tại trang đăng ký.</p>
    <Link className="btn btn-secondary" to={"/registrations?focus=" + row.id}>Xem hồ sơ & quyết định đăng ký</Link>
    <RegistrationForms key={row.id} row={row} userId={userId} onChanged={() => load()} defaultOpen />
  </div>;
}
