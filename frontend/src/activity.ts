export type ActivityItem = {
  id: string; action: string; actor_name: string; resource_type: string; resource_id: string;
  resource_label: string; reason: string | null; source_reference: string | null; occurred_at: string;
};
export type ActivityResult = {items: ActivityItem[]; total: number; actions: string[]; scope: string};

const actions: Record<string, string> = {
  DEFENSE_CORRECTION_REQUESTED:'Đề nghị đính chính sau khóa',DEFENSE_CORRECTION_APPROVED:'Duyệt đính chính sau khóa',
  DEFENSE_CORRECTION_REJECTED:'Không duyệt đính chính',DEFENSE_CORRECTION_CANCELLED:'Hủy đề nghị đính chính',
  DEFENSE_PRINT_SAVED:"Lưu bản xuất hội đồng để ký", THESIS_ARCHIVE_SUBMITTED:"Nộp bản khóa luận sau bảo vệ",
  THESIS_ARCHIVE_ACCEPTED:"Duyệt lưu khóa luận nội bộ", THESIS_ARCHIVE_RETURNED:"Yêu cầu nộp lại bản khóa luận lưu",
  THESIS_ARCHIVE_REOPENED:"Thu hồi bản đã duyệt lưu và yêu cầu nộp lại",
  DEFENSE_COUNCIL_CREATED:"Lập hội đồng bảo vệ", DEFENSE_COUNCIL_REVISED:"Điều chỉnh hội đồng", DEFENSE_COUNCIL_BEFORE_REVISION:"Lưu thành phần hội đồng trước sửa",
  DEFENSE_SCHEDULED:"Xếp / đổi lịch bảo vệ", DEFENSE_RESCHEDULED:"Đổi lịch bảo vệ", DEFENSE_SCHEDULE_BEFORE_REVISION:"Lưu lịch bảo vệ trước sửa", DEFENSE_SCHEDULE_PUBLISHED:"Công bố lịch bảo vệ", DEFENSE_CANCELLED:"Hủy lịch bảo vệ", DEFENSE_COUNCIL_ATTENDANCE:"Điểm danh hội đồng",
  DEFENSE_ATTENDANCE_RECORDED:"Điểm danh sinh viên", DEFENSE_MARK_SUBMITTED:"Lưu phiếu chấm", DEFENSE_MARK_REVISED:"Lưu phiên bản phiếu trước sửa",
  DEFENSE_MARK_VOIDED:"Hủy hiệu lực phiếu nhập nhầm", DEFENSE_MARK_CLEARED:"Ghi nhận hủy phiếu", DEFENSE_BONUS_CONFIRMED:"Xác nhận điểm thưởng và minh chứng",
  DEFENSE_PRINT_WITHDRAWN:"Thu hồi bản in hội đồng",
  DEFENSE_ACADEMIC_PROFILE_CORRECTED:"Đính chính thông tin học vụ phục vụ bản xuất",
  DEFENSE_MINUTES_SAVED:"Lưu biên bản bảo vệ", DEFENSE_FINALIZED:"Chốt kết quả bảo vệ", DEFENSE_UNSIGNED_REVISION:"Lưu bản chốt trước điều chỉnh",
  DEFENSE_REOPENED:"Mở sửa hồ sơ chưa ký", DEFENSE_COUNCIL_CLOSED:"Khóa bảng điểm hội đồng", DEFENSE_ABSENCE_DECIDED:"Khoa xử lý SV vắng",
  DEFENSE_ABSENCE_BEFORE_REVISION:"Lưu quyết định xử lý vắng trước sửa",
  PUBLICATION_CLAIM_SUBMITTED:"Nộp minh chứng công bố khoa học", PUBLICATION_CLAIM_CONFIRMED:"GVHD xác nhận minh chứng công bố",
  PUBLICATION_CLAIM_APPROVED:"TBM duyệt điểm thưởng công bố", PUBLICATION_CLAIM_REJECTED:"TBM không duyệt điểm thưởng công bố",
  PUBLICATION_CLAIM_REVISION_REQUIRED:"Yêu cầu bổ sung minh chứng công bố",
  PUBLICATION_SUBMITTED:"Nộp minh chứng công bố khoa học", PUBLICATION_ADVISOR_CONFIRMED:"GVHD xác nhận minh chứng công bố",
  PUBLICATION_APPROVED:"TBM duyệt điểm thưởng công bố", PUBLICATION_REJECTED:"TBM không duyệt điểm thưởng công bố",
  PUBLICATION_REVISION_REQUIRED:"Yêu cầu bổ sung minh chứng công bố",
  ROUND_MAU04_EXPORTED:"Xuất danh sách theo Mẫu 4",
  THESIS_CREATED_FROM_TOPIC_CHANGE:"Khởi tạo khóa luận từ tách nhóm / đổi đề tài",

  THESIS_CHANGE_SUBMITTED: "Gửi đề nghị đổi đề tài", THESIS_CHANGE_CONSENT: "Xác nhận nguyện vọng đổi đề tài",
  THESIS_CHANGE_REVIEWED: "GVHD xem xét đổi đề tài", THESIS_CHANGE_APPROVED: "Duyệt đổi đề tài",
  THESIS_CHANGE_REJECTED: "Từ chối đổi đề tài", THESIS_CHANGE_CANCELLED: "Hủy đề nghị đổi đề tài",
  THESIS_EXTENSION_RECORDED: "Ghi nhận gia hạn thực hiện KLTN", THESIS_EXTENSION_SUBMITTED: "Gửi yêu cầu gia hạn", THESIS_EXTENSION_CONSENT: "Xác nhận xin gia hạn", THESIS_EXTENSION_REVIEWED: "GVHD cho ý kiến gia hạn", THESIS_EXTENSION_APPROVED: "TBM duyệt gia hạn", THESIS_EXTENSION_REJECTED: "Không chấp thuận gia hạn", THESIS_EXTENSION_EXPIRED: "Hết hạn lấy ý kiến gia hạn", THESIS_EXTENSION_NOT_PASSED: "Không đạt sau thời hạn gia hạn", THESIS_EXTENSION_CANCELLED: "Hủy yêu cầu gia hạn", THESIS_EXTENSION_CONSENT_DEADLINE: "Đặt hạn / nhắc đồng thuận", THESIS_TOPIC_REPLACED: "Chuyển sang đề tài khác",
  THESIS_CHANGE_ASSIGNMENT_ENDED: "Kết thúc phân công theo đề tài cũ", ROUND_REGISTRATION_REOPENED: "Gia hạn và mở lại đăng ký",
  WITHDRAWAL_SUBMITTED: "SV gửi đơn xin thôi", WITHDRAWAL_ADVISOR_CONFIRMED: "GVHD xác nhận đơn xin thôi",
  WITHDRAWAL_RETURNED: "GVHD trả lại đơn xin thôi", WITHDRAWAL_CANCELLED: "Hủy yêu cầu xin thôi",
  WITHDRAWAL_SIGNED_COPY_ADDED: "Bổ sung đơn có xác nhận", WITHDRAWAL_FILE_SCANNED: "Kiểm tra an toàn đơn xin thôi",
  WITHDRAWAL_RECORDED: "Ghi nhận kết quả cho thôi KLTN", WITHDRAWAL_NOT_GRANTED: "Ghi nhận không chấp thuận xin thôi",
  WITHDRAWAL_PRINT_EXPORTED: "Xuất đơn xin thôi để in", WITHDRAWAL_START_RECORDED: "Ghi nhận ngày bắt đầu thực hiện",
  PROPOSAL_MEMBERSHIP_REVISION_REQUIRED: "Yêu cầu duyệt lại đề cương khi đổi thành viên",
  DOCUMENT_MEMBERSHIP_REVISION_REQUIRED: "Yêu cầu cập nhật báo cáo khi đổi thành viên",
  WITHDRAWAL_REVIEW_ASSIGNMENT_ENDED: "Kết thúc phân công do khóa luận không còn thành viên",
  LECTURER_PROFILE_SUBMITTED: "Gửi cập nhật hồ sơ giảng viên", LECTURER_PROFILE_APPROVED: "Duyệt hồ sơ giảng viên",
  LECTURER_PROFILE_RETURNED: "Yêu cầu bổ sung hồ sơ giảng viên", LECTURER_PROFILE_WITHDRAWN: "Rút cập nhật hồ sơ giảng viên",
  LECTURER_IDENTITY_CORRECTED: "Đối chiếu và sửa định danh giảng viên",
  THESIS_REVIEWER_ASSIGNED: "Phân công phản biện khóa luận", THESIS_REVIEWER_REVOKED: "Thu hồi phân công phản biện",
  THESIS_REVIEW_DEADLINE_EXTENDED: "Gia hạn gửi nhận xét phản biện", THESIS_REVIEW_SUBMITTED: "Gửi nhận xét Mẫu 7/8",
  THESIS_REVIEW_PAPER_RECEIVED: "Ghi nhận đã nhận bản giấy nhận xét",
  THESIS_REVIEW_EXPORTED: "Xuất phiếu nhận xét đã điền để ký",
  DEFENSE_ELIGIBILITY_CHECKED: "Xét điều kiện dự bảo vệ", DEFENSE_ELIGIBILITY_REOPENED: "Mở xét lại điều kiện bảo vệ",
  OFFICIAL_FORM_CREATED: "Tạo danh mục biểu mẫu Khoa", OFFICIAL_FORM_METADATA_UPDATED: "Cập nhật danh mục biểu mẫu",
  OFFICIAL_FORM_VERSION_UPLOADED: "Tải phiên bản biểu mẫu lên kho", OFFICIAL_FORM_PUBLISHED: "Phát hành biểu mẫu",
  OFFICIAL_FORM_WITHDRAWN: "Thu hồi phiên bản biểu mẫu", OFFICIAL_FORM_BOOTSTRAPPED: "Khởi tạo mẫu Khoa",
  LECTURER_IMPORTED: "Nhập tài khoản giảng viên từ Excel",
  LECTURER_ACTIVATION_SENDING: "Bắt đầu gửi link kích hoạt GV",
  LECTURER_ACTIVATION_SENT: "Dịch vụ thư đã nhận link kích hoạt GV",
  LECTURER_ACTIVATION_FAILED: "Gửi link kích hoạt GV thất bại",
  ACCOUNT_SIGNED_IN: "Đăng nhập", ACCOUNT_SIGNED_OUT: "Đăng xuất",
  ACCOUNT_ACTIVATED: "Kích hoạt tài khoản", ACCOUNT_LOCKED: "Khóa tài khoản", ACCOUNT_UNLOCKED: "Mở khóa tài khoản",
  ACCOUNT_DISABLED: "Vô hiệu hóa tài khoản", ACCOUNT_RESTORED: "Mở lại tài khoản", ACCOUNT_LINK_REISSUED: "Cấp lại liên kết",
  ACCOUNT_EMAIL_CORRECTED: "Đính chính email", PASSWORD_RESET: "Đặt lại mật khẩu", PASSWORD_CHANGED: "Đổi mật khẩu",
  LECTURER_INVITED: "Cấp tài khoản giảng viên", ROUND_CREATED: "Tạo đợt KLTN", ROUND_SCHEDULE_UPDATED: "Sửa lịch đợt",
  LECTURER_PROFILE_SELF_CONFIRMED: "TBM tự xác nhận hồ sơ chuyên môn",
  POSITION_ASSIGNED: "Ghi nhận bổ nhiệm chức vụ", POSITION_REPLACED: "Thay người giữ chức vụ", POSITION_REVOKED: "Thu hồi bổ nhiệm",
  ROUND_REGISTRATION_EXTENDED: "Gia hạn đăng ký của đợt", ROUND_OPENED: "Mở đợt đăng ký", ROUND_CLOSED: "Đóng đợt đăng ký", ROUND_PERMISSION_GRANTED: "Phân công nhiệm vụ theo đợt",
  ROUND_PERMISSION_REVOKED: "Thu hồi nhiệm vụ theo đợt", ELIGIBILITY_ROSTER_IMPORTED: "Nhập danh sách sinh viên đủ điều kiện",
  ELIGIBILITY_SPECIAL_DECISION_RECORDED: "Ghi nhận quyết định đủ điều kiện", ELIGIBILITY_REVOKED: "Thu hồi kết quả đủ điều kiện",
  ELIGIBILITY_RESTORED: "Khôi phục quyền tham gia đợt",
  ROSTER_IDENTITY_CORRECTED: "Đính chính thông tin sinh viên", TOPIC_CREATED: "Tạo đề tài", TOPIC_UPDATED: "Cập nhật đề tài",
  TOPIC_ARCHIVED: "Ngừng sử dụng đề tài", TOPIC_RESTORED: "Khôi phục hiển thị đề tài", TOPIC_DELETED: "Xóa đề tài nháp", TOPIC_SUBMITTED: "Gửi đề tài xét duyệt", TOPIC_APPROVED: "Duyệt đề tài", TOPIC_RETURNED: "Yêu cầu sửa đề tài",
  TOPIC_REJECTED: "Từ chối đề tài", TOPIC_PROPOSAL_WITHDRAWN: "Rút đề xuất đề tài",
  REGISTRATION_SUBMITTED: "Gửi hồ sơ đăng ký", REGISTRATION_CANCELLED: "Hủy hồ sơ đăng ký",
  REGISTRATION_ACCEPT: "GV chấp nhận đăng ký", REGISTRATION_REJECT: "GV từ chối đăng ký",
  REGISTRATION_MEMBER_WITHDREW: "Thành viên rút khỏi đăng ký", REGISTRATION_MEMBER_ACCEPTED: "Xác nhận tham gia nhóm",
  REGISTRATION_MEMBER_DECLINED: "Từ chối tham gia nhóm", REGISTRATION_CREATED: "Tạo hồ sơ đăng ký",
  REGISTRATION_UPDATED: "Cập nhật nhóm đăng ký", REGISTRATION_FORM_SUBMITTED: "Nộp đơn đăng ký Mẫu 1a/1b",
  REGISTRATION_MEMBER_JOINED: "Thành viên tham gia nhóm", REGISTRATION_EVIDENCE_LINK_CLEARED: "Gỡ liên kết minh chứng đăng ký cũ",
  PROPOSAL_REASSIGNED_AFTER_LECTURER_REJECTION: "TBM chọn GV khác sau khi GV từ chối",
  PROPOSAL_RETURNED_AFTER_LECTURER_REJECTION: "Trả đề xuất cho SV sửa sau khi GV từ chối",
  REGISTRATION_FORM_SCANNED: "Kiểm tra an toàn đơn đăng ký", REGISTRATION_FORM_PRINT_EXPORTED: "Xuất bản in đơn đăng ký",
  REGISTRATION_EVIDENCE_UPLOADED: "Nộp minh chứng đăng ký", REGISTRATION_EVIDENCE_REPLACED: "Cập nhật minh chứng đăng ký",
  REGISTRATION_EVIDENCE_SCANNED: "Kiểm tra an toàn minh chứng đăng ký",
  THESIS_CREATED_FROM_REGISTRATION_ACCEPTANCE: "Tạo hồ sơ khóa luận và GVHD chính thức",
  MILESTONE_OPENED: "Mở mốc tiến độ", MILESTONE_CLOSED: "Đóng mốc tiến độ", MILESTONE_EXTENDED: "Gia hạn mốc tiến độ",
  MILESTONE_REOPENED: "Gia hạn và mở lại mốc", DOCUMENT_DEADLINE_SET: "Thiết lập hạn tài liệu",
  DOCUMENT_DEADLINE_EXTENDED: "Gia hạn nộp tài liệu", DOCUMENT_DEADLINE_REOPENED: "Gia hạn và mở nhận lại tài liệu",
  DOCUMENT_DEADLINE_CLOSED: "Đóng nhận tài liệu", PROGRESS_SUBMITTED: "Nộp báo cáo tiến độ",
  PROGRESS_SELF_CORRECTED: "Cập nhật phiên bản báo cáo", PROGRESS_EVIDENCE_UPLOADED: "Nộp minh chứng tiến độ",
  PROGRESS_EVIDENCE_SCANNED: "Kiểm tra an toàn minh chứng", PROGRESS_COMMENT_ONLY: "Góp ý báo cáo tiến độ",
  PROGRESS_CONFIRM: "Xác nhận báo cáo tiến độ", PROGRESS_REVISION_REQUIRED: "Yêu cầu sửa báo cáo",
  PROGRESS_REVIEWER_ASSIGNED: "Phân công góp ý tiến độ", PROGRESS_REVIEWER_REVOKED: "Thu hồi phân công góp ý",
  DOCUMENT_CREATED: "Tạo hồ sơ tài liệu", DOCUMENT_UPLOADED: "Nộp phiên bản tài liệu",
  DOCUMENT_SELF_CORRECTED: "Cập nhật phiên bản tài liệu", DOCUMENT_WITHDRAWN: "Thu hồi tài liệu nộp nhầm",
  DOCUMENT_FILE_SCANNED: "Kiểm tra an toàn tài liệu", DOCUMENT_ACCEPT: "Duyệt tài liệu",
  DOCUMENT_REVISION_REQUIRED: "Yêu cầu sửa tài liệu", DOCUMENT_REVIEWED: "Ghi nhận phản hồi tài liệu",
  DOCUMENT_PRINT_COPY_EXPORTED: "Xuất bản in tài liệu đã duyệt", PROPOSAL_SUBMITTED: "Nộp đề cương",
  PROPOSAL_SELF_CORRECTED: "Cập nhật phiên bản đề cương", PROPOSAL_FILE_SCANNED: "Kiểm tra an toàn đề cương",
  PROPOSAL_REVIEWER_ASSIGNED: "Phân công góp ý đề cương", PROPOSAL_COMMENT: "Góp ý đề cương",
  PROPOSAL_CONFIRM: "GVHD xác nhận đề cương", PROPOSAL_REVISION_REQUIRED: "Yêu cầu sửa đề cương",
  PROPOSAL_DEPARTMENT_FINALIZED: "TBM chốt đề cương", PROPOSAL_DEAN_COPY_RECORDED: "Ghi nhận bản đề cương Khoa xác nhận",
  PROPOSAL_PRINT_COPY_EXPORTED: "Xuất bản in đề cương", WORK_SUBMITTED: "Gửi phân công công việc",
  WORK_APPROVE: "Duyệt phân công công việc", WORK_REVISION_REQUIRED: "Yêu cầu sửa phân công công việc",
};
export const actionLabel = (code: string) => actions[code] || code.replaceAll("_", " ");
export const resourceLabel = (code: string) => ({defense_slot:"Phiên bảo vệ",defense_council:"Hội đồng bảo vệ",thesis_withdrawal_request:"Đơn xin thôi KLTN", official_form: "Biểu mẫu / tài liệu Khoa", user_account: "Tài khoản", student_profile: "Hồ sơ sinh viên",
  lecturer_profile: "Hồ sơ giảng viên", lecturer_profile_change: "Cập nhật hồ sơ giảng viên", topic: "Đề tài", topic_registration: "Đăng ký", registration: "Đăng ký", thesis: "Khóa luận",
  round: "Đợt KLTN", thesis_round: "Đợt KLTN", resource_assignment: "Phân công", position_assignment: "Chức vụ", eligibility_snapshot: "Điều kiện đăng ký",
  document: "Tài liệu", document_version: "Phiên bản tài liệu", proposal: "Đề cương", proposal_version: "Phiên bản đề cương",
  document_deadline: "Hạn tài liệu", progress_report: "Báo cáo tiến độ",
  defense_eligibility_check: "Điều kiện dự bảo vệ", thesis_change_request: "Đổi đề tài", thesis_extension_request: "Gia hạn KLTN",
  thesis_review: "Phiếu nhận xét Mẫu 7/8", publication_claim: "Minh chứng công bố khoa học", thesis_archive_version: "Bản lưu khóa luận"} as Record<string,string>)[code] || code;

export function activityReason(item:ActivityItem):string|null {
  if(!item.reason||!item.action.startsWith("DEFENSE_"))return item.reason;
  try {
    const value=JSON.parse(item.reason);
    if(value.previous?.scores)return `Điểm từng tiêu chí trước sửa: ${value.previous.scores.join("; ")}. Nhận xét: ${value.previous.note||"Không có"}. ${value.reason||""}`;
    if(value.previous_version)return `Bản trước: v${value.previous_version}. Lý do: ${value.reason}. Nội dung biên bản trước: ${value.minutes?.discussion||""}. Kết luận trước: ${value.minutes?.conclusion||""}.`;
    if(value.members)return `${value.name} · ${value.reference}. Thành phần trước: ${value.members.map((p:{name:string})=>p.name).join(", ")}.`;
    if("room" in value && value.starts_at && value.ends_at) {
      const fmt = (iso: string) => new Date(iso).toLocaleString("vi-VN", {timeZone: "Asia/Ho_Chi_Minh"});
      return `Lịch trước điều chỉnh: Phòng ${value.room || "Chưa ghi"} · ${fmt(value.starts_at)} → ${fmt(value.ends_at)}.`;
    }
    const entries = Object.values(value).filter((v): v is {outcome?:string;reference?:string;reason?:string} => Boolean(v && typeof v === "object" && "outcome" in v));
    if(entries.length) {
      return entries.map(d=>`${d.outcome==="SUPPLEMENTARY"?"Cho phép bảo vệ bổ sung":"Không đạt do vắng"} · ${d.reference||""} · ${d.reason||""}`).join("; ");
    }
    return item.reason;
  }catch{return item.reason;}
}
