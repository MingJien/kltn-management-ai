import {useCallback,useEffect,useState} from "react";
import {Link,useSearchParams} from "react-router-dom";
import {Eye,FileSpreadsheet,GraduationCap,PenLine,RefreshCw,Search,ShieldCheck,UserPlus} from "lucide-react";
import {request,type Context} from "../api";
import {errorMessage} from "../errors";
import {degreeLabels,profileMutation,type Directory,type LecturerProfile} from "../lecturerProfiles";
import PageHeader from "../components/layout/PageHeader";
import Dialog from "../components/ui/Dialog";
import LecturerImport from "../components/domain/LecturerImport";
import LecturerAvatar from "../components/domain/LecturerAvatar";
import LecturerProfileLink,{LecturerProfileDialog} from "../components/domain/LecturerProfileDialog";

export default function LecturerDirectoryPage({context}:{context:Context}) {
  const [params,setParams]=useSearchParams();const activation=params.get("tab")==="activation"&&context.base_role==="ADMIN";
  const [data,setData]=useState<Directory>({items:[],total:0,departments:[]}),[query,setQuery]=useState(""),[department,setDepartment]=useState(""),[status,setStatus]=useState("");
  const [offset,setOffset]=useState(0),[revision,setRevision]=useState(0),[loading,setLoading]=useState(true),[error,setError]=useState("");
  const [preview,setPreview]=useState<string|null>(null),[identity,setIdentity]=useState<LecturerProfile|null>(null);
  const admin=context.base_role==="ADMIN";
  const load=useCallback(async(signal?:AbortSignal)=>{const result=await request<Directory>(`/lecturer-directory?q=${encodeURIComponent(query)}&offset=${offset}${department?`&department_id=${department}`:""}${status?`&status=${status}`:""}`,context.user_id,{signal});if(!signal?.aborted)setData(result);},[context.user_id,query,offset,department,status]);
  useEffect(()=>{const c=new AbortController();setLoading(true);setError("");const timer=setTimeout(()=>void load(c.signal).catch(e=>{if(!c.signal.aborted)setError(errorMessage(e));}).finally(()=>{if(!c.signal.aborted)setLoading(false);}),200);return()=>{clearTimeout(timer);c.abort();};},[load,revision]);
  async function edit(id:string){setError("");try{setIdentity(await request<LecturerProfile>(`/lecturer-profiles/${id}`,context.user_id));}catch(e){setError(errorMessage(e));}}
  return <div className="lecturer-page"><PageHeader title="Danh sách giảng viên" description={admin?"Quản lý định danh, tài khoản và tra cứu hồ sơ chuyên môn đã được duyệt.":"Tra cứu giảng viên, lĩnh vực chuyên môn và thông tin liên hệ đã được Khoa duyệt."}>
    {context.actions.includes("lecturer:profile_review")&&<Link className="btn btn-primary" to="/lecturer-profile-reviews"><ShieldCheck size={16} aria-hidden="true"/>Duyệt hồ sơ GV</Link>}
    {admin&&<Link className="btn btn-primary" to="/administration"><UserPlus size={16} aria-hidden="true"/>Mời GV / quản lý tài khoản</Link>}
    <button className="btn btn-secondary" disabled={loading} onClick={()=>setRevision(x=>x+1)}><RefreshCw size={16} aria-hidden="true"/>Làm mới danh sách</button>
  </PageHeader>
  {admin&&<div className="lecturer-directory-tabs" role="tablist" aria-label="Quản lý giảng viên"><button role="tab" aria-selected={!activation} className={!activation?"is-active":""} onClick={()=>setParams({})}><GraduationCap size={17} aria-hidden="true"/>Danh sách và hồ sơ</button><button role="tab" aria-selected={activation} className={activation?"is-active":""} onClick={()=>setParams({tab:"activation"})}><FileSpreadsheet size={17} aria-hidden="true"/>Nhập Excel và kích hoạt</button></div>}
  {error&&<p className="alert alert-danger" role="alert">{error}</p>}
  {activation?<LecturerImport directoryMode userId={context.user_id} departments={data.departments} refreshVersion={revision} onCreated={async()=>{setRevision(x=>x+1);}}/>:<>
    <div className="lecturer-directory-toolbar"><label className="lecturer-search"><Search size={17} aria-hidden="true"/><input aria-label="Tìm giảng viên" placeholder={admin?"Tìm tên, mã GV hoặc email…":"Tìm tên hoặc mã giảng viên…"} maxLength={200} value={query} onChange={e=>{setQuery(e.target.value);setOffset(0);}}/></label>
      <label className="lecturer-field">Bộ môn<select aria-label="Lọc theo bộ môn" value={department} onChange={e=>{setDepartment(e.target.value);setOffset(0);}}><option value="">Tất cả bộ môn</option>{data.departments.map(d=><option value={d.id} key={d.id}>{d.name}</option>)}</select></label>
      {admin&&<label className="lecturer-field">Tài khoản<select aria-label="Lọc trạng thái tài khoản" value={status} onChange={e=>{setStatus(e.target.value);setOffset(0);}}><option value="">Tất cả trạng thái</option><option value="ACTIVE">Đang hoạt động</option><option value="LOCKED">Đang khóa</option><option value="DISABLED">Ngừng hoạt động</option></select></label>}
    </div>
    {loading?<p role="status">Đang tải danh sách giảng viên…</p>:!data.items.length?<div className="lecturer-empty"><GraduationCap size={36} aria-hidden="true"/><h2>Chưa có giảng viên phù hợp</h2><p>Thử từ khóa hoặc bộ môn khác.{admin?" Có thể mời GV hoặc nhập danh sách Excel để tạo tài khoản.":" Chỉ tài khoản GV đang hoạt động được hiển thị trong danh bạ."}</p></div>:<>
      <p className="text-caption" role="status">{data.total} giảng viên phù hợp · Hiển thị {offset+1}–{Math.min(offset+20,data.total)}</p>
      <div className="table-scroll" role="region" aria-label="Danh sách hồ sơ giảng viên" tabIndex={0}><table className="lecturer-directory-table"><thead><tr><th>Giảng viên</th><th>Bộ môn / Khoa</th><th>Trình độ, chuyên môn</th>{admin&&<th>Tài khoản</th>}<th>Hồ sơ</th><th>Xem chi tiết</th></tr></thead><tbody>{data.items.map(row=><tr key={row.id}>
        <td><div className="lecturer-directory-person"><LecturerAvatar url={row.avatar_url} name={row.display_name} size="sm"/><div><LecturerProfileLink lecturerId={row.id} name={row.display_name} userId={context.user_id}/><small>{row.lecturer_code}</small></div></div></td>
        <td>{row.department_name}<small>{row.faculty_name}</small></td><td>{row.data.academic_degree?degreeLabels[row.data.academic_degree]:"Chưa cập nhật"}<small>{row.data.specializations.slice(0,2).join(" · ")||"Chưa bổ sung chuyên môn"}{row.data.specializations.length>2?` +${row.data.specializations.length-2}`:""}</small></td>
        {admin&&<td>{row.account_email||"Chưa có email"}<small>{({ACTIVE:"Đang hoạt động",LOCKED:"Đang khóa",DISABLED:"Ngừng hoạt động"} as Record<string,string>)[row.account_status||""]||"Chưa ghi nhận"}</small></td>}
        <td><span className={`lecturer-verification ${row.verified_at?"is-verified":""}`}><ShieldCheck size={13} aria-hidden="true"/>{row.verified_at?"Đã duyệt":"Thông tin cơ bản"}</span></td>
        <td><div className="lecturer-table-actions"><button className="btn btn-secondary btn-sm" onClick={()=>setPreview(row.id)} aria-label={`Xem chi tiết ${row.display_name}`}><Eye size={15} aria-hidden="true"/>Xem chi tiết</button>{admin&&<button className="btn btn-ghost btn-sm" onClick={()=>void edit(row.id)} aria-label={`Sửa định danh ${row.display_name}`}><PenLine size={14} aria-hidden="true"/>Sửa thông tin gốc</button>}</div></td>
      </tr>)}</tbody></table></div>
      <nav className="lecturer-pagination" aria-label="Phân trang giảng viên"><button className="btn btn-secondary" disabled={!offset} onClick={()=>setOffset(v=>Math.max(0,v-20))}>Trang trước</button><span>Trang {Math.floor(offset/20)+1}/{Math.ceil(data.total/20)}</span><button className="btn btn-secondary" disabled={offset+20>=data.total} onClick={()=>setOffset(v=>v+20)}>Trang sau</button></nav>
    </>}
  </>}
  {preview&&<LecturerProfileDialog lecturerId={preview} userId={context.user_id} onClose={()=>setPreview(null)}/>}
  {identity&&<IdentityDialog initial={identity} departments={data.departments} userId={context.user_id} onClose={()=>setIdentity(null)} onSaved={()=>{setIdentity(null);setRevision(v=>v+1);}}/>}
  </div>;
}

function IdentityDialog({initial,departments,userId,onClose,onSaved}:{initial:LecturerProfile;departments:Directory["departments"];userId:string;onClose:()=>void;onSaved:()=>void}) {
  const [name,setName]=useState(initial.display_name),[code,setCode]=useState(initial.lecturer_code),[department,setDepartment]=useState(initial.department_id),[reason,setReason]=useState(""),[reference,setReference]=useState("");
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  async function save(e:React.FormEvent){e.preventDefault();if(busy)return;setBusy(true);setError("");try{await profileMutation(`/lecturer-directory/${initial.id}/identity`,userId,{display_name:name,lecturer_code:code,department_id:department,source_reference:reference,reason},initial.row_version,"PUT");onSaved();}catch(e){setError(errorMessage(e));}finally{setBusy(false);}}
  return <Dialog open title="Đối chiếu và sửa định danh GV" onClose={onClose} busy={busy} footer={<><button className="btn btn-secondary" disabled={busy} onClick={onClose}>Hủy</button><button className="btn btn-primary" type="submit" form="lecturer-identity-form" disabled={busy}>Lưu định danh</button></>}><form id="lecturer-identity-form" onSubmit={e=>void save(e)}>
    <p>Chỉ sửa theo danh sách chính thức. GV tự gửi thay đổi chuyên môn để Khoa duyệt trong trang tài khoản.</p>{error&&<p className="alert alert-danger" role="alert">{error}</p>}
    <label className="lecturer-field">Họ và tên<input required minLength={2} maxLength={255} value={name} onChange={e=>setName(e.target.value)}/></label>
    <label className="lecturer-field">Mã giảng viên<input required maxLength={32} value={code} onChange={e=>setCode(e.target.value)}/></label>
    <label className="lecturer-field">Bộ môn<select aria-label="Bộ môn định danh" value={department} onChange={e=>setDepartment(e.target.value)}>{departments.map(d=><option value={d.id} key={d.id}>{d.name}</option>)}</select></label>
    <p className="text-caption">Không điều chuyển trực tiếp bộ môn khi GV đã có hồ sơ/phân công nghiệp vụ. Đổi định danh có thể làm yêu cầu cập nhật đang chờ cần đối chiếu lại.</p>
    <label className="lecturer-field">Căn cứ / số văn bản<input required minLength={3} maxLength={500} value={reference} onChange={e=>setReference(e.target.value)}/></label>
    <label className="lecturer-field">Lý do chỉnh sửa<textarea required minLength={5} maxLength={2000} rows={3} value={reason} onChange={e=>setReason(e.target.value)}/></label>
    <p>Email đăng nhập: {initial.account_email||"Chưa có"}. <Link to="/administration">Đổi email hoặc khóa/mở tài khoản tại Quản lý tài khoản.</Link></p>
  </form></Dialog>;
}
