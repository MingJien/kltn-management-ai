import { FormEvent, useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Plus, Users } from "lucide-react";
import type { Context, Lecturer, OpenRound, Registration, Requirement, Topic } from "../api";
import { request } from "../api";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import { RequirementEditor, RequirementList } from "../components/domain/TopicRequirements";
import RegistrationForm from "../components/domain/RegistrationForm";
import PageHeader from "../components/layout/PageHeader";
import Dialog from "../components/ui/Dialog";

function TopicEditor({topic, rounds, lecturers, student, busy, onSave, onPropose, context, userId}: {
  topic?: Topic; rounds: OpenRound[]; lecturers: Lecturer[]; student: boolean; busy: boolean;
  onSave: (body: object) => Promise<void>; onPropose?: (body: object) => Promise<void>;
  context: Context; userId: string;
}) {
  const [roundId, setRoundId] = useState(topic?.round_id || rounds[0]?.id || "");
  const [title, setTitle] = useState(topic?.title || "");
  const [description, setDescription] = useState(topic?.description || "");
  const [capacity, setCapacity] = useState(topic?.max_students || 3);
  const [requirements, setRequirements] = useState<Requirement[]>(topic?.requirements || []);
  const [lecturerId, setLecturerId] = useState(topic?.receiving_lecturer_id || "");
  function body() {return {...(!topic ? {round_id: roundId} : {}), title, description,
    ...(!student || !topic ? {max_students: capacity} : {}),
    ...(!student ? {requirements} : {receiving_lecturer_id: lecturerId})};}
  return <div className="stack">
    <form className="stack" onSubmit={(e: FormEvent) => {e.preventDefault(); void onSave(body());}}>
      {!topic ? <label>Năm học / đợt đăng ký<select className="input" required value={roundId} onChange={(e) => setRoundId(e.target.value)}>
        <option value="">Chọn đợt đang mở</option>{rounds.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
      </select></label> : <p className="text-caption">{topic.code} · {topic.round_label}</p>}
      <label>Tên đề tài<input className="input" required minLength={5} maxLength={500} value={title} onChange={(e) => setTitle(e.target.value)}/></label>
      <label>Mô tả, mục tiêu và phạm vi<textarea className="input" rows={4} maxLength={5000} value={description} onChange={(e) => setDescription(e.target.value)}/></label>
      {!student || !topic ? <label>Số sinh viên tối đa<select className="input" value={capacity} onChange={(e) => setCapacity(Number(e.target.value))}>
        {[1,2,3].map((n) => <option key={n} value={n}>{n === 1 ? "1 — chỉ cá nhân" : `${n} — cá nhân hoặc nhóm tối đa ${n}`}</option>)}
      </select></label> : null}
      {student ? <label>GV mong muốn tiếp nhận<select className="input" required value={lecturerId} onChange={(e) => setLecturerId(e.target.value)}>
        <option value="">Chọn GV trong bộ môn</option>{lecturers.map((l) => <option key={l.id} value={l.id}>{l.display_name} — {l.lecturer_code}</option>)}
      </select><span className="text-caption">TBM xác nhận hoặc chọn GV phù hợp khi duyệt. GV vẫn có quyền từ chối tiếp nhận.</span></label>
        : <RequirementEditor items={requirements} onChange={setRequirements}/>}
      {topic || !student ? <button className="btn btn-primary" type="submit" disabled={busy || (!topic && !roundId)}>{busy ? "Đang lưu…" : topic ? "Lưu chỉnh sửa" : "Tạo bản nháp"}</button> : null}
    </form>
    {student && !topic && onPropose && roundId ? <RegistrationForm key={`${roundId}-${capacity}`} context={context} userId={userId} roundId={roundId} capacity={capacity}
      busy={busy} disabled={title.trim().length < 5 || !lecturerId} onSubmit={(members) => onPropose({...body(), member_student_ids: members, confirm_creator: true})}/> : null}
  </div>;
}

export default function TopicsPage({userId, context}: {userId: string; context: Context}) {
  const navigate = useNavigate();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [rounds, setRounds] = useState<OpenRound[]>([]);
  const [lecturers, setLecturers] = useState<Lecturer[]>([]);
  const [selected, setSelected] = useState<Topic | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [view, setView] = useState(context.actions.includes("topic:department_decide") ? "pending" : "all");
  const [revisedTitle, setRevisedTitle] = useState("");
  const [reason, setReason] = useState("");
  const [receiver, setReceiver] = useState("");
  const student = context.base_role === "STUDENT";
  const head = context.actions.includes("topic:department_decide");
  const reload = useCallback(async () => setTopics(await request<Topic[]>("/topics?limit=100", userId)), [userId]);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.all([request<Topic[]>("/topics?limit=100", userId), request<OpenRound[]>("/rounds/open", userId), request<Lecturer[]>("/lecturers", userId)])
      .then(([t,r,l]) => {if (alive) {setTopics(t); setRounds(r); setLecturers(l);}})
      .catch((e) => {if (alive) setMessage(String(e));}).finally(() => {if (alive) setLoading(false);});
    return () => {alive = false;};
  }, [userId]);
  function choose(topic: Topic) {setSelected(topic); setRevisedTitle(topic.title); setReason(""); setReceiver(topic.receiving_lecturer_id || ""); setMessage("");}
  async function mutate(path: string, method: string, body?: object, version?: number) {
    setBusy(true); setMessage("");
    try {
      const updated = await request<Topic>(path, userId, {method, headers: version ? {"If-Match": String(version)} : {}, body: body ? JSON.stringify(body) : undefined});
      choose(updated); setCreateOpen(false); await reload(); setMessage("Đã lưu đề tài.");
    } catch (e) {setMessage(String(e));} finally {setBusy(false);}
  }
  async function register(body: object, proposal = false) {
    setBusy(true); setMessage("");
    try {
      await request<Registration>(proposal ? "/student-proposals" : "/topic-registrations", userId, {method: "POST", body: JSON.stringify(body)});
      navigate("/registrations");
    } catch (e) {setMessage(String(e));} finally {setBusy(false);}
  }
  const filtered = topics.filter((t) => (!filter || `${t.code} ${t.title} ${t.receiving_lecturer_name || ""}`.toLocaleLowerCase().includes(filter.toLocaleLowerCase()))
    && (view === "pending" ? t.state === "SUBMITTED" : view === "mine" ? t.proposer_user_id === userId : student ? t.proposer_type === "LECTURER" : true));
  const editable = selected?.proposer_user_id === userId && ["DRAFT", "RETURNED"].includes(selected.state);
  return <>
    <PageHeader title={head ? "Đề tài và duyệt đề tài" : "Đề tài"} description={student ? "Chọn đề tài GV đã duyệt hoặc tự đề xuất đề tài với nhóm của bạn." : "Tạo đề tài, nêu yêu cầu và theo dõi kết quả duyệt của bộ môn."}/>
    <div className="topic-toolbar"><input aria-label="Tìm đề tài" className="input" placeholder="Tìm theo mã, tên đề tài hoặc GV" value={filter} onChange={(e) => setFilter(e.target.value)}/>
      <button className="btn btn-secondary" disabled={loading || busy} onClick={() => void reload().catch((e) => setMessage(String(e)))}>Làm mới</button>
      <button className="btn btn-primary" disabled={!rounds.length || busy} onClick={() => {setCreateOpen(true); setMessage("");}}><Plus size={16}/>{student ? "Tự đề xuất đề tài" : "Tạo đề tài"}</button></div>
    <div className="tabs" aria-label="Nhóm đề tài">{[...(head ? [["pending", `Chờ duyệt (${topics.filter((t) => t.state === "SUBMITTED").length})`]] : []), ["all", student ? "Đề tài có sẵn" : "Tất cả đề tài"], ["mine", student ? "Đề xuất của tôi" : "Đề tài của tôi"]].map(([key,label]) =>
      <button key={key} className={`tabs__tab ${view === key ? "tabs__tab--active" : ""}`} onClick={() => setView(key)}>{label}</button>)}</div>
    {message ? <p className="alert alert-info" role="status">{message}</p> : null}
    {loading ? <p>Đang tải đề tài…</p> : !filtered.length ? <div className="card empty-state"><FileText/><h3>Chưa có đề tài trong danh sách này</h3><p>Đổi mục hoặc tạo đề tài mới khi có đợt đang mở.</p></div> :
      <div className="grid grid-auto">{filtered.map((t) => <article key={t.id} className="card"><div className="card-body stack">
        <div className="flex gap-2 items-center"><span className="topic-code">{t.code}</span><ThesisStatusBadge state={t.state}/></div>
        <h3>{t.title}</h3><p className="text-caption">{t.round_label} · {t.proposer_type === "STUDENT" ? "SV đề xuất" : "GV đề xuất"}</p>
        <p className="text-body-sm text-truncate-2">{t.description || "Chưa có mô tả."}</p><p className="text-body-sm">GV: {t.receiving_lecturer_name || "Chờ bộ môn chọn"}</p>
        <span className="badge badge-neutral"><Users size={14}/>{t.max_students === 1 ? "Cá nhân · 1 SV" : `Cá nhân / nhóm · tối đa ${t.max_students} SV`}</span>
        <RequirementList items={t.requirements}/><div className="flex gap-2"><button className="btn btn-secondary" onClick={() => choose(t)}>{head && t.state === "SUBMITTED" ? "Xem và duyệt" : "Xem chi tiết"}</button>
          {student && t.proposer_type === "LECTURER" ? <button className="btn btn-primary" disabled={!t.available} onClick={() => {choose(t); setRegisterOpen(true);}}>{t.available ? "Đăng ký" : "Không còn mở đăng ký"}</button> : null}</div>
      </div></article>)}</div>}
    {selected && !registerOpen ? <section className="card topic-detail"><div className="card-header"><h3>{selected.code} · {selected.title}</h3><button className="btn btn-ghost" onClick={() => setSelected(null)}>Đóng chi tiết</button></div><div className="card-body stack">
      <p>{selected.description}</p><RequirementList items={selected.requirements}/>{selected.decision_reason ? <p className="alert alert-warning">Lý do: {selected.decision_reason}</p> : null}
      {editable ? <><TopicEditor key={`${selected.id}-${selected.row_version}`} topic={selected} rounds={rounds} lecturers={lecturers} student={student} busy={busy} context={context} userId={userId} onSave={(body) => mutate(`/topics/${selected.id}`, "PATCH", body, selected.row_version)}/>
        {!student ? <button className="btn btn-primary" disabled={busy} onClick={() => void mutate(`/topics/${selected.id}/submit`, "POST", undefined, selected.row_version)}>Gửi bộ môn duyệt</button> : <p>Chỉnh sửa xong, mở Đăng ký để đại diện gửi đề xuất sau khi đủ xác nhận thành viên.</p>}</> : null}
      {head && selected.state === "SUBMITTED" && selected.proposer_user_id !== userId ? <form className="review-panel stack" onSubmit={(e) => {e.preventDefault(); void mutate(`/topics/${selected.id}/department-decision`, "POST", {decision:"APPROVE", revised_title: revisedTitle, reason: reason || null, ...(selected.proposer_type === "STUDENT" ? {receiving_lecturer_id: receiver} : {})}, selected.row_version);}}>
        <h3>Bộ môn xét duyệt</h3><label>Tên đề tài sau khi duyệt<input className="input" required minLength={5} maxLength={500} value={revisedTitle} onChange={(e) => setRevisedTitle(e.target.value)}/></label>
        <p className="text-caption">Sửa tên tại đây sẽ lưu cả tên cũ và tên mới trong lịch sử.</p>
        {selected.proposer_type === "STUDENT" ? <label>GV tiếp nhận (xác nhận hoặc chọn lại)<select className="input" required value={receiver} onChange={(e) => setReceiver(e.target.value)}><option value="">Chọn GV</option>{lecturers.map((l) => <option key={l.id} value={l.id}>{l.display_name}</option>)}</select></label> : null}
        <label>Góp ý / lý do<textarea className="input" rows={3} maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)}/></label>
        <div className="flex gap-2"><button className="btn btn-primary" disabled={busy}>Duyệt đề tài</button>{(["RETURN", "REJECT"] as const).map((decision) => <button key={decision} type="button" className={`btn ${decision === "RETURN" ? "btn-secondary" : "btn-destructive"}`} disabled={busy || !reason.trim()}
          onClick={() => void mutate(`/topics/${selected.id}/department-decision`, "POST", {decision,reason}, selected.row_version)}>{decision === "RETURN" ? "Trả lại để sửa" : "Từ chối đề tài"}</button>)}</div>
      </form> : null}
      <details><summary>Lịch sử tên đề tài ({selected.title_versions.length})</summary><ol className="requirement-list">{selected.title_versions.map((v) => <li key={v.version_no}>Phiên bản {v.version_no}: {v.title} — {new Date(v.created_at).toLocaleString("vi-VN")}</li>)}</ol></details>
    </div></section> : null}
    <Dialog open={createOpen} onClose={() => {if (!busy) setCreateOpen(false);}} title={student ? "Tự đề xuất và lập đăng ký" : "Tạo đề tài mới"} size="lg">
      {createOpen ? <TopicEditor rounds={rounds} lecturers={lecturers} student={student} busy={busy} context={context} userId={userId} onSave={(body) => mutate("/topics", "POST", body)} onPropose={(body) => register(body,true)}/> : null}{message ? <p className="alert alert-danger" role="alert">{message}</p> : null}
    </Dialog>
    <Dialog open={registerOpen && !!selected} onClose={() => {if (!busy) setRegisterOpen(false);}} title="Đăng ký đề tài" size="lg">
      {selected && registerOpen ? <div className="stack"><h3>{selected.title}</h3><p>{selected.code} · {selected.round_label}</p><RequirementList items={selected.requirements}/>
        <RegistrationForm key={selected.id} context={context} userId={userId} roundId={selected.round_id} capacity={selected.max_students} busy={busy} onSubmit={(members) => register({topic_id:selected.id,member_student_ids:members,confirm_creator:true})}/></div> : null}
      {message ? <p className="alert alert-danger" role="alert">{message}</p> : null}
    </Dialog>
  </>;
}
