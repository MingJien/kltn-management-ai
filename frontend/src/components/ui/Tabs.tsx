import { Check } from "lucide-react";
import { useRef, type KeyboardEvent, type ReactNode } from "react";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  icon?: ReactNode;
  completed?: boolean;
  disabled?: boolean;
}

interface TabsProps {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  ariaLabel: string;
  variant?: "underline" | "rail";
  idPrefix?: string;
  className?: string;
  /** Render semantic navigation buttons (aria-pressed) instead of ARIA tablist when E2E/workflow views act as view switches. */
  asButtons?: boolean;
}

/** WAI-ARIA compliant Tabs supporting both section underline navigation and numbered workflow rails. */
export default function Tabs({
  items,
  activeId,
  onChange,
  ariaLabel,
  variant = "underline",
  idPrefix = "ui-tab",
  className = "",
  asButtons = false,
}: TabsProps) {
  const listRef = useRef<HTMLDivElement>(null);

  function focusByIndex(index: number) {
    const enabled = items.filter((t) => !t.disabled);
    if (!enabled.length) return;
    const clamped = ((index % enabled.length) + enabled.length) % enabled.length;
    const targetId = enabled[clamped].id;
    onChange(targetId);
    const el = listRef.current?.querySelector<HTMLButtonElement>(`[data-tab-id="${targetId}"]`);
    el?.focus();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLButtonElement>, currentId: string) {
    const enabled = items.filter((t) => !t.disabled);
    const idx = enabled.findIndex((t) => t.id === currentId);
    if (idx < 0) return;

    if (e.key === "ArrowRight") {
      e.preventDefault();
      focusByIndex(idx + 1);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      focusByIndex(idx - 1);
    } else if (e.key === "Home") {
      e.preventDefault();
      focusByIndex(0);
    } else if (e.key === "End") {
      e.preventDefault();
      focusByIndex(enabled.length - 1);
    }
  }

  const rootClass = variant === "rail" ? "ui-tabs ui-tabs--rail" : "ui-tabs ui-tabs--underline";

  return (
    <div
      ref={listRef}
      role={asButtons ? "navigation" : "tablist"}
      aria-label={ariaLabel}
      className={`${rootClass} ${className}`.trim()}
    >
      {items.map((item, index) => {
        const selected = item.id === activeId;
        const tabClass = [
          "ui-tabs__tab",
          selected ? "ui-tabs__tab--active" : "",
          item.completed ? "ui-tabs__tab--done" : "",
        ].filter(Boolean).join(" ");

        return (
          <button
            key={item.id}
            id={`${idPrefix}-${item.id}`}
            data-tab-id={item.id}
            type="button"
            role={asButtons ? undefined : "tab"}
            aria-selected={asButtons ? undefined : selected}
            aria-pressed={asButtons ? selected : undefined}
            tabIndex={asButtons ? 0 : selected ? 0 : -1}
            disabled={item.disabled}
            className={tabClass}
            onClick={() => onChange(item.id)}
            onKeyDown={(e) => handleKeyDown(e, item.id)}
          >
            {variant === "rail" ? (
              <span className="ui-tabs__step-num" aria-hidden="true">
                {item.completed ? <Check size={13} strokeWidth={2.5} /> : index + 1}
              </span>
            ) : item.icon ? (
              <span className="ui-tabs__icon" aria-hidden="true">{item.icon}</span>
            ) : null}
            <span className="ui-tabs__label">{item.label}</span>
            {typeof item.count === "number" && (
              <>
                {asButtons && <span className="sr-only"> (</span>}
                <span className="ui-tabs__count">{item.count}</span>
                {asButtons && <span className="sr-only">)</span>}
              </>
            )}
          </button>
        );
      })}
    </div>
  );
}
