import { useState } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import type { Context } from "../../api";

interface AppShellProps {
  context: Context | null;
  children: React.ReactNode;
  onLogout: () => void;
}

export default function AppShell({ context, children, onLogout }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar
        context={context}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="app-shell__main">
        <Header onToggleSidebar={() => setSidebarOpen((prev) => !prev)} onLogout={onLogout} />
        <main className="app-shell__content">
          {children}
        </main>
      </div>
    </div>
  );
}
