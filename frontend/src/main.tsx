import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { ToastProvider } from "./components/ui/Toast";
import { ConfirmHost } from "./components/ui/ConfirmDialog";

/* Design System — import order matters */
import "./styles/tokens.css";
import "./styles/reset.css";
import "./styles/typography.css";
import "./styles/layout.css";
import "./styles/components.css";
import "./styles/content-polish.css";
import "./styles/roster.css";
import "./styles/admin.css";
import "./styles/workflow-clarity.css";
import "./styles/signature.css";
import "./styles/evaluation.css";
import "./styles/lecturer-profile.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter><ToastProvider><App /><ConfirmHost /></ToastProvider></BrowserRouter>
  </React.StrictMode>,
);
