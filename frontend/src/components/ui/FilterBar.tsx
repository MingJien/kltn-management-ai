import { Search, X } from "lucide-react";
import type { ReactNode } from "react";

export interface FilterChip {
  key: string;
  label: string;
  onRemove: () => void;
}

interface FilterBarProps {
  search?: {
    value: string;
    onChange: (value: string) => void;
    placeholder: string;
    ariaLabel: string;
    id?: string;
  };
  children?: ReactNode;
  chips?: FilterChip[];
  onClearAll?: () => void;
  summary?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

/** Unified toolbar for search, compact select filters, active filter chips, and quick clear. */
export default function FilterBar({
  search,
  children,
  chips = [],
  onClearAll,
  summary,
  actions,
  className = "",
}: FilterBarProps) {
  return (
    <section className={`filter-bar ${className}`.trim()} aria-label="Bộ lọc và tìm kiếm">
      <div className="filter-bar__row">
        {search && (
          <div className="filter-bar__search">
            <Search size={16} className="filter-bar__search-icon" aria-hidden="true" />
            <input
              id={search.id}
              type="search"
              className="input filter-bar__search-input"
              value={search.value}
              onChange={(e) => search.onChange(e.target.value)}
              placeholder={search.placeholder}
              aria-label={search.ariaLabel}
            />
            {search.value && (
              <button
                type="button"
                className="filter-bar__clear-input"
                aria-label="Xóa từ khóa tìm kiếm"
                onClick={() => search.onChange("")}
              >
                <X size={14} aria-hidden="true" />
              </button>
            )}
          </div>
        )}
        {children && <div className="filter-bar__controls">{children}</div>}
        {(summary || actions) && (
          <div className="filter-bar__meta">
            {summary && <span className="filter-bar__summary">{summary}</span>}
            {actions}
          </div>
        )}
      </div>

      {chips.length > 0 && (
        <div className="filter-bar__chips" aria-label="Bộ lọc đang áp dụng">
          {chips.map((chip) => (
            <span className="filter-chip" key={chip.key}>
              <span>{chip.label}</span>
              <button
                type="button"
                className="filter-chip__remove"
                aria-label={`Bỏ lọc ${chip.label}`}
                onClick={chip.onRemove}
              >
                <X size={12} aria-hidden="true" />
              </button>
            </span>
          ))}
          {onClearAll && (
            <button type="button" className="btn btn-ghost btn-sm filter-bar__reset" onClick={onClearAll}>
              Xóa bộ lọc
            </button>
          )}
        </div>
      )}
    </section>
  );
}
