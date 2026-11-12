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
type RosterEntry = {snapshot_id:string; student_id:string; student_code:string; display_name:string; email:string; department_code:string; class_name:string|null; birth_date?:string|null; major_code:string|null; account_status:string; account_activated?:boolean; state:string; version:number; evidence_ref:string; confirmed_at:string|null; registration_submitted:boolean; registration_submitted_at:string|null; mail_status?:string|null; delivery_mode?:string|null; current_delivery_mode?:string|null; mail_ready?:boolean; mail_retry_at?:string|null; can_send_activation?:boolean};
type ImportResult = {new_accounts:number; confirmed:number; unchanged:number; snapshot_ids:string[]};

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
  const [revokeBasis, setRevokeBasis] = useState("");
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [stateFilter, setStateFilter] = useState("all");
  const [rosterQuery,setRosterQuery] = useState("");
  const [activationFilter,setActivationFilter] = useState("all");
  const [revokeStudent, setRevokeStudent] = useState("");
  const [revokeReason, setRevokeReason] = useState("");
  const [restoreStudent, setRestoreStudent] = useState("");
  const [restoreReason, setRestoreReason] = useState("");
  const [restoreBasis, setRestoreBasis] = useState("");
  const [specialStudent, setSpecialStudent] = useState("");
  const [specialRef, setSpecialRef] = useState("");
  const [specialReason, setSpecialReason] = useState("");
  const [specialClauseOne, setSpecialClauseOne] = useState(false);
  const [correctionStudent, setCorrectionStudent] = useState("");
  const [correctionCode, setCorrectionCode] = useState("");
  const [correctionName, setCorrectionName] = useState("");
  const [correctionClass, setCorrectionClass] = useState("");
  const [correctionBirth, setCorrectionBirth] = useState("");
  const [correctionMajor, setCorrectionMajor] = useState("");
  const [correctionRef, setCorrectionRef] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [activePanel, setActivePanel] = useState("list");
  const [selectedStudents, setSelectedStudents] = useState<Set<string>>(new Set());
  const [sendingLinks, setSendingLinks] = useState(false);
  const [mailProgress, setMailProgress] = useState("");
  const [mailErrors, setMailErrors] = useState<Record<string,string>>({});

  useEffect(()=>setSelectedStudents(new Set()),[stateFilter,activationFilter,rosterQuery]);

  const permissions = useMemo(()=>assignments.filter(a=>a.round_id===roundId).map(a=>a.assignment_type),[assignments,roundId]);
  const canImport = permissions.includes("ELIGIBILITY_IMPORTER");
  const canManage = permissions.includes("ELIGIBILITY_VERIFIER");
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
    setRestoreStudent("");setRestoreReason("");setRestoreBasis("");setPreview(null);setRevokeStudent("");setSpecialStudent("");setCorrectionStudent("");setSelectedStudents(new Set());setMailErrors({});
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

  const filteredRoster = roster.filter(row=>
    (stateFilter === "all" || row.state === stateFilter)
    && (activationFilter==="all" || (activationFilter==="activated")===accountActivated(row))
    && normalized(`${row.student_code} ${row.display_name} ${row.email}`).includes(normalized(rosterQuery.trim())));
  const canSendStudentLinks = context.base_role === "ADMIN";
  const sendableStudents = filteredRoster.filter(row=>row.can_send_activation);
  const selectedVisibleStudents = sendableStudents.filter(row=>selectedStudents.has(row.student_id));
  const allSendableSelected = sendableStudents.length > 0 && selectedVisibleStudents.length === sendableStudents.length;
  async function sendStudentLinks(ids:string[]) {
    if (!ids.length || sendingLinks) return;
    setSendingLinks(true);setError("");setNotice("");setMailErrors({});
    let sent=0;
    for (const [index,id] of ids.entries()) {
      setMailProgress(`Đang gửi ${index+1}/${ids.length}…`);
      try {
        const result=await request<{sent:boolean;delivery_mode:string}>(`/rounds/${roundId}/roster/${id}/activation-link`,context.user_id,{method:"POST"});
        if(result.sent) sent++;
        else setMailErrors(old=>({...old,[id]:"Gửi thất bại; kiểm tra dịch vụ thư và thử lại sau."}));
      } catch(cause) {setMailErrors(old=>({...old,[id]:errorMessage(cause)}));}
    }
    setSelectedStudents(new Set());setMailProgress("");
    setNotice(`Đã xử lý ${ids.length} sinh viên: ${sent} yêu cầu gửi thành công, ${ids.length-sent} chưa gửi được. Xem kết quả từng dòng.`);
    try {await refreshRoster(roundId);} catch {setError("Đã xử lý gửi nhưng chưa tải lại được danh sách; hãy làm mới trang.");}
    setSendingLinks(false);
  }
  function studentMailLabel(row:RosterEntry) {
    if(row.mail_status==="ACTIVATED") return "Đã kích hoạt";
    if(row.mail_status==="BLOCKED") return "Không đủ điều kiện gửi";
    if(row.mail_status==="SENT") return row.delivery_mode==="smtp" ? "Máy chủ thư đã tiếp nhận" : row.delivery_mode==="development_outbox" ? "Đã lưu thư thử nghiệm trên máy" : "Đã xử lý gửi";
    if(row.mail_status==="FAILED") return "Gửi thất bại";
    if(row.mail_status==="SENDING") return "Đang xử lý gửi";
    if(row.mail_status==="UNKNOWN") return "Chưa rõ kết quả; có thể gửi lại";
    return "Chưa ghi nhận gửi link";
  }
  const legacyPendingCount = roster.filter(row=>row.state==="SUBMITTED").length;
  const confirmedRows = roster.filter(row=>row.state==="CONFIRMED");
  const confirmedCount = confirmedRows.length;
  const activatedCount = confirmedRows.filter(accountActivated).length;
  const registrationSubmittedCount = confirmedRows.filter(row=>row.registration_submitted).length;
  const revokedCount = roster.filter(row=>row.state==="REJECTED").length;
  const specialIsDemo = roster.some(row=>row.student_id===specialStudent && /^(SYN-|E2E-)/.test(row.student_code));
  const panels = [
    {id:"list",label:"Danh sách sinh viên",detail:confirmedCount+" đủ điều kiện",visible:canImport||canManage},
    {id:"import",label:"Nhập danh sách",detail:"Ghi nhận đủ điều kiện ngay",visible:canImport},
    {id:"special",label:"Ngoại lệ Hiệu trưởng",detail:"Theo quyết định cá biệt",visible:canManage},
    {id:"correction",label:"Đính chính hồ sơ",detail:"Theo văn bản Khoa",visible:canManage},
  ].filter(panel=>panel.visible);
  const selectedPanel = panels.some(panel=>panel.id===activePanel)?activePanel:(panels[0]?.id||"");

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

  return <><PageHeader title="Danh sách đủ điều kiện" description="Nhập danh sách chính thức, theo dõi kích hoạt tài khoản và đăng ký đề tài theo từng đợt" />
    <div className="stack roster-page">

      {error&&selectedPanel!=="import"?<p role="alert" className="alert alert-danger">{error}</p>:null}
      {notice?<p role="status" className="alert alert-success">{notice}</p>:null}

      {assignments.length?<section className="roster-context card" aria-label="Phạm vi danh sách">
        <div className="roster-context__copy"><span className="roster-eyebrow">PHẠM VI ĐANG LÀM VIỆC</span>
          <strong>Danh sách theo đợt KLTN</strong><p>Chọn một đợt để xem, nhập hoặc cập nhật kết quả sinh viên.</p></div>
        <label className="input-group roster-context__select">Đợt KLTN<select className="input" value={roundId} disabled={sendingLinks} onChange={e=>setRoundId(e.target.value)}>
          {[...new Map(assignments.map(a=>[a.round_id,a])).values()].map(a=><option key={a.round_id} value={a.round_id}>{a.round_code}</option>)}
        </select></label>
        <div className={`roster-metrics${revokedCount ? " roster-metrics--with-revoked" : ""}`} role="region" aria-label="Tình trạng danh sách" tabIndex={0}>
          <div><span>Đủ điều kiện</span><strong>{confirmedCount}</strong></div>
          <div><span>Đã kích hoạt</span><strong>{activatedCount}/{confirmedCount}</strong></div>
          <div><span>Đã gửi đăng ký</span><strong>{registrationSubmittedCount}/{confirmedCount}</strong></div>
          {legacyPendingCount > 0 ? <div><span>Cần nhập lại DS</span><strong>{legacyPendingCount}</strong></div> : null}
          {revokedCount > 0 ? (
            <div className="roster-metric--revoked">
              <span>Bị thu hồi</span>
              <strong>{revokedCount}</strong>
            </div>
          ) : null}
        </div>
      </section>:null}
      {!assignments.length?<section className="card"><div className="card-body">Bạn chưa được Khoa phân công nhập hoặc quản lý danh sách cho đợt nào.</div></section>:null}

      {panels.length?<>
        <div className="roster-tabs-wrap"><div className="roster-tabs" role="tablist" aria-label="Thao tác danh sách sinh viên" onKeyDown={handlePanelKeyDown}>
          {panels.map(panel=><button key={panel.id} id={`roster-tab-${panel.id}`} type="button" role="tab" disabled={sendingLinks}
            aria-selected={selectedPanel===panel.id} aria-controls={`roster-panel-${panel.id}`} tabIndex={selectedPanel===panel.id?0:-1}
            className={`roster-tab${selectedPanel===panel.id?" roster-tab--active":""}`} onClick={()=>setActivePanel(panel.id)}>
            <span>{panel.label}</span><small>{panel.detail}</small>
          </button>)}
        </div></div>

        <div id={`roster-panel-${selectedPanel}`} className="roster-tabpanel" role="tabpanel" aria-labelledby={`roster-tab-${selectedPanel}`} tabIndex={0}>
          {selectedPanel==="list"?<section className="card roster-section-card">
            <div className="roster-section-heading"><div><span className="roster-eyebrow">QUY TRÌNH THƯỜNG XUYÊN</span><h2>Sinh viên đủ điều kiện</h2>
              <p>Danh sách chính thức được ghi nhận đủ điều kiện ngay sau khi nhập. Sinh viên kích hoạt tài khoản rồi mới gửi đăng ký đề tài.</p></div>
              <div className="roster-section-badges">
                <span className="badge badge-success">{confirmedCount} đủ điều kiện</span>
                <span className="badge badge-info">{activatedCount}/{confirmedCount} đã kích hoạt</span>
                <span className="badge badge-primary">{registrationSubmittedCount}/{confirmedCount} đã gửi đăng ký</span>
                {revokedCount > 0 ? <span className="badge badge-danger">{revokedCount} bị thu hồi</span> : null}
              </div>
            </div>
            <div className="card-body stack">
              <div className="roster-filter-grid">
                <label className="input-group">Trạng thái đủ điều kiện<select className="input" aria-label="Trạng thái đủ điều kiện" disabled={sendingLinks} value={stateFilter} onChange={e=>setStateFilter(e.target.value)}>
                  <option value="all">Tất cả hồ sơ ({roster.length})</option>
                  <option value="CONFIRMED">Đủ điều kiện ({confirmedCount})</option>
                  {legacyPendingCount > 0 ? <option value="SUBMITTED">Cần nhập lại danh sách ({legacyPendingCount})</option> : null}
                  {revokedCount > 0 ? <option value="REJECTED">Đã thu hồi ({revokedCount})</option> : null}
                </select></label>
                <label className="input-group">Kích hoạt tài khoản<select className="input" aria-label="Kích hoạt tài khoản" disabled={sendingLinks} value={activationFilter} onChange={e=>setActivationFilter(e.target.value)}>
                  <option value="all">Tất cả tài khoản</option><option value="activated">Đã kích hoạt</option><option value="not-activated">Chưa kích hoạt</option>
                </select></label>
                <label className="input-group">Tìm sinh viên<input className="input" type="search" aria-label="Tìm sinh viên" disabled={sendingLinks} value={rosterQuery} onChange={e=>setRosterQuery(e.target.value)} placeholder="MSSV, họ tên hoặc email" /></label>
              </div>
              <p className="text-caption">Đang hiện {filteredRoster.length}/{roster.length} sinh viên thuộc đợt đã chọn{stateFilter !== "all" || activationFilter !== "all" || rosterQuery.trim() ? ` (đang lọc: ${[
                stateFilter !== "all" ? (stateFilter === "SUBMITTED" ? "Cần nhập lại danh sách" : stateFilter === "CONFIRMED" ? "Đủ điều kiện" : "Đã thu hồi") : "",
                activationFilter !== "all" ? (activationFilter === "activated" ? "Đã kích hoạt" : "Chưa kích hoạt") : "",
                rosterQuery.trim() ? `“${rosterQuery.trim()}”` : ""
              ].filter(Boolean).join(" · ")})` : ""}.</p>
              {legacyPendingCount > 0 ? (
                <div className="roster-help-note">
                  <strong>Có hồ sơ từ quy trình cũ cần cập nhật</strong>
                  <p>Nhập lại danh sách chính thức của đợt để các hồ sơ này được ghi nhận đủ điều kiện ngay; không cần thao tác xác nhận riêng.</p>
                </div>
              ) : null}
              {canSendStudentLinks ? <div className="stack">
                <p className="text-caption">Danh sách nhập không tự gửi thư. Chọn sinh viên đang chờ kích hoạt rồi gửi; sinh viên vẫn có thể tự yêu cầu link. Chỉ chọn trong kết quả lọc hiện tại.</p>
                {roster.some(row=>row.current_delivery_mode==="development_outbox") ? <p className="alert alert-warning">Thư đang lưu thử nghiệm trên máy, chưa gửi đến email thật.</p> : null}
                {roster.length && !roster.some(row=>row.mail_ready) ? <p className="alert alert-warning">Dịch vụ gửi thư chưa sẵn sàng.</p> : null}
                <div className="account-actions">
                  <button
                    type="button"
                    className="btn btn-secondary btn-bulk-toggle"
                    disabled={sendingLinks || !sendableStudents.length}
                    onClick={() => {
                      if (allSendableSelected) {
                        setSelectedStudents(new Set());
                      } else {
                        setSelectedStudents(new Set(sendableStudents.map(row => row.student_id)));
                      }
                    }}
                  >
                    {allSendableSelected ? `Bỏ chọn tất cả (${sendableStudents.length})` : `Chọn tất cả có thể gửi (${sendableStudents.length})`}
                  </button>
                  <button type="button" className="btn btn-secondary" disabled={sendingLinks || busy} onClick={() => void refreshRoster(roundId).catch(cause => setError(errorMessage(cause)))}>Làm mới trạng thái</button>
                  <button type="button" className="btn btn-primary btn-bulk-submit" disabled={sendingLinks || busy || !selectedVisibleStudents.length || !roster.some(row => row.mail_ready)} onClick={() => void sendStudentLinks(selectedVisibleStudents.map(row => row.student_id))}>Gửi link đã chọn ({selectedVisibleStudents.length})</button>
                </div>
                <p role="status" aria-live="polite" className="text-caption">{mailProgress || `Đã chọn ${selectedVisibleStudents.length} sinh viên trong kết quả lọc.`}</p>
              </div> : null}
              <div className="table-scroll" role="region" aria-label="Danh sách sinh viên đủ điều kiện" tabIndex={0}><table className="account-table"><thead><tr>{canSendStudentLinks ? (
                    <th style={{ width: 44, textAlign: "center" }}>
                      <input
                        type="checkbox"
                        aria-label="Chọn hoặc bỏ chọn tất cả sinh viên có thể gửi"
                        title={allSendableSelected ? "Bỏ chọn tất cả" : "Chọn tất cả có thể gửi"}
                        checked={allSendableSelected}
                        disabled={sendingLinks || !sendableStudents.length}
                        onChange={e => setSelectedStudents(e.target.checked ? new Set(sendableStudents.map(row => row.student_id)) : new Set())}
                      />
                    </th>
                  ) : null}<th>MSSV</th><th>Họ tên</th><th>Email</th><th>Bộ môn</th><th>Ngành</th><th>Đủ điều kiện</th><th>Kích hoạt</th>{canSendStudentLinks?<th>Trạng thái gửi link</th>:null}<th>Đăng ký đề tài</th>{canSendStudentLinks?<th>Thao tác</th>:null}</tr></thead>
                <tbody>{filteredRoster.map(row=><tr key={row.snapshot_id}>{canSendStudentLinks?<td><input type="checkbox" aria-label={`Chọn SV ${row.student_code}`} checked={selectedStudents.has(row.student_id)} disabled={!row.can_send_activation||sendingLinks||busy} onChange={e=>setSelectedStudents(old=>{const next=new Set(old);if(e.target.checked)next.add(row.student_id);else next.delete(row.student_id);return next;})}/></td>:null}<td>{row.student_code}</td><td>{row.display_name}</td><td>{row.email}</td>
                  <td>{row.department_code}</td><td>{row.major_code||"—"}{catalog.find(item=>item.department_code===row.department_code&&item.major_code===row.major_code)?.major_name
                    ? ` · ${catalog.find(item=>item.department_code===row.department_code&&item.major_code===row.major_code)?.major_name}`:""}</td>
                  <td>{row.state === "SUBMITTED" ? <span className="badge badge-warning">Cần nhập lại danh sách</span> :
                       row.state === "CONFIRMED" ? <span className="badge badge-success">Đủ điều kiện</span> :
                       row.state === "REJECTED" ? <span className="badge badge-danger">Đã thu hồi</span> :
                       <span className="badge badge-neutral">{row.state}</span>}</td>
                  <td>{accountActivated(row)?"Đã kích hoạt":"Chưa kích hoạt"}{row.account_status==="LOCKED"?" · Đã khóa":""}</td>
                  {canSendStudentLinks?<td>{studentMailLabel(row)}{row.mail_retry_at&&!row.can_send_activation&&row.mail_status!=="ACTIVATED"&&row.mail_status!=="BLOCKED"?<div className="text-caption">Gửi lại sau {new Date(row.mail_retry_at).toLocaleTimeString("vi-VN")} · làm mới trang</div>:null}{mailErrors[row.student_id]?<p role="alert" className="text-danger">{mailErrors[row.student_id]}</p>:null}</td>:null}
                  <td>{row.registration_submitted ? <>Đã gửi{row.registration_submitted_at ? <small className="text-caption"> · {new Date(row.registration_submitted_at).toLocaleString("vi-VN")}</small> : null}</> : "Chưa gửi"}</td>{canSendStudentLinks?<td><button type="button" className="btn btn-secondary btn-sm" disabled={!row.can_send_activation||!row.mail_ready||busy||sendingLinks} onClick={()=>void sendStudentLinks([row.student_id])}>Gửi link</button></td>:null}</tr>)}</tbody></table></div>
              {!filteredRoster.length?<p className="text-muted">Không có sinh viên khớp bộ lọc.</p>:null}
              {canManage ? <><details className="roster-accordion roster-accordion--danger">
                <summary><span><strong>Thu hồi kết quả đã xác nhận</strong><small>SV vẫn đăng nhập và xem hồ sơ; ngừng đăng ký và nộp nội dung trong đợt này. Các thành viên khác không bị khóa.</small></span><span className="badge badge-danger">Thao tác cần thận trọng</span></summary>
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
              <details>
                <summary><strong>Khôi phục quyền tham gia đã thu hồi</strong></summary>
                <div className="stack">
                  <p>Chỉ dùng khi Khoa xác nhận lại điều kiện. Giữ nguyên lịch sử thu hồi; không tự mở khóa tài khoản hoặc tạo lại hồ sơ.</p>
                  <StudentPicker label="Sinh viên cần khôi phục" rows={roster.filter(r=>r.state==="REJECTED")} value={restoreStudent} onChange={setRestoreStudent} placeholder="Chọn sinh viên đã bị thu hồi" disabled={busy} />
                  <label className="input-group">Văn bản/căn cứ khôi phục<input className="input" value={restoreBasis} onChange={e=>setRestoreBasis(e.target.value)} maxLength={500} /></label>
                  <label className="input-group">Lý do khôi phục<input className="input" value={restoreReason} onChange={e=>setRestoreReason(e.target.value)} maxLength={2000} /></label>
                  <button className="btn btn-secondary" disabled={busy||!restoreStudent||restoreBasis.trim().length<3||restoreReason.trim().length<5} onClick={()=>void run(async()=>{
                    await request(`/rounds/${roundId}/roster/restore`,context.user_id,{method:"POST",body:JSON.stringify({student_id:restoreStudent,basis_ref:restoreBasis,reason:restoreReason})});
                    setRestoreStudent("");setRestoreBasis("");setRestoreReason("");
                  },"Đã khôi phục quyền tham gia; lịch sử cũ được giữ.")}>Khôi phục quyền tham gia</button>
                </div>
              </details></> : null}
            </div>
          </section>:null}

          {selectedPanel==="import"?<section className="card roster-section-card">
            <div className="roster-section-heading"><div><span className="roster-eyebrow">NHẬP DANH SÁCH CHÍNH THỨC</span><h2>Ghi nhận sinh viên đủ điều kiện</h2>
              <p>Kiểm tra tệp, xem trước dữ liệu; khi nhập, sinh viên được ghi nhận đủ điều kiện ngay và có thể kích hoạt tài khoản.</p></div><span className="badge badge-primary">CSV · XLSX</span></div>
            <div className="card-body stack">
              <div className="roster-form-grid">
                <label className="input-group">
                  <span>Tệp danh sách</span>
                  <input id="roster-file-input" className="input" type="file" accept=".csv,.xlsx" onChange={e=>{setFile(e.target.files?.[0]||null);setPreview(null);setError("");setNotice("");}} />
                  {file && <div className="roster-file-selected flex items-center justify-between gap-2">
                    <span className="text-body-sm font-semibold">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
                    <button type="button" className="btn btn-ghost btn-sm" title="Hủy chọn tệp" onClick={() => {
                      setFile(null); setPreview(null);
                      const el = document.getElementById("roster-file-input") as HTMLInputElement | null;
                      if (el) el.value = "";
                    }}><X size={14} aria-hidden="true" style={{marginRight: 4}} /> Xóa tệp đã chọn</button>
                  </div>}
                </label>
                <label className="input-group">
                  <span>Mã/số văn bản nguồn</span>
                  <input id="roster-reference" className="input" required minLength={3} maxLength={500} value={reference} onChange={e=>{setReference(e.target.value);setError("");}} placeholder="Demo: DEMO-DS-SV-DOT-1-2026" />
                </label>
              </div>
              {departmentError && <p role="alert" className="alert alert-danger">{departmentError}</p>}
              {!departmentError && !catalog.length && <p role="alert" className="alert alert-warning">Chưa có danh mục bộ môn và ngành đang hoạt động, chưa thể nhập.</p>}
              <details><summary>Xem mã bộ môn và ngành được chấp nhận</summary><div className="table-scroll" role="region" aria-label="Danh mục bộ môn và ngành" tabIndex={0}><table className="account-table"><thead><tr><th>Mã bộ môn</th><th>Tên bộ môn</th><th>Mã ngành</th><th>Tên ngành</th></tr></thead><tbody>
                {catalog.map(item=><tr key={item.department_code+"-"+item.major_code}><td>{item.department_code}</td><td>{item.department_name}</td><td>{item.major_code}</td><td>{item.major_name}</td></tr>)}
              </tbody></table></div></details>
              <a href="/templates/danh-sach-sinh-vien-kltn-mau.xlsx" download>Tải Excel mẫu</a>
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
                    setPreview(null);setFile(null);
                    setActivePanel("list");
                    return "Đã ghi nhận " + result.confirmed + " sinh viên đủ điều kiện; tạo " + result.new_accounts + " tài khoản chờ kích hoạt; " + result.unchanged + " hồ sơ đã có.";
                  },"Đã nhập danh sách.");}}>Nhập sau khi kiểm</button></div>
              <p role="status" className="text-caption">{!file?"Chọn tệp CSV UTF-8 hoặc Excel .xlsx (tối đa 2 MB).":
                !preview?"Nhấn “Kiểm tra tệp” và chờ bảng xem trước; chỉ khi kiểm tra thành công mới có thể nhập.":
                reference.trim().length<3?"Đã xem trước tệp. Nhập mã/số văn bản nguồn (ít nhất 3 ký tự) để hoàn tất.":
                `Đã xem trước ${preview.count} sinh viên. Kiểm tra các dòng rồi nhấn “Nhập sau khi kiểm”.`}</p>
              {error?<p role="alert" className="alert alert-danger">{error}</p>:null}
              {preview?<div className="roster-preview stack"><div><span className="roster-eyebrow">ĐÃ KIỂM TRA · CHƯA NHẬP</span><h3>Xem trước: {preview.count} sinh viên</h3></div>
                <div className="table-scroll" role="region" aria-label="Xem trước danh sách nhập" tabIndex={0}><table className="account-table"><thead><tr><th className="table-col-index">Dòng</th><th>MSSV</th><th>Họ tên</th><th>Email</th><th>Mã bộ môn</th><th>Lớp</th><th>Mã ngành</th></tr></thead>
                  <tbody>{preview.rows.map(row=><tr key={row.line}><td className="table-col-index">{row.line}</td><td className="table-col-code">{row.student_code}</td><td>{row.display_name}</td>
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
              <StudentPicker label="Sinh viên được xét ngoại lệ" rows={roster.filter(r=>r.state!=="CONFIRMED")} value={specialStudent} onChange={setSpecialStudent} placeholder="Chọn sinh viên chưa đủ điều kiện" disabled={busy} />
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
                setCorrectionClass(row?.class_name||"");setCorrectionBirth(row?.birth_date||"");setCorrectionMajor(row?.major_code||"");
              }} placeholder="Chọn sinh viên" disabled={busy} />
              {correctionStudent?<div className="roster-form-grid">
                <label className="input-group">MSSV<input className="input" value={correctionCode} onChange={e=>setCorrectionCode(e.target.value)} /></label>
                <label className="input-group">Họ tên<input className="input" value={correctionName} onChange={e=>setCorrectionName(e.target.value)} /></label>
                <label className="input-group">Ngày sinh (Mẫu 11)<input className="input" type="date" min="1900-01-01" max={new Date().toISOString().slice(0,10)} value={correctionBirth} onChange={e=>setCorrectionBirth(e.target.value)} /></label>
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
                      class_name:correctionClass,major_code:correctionMajor,birth_date:correctionBirth||null,
                      basis_ref:correctionRef.trim(),reason:correctionReason.trim()})});
                  return "Đã đính chính hồ sơ và lưu dấu vết.";
                }, "Đã đính chính thông tin.")}>Lưu đính chính</button></div>
            </div>
          </section>:null}
        </div>
      </>:null}

    </div>
  </>;
}
