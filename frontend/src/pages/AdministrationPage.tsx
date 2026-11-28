import AssignmentTabs from "../components/layout/AssignmentTabs";
import LecturerActivationPicker from "../components/domain/LecturerActivationPicker";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Context } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";
import EmptyState from "../components/ui/EmptyState";
import { type FilterChip } from "../components/ui/FilterBar";

import {
  AlertTriangle,
  Ban,
  BookOpen,
  Briefcase,
  Calendar,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  GraduationCap,
  Info,
  Lock,
  Mail,
  RotateCcw,
  Search,
  Send,
  Shield,
  Unlock,
  UserCog,
  UserPlus,
  Users,
  X,
} from "lucide-react";

type Department = { id: string; code: string; name: string; major_code: string | null };
type Round = { id: string; code: string; state: string };
type AccountRole = { code: string; label: string; scope: string | null };
type Account = { id: string; email: string; base_role: string; status: string; verified: boolean; student_code: string | null; display_name?: string | null; lecturer_code?: string | null; additional_roles?: AccountRole[] };
type AccountDirectory = {
  items: Account[];
  total: number;
  counts: Record<string, number>;
  role_catalog: { code: string; label: string; count: number }[];
};
type Assignment = { id: string; round_id: string; round_code: string; user_id: string; email: string; assignment_type: string };

type AdministrationSection = "accounts" | "assignments";

export default function AdministrationPage({
  context,
  onPermissionsChanged,
  section = "accounts",
}: {
  context: Context;
  onPermissionsChanged: () => Promise<void>;
  section?: AdministrationSection;
}) {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountCategory, setAccountCategory] = useState("ALL");
  const [additionalRole, setAdditionalRole] = useState("");
  const [accountStatus, setAccountStatus] = useState("ALL");
  const [directoryCounts, setDirectoryCounts] = useState<Record<string, number>>({});
  const [roleCatalog, setRoleCatalog] = useState<AccountDirectory["role_catalog"]>([]);
  const [staffAccounts, setStaffAccounts] = useState<Account[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [lecturerInviteMode, setLecturerInviteMode] = useState<"new" | "existing">("new");
  const [lecturerCode, setLecturerCode] = useState("");
  const [lecturerName, setLecturerName] = useState("");
  const [lecturerEmail, setLecturerEmail] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [roundId, setRoundId] = useState("");
  const [userId, setUserId] = useState("");
  const [staffSearch, setStaffSearch] = useState("");
  const [kind, setKind] = useState("");
  const [basis, setBasis] = useState("");
  const [search, setSearch] = useState("");
  const [reason, setReason] = useState("");
  const [emailReason, setEmailReason] = useState("");
  const [assignmentHint, setAssignmentHint] = useState("");
  const [selectedAccount, setSelectedAccount] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [emailRoundId, setEmailRoundId] = useState("");
  const [officialRef, setOfficialRef] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [lecturerRevision, setLecturerRevision] = useState(0);
  const [term, setTerm] = useState("");
  const [page, setPage] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const isAdmin = context.base_role === "ADMIN";

  const assignmentDescriptions: Record<string, string> = {
    REVIEW_RECORDS_MANAGER: "Theo dõi nhận xét Mẫu 7/8 đã gửi trong Phản biện & điều kiện bảo vệ, đối chiếu đúng sinh viên và bản báo cáo. GV xác nhận nội dung trên tài khoản của mình; TBM xét điều kiện dự bảo vệ.",
    FORM_MANAGER: "Mở Quản lý kho biểu mẫu Khoa để thêm bản mới, phát hành hoặc thu hồi biểu mẫu và tài liệu của đợt được giao.",
    ELIGIBILITY_IMPORTER:
      "Mở Danh sách sinh viên, nhập danh sách được Khoa duyệt để xác nhận đủ điều kiện đăng ký KLTN. Sinh viên kích hoạt tài khoản trước khi gửi đăng ký.",
    ELIGIBILITY_VERIFIER:
      "Mở Danh sách sinh viên để đính chính hoặc thu hồi điều kiện đăng ký đã ghi nhận. Quyền xét dự bảo vệ của TBM nằm trong hồ sơ phản biện.",
    ACCOUNT_MANAGER:
      "Mở Tài khoản để khóa, mở hoặc hỗ trợ kích hoạt tài khoản sinh viên thuộc đợt được giao.",
    KLTN_COORDINATOR:
      "Mở, gia hạn và đóng mốc tiến độ và hạn nhận tài liệu chung, xử lý hồ sơ xin thôi, điều phối hội đồng và lịch bảo vệ trong phạm vi được giao. Mở Mốc & báo cáo tiến độ, Hồ sơ nộp & xét duyệt hoặc Hội đồng và bảo vệ.",
  };

  const eligibleStaff = (a: Account, task: string) =>
    a.status === "ACTIVE" &&
    (task === "KLTN_COORDINATOR" || task === "ACCOUNT_MANAGER" || task === "REVIEW_RECORDS_MANAGER" ? a.base_role === "LECTURER" : a.base_role !== "STUDENT");

  function changeKind(next: string) {
    setKind(next);
    if (rounds.find(r => r.id === roundId)?.state === "CLOSED" && !["FORM_MANAGER","REVIEW_RECORDS_MANAGER","KLTN_COORDINATOR"].includes(next)) {setRoundId("");setAssignmentHint("Chọn đợt còn nhận phân công cho nhiệm vụ này.");}
    if (userId && !staffAccounts.some((a) => a.id === userId && eligibleStaff(a, next))) {
      setUserId("");
      setAssignmentHint("Người đã chọn không phù hợp nhiệm vụ mới. Vui lòng chọn lại người được giao.");
    } else {
      setAssignmentHint("");
    }
  }

  const foldStaffSearch = (value: string) =>
    value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[đĐ]/g, "d").toLowerCase().replace(/\s+/g, " ").trim();
  const staffQuery = foldStaffSearch(staffSearch);
  const matchingStaff = staffAccounts.filter((account) =>
    eligibleStaff(account, kind) &&
    foldStaffSearch([account.lecturer_code, account.display_name, account.email].filter(Boolean).join(" ")).includes(staffQuery),
  );
  const selectedStaff = matchingStaff.find((account) => account.id === userId);
  useEffect(() => {
    if (userId && !staffAccounts.some((account) => account.id === userId && eligibleStaff(account, kind))) {
      setUserId("");
    }
  }, [staffAccounts, userId, kind]);

  const PAGE_SIZE = 20;
  const refresh = useCallback(
    async (q: string, atPage: number) => {
      setBusy(true);
      try {
        const accountUrl = isAdmin
          ? "/admin/users/directory?search=" + encodeURIComponent(q)
            + "&category=" + encodeURIComponent(accountCategory)
            + "&additional_role=" + encodeURIComponent(additionalRole)
            + "&account_status=" + encodeURIComponent(accountStatus)
            + "&offset=" + atPage * PAGE_SIZE + "&limit=" + PAGE_SIZE
          : "/admin/users?search=" + encodeURIComponent(q)
            + "&account_status=" + encodeURIComponent(accountStatus)
            + "&offset=" + atPage * PAGE_SIZE + "&limit=" + PAGE_SIZE;
        const [d, r, usersResult, staff, a] = await Promise.all([
          isAdmin ? request<Department[]>("/admin/departments", context.user_id) : Promise.resolve([]),
          isAdmin
            ? request<Round[]>("/admin/rounds", context.user_id)
            : request<{ round_id: string; round_code: string; assignment_type: string }[]>("/me/round-assignments", context.user_id).then((rows) =>
                rows
                  .filter((row) => row.assignment_type === "ACCOUNT_MANAGER")
                  .map((row) => ({ id: row.round_id, code: row.round_code, state: "OPEN" })),
              ),
          isAdmin
            ? request<AccountDirectory>(accountUrl, context.user_id)
            : request<Account[]>(accountUrl, context.user_id),
          isAdmin ? request<Account[]>("/admin/staff", context.user_id) : Promise.resolve<Account[]>([]),
          isAdmin ? request<Assignment[]>("/admin/round-assignments", context.user_id) : Promise.resolve([]),
        ]);
        const directory = Array.isArray(usersResult) ? null : usersResult as AccountDirectory;
        const u = directory ? directory.items : usersResult as Account[];
        setDepartments(d);
        setRounds(r);
        setAccounts(u);
        setDirectoryCounts(directory?.counts ?? {});
        setRoleCatalog(directory?.role_catalog ?? []);
        setStaffAccounts(staff);
        setAssignments(a);
        setHasNext(directory ? directory.total > (atPage + 1) * PAGE_SIZE : u.length === PAGE_SIZE);
      } finally {
        setBusy(false);
      }
    },
    [accountCategory, additionalRole, accountStatus, context.user_id, isAdmin, PAGE_SIZE],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = search.trim();
      if (next !== term) {
        setTerm(next);
        setPage(0);
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search, term]);

  useEffect(() => {
    void refresh(term, page).catch((cause) => setError(errorMessage(cause)));
  }, [refresh, term, page]);

  const accountById = useCallback(
    (id: string) => accounts.find((a) => a.id === id) ?? staffAccounts.find((a) => a.id === id),
    [accounts, staffAccounts],
  );

  async function run(action: () => Promise<unknown>, message: string, permissionsChanged = false) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await action();
      setLecturerRevision(value => value + 1);
      await refresh(search.trim() || term, page);
      if (permissionsChanged) await onPermissionsChanged();
      setNotice(typeof result === "string" ? result : message);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  // Statistics for quick glance (global totals when directory counts available)
  const hasDirectoryTotals = isAdmin && directoryCounts.ALL !== undefined;
  const totalAccounts = directoryCounts.ALL ?? accounts.length;
  const studentCount = directoryCounts.STUDENT ?? accounts.filter((a) => a.base_role === "STUDENT").length;
  const lecturerCount = directoryCounts.LECTURER ?? accounts.filter((a) => a.base_role === "LECTURER").length;
  const unverifiedCount = accounts.filter((a) => !a.verified).length;
  const lockedOrDisabledCount = accounts.filter((a) => a.status === "LOCKED" || (a.status === "DISABLED" && a.verified)).length;

  return (
    <div className="admin-page">
      <PageHeader
        title={section === "accounts" ? (isAdmin ? "Quản lý tài khoản" : "Tài khoản sinh viên theo đợt") : "Phân công theo đợt"}
        description={section === "accounts"
          ? "Tìm kiếm tài khoản, theo dõi trạng thái và hỗ trợ truy cập."
          : "Giao hoặc thu hồi nhiệm vụ KLTN theo từng đợt."}
      />

      {section === "assignments" && isAdmin && <AssignmentTabs />}
      <div className="stack">
        {isAdmin && <nav className="admin-page__quick-links" aria-label="Lối tắt quản trị">
          {section === "accounts" && <>
            <Link className="btn btn-secondary" to="/lecturers">Danh sách giảng viên · Nhập Excel</Link>
            <Link className="btn btn-secondary" to="/rounds">Quản lý đợt KLTN</Link>
          </>}
          {section === "assignments" && <>
            <Link className="btn btn-secondary" to="/forms">Kho biểu mẫu và tài liệu Khoa</Link>
          </>}
        </nav>}
        {error ? (
          <p role="alert" className="alert alert-danger alert-icon-row">
            <AlertTriangle size={18} aria-hidden="true" /> {error}
          </p>
        ) : null}
        {notice ? (
          <p role="status" className="alert alert-success alert-icon-row">
            <CheckCircle2 size={18} aria-hidden="true" /> {notice}
          </p>
        ) : null}

        {isAdmin && (
          <div className="admin-grid-top admin-grid-top--single">
            {/* CARD 1: MỜI GIẢNG VIÊN */}
            {section === "accounts" && (<section className="card admin-card">
              <div className="admin-card__header">
                <div className="admin-card__title-group">
                  <div className="admin-card__icon">
                    <UserPlus size={18} aria-hidden="true" />
                  </div>
                  <div>
                    <h2 className="admin-card__title">Mời giảng viên</h2>
                    <p className="admin-card__subtitle">Tạo tài khoản và gửi liên kết kích hoạt qua email</p>
                  </div>
                </div>
                <span className="admin-card__counter">Giảng viên mới</span>
              </div>
              <div className="card-body stack">
                <div className="lecturer-invite-tabs" role="group" aria-label="Cách mời giảng viên">
                  <button type="button" className={`btn ${lecturerInviteMode === "new" ? "btn-primary" : "btn-secondary"}`} aria-pressed={lecturerInviteMode === "new"} onClick={() => setLecturerInviteMode("new")}>Tạo giảng viên mới</button>
                  <button type="button" className={`btn ${lecturerInviteMode === "existing" ? "btn-primary" : "btn-secondary"}`} aria-pressed={lecturerInviteMode === "existing"} onClick={() => setLecturerInviteMode("existing")}>Gửi liên kết cho GV đã có</button>
                </div>
                {lecturerInviteMode === "existing" ? <LecturerActivationPicker userId={context.user_id} /> : <form
                  className="stack"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void run(async () => {
                      const result = await request<{ invitation_sent: boolean }>("/admin/lecturers", context.user_id, {
                        method: "POST",
                        body: JSON.stringify({
                          lecturer_code: lecturerCode,
                          display_name: lecturerName,
                          email: lecturerEmail,
                          department_id: departmentId,
                        }),
                      });
                      return result.invitation_sent
                        ? "Đã tạo tài khoản và gửi liên kết kích hoạt."
                        : "Đã tạo tài khoản nhưng chưa gửi được email; giảng viên có thể yêu cầu lại liên kết kích hoạt.";
                    }, "Đã tạo tài khoản.");
                  }}
                >
                  <div className="grid grid-cols-2">
                    <label className="input-group">
                      Mã giảng viên
                      <input
                        className="input"
                        required
                        placeholder="VD: GV001"
                        value={lecturerCode}
                        onChange={(e) => setLecturerCode(e.target.value)}
                      />
                    </label>
                    <label className="input-group">
                      Bộ môn
                      <select className="input" required value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
                        <option value="">Chọn bộ môn trực thuộc</option>
                        {departments.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.code} · {d.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <div className="grid grid-cols-2">
                    <label className="input-group">
                      Họ tên
                      <input
                        className="input"
                        required
                        placeholder="VD: TS. Nguyễn Văn A"
                        value={lecturerName}
                        onChange={(e) => setLecturerName(e.target.value)}
                      />
                    </label>
                    <label className="input-group">
                      Email
                      <input
                        className="input"
                        type="email"
                        required
                        placeholder="email@truong.edu.vn"
                        value={lecturerEmail}
                        onChange={(e) => setLecturerEmail(e.target.value)}
                      />
                    </label>
                  </div>
                  <div className="admin-callout admin-callout--neutral">
                    <Info size={15} aria-hidden="true" />
                    <span>Hệ thống tạo tài khoản cơ sở và gửi liên kết kích hoạt đến hộp thư công vụ.</span>
                  </div>
                  <button className="btn btn-primary" disabled={busy}>
                    <UserPlus size={16} aria-hidden="true" /> Tạo và gửi lời mời
                  </button>
                </form>}
              </div>
            </section>)}

            {/* CARD 2: PHÂN CÔNG THEO ĐỢT */}
            {section === "assignments" && (<section className="card admin-card">
              <div className="admin-card__header">
                <div className="admin-card__title-group">
                  <div className="admin-card__icon admin-card__icon--info">
                    <Shield size={18} aria-hidden="true" />
                  </div>
                  <div>
                    <h2 className="admin-card__title">Giao nhiệm vụ theo đợt</h2>
                    <p className="admin-card__subtitle">Gán trách nhiệm quản trị đợt khóa luận cho cán bộ/GV</p>
                  </div>
                </div>
                <span className="admin-card__counter">Nhiệm vụ đợt</span>
              </div>
              <div className="card-body stack">
                <form
                  className="stack"
                  onInvalidCapture={() =>
                    setAssignmentHint("Vui lòng chọn đợt, nhiệm vụ, người được giao và nhập căn cứ phân công ít nhất 3 ký tự.")
                  }
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!selectedStaff) {
                      setAssignmentHint("Hãy chọn email của người được giao trong danh sách phù hợp.");
                      return;
                    }
                    setAssignmentHint("");
                    void run(
                      () =>
                        request("/admin/round-assignments", context.user_id, {
                          method: "POST",
                          body: JSON.stringify({
                            round_id: roundId,
                            user_id: selectedStaff.id,
                            assignment_type: kind,
                            basis_ref: basis,
                          }),
                        }),
                      "Đã lưu phân công.",
                      true,
                    );
                  }}
                >
                  <label className="input-group">
                    Đợt
                    <select className="input" required value={roundId} onChange={(e) => setRoundId(e.target.value)}>
                      <option value="">Chọn đợt khóa luận áp dụng</option>
                      {rounds
                        .filter((r) => r.state === "DRAFT" || r.state === "OPEN" || (["FORM_MANAGER","REVIEW_RECORDS_MANAGER","KLTN_COORDINATOR"].includes(kind) && r.state === "CLOSED"))
                        .map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.code} · {r.state}
                          </option>
                        ))}
                    </select>
                  </label>
                  <div className="input-group">
                    <span id="assignment-person-label">Người được giao</span>
                    <div className="roster-student-picker__controls staff-picker" role="group" aria-labelledby="assignment-person-label">
                      <input
                        className="input"
                        aria-label="Tìm người được giao theo mã hoặc tên"
                        placeholder="Mã hoặc tên GV"
                        maxLength={100}
                        value={staffSearch}
                        disabled={busy}
                        onChange={(e) => {
                          setStaffSearch(e.target.value);
                          setUserId("");
                          setAssignmentHint("");
                        }}
                      />
                      <select
                        className="input"
                        aria-label="Người được giao"
                        required
                        value={userId}
                        disabled={busy || !matchingStaff.length}
                        aria-describedby={assignmentHint ? "assignment-hint" : undefined}
                        onChange={(e) => {
                          setUserId(e.target.value);
                          setAssignmentHint("");
                        }}
                      >
                        <option value="">{matchingStaff.length ? "Chọn email phù hợp" : "Không có tài khoản phù hợp"}</option>
                        {matchingStaff.map((account) => (
                          <option key={account.id} value={account.id}>
                            {account.email || "Chưa có email"}{account.lecturer_code ? " · " + account.lecturer_code : ""}{account.display_name && account.display_name !== account.email ? " · " + account.display_name : ""}
                          </option>
                        ))}
                      </select>
                    </div>
                    <span className="text-caption">{matchingStaff.length} tài khoản phù hợp. Tìm bằng mã/tên, rồi chọn email bên phải.</span>
                    {selectedStaff ? <p role="status" className="text-caption text-primary-800">Đã chọn: {selectedStaff.display_name || selectedStaff.email}{selectedStaff.lecturer_code ? " · " + selectedStaff.lecturer_code : ""} · {selectedStaff.email}.</p> : null}
                  </div>
                  <div className="assignment-details-grid">
                  <label className="input-group">
                    Nhiệm vụ
                    <select className="input" required value={kind} onChange={(e) => changeKind(e.target.value)}>
                      <option value="">Chọn nhiệm vụ</option>
                      <option value="ELIGIBILITY_IMPORTER">Nhập danh sách SV</option>
                      <option value="ELIGIBILITY_VERIFIER">Điều chỉnh/thu hồi điều kiện</option>
                      <option value="ACCOUNT_MANAGER">Quản lý tài khoản SV theo đợt</option>
                      <option value="KLTN_COORDINATOR">Điều phối KLTN theo đợt</option>
                      <option value="REVIEW_RECORDS_MANAGER">Tiếp nhận hồ sơ phản biện (cán bộ/thư ký)</option>
                      <option value="FORM_MANAGER">Quản lý biểu mẫu và tài liệu Khoa</option>
                    </select>
                  </label>
                  <label className="input-group">
                    Căn cứ phân công
                    <input
                      className="input"
                      required
                      minLength={3}
                      value={basis}
                      onChange={(e) => setBasis(e.target.value)}
                      placeholder="Số văn bản hoặc quyết định của Khoa"
                    />
                  </label>
                  </div>
                  {assignmentDescriptions[kind] ? (
                    <div className="admin-callout" role="status" aria-live="polite">
                      <Info size={16} aria-hidden="true" />
                      <span>{assignmentDescriptions[kind]}</span>
                    </div>
                  ) : null}
                  {assignmentHint ? (
                    <p id="assignment-hint" role="status" className="text-caption text-muted">
                      {assignmentHint}
                    </p>
                  ) : null}
                  <button className="btn btn-primary" disabled={busy || !kind || !selectedStaff}>
                    <Shield size={16} aria-hidden="true" /> Lưu phân công
                  </button>
                </form>
              </div>
            </section>)}
          </div>
        )}

        {/* CARD 3: PHÂN CÔNG ĐANG HIỆU LỰC */}
        {section === "assignments" && isAdmin && (
          <section className="card admin-card">
            <div className="admin-card__header">
              <div className="admin-card__title-group">
                <div className="admin-card__icon">
                  <Briefcase size={18} aria-hidden="true" />
                </div>
                <div>
                  <h2 className="admin-card__title">Phân công đang hiệu lực</h2>
                  <p className="admin-card__subtitle">Các quyền hạn bổ nhiệm đang hoạt động trong các đợt khóa luận</p>
                </div>
              </div>
              <span className="admin-card__counter">{assignments.length} phân công</span>
            </div>
            <div className="card-body stack">
              <div className="admin-revoke-bar">
                <label className="input-group">
                  <span className="admin-reason-label">
                    <Shield size={14} aria-hidden="true" className="admin-shield-icon" />
                    <span>Lý do thu hồi (nếu cần)</span>
                    <small className="text-muted">(yêu cầu tối thiểu 5 ký tự để kích hoạt nút Thu hồi)</small>
                  </span>
                  <input
                    className="input"
                    minLength={5}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Nhập lý do thu hồi nhiệm vụ..."
                  />
                </label>
                <div
                  className={`admin-reason-status ${
                    reason.trim().length >= 5 ? "admin-reason-status--valid" : "admin-reason-status--hint"
                  }`}
                >
                  {reason.trim().length >= 5 ? (
                    <>
                      <CheckCircle2 size={13} aria-hidden="true" /> Đã đủ điều kiện thu hồi ({reason.trim().length} ký tự)
                    </>
                  ) : (
                    <>
                      <Info size={13} aria-hidden="true" /> Cần tối thiểu 5 ký tự để thu hồi ({reason.trim().length}/5)
                    </>
                  )}
                </div>
              </div>

              <div className="account-list assignment-list">
                {assignments.map((a) => {
                  const dutyClass =
                    a.assignment_type === "KLTN_COORDINATOR"
                      ? "assignment-item__duty--coordinator"
                      : a.assignment_type === "ELIGIBILITY_VERIFIER"
                      ? "assignment-item__duty--verifier"
                      : a.assignment_type === "ACCOUNT_MANAGER"
                      ? "assignment-item__duty--manager"
                      : "assignment-item__duty--importer";

                  return (
                    <div className="account-list__row assignment-item" key={a.id}>
                      <div className="assignment-item__info">
                        <span className="assignment-item__round">
                          <Calendar size={13} aria-hidden="true" /> {a.round_code}
                        </span>
                        <span className="assignment-item__email">
                          <Mail size={13} aria-hidden="true" className="admin-mail-icon" />
                          {a.email}
                        </span>
                        <span className={`badge ${dutyClass} assignment-item__duty`}>
                          <Briefcase size={12} aria-hidden="true" />
                          {a.assignment_type === "REVIEW_RECORDS_MANAGER" ? "Tiếp nhận hồ sơ phản biện" : a.assignment_type === "FORM_MANAGER" ? "Quản lý biểu mẫu và tài liệu Khoa" : a.assignment_type === "ELIGIBILITY_VERIFIER"
                            ? "Điều chỉnh/thu hồi điều kiện"
                            : a.assignment_type === "ACCOUNT_MANAGER"
                            ? "Quản lý tài khoản SV"
                            : a.assignment_type === "KLTN_COORDINATOR"
                            ? "Điều phối KLTN theo đợt"
                            : "Nhập danh sách SV"}
                        </span>
                      </div>
                      <button
                        className="btn btn-secondary btn-sm admin-btn-danger-hover"
                        disabled={busy || reason.trim().length < 5}
                        title={reason.trim().length < 5 ? "Cần nhập lý do thu hồi (ít nhất 5 ký tự)" : ""}
                        onClick={() =>
                          void run(
                            () =>
                              request(`/admin/round-assignments/${a.id}/revoke`, context.user_id, {
                                method: "POST",
                                body: JSON.stringify({ reason }),
                              }),
                            "Đã thu hồi phân công.",
                            true,
                          )
                        }
                      >
                        Thu hồi
                      </button>
                    </div>
                  );
                })}
                {!assignments.length ? (
                  <div className="admin-empty-state">
                    <Briefcase size={28} aria-hidden="true" />
                    <p>Chưa có phân công nào đang hiệu lực.</p>
                  </div>
                ) : null}
              </div>
            </div>
          </section>
        )}

        {/* CARD 4: DANH SÁCH TÀI KHOẢN */}
        {section === "accounts" && (<section className="card admin-card">
          <div className="admin-card__header">
            <div className="admin-card__title-group">
              <div className="admin-card__icon">
                <Users size={18} aria-hidden="true" />
              </div>
              <div>
                <h2 className="admin-card__title">Tài khoản</h2>
                <p className="admin-card__subtitle">Quản lý trạng thái, cấp lại mật khẩu/liên kết và hiệu chỉnh email</p>
              </div>
            </div>
            <span className="admin-card__counter">{directoryCounts.ALL ?? accounts.length} tài khoản</span>
          </div>

          <div className="card-body stack">
            {/* Overview Metric Bar */}
            <div className="admin-metrics" role="region" aria-label="Thống kê tài khoản trang hiện tại" tabIndex={0}>
              <div className="admin-metric-card">
                <div className="admin-metric-card__icon-box">
                  <Users size={18} aria-hidden="true" />
                </div>
                <div className="admin-metric-card__content">
                  <span className="admin-metric-card__label">{hasDirectoryTotals ? "Tổng tài khoản" : "Tổng trên trang"}</span>
                  <span className="admin-metric-card__value">{totalAccounts}</span>
                </div>
              </div>
              <div className="admin-metric-card admin-metric-card--student">
                <div className="admin-metric-card__icon-box">
                  <GraduationCap size={18} aria-hidden="true" />
                </div>
                <div className="admin-metric-card__content">
                  <span className="admin-metric-card__label">{hasDirectoryTotals ? "Sinh viên" : "SV trên trang"}</span>
                  <span className="admin-metric-card__value">{studentCount}</span>
                </div>
              </div>
              <div className="admin-metric-card admin-metric-card--lecturer">
                <div className="admin-metric-card__icon-box">
                  <BookOpen size={18} aria-hidden="true" />
                </div>
                <div className="admin-metric-card__content">
                  <span className="admin-metric-card__label">{hasDirectoryTotals ? "Giảng viên" : "GV trên trang"}</span>
                  <span className="admin-metric-card__value">{lecturerCount}</span>
                </div>
              </div>
              <div className="admin-metric-card admin-metric-card--warning">
                <div className="admin-metric-card__icon-box">
                  <Clock size={18} aria-hidden="true" />
                </div>
                <div className="admin-metric-card__content">
                  <span className="admin-metric-card__label">Chưa kích hoạt trên trang</span>
                  <span className="admin-metric-card__value">{unverifiedCount}</span>
                </div>
              </div>
              {lockedOrDisabledCount > 0 && (
                <div className="admin-metric-card admin-metric-card--danger">
                  <div className="admin-metric-card__icon-box">
                    <Lock size={18} aria-hidden="true" />
                  </div>
                  <div className="admin-metric-card__content">
                    <span className="admin-metric-card__label">Khóa / Vô hiệu trên trang</span>
                    <span className="admin-metric-card__value text-danger-val">
                      {lockedOrDisabledCount}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {isAdmin ? (
              <div className="account-category-tabs" role="tablist" aria-label="Lọc tài khoản theo vai trò">
                {[
                  { code: "ALL", label: "Tất cả", count: directoryCounts.ALL ?? 0 },
                  { code: "STUDENT", label: "Sinh viên", count: directoryCounts.STUDENT ?? 0 },
                  { code: "LECTURER", label: "Giảng viên", count: directoryCounts.LECTURER ?? 0 },
                  { code: "ADMIN", label: "Quản trị", count: directoryCounts.ADMIN ?? 0 },
                  { code: "LECTURER_WITH_DUTIES", label: "Giảng viên có quyền bổ sung", count: directoryCounts.LECTURER_WITH_DUTIES ?? 0 },
                ].map((tab) => (
                  <button
                    key={tab.code}
                    type="button"
                    role="tab"
                    aria-selected={accountCategory === tab.code}
                    className={"account-category-tab" + (accountCategory === tab.code ? " account-category-tab--active" : "")}
                    onClick={() => {
                      setAccountCategory(tab.code);
                      setAdditionalRole("");
                      setPage(0);
                    }}
                  >
                    <span>{tab.label}</span><small>{tab.count}</small>
                  </button>
                ))}
              </div>
            ) : null}

            {isAdmin && accountCategory === "LECTURER_WITH_DUTIES" ? (
              <label className="input-group account-role-filter">
                Lọc theo quyền/phân công
                <select
                  className="input"
                  value={additionalRole}
                  onChange={(event) => {
                    setAdditionalRole(event.target.value);
                    setPage(0);
                  }}
                >
                  <option value="">Tất cả quyền bổ sung</option>
                  {roleCatalog.map((role) => (
                    <option key={role.code} value={role.code}>{role.label} ({role.count})</option>
                  ))}
                </select>
              </label>
            ) : null}

            <label className="input-group">Trạng thái tài khoản
              <select className="input" aria-label="Trạng thái tài khoản" value={accountStatus} disabled={busy} onChange={e=>{setAccountStatus(e.target.value);setPage(0);}}>
                <option value="ALL">Tất cả trạng thái</option><option value="PENDING">Chờ kích hoạt</option><option value="ACTIVE">Hoạt động</option><option value="LOCKED">Bị khóa</option><option value="DISABLED">Vô hiệu hóa trước đây</option>
              </select>
            </label>
            {/* Toolbar: Search & Action Reason */}
            <div className="admin-toolbar">
              <div className="admin-toolbar__row">
                <form
                  className="account-search"
                  onSubmit={(e) => {
                    e.preventDefault();
                    setTerm(search.trim());
                    setPage(0);
                  }}
                >
                  <div className="admin-search-wrap">
                    <Search size={16} className="admin-search-wrap__icon" aria-hidden="true" />
                    <input
                      className="input"
                      aria-label="Tìm theo mã, tên hoặc email tài khoản"
                      placeholder="Tìm email, MSSV, mã hoặc tên giảng viên..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                    {search && (
                      <button
                        type="button"
                        className="admin-search-wrap__clear"
                        onClick={() => {
                          setSearch("");
                          setTerm("");
                          setPage(0);
                        }}
                        aria-label="Xóa nội dung tìm kiếm"
                      >
                        <X size={14} aria-hidden="true" />
                      </button>
                    )}
                  </div>
                  <button className="btn btn-secondary">Tìm</button>
                </form>
              </div>
              {(() => {
                const statusLabels: Record<string, string> = {
                  PENDING: "Chờ kích hoạt",
                  ACTIVE: "Hoạt động",
                  LOCKED: "Bị khóa",
                  DISABLED: "Vô hiệu hóa trước đây",
                };
                const chips: FilterChip[] = [
                  ...(term ? [{ key: "term", label: `Từ khóa: "${term}"`, onRemove: () => { setSearch(""); setTerm(""); setPage(0); } }] : []),
                  ...(accountStatus !== "ALL" ? [{ key: "status", label: `Trạng thái: ${statusLabels[accountStatus] || accountStatus}`, onRemove: () => { setAccountStatus("ALL"); setPage(0); } }] : []),
                  ...(additionalRole ? [{ key: "role", label: `Quyền: ${roleCatalog.find((r) => r.code === additionalRole)?.label || additionalRole}`, onRemove: () => { setAdditionalRole(""); setPage(0); } }] : []),
                ];
                if (!chips.length) return null;
                return (
                  <div className="filter-bar__chips" aria-label="Bộ lọc tài khoản đang áp dụng">
                    {chips.map((chip) => (
                      <span className="filter-chip" key={chip.key}>
                        <span>{chip.label}</span>
                        <button type="button" className="filter-chip__remove" aria-label={`Bỏ lọc ${chip.label}`} onClick={chip.onRemove}>
                          <X size={12} aria-hidden="true" />
                        </button>
                      </span>
                    ))}
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => {
                        setSearch("");
                        setTerm("");
                        setAccountStatus("ALL");
                        setAdditionalRole("");
                        setPage(0);
                      }}
                    >
                      Xóa bộ lọc
                    </button>
                  </div>
                );
              })()}

              <div className="admin-reason-field">
                <label className="input-group">
                  <span className="admin-reason-label">
                    <Shield size={14} aria-hidden="true" className="admin-shield-icon" />
                    <span>Lý do thao tác tài khoản</span>
                    <small className="text-muted">(yêu cầu tối thiểu 5 ký tự để Khóa, Mở khóa hoặc Cấp lại)</small>
                  </span>
                  <input
                    className="input"
                    minLength={5}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Nhập lý do thao tác (vd: Tiếp nhận yêu cầu hỗ trợ sinh viên / Căn cứ công văn Khoa...)"
                  />
                </label>
                <div
                  className={`admin-reason-status ${
                    reason.trim().length >= 5 ? "admin-reason-status--valid" : "admin-reason-status--hint"
                  }`}
                >
                  {reason.trim().length >= 5 ? (
                    <>
                      <CheckCircle2 size={13} aria-hidden="true" /> Đã đủ điều kiện thao tác ({reason.trim().length} ký tự)
                    </>
                  ) : (
                    <>
                      <Info size={13} aria-hidden="true" />{" "}
                      {reason.trim().length === 0
                        ? "Chưa nhập lý do thao tác — các nút tác vụ tạm vô hiệu để đảm bảo an toàn"
                        : `Cần thêm ${5 - reason.trim().length} ký tự để kích hoạt các nút tác vụ (${reason.trim().length}/5)`}
                    </>
                  )}
                </div>
              </div>

              <div className="admin-callout admin-callout--neutral">
                <Info size={16} aria-hidden="true" />
                <span>
                  Khóa tài khoản chặn đăng nhập và giữ hồ sơ; có thể mở khóa. Thu hồi điều kiện tham gia từng đợt thực hiện ở Danh sách sinh viên.
                </span>
              </div>
            </div>

            {/* Account List */}
            <div className="account-list">
              {accounts.map((a) => {
                const isSelf = a.id === context.user_id;
                const isStudent = a.base_role === "STUDENT";
                const isLecturer = a.base_role === "LECTURER";
                const roleTitle = isStudent ? "Sinh viên" : isLecturer ? "Giảng viên" : "Quản trị";

                return (
                  <div
                    className={`account-list__row ${isSelf ? "account-list__row--current" : ""}`}
                    key={a.id}
                  >
                    <div className="account-list__info">
                      <div className="account-item">
                        {/* Avatar / Role icon */}
                        <div
                          className={`account-item__avatar ${
                            isStudent
                              ? "account-item__avatar--student"
                              : isLecturer
                              ? "account-item__avatar--lecturer"
                              : "account-item__avatar--admin"
                          }`}
                          aria-hidden="true"
                        >
                          {isStudent ? (
                            <GraduationCap size={18} />
                          ) : isLecturer ? (
                            <BookOpen size={18} />
                          ) : (
                            <UserCog size={18} />
                          )}
                        </div>

                        {/* Details */}
                        <div className="account-item__main">
                          <div className="account-item__header">
                            <span className="account-item__email">{a.email}</span>
                            {a.student_code ? (
                              <span className="account-item__code" title="Mã số sinh viên">
                                <span className="account-item__code-label">MSSV</span>
                                <strong>{a.student_code}</strong>
                              </span>
                            ) : null}
                            {isLecturer && a.lecturer_code ? (
                              <span className="account-item__code" title="Mã giảng viên">
                                <span className="account-item__code-label">Mã GV</span>
                                <strong>{a.lecturer_code}</strong>
                              </span>
                            ) : null}
                            {a.display_name ? (
                              <span className="account-item__display-name">{a.display_name}</span>
                            ) : null}
                          </div>

                          <div className="account-item__meta">
                            {/* Role Badge */}
                            <span
                              className={`badge ${
                                isStudent ? "badge-info" : isLecturer ? "badge-primary" : "badge-neutral"
                              } account-badge--role`}
                              title={`Vai trò gốc: ${a.base_role}`}
                            >
                              {isStudent ? (
                                <GraduationCap size={12} aria-hidden="true" />
                              ) : isLecturer ? (
                                <BookOpen size={12} aria-hidden="true" />
                              ) : (
                                <UserCog size={12} aria-hidden="true" />
                              )}
                              {roleTitle}
                            </span>

                            {/* Account Status Badge */}
                            <span
                              className={`badge ${
                                a.status === "ACTIVE"
                                  ? "badge-success"
                                  : a.status === "LOCKED"
                                  ? "badge-warning"
                                  : "badge-danger"
                              } account-badge--status`}
                            >
                              {a.status === "ACTIVE" ? (
                                <>
                                  <CheckCircle2 size={12} aria-hidden="true" /> Hoạt động
                                </>
                              ) : a.status === "LOCKED" ? (
                                <>
                                  <Lock size={12} aria-hidden="true" /> Bị khóa
                                </>
                              ) : (
                                <>
                                  <Ban size={12} aria-hidden="true" /> {a.verified ? "Vô hiệu hóa" : "Chờ kích hoạt"}
                                </>
                              )}
                            </span>

                            {/* Verification Badge */}
                            {!a.verified ? (
                              <span className="badge badge-warning badge-outline account-badge--verification">
                                <Clock size={12} aria-hidden="true" /> Chưa kích hoạt
                              </span>
                            ) : (
                              <span className="badge badge-success badge-subtle account-badge--verification">
                                <Check size={12} aria-hidden="true" /> Đã kích hoạt
                              </span>
                            )}
                          </div>
                          {isLecturer && a.additional_roles?.length ? (
                            <div className="account-item__duties" aria-label={"Quyền bổ sung của " + (a.display_name || a.email)}>
                              {a.additional_roles.map((role) => (
                                <span
                                  key={role.code + "-" + (role.scope || "")}
                                  className="badge badge-neutral account-badge--extra"
                                  title={role.scope ? role.label + " · " + role.scope : role.label}
                                >
                                  {role.label}{role.scope ? " · " + role.scope : ""}
                                </span>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </div>

                    {/* Actions Toolbar */}
                    <div className="account-list__actions">
                      <Link className="btn btn-ghost btn-sm col-span-full"
                        to={`/activity?resource_type=user_account&resource_id=${a.id}`}>Lịch sử tài khoản</Link>
                      {isSelf ? (
                        <span
                          className="account-current-badge text-caption col-span-full-right"
                        >
                          <CheckCircle2 size={13} aria-hidden="true" /> Tài khoản hiện tại
                        </span>
                      ) : (
                        <>
                          <div className="account-list__action-slot">
                            {a.status !== "DISABLED" || !a.verified ? (
                              <button
                                className="btn btn-secondary btn-sm"
                                disabled={busy || reason.trim().length < 5}
                                title={reason.trim().length < 5 ? "Cần nhập lý do thao tác ít nhất 5 ký tự" : ""}
                                onClick={() =>
                                  void run(
                                    () =>
                                      request(`/admin/users/${a.id}/lock`, context.user_id, {
                                        method: "POST",
                                        body: JSON.stringify({ locked: a.status !== "LOCKED", reason }),
                                      }),
                                    a.status === "LOCKED" ? "Đã mở khóa." : "Đã khóa tài khoản.",
                                  )
                                }
                              >
                                {a.status === "LOCKED" ? (
                                  <>
                                    <Unlock size={13} aria-hidden="true" /> Mở khóa
                                  </>
                                ) : (
                                  <>
                                    <Lock size={13} aria-hidden="true" /> Khóa
                                  </>
                                )}
                              </button>
                            ) : null}
                          </div>

                          <div className="account-list__action-slot">
                            {a.status === "DISABLED" && a.verified ? (
                              <button
                                className="btn btn-secondary btn-sm"
                                disabled={busy || reason.trim().length < 5}
                                title={reason.trim().length < 5 ? "Cần nhập lý do thao tác ít nhất 5 ký tự" : ""}
                                onClick={() =>
                                  void run(
                                    () =>
                                      request(`/admin/users/${a.id}/restore`, context.user_id, {
                                        method: "POST",
                                        body: JSON.stringify({ reason }),
                                      }),
                                    "Đã mở lại tài khoản cũ.",
                                  )
                                }
                              >
                                <RotateCcw size={13} aria-hidden="true" /> Mở lại tài khoản
                              </button>
                            ) : null}
                          </div>

                          <div className="account-list__action-slot">
                            {a.status !== "LOCKED" && !(a.status === "DISABLED" && a.verified) ? (
                              <button
                                className="btn btn-secondary btn-sm"
                                disabled={busy || reason.trim().length < 5}
                                title={reason.trim().length < 5 ? "Cần nhập lý do thao tác ít nhất 5 ký tự" : ""}
                                onClick={() =>
                                  void run(async () => {
                                    const result = await request<{ link_sent: boolean }>(
                                      `/admin/users/${a.id}/reissue-link`,
                                      context.user_id,
                                      { method: "POST", body: JSON.stringify({ reason }) },
                                    );
                                    return result.link_sent
                                      ? "Đã gửi liên kết mới."
                                      : "Chưa gửi được email; kiểm tra cấu hình thư.";
                                  }, "Đã cấp lại liên kết.")
                                }
                              >
                                <Send size={13} aria-hidden="true" /> Cấp lại liên kết
                              </button>
                            ) : null}
                          </div>

                          <div className="account-list__action-slot">
                            <button
                              className="btn btn-secondary btn-sm"
                              disabled={busy}
                              onClick={() => {
                                setSelectedAccount(a.id);
                                setNewEmail(a.email);
                                setEmailReason("");
                                setOfficialRef("");
                                setEmailRoundId("");
                                setTimeout(() => {
                                  document.querySelector(".admin-edit-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
                                }, 50);
                              }}
                            >
                              <Mail size={13} aria-hidden="true" /> Sửa email
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Empty State */}
            {!accounts.length ? (
              <EmptyState
                compact
                icon={<Users size={24} aria-hidden="true" />}
                title="Không có tài khoản khớp tìm kiếm"
                description="Thử thay đổi từ khóa hoặc xóa bộ lọc để xem lại danh sách."
              >
                {(search || term || accountStatus !== "ALL" || additionalRole) && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setSearch("");
                      setTerm("");
                      setAccountStatus("ALL");
                      setAdditionalRole("");
                      setPage(0);
                    }}
                  >
                    Xóa bộ lọc
                  </button>
                )}
              </EmptyState>
            ) : null}

            {/* Pagination Controls */}
            {accounts.length ? (
              <nav className="pagination" aria-label="Phân trang tài khoản">
                <button
                  className="btn btn-secondary"
                  disabled={busy || page === 0}
                  onClick={() => setPage(page - 1)}
                >
                  <ChevronLeft size={15} aria-hidden="true" />
                  Trang trước
                </button>
                <span>Trang {page + 1}</span>
                <button
                  className="btn btn-secondary"
                  disabled={busy || !hasNext}
                  onClick={() => setPage(page + 1)}
                >
                  Trang sau
                  <ChevronRight size={15} aria-hidden="true" />
                </button>
              </nav>
            ) : null}

            {/* Inline / Modal Email Update Form */}
            {selectedAccount &&
              (() => {
                const account = accountById(selectedAccount);
                if (!account) return null;
                const isStudent = account.base_role === "STUDENT";
                return (
                  <div className="admin-edit-panel">
                    <form
                      className="core-form"
                      onSubmit={(e) => {
                        e.preventDefault();
                        void run(async () => {
                          const result = isStudent
                            ? await request<{ activation_sent: boolean }>(
                                `/admin/users/${selectedAccount}/email`,
                                context.user_id,
                                {
                                  method: "PATCH",
                                  body: JSON.stringify({
                                    round_id: emailRoundId,
                                    student_code: account.student_code,
                                    email: newEmail,
                                    basis_ref: officialRef,
                                    reason: emailReason.trim(),
                                  }),
                                },
                              )
                            : await request<{ activation_sent: boolean }>(
                                `/admin/users/${selectedAccount}/contact-email`,
                                context.user_id,
                                {
                                  method: "PATCH",
                                  body: JSON.stringify({
                                    email: newEmail,
                                    basis_ref: officialRef,
                                    reason: emailReason.trim(),
                                  }),
                                },
                              );
                          setSelectedAccount("");
                          return result.activation_sent
                            ? "Đã sửa email trên tài khoản cũ và gửi liên kết kích hoạt."
                            : "Đã sửa email trên tài khoản cũ; cần cấp lại liên kết khi email hoạt động.";
                        }, "Đã sửa email.");
                      }}
                    >
                      <div className="modal-header-row">
                        <h3>{isStudent ? "Sửa email sinh viên trên tài khoản hiện có" : "Sửa email trên tài khoản hiện có"}</h3>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={() => setSelectedAccount("")}
                          aria-label="Đóng biểu mẫu sửa email"
                        >
                          <X size={16} aria-hidden="true" />
                        </button>
                      </div>

                      <p className="text-muted">
                        {isStudent
                          ? "Đối chiếu MSSV và danh sách chính thức trước khi lưu. Mật khẩu, phiên đăng nhập và liên kết cũ sẽ mất hiệu lực."
                          : "Chỉ ADMIN sửa sau khi đối chiếu căn cứ của Khoa. Giữ nguyên UUID và hồ sơ; mật khẩu, phiên đăng nhập và liên kết cũ mất hiệu lực."}
                      </p>

                      <div className="target-user-chip">
                        <Mail size={14} aria-hidden="true" />
                        <span>
                          {account.student_code ? `${account.student_code} · ` : ""}
                          {account.email}
                        </span>
                      </div>

                      {isStudent && (
                        <label className="input-group">
                          Đợt đối chiếu
                          <select
                            className="input"
                            required
                            value={emailRoundId}
                            onChange={(e) => setEmailRoundId(e.target.value)}
                          >
                            <option value="">Chọn đợt</option>
                            {rounds.map((r) => (
                              <option key={r.id} value={r.id}>
                                {r.code}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}

                      <label className="input-group">
                        Email mới
                        <input
                          className="input"
                          type="email"
                          required
                          value={newEmail}
                          onChange={(e) => setNewEmail(e.target.value)}
                        />
                      </label>

                      <label className="input-group">
                        {isStudent ? "Căn cứ danh sách chính thức" : "Căn cứ xác minh của Khoa"}
                        <input
                          className="input"
                          required
                          minLength={3}
                          value={officialRef}
                          onChange={(e) => setOfficialRef(e.target.value)}
                        />
                      </label>

                      <label className="input-group">
                        Lý do sửa email
                        <input
                          className="input"
                          required
                          minLength={5}
                          value={emailReason}
                          aria-describedby="email-reason-hint"
                          onChange={(e) => setEmailReason(e.target.value)}
                        />
                      </label>

                      <p id="email-reason-hint" role="status" className="text-caption">
                        {emailReason.trim().length < 5
                          ? "Nhập lý do sửa email ít nhất 5 ký tự để lưu."
                          : "Đã đủ lý do sửa email."}
                      </p>

                      <div className="modal-footer-row">
                        <button
                          className="btn btn-primary"
                          disabled={
                            busy ||
                            !newEmail ||
                            emailReason.trim().length < 5 ||
                            officialRef.trim().length < 3 ||
                            (isStudent && !emailRoundId)
                          }
                        >
                          Lưu email mới
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          disabled={busy}
                          onClick={() => setSelectedAccount("")}
                        >
                          Hủy sửa email
                        </button>
                      </div>
                    </form>
                  </div>
                );
              })()}
          </div>
        </section>)}
      </div>
    </div>
  );
}
