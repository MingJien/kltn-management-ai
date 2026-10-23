import { useCallback, useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import type { KeyboardEvent } from "react";
import type { Context } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";

type Assignment = {round_id:string; round_code:string; assignment_type:string};
type PreviewRow = {line:number; student_code:string; display_name:string; email:string; department_code:string; class_name:string; major_code:string};
type Preview = {sha256:string; count:number; rows:PreviewRow[]};
type CatalogEntry = {department_code:string; department_name:string; major_code:string; major_name:string};
type RosterEntry = {snapshot_id:string; student_id:string; student_code:string; display_name:string; email:string; department_code:string; class_name:string|null; major_code:string|null; account_status:string; account_activated?:boolean; state:string; version:number; evidence_ref:string; confirmed_at:string|null};
type ImportResult = {new_accounts:number; submitted:number; unchanged:number; snapshot_ids:string[]};

function normalized(value:string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
}

function accountActivated(row:RosterEntry) {
  // Existing API processes may still serve the response shape from before account_activated was added.
  return typeof row.account_activated === "boolean"
    ? row.account_activated : row.account_status === "ACTIVE" || row.account_status === "LOCKED";
}

function StudentPicker({label,rows,value,onChange,placeholder,disabled}:{
  label:string;rows:RosterEntry[];value:string;onChange:(id:string)=>void;placeholder:string;disabled?:boolean;
}) {
  const [query,setQuery] = useState("");
  const matches = rows.filter(row=>normalized(`${row.student_code} ${row.display_name} ${row.email}`).includes(normalized(query.trim())));
  const shown = matches.slice(0,30);
  const chosen = rows.find(row=>row.student_id===value);
  if (chosen && !shown.some(row=>row.student_id===value)) shown.unshift(chosen);
  return <div className="roster-student-picker">
    <span className="roster-student-picker__label">{label}</span>
    <div className="roster-student-picker__controls">
      <input className="input" type="search" aria-label={`Tìm ${label.toLowerCase()}`} value={query}
        onChange={event=>setQuery(event.target.value)} placeholder="Tìm MSSV, họ tên hoặc email" disabled={disabled} />
      <select className="input" aria-label={label} value={value} onChange={event=>onChange(event.target.value)} disabled={disabled}>
        <option value="">{placeholder}</option>
        {shown.map(row=><option key={row.student_id} value={row.student_id}>{row.student_code} · {row.display_name}</option>)}
      </select>
    </div>
    {matches.length>30?<p className="text-caption">Đang hiện 30/{matches.length} kết quả; nhập thêm MSSV hoặc tên để thu hẹp.</p>:null}
    {!matches.length?<p className="text-caption">Không tìm thấy sinh viên phù hợp trong đợt này.</p>:null}
  </div>;
}

export default function RosterPage({context}: {context:Context}) {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [roundId, setRoundId] = useState("");
  const [file, setFile] = useState<File|null>(null);
  const [preview, setPreview] = useState<Preview|null>(null);
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [departmentError, setDepartmentError] = useState("");
  const [reference, setReference] = useState("");
  const [basis, setBasis] = useState("");
  const [revokeBasis, setRevokeBasis] = useState("");
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [rosterQuery,setRosterQuery] = useState("");
  const [activationFilter,setActivationFilter] = useState("all");
  const [revokeStudent, setRevokeStudent] = useState("");
  const [revokeReason, setRevokeReason] = useState("");
  const [specialStudent, setSpecialStudent] = useState("");
  const [specialRef, setSpecialRef] = useState("");
  const [specialReason, setSpecialReason] = useState("");
  const [specialClauseOne, setSpecialClauseOne] = useState(false);
  const [correctionStudent, setCorrectionStudent] = useState("");
  const [correctionCode, setCorrectionCode] = useState("");
  const [correctionName, setCorrectionName] = useState("");
  const [correctionClass, setCorrectionClass] = useState("");
  const [correctionMajor, setCorrectionMajor] = useState("");
  const [correctionRef, setCorrectionRef] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [activePanel, setActivePanel] = useState("review");

  const permissions = useMemo(()=>assignments.filter(a=>a.round_id===roundId).map(a=>a.assignment_type),[assignments,roundId]);
  const canImport = permissions.includes("ELIGIBILITY_IMPORTER");
  const canConfirm = permissions.includes("ELIGIBILITY_VERIFIER");
  const refreshRoster = useCallback(async (id:string)=>{
    if (id) setRoster(await request<RosterEntry[]>(`/rounds/${id}/roster`,context.user_id));
    else setRoster([]);
  },[context.user_id]);

  useEffect(()=>{void request<Assignment[]>("/me/round-assignments",context.user_id)
    .then(rows=>{setAssignments(rows); if(rows.length) setRoundId(rows[0].round_id);})
    .catch(cause=>setError(errorMessage(cause)));},[context.user_id]);
  useEffect(()=>{
    void request<CatalogEntry[]>("/me/roster-catalog",context.user_id)
      .then(rows=>{setCatalog(rows);setDepartmentError("");})
      .catch(()=>setDepartmentError("Chưa tải được danh mục bộ môn–ngành. Hãy làm mới trang rồi thử lại."));
  },[context.user_id]);
  useEffect(()=>{
    setPreview(null);setSelected([]);setRevokeStudent("");setSpecialStudent("");setCorrectionStudent("");
    void refreshRoster(roundId).catch(cause=>setError(errorMessage(cause)));
  },[roundId,refreshRoster]);

  async function run(action:()=>Promise<unknown>,message:string) {
    setBusy(true);setError("");setNotice("");
    try {const result=await action();await refreshRoster(roundId);setNotice(typeof result==="string"?result:message);}
    catch(cause){setError(errorMessage(cause));}
    finally{setBusy(false);}
  }

  function fileHeaders(chosen:File) {
    const name = chosen.name.toLowerCase();
    if (!name.endsWith(".csv") && !name.endsWith(".xlsx")) {
      throw new Error("Chỉ nhận tệp CSV UTF-8 hoặc Excel .xlsx; hãy chuyển bảng Word sang một trong hai định dạng này.");
    }
    return {"Content-Type":"application/octet-stream",
      "X-File-Name":name.endsWith(".xlsx")?"roster.xlsx":"roster.csv"};
  }

  const filteredRoster = roster.filter(row=>(activationFilter==="all" || (activationFilter==="activated")===accountActivated(row))
    && normalized(`${row.student_code} ${row.display_name} ${row.email}`).includes(normalized(rosterQuery.trim())));
  const pending = filteredRoster.filter(row=>row.state==="SUBMITTED");
  const allPendingSelected = pending.length > 0 && pending.every(row=>selected.includes(row.snapshot_id));
  const pendingCount = roster.filter(row=>row.state==="SUBMITTED").length;
  const confirmedCount = roster.filter(row=>row.state==="CONFIRMED").length;
  const specialIsDemo = roster.some(row=>row.student_id===specialStudent && /^(SYN-|E2E-)/.test(row.student_code));
  const panels = [
    {id:"review",label:"Danh sách & xác nhận",detail:`${pendingCount} chờ xác nhận`,visible:canConfirm},
    {id:"import",label:"Nhập danh sách",detail:"CSV hoặc Excel",visible:canImport},
    {id:"special",label:"Ngoại lệ Hiệu trưởng",detail:"Theo quyết định cá biệt",visible:canConfirm},
    {id:"correction",label:"Đính chính hồ sơ",detail:"Theo văn bản Khoa",visible:canConfirm},
  ].filter(panel=>panel.visible);
  const selectedPanel = panels.some(panel=>panel.id===activePanel)?activePanel:(panels[0]?.id||"");
  useEffect(()=>{setSelected([]);},[roundId,activationFilter,rosterQuery]);

  function handlePanelKeyDown(event:KeyboardEvent<HTMLDivElement>) {
    if (!panels.length) return;
    const currentIndex=panels.findIndex(panel=>panel.id===selectedPanel);
    let nextIndex=currentIndex;
    if (event.key==="ArrowRight") nextIndex=(currentIndex+1)%panels.length;
    else if (event.key==="ArrowLeft") nextIndex=(currentIndex-1+panels.length)%panels.length;
    else if (event.key==="Home") nextIndex=0;
    else if (event.key==="End") nextIndex=panels.length-1;
    else return;
    event.preventDefault();
    const nextPanel=panels[nextIndex];
    setActivePanel(nextPanel.id);
    document.getElementById(`roster-tab-${nextPanel.id}`)?.focus();
  }

  return <><PageHeader title="Danh sách đủ điều kiện" description="Nhập, xác nhận và quản lý kết quả sinh viên theo từng đợt" />
    <div className="stack roster-page">

      {error&&selectedPanel!=="import"?<p role="alert" className="alert alert-danger">{error}</p>:null}
      {notice?<p role="status" className="alert alert-success">{notice}</p>:null}

      {assignments.length?<section className="roster-context card" aria-label="Phạm vi danh sách">
        <div className="roster-context__copy"><span className="roster-eyebrow">PHẠM VI ĐANG LÀM VIỆC</span>
          <strong>Danh sách theo đợt KLTN</strong><p>Chọn một đợt để xem, nhập hoặc cập nhật kết quả sinh viên.</p></div>
        <label className="input-group roster-context__select">Đợt KLTN<select className="input" value={roundId} onChange={e=>setRoundId(e.target.value)}>
          {[...new Map(assignments.map(a=>[a.round_id,a])).values()].map(a=><option key={a.round_id} value={a.round_id}>{a.round_code}</option>)}
        </select></label>
        <div className="roster-metrics" aria-label="Tình trạng danh sách">
          <div><span>Tổng sinh viên</span><strong>{roster.length}</strong></div>
          <div><span>Chờ xác nhận</span><strong>{pendingCount}</strong></div>
          <div><span>Đã xác nhận</span><strong>{confirmedCount}</strong></div>
        </div>
      </section>:null}
      {!assignments.length?<section className="card"><div className="card-body">Bạn chưa được Khoa phân công nhập hoặc xác nhận danh sách cho đợt nào.</div></section>:null}

      {panels.length?<>
        <div className="roster-tabs-wrap"><div className="roster-tabs" role="tablist" aria-label="Thao tác danh sách sinh viên" onKeyDown={handlePanelKeyDown}>
          {panels.map(panel=><button key={panel.id} id={`roster-tab-${panel.id}`} type="button" role="tab"
            aria-selected={selectedPanel===panel.id} aria-controls={`roster-panel-${panel.id}`} tabIndex={selectedPanel===panel.id?0:-1}
            className={`roster-tab${selectedPanel===panel.id?" roster-tab--active":""}`} onClick={()=>setActivePanel(panel.id)}>
            <span>{panel.label}</span><small>{panel.detail}</small>
          </button>)}
        </div></div>

        <div id={`roster-panel-${selectedPanel}`} className="roster-tabpanel" role="tabpanel" aria-labelledby={`roster-tab-${selectedPanel}`} tabIndex={0}>
          {selectedPanel==="review"?<section className="card roster-section-card">
            <div className="roster-section-heading"><div><span className="roster-eyebrow">QUY TRÌNH THƯỜNG XUYÊN</span><h2>Danh sách và xác nhận</h2>
              <p>Đối chiếu căn cứ, xác nhận kết quả theo đợt và theo dõi trạng thái tài khoản.</p></div>
              <span className="badge badge-info">{pendingCount} chờ xác nhận</span></div>
            <div className="card-body stack">
              <div className="grid grid-auto roster-filter-grid">
                <label className="input-group">Kích hoạt tài khoản<select className="input" value={activationFilter} onChange={e=>setActivationFilter(e.target.value)}>
                  <option value="all">Tất cả</option><option value="activated">Đã kích hoạt</option><option value="not-activated">Chưa kích hoạt</option>
                </select></label>
                <label className="input-group">Tìm sinh viên<input className="input" type="search" value={rosterQuery} onChange={e=>setRosterQuery(e.target.value)} placeholder="MSSV, họ tên hoặc email" /></label>
              </div>
              <p className="text-caption">Đang hiện {filteredRoster.length}/{roster.length} sinh viên thuộc đợt đã chọn. “Chọn tất cả” chỉ áp dụng cho kết quả đang hiện.</p>
              <label className="input-group roster-basis-field">Căn cứ đối chiếu danh sách<input className="input" minLength={3} value={basis} onChange={e=>setBasis(e.target.value)} placeholder="Demo: DEMO-XAC-NHAN-DOT-1-2026" /></label>
              <div className="roster-selection-toolbar"><span>{selected.length?`Đã chọn ${selected.length} kết quả`:"Chọn các kết quả đã đối chiếu trước khi xác nhận."}</span>
                <div className="account-actions"><button className="btn btn-secondary" disabled={!pending.length||busy}
                  onClick={()=>setSelected(allPendingSelected?[]:pending.map(row=>row.snapshot_id))}>{allPendingSelected?"Bỏ chọn tất cả":"Chọn tất cả chờ xác nhận"}</button>
                  <button className="btn btn-primary" disabled={!selected.length||basis.trim().length<3||busy}
                    onClick={()=>void run(async()=>{await request(`/rounds/${roundId}/roster/confirm`,context.user_id,
                      {method:"POST",body:JSON.stringify({snapshot_ids:selected,basis_ref:basis})});setSelected([]);},
                      `Đã xác nhận ${selected.length} sinh viên.`)}>Xác nhận đã đối chiếu</button></div>
              </div>
              <div className="table-scroll"><table className="account-table"><thead><tr><th>Chọn</th><th>MSSV</th><th>Họ tên</th><th>Email</th><th>Bộ môn</th><th>Ngành</th><th>Trạng thái</th><th>Tài khoản</th></tr></thead>
                <tbody>{filteredRoster.map(row=><tr key={row.snapshot_id}><td>{row.state==="SUBMITTED"?<input type="checkbox" aria-label={`Chọn ${row.student_code}`}
                  checked={selected.includes(row.snapshot_id)} onChange={e=>setSelected(current=>e.target.checked?[...current,row.snapshot_id]:current.filter(x=>x!==row.snapshot_id))}/>:null}</td>
                  <td>{row.student_code}</td><td>{row.display_name}</td><td>{row.email}</td>
                  <td>{row.department_code}</td><td>{row.major_code||"—"}{catalog.find(item=>item.department_code===row.department_code&&item.major_code===row.major_code)?.major_name
                    ? ` · ${catalog.find(item=>item.department_code===row.department_code&&item.major_code===row.major_code)?.major_name}`:""}</td>
                  <td>{row.state}</td><td>{accountActivated(row)?"Đã kích hoạt":"Chưa kích hoạt"}{row.account_status==="LOCKED"?" · Đã khóa":""}</td></tr>)}</tbody></table></div>
              {!filteredRoster.length?<p className="text-muted">Không có sinh viên khớp bộ lọc.</p>:null}
              <details className="roster-accordion roster-accordion--danger">
                <summary><span><strong>Thu hồi kết quả đã xác nhận</strong><small>Chỉ dùng khi có căn cứ cần thu hồi; hồ sơ cũ vẫn được giữ.</small></span><span className="badge badge-danger">Thao tác cần thận trọng</span></summary>
                <div className="roster-accordion__body stack">
                  <StudentPicker label="Sinh viên cần thu hồi" rows={roster.filter(r=>r.state==="CONFIRMED")}
                    value={revokeStudent} onChange={setRevokeStudent} placeholder="Chọn sinh viên đã xác nhận" disabled={busy} />
                  <div className="grid grid-auto">
                    <label className="input-group">Văn bản nguồn thu hồi<input className="input" minLength={3} value={revokeBasis} onChange={e=>setRevokeBasis(e.target.value)} placeholder="Demo: DEMO-THU-HOI-DOT-1-2026" disabled={busy} /></label>
                    <label className="input-group">Lý do<input className="input" minLength={5} value={revokeReason} onChange={e=>setRevokeReason(e.target.value)} placeholder="Nêu lý do và nội dung đối chiếu" disabled={busy} /></label>
                  </div>
                  <div><button className="btn btn-destructive" disabled={!revokeStudent||revokeReason.trim().length<5||revokeBasis.trim().length<3||busy}
                    onClick={()=>void run(async()=>{await request(`/rounds/${roundId}/roster/revoke`,context.user_id,{method:"POST",
                      body:JSON.stringify({student_id:revokeStudent,reason:revokeReason,basis_ref:revokeBasis})});setRevokeStudent("");setRevokeReason("");setRevokeBasis("");},
                      "Đã thu hồi quyền tham gia; hồ sơ cũ được giữ để rà soát.")}>Thu hồi quyền tham gia</button></div>
                </div>
              </details>
            </div>
          </section>:null}

          {selectedPanel==="import"?<section className="card roster-section-card">
            <div className="roster-section-heading"><div><span className="roster-eyebrow">BƯỚC 1 · ĐƯA DANH SÁCH VÀO HỆ THỐNG</span><h2>Nhập danh sách đã được Khoa chấp thuận</h2>
              <p>Kiểm tra tệp và xem trước dữ liệu trước khi nhập vào đợt đã chọn.</p></div><span className="badge badge-primary">CSV · XLSX</span></div>
            <div className="card-body stack">
              <div className="roster-form-grid">
                <label className="input-group">Tệp danh sách<input id="roster-file-input" className="input" type="file" accept=".csv,.xlsx" onChange={e=>{setFile(e.target.files?.[0]||null);setPreview(null);setError("");setNotice("");}} /></label>
                {file && <div className="flex items-center gap-2" style={{margin: "var(--space-1) 0"}}>
                  <span className="text-body-sm font-semibold">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
                  <button type="button" className="btn btn-ghost btn-sm" title="Hủy chọn tệp" onClick={() => {
                    setFile(null); setPreview(null);
                    const el = document.getElementById("roster-file-input") as HTMLInputElement | null;
                    if (el) el.value = "";
                  }}><X size={14} aria-hidden="true" style={{marginRight: 4}} /> Xóa tệp đã chọn</button>
                </div>}
                <label className="input-group">Mã/số văn bản nguồn<input id="roster-reference" className="input" required minLength={3} maxLength={500} value={reference} onChange={e=>{setReference(e.target.value);setError("");}} placeholder="Demo: DEMO-DS-SV-DOT-1-2026" /></label>
              </div>
              <div className="roster-help-note"><strong>Mã bộ môn trong Excel</strong>
                <p>Cột này xác định bộ môn quản lý sinh viên và phạm vi đề tài, GVHD; hãy điền đúng mã đã có trong hệ thống. Không dùng mã giả lập cho danh sách thật.</p>
                <p>{departmentError||(!catalog.length?"Chưa có cặp bộ môn–ngành đang hoạt động; chưa thể nhập.":
                  `Đã có ${new Set(catalog.map(item=>item.department_code)).size} bộ môn và ${catalog.length} ngành để đối chiếu.`)}</p>
                <p>Mã BM-* là mã nội bộ trong danh mục Khoa, không phải mã bộ môn chính thức của Trường. Mỗi dòng Excel cần đủ MSSV, họ tên, email, mã bộ môn, lớp, mã ngành; cặp mã phải đúng danh mục.</p>
                <details><summary>Xem mã bộ môn và ngành được chấp nhận</summary><div className="table-scroll"><table className="account-table"><thead><tr><th>Mã bộ môn</th><th>Tên bộ môn</th><th>Mã ngành</th><th>Tên ngành</th></tr></thead><tbody>
                  {catalog.map(item=><tr key={`${item.department_code}-${item.major_code}`}><td>{item.department_code}</td><td>{item.department_name}</td><td>{item.major_code}</td><td>{item.major_name}</td></tr>)}
                </tbody></table></div></details>
                <a href="/templates/danh-sach-sinh-vien-kltn-mau.xlsx" download>Tải Excel mẫu (dữ liệu giả lập, mã hợp lệ)</a>
              </div>
              <div className="roster-help-note"><strong>Căn cứ nhập danh sách</strong><p>Với dữ liệu giả lập, dùng <strong>DEMO-DS-SV-DOT-1-2026</strong>. Khi dùng dữ liệu thật, ghi số văn bản; nếu không có số, ghi tên văn bản, đơn vị và ngày ban hành.</p></div>
              <div className="account-actions"><button className="btn btn-secondary" disabled={!file||!catalog.length||busy} onClick={()=>{if(!file)return;void run(async()=>{
                const data=await request<Preview>(`/rounds/${roundId}/roster/preview`,context.user_id,
                  {method:"POST",body:file,headers:fileHeaders(file)});setPreview(data);
              },"Đã kiểm định dạng và đối chiếu dữ liệu hiện có. Hãy kiểm tra trước khi nhập.");}}>Kiểm tra tệp</button>
                <button className="btn btn-primary" disabled={!file||!preview||busy}
                  onClick={()=>{if(!file||!preview)return;
                    if(reference.trim().length<3){setError("Nhập mã/số văn bản nguồn (ít nhất 3 ký tự) trước khi nhập danh sách.");document.getElementById("roster-reference")?.focus();return;}
                    void run(async()=>{
                    const result=await request<ImportResult>(`/rounds/${roundId}/roster?reference=${encodeURIComponent(reference.trim())}`,context.user_id,
                      {method:"POST",body:file,headers:{...fileHeaders(file),"X-Preview-SHA256":preview.sha256}});
                    setPreview(null);setFile(null);setSelected(result.snapshot_ids);
                    if(canConfirm)setActivePanel("review");
                    return `Đã nhập ${result.submitted} kết quả chờ xác nhận, tạo ${result.new_accounts} tài khoản; ${result.unchanged} dòng đã có.`;
                  },"Đã nhập danh sách.");}}>Nhập sau khi kiểm</button></div>
              <p role="status" className="text-caption">{!file?"Chọn tệp CSV UTF-8 hoặc Excel .xlsx (tối đa 2 MB).":
                !preview?"Nhấn “Kiểm tra tệp” và chờ bảng xem trước; chỉ khi kiểm tra thành công mới có thể nhập.":
                reference.trim().length<3?"Đã xem trước tệp. Nhập mã/số văn bản nguồn (ít nhất 3 ký tự) để hoàn tất.":
                `Đã xem trước ${preview.count} sinh viên. Kiểm tra các dòng rồi nhấn “Nhập sau khi kiểm”.`}</p>
              {error?<p role="alert" className="alert alert-danger">{error}</p>:null}
              {preview?<div className="roster-preview stack"><div><span className="roster-eyebrow">ĐÃ KIỂM TRA · CHƯA NHẬP</span><h3>Xem trước: {preview.count} sinh viên</h3></div>
                <div className="table-scroll"><table className="account-table"><thead><tr><th>Dòng</th><th>MSSV</th><th>Họ tên</th><th>Email</th><th>Mã bộ môn</th><th>Lớp</th><th>Mã ngành</th></tr></thead>
                  <tbody>{preview.rows.map(row=><tr key={row.line}><td>{row.line}</td><td>{row.student_code}</td><td>{row.display_name}</td>
                    <td>{row.email}</td><td>{row.department_code} · {catalog.find(item=>item.department_code===row.department_code)?.department_name||"?"}</td><td>{row.class_name}</td>
                    <td>{row.major_code} · {catalog.find(item=>item.department_code===row.department_code&&item.major_code===row.major_code)?.major_name||"?"}</td></tr>)}</tbody></table></div>
              </div>:null}
            </div>
          </section>:null}

          {selectedPanel==="special"?<section className="card roster-section-card">
            <div className="roster-section-heading"><div><span className="roster-eyebrow">NGOẠI LỆ · CHỈ DÙNG KHI CÓ QUYẾT ĐỊNH</span><h2>Ghi nhận quyết định đặc biệt của Hiệu trưởng</h2>
              <p>Ghi nhận ngoại lệ ngưỡng tín chỉ/GPA theo quyết định cá biệt đã ký.</p></div><span className="badge badge-warning">Trường hợp hiếm</span></div>
            <div className="card-body stack">
              <div className="roster-policy-note"><strong>Phạm vi ngoại lệ</strong><p>QĐ5964 chỉ cho phép ngoại lệ đối với ngưỡng tín chỉ/GPA ở khoản 2 Điều 2. Hồ sơ thật cần quyết định cá biệt đã ký và phải đối chiếu khoản 1; không nhập chi tiết kỷ luật hoặc án tích.</p></div>
              <StudentPicker label="Sinh viên được xét ngoại lệ" rows={roster.filter(r=>r.state!=="CONFIRMED")} value={specialStudent} onChange={setSpecialStudent} placeholder="Chọn sinh viên chưa được xác nhận" disabled={busy} />
              <div className="roster-form-grid">
                <label className="input-group">Số quyết định của Hiệu trưởng<input className="input" value={specialRef} onChange={e=>setSpecialRef(e.target.value)} maxLength={500} placeholder="Demo: DEMO-QD-HT-001" disabled={busy} /></label>
                <label className="input-group">Lý do đối chiếu<input className="input" value={specialReason} onChange={e=>setSpecialReason(e.target.value)} maxLength={2000} placeholder="Demo: Ngoại lệ ngưỡng GPA theo quyết định mô phỏng" disabled={busy} /></label>
              </div>
              <div className="roster-help-note"><strong>Hồ sơ demo và hồ sơ thật</strong><p>Chỉ dùng <strong>DEMO-QD-HT-001</strong> với sinh viên giả lập. QĐ5964 là quy định chung, không thay cho quyết định ngoại lệ đã ký.</p></div>
              <label className="roster-check-row"><input type="checkbox" checked={specialClauseOne} onChange={e=>setSpecialClauseOne(e.target.checked)} disabled={busy} />
                <span>{specialIsDemo?"Tình huống demo: giả định đã đối chiếu khoản 1 và quyết định mô phỏng":"Đã kiểm khoản 1 Điều 2 QĐ5964 và quyết định gốc"}</span></label>
              <div><button className="btn btn-primary" disabled={!specialStudent||specialRef.trim().length<3||specialReason.trim().length<5||!specialClauseOne||busy}
                onClick={()=>void run(async()=>{await request(`/rounds/${roundId}/roster/special-decision`,context.user_id,{method:"POST",
                  body:JSON.stringify({student_id:specialStudent,official_ref:specialRef.trim(),reason:specialReason.trim(),clause_1_verified:specialClauseOne})});
                  setSpecialStudent("");setSpecialRef("");setSpecialReason("");setSpecialClauseOne(false);},
                  "Đã ghi nhận kết quả theo quyết định đặc biệt; phiên bản cũ được giữ.")}>Ghi nhận ngoại lệ</button></div>
            </div>
          </section>:null}

          {selectedPanel==="correction"?<section className="card roster-section-card">
            <div className="roster-section-heading"><div><span className="roster-eyebrow">QUẢN TRỊ HỒ SƠ · CÓ LƯU DẤU VẾT</span><h2>Đính chính thông tin theo văn bản Khoa</h2>
              <p>Sửa thông tin định danh trong hồ sơ sinh viên khi có căn cứ chính thức.</p></div><span className="badge badge-neutral">Thao tác quản trị</span></div>
            <div className="card-body stack">
              <div className="roster-policy-note roster-policy-note--neutral"><strong>Thông tin thuộc chức năng này</strong><p>Chỉ sửa MSSV, họ tên, lớp và ngành. Email, mật khẩu và quyền truy cập được quản lý tại mục Quản trị tài khoản.</p></div>
              <StudentPicker label="Sinh viên cần đính chính" rows={roster} value={correctionStudent} onChange={id=>{
                const row=roster.find(r=>r.student_id===id);setCorrectionStudent(id);
                setCorrectionCode(row?.student_code||"");setCorrectionName(row?.display_name||"");
                setCorrectionClass(row?.class_name||"");setCorrectionMajor(row?.major_code||"");
              }} placeholder="Chọn sinh viên" disabled={busy} />
              {correctionStudent?<div className="roster-form-grid">
                <label className="input-group">MSSV<input className="input" value={correctionCode} onChange={e=>setCorrectionCode(e.target.value)} /></label>
                <label className="input-group">Họ tên<input className="input" value={correctionName} onChange={e=>setCorrectionName(e.target.value)} /></label>
                <label className="input-group">Lớp<input className="input" value={correctionClass} onChange={e=>setCorrectionClass(e.target.value)} /></label>
                <label className="input-group">Ngành ({roster.find(row=>row.student_id===correctionStudent)?.department_code})
                  <select className="input" value={correctionMajor} onChange={e=>setCorrectionMajor(e.target.value)}>
                    {!correctionMajor?<option value="">Chọn ngành</option>:null}
                    {!catalog.some(item=>item.department_code===roster.find(row=>row.student_id===correctionStudent)?.department_code&&item.major_code===correctionMajor)
                      && correctionMajor?<option value={correctionMajor}>{correctionMajor} · Mã cũ chưa xác minh</option>:null}
                    {catalog.filter(item=>item.department_code===roster.find(row=>row.student_id===correctionStudent)?.department_code)
                      .map(item=><option key={item.major_code} value={item.major_code}>{item.major_code} · {item.major_name}</option>)}
                  </select></label>
              </div>:<p className="text-caption">Chọn sinh viên để hiện các thông tin được phép đính chính.</p>}
              <div className="roster-form-grid">
                <label className="input-group">Văn bản Khoa làm căn cứ<input className="input" minLength={3} maxLength={500} value={correctionRef} onChange={e=>setCorrectionRef(e.target.value)} placeholder="Demo: DEMO-DINH-CHINH-001" /></label>
                <label className="input-group">Lý do đính chính<input className="input" minLength={5} maxLength={1000} value={correctionReason} onChange={e=>setCorrectionReason(e.target.value)} placeholder="Nêu trường sai, giá trị đúng và căn cứ đối chiếu" /></label>
              </div>
              <div className="roster-help-note"><strong>Căn cứ và lưu vết</strong><p>Với dữ liệu giả lập, dùng <strong>DEMO-DINH-CHINH-001</strong>. Hồ sơ thật cần căn cứ Khoa; hệ thống lưu người sửa, thời điểm và lý do.</p></div>
              <div><button className="btn btn-primary" disabled={!correctionStudent||correctionRef.trim().length<3||correctionReason.trim().length<5||busy}
                onClick={()=>void run(async()=>{
                  await request(`/rounds/${roundId}/roster/${correctionStudent}`,context.user_id,
                    {method:"PATCH",body:JSON.stringify({student_code:correctionCode,display_name:correctionName,
                      class_name:correctionClass,major_code:correctionMajor,
                      basis_ref:correctionRef.trim(),reason:correctionReason.trim()})});
                  return "Đã đính chính hồ sơ và lưu dấu vết.";
                }, "Đã đính chính thông tin.")}>Lưu đính chính</button></div>
            </div>
          </section>:null}
        </div>
      </>:null}

      {!canConfirm&&roundId?<section className="card"><div className="card-body stack"><h2>Trạng thái danh sách</h2>
        <p>{roster.length} sinh viên; {pending.length} kết quả đang chờ người được giao xác nhận.</p></div></section>:null}
    </div>
  </>;
}
