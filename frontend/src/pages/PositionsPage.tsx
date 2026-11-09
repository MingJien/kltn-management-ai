import AssignmentTabs from "../components/layout/AssignmentTabs";
import {useCallback,useEffect,useState} from "react";
import {Link} from "react-router-dom";
import {CalendarDays,RefreshCw,ShieldCheck,UserRoundPlus} from "lucide-react";
import type {Context} from "../api";
import {request} from "../api";
import {errorMessage} from "../errors";
import PageHeader from "../components/layout/PageHeader";
import "../styles/positions.css";
import {formatDate} from "../components/domain/CoreForms";

type Catalog={departments:{id:string;code:string;name:string}[];lecturers:{id:string;user_id:string;department_id:string;name:string;code:string;email:string|null}[]};
type Appointment={id:string;row_version:number;lecturer_id:string;lecturer_name:string;lecturer_code:string;department_id:string;department_name:string;effective_from:string;effective_to:string|null;state:string;status:string;basis_ref:string|null;changes:{action:string;at:string;reason:string|null;basis_ref:string|null}[]};
const statusLabels:Record<string,string>={EFFECTIVE:"Đang hiệu lực",SCHEDULED:"Chờ hiệu lực",EXPIRED:"Đã hết hạn",REVOKED:"Đã thu hồi / thay người"};
const actionLabels:Record<string,string>={POSITION_ASSIGNED:"Ghi nhận bổ nhiệm",POSITION_REPLACED:"Thay người",POSITION_REVOKED:"Thu hồi bổ nhiệm"};
const SIZE=20;

export default function PositionsPage({context}:{context:Context}){
  const [catalog,setCatalog]=useState<Catalog>({departments:[],lecturers:[]});
  const [rows,setRows]=useState<Appointment[]>([]),[available,setAvailable]=useState<Appointment[]>([]),[total,setTotal]=useState(0),[page,setPage]=useState(0);
  const [filter,setFilter]=useState(""),[department,setDepartment]=useState(""),[lecturer,setLecturer]=useState("");
  const [from,setFrom]=useState(""),[to,setTo]=useState(""),[basis,setBasis]=useState(""),[reason,setReason]=useState("");
  const [mode,setMode]=useState<"grant"|"replace"|"revoke">("grant"),[selected,setSelected]=useState<Appointment|null>(null);
  const [error,setError]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true);
  const [listLoaded,setListLoaded]=useState(false),[availableError,setAvailableError]=useState("");
  const load=useCallback(async(signal?:AbortSignal)=>{
    const [c,result,eligible]=await Promise.all([
      request<Catalog>("/admin/positions/catalog",context.user_id,{signal}),
      request<{items:Appointment[];total:number}>("/admin/positions?"+new URLSearchParams({...(filter?{department_id:filter}:{}),offset:String(page*SIZE),limit:String(SIZE)}),context.user_id,{signal}),
      request<Appointment[]>("/admin/positions/available",context.user_id,{signal})
        .then(items=>({items,error:""}))
        .catch(cause=>({items:[] as Appointment[],error:errorMessage(cause)}))
    ]);
    if(!signal?.aborted){setCatalog(c);setRows(result.items);setTotal(result.total);setListLoaded(true);setAvailable(eligible.items);setAvailableError(eligible.error);}
  },[context.user_id,filter,page]);
  useEffect(()=>{const controller=new AbortController();setLoading(true);setListLoaded(false);void load(controller.signal).catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[load]);
  const reset=()=>{setMode("grant");setSelected(null);setLecturer("");setFrom("");setTo("");setBasis("");setReason("");};
  const switchMode=(action:"grant"|"replace"|"revoke")=>{
    setMode(action);setSelected(null);setDepartment("");setLecturer("");setFrom("");setTo("");setBasis("");setReason("");setError("");setNotice("");
  };
  const choose=(id:string)=>{
    const row=available.find(item=>item.id===id) || null;
    setSelected(row);setDepartment(row?.department_id || "");setLecturer("");setFrom("");setTo("");setBasis("");setReason("");
  };
  const candidates=catalog.lecturers.filter(row=>row.department_id===department && (mode!=="replace" || row.id!==selected?.lecturer_id));
  async function submit(event:React.FormEvent){
    event.preventDefault();if(busy || (mode!=="grant" && !selected))return;setBusy(true);setError("");setNotice("");
    try{
      const data={lecturer_id:lecturer,effective_from:from?new Date(from+"+07:00").toISOString():null,effective_to:to?new Date(to+"+07:00").toISOString():null,basis_ref:basis,reason};
      await request(mode==="grant"?"/admin/positions":"/admin/positions/"+selected!.id+"/"+mode,context.user_id,{
        method:"POST",headers:selected?{"If-Match":String(selected.row_version)}:{},
        body:JSON.stringify(mode==="revoke"?{basis_ref:basis,reason}:mode==="grant"?{...data,department_id:department}:data)
      });
      const message=mode==="revoke"?"Đã thu hồi bổ nhiệm; giữ nguyên hồ sơ và lịch sử.":mode==="replace"?"Đã ghi nhận thay người; quyền áp dụng theo thời gian hiệu lực.":"Đã ghi nhận bổ nhiệm; quyền áp dụng theo thời gian hiệu lực.";
      reset();await load();setNotice(message);
    }catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}
  }
  return <><PageHeader title="Chức vụ và phạm vi" description="Ghi nhận bổ nhiệm Trưởng bộ môn theo căn cứ của Khoa; quản lý thời gian hiệu lực, thay người và lịch sử."/>
    <AssignmentTabs />
    <div className="stack positions-page">
      <aside className="positions-info"><ShieldCheck size={20} aria-hidden="true"/><div><strong>Phạm vi của Trưởng bộ môn</strong><p>Được duyệt đề tài và hồ sơ giảng viên thuộc bộ môn. Quyền điều phối đợt và quản lý tài khoản được phân công riêng. TBM có thể tự xác nhận hồ sơ chuyên môn, hệ thống ghi rõ người xác nhận.</p></div></aside>
      {error&&<p className="alert alert-danger" role="alert">{error}</p>}{notice&&<p className="alert alert-success" role="status">{notice}</p>}
      <section className="card positions-card"><div className="card-body stack">
        <div className="positions-section-heading"><div><h2><CalendarDays size={20}/> Quyết định và thời gian hiệu lực</h2><p>Theo dõi người được bổ nhiệm và lịch sử thay đổi theo bộ môn.</p></div>
          <button className="btn btn-secondary" disabled={busy||loading} onClick={async()=>{setError("");setLoading(true);try{await load();}catch(cause){setError(errorMessage(cause));}finally{setLoading(false);}}}><RefreshCw size={16}/>Làm mới</button>
        </div>
        <div className="positions-filter"><label>Lọc theo bộ môn<select aria-label="Lọc theo bộ môn" className="input" value={filter} disabled={busy} onChange={event=>{setFilter(event.target.value);setPage(0);}}><option value="">Tất cả bộ môn</option>{catalog.departments.map(row=><option value={row.id} key={row.id}>{row.code} · {row.name}</option>)}</select></label><span>{total} quyết định</span></div>
        <p className="positions-scroll-hint">Kéo bảng sang ngang để xem thời gian, căn cứ và trạng thái.</p>
        {loading?<p role="status">Đang tải chức vụ…</p>:!listLoaded?<p role="alert">Không tải được danh sách quyết định. Hãy kiểm tra kết nối và bấm Làm mới.</p>:<div className="table-container" role="region" aria-label="Danh sách bổ nhiệm Trưởng bộ môn" tabIndex={0}><table className="table positions-table"><thead><tr><th>Giảng viên</th><th>Chức vụ / phạm vi</th><th>Thời gian hiệu lực</th><th>Căn cứ bổ nhiệm</th><th>Trạng thái</th></tr></thead><tbody>{rows.map(row=><tr key={row.id}>
          <td><strong>{row.lecturer_name}</strong><small>{row.lecturer_code}</small></td><td><strong>Trưởng bộ môn</strong><small>{row.department_name}</small></td>
          <td><span>Từ {formatDate(row.effective_from)}</span><small>Đến {row.effective_to?formatDate(row.effective_to):"chưa ấn định"}</small></td>
          <td className="positions-table__basis">{row.basis_ref||"Chưa ghi nhận căn cứ trên hệ thống"}</td>
          <td><span className={"positions-status positions-status--"+row.status.toLowerCase()}>{statusLabels[row.status]||row.status}</span></td></tr>)}</tbody></table>{!rows.length&&<p className="positions-empty">Chưa có quyết định trong phạm vi đã chọn.</p>}</div>}
        <div className="positions-pagination"><button className="btn btn-secondary" disabled={loading||busy||page===0} onClick={()=>setPage(value=>value-1)}>Trang trước</button><span>Trang {page+1} · {total} quyết định</span><button className="btn btn-secondary" disabled={loading||busy||(page+1)*SIZE>=total} onClick={()=>setPage(value=>value+1)}>Trang sau</button></div>
      </div></section>
      <nav className="positions-task-tabs" aria-label="Thao tác chức vụ">
        <button type="button" className={mode==="grant"?"is-active":""} aria-current={mode==="grant"?"page":undefined} disabled={busy} onClick={()=>switchMode("grant")}>Bổ nhiệm</button>
        <button type="button" className={mode==="replace"?"is-active":""} aria-current={mode==="replace"?"page":undefined} disabled={busy} onClick={()=>switchMode("replace")}>Thay người</button>
        <button type="button" className={mode==="revoke"?"is-active":""} aria-current={mode==="revoke"?"page":undefined} disabled={busy} onClick={()=>switchMode("revoke")}>Thu hồi chức vụ</button>
      </nav>
      <section className="card positions-card"><div className="card-body stack">
        <div className="positions-section-heading"><div><h2><UserRoundPlus size={20}/>{mode==="grant"?"Ghi nhận bổ nhiệm Trưởng bộ môn":mode==="replace"?"Ghi nhận thay người giữ chức vụ":"Thu hồi bổ nhiệm"}</h2><p>Nhập thông tin theo căn cứ bổ nhiệm của Khoa hoặc Trường.</p></div></div>
        {mode!=="grant" && <label className="positions-decision-picker">Quyết định cần {mode==="replace"?"thay người":"thu hồi"}
          <select aria-label="Quyết định cần xử lý" className="input" value={selected?.id || ""} disabled={busy || loading} onChange={event=>choose(event.target.value)}>
            <option value="">Chọn quyết định đang hoặc sắp hiệu lực</option>
            {available.map(row=><option key={row.id} value={row.id}>{row.department_name} · {row.lecturer_name} ({row.lecturer_code}) · {statusLabels[row.status]} · từ {formatDate(row.effective_from)}</option>)}
          </select>
          {availableError ? <small role="alert">Không tải được danh sách quyết định để thay người hoặc thu hồi. Kiểm tra API và bấm Làm mới.</small> : !loading && !available.length && <small>Chưa có quyết định đang hoặc sắp hiệu lực.</small>}
        </label>}
        {selected&&<p className="positions-selected">Đang xử lý: <strong>{selected.lecturer_name}</strong> · {selected.department_name}. {mode==="replace"?"Quyết định cũ kết thúc theo thời điểm thay người; lịch sử xét duyệt vẫn được giữ.":"Thu hồi có hiệu lực ngay khi xác nhận; không xóa kết quả đã xử lý trước đó. Hủy quyết định tương lai không tự kéo dài hiệu lực quyết định cũ đã được ấn định."}</p>}
        <form id="position-action-form" className="core-form positions-form" onSubmit={event=>void submit(event)}>
          {mode!=="revoke"&&<><label>Bộ môn bổ nhiệm<select aria-label="Bộ môn bổ nhiệm" className="input" required value={department} disabled={busy||mode==="replace"} onChange={event=>{setDepartment(event.target.value);setLecturer("");}}><option value="">Chọn bộ môn</option>{catalog.departments.map(row=><option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}</select></label>
          <label>Giảng viên được bổ nhiệm<select aria-label="Giảng viên được bổ nhiệm" className="input" required value={lecturer} disabled={busy||!department} onChange={event=>setLecturer(event.target.value)}><option value="">Chọn giảng viên đang hoạt động thuộc bộ môn</option>{candidates.map(row=><option key={row.id} value={row.id}>{row.code} · {row.name}{row.email?" · "+row.email:""}</option>)}</select></label>
          {department&&!candidates.length&&<p role="status">Chưa có tài khoản GV phù hợp trong bộ môn. Kiểm tra thông tin gốc và trạng thái tài khoản trước khi bổ nhiệm.</p>}
          <label>Bắt đầu hiệu lực (giờ Việt Nam)<input aria-label="Bắt đầu hiệu lực (giờ Việt Nam)" className="input" type="datetime-local" value={from} disabled={busy} onChange={event=>setFrom(event.target.value)}/><small>Để trống để áp dụng ngay; có thể chọn thời điểm tương lai. Không ghi lùi thời gian cấp quyền.</small></label>
          <label>Kết thúc hiệu lực (không bắt buộc)<input className="input" type="datetime-local" value={to} disabled={busy} onChange={event=>setTo(event.target.value)}/></label></>}
          <label>Căn cứ / số quyết định<input className="input" required minLength={3} maxLength={500} value={basis} disabled={busy} placeholder="Ví dụ: Số quyết định bổ nhiệm của Khoa / Trường" onChange={event=>setBasis(event.target.value)}/></label>
          <label>Nội dung ghi nhận / lý do<textarea className="input" required minLength={5} maxLength={2000} rows={3} disabled={busy} value={reason} onChange={event=>setReason(event.target.value)}/></label>
          <div className="positions-form__actions"><button className="btn btn-primary" disabled={busy||basis.trim().length<3||reason.trim().length<5||(mode!=="grant"&&!selected)||(mode!=="revoke"&&(!department||!lecturer))}>{busy?"Đang lưu…":mode==="grant"?"Lưu bổ nhiệm":mode==="replace"?"Xác nhận thay người":"Xác nhận thu hồi"}</button>{selected&&<button type="button" className="btn btn-secondary" disabled={busy} onClick={reset}>Hủy thao tác</button>}</div>
        </form>
      </div></section>
      <section className="card positions-card positions-history"><div className="card-body stack">
        <div className="positions-section-heading"><div><h2>Lịch sử quyết định</h2><p>Các quyết định trên trang hiện tại theo bộ lọc và phân trang ở trên.</p></div></div>
        {rows.length ? rows.map(row=><details key={row.id}>
          <summary>{row.lecturer_name} · {row.department_name} · {statusLabels[row.status] || row.status} · từ {formatDate(row.effective_from)}</summary>
          <div className="positions-history__body">{row.changes.length ? row.changes.map((change,index)=><p key={index}><strong>{actionLabels[change.action]||change.action}</strong> · {formatDate(change.at)}<br/>Căn cứ: {change.basis_ref || "Chưa ghi nhận"}<br/>{change.reason}</p>) : <p>Quyết định có trước chức năng này; chưa có lịch sử thao tác mới.</p>}
          <Link to={"/activity?resource_type=position_assignment&resource_id="+row.id}>Xem nhật ký đầy đủ</Link></div>
        </details>) : <p className="text-muted">{loading?"Đang tải lịch sử…":"Chưa có quyết định trong phạm vi đã chọn."}</p>}
      </div></section>
    </div></>;
}
