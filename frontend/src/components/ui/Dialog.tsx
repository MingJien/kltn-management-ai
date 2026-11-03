import { X } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import {createPortal} from "react-dom";

const dialogStack:symbol[]=[];
let initialBodyOverflow="";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
  footer?: React.ReactNode;
  busy?: boolean;
}

export default function Dialog({
  open,
  onClose,
  title,
  size = "sm",
  children,
  footer,
  busy = false,
}: DialogProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const busyRef = useRef(busy);
  busyRef.current = busy;

  useEffect(() => {
    if (!open) return;
    const token=Symbol("dialog");
    if(!dialogStack.length)initialBodyOverflow=document.body.style.overflow;
    dialogStack.push(token);
    const previousFocus = document.activeElement as HTMLElement | null;
    const focusables = () => Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]') || []).filter((node) => node.getClientRects().length > 0);
    focusables()[0]?.focus();
    const handleEsc = (e: KeyboardEvent) => {
      if(dialogStack.at(-1)!==token)return;
      if (e.key === "Escape" && !busyRef.current) closeRef.current();
      if (e.key === "Tab") {
        const nodes = focusables();
        const first = nodes[0], last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {e.preventDefault(); last?.focus();}
        else if (!e.shiftKey && document.activeElement === last) {e.preventDefault(); first?.focus();}
      }
    };
    document.addEventListener("keydown", handleEsc);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleEsc);
      const index=dialogStack.indexOf(token);if(index>=0)dialogStack.splice(index,1);
      document.body.style.overflow = dialogStack.length?"hidden":initialBodyOverflow;
      previousFocus?.focus();
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className="dialog-overlay"
      onClick={(e) => { e.stopPropagation(); if (e.target === e.currentTarget && !busy) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-busy={busy}
    >
      <div className={`dialog dialog--${size}`} ref={dialogRef}>
        <div className="dialog__header">
          <h2 id={titleId}>{title}</h2>
          <button
            className="btn btn-ghost btn-icon btn-sm"
            onClick={onClose}
            disabled={busy}
            aria-label="Đóng"
          >
            <X size={18} />
          </button>
        </div>
        <div className="dialog__body">{children}</div>
        {footer && <div className="dialog__footer">{footer}</div>}
      </div>
    </div>,document.body
  );
}
