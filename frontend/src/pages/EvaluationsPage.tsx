import {useEffect,useState} from "react";
import {Link} from "react-router-dom";
import {ArrowRight, ClipboardCheck, RefreshCw, Search} from "lucide-react";
import {request,type Context} from "../api";
import {errorMessage} from "../errors";
import {labels,type EvaluationList} from "../evaluation";
import PageHeader from "../components/layout/PageHeader";

export default function EvaluationsPage({context}:{context:Context}) {
  const [data,setData]=useState<EvaluationList|null>(null),[query,setQuery]=useState(""),[offset,setOffset]=useState(0);
  const [error,setError]=useState(""),[loading,setLoading]=useState(true),[revision,setRevision]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();setLoading(true);setError("");
    const timer=setTimeout(()=>void request<EvaluationList>(`/evaluations?q=${encodeURIComponent(query)}&offset=${offset}`,context.user_id,{signal:controller.signal})
      .then(setData).catch(e=>{if(!controller.signal.aborted)setError(errorMessage(e));})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);}),250);
    return ()=>{clearTimeout(timer);controller.abort();};
  },[context.user_id,query,offset,revision]);
  return <div className="evaluation-page">
    <PageHeader title="Phản biện & điều kiện bảo vệ" description="Theo dõi phân công, nhận xét theo Mẫu 7–8 và kết quả xét điều kiện dự bảo vệ.">
      <button className="btn btn-secondary" disabled={loading} onClick={()=>setRevision(x=>x+1)}><RefreshCw size={16} aria-hidden="true"/>Làm mới</button>
    </PageHeader>
    <div className="evaluation-intro"><ClipboardCheck size={28} aria-hidden="true"/><div><strong>Hồ sơ rõ ràng, đúng người phụ trách</strong><p>{context.base_role==="STUDENT" ? "Bạn xem nhận xét đã gửi và kết quả xét của mình. Các phiếu nháp chỉ người viết được xem." : "TBM giao phản biện và xét điều kiện theo bộ môn. GVHD viết Mẫu 7; GV phản biện viết Mẫu 8 theo phân công."}</p></div></div>
    <label className="evaluation-search"><Search size={18} aria-hidden="true"/><span className="sr-only">Tìm khóa luận, sinh viên hoặc đợt</span><input value={query} maxLength={200} placeholder="Tìm tên khóa luận, mã sinh viên hoặc đợt…" onChange={e=>{setQuery(e.target.value);setOffset(0);}}/></label>
    {error&&<div className="alert alert-danger" role="alert">{error}<button className="btn btn-secondary" onClick={()=>setRevision(x=>x+1)}>Thử lại</button></div>}
    {loading?<p role="status">Đang tải hồ sơ phản biện…</p>:data&&!error?<>
      <p className="text-muted" role="status">{data.total} khóa luận trong phạm vi của bạn</p>
      {!data.items.length?<div className="evaluation-empty"><ClipboardCheck size={40} aria-hidden="true"/><h2>Chưa có hồ sơ phù hợp</h2><p>{query?"Thử tên hoặc mã sinh viên khác, hoặc xóa từ khóa tìm kiếm.":"Hồ sơ xuất hiện khi có khóa luận được tiếp nhận hoặc bạn được giao phản biện. TBM xem các khóa luận thuộc bộ môn."}</p>{query&&<button className="btn btn-secondary" onClick={()=>setQuery("")}>Xóa tìm kiếm</button>}</div>:<div className="evaluation-catalogue">{data.items.map(item=><article className="evaluation-card" key={item.id}>
        <div className="evaluation-card-heading"><small>{item.round_label}</small><span className={`evaluation-badge ${item.state==="READY_FOR_DEFENSE"?"is-success":""}`}>{labels[item.state]||item.state}</span></div>
        <h2><Link to={`/evaluation/${item.id}`}>{item.title}</Link></h2><p>{item.members.map(m=>`${m.name} (${m.code})`).join(" · ")}</p>
        <dl className="evaluation-facts"><div><dt>GV hướng dẫn</dt><dd>{item.advisor_name||"Chưa ghi nhận"}</dd></div><div><dt>GV phản biện</dt><dd>{item.reviewer_count}/2 đã phân công</dd></div><div><dt>Cuốn báo cáo</dt><dd>{item.report_available?"Đã nộp":"Chưa nộp"}</dd></div></dl>
        <Link className="btn btn-primary" to={`/evaluation/${item.id}`}>Mở hồ sơ<ArrowRight size={16} aria-hidden="true"/></Link>
      </article>)}</div>}
      {data.total>20&&<nav className="flex gap-3 items-center" aria-label="Phân trang hồ sơ"><button className="btn btn-secondary" disabled={offset===0} onClick={()=>setOffset(v=>Math.max(0,v-20))}>Trang trước</button><span>Trang {Math.floor(offset/20)+1}/{Math.ceil(data.total/20)}</span><button className="btn btn-secondary" disabled={offset+20>=data.total} onClick={()=>setOffset(v=>v+20)}>Trang sau</button></nav>}
    </>:null}
  </div>;
}
