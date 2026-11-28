import { FolderOpen } from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  compact?: boolean;
  children?: ReactNode;
}

export default function EmptyState({
  title,
  description,
  icon,
  compact = false,
  children,
}: EmptyStateProps) {
  return (
    <div className={`empty-state ${compact ? "empty-state--compact" : ""}`.trim()}>
      {icon ?? <FolderOpen aria-hidden="true" />}
      <h3>{title}</h3>
      {description ? <p>{description}</p> : null}
      {children ? <div className="empty-state__action">{children}</div> : null}
    </div>
  );
}
