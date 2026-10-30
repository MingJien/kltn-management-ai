import { FolderOpen } from "lucide-react";
import type { ReactNode } from "react";

export default function EmptyState({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <FolderOpen aria-hidden="true" />
      <h3>{title}</h3>
      {description ? <p>{description}</p> : null}
      {children ? <div className="empty-state__action">{children}</div> : null}
    </div>
  );
}