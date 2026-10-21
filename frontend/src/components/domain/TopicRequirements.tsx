import { X } from "lucide-react";
import type { Requirement } from "../../api";
const labels: Record<Requirement["requirement_type"], string> = {
  PREFERRED_GPA: "GPA mong muốn", SKILL: "Kỹ năng", TECHNOLOGY: "Công nghệ", KNOWLEDGE: "Kiến thức", OTHER: "Yêu cầu khác",
};
export function RequirementList({ items, preview = false }: { items: Requirement[]; preview?: boolean }) {
  const visible = preview ? items.slice(0, 2) : items;
  return items.length ? <ul className={preview ? "requirement-preview" : "requirement-list requirement-list--detailed"}>
    {visible.map((item, i) => <li key={i}>
      <strong>{labels[item.requirement_type]}</strong>
      <span>{item.requirement_type === "PREFERRED_GPA" ? `Từ ${item.preferred_gpa?.toFixed(2)}/4` : item.value_text}
        {item.requirement_type === "PREFERRED_GPA" && item.value_text ? ` — ${item.value_text}` : ""}</span>
    </li>)}
    {preview && items.length > visible.length ? <li className="requirement-preview__more">+{items.length - visible.length} yêu cầu khác</li> : null}
  </ul> : <p className="text-body-sm text-muted">Không có yêu cầu bổ sung.</p>;
}
export function RequirementEditor({ items, onChange }: {items: Requirement[]; onChange: (items: Requirement[]) => void}) {
  function change(index: number, fields: Partial<Requirement>) {
    onChange(items.map((row, i) => i === index ? {...row, ...fields} : row));
  }
  return <fieldset className="registration-fieldset stack"><legend>Yêu cầu bổ sung của GV</legend>
    <p className="text-body-sm text-muted">Để GV xem xét mức phù hợp; điều kiện đăng ký chính thức vẫn theo quy định của đợt.</p>
    {items.map((item, i) => <div className="requirement-editor" key={i}>
      <div className="input-group">
        <label htmlFor={`req-type-${i}`}>Loại yêu cầu</label>
        <select id={`req-type-${i}`} className="input" value={item.requirement_type} onChange={(e) => change(i, {requirement_type: e.target.value as Requirement["requirement_type"], preferred_gpa: e.target.value === "PREFERRED_GPA" ? 3 : null})}>
          {Object.entries(labels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </div>
      {item.requirement_type === "PREFERRED_GPA" ? (
        <div className="input-group">
          <label htmlFor={`req-gpa-${i}`}>GPA (thang 4)</label>
          <input id={`req-gpa-${i}`} className="input" type="number" min={0} max={4} step={0.01} required value={item.preferred_gpa ?? ""} onChange={(e) => change(i, {preferred_gpa: e.target.value === "" ? null : Number(e.target.value)})} />
        </div>
      ) : null}
      <div className={"input-group" + (item.requirement_type === "PREFERRED_GPA" ? "" : " requirement-editor__wide")}>
        <label htmlFor={`req-text-${i}`}>{item.requirement_type === "PREFERRED_GPA" ? "Ghi chú" : "Nội dung"}</label>
        <input id={`req-text-${i}`} className="input" maxLength={1000} required={item.requirement_type !== "PREFERRED_GPA"} value={item.value_text} onChange={(e) => change(i, {value_text: e.target.value})} />
      </div>
      <button type="button" className="requirement-editor__remove" onClick={() => onChange(items.filter((_, index) => index !== i))} aria-label="Bỏ yêu cầu này" title="Bỏ yêu cầu này">
        <X size={15} aria-hidden="true" />
      </button>
    </div>)}
    <div>
      <button type="button" className="btn btn-secondary" disabled={items.length >= 10} onClick={() => onChange([...items, {requirement_type: "SKILL", value_text: "", preferred_gpa: null}])}>+ Thêm yêu cầu</button>
    </div>
  </fieldset>;
}
