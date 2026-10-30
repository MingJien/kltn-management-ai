import { stateLabel } from "./stateLabels";

type BadgeVariant = "info" | "warning" | "success" | "danger" | "neutral" | "primary";

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Bản nháp",
  SUBMITTED: "Đã gửi",
  APPROVED: "Đã duyệt",
  RETURNED: "Trả lại để sửa",
  REJECTED: "Từ chối",
  LOCKED: "Đã khóa",
  CANCELLED: "Đã hủy",
  LECTURER_ACCEPTED: "GV đã chấp nhận",
  LECTURER_REJECTED: "GV từ chối",
  FINALIZED: "Đã tiếp nhận chính thức",
  ACCEPTED: "Đã xác nhận",
  PENDING: "Chờ xác nhận",
  DECLINED: "Không tham gia",
};

const STATE_VARIANT: Record<string, BadgeVariant> = {
  DRAFT: "info",
  SUBMITTED: "warning",
  UNDER_REVIEW: "warning",
  LECTURER_ACCEPTED: "warning",
  LECTURER_REJECTED: "danger",
  RETURNED: "info",
  APPROVED: "success",
  FINALIZED: "success",
  CANCELLED: "danger",
  REJECTED: "danger",
  ADVISOR_CONFIRMED: "success",
  DEPARTMENT_FINALIZED: "success",
  PRINT_READY: "neutral",
  DEAN_CONFIRMED: "success",
  SIGNED: "success",
  VOID: "danger",
  IN_PROGRESS: "warning",
  ACTIVE: "primary",
  COMPLETED: "success",
  QUEUED: "neutral",
  RUNNING: "warning",
  FAILED: "danger",
  NO_EVIDENCE: "neutral",
  RETRIEVAL_ONLY: "info",
  ANSWERED: "success",
  ACCEPTED: "success",
  PENDING: "warning",
  DECLINED: "danger",
  REVISION_REQUIRED: "warning",
  REVISION_REQUESTED: "warning",
  OPEN: "success",
  CLOSED: "neutral",
  CONFIRMED: "success",
  PROPOSAL_APPROVED: "success",
  EXTENDED: "info",
  READY_FOR_DEFENSE: "info",
  DEFENDED: "success",
  ARCHIVED: "neutral",
  WITHDRAWN: "danger",
  REVOKED: "danger",
  FINAL: "success",
  SUPERSEDED: "neutral",
  LOCKED: "neutral",
  DISABLED: "neutral",
  ENDED: "neutral",
  COMMENT_ONLY: "info",
  COMMENT: "info",
  CONFIRM: "info",
  ACCEPT: "success",
};

interface ThesisStatusBadgeProps {
  state: string;
  showIcon?: boolean;
  className?: string;
  label?: string;
}

export default function ThesisStatusBadge({
  state,
  showIcon = true,
  className = "",
  label,
}: ThesisStatusBadgeProps) {
  const variant = STATE_VARIANT[state] || "neutral";
  const classes = ["badge", "badge-" + variant, className].filter(Boolean).join(" ");

  return (
    <span className={classes}>
      {showIcon ? <span className={"status-dot status-dot--" + variant} aria-hidden="true" /> : null}
      {label || STATUS_LABEL[state] || stateLabel[state] || state}
    </span>
  );
}