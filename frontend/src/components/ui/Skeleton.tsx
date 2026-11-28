interface SkeletonProps {
  width?: string;
  height?: string;
  className?: string;
  variant?: "text" | "circle" | "rect";
}

export function Skeleton({
  width,
  height = "1em",
  className = "",
  variant = "text",
}: SkeletonProps) {
  return (
    <span
      className={`skeleton skeleton--${variant} ${className}`}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}

export function SkeletonTable({
  rows = 5,
  cols = 4,
}: {
  rows?: number;
  cols?: number;
}) {
  return (
    <div className="skeleton-table" role="status" aria-label="Đang tải dữ liệu">
      <div className="skeleton-table__header">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} height="12px" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div className="skeleton-table__row" key={r}>
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} height="14px" />
          ))}
        </div>
      ))}
    </div>
  );
}

/** Card placeholder. Wrap groups in an element with role="status" + aria-label so the
 *  loading state is announced once, not per card. */
export function SkeletonCard() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <Skeleton height="16px" width="60%" />
      <Skeleton height="12px" width="90%" />
      <Skeleton height="12px" width="75%" />
      <Skeleton height="32px" width="100px" />
    </div>
  );
}
