import Badge, { type BadgeVariant } from "../ui/Badge";
import { stateLabel } from "./stateLabels";

/** Preserves E2E-verified registration & status wording while eliminating shadowed mismatches. */
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

/** Semantic Academic Blue mapping:
 *  - neutral: Draft / Queued / Locked / Print Ready / Disabled / Ended
 *  - info: Normal active progress / In-flight / Retrieved / Extended
 *  - warning: Needs review or user revision (Submitted / Under review / Returned / Revision required / Pending)
 *  - success: Approved / Accepted / Finalized / Completed / Clean / Eligible
 *  - danger: Rejected / Cancelled / Withdrawn / Failed / Blocked / Void / Infected
 */
const STATE_VARIANT: Record<string, BadgeVariant> = {
  DRAFT: "neutral",
  QUEUED: "neutral",
  PRINT_READY: "neutral",
  LOCKED: "neutral",
  NOT_CHECKED: "neutral",
  UNKNOWN: "neutral",

  CLOSED: "muted",
  ARCHIVED: "muted",
  SUPERSEDED: "muted",
  DISABLED: "muted",
  ENDED: "muted",
  NO_EVIDENCE: "muted",
  EXPIRED: "muted",
  NOT_GRANTED: "muted",

  ACTIVE: "info",
  IN_PROGRESS: "info",
  LECTURER_ACCEPTED: "info",
  READY_FOR_DEFENSE: "info",
  EXTENDED: "info",
  RUNNING: "info",
  RETRIEVAL_ONLY: "info",
  COMMENT_ONLY: "info",
  COMMENT: "info",
  CONFIRM: "info",
  ADVISOR_REVIEWED: "info",
  RECORDED: "info",

  SUBMITTED: "warning",
  UNDER_REVIEW: "warning",
  PENDING: "warning",
  PENDING_ACTIVATION: "warning",
  RETURNED: "warning",
  REVISION_REQUIRED: "warning",
  REVISION_REQUESTED: "warning",
  REOPENED: "warning",
  STALE: "warning",
  QUARANTINED: "warning",
  WARNING_OR_HIGHER: "warning",

  APPROVED: "success",
  FINALIZED: "success",
  ADVISOR_CONFIRMED: "success",
  DEPARTMENT_FINALIZED: "success",
  DEAN_CONFIRMED: "success",
  SIGNED: "success",
  ANSWERED: "success",
  ACCEPTED: "success",
  OPEN: "success",
  PUBLISHED: "success",
  CONFIRMED: "success",
  PROPOSAL_APPROVED: "success",
  DEFENDED: "success",
  COMPLETED: "success",
  FINAL: "success",
  ACCEPT: "success",
  ELIGIBLE: "success",
  CLEAN: "success",
  CLEAR: "success",
  AGREE: "success",

  LECTURER_REJECTED: "danger",
  CANCELLED: "danger",
  REJECTED: "danger",
  VOID: "danger",
  FAILED: "danger",
  DECLINED: "danger",
  WITHDRAWN: "danger",
  REVOKED: "danger",
  BLOCKED: "danger",
  INFECTED: "danger",
  DECLINE: "danger",
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
  const text = label || STATUS_LABEL[state] || stateLabel[state] || state;
  return (
    <Badge variant={variant} dot={showIcon} className={className}>
      {text}
    </Badge>
  );
}
