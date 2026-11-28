import { AlertTriangle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import Dialog from "./Dialog";

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "default";
  busy?: boolean;
}

export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = "Xác nhận",
  cancelLabel = "Hủy bỏ",
  variant = "default",
  busy = false,
}: ConfirmDialogProps) {
  const btnClass = variant === "danger" ? "btn btn-danger" : "btn btn-primary";

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      busy={busy}
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>
            {cancelLabel}
          </button>
          <button type="button" className={btnClass} onClick={onConfirm} disabled={busy}>
            {busy ? "Đang xử lý…" : confirmLabel}
          </button>
        </>
      }
    >
      <div className="confirm-dialog__body">
        {variant !== "default" && (
          <div className={`confirm-dialog__icon confirm-dialog__icon--${variant}`} aria-hidden="true">
            <AlertTriangle size={20} />
          </div>
        )}
        <p>{description}</p>
      </div>
    </Dialog>
  );
}

/* ── Imperative API: `if (await confirmAction({...})) doIt();` ──
   Replaces window.confirm with an accessible, on-brand dialog without forcing
   every caller to own open/close state. Falls back to window.confirm if the
   host is not mounted (e.g. isolated tests). */
export type ConfirmOptions = Pick<ConfirmDialogProps, "title" | "description" | "confirmLabel" | "cancelLabel" | "variant">;
type Pending = { options: ConfirmOptions; resolve: (ok: boolean) => void };

let enqueue: ((pending: Pending) => void) | null = null;

export function confirmAction(options: ConfirmOptions): Promise<boolean> {
  if (!enqueue) return Promise.resolve(window.confirm(options.description));
  return new Promise((resolve) => enqueue!({ options, resolve }));
}

export function ConfirmHost() {
  const [pending, setPending] = useState<Pending | null>(null);
  const current = useRef<Pending | null>(null);

  useEffect(() => {
    enqueue = (next) => {
      current.current?.resolve(false);
      current.current = next;
      setPending(next);
    };
    return () => {
      enqueue = null;
    };
  }, []);

  const settle = (ok: boolean) => {
    current.current?.resolve(ok);
    current.current = null;
    setPending(null);
  };

  return (
    <ConfirmDialog
      open={pending !== null}
      onClose={() => settle(false)}
      onConfirm={() => settle(true)}
      title={pending?.options.title ?? ""}
      description={pending?.options.description ?? ""}
      confirmLabel={pending?.options.confirmLabel}
      cancelLabel={pending?.options.cancelLabel}
      variant={pending?.options.variant}
    />
  );
}
