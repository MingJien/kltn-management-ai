import {useEffect, useState} from "react";
import {Link} from "react-router-dom";
import {request} from "../../api";
import {errorMessage} from "../../errors";
import DefensePrintHistory from "./DefensePrintHistory";
import DefensePrintPreview from "./DefensePrintPreview";

type Round = {id:string;code:string};
type Row = {name:string;code:string;class_name:string;grade:string|null;status:string;slot_id:string;council:string;has_birth_date:boolean};
type Register = {code:string;issues:string[];rows:Row[];unscheduled?:{name:string;code:string;thesis_id:string}[]};

export default function DefenseRegister({rounds,refresh}: {rounds:Round[];refresh:number}) {
  const [selected,setSelected] = useState("");
  const [data,setData] = useState<Register|null>(null);
  const [error,setError] = useState("");
  const [history,setHistory] = useState(0);
  const [course,setCourse] = useState("");
  const [custom,setCustom] = useState("");
  const [search,setSearch] = useState("");
  const [count,setCount] = useState(30);
  const endpoint = `/defense/round-register/${selected}`;
  const code = course === "other" ? custom.trim().toUpperCase() : course;
  const validCode = /^[A-Z0-9][A-Z0-9._-]{0,31}$/.test(code);

  useEffect(() => {
    setData(null);
    setError("");
    if (!selected) return;
    const controller = new AbortController();
    void request<Register>(endpoint,"",{signal:controller.signal})
      .then(result=>{if(!controller.signal.aborted)setData(result);})
      .catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));});
    return () => controller.abort();
  },[selected,endpoint,refresh]);

  const filtered = data?.rows.filter(row=>`${row.name} ${row.code} ${row.class_name}`.toLocaleLowerCase("vi").includes(search.trim().toLocaleLowerCase("vi"))) ?? [];
  return <details className="defense-operation">
    <summary>Bảng điểm toàn đợt · Mẫu 10 và 11</summary>
    <div className="stack">
      <p>Đối chiếu mỗi sinh viên một dòng, gồm kết quả phiên chính và phiên bổ sung ở các hội đồng trong đợt.</p>
      <label>Đợt bảo vệ<select className="input" value={selected} onChange={e=>{setSelected(e.target.value);setCourse("");setCustom("");setSearch("");setCount(30);}}>
        <option value="">Chọn đợt</option>{rounds.map(round=><option key={round.id} value={round.id}>{round.code}</option>)}
      </select></label>
      {error&&<p role="alert" className="alert alert-danger">{error}</p>}
      {selected&&!data&&!error&&<p role="status">Đang đối chiếu kết quả toàn đợt…</p>}
      {data&&<>
        <p>Danh sách dưới đây gồm sinh viên đã xếp lịch bảo vệ trong đợt; không tự ghi không đạt cho SV chưa xếp lịch.</p>
        {!!data.unscheduled?.length&&<aside className="defense-blockers"><strong>{data.unscheduled.length} SV đủ điều kiện chưa xếp lịch — cần đối chiếu trước khi phát hành</strong><ul>{data.unscheduled.map(row=><li key={row.code}><Link to={`/evaluation/${row.thesis_id}`}>{row.name} · {row.code}</Link></li>)}</ul></aside>}
        {!!data.issues.length&&<aside className="defense-blockers"><strong>Việc cần hoàn tất trước khi xuất</strong><ul>{data.issues.map(issue=><li key={issue}>{issue}</li>)}</ul></aside>}
        {!!data.rows.length&&<>
          <p><strong>{data.rows.length}</strong> sinh viên · {data.rows.filter(row=>row.grade!==null).length} đã có điểm</p>
          <label>Tìm theo họ tên, MSSV hoặc lớp<input className="input" value={search} onChange={e=>{setSearch(e.target.value);setCount(30);}}/></label>
          <div className="defense-results" tabIndex={0} role="region" aria-label="Kết quả bảo vệ toàn đợt"><table><thead><tr><th>Sinh viên</th><th>Lớp</th><th>Hội đồng xử lý</th><th>Điểm</th><th>Trạng thái</th><th>Thông tin xuất</th></tr></thead>
            <tbody>{filtered.slice(0,count).map(row=><tr key={row.code}><td>{row.name}<br/><small>{row.code}</small></td><td>{row.class_name||"Chưa có"}</td><td>{row.council}</td><td>{row.grade??"—"}</td><td>{row.status}</td>
              <td>{!row.class_name||!row.has_birth_date?<Link to={`/defense?focus=${row.slot_id}&tab=results`}>{[!row.class_name&&"Lớp",!row.has_birth_date&&"Ngày sinh"].filter(Boolean).join(", ")} cần bổ sung</Link>:"Đủ"}</td></tr>)}</tbody></table></div>
          {!filtered.length&&<p>Không tìm thấy sinh viên theo từ khóa.</p>}
          {filtered.length>count&&<button className="btn btn-secondary" onClick={()=>setCount(count+30)}>Xem thêm sinh viên</button>}
          {search&&<small>Bộ lọc chỉ dùng để kiểm tra trên màn hình. Tệp xuất luôn gồm cả đợt.</small>}
        </>}
        {!data.issues.length&&<>
          {data.rows.every(row=>row.class_name)&&<DefensePrintPreview endpoint={`${endpoint}/forms/10`} name="Mau-10-Bang-diem.docx" label="Mẫu 10 · Bảng điểm tổng hợp" record onRecord={()=>setHistory(v=>v+1)}/>}
          {data.rows.every(row=>row.has_birth_date)&&<div className="stack">
            <label>Mã học phần của bảng Mẫu 11<select className="input" value={course} onChange={e=>setCourse(e.target.value)}>
              <option value="">Chọn mã học phần</option><option value="IN4299N">IN4299N · Gợi ý từ mẫu Khoa</option><option value="other">Nhập mã khác</option>
            </select></label>
            {course==="other"&&<label>Mã học phần khác<input className="input" value={custom} maxLength={32} onChange={e=>setCustom(e.target.value)} aria-invalid={!!custom&&!validCode}/>
              <small>Dùng chữ, số, dấu chấm, gạch nối hoặc gạch dưới.</small></label>}
            {validCode&&<DefensePrintPreview key={code} endpoint={`${endpoint}/forms/11?course_code=${encodeURIComponent(code)}`} name="Mau-11-Bang-diem.xlsx" label={`Mẫu 11 · ${code}`} record onRecord={()=>setHistory(v=>v+1)}/>}
          </div>}
        </>}
        <DefensePrintHistory key={selected} endpoint={`${endpoint}/prints`} revision={history}/>
      </>}
    </div>
  </details>;
}
