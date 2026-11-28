import type { ReactNode } from "react";

export type BadgeVariant = "neutral" | "primary" | "info" | "success" | "warning" | "danger" | "muted";

interface BadgeProps {
  variant?: BadgeVariant;
  dot?: boolean;
  icon?: ReactNode;
  pill?: boolean;
  className?: string;
  children: ReactNode;
}

/** Semantic status badge aligned with DThU Academic Blue palette. */
export default function Badge({
  variant = "neutral",
  dot = false,
  icon,
  pill = false,
  className = "",
  children,
}: BadgeProps) {
  const classes = [
    "badge",
    `badge-${variant}`,
    pill ? "badge-pill" : "",
    className,
  ].filter(Boolean).join(" ");

  return (
    <span className={classes}>
      {icon ? (
        <span className="inline-flex items-center" aria-hidden="true">{icon}</span>
      ) : dot ? (
        <span className={`status-dot status-dot--${variant}`} aria-hidden="true" />
      ) : null}
      {children}
    </span>
  );
}
