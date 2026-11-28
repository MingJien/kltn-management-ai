import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, Check, CheckCircle2, Clock, FileText, RotateCcw, Send, XCircle } from "lucide-react";

export type JourneyStageState = "done" | "current" | "upcoming";

export interface JourneyStage {
  id: string;
  title: string;
  statusText: string;
  meta?: string;
  state: JourneyStageState;
  to?: string;
}

/** Connected 5-stage horizontal (desktop) / vertical (mobile) Thesis Journey timeline. */
export function ThesisJourney({
  stages,
  ariaLabel = "Hành trình khóa luận",
  compact = false,
}: {
  stages: JourneyStage[];
  ariaLabel?: string;
  compact?: boolean;
}) {
  return (
    <ol className={`thesis-journey ${compact ? "thesis-journey--compact" : ""}`.trim()} aria-label={ariaLabel}>
      {stages.map((stage, index) => {
        const content = (
          <>
            <span className="thesis-journey__marker" aria-hidden="true">
              {stage.state === "done" ? <Check size={compact ? 15 : 18} strokeWidth={2.5} /> : index + 1}
            </span>
            <span className="thesis-journey__copy">
              <strong className="thesis-journey__title">{stage.title}</strong>
              <span className="thesis-journey__status">{stage.statusText}</span>
              {stage.meta ? <span className="thesis-journey__meta">{stage.meta}</span> : null}
            </span>
          </>
        );

        return (
          <li
            key={stage.id}
            className={`thesis-journey__step thesis-journey__step--${stage.state}`}
            aria-current={stage.state === "current" ? "step" : undefined}
          >
            {stage.to ? (
              <Link className="thesis-journey__step-link" to={stage.to}>
                {content}
              </Link>
            ) : (
              <div className="thesis-journey__step-link">{content}</div>
            )}
          </li>
        );
      })}
    </ol>
  );
}

export type TimelineTone = "neutral" | "info" | "primary" | "success" | "warning" | "danger";

export interface ActivityTimelineItem {
  id: string;
  title: string;
  actor?: string;
  timestamp?: string;
  note?: string;
  tone?: TimelineTone;
  badge?: ReactNode;
  icon?: ReactNode;
  extra?: ReactNode;
}

const DEFAULT_ICONS: Record<TimelineTone, ReactNode> = {
  neutral: <FileText size={14} />,
  info: <Send size={14} />,
  primary: <Clock size={14} />,
  success: <CheckCircle2 size={14} />,
  warning: <RotateCcw size={14} />,
  danger: <XCircle size={14} />,
};

export function inferTimelineTone(actionOrState: string): TimelineTone {
  const key = actionOrState.toUpperCase();
  if (/(REJECT|CANCEL|WITHDRAW|REVOKE|VOID|FAIL|DELETE|DECLINE|LOCK)/.test(key)) return "danger";
  if (/(RETURN|REVISION|WARNING|EXTEND|REOPEN|ALERT)/.test(key)) return "warning";
  if (/(APPROV|FINALIZ|ACCEPT|CONFIRM|COMPLETE|SIGN|OPEN|CLEAN|PASS|ELIGIBLE)/.test(key)) return "success";
  if (/(SUBMIT|CREATE|START|SEND|UPLOAD|ASSIGN|REGISTER)/.test(key)) return "info";
  return "neutral";
}

/** Vertical audit & workflow processing history timeline with semantic markers and optional collapse. */
export function ActivityTimeline({
  items,
  ariaLabel = "Lịch sử xử lý",
  initialLimit,
  emptyText = "Chưa có lịch sử xử lý.",
}: {
  items: ActivityTimelineItem[];
  ariaLabel?: string;
  initialLimit?: number;
  emptyText?: string;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!items.length) {
    return (
      <p className="text-caption m-0">
        <AlertCircle size={13} aria-hidden="true" className="timeline-empty-icon" />
        {emptyText}
      </p>
    );
  }

  const shouldCollapse = typeof initialLimit === "number" && initialLimit > 0 && items.length > initialLimit;
  const visibleItems = shouldCollapse && !expanded ? items.slice(0, initialLimit) : items;

  return (
    <div>
      <ol className="activity-timeline" aria-label={ariaLabel}>
        {visibleItems.map((item) => {
          const tone = item.tone ?? "neutral";
          return (
            <li key={item.id} className="activity-timeline__item">
              <div className="activity-timeline__rail" aria-hidden="true">
                <span className={`activity-timeline__marker activity-timeline__marker--${tone}`}>
                  {item.icon ?? DEFAULT_ICONS[tone]}
                </span>
                <span className="activity-timeline__connector" />
              </div>
              <div className="activity-timeline__body">
                <div className="activity-timeline__head">
                  <strong className="activity-timeline__title">{item.title}</strong>
                  {item.badge}
                </div>
                {(item.actor || item.timestamp) && (
                  <div className="activity-timeline__meta">
                    {item.actor ? <span>{item.actor}</span> : null}
                    {item.actor && item.timestamp ? <span aria-hidden="true">·</span> : null}
                    {item.timestamp ? <time>{item.timestamp}</time> : null}
                  </div>
                )}
                {item.note ? <p className="activity-timeline__note">{item.note}</p> : null}
                {item.extra}
              </div>
            </li>
          );
        })}
      </ol>
      {shouldCollapse ? (
        <button
          type="button"
          className="btn btn-ghost btn-sm activity-timeline__toggle"
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? "Thu gọn lịch sử" : `Xem thêm ${items.length - initialLimit!} mốc trước đó`}
        </button>
      ) : null}
    </div>
  );
}
