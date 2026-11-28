import WorkflowSteps from "../components/domain/WorkflowSteps";
import LecturerProfileLink from "../components/domain/LecturerProfileDialog";
import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { CalendarDays, Check, ChevronLeft, ChevronRight, ClipboardCheck, Download, Eye, FileText, LayoutGrid, List, Plus, RefreshCw, RotateCcw, Send, UserRound, Users, XCircle } from "lucide-react";
import type { Context, Lecturer, OpenRound, Registration, SchoolFormRound, Topic } from "../api";
import { exportRoundMau04, request, uploadEvidence } from "../api";
import { ApiError, errorMessage } from "../errors";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import TopicDescriptionPreview from "../components/domain/TopicDescriptionPreview";
import { RequirementList } from "../components/domain/TopicRequirements";
import RegistrationForm from "../components/domain/RegistrationForm";
import TopicEditor from "../components/domain/TopicEditor";
import PageHeader from "../components/layout/PageHeader";
import { SkeletonCard } from "../components/ui/Skeleton";
import Dialog from "../components/ui/Dialog";
import FilterBar, { type FilterChip } from "../components/ui/FilterBar";
import EmptyState from "../components/ui/EmptyState";
import Tabs from "../components/ui/Tabs";
import TopicLifecycle from "../components/domain/TopicLifecycle";

const PAGE_SIZE = 9;
function roundDisplay(label: string) {
  const match = /^Năm học\s+(.+?)(?:\s+\((đợt\s+\d+)\))?$/i.exec(label);
  return {year: match?.[1] || label, period: match?.[2] || ""};
}

function renderDescriptionContent(description: string | null) {
  const raw = (description || "").trim();
  if (!raw) return <p>Chưa có mô tả.</p>;
  const lines = raw.split(/\r?\n/);
  const nodes: React.ReactNode[] = [];
  let bullets: string[] = [];
  let paragraph: string[] = [];

  const flushParagraph = (key: string) => {
    if (!paragraph.length) return;
    nodes.push(<p key={key}>{paragraph.join("\n")}</p>);
    paragraph = [];
  };
  const flushBullets = (key: string) => {
    if (!bullets.length) return;
    nodes.push(
      <ul key={key} className="topic-drawer-bullets">
        {bullets.map((item, idx) => <li key={idx}>{item}</li>)}
      </ul>
    );
    bullets = [];
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    const bulletMatch = /^[-•*]\s+(.+)$/.exec(trimmed);
    if (bulletMatch) {
      flushParagraph(`p-${index}`);
      bullets.push(bulletMatch[1]);
    } else if (!trimmed) {
      flushParagraph(`p-${index}`);
      flushBullets(`b-${index}`);
    } else {
      flushBullets(`b-${index}`);
      paragraph.push(line);
    }
  });
  flushParagraph("p-end");
  flushBullets("b-end");

  return <div className="topic-drawer-prose">{nodes}</div>;
}



export default function TopicsPage({userId, context}: {userId: string; context: Context}) {
  const navigate = useNavigate();
  const location = useLocation();
  const focusedTopicId = new URLSearchParams(location.search).get("focus");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [rounds, setRounds] = useState<OpenRound[]>([]);
  const [exportRounds,setExportRounds]=useState<SchoolFormRound[]>([]);
  const [exportRoundId,setExportRoundId]=useState(() => new URLSearchParams(window.location.search).get("round_id") || "");
  const [exportPreview,setExportPreview]=useState<{round_id:string;round_code:string;students:number;theses:number;missing_advisors:number}|null>(null);
  const [previewLoading,setPreviewLoading]=useState(false);
  const [previewError,setPreviewError]=useState("");
  const [roundsLoaded, setRoundsLoaded] = useState(false);
  const [lecturers, setLecturers] = useState<Lecturer[]>([]);
  const [lecturersLoading, setLecturersLoading] = useState(true);
  const [lecturersError, setLecturersError] = useState("");
  const [selected, setSelected] = useState<Topic | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [drawerError, setDrawerError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [view, setView] = useState(context.actions.includes("topic:department_decide") ? "pending" : "all");
  const [sort, setSort] = useState("newest");
  const [layoutMode, setLayoutMode] = useState<"grid" | "list">("grid");
  const [revisedTitle, setRevisedTitle] = useState("");
  const [reason, setReason] = useState("");
  const [receiver, setReceiver] = useState("");
  const student = context.base_role === "STUDENT";
  const admin = context.base_role === "ADMIN";
  const head = context.actions.includes("topic:department_decide");
  useEffect(()=>{
    if (!admin && !context.actions.includes("progress:coordinate")) {setExportRounds([]);return;}
    const controller=new AbortController();
    void request<SchoolFormRound[]>("/school-forms/access",userId,{signal:controller.signal}).then(rows=>{
      if(controller.signal.aborted)return;
      const allowed=rows.filter(row=>row.can_export_list);setExportRounds(allowed);
      setExportRoundId(previous=>allowed.some(row=>row.id===previous)?previous:allowed[0]?.id || "");
    }).catch(cause=>{if(!controller.signal.aborted)setMessage(errorMessage(cause));});
    return()=>controller.abort();
  },[userId,admin,context.actions.includes("progress:coordinate")]);
  useEffect(()=>{
    if(!exportRoundId || !exportRounds.some(row=>row.id===exportRoundId)){setExportPreview(null);return;}
    const controller=new AbortController();
    setExportPreview(null);setPreviewError("");setPreviewLoading(true);
    void request<{round_id:string;round_code:string;students:number;theses:number;missing_advisors:number}>("/school-forms/rounds/"+exportRoundId+"/mau-04/preview",userId,{signal:controller.signal})
      .then(result=>{if(!controller.signal.aborted)setExportPreview(result);})
      .catch(cause=>{if(!controller.signal.aborted)setPreviewError(errorMessage(cause));})
      .finally(()=>{if(!controller.signal.aborted)setPreviewLoading(false);});
    return()=>controller.abort();
  },[exportRoundId,exportRounds,userId]);
  const path = "/topics?" + new URLSearchParams({limit:String(PAGE_SIZE), offset:String(page * PAGE_SIZE), search, view, sort});
  const reload = useCallback(async () => setTopics(await request<Topic[]>(path, userId)), [path, userId]);
  const loadLecturers = useCallback(async (signal?: AbortSignal) => {
    if (admin) {setLecturers([]);setLecturersLoading(false);return;}
    setLecturersLoading(true); setLecturersError("");
    try {
      const rows = await request<Lecturer[]>("/lecturers"+(selected?"?topic_id="+selected.id:""), userId, {signal});
      if (!signal?.aborted) setLecturers(rows);
    } catch (cause) {
      if (!signal?.aborted) setLecturersError(errorMessage(cause));
    } finally {if (!signal?.aborted) setLecturersLoading(false);}
  }, [userId,admin,selected?.id]);
  useEffect(() => {
    const controller = new AbortController();
    void loadLecturers(controller.signal);
    return () => controller.abort();
  }, [loadLecturers]);
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
    request<OpenRound[]>("/rounds/open", userId)
      .then((r) => {if (alive) {setRounds(r); setRoundsLoaded(true);}})
      .catch((cause) => {if (alive) setMessage(errorMessage(cause));});
    return () => {alive = false;};
  }, [userId]);
  useEffect(() => {
    if (!focusedTopicId) return;
    let alive = true;
    request<Topic>(`/topics/${focusedTopicId}`, userId)
      .then((topic) => {if (alive) {
        setSelected(topic); setRevisedTitle(topic.title); setReason("");
        setReceiver(topic.receiving_lecturer_id || ""); setDetailOpen(true);
      }})
      .catch((cause) => {if (alive) setMessage(errorMessage(cause));});
    return () => {alive = false;};
  }, [focusedTopicId, userId]);
  function choose(topic: Topic, detail = true) {
    setSelected(topic); setRevisedTitle(topic.title); setReason("");
    setReceiver(topic.receiving_lecturer_id || ""); setMessage(""); setDrawerError(""); setDetailOpen(detail);
  }
  function closeDetail() {
    setDetailOpen(false);
    setDrawerError("");
    if (focusedTopicId) navigate("/topics", {replace:true});
  }
  async function mutate(endpoint: string, method: string, payload?: object, version?: number) {
    if (busy) return;
    setBusy(true); setMessage(""); setDrawerError("");
    try {
      const updated = await request<Topic>(endpoint, userId, {method,
        headers: version !== undefined ? {"If-Match":String(version)} : {},
        body: payload ? JSON.stringify(payload) : undefined});
      setCreateOpen(false); choose(updated); await reload(); setMessage("Đã lưu đề tài.");
    } catch (cause) {
      const msg = errorMessage(cause);
      if (detailOpen) {
        setDrawerError(msg);
        if (cause instanceof ApiError && cause.status === 409 && selected) {
          const fresh = await request<Topic>(`/topics/${selected.id}`, userId).catch(() => null);
          if (fresh) {
            setSelected(fresh);
            setRevisedTitle(fresh.title);
            setReceiver(fresh.receiving_lecturer_id || "");
          }
          await reload().catch(() => undefined);
        }
      } else {
        setMessage(msg);
      }
    }
    finally {setBusy(false);}
  }
  async function register(payload: object, proposal = false, evidence?: File) {
    if (busy) return;
    setBusy(true); setMessage("");
    try {
      const registration = await request<Registration>(proposal ? "/student-proposals" : "/topic-registrations", userId,
        {method:"POST", body:JSON.stringify(payload)});
      let notice = "Đã lập đăng ký. Bạn có thể kiểm tra và gửi hồ sơ cho GV.";
      if (evidence) {
        try {
          await uploadEvidence(registration.id, userId, evidence);
          notice = "Đã lập đăng ký và lưu minh chứng của bạn.";
        } catch (cause) {
          notice = `Đã lập đăng ký nhưng chưa tải được minh chứng (${errorMessage(cause)}). Hãy vào hồ sơ đăng ký để thử lại.`;
        }
      }
      navigate("/registrations", {state:{notice}});
    } catch (cause) {setMessage(errorMessage(cause)); await reload().catch(() => undefined);}
    finally {setBusy(false);}
  }
  const editable = selected?.proposer_user_id === userId && ["DRAFT","RETURNED"].includes(selected.state);
  const receiverReady = !lecturersLoading && !lecturersError && lecturers.some(item => item.id === receiver && item.available !== false);
  const sortLabels: Record<string, string> = {
    newest: "Mới nhất",
    oldest: "Cũ nhất",
    title_asc: "Tên A → Z",
    title_desc: "Tên Z → A",
  };
  const topicTabs = [
    ...(head ? [["pending", "Chờ duyệt"], ["archived", "Đã ngừng sử dụng"]] : []),
    ["all", student ? "Đề tài có sẵn" : "Tất cả đề tài"],
    ...(!student && !admin ? [["suggested", "SV đề xuất cho tôi"]] : []),
    ...(!admin ? [["mine", student ? "Đề xuất của tôi" : "Đề tài của tôi"]] : []),
  ].map(([id, label]) => ({ id, label }));
  const topicChips: FilterChip[] = [
    ...(filter.trim() ? [{ key: "q", label: `Từ khóa: "${filter.trim()}"`, onRemove: () => setFilter("") }] : []),
    ...(sort !== "newest" ? [{ key: "sort", label: `Sắp xếp: ${sortLabels[sort] || sort}`, onRemove: () => { setSort("newest"); setPage(0); } }] : []),
  ];

  return <>
    <PageHeader title={head ? "Đề tài và duyệt đề tài" : "Đề tài"}
      description={admin ? "Danh sách đề tài đã công bố để tra cứu theo quyền được giao." : student ? "Đăng ký vào đề tài còn chỗ hoặc đề xuất đề tài để bộ môn xét duyệt." : "Quản lý, theo dõi và duyệt đề tài trong phạm vi bộ môn."} />
    {exportRounds.length>0 && <section className="card mb-4" aria-label="Xuất danh sách KLTN"><div className="card-body stack">
      <h2>Danh sách sinh viên và GVHD thực hiện KLTN</h2>
     
      <div className="flex flex-wrap gap-2 items-center"><label>Đợt xuất danh sách<select className="input" value={exportRoundId} disabled={busy} onChange={event=>setExportRoundId(event.target.value)}>{exportRounds.map(row=><option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
      <button type="button" className="btn btn-soft" disabled={busy || previewLoading || exportPreview?.round_id !== exportRoundId || !exportPreview?.students} onClick={async()=>{setBusy(true);setMessage("");try{await exportRoundMau04(exportRoundId);setMessage("Đã xuất Mẫu 4 theo dữ liệu hiện tại; kiểm tra và ký ngoài hệ thống trước khi công bố.");}catch(cause){setMessage(errorMessage(cause));}finally{setBusy(false);}}}><Download size={15} aria-hidden="true" />Xuất danh sách đã điền theo Mẫu 4</button></div>
      {previewLoading && <p role="status">Đang kiểm tra dữ liệu của đợt…</p>}
      {previewError && <p role="alert" className="alert alert-danger">{previewError}</p>}
      {exportPreview?.round_id === exportRoundId && (exportPreview.students > 0
        ? <p role="status"><strong>{exportPreview.students} sinh viên · {exportPreview.theses} khóa luận</strong> sẽ được đưa vào danh sách.{exportPreview.missing_advisors > 0 && (" Có "+exportPreview.missing_advisors+" sinh viên chưa có GVHD chính thức; cột ghi chú sẽ đánh dấu.")}</p>
        : <p role="status" className="alert alert-info">Đợt này chưa có sinh viên đang thực hiện khóa luận. Hãy chọn đợt có hồ sơ đã được GV tiếp nhận.</p>)}
    </div></section>}
    <FilterBar
      search={{
        value: filter,
        onChange: setFilter,
        placeholder: "Tìm theo mã, tên đề tài hoặc GV...",
        ariaLabel: "Tìm đề tài",
      }}
      chips={topicChips}
      onClearAll={() => { setFilter(""); setSort("newest"); setPage(0); }}
      actions={
        <div className="flex flex-wrap gap-2">
          <button className="btn btn-secondary" disabled={loading || busy} onClick={() => void reload().catch((cause) => setMessage(errorMessage(cause)))}>
            <RefreshCw size={15} aria-hidden="true" />Làm mới
          </button>
          {(student ? context.actions.includes("registration:create") : context.actions.includes("topic:create")) ?
            <button className="btn btn-primary" disabled={!rounds.length || busy}
              onClick={() => {setDetailOpen(false); setCreateOpen(true); setMessage("");}}>
              <Plus size={16} aria-hidden="true" />{student ? "Tự đề xuất đề tài" : "Tạo đề tài"}
            </button> : null}
        </div>
      }
    >
      <div className="topic-sort-control">
        <span>Sắp xếp:</span>
        <select
          aria-label="Thứ tự sắp xếp"
          className="input topic-sort-select"
          value={sort}
          onChange={(e) => { setSort(e.target.value); setPage(0); }}
        >
          <option value="newest">Mới nhất</option>
          <option value="oldest">Cũ nhất</option>
          <option value="title_asc">Tên A → Z</option>
          <option value="title_desc">Tên Z → A</option>
        </select>
      </div>
    </FilterBar>
    {!admin && roundsLoaded && !rounds.length ? <p className="text-caption mb-2">Không có đợt đang mở để tạo hoặc đăng ký đề tài mới.</p> : null}
    <div className="topics-subbar">
      <Tabs
        variant="underline"
        asButtons
        idPrefix="topic-view"
        ariaLabel="Lọc đề tài"
        items={topicTabs}
        activeId={view}
        onChange={(next) => { setView(next); setPage(0); }}
      />
      <div className="topic-view-toggle" role="group" aria-label="Chế độ hiển thị danh sách đề tài">
        <button
          type="button"
          className={`topic-view-toggle__btn${layoutMode === "grid" ? " topic-view-toggle__btn--active" : ""}`}
          aria-pressed={layoutMode === "grid"}
          onClick={() => setLayoutMode("grid")}
        >
          <LayoutGrid size={14} aria-hidden="true" />
          Dạng thẻ
        </button>
        <button
          type="button"
          className={`topic-view-toggle__btn${layoutMode === "list" ? " topic-view-toggle__btn--active" : ""}`}
          aria-pressed={layoutMode === "list"}
          onClick={() => setLayoutMode("list")}
        >
          <List size={14} aria-hidden="true" />
          Dạng danh sách
        </button>
      </div>
    </div>
    {message && !detailOpen && !createOpen && !registerOpen ? <p className="alert alert-info" role="status">{message}</p> : null}
    {loading ? <div className="topic-grid" role="status" aria-label="Đang tải đề tài"><SkeletonCard /><SkeletonCard /><SkeletonCard /></div> : !topics.length ?
      <EmptyState icon={<FileText aria-hidden="true" />} title="Chưa có đề tài trong danh sách này" description="Thử đổi mục hoặc từ khóa tìm kiếm để xem thêm đề tài.">
        {!topicChips.length && (filter || sort !== "newest") && <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setFilter(""); setSort("newest"); setPage(0); }}>Xóa bộ lọc</button>}
      </EmptyState> :
      <div className={layoutMode === "list" ? "topic-grid--list" : "grid topic-grid"}>{topics.map((topic) => {
        const round = roundDisplay(topic.round_label);
        const full = topic.registered_member_count >= topic.max_students;
        const canRegister = topic.available && !full && topic.department_id === context.department_id;
        return <article key={topic.id} className={`card topic-card${layoutMode === "list" ? " topic-card--list" : ""}`}>
          <div className="card-body topic-card__body">
            <div className="topic-card__top">
              <div className="topic-card__top-left">
                <span className="topic-code">{topic.code}</span>
                <span className={"topic-card__proposer " + (topic.proposer_type === "STUDENT" ? "topic-card__proposer--student" : "topic-card__proposer--lecturer")}>{topic.proposer_type === "STUDENT" ? "Sinh viên đề xuất" : "Giảng viên đề xuất"}</span>
              </div>
              <div className="topic-card__top-right">
                {topic.proposer_type === "STUDENT" && topic.state === "SUBMITTED" ? (
                  <span className="badge badge-warning">Chờ bộ môn duyệt</span>
                ) : (
                  <ThesisStatusBadge state={topic.state} />
                )}
                {topic.state === "APPROVED" && full && (
                  <span className="badge badge-warning" title="Đã nhận đủ số lượng sinh viên tối đa">
                    Đã đủ số lượng
                  </span>
                )}
              </div>
            </div>
            <h2 className="topic-card-title" title={topic.title}>
              <button type="button" className="topic-card__title-btn" onClick={() => choose(topic)}>
                {topic.title}
              </button>
            </h2>
            <TopicDescriptionPreview description={topic.description} />
            {topic.requirements.length > 0 && <RequirementList items={topic.requirements} preview />}
            {!student && topic.proposer_type === "STUDENT" && topic.state === "SUBMITTED" ?
              <p className="topic-card__pending-note">Chờ bộ môn duyệt. GV được đề xuất có thể xem nội dung, chưa xét tiếp nhận.</p> : null}
            {!student && topic.proposer_type === "STUDENT" && topic.state === "RETURNED" ?
              <p className="topic-card__pending-note">Bộ môn đã trả đề xuất để SV chỉnh sửa. GV chưa xét tiếp nhận.</p> : null}
            <div className="topic-card__footer">
              <div className="topic-card__meta-inline">
                <span className="topic-card__fact">
                  <UserRound size={15} aria-hidden="true" />
                  <span>
                    <small>{topic.proposer_type === "STUDENT" && topic.state !== "APPROVED" ? "GV được SV đề xuất" : "GV tiếp nhận"}</small>{" "}
                    <LecturerProfileLink userId={userId} lecturerId={topic.receiving_lecturer_id} name={topic.receiving_lecturer_name} />
                  </span>
                </span>
                <span className="topic-card__year">
                  <CalendarDays size={15} aria-hidden="true" />
                  <span><small>Năm học</small> <strong>{round.year}</strong>{round.period ? <em>{round.period}</em> : null}</span>
                </span>
                <span className={"topic-card__fact topic-card__capacity" + (full ? " topic-card__capacity--full" : "")}>
                  <Users size={14} aria-hidden="true" />
                  <strong>{topic.registered_member_count}/{topic.max_students} SV</strong>
                </span>
              </div>
              <div className="topic-card__actions">
                <button type="button" className={head && topic.state === "SUBMITTED" ? "btn btn-soft btn-sm" : "btn btn-secondary btn-sm"} onClick={() => choose(topic)}>
                  {head && topic.state === "SUBMITTED" ? <ClipboardCheck size={14} aria-hidden="true" /> : <Eye size={14} aria-hidden="true" />}
                  {head && topic.state === "SUBMITTED" ? "Xem và duyệt" : "Xem chi tiết"}
                </button>
                {student && topic.state === "APPROVED" ? <button type="button" className="btn btn-primary btn-sm" disabled={!canRegister}
                  title={full ? `Đề tài đã nhận đủ ${topic.max_students} sinh viên tối đa.` : undefined}
                  onClick={() => {choose(topic,false); setRegisterOpen(true);}}>
                  <Send size={13} aria-hidden="true" />
                  {canRegister ? topic.registered_member_count ? "Tham gia" : "Đăng ký" : full ? "Đã đủ số lượng" : topic.department_id !== context.department_id ? "Đề tài bộ môn khác" : "Đã đóng đăng ký"}
                </button> : null}
              </div>
            </div>
          </div>
        </article>;
      })}</div>}
    <nav className="pagination" aria-label="Phân trang đề tài">
      <button className="btn btn-secondary" disabled={!page || loading} onClick={() => setPage(page - 1)}>
        <ChevronLeft size={15} aria-hidden="true" />Trang trước
      </button>
      <span>Trang {page + 1}</span>
      <button className="btn btn-secondary" disabled={topics.length < PAGE_SIZE || loading} onClick={() => setPage(page + 1)}>
        Trang sau<ChevronRight size={15} aria-hidden="true" />
      </button>
    </nav>

    <Dialog
      open={detailOpen && !!selected}
      onClose={closeDetail}
      busy={busy}
      variant="drawer"
      size="lg"
      title={selected ? selected.title : "Chi tiết đề tài"}
      headerMeta={selected ? <>
        <span className="topic-code">{selected.code}</span>
        <span className={selected.proposer_type === "STUDENT" ? "topic-card__proposer topic-card__proposer--student" : "topic-card__proposer topic-card__proposer--lecturer"}>
          {selected.proposer_type === "STUDENT" ? "Sinh viên đề xuất" : "Giảng viên đề xuất"}
        </span>
        <ThesisStatusBadge state={selected.state} />
      </> : null}
      footer={selected ? (
        head && selected.state === "SUBMITTED" && selected.proposer_user_id !== userId ? (
          <>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy || !reason.trim()}
              onClick={() => void mutate("/topics/" + selected.id + "/department-decision", "POST", { decision: "RETURN", reason }, selected.row_version)}
            >
              <RotateCcw size={15} aria-hidden="true" />Trả lại để sửa
            </button>
            <button
              type="button"
              className="btn btn-destructive"
              disabled={busy || !reason.trim()}
              onClick={() => void mutate("/topics/" + selected.id + "/department-decision", "POST", { decision: "REJECT", reason }, selected.row_version)}
            >
              <XCircle size={15} aria-hidden="true" />Từ chối đề tài
            </button>
            <button
              type="submit"
              form="topic-dept-review-form"
              className="btn btn-primary"
              disabled={busy || (selected.proposer_type === "STUDENT" && !receiverReady)}
            >
              <Check size={15} aria-hidden="true" />Duyệt đề tài
            </button>
          </>
        ) : editable && !student ? (
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy}
            onClick={() => void mutate("/topics/" + selected.id + "/submit", "POST", undefined, selected.row_version)}
          >
            <Send size={14} aria-hidden="true" />Gửi bộ môn duyệt
          </button>
        ) : student && selected.state === "APPROVED" ? (() => {
          const full = selected.registered_member_count >= selected.max_students;
          const canRegister = selected.available && !full && selected.department_id === context.department_id;
          return (
            <button
              type="button"
              className="btn btn-primary"
              disabled={!canRegister || busy}
              title={full ? `Đề tài đã nhận đủ ${selected.max_students} sinh viên tối đa.` : undefined}
              onClick={() => { setDetailOpen(false); setRegisterOpen(true); }}
            >
              <Send size={14} aria-hidden="true" />
              {canRegister ? selected.registered_member_count ? "Tham gia" : "Đăng ký" : full ? "Đã đủ số lượng" : selected.department_id !== context.department_id ? "Đề tài bộ môn khác" : "Đã đóng đăng ký"}
            </button>
          );
        })() : null
      ) : null}
    >
      {selected ? <div className="stack topic-detail-content">
        <WorkflowSteps steps={["Soạn đề xuất","TBM xét duyệt","Mở đăng ký"]} current={["APPROVED","LOCKED"].includes(selected.state)?2:selected.state==="SUBMITTED"?1:0}/>
        {selected.archived_at && <p className="alert alert-warning">Đề tài đã ngừng sử dụng: {selected.archive_reason}. Hồ sơ đã liên kết vẫn được giữ nguyên.</p>}
        <section className="topic-detail-content__section">
          <h3>Mô tả đề tài</h3>
          {renderDescriptionContent(selected.description)}
        </section>
        <dl className="topic-drawer-meta">
          <div>
            <dt>{selected.proposer_type === "STUDENT" && selected.state !== "APPROVED" ? "GV được SV đề xuất" : "Giảng viên tiếp nhận"}</dt>
            <dd><LecturerProfileLink userId={userId} lecturerId={selected.receiving_lecturer_id} name={selected.receiving_lecturer_name} /></dd>
          </div>
          <div>
            <dt>Chỉ tiêu sinh viên</dt>
            <dd>{selected.registered_member_count}/{selected.max_students} SV</dd>
          </div>
          <div>
            <dt>Đợt khóa luận</dt>
            <dd>{selected.round_label}</dd>
          </div>
          <div>
            <dt>Nguồn đề xuất</dt>
            <dd>{selected.proposer_type === "STUDENT" ? "Sinh viên đề xuất" : "Giảng viên đề xuất"}</dd>
          </div>
        </dl>
        <section className="topic-detail-content__section">
          <h3>Kỹ năng và yêu cầu đối với sinh viên</h3>
          <RequirementList items={selected.requirements} />
        </section>
        <section className="topic-detail-content__section topic-registered-students">
          <div className="topic-registered-students__header">
            <Users size={16} aria-hidden="true" />
            <h3>Sinh viên đã đăng ký ({selected.registered_member_count}/{selected.max_students} SV)</h3>
          </div>
          {selected.registered_students && selected.registered_students.length > 0 ? (
            <ul className="topic-drawer-students" aria-label="Sinh viên đã đăng ký đề tài">
              {selected.registered_students.map((st) => (
                <li key={st.student_id} className="topic-drawer-student">
                  <div className="topic-drawer-student__ident">
                    <strong>{st.display_name}</strong>
                    <span className="topic-drawer-student__sub">
                      <span className="code-chip">{st.student_code}</span>
                      {st.class_name ? <span>· {st.class_name}</span> : null}
                    </span>
                  </div>
                  <div className="topic-drawer-student__badges">
                    {st.is_coordinator ? (
                      <span className="badge badge-primary">Nhóm trưởng</span>
                    ) : (
                      <span className="badge badge-neutral">Thành viên</span>
                    )}
                    {st.registration_state === "LECTURER_ACCEPTED" || st.registration_state === "FINALIZED" ? (
                      <span className="badge badge-success">Đã tiếp nhận</span>
                    ) : st.registration_state === "SUBMITTED" ? (
                      <span className="badge badge-info">Chờ GV duyệt</span>
                    ) : (
                      <span className="badge badge-warning">Đang đăng ký</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : selected.registered_member_count > 0 ? (
            <p className="text-body-sm text-muted">Đã có {selected.registered_member_count} sinh viên đăng ký tham gia đề tài này.</p>
          ) : (
            <p className="text-body-sm text-muted">Chưa có sinh viên nào đăng ký đề tài này.</p>
          )}
        </section>
        {!student && selected.proposer_type === "STUDENT" && selected.state === "SUBMITTED" && !head ?
          <p className="registration-card__stage"><strong>Đang chờ bộ môn xét đề tài</strong>
            <span>Bạn chỉ xem nội dung ở bước này. Sau khi bộ môn duyệt và xác nhận GV tiếp nhận, bạn mới xét đăng ký của SV.</span></p> : null}
        {selected.decision_reason ? <p className="alert alert-warning">Góp ý của bộ môn: {selected.decision_reason}</p> : null}
        {student && selected.proposer_type === "STUDENT" && selected.proposer_user_id === userId && selected.state === "APPROVED" ?
          <p className="alert alert-info">Bộ môn đã duyệt đề tài. Đăng ký cá nhân bạn đã gửi vẫn chờ GV tiếp nhận xét; không cần đăng ký lại. Xem trạng thái tại mục Đăng ký.</p> : null}
        {editable ? <>
          <TopicEditor key={selected.id + "-" + selected.row_version} topic={selected} rounds={rounds}
            lecturers={lecturers} context={context} busy={busy}
            onSave={(payload) => mutate("/topics/" + selected.id,"PATCH",payload,selected.row_version)} />
          {student ? <p className="text-body-sm text-muted">Chỉnh sửa xong, mở Đăng ký để gửi đề xuất cho bộ môn.</p> : null}
        </> : null}
        {head && selected.state === "SUBMITTED" && selected.proposer_user_id !== userId ?
          <form id="topic-dept-review-form" className="review-panel" onSubmit={(event) => {event.preventDefault(); if (selected.proposer_type === "STUDENT" && !receiverReady) return; void mutate("/topics/" + selected.id + "/department-decision","POST",
            {decision:"APPROVE",revised_title:revisedTitle,reason:reason || null,
              ...(selected.proposer_type === "STUDENT" ? {receiving_lecturer_id:receiver} : {})},selected.row_version);}}>
            <div className="review-panel__head"><ClipboardCheck size={16} aria-hidden="true" /><h3>Bộ môn xét duyệt</h3></div>
            <div className="review-panel__fields">
              <label className="review-field">
                <span className="review-field__label">Tên đề tài sau khi duyệt</span>
                <input className="input" required minLength={5} maxLength={500}
                  value={revisedTitle} onChange={(event) => setRevisedTitle(event.target.value)} />
                <span className="review-field__hint">Tên cũ và tên mới được giữ trong lịch sử.</span>
              </label>
              {selected.proposer_type === "STUDENT" ? <div className="review-field">
                <label htmlFor="topic-receiver" className="review-field__label">GV tiếp nhận (xác nhận hoặc chọn lại)</label>
                <select id="topic-receiver" className="input" required disabled={busy || lecturersLoading || !!lecturersError} value={receiverReady ? receiver : ""} aria-describedby="receiver-hint" onChange={(event) => setReceiver(event.target.value)}>
                  <option value="">Chọn GV</option>{lecturers.map((lecturer) => <option key={lecturer.id} value={lecturer.id} disabled={lecturer.available === false}>{lecturer.recommended ? "★ Phù hợp · " : ""}{lecturer.display_name} — {lecturer.department_name}{lecturer.available === false ? " · Đã đủ 3 khóa luận" : ""}</option>)}
                </select>
                <span id="receiver-hint" className="review-field__hint" role="status">{lecturersLoading ? "Đang tải danh sách giảng viên…" : lecturersError ? `Chưa tải được danh sách: ${lecturersError}` : !lecturers.length ? "Chưa có giảng viên phù hợp trong phạm vi của bạn." : !receiverReady ? "Vui lòng chọn GV tiếp nhận hợp lệ trước khi duyệt. GV được đề xuất có thể không còn trong danh sách hiện hành." : "Đã chọn GV tiếp nhận. Bạn có thể giữ hoặc chọn lại."}</span>
                {lecturers.find(row=>row.id===receiver)?.recommended&&<span className="review-field__hint">Chuyên môn đã xác nhận: {lecturers.find(row=>row.id===receiver)?.recommendation_reasons?.join("; ")}. Đây là gợi ý để TBM xem xét.</span>}
                {lecturersError && <button type="button" className="btn btn-secondary" disabled={busy || lecturersLoading} onClick={()=>void loadLecturers()}>Tải lại danh sách giảng viên</button>}
                </div> : null}
              <label className="review-field">
                <span className="review-field__label">Góp ý / lý do</span>
                <textarea className="input" rows={3} maxLength={2000} value={reason} onChange={(event) => setReason(event.target.value)} />
              </label>
            </div>
          </form> : null}
        <TopicLifecycle key={selected.id+"-"+selected.row_version} topic={selected} context={context} onChanged={async()=>{closeDetail();setSelected(null);await reload();setMessage("Đã cập nhật đề tài và ghi nhật ký.");}}/>
        {selected.title_versions.length > 1 ? <details className="topic-drawer-accordion"><summary>Lịch sử đổi tên đề tài ({selected.title_versions.length - 1} lần)</summary>
          <ol className="requirement-list">{selected.title_versions.map((version) => <li key={version.version_no}>
            Phiên bản {version.version_no}: {version.title} — {new Date(version.created_at).toLocaleString("vi-VN")}
          </li>)}</ol>
        </details> : null}
      </div> : null}
      {drawerError ? <p className="alert alert-danger" role="alert">{drawerError}</p> : message ? <p className="alert alert-info" role="status">{message}</p> : null}
    </Dialog>
    <Dialog open={createOpen} onClose={() => setCreateOpen(false)} busy={busy}
      title={student ? "Tự đề xuất và lập đăng ký" : "Tạo đề tài mới"} size="lg">
      {createOpen ? <TopicEditor rounds={rounds} lecturers={lecturers} context={context} busy={busy}
        onSave={(payload) => mutate("/topics","POST",payload)} onPropose={(payload, evidence) => register(payload, true, evidence)} /> : null}
      {message ? <p className="alert alert-danger" role="alert">{message}</p> : null}
    </Dialog>
    <Dialog open={registerOpen && !!selected} onClose={() => setRegisterOpen(false)} busy={busy} title="Đăng ký đề tài" size="lg">
      {selected && registerOpen ? <div className="stack">
        <h3>{selected.title}</h3><p>{selected.code} · {selected.round_label}</p>
        <p>Đã đăng ký: {selected.registered_member_count}/{selected.max_students} SV.</p>
        {selected.registration_state === "LECTURER_ACCEPTED" || selected.registration_state === "FINALIZED" || selected.state === "LOCKED"
          ? <p className="alert alert-success">Giảng viên đã chấp nhận chính thức. Nhóm và GVHD đã được chốt trong hồ sơ khóa luận; không nhận thêm thành viên qua đăng ký này.</p>
          : null}
        <RequirementList items={selected.requirements} />
        {selected.registration_state === "LECTURER_ACCEPTED" || selected.registration_state === "FINALIZED" || selected.state === "LOCKED" ? null :
          <RegistrationForm context={context} userId={userId} roundId={selected.round_id} busy={busy}
            joining={selected.registered_member_count > 0} onSubmit={(evidence) => register({topic_id:selected.id,confirm_creator:true},false,evidence)} />}
      </div> : null}
      {message ? <p className="alert alert-danger" role="alert">{message}</p> : null}
    </Dialog>
  </>;
}
