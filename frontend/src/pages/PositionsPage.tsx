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
  const [rows,setRows]=useState<Appointment[]>([]),[total,setTotal]=useState(0),[page,setPage]=useState(0);
  const [filter,setFilter]=useState(""),[department,setDepartment]=useState(""),[lecturer,setLecturer]=useState("");
  const [from,setFrom]=useState(""),[to,setTo]=useState(""),[basis,setBasis]=useState(""),[reason,setReason]=useState("");
  const [mode,setMode]=useState<"grant"|"replace"|"revoke">("grant"),[selected,setSelected]=useState<Appointment|null>(null);
  const [error,setError]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true);
  const load=useCallback(async(signal?:AbortSignal)=>{
    const [c,result]=await Promise.all([
      request<Catalog>("/admin/positions/catalog",context.user_id,{signal}),
      request<{items:Appointment[];total:number}>("/admin/positions?"+new URLSearchParams({...(filter?{department_id:filter}:{}),offset:String(page*SIZE),limit:String(SIZE)}),context.user_id,{signal})
    ]);
    if(!signal?.aborted){setCatalog(c);setRows(result.items);setTotal(result.total);}
  },[context.user_id,filter,page]);
  useEffect(()=>{const controller=new AbortController();setLoading(true);void load(controller.signal).catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[load]);
  const reset=()=>{setMode("grant");setSelected(null);setLecturer("");setFrom("");setTo("");setBasis("");setReason("");};
  const choose=(row:Appointment,action:"replace"|"revoke")=>{
    setSelected(row);setMode(action);setDepartment(row.department_id);setLecturer("");setFrom("");setTo("");setBasis("");setReason("");setError("");setNotice("");
    window.requestAnimationFrame(()=>document.getElementById("position-action-form")?.scrollIntoView({behavior:"smooth",block:"start"}));
  };
  const candidates=catalog.lecturers.filter(row=>row.department_id===department && (mode!=="replace" || row.id!==selected?.lecturer_id));
  async function submit(event:React.FormEvent){
    event.preventDefault();if(busy)return;setBusy(true);setError("");setNotice("");
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
    <div className="stack positions-page">
      <div className="alert alert-info"><ShieldCheck size={18}/> Chức vụ Trưởng bộ môn cấp quyền duyệt đề tài và hồ sơ GV trong đúng bộ môn. Không tự cấp quyền điều phối toàn đợt hoặc quản lý tài khoản. TBM có thể tự xác nhận hồ sơ chuyên môn của mình; hệ thống ghi rõ người xác nhận.</div>
      <div className="flex gap-2" style={{flexWrap:"wrap"}}><Link className="btn btn-secondary" to="/administration/assignments">Phân công theo đợt</Link><button className="btn btn-secondary" disabled={busy||loading} onClick={async()=>{setError("");setLoading(true);try{await load();}catch(cause){setError(errorMessage(cause));}finally{setLoading(false);}}}><RefreshCw size={16}/>Làm mới chức vụ</button></div>
      {error&&<p className="alert alert-danger" role="alert">{error}</p>}{notice&&<p className="alert alert-success" role="status">{notice}</p>}
      <section className="card positions-card"><div className="card-body stack">
        <h2><CalendarDays size={20}/> Quyết định và thời gian hiệu lực</h2>
        <label>Lọc theo bộ môn<select aria-label="Lọc theo bộ môn" className="input" value={filter} disabled={busy} onChange={event=>{setFilter(event.target.value);setPage(0);}}><option value="">Tất cả bộ môn</option>{catalog.departments.map(row=><option value={row.id} key={row.id}>{row.code} · {row.name}</option>)}</select></label>
        {loading?<p role="status">Đang tải chức vụ…</p>:<div className="table-container" role="region" aria-label="Danh sách bổ nhiệm Trưởng bộ môn" tabIndex={0}><table className="table" style={{minWidth:1100}}><thead><tr><th>Giảng viên</th><th>Chức vụ / phạm vi</th><th>Thời gian hiệu lực</th><th>Căn cứ bổ nhiệm</th><th>Trạng thái</th><th>Thao tác / lịch sử</th></tr></thead><tbody>{rows.map(row=><tr key={row.id}>
          <td><strong>{row.lecturer_name}</strong><div>{row.lecturer_code}</div></td><td>Trưởng bộ môn<div>{row.department_name}</div></td>
          <td>{formatDate(row.effective_from)}<div>Đến: {row.effective_to?formatDate(row.effective_to):"Chưa ấn định"}</div></td>
          <td style={{whiteSpace:"pre-wrap",minWidth:180}}>{row.basis_ref||"Chưa ghi nhận căn cứ trên hệ thống"}</td>
          <td><span className="badge badge-neutral">{statusLabels[row.status]||row.status}</span></td><td style={{minWidth:230}}>
            <div className="flex gap-2" style={{flexWrap:"wrap"}}>{["EFFECTIVE","SCHEDULED"].includes(row.status)&&<><button className="btn btn-secondary btn-sm" disabled={busy} onClick={()=>choose(row,"replace")}>Thay người</button><button className="btn btn-secondary btn-sm" disabled={busy} onClick={()=>choose(row,"revoke")}>{row.status==="SCHEDULED"?"Hủy bổ nhiệm chờ hiệu lực":"Thu hồi chức vụ"}</button></>}</div>
            <details><summary>Lịch sử quyết định</summary>{row.changes.length?row.changes.map((change,index)=><p key={index} style={{whiteSpace:"pre-wrap"}}><strong>{actionLabels[change.action]||change.action}</strong> · {formatDate(change.at)}<br/>Căn cứ: {change.basis_ref}<br/>{change.reason}</p>):<p>Quyết định có trước chức năng này; chưa có lịch sử thao tác mới.</p>}<Link to={"/activity?resource_type=position_assignment&resource_id="+row.id}>Xem nhật ký đầy đủ</Link></details>
          </td></tr>)}</tbody></table>{!rows.length&&<p>Chưa có quyết định trong phạm vi đã chọn.</p>}</div>}
        <div className="flex gap-2"><button className="btn btn-secondary" disabled={loading||busy||page===0} onClick={()=>setPage(value=>value-1)}>Trang trước</button><span>Trang {page+1} · {total} quyết định</span><button className="btn btn-secondary" disabled={loading||busy||(page+1)*SIZE>=total} onClick={()=>setPage(value=>value+1)}>Trang sau</button></div>
      </div></section>
      <section className="card positions-card"><div className="card-body stack">
        <h2><UserRoundPlus size={20}/>{mode==="grant"?"Ghi nhận bổ nhiệm Trưởng bộ môn":mode==="replace"?"Ghi nhận thay người giữ chức vụ":"Thu hồi bổ nhiệm"}</h2>
        {selected&&<p>Đang xử lý: <strong>{selected.lecturer_name}</strong> · {selected.department_name}. {mode==="replace"?"Quyết định cũ kết thúc theo thời điểm thay người; lịch sử xét duyệt vẫn được giữ.":"Thu hồi có hiệu lực ngay khi xác nhận; không xóa kết quả đã xử lý trước đó. Hủy quyết định tương lai không tự kéo dài hiệu lực quyết định cũ đã được ấn định."}</p>}
        <form id="position-action-form" className="core-form positions-form" onSubmit={event=>void submit(event)}>
          {mode!=="revoke"&&<><label>Bộ môn bổ nhiệm<select aria-label="Bộ môn bổ nhiệm" className="input" required value={department} disabled={busy||mode==="replace"} onChange={event=>{setDepartment(event.target.value);setLecturer("");}}><option value="">Chọn bộ môn</option>{catalog.departments.map(row=><option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}</select></label>
          <label>Giảng viên được bổ nhiệm<select aria-label="Giảng viên được bổ nhiệm" className="input" required value={lecturer} disabled={busy||!department} onChange={event=>setLecturer(event.target.value)}><option value="">Chọn giảng viên đang hoạt động thuộc bộ môn</option>{candidates.map(row=><option key={row.id} value={row.id}>{row.code} · {row.name}{row.email?" · "+row.email:""}</option>)}</select></label>
          {department&&!candidates.length&&<p role="status">Chưa có tài khoản GV phù hợp trong bộ môn. Kiểm tra thông tin gốc và trạng thái tài khoản trước khi bổ nhiệm.</p>}
          <label>Bắt đầu hiệu lực (giờ Việt Nam)<input className="input" type="datetime-local" value={from} disabled={busy} onChange={event=>setFrom(event.target.value)}/></label><small>Để trống để áp dụng ngay khi lưu; chọn thời điểm tương lai để hẹn hiệu lực. Không ghi lùi thời gian cấp quyền.</small>
          <label>Kết thúc hiệu lực (không bắt buộc)<input className="input" type="datetime-local" value={to} disabled={busy} onChange={event=>setTo(event.target.value)}/></label></>}
          <label>Căn cứ / số quyết định<input className="input" required minLength={3} maxLength={500} value={basis} disabled={busy} onChange={event=>setBasis(event.target.value)}/></label>
          <label>Nội dung ghi nhận / lý do<textarea className="input" required minLength={5} maxLength={2000} rows={3} disabled={busy} value={reason} onChange={event=>setReason(event.target.value)}/></label>
          <div className="flex gap-2"><button className="btn btn-primary" disabled={busy||basis.trim().length<3||reason.trim().length<5||(mode!=="revoke"&&(!department||!lecturer))}>{busy?"Đang lưu…":mode==="grant"?"Lưu bổ nhiệm":mode==="replace"?"Xác nhận thay người":"Xác nhận thu hồi"}</button>{selected&&<button type="button" className="btn btn-secondary" disabled={busy} onClick={reset}>Hủy thao tác</button>}</div>
        </form>
      </div></section>
    </div></>;
}
