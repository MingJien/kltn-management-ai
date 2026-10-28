import { useId, useState } from "react";
import type { Review } from "../../api";
import ReviewCommentText from "./ReviewCommentText";

export const stateLabel: Record<string, string> = {
  ACTIVE: "Đang thực hiện", IN_PROGRESS: "Đang thực hiện", PROPOSAL_APPROVED: "Đề cương đã duyệt",
  EXTENDED: "Được gia hạn", WITHDRAWN: "Đã rút", READY_FOR_DEFENSE: "Sẵn sàng bảo vệ",
  DEFENDED: "Đã bảo vệ", COMPLETED: "Hoàn thành", ARCHIVED: "Đã lưu trữ",
  SUBMITTED: "Chờ GVHD xem", CONFIRMED: "Đã xác nhận", REVISION_REQUIRED: "Cần chỉnh sửa",
  REVISION_REQUESTED: "Cần chỉnh sửa", ACCEPTED: "GVHD đã tiếp nhận", APPROVED: "Đã duyệt",
  OPEN: "Đang mở", CLOSED: "Đã đóng", ENDED: "Đã kết thúc", REVOKED: "Đã thu hồi",
  COMMENT_ONLY: "Góp ý chéo", CONFIRM: "Xác nhận", ACCEPT: "Tiếp nhận",
  UNDER_REVIEW: "Đang nhận xét", ADVISOR_CONFIRMED: "GVHD đã xác nhận",
  DEPARTMENT_FINALIZED: "Bộ môn đã chốt", DEAN_CONFIRMED: "Đã ghi nhận bản ký Trưởng khoa",
  COMMENT: "Góp ý đề cương",
  LOCKED: "Đã khóa", DISABLED: "Ngừng sử dụng", FINAL: "Bản cuối đã khóa",
  SUPERSEDED: "Đã có phiên bản mới",
};

export function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString("vi-VN", {timeZone: "Asia/Ho_Chi_Minh"}) : "Chưa đặt";
}

export function Status({value, label}: {value: string; label?: string}) {
  return <span className="badge badge-primary">{label || stateLabel[value] || value}</span>;
}

export function Reviews({items}: {items: Review[]}) {
  return <div className="stack">{items.map((item, index) => <div className="core-review" key={`${item.created_at}-${index}`}>
    <strong>{item.reviewer_name}</strong> · {stateLabel[item.decision] || item.decision}
    <p className="core-prewrap"><ReviewCommentText text={item.comment} /></p>
    <small className="text-muted">{formatDate(item.created_at)}</small>
  </div>)}</div>;
}

export function ReviewForm({choices, disabled, onSubmit}: {
  choices: {value: string; label: string}[]; disabled: boolean;
  onSubmit: (decision: string, comment: string) => Promise<boolean>;
}) {
  const id = useId();
  const [decision, setDecision] = useState(choices[0].value);
  const [comment, setComment] = useState("");
  const selected = choices.some(choice=>choice.value===decision) ? decision : choices[0].value;
  return <form className="core-form" onSubmit={async (event) => {
    event.preventDefault();
    if (await onSubmit(selected, comment.trim())) setComment("");
  }}>
    <div className="input-group"><label htmlFor={`${id}-decision`}>Kết quả</label>
      <select className="input" id={`${id}-decision`} value={selected} onChange={event => setDecision(event.target.value)} disabled={disabled}>
        {choices.map(choice => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
      </select>
    </div>
    <div className="input-group"><label htmlFor={`${id}-comment`}>Nhận xét / lý do</label>
      <textarea className="input" id={`${id}-comment`} value={comment} onChange={event => setComment(event.target.value)} required maxLength={2000} disabled={disabled} />
    </div>
    <button className="btn btn-primary" disabled={disabled || !comment.trim()}>Gửi kết quả</button>
  </form>;
}
