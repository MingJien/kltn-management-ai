import type { ReactNode } from "react";
import { formatDate } from "./CoreForms";
import "../../styles/version-timeline.css";

type Version = {id: string; version_no: number; file_name: string; submitted_at: string; submitted_by_name: string; reviews: unknown[]};
export default function VersionTimeline<T extends Version>({versions, render}: {versions: T[]; render: (version: T, index: number) => ReactNode}) {
  if (!versions.length) return null;
  return <div className="version-timeline">
    <div className="version-current-label">BẢN MỚI NHẤT · v{versions[0].version_no}</div>
    {render(versions[0], 0)}
    {versions.length > 1 && <details className="version-history"><summary>Lịch sử cập nhật ({versions.length - 1} bản trước)</summary>
      <div className="version-history-list">{versions.slice(1).map((version, index) => <details className="version-history-item" key={version.id}>
        <summary><span className="version-history-number">v{version.version_no}</span><span className="version-history-caption">{version.file_name}<small>{version.submitted_by_name} · {formatDate(version.submitted_at)}</small></span>
          <span className="version-review-count">{version.reviews.length ? `${version.reviews.length} phản hồi` : "Chưa có phản hồi"}</span></summary>
        {render(version, index + 1)}
      </details>)}</div>
    </details>}
  </div>;
}
