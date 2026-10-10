import { useCallback, useEffect, useState } from "react";
import type { Context } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";

type Department = {id:string; code:string; name:string; major_code:string|null};
type Round = {id:string; code:string; state:string};
type Account = {id:string; email:string; base_role:string; status:string; verified:boolean};
type Assignment = {id:string; round_id:string; round_code:string; user_id:string; email:string; assignment_type:string};

export default function AdministrationPage({context}: {context:Context}) {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [lecturerCode, setLecturerCode] = useState("");
  const [lecturerName, setLecturerName] = useState("");
  const [lecturerEmail, setLecturerEmail] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [roundId, setRoundId] = useState("");
  const [userId, setUserId] = useState("");
  const [kind, setKind] = useState("ELIGIBILITY_IMPORTER");
  const [basis, setBasis] = useState("");
  const [search, setSearch] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async (term = "") => {
    const [d,r,u,a] = await Promise.all([
      request<Department[]>("/admin/departments", context.user_id),
      request<Round[]>("/admin/rounds", context.user_id),
      request<Account[]>("/admin/users?search="+encodeURIComponent(term), context.user_id),
      request<Assignment[]>("/admin/round-assignments", context.user_id),
    ]);
    setDepartments(d); setRounds(r); setAccounts(u); setAssignments(a);
  }, [context.user_id]);
  useEffect(() => {void refresh().catch(cause=>setError(errorMessage(cause)));}, [refresh]);
  async function run(action:()=>Promise<unknown>, message:string) {
    setBusy(true); setError(""); setNotice("");
    try {const result=await action(); await refresh(search); setNotice(typeof result==="string"?result:message);} catch(cause) {setError(errorMessage(cause));}
    finally {setBusy(false);}
  }
  return <><PageHeader title="Quản trị tài khoản" description="Cấp tài khoản và ghi nhận phân công theo đợt" />
    <div className="stack">
      <p className="alert">Quản trị tài khoản không đồng nghĩa quyền xác nhận đủ điều kiện. Người được Khoa giao nhiệm vụ phải có phân công theo đợt và căn cứ tương ứng.</p>
      {error ? <p role="alert" className="alert alert-danger">{error}</p> : null}
      {notice ? <p role="status" className="alert alert-success">{notice}</p> : null}
      <div className="grid grid-auto">
        <section className="card"><div className="card-body stack"><h2>Mời giảng viên</h2>
          <form className="stack" onSubmit={e=>{e.preventDefault(); void run(async()=>{
            const result=await request<{invitation_sent:boolean}>("/admin/lecturers", context.user_id,
              {method:"POST", body:JSON.stringify({lecturer_code:lecturerCode,display_name:lecturerName,email:lecturerEmail,department_id:departmentId})});
            return result.invitation_sent ? "Đã tạo tài khoản và gửi liên kết kích hoạt." :
              "Đã tạo tài khoản nhưng chưa gửi được email; giảng viên có thể yêu cầu lại liên kết kích hoạt.";
          },"Đã tạo tài khoản.");}}>
            <label className="input-group">Mã giảng viên<input className="input" required value={lecturerCode} onChange={e=>setLecturerCode(e.target.value)} /></label>
            <label className="input-group">Họ tên<input className="input" required value={lecturerName} onChange={e=>setLecturerName(e.target.value)} /></label>
            <label className="input-group">Email<input className="input" type="email" required value={lecturerEmail} onChange={e=>setLecturerEmail(e.target.value)} /></label>
            <label className="input-group">Bộ môn<select className="input" required value={departmentId} onChange={e=>setDepartmentId(e.target.value)}>
              <option value="">Chọn bộ môn</option>{departments.map(d=><option key={d.id} value={d.id}>{d.code} · {d.name}</option>)}</select></label>
            <button className="btn btn-primary" disabled={busy}>Tạo và gửi lời mời</button>
          </form>
        </div></section>
        <section className="card"><div className="card-body stack"><h2>Phân công theo đợt</h2>
          <form className="stack" onSubmit={e=>{e.preventDefault();void run(()=>request("/admin/round-assignments",context.user_id,
            {method:"POST",body:JSON.stringify({round_id:roundId,user_id:userId,assignment_type:kind,basis_ref:basis})}),"Đã lưu phân công.");}}>
            <label className="input-group">Đợt<select className="input" required value={roundId} onChange={e=>setRoundId(e.target.value)}>
              <option value="">Chọn đợt</option>{rounds.map(r=><option key={r.id} value={r.id}>{r.code} · {r.state}</option>)}</select></label>
            <label className="input-group">Người được giao<select className="input" required value={userId} onChange={e=>setUserId(e.target.value)}>
              <option value="">Chọn tài khoản đang hoạt động</option>{accounts.filter(a=>a.status==="ACTIVE" && a.base_role!=="STUDENT").map(a=><option key={a.id} value={a.id}>{a.email}</option>)}</select></label>
            <label className="input-group">Nhiệm vụ<select className="input" value={kind} onChange={e=>setKind(e.target.value)}>
              <option value="ELIGIBILITY_IMPORTER">Nhập danh sách</option><option value="ELIGIBILITY_VERIFIER">Xác nhận điều kiện</option></select></label>
            <label className="input-group">Căn cứ phân công<input className="input" required minLength={3} value={basis} onChange={e=>setBasis(e.target.value)} placeholder="Số văn bản hoặc quyết định của Khoa" /></label>
            <button className="btn btn-primary" disabled={busy}>Lưu phân công</button>
          </form>
        </div></section>
      </div>
      <section className="card"><div className="card-body stack"><h2>Phân công đang hiệu lực</h2>
        <label className="input-group">Lý do thu hồi (nếu cần)<input className="input" minLength={5} value={reason} onChange={e=>setReason(e.target.value)} /></label>
        <div className="account-list">{assignments.map(a=><div className="account-list__row" key={a.id}>
          <span>{a.round_code} · {a.email} · {a.assignment_type === "ELIGIBILITY_VERIFIER" ? "Xác nhận" : "Nhập danh sách"}</span>
          <button className="btn btn-secondary btn-sm" disabled={busy || reason.trim().length<5}
            onClick={()=>void run(()=>request(`/admin/round-assignments/${a.id}/revoke`,context.user_id,
              {method:"POST",body:JSON.stringify({reason})}),"Đã thu hồi phân công.")}>Thu hồi</button>
        </div>)}{!assignments.length ? <p>Chưa có phân công.</p> : null}</div>
      </div></section>
      <section className="card"><div className="card-body stack"><h2>Tài khoản</h2>
        <form className="account-search" onSubmit={e=>{e.preventDefault();void refresh(search).catch(cause=>setError(errorMessage(cause)));}}>
          <input className="input" aria-label="Tìm theo email" placeholder="Tìm theo email" value={search} onChange={e=>setSearch(e.target.value)} />
          <button className="btn btn-secondary">Tìm</button>
        </form>
        <p className="text-muted">Để khóa hoặc mở khóa, nhập lý do ở ô phía trên.</p>
        <div className="account-list">{accounts.map(a=><div className="account-list__row" key={a.id}>
          <span>{a.email} · {a.base_role} · {a.status}{!a.verified ? " · chưa kích hoạt" : ""}</span>
          {a.id!==context.user_id ? <button className="btn btn-secondary btn-sm" disabled={busy || reason.trim().length<5}
            onClick={()=>void run(()=>request(`/admin/users/${a.id}/lock`,context.user_id,
              {method:"POST",body:JSON.stringify({locked:a.status!=="LOCKED",reason})}),
              a.status==="LOCKED"?"Đã mở khóa.":"Đã khóa tài khoản.")}>
            {a.status==="LOCKED"?"Mở khóa":"Khóa"}</button> : null}
        </div>)}</div>
      </div></section>
    </div>
  </>;
}
