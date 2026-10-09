import { useState } from "react";
import type { Context, Lecturer, OpenRound, Requirement, Topic } from "../../api";
import { RequirementEditor } from "./TopicRequirements";
import RegistrationForm from "./RegistrationForm";

export default function TopicEditor({topic, rounds, lecturers, context, busy, onSave, onPropose}: {
  topic?: Topic; rounds: OpenRound[]; lecturers: Lecturer[]; context: Context; busy: boolean;
  onSave: (body: object) => Promise<void>; onPropose?: (body: object) => Promise<void>;
}) {
  const student = context.base_role === "STUDENT";
  const [roundId, setRoundId] = useState(topic?.round_id || rounds[0]?.id || "");
  const [title, setTitle] = useState(topic?.title || "");
  const [description, setDescription] = useState(topic?.description || "");
  const [capacity, setCapacity] = useState(topic?.max_students || 3);
  const [requirements, setRequirements] = useState<Requirement[]>(topic?.requirements || []);
  const [lecturerId, setLecturerId] = useState(topic?.receiving_lecturer_id || "");
  const valid = title.trim().length >= 5 && (topic || roundId) && (!student || lecturerId);
  function body() {
    return {
      ...(!topic ? {round_id: roundId} : {}), title: title.trim(), description,
      ...(!student || !topic ? {max_students: capacity} : {}),
      ...(!student ? {requirements} : {receiving_lecturer_id: lecturerId}),
    };
  }
  return <div className="stack">
    <form className="stack" onSubmit={(event) => {event.preventDefault(); if (valid && !busy) void onSave(body());}}>
      <fieldset className="stack plain-fieldset" disabled={busy}>
        {!topic ? <label>Năm học / đợt đăng ký
          <select className="input" required value={roundId} onChange={(event) => setRoundId(event.target.value)}>
            <option value="">Chọn đợt đang mở</option>
            {rounds.map((round) => <option key={round.id} value={round.id}>{round.label}</option>)}
          </select>
        </label> : <p className="text-caption">{topic.code} · {topic.round_label}</p>}
        <label>Tên đề tài
          <input className="input" required minLength={5} maxLength={500} value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label>Mô tả, mục tiêu và phạm vi
          <textarea className="input" rows={4} maxLength={5000} value={description} onChange={(event) => setDescription(event.target.value)} />
        </label>
        {!student || !topic ? <label>Số sinh viên tối đa
          <select className="input" value={capacity} onChange={(event) => setCapacity(Number(event.target.value))}>
            {[1,2,3].map((n) => <option key={n} value={n}>{n} SV</option>)}
          </select>
          <span className="text-caption">Một SV vẫn có thể gửi đăng ký để GV xét. Có thể bổ sung khi còn chỗ và còn hạn.</span>
        </label> : null}
        {student ? <label>GV mong muốn tiếp nhận
          <select className="input" required value={lecturerId} onChange={(event) => setLecturerId(event.target.value)}>
            <option value="">Chọn GV trong bộ môn</option>
            {lecturers.map((lecturer) => <option key={lecturer.id} value={lecturer.id}>{lecturer.display_name} — {lecturer.lecturer_code}</option>)}
          </select>
          <span className="text-caption">Bộ môn xác nhận hoặc chọn GV phù hợp khi duyệt. GV có quyền từ chối tiếp nhận.</span>
        </label> : <RequirementEditor items={requirements} onChange={setRequirements} />}
        {topic || !student ? <button className="btn btn-primary" type="submit" disabled={busy || !valid}>
          {busy ? "Đang lưu…" : topic ? "Lưu chỉnh sửa" : "Tạo bản nháp"}
        </button> : null}
      </fieldset>
    </form>
    {student && !topic && onPropose && roundId ? <>
      <p className="alert alert-info">Đề xuất bắt đầu bằng đăng ký cá nhân của bạn. Sau khi bộ môn duyệt, các SV khác có thể tự tham gia khi còn chỉ tiêu.</p>
      <RegistrationForm key={roundId} context={context} userId={context.user_id} roundId={roundId} busy={busy}
        disabled={!valid} onSubmit={() => onPropose({...body(), confirm_creator: true})} />
    </> : null}
  </div>;
}
