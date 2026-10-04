import type { Requirement } from "../../api";
const labels: Record<Requirement["requirement_type"], string> = {
  PREFERRED_GPA: "GPA mong muốn", SKILL: "Kỹ năng", TECHNOLOGY: "Công nghệ", KNOWLEDGE: "Kiến thức", OTHER: "Yêu cầu khác",
};
export function RequirementList({ items }: { items: Requirement[] }) {
  return items.length ? <ul className="requirement-list">{items.map((item, i) => <li key={i}>
    <strong>{labels[item.requirement_type]}: </strong>
    {item.requirement_type === "PREFERRED_GPA" ? `từ ${item.preferred_gpa?.toFixed(2)}/4` : item.value_text}
    {item.requirement_type === "PREFERRED_GPA" && item.value_text ? ` — ${item.value_text}` : ""}
  </li>)}</ul> : <p className="text-body-sm">Không có yêu cầu bổ sung.</p>;
}
export function RequirementEditor({ items, onChange }: {items: Requirement[]; onChange: (items: Requirement[]) => void}) {
  function change(index: number, fields: Partial<Requirement>) {
    onChange(items.map((row, i) => i === index ? {...row, ...fields} : row));
  }
  return <fieldset className="registration-fieldset stack"><legend>Yêu cầu bổ sung của GV</legend>
    <p className="text-body-sm">Để GV xem xét mức phù hợp; điều kiện đăng ký chính thức vẫn theo quy định của đợt.</p>
    {items.map((item, i) => <div className="requirement-editor" key={i}>
      <label>Loại yêu cầu<select className="input" value={item.requirement_type} onChange={(e) => change(i, {requirement_type: e.target.value as Requirement["requirement_type"], preferred_gpa: e.target.value === "PREFERRED_GPA" ? 3 : null})}>
        {Object.entries(labels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      {item.requirement_type === "PREFERRED_GPA" ? <label>GPA (thang 4)<input className="input" type="number" min={0} max={4} step={0.01} required value={item.preferred_gpa ?? ""} onChange={(e) => change(i, {preferred_gpa: e.target.value === "" ? null : Number(e.target.value)})}/></label> : null}
      <label>{item.requirement_type === "PREFERRED_GPA" ? "Ghi chú" : "Nội dung"}<input className="input" maxLength={1000} required={item.requirement_type !== "PREFERRED_GPA"} value={item.value_text} onChange={(e) => change(i, {value_text: e.target.value})}/></label>
      <button type="button" className="btn btn-ghost" onClick={() => onChange(items.filter((_, index) => index !== i))}>Bỏ yêu cầu</button>
    </div>)}
    <button type="button" className="btn btn-secondary" disabled={items.length >= 10} onClick={() => onChange([...items, {requirement_type: "SKILL", value_text: "", preferred_gpa: null}])}>+ Thêm yêu cầu</button>
  </fieldset>;
}
