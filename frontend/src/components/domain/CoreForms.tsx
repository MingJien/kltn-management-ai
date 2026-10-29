import { useId, useState } from "react";
import type { Review } from "../../api";
import ReviewCommentText from "./ReviewCommentText";
import ThesisStatusBadge from "./ThesisStatusBadge";
import { stateLabel } from "./stateLabels";

export { stateLabel } from "./stateLabels";

export function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString("vi-VN", {timeZone: "Asia/Ho_Chi_Minh"}) : "Chưa đặt";
}

export function Status({value, label}: {value: string; label?: string}) {
  return <ThesisStatusBadge state={value} label={label || stateLabel[value] || value} />;
}

export function Reviews({items}: {items: Review[]}) {
  return <div className="stack">{items.map((item, index) => <div className="core-review" key={`${item.created_at}-${index}`}>
    <strong>{item.reviewer_name}</strong> · {stateLabel[item.decision] || item.decision}
    <p className="core-prewrap"><ReviewCommentText text={item.comment} /></p>
    <small className="text-muted">{formatDate(item.created_at)}</small>
  </div>)}</div>;
}

export function ReviewForm({choices, disabled, onSubmit}: {
  choices: {value: string; label: string}[]; disabled: boolean;
  onSubmit: (decision: string, comment: string) => Promise<boolean>;
}) {
  const id = useId();
  const [decision, setDecision] = useState(choices[0].value);
  const [comment, setComment] = useState("");
  const selected = choices.some(choice=>choice.value===decision) ? decision : choices[0].value;
  return <form className="core-form" onSubmit={async (event) => {
    event.preventDefault();
    if (await onSubmit(selected, comment.trim())) setComment("");
  }}>
    <div className="input-group"><label htmlFor={`${id}-decision`}>Kết quả</label>
      <select className="input" id={`${id}-decision`} value={selected} onChange={event => setDecision(event.target.value)} disabled={disabled}>
        {choices.map(choice => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
      </select>
    </div>
    <div className="input-group"><label htmlFor={`${id}-comment`}>Nhận xét / lý do</label>
      <textarea className="input" id={`${id}-comment`} value={comment} onChange={event => setComment(event.target.value)} required maxLength={2000} disabled={disabled} />
    </div>
    <button className="btn btn-primary" disabled={disabled || !comment.trim()}>Gửi kết quả</button>
  </form>;
}
