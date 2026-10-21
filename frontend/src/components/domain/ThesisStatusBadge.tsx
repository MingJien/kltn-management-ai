import {
  FileEdit, Send, Eye, UserCheck, UserX, RotateCcw, Check, CheckCheck, X,
  ShieldCheck, Building2, Printer, Award, PenTool, Ban, Clock, CheckCircle,
  Loader, Play, AlertTriangle, HelpCircle, Database, MessageCircle,
  ThumbsUp, ThumbsDown,
} from "lucide-react";

type BadgeVariant = "info" | "warning" | "success" | "danger" | "neutral" | "primary";

interface StateConfig {
  variant: BadgeVariant;
  icon: React.ComponentType<{ size?: number }>;
  label?: string;
}

/**
 * Maps every business state from state-models.md to a badge variant + icon.
 * UI changes ONLY the visual presentation, not the state names or transitions.
 */
const STATE_MAP: Record<string, StateConfig> = {
  // Topic & Registration states
  DRAFT: { variant: "info", icon: FileEdit },
  SUBMITTED: { variant: "warning", icon: Send },
  UNDER_REVIEW: { variant: "warning", icon: Eye },
  LECTURER_ACCEPTED: { variant: "warning", icon: UserCheck },
  LECTURER_REJECTED: { variant: "danger", icon: UserX },
  RETURNED: { variant: "info", icon: RotateCcw },
  APPROVED: { variant: "success", icon: Check },
  FINALIZED: { variant: "success", icon: CheckCheck },
  CANCELLED: { variant: "danger", icon: X },
  // Thesis lifecycle states
  ADVISOR_CONFIRMED: { variant: "success", icon: ShieldCheck },
  DEPARTMENT_FINALIZED: { variant: "success", icon: Building2 },
  PRINT_READY: { variant: "neutral", icon: Printer },
  DEAN_CONFIRMED: { variant: "success", icon: Award },
  SIGNED: { variant: "success", icon: PenTool },
  VOID: { variant: "danger", icon: Ban },
  IN_PROGRESS: { variant: "warning", icon: Clock },
  COMPLETED: { variant: "success", icon: CheckCircle },
  // AI / Async states
  QUEUED: { variant: "neutral", icon: Loader },
  RUNNING: { variant: "warning", icon: Play },
  FAILED: { variant: "danger", icon: AlertTriangle },
  NO_EVIDENCE: { variant: "neutral", icon: HelpCircle },
  RETRIEVAL_ONLY: { variant: "info", icon: Database },
  ANSWERED: { variant: "success", icon: MessageCircle },
  // Consent states
  ACCEPTED: { variant: "success", icon: ThumbsUp },
  PENDING: { variant: "warning", icon: Clock },
  DECLINED: { variant: "danger", icon: ThumbsDown },
};

interface ThesisStatusBadgeProps {
  state: string;
  showIcon?: boolean;
  className?: string;
}

export default function ThesisStatusBadge({
  state,
  showIcon = true,
  className = "",
}: ThesisStatusBadgeProps) {
  const config = STATE_MAP[state] || { variant: "neutral" as BadgeVariant, icon: HelpCircle };
  const Icon = config.icon;

  return (
    <span className={`badge badge-${config.variant} ${className}`}>
      {showIcon && <Icon size={12} />}
      {({DRAFT:"Bản nháp",SUBMITTED:"Đã gửi",APPROVED:"Đã duyệt",RETURNED:"Trả lại để sửa",REJECTED:"Từ chối",LOCKED:"Đã khóa",CANCELLED:"Đã hủy",LECTURER_ACCEPTED:"GV đã chấp nhận",LECTURER_REJECTED:"GV từ chối",FINALIZED:"Đã tiếp nhận chính thức",ACCEPTED:"Đã xác nhận",PENDING:"Chờ xác nhận",DECLINED:"Không tham gia"} as Record<string,string>)[state] || state}
    </span>
  );
}
