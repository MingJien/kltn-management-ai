import type {ProgressReport, Thesis} from "../../api";
import type {CoreRun} from "./ThesisDocuments";
import FileReviewWorkspace from "./FileReviewWorkspace";

export default function ProgressReviewWorkspace({thesis, report, userId, run, onClose}: {
  thesis: Thesis; report: ProgressReport; userId: string; run: CoreRun; onClose: () => void;
}) {
  const path = `/theses/${thesis.id}/progress-reports/${report.id}`;
  return <FileReviewWorkspace userId={userId} run={run} onClose={onClose} target={{
    versionId: report.evidence_document_version_id || report.id, fileName: report.evidence_file_name || "", versionNo: report.version_no,
    submittedBy: report.submitted_by_name, rowVersion: report.row_version,
    annotationsPath: path + "/annotations", downloadPath: path + "/evidence", reviewPath: path + "/review",
    label: "Báo cáo tiến độ", reviews: report.reviews,
    legacyCacheKey: `kltn-progress-review:${userId}:${report.id}:${report.evidence_document_version_id}`,
    choices: thesis.actions.includes("progress:review") ? [{value:"REVISION_REQUIRED", label:"Yêu cầu sửa và nộp lại"}, {value:"CONFIRM", label:"Xác nhận tiến độ"}]
      : [{value:"COMMENT_ONLY", label:"Góp ý chéo"}],
  }} />;
}
