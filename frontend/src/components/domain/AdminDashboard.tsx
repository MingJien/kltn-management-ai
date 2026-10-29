import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { request } from "../../api";
import { errorMessage } from "../../errors";
import { Status } from "./CoreForms";
type Summary={generated_at:string;accounts:Record<string,number>;account_status:Record<string,number>;rounds:Record<string,number>;topics:Record<string,number>;registrations:Record<string,number>;theses:Record<string,number>;documents:Record<string,number>;reports:Record<string,number>};
const total=(rows:Record<string,number>)=>Object.values(rows).reduce((a,b)=>a+b,0);
export default function AdminDashboard({userId}:{userId:string}){
 const [data,setData]=useState<Summary|null>(null),[error,setError]=useState(""),[loading,setLoading]=useState(false);
 const load=useCallback(async(signal?:AbortSignal)=>{setLoading(true);try{const result=await request<Summary>("/admin/dashboard",userId,{signal});if(!signal?.aborted){setData(result);setError("");}}catch(e){if(!signal?.aborted)setError(errorMessage(e));}finally{if(!signal?.aborted)setLoading(false);}},[userId]);
 useEffect(()=>{const c=new AbortController();void load(c.signal);return()=>c.abort();},[load]);
 return <section className="stack" aria-label="Thống kê quản trị"><div className="workspace-section-head"><div><span className="section-eyebrow">DỮ LIỆU HỆ THỐNG</span><h2>Thống kê hiện tại</h2></div><button className="btn btn-secondary" disabled={loading} onClick={()=>void load()}><RefreshCw size={16}/>Làm mới thống kê</button></div>
 {error && <p className="alert alert-danger" role="alert">{error}</p>}{loading && !data && <p role="status">Đang tổng hợp dữ liệu…</p>}
 {data && <><div className="dashboard-metrics">{[["Sinh viên",data.accounts.STUDENT||0,"/roster"],["Giảng viên",data.accounts.LECTURER||0,"/lecturers"],["Đề tài",total(data.topics),"/topics"],["Khóa luận",total(data.theses),null]].map(([label,count,to])=><div className="card metric-card" key={String(label)}><span>{label}</span><strong>{count}</strong>{to && <Link to={String(to)}>Xem danh sách →</Link>}</div>)}</div>
 <div className="dashboard-breakdown">{([["Tài khoản",data.account_status],["Đợt KLTN",data.rounds],["Đề tài",data.topics],["Hồ sơ đăng ký",data.registrations],["Khóa luận",data.theses],["Phiên bản tài liệu",data.documents],["Lần nộp báo cáo tiến độ",data.reports]] as [string,Record<string,number>][]).map(([label,rows])=><article className="card" key={label}><div className="card-body"><h3>{label} <span className="text-muted">({total(rows)})</span></h3><ul className="dashboard-status-list">{Object.entries(rows).map(([status,count])=><li key={status}><Status value={status} label={label==="Tài khoản" && status==="ACTIVE"?"Đang hoạt động":status==="PENDING_ACTIVATION"?"Chờ kích hoạt":label==="Đề tài" && status==="ARCHIVED"?"Ngừng sử dụng":undefined}/><strong>{count}</strong></li>)}{!Object.keys(rows).length && <li>Chưa có dữ liệu</li>}</ul></div></article>)}</div>
 <p className="text-caption">Cập nhật: {new Date(data.generated_at).toLocaleString("vi-VN")}. Đếm toàn hệ thống, bao gồm dữ liệu DEMO đang lưu. Báo cáo tiến độ/tài liệu tính theo từng lần nộp, không phải số sinh viên.</p></>}
 </section>;
}
