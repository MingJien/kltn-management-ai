import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

export type ToastVariant = "success" | "error" | "info" | "warning";

interface ToastMessage {
  id: number;
  text: string;
  variant: ToastVariant;
}

interface ToastContextType {
  toast: (text: string, variant?: ToastVariant) => void;
}

const ToastContext = createContext<ToastContextType>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

/* Imperative entry point for code outside React render (event handlers in deep trees). */
let push: ((text: string, variant: ToastVariant) => void) | null = null;
export function toast(text: string, variant: ToastVariant = "success") {
  push?.(text, variant);
}

let nextId = 0;
const DURATION: Record<ToastVariant, number | null> = {
  success: 4000,
  info: 4000,
  warning: 7000,
  error: null, // Critical/error toasts persist until manually dismissed
};

const ICONS: Record<ToastVariant, React.ReactNode> = {
  success: <CheckCircle2 size={18} />,
  error: <AlertTriangle size={18} />,
  warning: <AlertTriangle size={18} />,
  info: <Info size={18} />,
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);
  const timers = useRef(new Map<number, number>());

  const dismiss = useCallback((id: number) => {
    window.clearTimeout(timers.current.get(id));
    timers.current.delete(id);
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  const schedule = useCallback((id: number, variant: ToastVariant) => {
    window.clearTimeout(timers.current.get(id));
    const ms = DURATION[variant];
    if (ms !== null) {
      timers.current.set(id, window.setTimeout(() => dismiss(id), ms));
    }
  }, [dismiss]);

  const show = useCallback((text: string, variant: ToastVariant = "success") => {
    const id = ++nextId;
    setMessages((prev) => [...prev.slice(-2), { id, text, variant }]);
    schedule(id, variant);
  }, [schedule]);

  useEffect(() => {
    push = show;
    const pending = timers.current;
    return () => {
      push = null;
      pending.forEach((t) => window.clearTimeout(t));
    };
  }, [show]);

  return (
    <ToastContext.Provider value={{ toast: show }}>
      {children}
      {createPortal(
        <div className="toast-container" aria-live="polite">
          {messages.map((msg) => (
            <div
              key={msg.id}
              role={msg.variant === "error" ? "alert" : "status"}
              className={`toast toast--${msg.variant}`}
              onMouseEnter={() => window.clearTimeout(timers.current.get(msg.id))}
              onMouseLeave={() => schedule(msg.id, msg.variant)}
            >
              <span className="toast__icon" aria-hidden="true">{ICONS[msg.variant]}</span>
              <span className="toast__text">{msg.text}</span>
              <button type="button" className="toast__dismiss" onClick={() => dismiss(msg.id)} aria-label="Đóng thông báo">
                <X size={14} />
              </button>
            </div>
          ))}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
}
