import { useEffect, useState } from "react";
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
  useEffect(() => {
    if (topic) return;
    if (rounds.length === 1) {
      setRoundId(rounds[0].id);
    } else if (!rounds.some((round) => round.id === roundId)) {
      setRoundId("");
    }
  }, [topic, rounds, roundId]);
  const valid = title.trim().length >= 5 && (topic || roundId) && (!student || lecturerId);
  const soleOpenRound = !topic && rounds.length === 1 ? rounds[0] : null;
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
        {!topic ? (
          <div className="input-row">
            <div className="input-group">
              <label htmlFor="topic-round">Đợt đăng ký</label>
              {soleOpenRound ? <>
                <div id="topic-round" className="topic-edit__round" aria-live="polite">{soleOpenRound.label}</div>
                <span className="input-group__hint">Hệ thống tự chọn vì hiện chỉ có một đợt đang mở.</span>
              </> : <>
                <select id="topic-round" className="input" required value={roundId} onChange={(event) => setRoundId(event.target.value)}>
                  <option value="">Chọn đợt đăng ký đang mở</option>
                  {rounds.map((round) => <option key={round.id} value={round.id}>{round.label}</option>)}
                </select>
                <span className="input-group__hint">Chỉ cần chọn khi có từ hai đợt đang mở.</span>
              </>}
            </div>
            <div className="input-group">
              <label htmlFor="topic-capacity">Số sinh viên tối đa</label>
              <select id="topic-capacity" className="input" value={capacity} onChange={(event) => setCapacity(Number(event.target.value))}>
                {[1, 2, 3].map((n) => <option key={n} value={n}>{n} SV</option>)}
              </select>

            </div>
          </div>
        ) : <p className="text-caption topic-edit__code">{topic.code} · {topic.round_label}</p>}
        {!topic ? null : !student ? (
          <div className="input-group">
            <label htmlFor="topic-capacity">Số sinh viên tối đa</label>
            <select id="topic-capacity" className="input" value={capacity} onChange={(event) => setCapacity(Number(event.target.value))}>
              {[1, 2, 3].map((n) => <option key={n} value={n}>{n} SV</option>)}
            </select>
            <span className="input-group__hint">Có thể bổ sung khi còn chỗ và còn hạn đăng ký.</span>
          </div>
        ) : null}
        <div className="input-group">
          <label htmlFor="topic-title">Tên đề tài</label>
          <input id="topic-title" className="input" required minLength={5} maxLength={500} value={title}
            onChange={(event) => setTitle(event.target.value)} />
          <span className="input-group__counter">Tối thiểu 5 ký tự · {title.trim().length} / 500</span>
        </div>
        <div className="input-group">
          <label htmlFor="topic-description">Mô tả, mục tiêu và phạm vi</label>
          <textarea id="topic-description" className="input" rows={5} maxLength={5000} value={description}
            onChange={(event) => setDescription(event.target.value)} />
          <span className="input-group__counter">{description.length} / 5.000</span>
        </div>
        {student ? (
          <div className="input-group">
            <label htmlFor="topic-lecturer">GV mong muốn tiếp nhận</label>
            <select id="topic-lecturer" className="input" required value={lecturerId} onChange={(event) => setLecturerId(event.target.value)}>
              <option value="">Chọn GV trong bộ môn</option>
              {lecturers.map((lecturer) => <option key={lecturer.id} value={lecturer.id}>{lecturer.display_name} — {lecturer.lecturer_code}</option>)}
            </select>
            <span className="input-group__hint">Bộ môn xác nhận hoặc chọn GV phù hợp khi duyệt. GV có quyền từ chối tiếp nhận.</span>
          </div>
        ) : <RequirementEditor items={requirements} onChange={setRequirements} />}
        {topic || !student ? (
          <div className="topic-edit__actions">
            <button className="btn btn-primary" type="submit" disabled={busy || !valid}>
              {busy ? "Đang lưu…" : topic ? "Lưu chỉnh sửa" : "Tạo bản nháp"}
            </button>
          </div>
        ) : null}
      </fieldset>
    </form>
    {student && !topic && onPropose && roundId ? <>
      <p className="alert alert-info">Đề xuất bắt đầu bằng đăng ký cá nhân của bạn. Sau khi bộ môn duyệt, các SV khác có thể tự tham gia khi còn chỉ tiêu.</p>
      <RegistrationForm key={roundId} context={context} userId={context.user_id} roundId={roundId} busy={busy}
        disabled={!valid} onSubmit={() => onPropose({...body(), confirm_creator: true})} />
    </> : null}
  </div>;
}
