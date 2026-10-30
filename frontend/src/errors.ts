export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const messages: Record<string, string> = {
  "The selected round is not open": "Đợt đăng ký đã đóng hoặc chưa mở. Hãy làm mới danh sách.",
  "Students describe their proposal; lecturer requirements are not student-editable": "SV nhập phạm vi trong mô tả đề xuất; không được sửa yêu cầu của GV.",
  "Topic registration capacity is full": "Đề tài đã đủ số SV. Hãy làm mới danh sách và chọn đề tài còn chỗ.",
  "Students must register themselves and confirm their own participation": "Chỉ được đăng ký và xác nhận cho tài khoản của mình.",
  "Group membership is locked after submission": "Đăng ký đã chốt thành khóa luận; không thể bổ sung SV tại đây.",
  "This topic has legacy competing groups; department review is required": "Đề tài có nhiều nhóm đăng ký theo cách cũ. Cần người phụ trách đối chiếu trước khi đăng ký thêm.",
  "Student proposals start with one student; others join after department approval": "Đề xuất bắt đầu bằng một SV; các bạn khác tham gia sau khi bộ môn duyệt.",
  "Group membership or account eligibility has changed; reload before submission": "Có thành viên không còn đủ điều kiện hoặc tài khoản đã bị khóa. Làm mới và liên hệ Khoa.",
  "Group membership or account eligibility has changed; acceptance is unavailable": "Chưa thể nhận: có thành viên không còn đủ điều kiện hoặc tài khoản đã bị khóa.",
  "Sign in required": "Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.",
  "Sign-in session has expired": "Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.",
  "Request verification failed": "Phiên bảo vệ thao tác đã hết. Hãy tải lại trang và thử lại.",
  "Request origin is not allowed": "Địa chỉ giao diện chưa được phép kết nối. Hãy mở đúng địa chỉ của hệ thống.",
  "Email or password is incorrect, or the account is unavailable": "Email hoặc mật khẩu chưa đúng, hoặc tài khoản chưa được cấp quyền.",
  "Too many sign-in attempts; try again later": "Bạn đã thử đăng nhập sai nhiều lần. Vui lòng thử lại sau 15 phút.",
  "Version conflict; reload before deciding": "Hồ sơ đã được cập nhật ở nơi khác. Hãy làm mới và kiểm tra lại trước khi quyết định.",
  "A member already has an active registration in this round": "Bạn đã có đăng ký đang hoạt động trong đợt này. Mở mục Đăng ký để xem.",
  "This topic already has an accepted group": "Đề tài đã có nhóm được GV chấp nhận. Vui lòng chọn đề tài khác.",
  "Another group has already been accepted": "Đề tài đã có nhóm được GV chấp nhận.",
  "Another group has already been accepted for this topic": "Đề tài đã có nhóm được chấp nhận; chỉ có thể từ chối hồ sơ còn chờ.",
  "Topic or registration round is not open": "Đề tài hoặc đợt đăng ký đã đóng. Hãy làm mới danh sách.",
  "The topic or registration round is no longer open": "Đề tài hoặc đợt đăng ký đã đóng. Bạn chưa thể gửi hồ sơ này.",
  "Every member needs a current confirmed eligibility snapshot": "Cần được xác nhận đủ điều kiện ở đợt này trước khi đăng ký.",
  "Every group member must still have a confirmed eligibility snapshot": "Có thành viên chưa còn đủ điều kiện ở đợt này. Liên hệ người xác nhận của Khoa.",
  "Group exceeds topic capacity": "Số sinh viên vượt sức chứa của đề tài.",
  "A proposer cannot approve their own topic": "Người đề xuất không được tự duyệt đề tài của mình.",
  "A rejection requires a reason": "Vui lòng ghi lý do từ chối.",
  "Returning or rejecting a topic requires a reason": "Vui lòng ghi góp ý hoặc lý do trả lại/từ chối.",
  "Topic is not awaiting department decision": "Đề tài đã được xử lý. Hãy làm mới hàng chờ duyệt.",
  "Department topic approval is required before the lecturer decision": "Cần bộ môn duyệt đề tài trước khi GV quyết định tiếp nhận.",
  "Evidence is locked after submission": "Hồ sơ đã gửi nên không thể thay minh chứng.",
  "Evidence file must be at most 5 MB": "Minh chứng tối đa 5 MB.",
  "Use a PDF, PNG or JPEG with matching file content": "Chọn tệp PDF, PNG hoặc JPEG hợp lệ.",
  "Topic title is too short": "Tên đề tài cần ít nhất 5 ký tự có nội dung.",
  "Revised title is too short": "Tên đề tài sau duyệt cần ít nhất 5 ký tự có nội dung.",
};

export function apiMessage(status: number, detail: unknown, path = ""): string {
  if (path.startsWith("/admin/lecturers") && typeof detail === "string"
      && [409, 413, 422, 429, 503].includes(status)) return messages[detail] || detail;
  if (status === 422 && path.includes("/roster")) {
    if (Array.isArray(detail)) {
      const locations = detail.flatMap(item => Array.isArray(item?.loc) ? item.loc : []);
      if (locations.includes("X-File-Name")) return "Không nhận được tên tệp. Hãy chọn lại tệp CSV/XLSX rồi thử lại.";
      if (locations.includes("round_id")) return "Đợt KLTN chưa hợp lệ. Hãy chọn lại đợt rồi thử lại.";
    }
    if (typeof detail === "string") {
      if (detail.startsWith("Dòng ") && detail.includes("mã bộ môn")) return detail;
      const row = /^Row (\d+)(.*)$/.exec(detail);
      if (row) {
        const line = `Dòng ${row[1]}`;
        if (row[2].includes("department code")) return `${line}: mã bộ môn không tồn tại hoặc bị trùng trong hệ thống.`;
        if (row[2].includes("major does not match")) return `${line}: mã ngành không khớp bộ môn.`;
        if (row[2].includes("duplicates")) return `${line}: MSSV hoặc email bị trùng trong tệp.`;
        if (row[2].includes("formula-like")) return `${line}: không được nhập công thức bảng tính.`;
        if (row[2].includes("invalid required value")) return `${line}: thiếu hoặc sai MSSV, tên, email, bộ môn, lớp hoặc mã ngành.`;
        if (row[2].includes("empty or has extra cells")) return `${line}: dòng rỗng hoặc thừa ô.`;
      }
      if (detail.startsWith("Required columns:") || detail === "The roster contains an unsupported column")
        return "Backend đang chạy bộ đọc danh sách cũ. Hãy dừng và chạy lại terminal backend, tải lại trang rồi chọn tệp Excel/CSV với cột MSSV, Họ tên, Email, Mã bộ môn, Lớp, Mã ngành.";
      if (detail.startsWith("Thiếu hoặc trùng cột.") || detail.startsWith("Cột không được hỗ trợ.")) return detail;
      if (detail.startsWith("Invalid roster:")) return "Không đọc được tệp CSV UTF-8 hoặc XLSX. Hãy chọn lại tệp mẫu, không đổi phần mở rộng bằng tay.";
      if (detail.startsWith("Roster must contain")) return "Tệp cần có dữ liệu và không vượt quá 2 MB.";
    }
  }
  if (Array.isArray(detail)) return "Thông tin chưa hợp lệ. Kiểm tra các ô bắt buộc, độ dài và giới hạn số lượng.";
  if (typeof detail === "string" && messages[detail]) return messages[detail];
  if (status === 401) return "Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.";
  if (status === 403) return "Tài khoản không có quyền thực hiện thao tác này.";
  if (status === 404) return "Không tìm thấy hồ sơ hoặc bạn không có quyền xem.";
  if (status === 409) return "Hồ sơ đã thay đổi hoặc không còn ở trạng thái cho phép. Hãy làm mới rồi kiểm tra lại.";
  if (status === 422) return "Thông tin chưa hợp lệ. Vui lòng kiểm tra nội dung đã nhập.";
  return "Chưa thực hiện được thao tác. Vui lòng thử lại hoặc liên hệ người quản lý hệ thống.";
}

export function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : "Không thể kết nối. Vui lòng kiểm tra mạng và thử lại.";
}
