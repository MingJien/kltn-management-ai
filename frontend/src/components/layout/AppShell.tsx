import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import type { Context } from "../../api";

interface AppShellProps {
  context: Context;
  children: React.ReactNode;
  onLogout: () => void;
}

const COLLAPSE_KEY = "kltn.sidebar.collapsed";

export default function AppShell({ context, children, onLogout }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  useEffect(() => {
    if (!sidebarOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSidebarOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [sidebarOpen]);
  const [collapsed, setCollapsed] = useState(() => {
    try { return window.localStorage.getItem(COLLAPSE_KEY) === "1"; } catch { return false; }
  });

  useEffect(() => {
    try { window.localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0"); } catch { /* bỏ qua */ }
  }, [collapsed]);

  return (
    <div className={"app-shell " + (collapsed ? "app-shell--collapsed" : "")}>
      <a className="skip-link" href="#main-content">Đến nội dung chính</a>
      <Sidebar
        context={context}
        isOpen={sidebarOpen}
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((prev) => !prev)}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="app-shell__main">
        <Header
          context={context}
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
          onLogout={onLogout}
        />
        <main className="app-shell__content" id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
