import { lazy, Suspense, useState } from "react";
import { FileSearch } from "lucide-react";
import type {FileReviewTarget} from "./FileReviewWorkspace";
import type {CoreRun} from "./ThesisDocuments";
const Workspace = lazy(() => import("./FileReviewWorkspace"));

export default function FileReviewButton({target, userId, run, disabled}: {
  target: FileReviewTarget; userId: string; run: CoreRun; disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return <><button type="button" className="btn btn-primary" disabled={disabled} onClick={() => setOpen(true)}>
    <FileSearch size={16} /> Xem tệp & nhận xét</button>
    {open && <Suspense fallback={<p role="status">Đang mở không gian nhận xét…</p>}><Workspace target={target} userId={userId} run={run} onClose={() => setOpen(false)} /></Suspense>}
  </>;
}
