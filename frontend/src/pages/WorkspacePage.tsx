import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, CalendarDays, ClipboardList, FileText, GraduationCap, UsersRound } from "lucide-react";
import type { Context, OpenRound, Registration, Topic } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";
import AdminDashboard from "../components/domain/AdminDashboard";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import { roleLabel } from "../components/layout/roleLabel";

type PendingSummary = {count: number; items: Registration[]};
type WorkspaceLink = {path: string; title: string; detail: string; icon: typeof FileText};

function formatLocalDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("vi-VN", {
    day: "numeric", month: "long", hour: "2-digit", minute: "2-digit",
  });
}

export default function WorkspacePage({context}: {context: Context}) {
  const [rounds, setRounds] = useState<OpenRound[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const head = context.actions.includes("topic:department_decide");
  const workflowAccess = context.base_role === "STUDENT" || context.base_role === "LECTURER";
  const isStudent = context.base_role === "STUDENT";
  const isAdmin = context.base_role === "ADMIN";

  useEffect(() => {
    if (!workflowAccess) {setLoading(false); return;}
    let alive = true;
    Promise.all([request<OpenRound[]>("/rounds/open", context.user_id),
      request<Topic[]>("/topics?limit=5&view=" + (head ? "pending" : context.base_role === "LECTURER" ? "mine" : "all"), context.user_id),
      context.base_role === "LECTURER"
        ? request<PendingSummary>("/topic-registrations/pending-summary", context.user_id)
        : request<Registration[]>("/topic-registrations?limit=5", context.user_id)])
      .then(([r,t,g]) => {if (alive) {setRounds(r); setTopics(t);
        if (Array.isArray(g)) setRegistrations(g);
        else {setRegistrations(g.items); setPendingCount(g.count);}
      }})
      .catch((cause) => {if (alive) setError(errorMessage(cause));})
      .finally(() => {if (alive) setLoading(false);});
    return () => {alive = false;};
  }, [context.user_id, context.base_role, head, workflowAccess]);

  const dateLabel = new Date().toLocaleDateString("vi-VN", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
  const person = context.display_name.trim() || "bạn";
  const primaryPath = isAdmin ? "/rounds"
    : isStudent ? (registrations.length ? "/registrations" : "/topics")
    : head ? (pendingCount > 0 ? "/registrations" : "/topics") : "/topics";
  const primaryLabel = isAdmin ? "Quản lý đợt KLTN"
    : isStudent ? (registrations.length ? "Theo dõi đăng ký" : "Khám phá đề tài")
    : head && pendingCount > 0 ? "Xem hồ sơ chờ xét"
    : head ? "Duyệt đề tài" : "Quản lý đề tài";
  const secondaryPath = isAdmin ? "/administration" : isStudent ? "/theses" : head ? "/topics" : "/registrations";
  const secondaryLabel = isAdmin ? "Tài khoản"
    : isStudent ? "Không gian khóa luận" : head ? "Danh sách đề tài" : "Hồ sơ đăng ký";
  const welcomeCopy = isAdmin
    ? "Tổ chức đợt khóa luận, phân công nhiệm vụ và quản lý tài khoản."
    : isStudent
      ? "Chọn đề tài, theo dõi đăng ký và từng bước hoàn thành khóa luận."
      : head
        ? "Rà soát đề tài và tiếp nhận hồ sơ trong phạm vi bộ môn."
        : "Quản lý đề tài, hồ sơ đăng ký và khóa luận đang hướng dẫn.";

  const shortcuts: WorkspaceLink[] = isAdmin ? [
    {path: "/rounds", title: "Đợt khóa luận", detail: "Lịch đăng ký và trạng thái đợt", icon: CalendarDays},
    {path: "/administration", title: "Tài khoản", detail: "Trạng thái và hỗ trợ truy cập", icon: UsersRound},
    {path: "/administration/assignments", title: "Phân công theo đợt", detail: "Nhiệm vụ và quyền theo đợt KLTN", icon: ClipboardList},
    {path: "/forms", title: "Biểu mẫu Khoa", detail: "Tài liệu học vụ đang phát hành", icon: FileText},
  ] : [
    {path: "/topics", title: isStudent ? "Tìm đề tài" : head ? "Duyệt đề tài" : "Đề tài của tôi",
      detail: isStudent ? "Lọc theo nội dung và yêu cầu" : "Theo dõi danh sách theo vai trò", icon: FileText},
    {path: "/registrations", title: isStudent ? "Đăng ký của tôi" : head ? "Hồ sơ cần xử lý" : "Hồ sơ đăng ký",
      detail: isStudent ? "Gửi hồ sơ và theo dõi xét duyệt" : "Xem quyết định và phản hồi", icon: ClipboardList},
    {path: "/theses", title: "Không gian khóa luận", detail: "Đề cương, tiến độ và tài liệu", icon: GraduationCap},
  ];

  return <>
    <PageHeader title="Tổng quan">
      <span className="workspace-date">{dateLabel}</span>
    </PageHeader>
    {error ? <p role="alert" className="alert alert-danger">{error}</p> : null}

    <section className="welcome-spread" aria-label="Lối vào không gian KLTN">
      <div className="welcome-copy">
        <span className="welcome-kicker">DHTU / KHÓA LUẬN TỐT NGHIỆP</span>
        <h2>Chào {person}</h2>
        <p>{welcomeCopy}</p>
        <div className="welcome-actions">
          <Link className="btn btn-primary btn-lg" to={primaryPath}>{primaryLabel}<ArrowRight size={16} aria-hidden="true" /></Link>
          <Link className="btn btn-secondary" to={secondaryPath}>{secondaryLabel}</Link>
        </div>
      </div>
      <aside className="welcome-brief" aria-label="Thông tin đợt KLTN">
        <div className="welcome-brief-top">
          <span>{isAdmin ? "ĐIỀU HÀNH HỌC VỤ" : "LỊCH HỌC VỤ"}</span>
          <span className="welcome-brief-mark"><CalendarDays size={15} aria-hidden="true" /></span>
        </div>
        {isAdmin ? <>
          <div><span className="welcome-brief-label">KHÔNG GIAN QUẢN TRỊ</span>
            <h3>Đợt & phân công</h3>
            <p>Thiết lập lịch học vụ và phân quyền theo nhiệm vụ.</p>
          </div>
          <div className="welcome-brief-date"><CalendarDays size={15} aria-hidden="true" /><span>{dateLabel}</span></div>
        </> : loading ? <>
          <div><span className="welcome-brief-label">ĐỢT ĐĂNG KÝ</span><h3>Đang cập nhật lịch</h3>
            <p>Thông tin mới nhất sẽ hiện tại đây.</p></div>
        </> : rounds.length ? <>
          <div><span className="welcome-brief-label">ĐỢT ĐANG MỞ</span><h3>{rounds[0].label}</h3>
            <p>{rounds[0].academic_year} · {rounds[0].code}</p>
          </div>
          <div className="welcome-brief-date"><CalendarDays size={15} aria-hidden="true" />
            <span>Đóng đăng ký<br /><strong>{formatLocalDate(rounds[0].closes_at)}</strong></span></div>
        </> : <>
          <div><span className="welcome-brief-label">ĐỢT ĐĂNG KÝ</span><h3>Chưa có đợt mở</h3>
            <p>Các đợt đang mở sẽ hiển thị tại không gian này.</p></div>
          <div className="welcome-brief-date"><CalendarDays size={15} aria-hidden="true" /><span>{dateLabel}</span></div>
        </>}
      </aside>
    </section>

    {isAdmin && <AdminDashboard userId={context.user_id}/>}
    <section className="workspace-shortcuts" aria-labelledby="workspace-shortcuts-title">
      <div className="workspace-section-head">
        <div><span className="workspace-section-kicker">{roleLabel(context).toLocaleUpperCase("vi-VN")}</span>
          <h2 id="workspace-shortcuts-title">Đi đến công việc</h2></div>
      </div>
      <div className="workspace-shortcut-grid">
        {shortcuts.map((item, index) => {
          const Icon = item.icon;
          return <Link className="workspace-shortcut" to={item.path} key={item.path}>
            <span className="workspace-shortcut-number">0{index + 1}</span>
            <Icon className="workspace-shortcut-icon" size={19} aria-hidden="true" />
            <span className="workspace-shortcut-copy"><strong>{item.title}</strong><small>{item.detail}</small></span>
            <ArrowRight className="workspace-shortcut-arrow" size={15} aria-hidden="true" />
          </Link>;
        })}
      </div>
    </section>

    {workflowAccess && loading ? <p className="workspace-loading" role="status">Đang cập nhật công việc…</p> : null}
    {workflowAccess && !loading ? <div className="workspace-records">
      <section className="card overview-card"><div className="card-body stack">
        <div className="workspace-panel-heading"><h2><BookOpen size={17} aria-hidden="true" />{head ? "Đề tài chờ duyệt" : isStudent ? "Đề tài đã duyệt" : "Đề tài của tôi"}</h2>
          <Link to="/topics">Tất cả đề tài <ArrowRight size={13} aria-hidden="true" /></Link></div>
        {topics.length ? <ul className="overview-list">{topics.map((topic) => <li key={topic.id}>
          <span><span className="topic-code">{topic.code}</span>{topic.title}</span><ThesisStatusBadge state={topic.state} />
        </li>)}</ul> : <div className="overview-empty"><BookOpen size={24} aria-hidden="true" /><p>{head ? "Không có đề tài chờ duyệt." : "Chưa có đề tài trong danh sách."}</p></div>}
      </div></section>
      <section className="card overview-card"><div className="card-body stack">
        <div className="workspace-panel-heading"><h2><ClipboardList size={17} aria-hidden="true" />
          {context.base_role === "LECTURER" ? <>Hồ sơ cần xử lý <span className="overview-count">{pendingCount}</span></> : "Đăng ký gần đây"}</h2>
          <Link to="/registrations">Tất cả hồ sơ <ArrowRight size={13} aria-hidden="true" /></Link></div>
        {registrations.length ? <ul className="overview-list">{registrations.map((row) => <li key={row.id}>
          {context.base_role === "LECTURER" ? <Link to={"/registrations?focus=" + row.id}><span className="topic-code">{row.topic_code}</span>{row.topic_title}</Link>
            : <span><span className="topic-code">{row.topic_code}</span>{row.topic_title}</span>}<ThesisStatusBadge state={row.state} />
        </li>)}</ul> : <div className="overview-empty"><ClipboardList size={24} aria-hidden="true" /><p>{context.base_role === "LECTURER" ? "Không có hồ sơ cần xử lý." : "Chưa có đăng ký trong phạm vi của bạn."}</p></div>}
      </div></section>
    </div> : null}
  </>;
}
