import { useCallback, useEffect, useState } from "react";
import type { Context } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";

type Department = {id:string; code:string; name:string; major_code:string|null};
type Round = {id:string; code:string; state:string};
type Account = {id:string; email:string; base_role:string; status:string; verified:boolean; student_code:string|null};
type Assignment = {id:string; round_id:string; round_code:string; user_id:string; email:string; assignment_type:string};

export default function AdministrationPage({context,onPermissionsChanged}: {
  context:Context; onPermissionsChanged:()=>Promise<void>;
}) {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [staffAccounts, setStaffAccounts] = useState<Account[]>([]);
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
  const [emailReason, setEmailReason] = useState("");
  const [assignmentHint, setAssignmentHint] = useState("");
  const [selectedAccount, setSelectedAccount] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [emailRoundId, setEmailRoundId] = useState("");
  const [officialRef, setOfficialRef] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [term, setTerm] = useState("");
  const [page, setPage] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const isAdmin = context.base_role === "ADMIN";
  const eligibleStaff = (a: Account, task: string) => a.status === "ACTIVE" &&
    (task === "KLTN_COORDINATOR" || task === "ACCOUNT_MANAGER" ? a.base_role === "LECTURER" : a.base_role !== "STUDENT");
  function changeKind(next: string) {
    setKind(next);
    if (userId && !staffAccounts.some(a => a.id === userId && eligibleStaff(a, next))) {
      setUserId("");
      setAssignmentHint("Người đã chọn không phù hợp nhiệm vụ mới. Vui lòng chọn lại người được giao.");
    } else setAssignmentHint("");
  }
  const PAGE_SIZE = 20;
  const refresh = useCallback(async (q: string, atPage: number) => {
    setBusy(true);
    try {
      const [d,r,u,staff,a] = await Promise.all([
        isAdmin ? request<Department[]>("/admin/departments", context.user_id) : Promise.resolve([]),
        isAdmin ? request<Round[]>("/admin/rounds", context.user_id) :
          request<{round_id:string;round_code:string;assignment_type:string}[]>("/me/round-assignments", context.user_id)
            .then(rows => rows.filter(row => row.assignment_type === "ACCOUNT_MANAGER")
              .map(row => ({id:row.round_id,code:row.round_code,state:"OPEN"}))),
        request<Account[]>("/admin/users?search="+encodeURIComponent(q)+"&offset="+(atPage*PAGE_SIZE)+"&limit="+PAGE_SIZE, context.user_id),
        isAdmin ? request<Account[]>("/admin/users?limit=100", context.user_id) : Promise.resolve<Account[]>([]),
        isAdmin ? request<Assignment[]>("/admin/round-assignments", context.user_id) : Promise.resolve([]),
      ]);
      setDepartments(d); setRounds(r); setAccounts(u); setStaffAccounts(staff); setAssignments(a);
      setHasNext(u.length === PAGE_SIZE);
    } finally { setBusy(false); }
  }, [context.user_id, isAdmin, PAGE_SIZE]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = search.trim();
      if (next !== term) {setTerm(next); setPage(0);}
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search, term]);
  useEffect(() => {void refresh(term, page).catch(cause=>setError(errorMessage(cause)));}, [refresh, term, page]);
  const accountById = useCallback((id: string) =>
    accounts.find(a => a.id === id) ?? staffAccounts.find(a => a.id === id), [accounts, staffAccounts]);
  async function run(action:()=>Promise<unknown>, message:string, permissionsChanged=false) {
    setBusy(true); setError(""); setNotice("");
    try {const result=await action(); await refresh(search.trim() || term, page);
      if (permissionsChanged) await onPermissionsChanged();
      setNotice(typeof result==="string"?result:message);} catch(cause) {setError(errorMessage(cause));}
    finally {setBusy(false);}
  }
  return <><PageHeader title="Quản trị tài khoản" description="Cấp tài khoản và ghi nhận phân công theo đợt" />
    <div className="stack">
      {error ? <p role="alert" className="alert alert-danger">{error}</p> : null}
      {notice ? <p role="status" className="alert alert-success">{notice}</p> : null}
      {isAdmin && <div className="grid grid-auto">
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
          <form className="stack" onInvalidCapture={()=>setAssignmentHint("Vui lòng chọn đợt, người được giao và nhập căn cứ phân công ít nhất 3 ký tự.")} onSubmit={e=>{e.preventDefault();setAssignmentHint("");void run(()=>request("/admin/round-assignments",context.user_id,
            {method:"POST",body:JSON.stringify({round_id:roundId,user_id:userId,assignment_type:kind,basis_ref:basis})}),"Đã lưu phân công.",true);}}>
            <label className="input-group">Đợt<select className="input" required value={roundId} onChange={e=>setRoundId(e.target.value)}>
              <option value="">Chọn đợt</option>{rounds.filter(r=>r.state==="DRAFT"||r.state==="OPEN").map(r=><option key={r.id} value={r.id}>{r.code} · {r.state}</option>)}</select></label>
            <label className="input-group">Người được giao<select className="input" required value={userId} aria-describedby="assignment-hint" onChange={e=>{setUserId(e.target.value);setAssignmentHint("");}}>
              <option value="">Chọn người đang hoạt động phù hợp nhiệm vụ</option>{staffAccounts.filter(a=>eligibleStaff(a, kind)).map(a=><option key={a.id} value={a.id}>{a.email}</option>)}</select></label>
            <label className="input-group">Nhiệm vụ<select className="input" value={kind} onChange={e=>changeKind(e.target.value)}>
              <option value="ELIGIBILITY_IMPORTER">Nhập danh sách SV</option><option value="ELIGIBILITY_VERIFIER">Xác nhận điều kiện</option><option value="ACCOUNT_MANAGER">Quản lý tài khoản SV theo đợt</option><option value="KLTN_COORDINATOR">Quản lý mốc tiến độ toàn đợt</option></select></label>
            <p className="text-caption">Quyền điều phối mốc chỉ cho phép mở, gia hạn và đóng mốc chung của đợt; không thay GVHD nhận xét hoặc xác nhận báo cáo.</p>
            <p id="assignment-hint" role="status" className="text-caption">{assignmentHint || "Đổi nhiệm vụ sẽ giữ người đã chọn nếu vẫn phù hợp; nếu không, hãy chọn lại."}</p>
            <label className="input-group">Căn cứ phân công<input className="input" required minLength={3} value={basis} onChange={e=>setBasis(e.target.value)} placeholder="Số văn bản hoặc quyết định của Khoa" /></label>
            <button className="btn btn-primary" disabled={busy}>Lưu phân công</button>
          </form>
        </div></section>
      </div>}
      {isAdmin && <section className="card"><div className="card-body stack"><h2>Phân công đang hiệu lực</h2>
        <label className="input-group">Lý do thu hồi (nếu cần)<input className="input" minLength={5} value={reason} onChange={e=>setReason(e.target.value)} /></label>
        <div className="account-list">{assignments.map(a=><div className="account-list__row" key={a.id}>
          <span>{a.round_code} · {a.email} · {a.assignment_type === "ELIGIBILITY_VERIFIER" ? "Xác nhận điều kiện" : a.assignment_type === "ACCOUNT_MANAGER" ? "Quản lý tài khoản SV" : a.assignment_type === "KLTN_COORDINATOR" ? "Quản lý mốc tiến độ toàn đợt" : "Nhập danh sách SV"}</span>
          <button className="btn btn-secondary btn-sm" disabled={busy || reason.trim().length<5}
            onClick={()=>void run(()=>request(`/admin/round-assignments/${a.id}/revoke`,context.user_id,
              {method:"POST",body:JSON.stringify({reason})}),"Đã thu hồi phân công.",true)}>Thu hồi</button>
        </div>)}{!assignments.length ? <p>Chưa có phân công.</p> : null}</div>
      </div></section>}
      <section className="card"><div className="card-body stack"><h2>Tài khoản</h2>
        <form className="account-search" onSubmit={e=>{e.preventDefault(); setTerm(search.trim()); setPage(0);}}>
          <input className="input" aria-label="Tìm theo email hoặc MSSV" placeholder="Tìm theo email hoặc MSSV" value={search} onChange={e=>setSearch(e.target.value)} />
          <button className="btn btn-secondary">Tìm</button>
        </form>
        <label className="input-group">Lý do thao tác tài khoản<input className="input" minLength={5} value={reason} onChange={e=>setReason(e.target.value)} /></label>
        <p className="text-muted">Khóa hoặc vô hiệu hóa giữ nguyên đề tài, tài liệu và lịch sử. Cấp lại liên kết qua email đang lưu.</p>
        <div className="account-list">{accounts.map(a=><div className="account-list__row" key={a.id}>
          <span className="account-list__info">{a.student_code ? `${a.student_code} · ` : ""}{a.email} · {a.base_role} · {a.status}{!a.verified ? " · chưa kích hoạt" : ""}</span>
          <div className="account-list__actions">
            {a.id === context.user_id ? (
              <span className="text-muted text-caption" style={{gridColumn: "1 / -1", textAlign: "right"}}>Tài khoản hiện tại</span>
            ) : (
              <>
                <div className="account-list__action-slot">
                  {a.status !== "DISABLED" ? (
                    <button className="btn btn-secondary btn-sm" disabled={busy || reason.trim().length < 5}
                      onClick={() => void run(() => request(`/admin/users/${a.id}/lock`, context.user_id,
                        {method: "POST", body: JSON.stringify({locked: a.status !== "LOCKED", reason})}),
                        a.status === "LOCKED" ? "Đã mở khóa." : "Đã khóa tài khoản.")}>
                      {a.status === "LOCKED" ? "Mở khóa" : "Khóa"}
                    </button>
                  ) : null}
                </div>
                <div className="account-list__action-slot">
                  {a.status !== "DISABLED" ? (
                    <button className="btn btn-secondary btn-sm" disabled={busy || reason.trim().length < 5}
                      onClick={() => void run(() => request(`/admin/users/${a.id}/disable`, context.user_id,
                        {method: "POST", body: JSON.stringify({reason})}), "Đã vô hiệu hóa tài khoản; hồ sơ vẫn được giữ.")}>
                      Vô hiệu hóa
                    </button>
                  ) : a.status === "DISABLED" && a.verified ? (
                    <button className="btn btn-secondary btn-sm" disabled={busy || reason.trim().length < 5}
                      onClick={() => void run(() => request(`/admin/users/${a.id}/restore`, context.user_id,
                        {method: "POST", body: JSON.stringify({reason})}), "Đã mở lại tài khoản cũ.")}>
                      Mở lại tài khoản
                    </button>
                  ) : null}
                </div>
                <div className="account-list__action-slot">
                  {a.status !== "LOCKED" ? (
                    <button className="btn btn-secondary btn-sm" disabled={busy || reason.trim().length < 5}
                      onClick={() => void run(async () => {
                        const result = await request<{link_sent: boolean}>(`/admin/users/${a.id}/reissue-link`, context.user_id,
                          {method: "POST", body: JSON.stringify({reason})});
                        return result.link_sent ? "Đã gửi liên kết mới." : "Chưa gửi được email; kiểm tra cấu hình thư.";
                      }, "Đã cấp lại liên kết.")}>
                      Cấp lại liên kết
                    </button>
                  ) : null}
                </div>
                <div className="account-list__action-slot">
                  <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => {setSelectedAccount(a.id); setNewEmail(a.email); setEmailReason(""); setOfficialRef(""); setEmailRoundId("");}}>
                    Sửa email
                  </button>
                </div>
              </>
            )}
          </div>
        </div>)}</div>
        {accounts.length ? <nav className="pagination" aria-label="Phân trang tài khoản">
          <button className="btn btn-secondary" disabled={busy || page === 0} onClick={() => setPage(page - 1)}>Trang trước</button>
          <span>Trang {page + 1}</span>
          <button className="btn btn-secondary" disabled={busy || !hasNext} onClick={() => setPage(page + 1)}>Trang sau</button>
        </nav> : <p>Không có tài khoản khớp tìm kiếm.</p>}
        {selectedAccount && (() => {
          const account = accountById(selectedAccount);
          if (!account) return null;
          const isStudent = account.base_role === "STUDENT";
          return <form className="core-form" onSubmit={e=>{e.preventDefault();
            void run(async()=>{
              const result = isStudent
                ? await request<{activation_sent:boolean}>(`/admin/users/${selectedAccount}/email`,context.user_id,
                    {method:"PATCH",body:JSON.stringify({round_id:emailRoundId,student_code:account.student_code,email:newEmail,basis_ref:officialRef,reason:emailReason.trim()})})
                : await request<{activation_sent:boolean}>(`/admin/users/${selectedAccount}/contact-email`,context.user_id,
                    {method:"PATCH",body:JSON.stringify({email:newEmail,basis_ref:officialRef,reason:emailReason.trim()})});
              setSelectedAccount("");
              return result.activation_sent
                ? "Đã sửa email trên tài khoản cũ và gửi liên kết kích hoạt."
                : "Đã sửa email trên tài khoản cũ; cần cấp lại liên kết khi email hoạt động.";
            },"Đã sửa email.");}}>
            <h3>{isStudent ? "Sửa email sinh viên trên tài khoản hiện có" : "Sửa email trên tài khoản hiện có"}</h3>
            <p className="text-muted">{isStudent
              ? "Đối chiếu MSSV và danh sách chính thức trước khi lưu. Mật khẩu, phiên đăng nhập và liên kết cũ sẽ mất hiệu lực."
              : "Chỉ ADMIN sửa sau khi đối chiếu căn cứ của Khoa. Giữ nguyên UUID và hồ sơ; mật khẩu, phiên đăng nhập và liên kết cũ mất hiệu lực."}</p>
            <p>{account.student_code ? `${account.student_code} · ` : ""}{account.email}</p>
            {isStudent && <label className="input-group">Đợt đối chiếu<select className="input" required value={emailRoundId} onChange={e=>setEmailRoundId(e.target.value)}>
              <option value="">Chọn đợt</option>{rounds.map(r=><option key={r.id} value={r.id}>{r.code}</option>)}</select></label>}
            <label className="input-group">Email mới<input className="input" type="email" required value={newEmail} onChange={e=>setNewEmail(e.target.value)} /></label>
            <label className="input-group">{isStudent ? "Căn cứ danh sách chính thức" : "Căn cứ xác minh của Khoa"}<input className="input" required minLength={3} value={officialRef} onChange={e=>setOfficialRef(e.target.value)} /></label>
            <label className="input-group">Lý do sửa email<input className="input" required minLength={5} value={emailReason} aria-describedby="email-reason-hint" onChange={e=>setEmailReason(e.target.value)} /></label>
            <p id="email-reason-hint" role="status" className="text-caption">{emailReason.trim().length < 5 ? "Nhập lý do sửa email ít nhất 5 ký tự để lưu." : "Đã đủ lý do sửa email."}</p>
            <button className="btn btn-primary" disabled={busy || !newEmail || emailReason.trim().length<5 || officialRef.trim().length<3 || (isStudent && !emailRoundId)}>Lưu email mới</button>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>setSelectedAccount("")}>Hủy sửa email</button>
          </form>;
        })()}
      </div></section>
    </div>
  </>;
}
