import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Plus, Users } from "lucide-react";
import type { Context, Lecturer, OpenRound, Registration, Topic } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import { RequirementList } from "../components/domain/TopicRequirements";
import RegistrationForm from "../components/domain/RegistrationForm";
import TopicEditor from "../components/domain/TopicEditor";
import PageHeader from "../components/layout/PageHeader";
import Dialog from "../components/ui/Dialog";

const PAGE_SIZE = 24;
export default function TopicsPage({userId, context}: {userId: string; context: Context}) {
  const navigate = useNavigate();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [rounds, setRounds] = useState<OpenRound[]>([]);
  const [lecturers, setLecturers] = useState<Lecturer[]>([]);
  const [selected, setSelected] = useState<Topic | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [view, setView] = useState(context.actions.includes("topic:department_decide") ? "pending" : "all");
  const [revisedTitle, setRevisedTitle] = useState("");
  const [reason, setReason] = useState("");
  const [receiver, setReceiver] = useState("");
  const student = context.base_role === "STUDENT";
  const head = context.actions.includes("topic:department_decide");
  const path = "/topics?" + new URLSearchParams({limit:String(PAGE_SIZE), offset:String(page * PAGE_SIZE), search, view});
  const reload = useCallback(async () => setTopics(await request<Topic[]>(path, userId)), [path, userId]);
  useEffect(() => {
    const timer = window.setTimeout(() => {setSearch(filter.trim()); setPage(0);}, 250);
    return () => window.clearTimeout(timer);
  }, [filter]);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    request<Topic[]>(path, userId).then((rows) => {if (alive) setTopics(rows);})
      .catch((cause) => {if (alive) setMessage(errorMessage(cause));})
      .finally(() => {if (alive) setLoading(false);});
    return () => {alive = false;};
  }, [path, userId]);
  useEffect(() => {
    let alive = true;
    Promise.all([request<OpenRound[]>("/rounds/open", userId), request<Lecturer[]>("/lecturers", userId)])
      .then(([r,l]) => {if (alive) {setRounds(r); setLecturers(l);}})
      .catch((cause) => {if (alive) setMessage(errorMessage(cause));});
    return () => {alive = false;};
  }, [userId]);
  function choose(topic: Topic, detail = true) {
    setSelected(topic); setRevisedTitle(topic.title); setReason("");
    setReceiver(topic.receiving_lecturer_id || ""); setMessage(""); setDetailOpen(detail);
  }
  async function mutate(endpoint: string, method: string, payload?: object, version?: number) {
    if (busy) return;
    setBusy(true); setMessage("");
    try {
      const updated = await request<Topic>(endpoint, userId, {method,
        headers: version !== undefined ? {"If-Match":String(version)} : {},
        body: payload ? JSON.stringify(payload) : undefined});
      setCreateOpen(false); choose(updated); await reload(); setMessage("Đã lưu đề tài.");
    } catch (cause) {setMessage(errorMessage(cause));}
    finally {setBusy(false);}
  }
  async function register(payload: object, proposal = false) {
    if (busy) return;
    setBusy(true); setMessage("");
    try {
      await request<Registration>(proposal ? "/student-proposals" : "/topic-registrations", userId,
        {method:"POST", body:JSON.stringify(payload)});
      navigate("/registrations");
    } catch (cause) {setMessage(errorMessage(cause)); await reload().catch(() => undefined);}
    finally {setBusy(false);}
  }
  const editable = selected?.proposer_user_id === userId && ["DRAFT","RETURNED"].includes(selected.state);
  return <>
    <PageHeader title={head ? "Đề tài và duyệt đề tài" : "Đề tài"}
      description={student ? "Tự đăng ký vào đề tài còn chỗ hoặc đề xuất đề tài để bộ môn xét duyệt." : "Tạo đề tài, nêu yêu cầu và theo dõi kết quả duyệt của bộ môn."} />
    <div className="topic-toolbar">
      <input aria-label="Tìm đề tài" className="input" maxLength={200} placeholder="Tìm theo mã, tên đề tài hoặc GV"
        value={filter} onChange={(event) => setFilter(event.target.value)} />
      <button className="btn btn-secondary" disabled={loading || busy} onClick={() => void reload().catch((cause) => setMessage(errorMessage(cause)))}>Làm mới</button>
      {(student ? context.actions.includes("registration:create") : context.actions.includes("topic:create")) ?
        <button className="btn btn-primary" disabled={!rounds.length || busy}
          onClick={() => {setDetailOpen(false); setCreateOpen(true); setMessage("");}}>
          <Plus size={16} aria-hidden="true" />{student ? "Tự đề xuất đề tài" : "Tạo đề tài"}
        </button> : null}
    </div>
    {!rounds.length ? <p className="text-caption">Không có đợt đang mở để tạo hoặc đăng ký đề tài mới.</p> : null}
    <div className="tabs" aria-label="Lọc đề tài">
      {[...(head ? [["pending","Chờ duyệt"]] : []), ["all",student ? "Đề tài có sẵn" : "Tất cả đề tài"],
        ["mine",student ? "Đề xuất của tôi" : "Đề tài của tôi"]].map(([key,label]) =>
        <button key={key} aria-pressed={view === key} className={"tabs__tab " + (view === key ? "tabs__tab--active" : "")}
          onClick={() => {setView(key); setPage(0);}}>{label}</button>)}
    </div>
    {message && !detailOpen && !createOpen && !registerOpen ? <p className="alert alert-info" role="status">{message}</p> : null}
    {loading ? <p role="status">Đang tải đề tài…</p> : !topics.length ?
      <div className="card empty-state"><FileText aria-hidden="true" /><h2>Chưa có đề tài trong danh sách này</h2><p>Thử đổi mục hoặc từ khóa tìm kiếm.</p></div> :
      <div className="grid grid-auto">{topics.map((topic) => <article key={topic.id} className="card">
        <div className="card-body stack">
          <div className="flex gap-2 items-center"><span className="topic-code">{topic.code}</span><ThesisStatusBadge state={topic.state} /></div>
          <h2 className="topic-card-title">{topic.title}</h2>
          <p className="text-caption">{topic.round_label} · {topic.proposer_type === "STUDENT" ? "SV đề xuất" : "GV đề xuất"}</p>
          <p className="text-body-sm text-truncate-2">{topic.description || "Chưa có mô tả."}</p>
          <p className="text-body-sm">GV: {topic.receiving_lecturer_name || "Chờ bộ môn chọn"}</p>
          <span className="badge badge-neutral"><Users size={14} aria-hidden="true" />
            {topic.registered_member_count}/{topic.max_students} SV · còn {topic.remaining_slots} chỗ
          </span>
          <RequirementList items={topic.requirements} />
          <div className="flex gap-2">
            <button className="btn btn-secondary" onClick={() => choose(topic)}>{head && topic.state === "SUBMITTED" ? "Xem và duyệt" : "Xem chi tiết"}</button>
            {student && topic.state === "APPROVED" ? <button className="btn btn-primary" disabled={!topic.available}
              onClick={() => {choose(topic,false); setRegisterOpen(true);}}>
              {topic.available ? topic.registered_member_count ? "Tham gia" : "Đăng ký" : "Đã đóng đăng ký"}
            </button> : null}
          </div>
        </div>
      </article>)}</div>}
    <nav className="pagination" aria-label="Phân trang đề tài">
      <button className="btn btn-secondary" disabled={!page || loading} onClick={() => setPage(page - 1)}>Trang trước</button>
      <span>Trang {page + 1}</span>
      <button className="btn btn-secondary" disabled={topics.length < PAGE_SIZE || loading} onClick={() => setPage(page + 1)}>Trang sau</button>
    </nav>

    <Dialog open={detailOpen && !!selected} onClose={() => setDetailOpen(false)} busy={busy}
      title={selected ? selected.code + " · " + selected.title : "Chi tiết đề tài"} size="lg">
      {selected ? <div className="stack">
        <p>{selected.round_label} · <ThesisStatusBadge state={selected.state} /></p>
        <p>{selected.description || "Chưa có mô tả."}</p>
        <p>GV: {selected.receiving_lecturer_name || "Chờ bộ môn chọn"} · Tối đa {selected.max_students} SV</p>
        <RequirementList items={selected.requirements} />
        {selected.decision_reason ? <p className="alert alert-warning">Góp ý của bộ môn: {selected.decision_reason}</p> : null}
        {editable ? <>
          <TopicEditor key={selected.id + "-" + selected.row_version} topic={selected} rounds={rounds}
            lecturers={lecturers} context={context} busy={busy}
            onSave={(payload) => mutate("/topics/" + selected.id,"PATCH",payload,selected.row_version)} />
          {!student ? <button className="btn btn-primary" disabled={busy}
            onClick={() => void mutate("/topics/" + selected.id + "/submit","POST",undefined,selected.row_version)}>Gửi bộ môn duyệt</button>
            : <p>Chỉnh sửa xong, mở Đăng ký để gửi đề xuất cho bộ môn.</p>}
        </> : null}
        {head && selected.state === "SUBMITTED" && selected.proposer_user_id !== userId ?
          <form className="review-panel stack" onSubmit={(event) => {event.preventDefault(); void mutate("/topics/" + selected.id + "/department-decision","POST",
            {decision:"APPROVE",revised_title:revisedTitle,reason:reason || null,
              ...(selected.proposer_type === "STUDENT" ? {receiving_lecturer_id:receiver} : {})},selected.row_version);}}>
            <h3>Bộ môn xét duyệt</h3>
            <label>Tên đề tài sau khi duyệt<input className="input" required minLength={5} maxLength={500}
              value={revisedTitle} onChange={(event) => setRevisedTitle(event.target.value)} /></label>
            <p className="text-caption">Tên cũ và tên mới được giữ trong lịch sử.</p>
            {selected.proposer_type === "STUDENT" ? <label>GV tiếp nhận (xác nhận hoặc chọn lại)
              <select className="input" required value={receiver} onChange={(event) => setReceiver(event.target.value)}>
                <option value="">Chọn GV</option>{lecturers.map((lecturer) => <option key={lecturer.id} value={lecturer.id}>{lecturer.display_name}</option>)}
              </select></label> : null}
            <label>Góp ý / lý do<textarea className="input" rows={3} maxLength={2000} value={reason} onChange={(event) => setReason(event.target.value)} /></label>
            <div className="flex gap-2">
              <button className="btn btn-primary" disabled={busy}>Duyệt đề tài</button>
              {(["RETURN","REJECT"] as const).map((decision) => <button key={decision} type="button"
                className={"btn " + (decision === "RETURN" ? "btn-secondary" : "btn-destructive")} disabled={busy || !reason.trim()}
                onClick={() => void mutate("/topics/" + selected.id + "/department-decision","POST",{decision,reason},selected.row_version)}>
                {decision === "RETURN" ? "Trả lại để sửa" : "Từ chối đề tài"}
              </button>)}
            </div>
          </form> : null}
        <details><summary>Lịch sử tên đề tài ({selected.title_versions.length})</summary>
          <ol className="requirement-list">{selected.title_versions.map((version) => <li key={version.version_no}>
            Phiên bản {version.version_no}: {version.title} — {new Date(version.created_at).toLocaleString("vi-VN")}
          </li>)}</ol>
        </details>
      </div> : null}
      {message ? <p className="alert alert-info" role="status">{message}</p> : null}
    </Dialog>
    <Dialog open={createOpen} onClose={() => setCreateOpen(false)} busy={busy}
      title={student ? "Tự đề xuất và lập đăng ký" : "Tạo đề tài mới"} size="lg">
      {createOpen ? <TopicEditor rounds={rounds} lecturers={lecturers} context={context} busy={busy}
        onSave={(payload) => mutate("/topics","POST",payload)} onPropose={(payload) => register(payload,true)} /> : null}
      {message ? <p className="alert alert-danger" role="alert">{message}</p> : null}
    </Dialog>
    <Dialog open={registerOpen && !!selected} onClose={() => setRegisterOpen(false)} busy={busy} title="Đăng ký đề tài" size="lg">
      {selected && registerOpen ? <div className="stack">
        <h3>{selected.title}</h3><p>{selected.code} · {selected.round_label}</p>
        <p>Đã có {selected.registered_member_count}/{selected.max_students} SV · còn {selected.remaining_slots} chỗ.</p>
        {selected.registration_state === "LECTURER_ACCEPTED" ? <p className="alert alert-info">Nhóm đã được nhận. Khi bạn tham gia, GV sẽ xét lại nhóm có thành viên mới.</p> : null}
        <RequirementList items={selected.requirements} />
        <RegistrationForm context={context} userId={userId} roundId={selected.round_id} busy={busy}
          joining={selected.registered_member_count > 0} onSubmit={() => register({topic_id:selected.id,confirm_creator:true})} />
      </div> : null}
      {message ? <p className="alert alert-danger" role="alert">{message}</p> : null}
    </Dialog>
  </>;
}
