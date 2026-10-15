import { useState } from "react";
import type { Context, Thesis, WorkAssignment } from "../../api";
import { request } from "../../api";
import type { CoreRun } from "./ThesisDocuments";
import { ReviewForm, Status } from "./CoreForms";

export default function ThesisWork({thesis, assignments, context, busy, run}: {
  thesis: Thesis; assignments: WorkAssignment[]; context: Context; busy: boolean; run: CoreRun;
}) {
  const [studentId, setStudentId] = useState(context.student_id || "");
  const [description, setDescription] = useState("");
  const [output, setOutput] = useState("");
  const active = ["ACTIVE", "PROPOSAL_APPROVED", "IN_PROGRESS", "EXTENDED"].includes(thesis.state);
  const coordinator = thesis.members.some(member => member.student_id === context.student_id && member.is_coordinator);
  const latest = new Map<string, WorkAssignment>();
  for (const assignment of assignments) {
    if ((latest.get(assignment.student_id)?.version_no || 0) < assignment.version_no) latest.set(assignment.student_id, assignment);
  }
  return <section className="stack">
    <h2>Phân công công việc theo sinh viên</h2>
    <p className="text-body-sm text-muted">Lưu sản phẩm từng người và xác nhận của GVHD để làm căn cứ đánh giá cá nhân.</p>
    {thesis.actions.includes("work:submit") && active && <form className="core-form core-version" onSubmit={async event => {
      event.preventDefault();
      if (await run(() => request(`/theses/${thesis.id}/work-assignments`, context.user_id, {method: "POST", body: JSON.stringify({
        student_id: studentId, work_description: description, expected_output: output,
      })}), "Đã gửi phân công công việc cho GVHD.")) {setDescription(""); setOutput("");}
    }}>
      <div className="input-group"><label htmlFor="work-student">Sinh viên thực hiện</label><select className="input" id="work-student" value={studentId} onChange={event => setStudentId(event.target.value)} disabled={busy} required>
        {thesis.members.filter(member => coordinator || member.student_id === context.student_id).map(member => <option key={member.student_id} value={member.student_id}>{member.display_name} ({member.student_code})</option>)}
      </select></div>
      <div className="input-group"><label htmlFor="work-description">Công việc</label><textarea className="input" id="work-description" value={description} onChange={event => setDescription(event.target.value)} maxLength={10000} required disabled={busy} /></div>
      <div className="input-group"><label htmlFor="work-output">Sản phẩm / kết quả dự kiến</label><textarea className="input" id="work-output" value={output} onChange={event => setOutput(event.target.value)} maxLength={10000} required disabled={busy} /></div>
      <button className="btn btn-primary" disabled={busy || !description.trim() || !output.trim() || latest.get(studentId)?.state === "SUBMITTED"}>Gửi phân công</button>
    </form>}
    {assignments.map(assignment => <article className="core-version stack" key={assignment.id}>
      <div className="flex justify-between gap-3"><strong>{assignment.student_name} · v{assignment.version_no}</strong><Status value={assignment.state} /></div>
      <p className="core-prewrap">{assignment.work_description}</p><p className="core-prewrap">Sản phẩm: {assignment.expected_output}</p>
      {assignment.review_comment && <p className="core-review core-prewrap">{assignment.reviewed_by_name}: {assignment.review_comment}</p>}
      {active && thesis.actions.includes("work:review") && assignment.state === "SUBMITTED" && latest.get(assignment.student_id)?.id === assignment.id &&
        <ReviewForm disabled={busy} choices={[{value: "APPROVE", label: "Duyệt phân công"}, {value: "REVISION_REQUIRED", label: "Yêu cầu chỉnh sửa"}]} onSubmit={(decision, comment) => run(() => request(`/theses/${thesis.id}/work-assignments/${assignment.id}/review`, context.user_id, {
          method: "POST", headers: {"If-Match": String(assignment.row_version)}, body: JSON.stringify({decision, comment}),
        }), "Đã lưu nhận xét phân công.")} />}
    </article>)}
    {assignments.length === 0 && <p className="text-muted">Chưa khai phân công công việc.</p>}
  </section>;
}
