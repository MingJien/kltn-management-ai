import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, ClipboardList } from "lucide-react";
import type { Context, OpenRound, Registration, Topic } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import { roleLabel } from "../components/layout/Sidebar";

export default function WorkspacePage({context}: {context: Context}) {
  const [rounds, setRounds] = useState<OpenRound[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const head = context.actions.includes("topic:department_decide");
  const workflowAccess = context.base_role === "STUDENT" || context.base_role === "LECTURER";
  useEffect(() => {
    if (!workflowAccess) {setLoading(false); return;}
    let alive = true;
    Promise.all([request<OpenRound[]>("/rounds/open", context.user_id),
      request<Topic[]>("/topics?limit=5&view=" + (head ? "pending" : context.base_role === "LECTURER" ? "mine" : "all"), context.user_id),
      request<Registration[]>("/topic-registrations?limit=5", context.user_id)])
      .then(([r,t,g]) => {if (alive) {setRounds(r); setTopics(t); setRegistrations(g);}})
      .catch((cause) => {if (alive) setError(errorMessage(cause));})
      .finally(() => {if (alive) setLoading(false);});
    return () => {alive = false;};
  }, [context.user_id, context.base_role, head, workflowAccess]);
  if (!workflowAccess) return <>
    <PageHeader title="Tổng quan" description={"Xin chào " + context.display_name + " · " + roleLabel(context)} />
    <section className="card"><div className="card-body stack">
      <h2>Chưa có công việc được giao trên giao diện này</h2>
      <p>Chức năng hiện tại dành cho sinh viên, giảng viên và Trưởng bộ môn trong quy trình đề tài, đăng ký.</p>
    </div></section>
  </>;
  return <>
    <PageHeader title="Tổng quan" description={"Xin chào " + context.display_name + " · " + roleLabel(context)} />
    {error ? <p role="alert" className="alert alert-danger">{error}</p> : null}
    {loading ? <p role="status">Đang tải công việc…</p> : <div className="stack">
      <section className="card"><div className="card-body stack">
        <h2>Đợt đăng ký đang mở</h2>
        {rounds.length ? rounds.map((round) => <p key={round.id}><strong>{round.label}</strong><br />
          Hạn đăng ký: {new Date(round.closes_at).toLocaleString("vi-VN")}</p>) : <p>Hiện chưa có đợt đăng ký đang mở.</p>}
      </div></section>
      <div className="grid grid-auto">
        <section className="card"><div className="card-body stack">
          <h2><BookOpen size={18} aria-hidden="true" /> {head ? "Đề tài chờ duyệt" : context.base_role === "LECTURER" ? "Đề tài của tôi gần đây" : "Đề tài đã duyệt gần đây"}</h2>
          {topics.length ? <ul className="requirement-list">{topics.map((topic) => <li key={topic.id}>{topic.code} · {topic.title} <ThesisStatusBadge state={topic.state} /></li>)}</ul> : <p>Chưa có đề tài trong mục này.</p>}
          <Link className="btn btn-secondary" to="/topics">Mở danh sách đề tài</Link>
        </div></section>
        <section className="card"><div className="card-body stack">
          <h2><ClipboardList size={18} aria-hidden="true" /> Đăng ký gần đây</h2>
          {registrations.length ? <ul className="requirement-list">{registrations.map((row) => <li key={row.id}>{row.topic_code} · {row.topic_title} <ThesisStatusBadge state={row.state} /></li>)}</ul> : <p>Chưa có đăng ký trong phạm vi của bạn.</p>}
          <Link className="btn btn-secondary" to="/registrations">Mở danh sách đăng ký</Link>
        </div></section>
      </div>
    </div>}
  </>;
}
