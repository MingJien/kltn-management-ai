import { useCallback, useEffect, useMemo, useState } from "react";
import type { Context } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";

type Assignment = {round_id:string; round_code:string; assignment_type:string};
type PreviewRow = {line:number; student_code:string; display_name:string; email:string; department_code:string; class_name:string; major_code:string};
type Preview = {sha256:string; count:number; rows:PreviewRow[]};
type RosterEntry = {snapshot_id:string; student_id:string; student_code:string; display_name:string; email:string; class_name:string|null; major_code:string|null; account_status:string; state:string; version:number; evidence_ref:string; confirmed_at:string|null};
type ImportResult = {new_accounts:number; submitted:number; unchanged:number; snapshot_ids:string[]};

export default function RosterPage({context}: {context:Context}) {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [roundId, setRoundId] = useState("");
  const [file, setFile] = useState<File|null>(null);
  const [preview, setPreview] = useState<Preview|null>(null);
  const [reference, setReference] = useState("");
  const [basis, setBasis] = useState("");
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [revokeStudent, setRevokeStudent] = useState("");
  const [revokeReason, setRevokeReason] = useState("");
  const [specialStudent, setSpecialStudent] = useState("");
  const [specialRef, setSpecialRef] = useState("");
  const [specialReason, setSpecialReason] = useState("");
  const [specialClauseOne, setSpecialClauseOne] = useState(false);
  const [correctionStudent, setCorrectionStudent] = useState("");
  const [correctionCode, setCorrectionCode] = useState("");
  const [correctionName, setCorrectionName] = useState("");
  const [correctionEmail, setCorrectionEmail] = useState("");
  const [correctionClass, setCorrectionClass] = useState("");
  const [correctionMajor, setCorrectionMajor] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const permissions = useMemo(()=>assignments.filter(a=>a.round_id===roundId).map(a=>a.assignment_type),[assignments,roundId]);
  const canImport = permissions.includes("ELIGIBILITY_IMPORTER");
  const canConfirm = permissions.includes("ELIGIBILITY_VERIFIER");
  const refreshRoster = useCallback(async (id:string)=>{
    if (id) setRoster(await request<RosterEntry[]>(`/rounds/${id}/roster`,context.user_id));
  },[context.user_id]);
  useEffect(()=>{void request<Assignment[]>("/me/round-assignments",context.user_id)
    .then(rows=>{setAssignments(rows); if(rows.length) setRoundId(rows[0].round_id);})
    .catch(cause=>setError(errorMessage(cause)));},[context.user_id]);
  useEffect(()=>{setPreview(null);setSelected([]);void refreshRoster(roundId).catch(cause=>setError(errorMessage(cause)));},[roundId,refreshRoster]);
  async function run(action:()=>Promise<unknown>,message:string) {
    setBusy(true);setError("");setNotice("");
    try {const result=await action();await refreshRoster(roundId);setNotice(typeof result==="string"?result:message);}
    catch(cause){setError(errorMessage(cause));}
    finally{setBusy(false);}
  }
  function fileHeaders(chosen:File) {
    return {"Content-Type":"application/octet-stream",
      "X-File-Name":chosen.name.toLowerCase().endsWith(".xlsx")?"roster.xlsx":"roster.csv"};
  }
  const pending = roster.filter(row=>row.state==="SUBMITTED");
  return <><PageHeader title="Danh sách đủ điều kiện" description="Nhập và xác nhận sinh viên theo từng đợt" />
    <div className="stack">
      <p className="alert">Tệp nhập chỉ chứa MSSV, họ tên, email, bộ môn, lớp và mã ngành. Không nhập điểm, GPA, bảng điểm hay tình trạng kỷ luật. Tệp gốc không được lưu trên máy chủ.</p>
      {error?<p role="alert" className="alert alert-danger">{error}</p>:null}
      {notice?<p role="status" className="alert alert-success">{notice}</p>:null}
      <label className="input-group">Đợt KLTN<select className="input" value={roundId} onChange={e=>setRoundId(e.target.value)}>
        {[...new Map(assignments.map(a=>[a.round_id,a])).values()].map(a=><option key={a.round_id} value={a.round_id}>{a.round_code}</option>)}
      </select></label>
      {!assignments.length?<section className="card"><div className="card-body">Bạn chưa được Khoa phân công nhập hoặc xác nhận danh sách cho đợt nào.</div></section>:null}
      {canImport?<section className="card"><div className="card-body stack"><h2>Nhập danh sách đã được Khoa chấp thuận</h2>
        <p className="text-muted">CSV UTF-8 hoặc XLSX, một trang tính, tối đa 1.000 dòng và 2 MB. Cột bắt buộc: <code>student_code, display_name, email, department_code, class_name, major_code</code>.</p>
        <label className="input-group">Tệp danh sách<input className="input" type="file" accept=".csv,.xlsx" onChange={e=>{setFile(e.target.files?.[0]||null);setPreview(null);}} /></label>
        <label className="input-group">Mã/số văn bản nguồn<input className="input" required minLength={3} value={reference} onChange={e=>setReference(e.target.value)} /></label>
        <div className="account-actions">
          <button className="btn btn-secondary" disabled={!file||busy} onClick={()=>{if(!file)return;void run(async()=>{
            const data=await request<Preview>(`/rounds/${roundId}/roster/preview`,context.user_id,
              {method:"POST",body:file,headers:fileHeaders(file)});setPreview(data);
          },"Đã kiểm định dạng và đối chiếu dữ liệu hiện có. Hãy kiểm tra trước khi nhập.");}}>Kiểm tra tệp</button>
          <button className="btn btn-primary" disabled={!file||!preview||reference.trim().length<3||busy}
            onClick={()=>{if(!file||!preview)return;void run(async()=>{
              const result=await request<ImportResult>(`/rounds/${roundId}/roster?reference=${encodeURIComponent(reference.trim())}`,context.user_id,
                {method:"POST",body:file,headers:{...fileHeaders(file),"X-Preview-SHA256":preview.sha256}});
              setPreview(null);setFile(null);setSelected(result.snapshot_ids);
              return `Đã nhập ${result.submitted} kết quả chờ xác nhận, tạo ${result.new_accounts} tài khoản; ${result.unchanged} dòng đã có.`;
            },"Đã nhập danh sách.");}}>Nhập sau khi kiểm</button>
        </div>
        {preview?<div className="stack"><h3>Xem trước: {preview.count} sinh viên</h3>
          <div className="table-scroll"><table className="account-table"><thead><tr><th>Dòng</th><th>MSSV</th><th>Họ tên</th><th>Email</th><th>Lớp</th><th>Ngành</th></tr></thead>
            <tbody>{preview.rows.map(row=><tr key={row.line}><td>{row.line}</td><td>{row.student_code}</td><td>{row.display_name}</td>
              <td>{row.email}</td><td>{row.class_name}</td><td>{row.major_code}</td></tr>)}</tbody></table></div>
        </div>:null}
      </div></section>:null}
      {canConfirm?<section className="card"><div className="card-body stack"><h2>Xác nhận hoặc thu hồi theo đợt</h2>
        <p className="text-muted">Chỉ người được giao quyền xác nhận mới quyết định kết quả. Tài khoản sinh viên chưa kích hoạt vẫn được giữ trong danh sách.</p>
        <label className="input-group">Căn cứ xác nhận/thu hồi<input className="input" minLength={3} value={basis} onChange={e=>setBasis(e.target.value)} placeholder="Số danh sách hoặc quyết định" /></label>
        <div className="account-actions"><button className="btn btn-secondary" disabled={!pending.length||busy}
          onClick={()=>setSelected(pending.map(row=>row.snapshot_id))}>Chọn tất cả chờ xác nhận</button>
          <button className="btn btn-primary" disabled={!selected.length||basis.trim().length<3||busy}
            onClick={()=>void run(async()=>{await request(`/rounds/${roundId}/roster/confirm`,context.user_id,
              {method:"POST",body:JSON.stringify({snapshot_ids:selected,basis_ref:basis})});setSelected([]);},
              `Đã xác nhận ${selected.length} sinh viên.`)}>Xác nhận đã đối chiếu</button></div>
        <div className="table-scroll"><table className="account-table"><thead><tr><th>Chọn</th><th>MSSV</th><th>Họ tên</th><th>Email</th><th>Trạng thái</th><th>Tài khoản</th></tr></thead>
          <tbody>{roster.map(row=><tr key={row.snapshot_id}><td>{row.state==="SUBMITTED"?<input type="checkbox" aria-label={`Chọn ${row.student_code}`}
            checked={selected.includes(row.snapshot_id)} onChange={e=>setSelected(current=>e.target.checked?[...current,row.snapshot_id]:current.filter(x=>x!==row.snapshot_id))}/>:null}</td>
            <td>{row.student_code}</td><td>{row.display_name}</td><td>{row.email}</td><td>{row.state}</td><td>{row.account_status}</td></tr>)}</tbody></table></div>
        <h3>Thu hồi kết quả hiện hành</h3>
        <label className="input-group">Sinh viên<select className="input" value={revokeStudent} onChange={e=>setRevokeStudent(e.target.value)}>
          <option value="">Chọn sinh viên đã xác nhận</option>{roster.filter(r=>r.state==="CONFIRMED").map(r=><option key={r.student_id} value={r.student_id}>{r.student_code} · {r.display_name}</option>)}</select></label>
        <label className="input-group">Lý do<input className="input" minLength={5} value={revokeReason} onChange={e=>setRevokeReason(e.target.value)} /></label>
        <button className="btn btn-destructive" disabled={!revokeStudent||revokeReason.trim().length<5||basis.trim().length<3||busy}
          onClick={()=>void run(async()=>{await request(`/rounds/${roundId}/roster/revoke`,context.user_id,{method:"POST",
            body:JSON.stringify({student_id:revokeStudent,reason:revokeReason,basis_ref:basis})});setRevokeStudent("");setRevokeReason("");},
            "Đã thu hồi quyền tham gia; hồ sơ cũ được giữ để rà soát.")}>Thu hồi quyền tham gia</button>
        <h3>Ghi nhận quyết định đặc biệt của Hiệu trưởng</h3>
        <p className="text-muted">QĐ5964 chỉ cho phép ngoại lệ đối với ngưỡng tín chỉ/GPA ở khoản 2 Điều 2. Chỉ ghi nhận khi đã có quyết định thật và đã đối chiếu khoản 1; không nhập chi tiết kỷ luật hoặc án tích.</p>
        <label className="input-group">Sinh viên<select className="input" value={specialStudent} onChange={e=>setSpecialStudent(e.target.value)} disabled={busy}>
          <option value="">Chọn sinh viên chưa được xác nhận</option>{roster.filter(r=>r.state!=="CONFIRMED").map(r=><option key={r.student_id} value={r.student_id}>{r.student_code} · {r.display_name}</option>)}
        </select></label>
        <label className="input-group">Số quyết định của Hiệu trưởng<input className="input" value={specialRef} onChange={e=>setSpecialRef(e.target.value)} maxLength={500} disabled={busy} /></label>
        <label className="input-group">Lý do đối chiếu ngắn gọn<input className="input" value={specialReason} onChange={e=>setSpecialReason(e.target.value)} maxLength={2000} disabled={busy} /></label>
        <label><input type="checkbox" checked={specialClauseOne} onChange={e=>setSpecialClauseOne(e.target.checked)} disabled={busy} /> Đã kiểm khoản 1 Điều 2 QĐ5964 và quyết định gốc</label>
        <button className="btn btn-secondary" disabled={!specialStudent||specialRef.trim().length<3||specialReason.trim().length<5||!specialClauseOne||busy}
          onClick={()=>void run(async()=>{await request(`/rounds/${roundId}/roster/special-decision`,context.user_id,{method:"POST",
            body:JSON.stringify({student_id:specialStudent,official_ref:specialRef.trim(),reason:specialReason.trim(),clause_1_verified:specialClauseOne})});
            setSpecialStudent("");setSpecialRef("");setSpecialReason("");setSpecialClauseOne(false);},
            "Đã ghi nhận kết quả theo quyết định đặc biệt; phiên bản cũ được giữ.")}>Ghi nhận ngoại lệ</button>
        <h3>Đính chính thông tin theo văn bản Khoa</h3>
        <p className="text-muted">Đổi email sẽ vô hiệu mật khẩu và các phiên cũ; sinh viên cần kích hoạt lại bằng email mới. Việc đính chính không tự thay đổi kết quả đủ điều kiện.</p>
        <label className="input-group">Sinh viên<select className="input" value={correctionStudent} onChange={e=>{
          const row=roster.find(r=>r.student_id===e.target.value);setCorrectionStudent(e.target.value);
          setCorrectionCode(row?.student_code||"");setCorrectionName(row?.display_name||"");
          setCorrectionEmail(row?.email||"");setCorrectionClass(row?.class_name||"");setCorrectionMajor(row?.major_code||"");
        }}><option value="">Chọn sinh viên</option>{roster.map(r=><option key={r.student_id} value={r.student_id}>{r.student_code} · {r.display_name}</option>)}</select></label>
        {correctionStudent?<div className="grid grid-auto">
          <label className="input-group">MSSV<input className="input" value={correctionCode} onChange={e=>setCorrectionCode(e.target.value)} /></label>
          <label className="input-group">Họ tên<input className="input" value={correctionName} onChange={e=>setCorrectionName(e.target.value)} /></label>
          <label className="input-group">Email<input className="input" type="email" value={correctionEmail} onChange={e=>setCorrectionEmail(e.target.value)} /></label>
          <label className="input-group">Lớp<input className="input" value={correctionClass} onChange={e=>setCorrectionClass(e.target.value)} /></label>
          <label className="input-group">Mã ngành<input className="input" value={correctionMajor} onChange={e=>setCorrectionMajor(e.target.value)} /></label>
        </div>:null}
        <button className="btn btn-secondary" disabled={!correctionStudent||basis.trim().length<3||busy}
          onClick={()=>void run(()=>request(`/rounds/${roundId}/roster/${correctionStudent}`,context.user_id,
            {method:"PATCH",body:JSON.stringify({student_code:correctionCode,display_name:correctionName,
              email:correctionEmail,class_name:correctionClass,major_code:correctionMajor,basis_ref:basis})}),
            "Đã ghi đính chính và lưu dấu vết; nếu đổi email, sinh viên phải kích hoạt lại.")}>Lưu đính chính</button>
      </div></section>:null}
      {!canConfirm&&roundId?<section className="card"><div className="card-body stack"><h2>Trạng thái danh sách</h2>
        <p>{roster.length} sinh viên; {pending.length} kết quả đang chờ người được giao xác nhận.</p></div></section>:null}
    </div>
  </>;
}
