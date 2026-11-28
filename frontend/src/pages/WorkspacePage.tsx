import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  Bot,
  CalendarDays,
  ClipboardList,
  Compass,
  FolderOpen,
  GraduationCap,
  Lightbulb,
  ListChecks,
  Scale,
  UsersRound,
} from "lucide-react";
import type { Context, OpenRound, Registration, Thesis, Topic } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";
import AdminDashboard from "../components/domain/AdminDashboard";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import { ThesisJourney, type JourneyStage } from "../components/ui/Timeline";
import { CampusBannerArt } from "../components/ui/CampusArtwork";
import { SkeletonCard } from "../components/ui/Skeleton";
import EmptyState from "../components/ui/EmptyState";

type PendingSummary = { count: number; items: Registration[] };

function formatLocalDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("vi-VN", {
        day: "numeric",
        month: "long",
        hour: "2-digit",
        minute: "2-digit",
      });
}

function buildStudentStages(activeThesis: Thesis | undefined, registrations: Registration[]): JourneyStage[] {
  const hasReg = registrations.length > 0;
  const st = activeThesis?.state || "";
  if (activeThesis && st === "WITHDRAWN") {
    return [
      { id: "reg", title: "Đăng ký", statusText: "Đã thôi thực hiện", state: "done", to: "/withdrawals" },
      { id: "proposal", title: "Đề cương", statusText: "Đã kết thúc", state: "upcoming", to: "/withdrawals" },
      { id: "progress", title: "Tiến độ", statusText: "Đã kết thúc", state: "upcoming" },
      { id: "evaluation", title: "Phản biện", statusText: "Đã kết thúc", state: "upcoming" },
      { id: "defense", title: "Bảo vệ", statusText: "Đã kết thúc", state: "upcoming" },
    ];
  }
  const proposalDone = ["PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED", "READY_FOR_DEFENSE", "DEFENDED", "COMPLETED", "ARCHIVED"].includes(st);
  const progressDone = ["READY_FOR_DEFENSE", "DEFENDED", "COMPLETED", "ARCHIVED"].includes(st);
  const evalDone = ["DEFENDED", "COMPLETED", "ARCHIVED"].includes(st);
  const defenseDone = ["DEFENDED", "COMPLETED", "ARCHIVED"].includes(st);

  const stage1State = activeThesis ? "done" : "current";
  const stage2State = !activeThesis ? "upcoming" : proposalDone ? "done" : "current";
  const stage3State = !activeThesis || !proposalDone ? "upcoming" : progressDone ? "done" : "current";
  const stage4State = !activeThesis ? "upcoming" : evalDone ? "done" : st === "READY_FOR_DEFENSE" ? "current" : "upcoming";
  const stage5State = !activeThesis ? "upcoming" : defenseDone ? "done" : "upcoming";

  return [
    {
      id: "reg",
      title: "Đăng ký",
      statusText: activeThesis ? "Hoàn thành" : hasReg ? "Đang theo dõi" : "Chọn đề tài",
      state: stage1State,
      to: "/registrations",
    },
    {
      id: "proposal",
      title: "Đề cương",
      statusText: !activeThesis ? "Chưa đến" : proposalDone ? "Hoàn thành" : "Đang thực hiện",
      state: stage2State,
      to: activeThesis ? `/theses/${activeThesis.id}?section=submissions&kind=PROPOSAL` : "/theses",
    },
    {
      id: "progress",
      title: "Tiến độ",
      statusText: !activeThesis || !proposalDone ? "Chưa đến" : progressDone ? "Hoàn thành" : "Đang thực hiện",
      state: stage3State,
      to: activeThesis ? `/theses/${activeThesis.id}?section=progress` : "/theses",
    },
    {
      id: "evaluation",
      title: "Phản biện",
      statusText: evalDone ? "Hoàn thành" : st === "READY_FOR_DEFENSE" ? "Đủ điều kiện" : "Chưa đến",
      state: stage4State,
      to: activeThesis ? `/evaluation/${activeThesis.id}` : "/evaluation",
    },
    {
      id: "defense",
      title: "Bảo vệ",
      statusText: st === "COMPLETED" || st === "ARCHIVED" ? "Hoàn thành" : st === "DEFENDED" ? "Đã bảo vệ · nộp lưu" : "Chưa đến",
      state: stage5State,
      to: "/defense",
    },
  ];
}

export default function WorkspacePage({ context }: { context: Context }) {
  const [rounds, setRounds] = useState<OpenRound[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const head = context.actions.includes("topic:department_decide");
  const workflowAccess = context.base_role === "STUDENT" || context.base_role === "LECTURER";
  const isStudent = context.base_role === "STUDENT";
  const isAdmin = context.base_role === "ADMIN";

  useEffect(() => {
    if (!workflowAccess) {
      setLoading(false);
      return;
    }
    let alive = true;
    Promise.all([
      request<OpenRound[]>("/rounds/open", context.user_id),
      request<Topic[]>(
        "/topics?limit=5&view=" + (head ? "pending" : context.base_role === "LECTURER" ? "mine" : "all"),
        context.user_id
      ),
      context.base_role === "LECTURER"
        ? request<PendingSummary>("/topic-registrations/pending-summary", context.user_id)
        : request<Registration[]>("/topic-registrations?limit=5", context.user_id),
      request<Thesis[]>("/theses", context.user_id).catch(() => [] as Thesis[]),
    ])
      .then(([r, t, g, th]) => {
        if (!alive) return;
        setRounds(r);
        setTopics(t);
        setTheses(th);
        if (Array.isArray(g)) setRegistrations(g);
        else {
          setRegistrations(g.items);
          setPendingCount(g.count);
        }
      })
      .catch((cause) => {
        if (alive) setError(errorMessage(cause));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [context.user_id, context.base_role, head, workflowAccess]);

  const dateLabel = new Date().toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const person = context.display_name.trim() || "bạn";
  const activeThesis = theses.find((t) => t.state !== "WITHDRAWN") ?? theses[0];
  const archivedOrDone = !!activeThesis && ["COMPLETED", "ARCHIVED"].includes(activeThesis.state);

  const primaryPath = isAdmin
    ? "/rounds"
    : isStudent
      ? activeThesis
        ? activeThesis.state === "WITHDRAWN"
          ? "/withdrawals"
          : activeThesis.state === "DEFENDED"
            ? `/repository?mode=work&focus=${activeThesis.id}`
            : archivedOrDone
              ? `/repository?focus=${activeThesis.id}`
              : `/theses/${activeThesis.id}`
        : registrations.length
          ? "/registrations"
          : "/topics"
      : head
        ? pendingCount > 0
          ? "/registrations"
          : "/topics"
        : pendingCount > 0
          ? "/registrations"
          : "/topics";

  const primaryLabel = isAdmin
    ? "Quản lý đợt KLTN"
    : isStudent
      ? activeThesis
        ? activeThesis.state === "WITHDRAWN"
          ? "Xem hồ sơ xin thôi"
          : activeThesis.state === "DEFENDED"
            ? "Mở hồ sơ nộp lưu"
            : archivedOrDone
              ? "Xem bản lưu trữ"
              : "Mở hồ sơ khóa luận"
        : registrations.length
          ? "Theo dõi đăng ký"
          : "Khám phá đề tài"
      : head && pendingCount > 0
        ? "Xem hồ sơ chờ xét"
        : head
          ? "Duyệt đề tài"
          : pendingCount > 0
            ? "Tiếp nhận đăng ký"
            : "Quản lý đề tài";

  const secondaryPath = isAdmin
    ? "/administration"
    : isStudent
      ? activeThesis
        ? ["DEFENDED", "COMPLETED", "ARCHIVED", "WITHDRAWN"].includes(activeThesis.state)
          ? `/theses/${activeThesis.id}`
          : `/theses/${activeThesis.id}?section=submissions`
        : "/topics"
      : head
        ? "/defense"
        : "/theses";
  const secondaryLabel = isAdmin
    ? "Quản lý tài khoản"
    : isStudent
      ? activeThesis
        ? ["DEFENDED", "COMPLETED", "ARCHIVED", "WITHDRAWN"].includes(activeThesis.state)
          ? "Xem hồ sơ khóa luận"
          : "Hồ sơ nộp & xét duyệt"
        : "Danh sách đề tài"
      : head
        ? "Hội đồng & bảo vệ"
        : "Khóa luận hướng dẫn";

  const welcomeCopy = isAdmin
    ? "Điều hành đợt khóa luận, phân công nhiệm vụ và quản lý tài khoản hệ thống."
    : isStudent
      ? "Theo dõi hành trình khóa luận, nộp hồ sơ đúng mốc và phối hợp cùng giảng viên hướng dẫn."
      : head
        ? "Rà soát đề tài, điều phối hồ sơ đăng ký và giám sát tiến độ hội đồng trong phạm vi bộ môn."
        : "Xử lý hồ sơ đăng ký, phản hồi đề cương và đồng hành cùng sinh viên trong suốt đợt khóa luận.";

  const studentStages = isStudent ? buildStudentStages(activeThesis, registrations) : [];
  const nextGuidance = isStudent
    ? activeThesis
      ? activeThesis.state === "WITHDRAWN"
        ? { text: "Hồ sơ khóa luận này đã được ghi nhận thôi thực hiện.", to: "/withdrawals", action: "Xem chi tiết xin thôi" }
        : archivedOrDone
          ? { text: "Khóa luận đã hoàn thành và lưu trữ nội bộ.", to: `/repository?focus=${activeThesis.id}`, action: "Xem bản lưu trữ" }
          : activeThesis.state === "DEFENDED"
            ? { text: "Đã bảo vệ: hoàn tất nộp bản chỉnh sửa sau bảo vệ vào kho nội bộ.", to: `/repository?mode=work&focus=${activeThesis.id}`, action: "Mở hồ sơ nộp lưu" }
            : activeThesis.state === "READY_FOR_DEFENSE"
              ? { text: "Đã đủ điều kiện bảo vệ: theo dõi lịch hội đồng và chuẩn bị trình bày.", to: "/defense", action: "Xem lịch bảo vệ" }
              : { text: `Đang thực hiện đề tài "${activeThesis.title}". Kiểm tra hạn nộp đề cương và báo cáo tiến độ.`, to: `/theses/${activeThesis.id}?section=submissions`, action: "Mở hồ sơ nộp" }
      : registrations.length
        ? { text: "Hồ sơ đăng ký đang được xử lý. Kiểm tra minh chứng và trạng thái xác nhận từ GV.", to: "/registrations", action: "Xem đăng ký của tôi" }
        : { text: "Bắt đầu bằng việc lựa chọn đề tài phù hợp hoặc tự đề xuất đề tài mới.", to: "/topics", action: "Chọn đề tài ngay" }
    : null;

  return (
    <>
      <PageHeader title="Tổng quan">
        <span className="workspace-date">{dateLabel}</span>
      </PageHeader>
      {error ? (
        <p role="alert" className="alert alert-danger">
          {error}
        </p>
      ) : null}

      <section className="welcome-spread" aria-label="Lối vào không gian KLTN">
        <div className="welcome-copy">
          <CampusBannerArt className="welcome-campus-art" />
          <span className="welcome-kicker">DThU · KHOA CÔNG NGHỆ VÀ KỸ THUẬT</span>
          <h2>Chào {person}</h2>
          <p>{welcomeCopy}</p>
          <div className="welcome-actions">
            <Link className="btn btn-primary btn-lg" to={primaryPath}>
              {isStudent ? <GraduationCap size={17} aria-hidden="true" /> : <ClipboardList size={17} aria-hidden="true" />}
              {primaryLabel}
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <Link className="btn btn-soft btn-lg" to={secondaryPath}>
              <FolderOpen size={16} aria-hidden="true" />
              {secondaryLabel}
            </Link>
          </div>
        </div>
        <aside className="welcome-brief" aria-label="Thông tin đợt KLTN">
          <div className="welcome-brief-top">
            <span>{isAdmin ? "ĐIỀU HÀNH HỌC VỤ" : "LỊCH HỌC VỤ"}</span>
            <span className="welcome-brief-mark">
              <CalendarDays size={16} aria-hidden="true" />
            </span>
          </div>
          {isAdmin ? (
            <>
              <div>
                <span className="welcome-brief-label">KHÔNG GIAN QUẢN TRỊ</span>
                <h3>Đợt &amp; phân công</h3>
                <p>Thiết lập lịch học vụ và phân quyền theo nhiệm vụ.</p>
              </div>
              <div className="welcome-brief-date">
                <CalendarDays size={15} aria-hidden="true" />
                <span>{dateLabel}</span>
              </div>
            </>
          ) : loading ? (
            <div>
              <span className="welcome-brief-label">ĐỢT ĐĂNG KÝ</span>
              <h3>Đang cập nhật lịch</h3>
              <p>Thông tin đợt hiện hành sẽ hiển thị tại đây.</p>
            </div>
          ) : rounds.length ? (
            <>
              <div>
                <span className="welcome-brief-label">ĐỢT ĐANG MỞ</span>
                <h3>{rounds[0].label}</h3>
                <p>
                  {rounds[0].academic_year} · {rounds[0].code}
                </p>
              </div>
              <div className="welcome-brief-date">
                <CalendarDays size={15} aria-hidden="true" />
                <span>
                  Đóng đăng ký
                  <br />
                  <strong>{formatLocalDate(rounds[0].closes_at)}</strong>
                </span>
              </div>
            </>
          ) : (
            <>
              <div>
                <span className="welcome-brief-label">ĐỢT ĐĂNG KÝ</span>
                <h3>Chưa có đợt mở</h3>
                <p>Các đợt đang mở sẽ hiển thị tại không gian này.</p>
              </div>
              <div className="welcome-brief-date">
                <CalendarDays size={15} aria-hidden="true" />
                <span>{dateLabel}</span>
              </div>
            </>
          )}
        </aside>
      </section>

      {isAdmin && <AdminDashboard userId={context.user_id} />}

      {workflowAccess && !loading && (
        <section className="role-brief" aria-label="Việc cần làm theo vai trò">
          {isStudent ? (
            <>
              <div className="role-brief__head">
                <div>
                  <span className="workspace-section-kicker">TIẾN TRÌNH CÁ NHÂN</span>
                  <h2>Hành trình Khóa luận Tốt nghiệp</h2>
                </div>
                {activeThesis && <ThesisStatusBadge state={activeThesis.state} />}
              </div>
              <ThesisJourney stages={studentStages} ariaLabel="Hành trình Khóa luận Tốt nghiệp" />
              {nextGuidance ? (
                <div className="journey-next-action">
                  <div className="journey-next-action__copy">
                    <Compass size={18} aria-hidden="true" />
                    <span>{nextGuidance.text}</span>
                  </div>
                  <Link className="btn btn-soft btn-sm" to={nextGuidance.to}>
                    {nextGuidance.action}
                    <ArrowRight size={14} aria-hidden="true" />
                  </Link>
                </div>
              ) : null}
            </>
          ) : (
            <>
              <div className="role-brief__head">
                <div>
                  <span className="workspace-section-kicker">
                    {head ? "BÀN ĐIỀU PHỐI TRƯỞNG BỘ MÔN" : "BÀN LÀM VIỆC GIẢNG VIÊN"}
                  </span>
                  <h2>{head ? "Hồ sơ & nghiệp vụ cần xử lý" : "Theo dõi hướng dẫn & phản biện"}</h2>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link className="btn btn-soft btn-sm" to="/evaluation">
                    <Scale size={14} aria-hidden="true" />
                    Phản biện &amp; điều kiện
                  </Link>
                  <Link className="btn btn-secondary btn-sm" to="/defense">
                    <CalendarDays size={14} aria-hidden="true" />
                    Hội đồng &amp; bảo vệ
                  </Link>
                </div>
              </div>
              <div className="role-queue-grid">
                <Link className="role-queue-item" to="/registrations">
                  <div>
                    <strong>Hồ sơ đăng ký chờ xử lý</strong>
                    <small>{head ? "Điều phối hoặc giải quyết từ chối" : "Xem xét tiếp nhận sinh viên"}</small>
                  </div>
                  <span className="role-queue-item__count">{pendingCount}</span>
                </Link>
                <Link className="role-queue-item" to="/topics">
                  <div>
                    <strong>{head ? "Đề tài chờ bộ môn duyệt" : "Đề tài phụ trách"}</strong>
                    <small>{head ? "Kiểm tra mục tiêu và yêu cầu" : "Đề tài đang quản lý"}</small>
                  </div>
                  <span className="role-queue-item__count">{topics.length}</span>
                </Link>
                <Link className="role-queue-item" to="/theses">
                  <div>
                    <strong>Khóa luận trong phạm vi</strong>
                    <small>Theo dõi đề cương, tiến độ, nhận xét</small>
                  </div>
                  <span className="role-queue-item__count">{theses.length}</span>
                </Link>
              </div>
            </>
          )}
        </section>
      )}

      {workflowAccess && loading ? (
        <div className="workspace-records" role="status" aria-label="Đang cập nhật công việc">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : null}

      {workflowAccess && !loading && isStudent ? (
        <div className="workspace-records workspace-records--student">
          <div className="stack">
            <section className="card overview-card">
              <div className="card-body stack">
                <div className="workspace-panel-heading">
                  <h2>
                    <UsersRound size={17} aria-hidden="true" />
                    Đăng ký gần đây
                  </h2>
                  <Link to="/registrations">
                    Tất cả hồ sơ <ArrowRight size={13} aria-hidden="true" />
                  </Link>
                </div>
                {registrations.length ? (
                  <ul className="overview-list">
                    {registrations.map((row) => (
                      <li key={row.id}>
                        <span>
                          <span className="topic-code">{row.topic_code}</span>
                          {row.topic_title}
                        </span>
                        <ThesisStatusBadge state={row.state} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState
                    compact
                    icon={<ClipboardList size={22} aria-hidden="true" />}
                    title="Chưa có hồ sơ đăng ký"
                    description="Chọn một đề tài phù hợp để bắt đầu gửi đăng ký thực hiện."
                  >
                    <Link className="btn btn-soft btn-sm" to="/topics">
                      Chọn đề tài
                    </Link>
                  </EmptyState>
                )}
              </div>
            </section>

            <section className="card overview-card">
              <div className="card-body stack">
                <div className="workspace-panel-heading">
                  <h2>
                    <Lightbulb size={17} aria-hidden="true" />
                    Đề tài đã duyệt
                  </h2>
                  <Link to="/topics">
                    Tất cả đề tài <ArrowRight size={13} aria-hidden="true" />
                  </Link>
                </div>
                {topics.length ? (
                  <ul className="overview-list">
                    {topics.map((topic) => (
                      <li key={topic.id}>
                        <span>
                          <span className="topic-code">{topic.code}</span>
                          {topic.title}
                        </span>
                        <ThesisStatusBadge state={topic.state} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState
                    compact
                    icon={<BookOpen size={22} aria-hidden="true" />}
                    title="Chưa có đề tài"
                    description="Khám phá hoặc đề xuất đề tài phù hợp chuyên ngành."
                  >
                    <Link className="btn btn-soft btn-sm" to="/topics">
                      Mở danh sách đề tài
                    </Link>
                  </EmptyState>
                )}
              </div>
            </section>
          </div>

          <aside className="card overview-card overview-contextual" aria-label="Lối tắt học vụ và tra cứu">
            <div className="card-body stack">
              <div className="workspace-panel-heading">
                <h2>
                  <Compass size={17} aria-hidden="true" />
                  Không gian &amp; tra cứu nhanh
                </h2>
              </div>
              <ul className="contextual-links-list">
                {activeThesis ? (
                  <>
                    {activeThesis.state === "DEFENDED" ? (
                      <li>
                        <Link className="contextual-link-row" to={`/repository?mode=work&focus=${activeThesis.id}`}>
                          <span className="contextual-link-row__main"><BookOpen size={15} aria-hidden="true" />Nộp lưu bản chỉnh sửa sau bảo vệ</span>
                          <ArrowRight size={14} aria-hidden="true" />
                        </Link>
                      </li>
                    ) : null}
                    {activeThesis.state !== "DEFENDED" && activeThesis.state !== "COMPLETED" ? (
                      <>
                        <li>
                          <Link className="contextual-link-row" to={`/theses/${activeThesis.id}?section=submissions`}>
                            <span className="contextual-link-row__main"><FolderOpen size={15} aria-hidden="true" />Hồ sơ nộp &amp; xét duyệt</span>
                            <ArrowRight size={14} aria-hidden="true" />
                          </Link>
                        </li>
                        <li>
                          <Link className="contextual-link-row" to={`/theses/${activeThesis.id}?section=progress`}>
                            <span className="contextual-link-row__main"><ListChecks size={15} aria-hidden="true" />Cập nhật báo cáo tiến độ</span>
                            <ArrowRight size={14} aria-hidden="true" />
                          </Link>
                        </li>
                      </>
                    ) : null}
                    <li>
                      <Link className="contextual-link-row" to="/defense">
                        <span className="contextual-link-row__main"><CalendarDays size={15} aria-hidden="true" />Hội đồng và lịch bảo vệ</span>
                        <ArrowRight size={14} aria-hidden="true" />
                      </Link>
                    </li>
                  </>
                ) : (
                  <>
                    <li>
                      <Link className="contextual-link-row" to="/topics">
                        <span className="contextual-link-row__main"><Lightbulb size={15} aria-hidden="true" />Khám phá &amp; chọn đề tài</span>
                        <ArrowRight size={14} aria-hidden="true" />
                      </Link>
                    </li>
                    <li>
                      <Link className="contextual-link-row" to="/registrations">
                        <span className="contextual-link-row__main"><ClipboardList size={15} aria-hidden="true" />Theo dõi hồ sơ đăng ký</span>
                        <ArrowRight size={14} aria-hidden="true" />
                      </Link>
                    </li>
                  </>
                )}
                <li>
                  <Link className="contextual-link-row" to="/forms">
                    <span className="contextual-link-row__main"><FolderOpen size={15} aria-hidden="true" />Tài liệu &amp; biểu mẫu Khoa</span>
                    <ArrowRight size={14} aria-hidden="true" />
                  </Link>
                </li>
              </ul>

              <div className="contextual-ai-callout">
                <div className="contextual-ai-callout__head">
                  <Bot size={16} aria-hidden="true" />
                  <span>Trợ lý tra cứu AI</span>
                </div>
                <p>Hỏi đáp quy chế KLTN, đối chiếu đề tài tương đồng và kiểm tra tham chiếu học vụ.</p>
                <Link className="btn btn-primary btn-sm" to="/ai">
                  Mở Tra cứu AI
                  <ArrowRight size={14} aria-hidden="true" />
                </Link>
              </div>
            </div>
          </aside>
        </div>
      ) : workflowAccess && !loading ? (
        <div className="workspace-records">
          <section className="card overview-card">
            <div className="card-body stack">
              <div className="workspace-panel-heading">
                <h2>
                  <Lightbulb size={17} aria-hidden="true" />
                  {head ? "Đề tài chờ duyệt" : isStudent ? "Đề tài đã duyệt" : "Đề tài của tôi"}
                </h2>
                <Link to="/topics">
                  Tất cả đề tài <ArrowRight size={13} aria-hidden="true" />
                </Link>
              </div>
              {topics.length ? (
                <ul className="overview-list">
                  {topics.map((topic) => (
                    <li key={topic.id}>
                      <span>
                        <span className="topic-code">{topic.code}</span>
                        {topic.title}
                      </span>
                      <ThesisStatusBadge state={topic.state} />
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState
                  compact
                  icon={<BookOpen size={22} aria-hidden="true" />}
                  title={head ? "Không có đề tài chờ duyệt" : "Chưa có đề tài"}
                  description={head ? "Các đề tài mới do giảng viên hoặc sinh viên đề xuất sẽ hiển thị tại đây." : "Khám phá hoặc đề xuất đề tài phù hợp chuyên ngành."}
                >
                  <Link className="btn btn-soft btn-sm" to="/topics">
                    Mở danh sách đề tài
                  </Link>
                </EmptyState>
              )}
            </div>
          </section>

          <section className="card overview-card">
            <div className="card-body stack">
              <div className="workspace-panel-heading">
                <h2>
                  <UsersRound size={17} aria-hidden="true" />
                  {context.base_role === "LECTURER" ? (
                    <>
                      Hồ sơ cần xử lý <span className="overview-count">{pendingCount}</span>
                    </>
                  ) : (
                    "Đăng ký gần đây"
                  )}
                </h2>
                <Link to="/registrations">
                  Tất cả hồ sơ <ArrowRight size={13} aria-hidden="true" />
                </Link>
              </div>
              {registrations.length ? (
                <ul className="overview-list">
                  {registrations.map((row) => (
                    <li key={row.id}>
                      {context.base_role === "LECTURER" ? (
                        <Link to={"/registrations?focus=" + row.id}>
                          <span className="topic-code">{row.topic_code}</span>
                          {row.topic_title}
                        </Link>
                      ) : (
                        <span>
                          <span className="topic-code">{row.topic_code}</span>
                          {row.topic_title}
                        </span>
                      )}
                      <ThesisStatusBadge state={row.state} />
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState
                  compact
                  icon={<ClipboardList size={22} aria-hidden="true" />}
                  title={context.base_role === "LECTURER" ? "Không có hồ sơ cần xử lý" : "Chưa có hồ sơ đăng ký"}
                  description={context.base_role === "LECTURER" ? "Khi sinh viên gửi hồ sơ đăng ký mới, thông báo sẽ hiện ở đây." : "Chọn một đề tài để bắt đầu gửi đăng ký thực hiện."}
                >
                  <Link className="btn btn-soft btn-sm" to={isStudent ? "/topics" : "/registrations"}>
                    {isStudent ? "Chọn đề tài" : "Xem tất cả hồ sơ"}
                  </Link>
                </EmptyState>
              )}
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}
