import LecturerProfileLink from "../components/domain/LecturerProfileDialog";
import {lazy,Suspense,useCallback,useEffect,useState} from "react";
import {Link,useParams} from "react-router-dom";
import {ArrowLeft,CheckCircle2,ClipboardCheck,Download,Eye,FileText,Plus,RefreshCw,ShieldCheck,Users,XCircle} from "lucide-react";
import {exportThesisReview,request,type Context} from "../api";
import {errorMessage} from "../errors";
import {downloadEvaluationFile,labels,mutate,when,type Evaluation,type Kind,type Review} from "../evaluation";
import PageHeader from "../components/layout/PageHeader";
import Dialog from "../components/ui/Dialog";
import ThesisReviewEditor from "../components/domain/ThesisReviewEditor";
const Preview=lazy(()=>import("../components/domain/ReviewAttachmentPreview").then(module=>({default:module.ReadOnlyFilePreview})));
type Operation={kind:"assign"}|{kind:"extend";id:string;name:string;due:string|null}|{kind:"revoke";id:string;name:string}|{kind:"check"}|{kind:"reopen"}|{kind:"create";role:Kind};

export default function EvaluationPage({context}:{context:Context}) {
  const {thesisId}=useParams();
  return <Workspace key={`${context.user_id}:${thesisId}`} context={context} thesisId={thesisId!}/>;
}

function Workspace({context,thesisId}:{context:Context;thesisId:string}) {
  const [data,setData]=useState<Evaluation|null>(null),[error,setError]=useState(""),[message,setMessage]=useState("");
  const [busy,setBusy]=useState(false),[memberId,setMemberId]=useState(""),[operation,setOperation]=useState<Operation|null>(null),[editor,setEditor]=useState<Review|null>(null);
  const [paperReview,setPaperReview]=useState<Review|null>(null);
  const [preview,setPreview]=useState<{name:string;path:string}|null>(null);
  const path=`/theses/${thesisId}/evaluation`;
  const load=useCallback(async(signal?:AbortSignal)=>{
    const result=await request<Evaluation>(path,context.user_id,{signal});
    if(!signal?.aborted){setData(result);setMemberId(old=>result.members.some(m=>m.id===old)?old:result.members[0]?.id||"");}
  },[path,context.user_id]);
  useEffect(()=>{const controller=new AbortController();void load(controller.signal).catch(e=>{if(!controller.signal.aborted)setError(errorMessage(e));});return()=>controller.abort();},[load]);
  async function run(action:()=>Promise<unknown>,success:string){
    if(busy)return;setBusy(true);setError("");setMessage("");
    try{await action();await load();setMessage(success);return true;}catch(e){setError(errorMessage(e));return false;}finally{setBusy(false);}
  }
  const fileAction=(name:string,url:string)=>void run(()=>downloadEvaluationFile(url,name),"Đã tải tệp.");
  if(!data)return <div className="evaluation-page"><Link to="/evaluation">← Danh sách hồ sơ</Link>{error?<div className="alert alert-danger" role="alert">{error}<button className="btn btn-secondary" disabled={busy} onClick={()=>void run(()=>load(),"Đã tải dữ liệu.")}>Thử lại</button></div>:<p role="status">Đang tải hồ sơ phản biện…</p>}</div>;
  const can=(action:string)=>data.actions.includes(`evaluation:${action}`);
  const member=data.members.find(m=>m.id===memberId),eligibility=member?.eligibility;
  const active=data.assignments.filter(a=>a.state==="ACTIVE");
  const open=["ACTIVE","PROPOSAL_APPROVED","IN_PROGRESS","EXTENDED"].includes(data.state);
  const reviewOpen=open||data.state==="READY_FOR_DEFENSE";
  const blocked=data.workflow_blockers.length>0;
  const reviews=data.reviews.filter(r=>r.thesis_member_id===memberId);
  const currentReviews=reviews.filter(r=>r.report_version_id===data.report?.id);
  const oldReviews=reviews.filter(r=>r.report_version_id!==data.report?.id);
  function reviewCard(review:Review){
    const current=review.report_version_id===data!.report?.id;
    return <article className="evaluation-review" key={review.id}><div className="evaluation-card-heading"><strong>Mẫu {review.kind==="ADVISOR"?"7 · GVHD":"8 · Phản biện"} · Phiếu v{review.version_no}</strong><span className={`evaluation-badge ${review.state==="SUBMITTED"?"is-success":""}`}>{labels[review.state]}</span></div>
      <p>{review.lecturer_name} · {current?`Báo cáo v${data!.report?.version_no}`:"Bản báo cáo trước"}{review.submitted_at?` · ${when(review.submitted_at)}`:""}</p>
      {review.can_edit?<button className="btn btn-primary btn-sm" disabled={busy} onClick={()=>setEditor(review)}>Tiếp tục viết phiếu</button>:review.state==="DRAFT"?<p className="text-muted">Phiếu nháp thuộc bản báo cáo hoặc phân công cũ, giữ để đối chiếu.</p>:null}
      <details><summary>Xem nội dung phiếu</summary><dl className="evaluation-review-content">{data!.form_fields[review.kind].map(f=><div key={f.key}><dt>{f.label}</dt><dd>{review.sections[f.key]||"Chưa nhập"}</dd></div>)}</dl>
        {review.kind==="ADVISOR"&&<p><strong>{review.thesis_completed?"Đã hoàn thành KLTN":"Chưa hoàn thành KLTN"} · {review.allow_defense?"Đồng ý cho bảo vệ":"Không đồng ý cho bảo vệ"}</strong></p>}
        <p>Lý do lập phiếu: {review.revision_reason}</p>{review.source_reference&&<p>Căn cứ: {review.source_reference}</p>}
      </details>
      {review.state==="SUBMITTED"&&<div className="evaluation-note">
        <strong>{review.paper_receipt?"Đã đối chiếu bản giấy":review.signed_file?.scan_state==="CLEAN"?"Đã có bản ký đính kèm":"Chờ đối chiếu bản ký"}</strong>
        {review.paper_receipt&&<p>{review.paper_receipt.reference} · {review.paper_receipt.confirmed_by} · {when(review.paper_receipt.confirmed_at)}<br/>Mã bản xuất: {review.paper_receipt.export_code}</p>}
        {(can("record")||review.lecturer_id===context.lecturer_id)&&<button className="btn btn-secondary btn-sm" disabled={busy} onClick={()=>void run(()=>exportThesisReview(thesisId,review.id,review.row_version),"Đã xuất đúng phiên bản phiếu; mã xuất nằm trong lịch sử.")}>Xuất phiếu đã gửi để ký</button>}
        {can("record")&&!review.paper_receipt&&<button className="btn btn-primary btn-sm" disabled={busy||!review.export_history.length} onClick={()=>setPaperReview(review)}>Ghi nhận bản giấy</button>}
        {!review.export_history.length&&can("record")&&<p>Xuất phiếu hiện tại trước khi đối chiếu bản giấy.</p>}
      </div>}
      {!!review.export_history.length&&<details><summary>Lịch sử xuất phiếu ({review.export_history.length})</summary>{review.export_history.map(e=><p key={e.code}><strong>{e.code}</strong> · {when(e.at)}</p>)}</details>}
      {review.signed_file&&<div className="evaluation-file-actions"><span>{review.signed_file.name} · {labels[review.signed_file.scan_state]}</span><button className="btn btn-secondary btn-sm" disabled={busy||review.signed_file.scan_state!=="CLEAN"} onClick={()=>setPreview({name:review.signed_file!.name,path:`${path}/reviews/${review.id}/signed-copy`})}><Eye size={15} aria-hidden="true"/>Xem bản ký</button><button className="btn btn-secondary btn-sm" disabled={busy||review.signed_file.scan_state!=="CLEAN"} onClick={()=>fileAction(review.signed_file!.name,`${path}/reviews/${review.id}/signed-copy`)}><Download size={15} aria-hidden="true"/>Tải bản ký</button></div>}
    </article>;
  }
  return <div className="evaluation-page">
    <Link className="workspace-back-link" to="/evaluation"><ArrowLeft size={16} aria-hidden="true"/>Danh sách phản biện</Link>
    <PageHeader title="Phản biện & điều kiện bảo vệ" description={`${data.title} · Đợt ${data.round_label}`}><button className="btn btn-secondary" disabled={busy} onClick={()=>void run(()=>load(),"Đã làm mới hồ sơ.")}><RefreshCw size={16} aria-hidden="true"/>Làm mới</button></PageHeader>
    {error&&<p role="alert" className="alert alert-danger">{error}</p>}{message&&<p role="status" className="alert alert-success">{message}</p>}
    {blocked&&<section className="evaluation-note" aria-labelledby="membership-update-heading"><h2 id="membership-update-heading">Cập nhật hồ sơ sau điều chỉnh</h2><p>Hồ sơ có thay đổi đề tài hoặc thành viên. Hoàn tất các mục sau để lập phiếu nhận xét và chốt đủ điều kiện bảo vệ. TBM vẫn có thể ghi nhận tình trạng kỷ luật trong lúc chờ.</p><ol>{data.workflow_blockers.map(item=><li key={item.key}>{item.message}</li>)}</ol>{(context.base_role==="STUDENT"||can("advisor")||can("manage"))&&<div className="flex gap-2"><Link className="btn btn-secondary" to={`/theses/${thesisId}?section=submissions&kind=PROPOSAL`}>Mở đề cương để cập nhật / duyệt lại</Link><Link className="btn btn-secondary" to={`/theses/${thesisId}?section=submissions&kind=REPORT`}>Mở báo cáo cần cập nhật</Link></div>}</section>}
    <details className="evaluation-note"><summary>Hướng dẫn thao tác theo vai trò</summary><ol><li>SV nộp cuốn báo cáo đã cập nhật; tệp phải được quét an toàn.</li><li>TBM phân công GV phản biện; người được giao nhận thông báo ở biểu tượng chuông.</li><li>GVHD lập Mẫu 7, GVPB lập Mẫu 8 cho từng sinh viên: lưu nháp → kiểm tra và gửi. Xuất phiếu để ký ngoài; cán bộ tiếp nhận/TBM ghi nhận bản giấy, không bắt tải lại bản quét.</li><li>TBM chọn từng sinh viên, đối chiếu căn cứ rồi xét và lưu điều kiện. Nhóm chỉ sẵn sàng khi tất cả thành viên đang thực hiện đều đủ điều kiện.</li><li>SV mở chuông thông báo hoặc hồ sơ này để xem nhận xét và kết quả của mình.</li></ol></details>
    <div className="evaluation-steps" aria-label="Các bước xử lý"><div><Users aria-hidden="true"/><strong>1. Phân công</strong><span>{active.length}/2 GV phản biện</span></div><div><FileText aria-hidden="true"/><strong>2. Nhận xét theo mẫu</strong><span>GVHD: Mẫu 7 · Phản biện: Mẫu 8</span></div><div><ShieldCheck aria-hidden="true"/><strong>3. Xét điều kiện</strong><span>{labels[data.state]||data.state}</span></div></div>
    {blocked&&(context.base_role==="STUDENT"||can("advisor")||can("manage"))&&<div className="flex gap-2"><Link className="btn btn-secondary" to={`/theses/${thesisId}?section=submissions&kind=REGISTRATION`}>Cập nhật Mẫu 1a/1b</Link><Link className="btn btn-secondary" to={`/theses/${thesisId}?section=submissions&kind=PLAN`}>Cập nhật kế hoạch Mẫu 2</Link></div>}
    <div className="evaluation-columns"><div className="evaluation-main">
      <section className="evaluation-panel" aria-labelledby="report-heading"><div className="evaluation-panel-title"><FileText size={20} aria-hidden="true"/><h2 id="report-heading">Cuốn báo cáo dùng để nhận xét</h2></div>
        {data.report?<><strong>{data.report.name}</strong><p>Bản v{data.report.version_no} · {labels[data.report.scan_state]}</p><div className="flex gap-2"><button className="btn btn-secondary" disabled={busy||data.report.scan_state!=="CLEAN"} onClick={()=>setPreview({name:data.report!.name,path:`${path}/reports/${data.report!.id}`})}><Eye size={16} aria-hidden="true"/>Đọc báo cáo</button><button className="btn btn-secondary" disabled={busy||data.report.scan_state!=="CLEAN"} onClick={()=>fileAction(data.report!.name,`${path}/reports/${data.report!.id}`)}><Download size={16} aria-hidden="true"/>Tải báo cáo</button></div></>:<div className="evaluation-note"><strong>Chưa có cuốn báo cáo</strong><p>Sinh viên nộp tại Hồ sơ nộp & xét duyệt → Cuốn báo cáo KLTN. Khi có bản đã quét an toàn, GV bắt đầu viết phiếu.</p>{context.base_role==="STUDENT"&&<Link className="btn btn-secondary" to={`/theses/${thesisId}?section=submissions&kind=REPORT`}>Đến nơi nộp báo cáo</Link>}</div>}
      </section>
      <section className="evaluation-panel" aria-labelledby="assignment-heading"><div className="evaluation-panel-title"><Users size={20} aria-hidden="true"/><h2 id="assignment-heading">Phân công phản biện</h2>{can("manage")&&reviewOpen&&<button className="btn btn-primary btn-sm" disabled={busy||active.length>=2} onClick={()=>setOperation({kind:"assign"})}><Plus size={16} aria-hidden="true"/>Phân công GV</button>}</div>
        {!active.length?<p className="text-muted">Bộ môn chưa phân công GV phản biện cho khóa luận này.</p>:active.map(a=><div className="evaluation-assignment" key={a.id}><div><strong><LecturerProfileLink userId={context.user_id} lecturerId={a.lecturer_id} name={a.name}/></strong><p>Hạn phản biện: {when(a.due_at)} (giờ Việt Nam)</p>{a.overdue&&<span className="evaluation-badge is-warning">Quá hạn, vẫn nhận phiếu và ghi thời điểm gửi</span>}<p className="text-caption">{a.source_reference} · {a.reason}</p></div>{can("manage")&&reviewOpen&&<div className="evaluation-assignment-actions"><button className="btn btn-secondary btn-sm" disabled={busy} onClick={()=>setOperation({kind:"extend",id:a.id,name:a.name,due:a.due_at})}>Gia hạn phản biện</button><button className="btn btn-secondary btn-sm" disabled={busy} onClick={()=>setOperation({kind:"revoke",id:a.id,name:a.name})}>Thu hồi phân công</button></div>}</div>)}
        {data.assignments.some(a=>a.state==="REVOKED")&&<details><summary>Lịch sử phân công đã thu hồi</summary>{data.assignments.filter(a=>a.state==="REVOKED").map(a=><p key={a.id}>{a.name} · Đã thu hồi · {a.source_reference}</p>)}</details>}
      </section>
      <section className="evaluation-panel" aria-labelledby="reviews-heading"><div className="evaluation-panel-title"><ClipboardCheck size={20} aria-hidden="true"/><h2 id="reviews-heading">Nhận xét cho từng sinh viên</h2></div>
        <label className="evaluation-field">Sinh viên trong hồ sơ<select aria-label="Sinh viên trong hồ sơ" value={memberId} onChange={e=>setMemberId(e.target.value)}>{data.members.map(m=><option key={m.id} value={m.id}>{m.name} · {m.student_code}</option>)}</select></label>
        {(can("advisor")||can("reviewer"))&&<div className="evaluation-note"><p>Mỗi phiếu gắn đúng sinh viên và phiên bản báo cáo. Nháp chỉ người viết xem; phiếu đã gửi giữ nguyên và có thể lập bản sửa kèm lý do.</p><div className="flex gap-2">{(["ADVISOR","REVIEWER"] as Kind[]).filter(kind=>can(kind==="ADVISOR"?"advisor":"reviewer")).map(kind=><button className="btn btn-primary" key={kind} disabled={busy||blocked||!(kind==="ADVISOR"?open:reviewOpen)||!data.report||data.report.scan_state!=="CLEAN"||currentReviews.some(r=>r.kind===kind&&r.lecturer_id===context.lecturer_id&&r.can_edit)} onClick={()=>setOperation({kind:"create",role:kind})}><Plus size={16} aria-hidden="true"/>Lập phiếu Mẫu {kind==="ADVISOR"?"7":"8"}</button>)}</div></div>}
        {can("advisor")&&(!open||blocked||!data.report||data.report.scan_state!=="CLEAN")&&
          <p className="text-caption">Chưa lập được Mẫu 7. {blocked?"Hoàn tất các mục cập nhật hồ sơ liệt kê ở trên.":!data.report?"SV cần nộp cuốn báo cáo.":data.report.scan_state!=="CLEAN"?"Cần bản báo cáo đã quét an toàn.":data.state==="READY_FOR_DEFENSE"?"TBM cần mở xét lại hồ sơ nếu chưa xếp lịch.":"Hồ sơ đã khóa giai đoạn nhận xét."}</p>}
        {!currentReviews.length?<p className="evaluation-empty-small">Chưa có phiếu nhận xét được phép xem cho sinh viên và bản báo cáo này.</p>:<div className="stack">{currentReviews.map(reviewCard)}</div>}
        {!!oldReviews.length&&<details className="evaluation-old-reviews"><summary>Phiếu theo các bản báo cáo trước ({oldReviews.length})</summary><div className="stack">{oldReviews.map(reviewCard)}</div></details>}
      </section>
    </div><aside className="evaluation-aside">
      <section className="evaluation-panel" aria-labelledby="eligibility-heading"><div className="evaluation-panel-title"><ShieldCheck size={20} aria-hidden="true"/><h2 id="eligibility-heading">Điều kiện dự bảo vệ</h2></div><div className="evaluation-student-identity"><span>Hồ sơ đang xét</span><strong>{member?.name}</strong><b>MSSV: {member?.student_code}</b></div>
        {eligibility?<><span className={`evaluation-badge ${eligibility.state==="ELIGIBLE"?"is-success":"is-warning"}`}>{labels[eligibility.state]}</span><ul className="evaluation-checklist">{eligibility.conditions.map(c=><li key={c.key}>{c.met?<CheckCircle2 aria-label="Đã có căn cứ"/>:<XCircle aria-label="Thiếu hoặc chưa đạt"/>}<span>{c.label}{!c.met&&<small className="text-caption" style={{display:"block"}}>{{
            discipline:"TBM đối chiếu hồ sơ kỷ luật, chọn tình trạng phù hợp và lưu lần xét.",
            completion:"GVHD chọn đúng SV và bản báo cáo đã quét an toàn, đánh dấu hoàn thành rồi gửi Mẫu 7.",
            consent:"GVHD đánh dấu đồng ý bảo vệ, gửi và ký Mẫu 7. TBM hoặc người tiếp nhận đối chiếu mã bản xuất và ghi nhận bản giấy.",
          }[c.key]}</small>}</span></li>)}</ul><p className="text-caption">{eligibility.checked_at?`Xét gần nhất: ${when(eligibility.checked_at)}`:"Bộ môn chưa ghi nhận kết quả xét."}</p>{eligibility.source_reference&&<p className="evaluation-reference">Căn cứ: {eligibility.source_reference}</p>}{eligibility.reason&&<p>{eligibility.reason}</p>}
          {can("eligibility")&&reviewOpen&&<button className="btn btn-primary" disabled={busy} onClick={()=>setOperation({kind:"check"})}>Xét và lưu điều kiện</button>}
        </>:<p>Chỉ sinh viên liên quan, GVHD và người xét có quyền xem căn cứ điều kiện cá nhân.</p>}
        <div className="evaluation-policy"><strong>Điều kiện cấp Trường</strong><p>Ba căn cứ theo quy định hiện hành của dự án. Nhận xét phản biện và kết quả tương đồng không tự tạo điều kiện chặn bổ sung.</p><p>Báo cáo hoặc Mẫu 7 thay đổi thì kết quả cũ cần được xét lại.</p></div>
        {can("eligibility")&&data.state==="READY_FOR_DEFENSE"&&<button className="btn btn-secondary" disabled={busy} onClick={()=>setOperation({kind:"reopen"})}>Mở xét lại hồ sơ</button>}
      </section>
      {!!data.eligibility_history.filter(h=>h.thesis_member_id===memberId).length&&<section className="evaluation-panel"><h2>Lịch sử xét điều kiện</h2><ol className="evaluation-history">{data.eligibility_history.filter(h=>h.thesis_member_id===memberId).map(h=><li key={h.id}><strong>Lần {h.version_no} · {labels[h.state]}</strong><small>{when(h.checked_at)} · {h.checked_by}</small><p>{h.source_reference}</p><p>{h.reason}</p></li>)}</ol></section>}
    </aside></div>
    {operation&&<OperationDialog key={`${operation.kind}:${memberId}`} operation={operation} data={data} memberId={memberId} context={context} onClose={()=>setOperation(null)} onSaved={async result=>{await load();setMessage("Đã lưu thay đổi và thông báo đến tài khoản liên quan.");setOperation(null);if(result)setEditor(result);}}/>}
    {paperReview&&<PaperReceiptDialog review={paperReview} userId={context.user_id} thesisId={thesisId} onClose={()=>setPaperReview(null)} onDone={async()=>{setPaperReview(null);await load();setMessage("Đã ghi nhận bản giấy. TBM xét lại điều kiện để cập nhật kết quả.");}}/>}
    {editor&&<ThesisReviewEditor key={editor.id} initial={editor} data={data} context={context} onClose={()=>setEditor(null)} onUpdated={load}/>}
    {preview&&<Dialog open size="lg" title="Xem tài liệu" onClose={()=>setPreview(null)}><Suspense fallback={<p role="status">Đang mở tài liệu…</p>}><Preview name={preview.name} endpoint={preview.path} label="Tài liệu phản biện" backLabel="Đóng xem trước" caption="Đúng phiên bản đã lưu trong hồ sơ." onBack={()=>setPreview(null)}/></Suspense></Dialog>}
  </div>;
}

function OperationDialog({operation:op,data,memberId,context,onClose,onSaved}:{operation:Operation;data:Evaluation;memberId:string;context:Context;onClose:()=>void;onSaved:(review?:Review)=>Promise<void>}) {
  const member=data.members.find(m=>m.id===memberId);
  const [reason,setReason]=useState(op.kind==="create"&&!data.reviews.some(r=>r.thesis_member_id===memberId&&r.kind===op.role)?"Nhận xét lần đầu cho bản báo cáo hiện hành":"");
  const [reference,setReference]=useState(""),[lecturer,setLecturer]=useState("");
  const [discipline,setDiscipline]=useState(member?.eligibility?.discipline_status||"UNKNOWN");
  const [due,setDue]=useState(()=>new Date((op.kind==="extend"&&op.due?Math.max(Date.now(),new Date(op.due).getTime()):Date.now())+7*86400000+7*3600000).toISOString().slice(0,16));
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  const path=`/theses/${data.thesis_id}/evaluation`;
  const titles={assign:"Phân công GV phản biện",extend:"Gia hạn gửi nhận xét phản biện",revoke:"Thu hồi phân công phản biện",check:"Xét điều kiện dự bảo vệ",reopen:"Mở xét lại hồ sơ",create:"Lập phiếu nhận xét"};
  async function submit(e:React.FormEvent){
    e.preventDefault();if(busy)return;setBusy(true);setError("");
    try{
      let result:Review|undefined;
      if(op.kind==="assign")await mutate(path+"/reviewers",context.user_id,{lecturer_id:lecturer,due_at:new Date(due+":00+07:00").toISOString(),reason,source_reference:reference},data.row_version);
      else if(op.kind==="extend")await mutate(path+`/reviewers/${op.id}/deadline`,context.user_id,{due_at:new Date(due+":00+07:00").toISOString(),reason,source_reference:reference},data.row_version);
      else if(op.kind==="revoke")await mutate(path+`/reviewers/${op.id}/revoke`,context.user_id,{reason},data.row_version);
      else if(op.kind==="reopen")await mutate(path+"/reopen",context.user_id,{reason},data.row_version);
      else if(op.kind==="create")result=await mutate<Review>(path+"/reviews",context.user_id,{thesis_member_id:memberId,kind:op.role,report_version_id:data.report?.id,reason},data.row_version);
      else await mutate(path+"/eligibility",context.user_id,{thesis_member_id:memberId,report_version_id:data.report?.id||null,advisor_review_id:member?.eligibility?.advisor_review_id||null,discipline_status:discipline,source_reference:reference,reason},data.row_version);
      await onSaved(result);
    }catch(e){setError(errorMessage(e));}finally{setBusy(false);}
  }
  return <Dialog open title={titles[op.kind]} busy={busy} onClose={onClose} footer={<><button className="btn btn-secondary" disabled={busy} onClick={onClose}>Hủy</button><button className="btn btn-primary" type="submit" form="evaluation-operation" disabled={busy}>{busy?"Đang lưu…":op.kind==="create"?"Tạo phiếu nháp":"Xác nhận và lưu"}</button></>}>
    <form id="evaluation-operation" className="evaluation-form" onSubmit={e=>void submit(e)}>
      {error&&<p className="alert alert-danger" role="alert">{error}</p>}
      {op.kind==="assign"&&<><label className="evaluation-field">Giảng viên phản biện<select aria-label="Giảng viên phản biện" required value={lecturer} onChange={e=>setLecturer(e.target.value)}><option value="">Chọn GV đang hoạt động phù hợp</option>{data.candidates.filter(c=>!data.assignments.some(a=>a.lecturer_id===c.id&&a.state==="ACTIVE")).map(c=><option value={c.id} key={c.id}>{c.recommended?"★ Phù hợp theo hồ sơ · ":""}{c.name} · {c.code} · {c.department} · {c.active_load} phân công đang mở</option>)}</select></label>{data.candidates.find(c=>c.id===lecturer)?.recommendation_reasons?.length? <p className="alert alert-info">Chuyên môn đối chiếu: {data.candidates.find(c=>c.id===lecturer)?.recommendation_reasons?.join("; ")}</p>:null}<label className="evaluation-field">Hạn gửi nhận xét (giờ Việt Nam)<input type="datetime-local" required value={due} onChange={e=>setDue(e.target.value)}/></label><p className="text-caption">Bộ môn của hồ sơ: <strong>{data.reviewer_department}</strong>. Có thể chọn GV trong Khoa. Gợi ý ưu tiên dựa trên chuyên môn đã xác nhận; người phân công đối chiếu sự phù hợp trước khi quyết định. GVHD không được phản biện cùng đề tài. Tối đa hai GV phản biện đang được phân công.</p></>}
      {op.kind==="revoke"&&<p>Thu hồi phân công của <strong>{op.name}</strong>. GV này sẽ mất quyền xem hồ sơ phản biện; các phiếu đã gửi vẫn được giữ trong lịch sử.</p>}
      {op.kind==="extend"&&<><p>Gia hạn cho <strong>{op.name}</strong>. Hạn hiện tại: {when(op.due)}.</p><label className="evaluation-field">Hạn mới (giờ Việt Nam)<input type="datetime-local" required value={due} onChange={e=>setDue(e.target.value)}/></label></>}
      {op.kind==="reopen"&&<p>Hồ sơ trở lại “Đang thực hiện”. Kết quả cũ vẫn được giữ, mọi thành viên cần được xét lại trước khi chốt đủ điều kiện bảo vệ.</p>}
      {op.kind==="create"&&<p><strong>{member?.name} · {member?.student_code}</strong><br/>Mẫu {op.role==="ADVISOR"?"7 (GVHD)":"8 (GV phản biện)"} · Bản báo cáo v{data.report?.version_no}. Bản nháp chỉ bạn được xem.</p>}
      {op.kind==="check"&&<><p><strong>{member?.name} · {member?.student_code}</strong></p><label className="evaluation-field">Tình trạng kỷ luật theo nguồn đã đối chiếu<select aria-label="Tình trạng kỷ luật theo nguồn đã đối chiếu" value={discipline} onChange={e=>setDiscipline(e.target.value)}><option value="UNKNOWN">Chưa đủ căn cứ xác nhận</option><option value="CLEAR">Không bị kỷ luật từ cảnh cáo toàn Trường</option><option value="WARNING_OR_HIGHER">Đang bị kỷ luật từ cảnh cáo toàn Trường trở lên</option></select></label><div className="evaluation-note">{member?.eligibility?.conditions.filter(c=>c.key!=="discipline").map(c=><p key={c.key}>{c.met?"✓":"○"} {c.label}</p>)}<strong>{discipline==="CLEAR"&&member?.eligibility?.conditions.filter(c=>c.key!=="discipline").every(c=>c.met)?"Dự kiến: đủ điều kiện dự bảo vệ":"Dự kiến: chưa đủ điều kiện dự bảo vệ"}</strong><p>Hệ thống tính kết quả từ ba căn cứ. Lưu “chưa đủ” để người liên quan biết phần cần bổ sung.</p></div></>}
      {(op.kind==="assign"||op.kind==="extend"||op.kind==="check")&&<label className="evaluation-field">Căn cứ / số văn bản đối chiếu<input required minLength={3} maxLength={500} value={reference} onChange={e=>setReference(e.target.value)}/></label>}
      <label className="evaluation-field">{op.kind==="create"?"Lý do lập phiếu / phiên bản sửa":"Lý do / ghi chú nghiệp vụ"}<textarea required minLength={5} maxLength={2000} rows={3} value={reason} onChange={e=>setReason(e.target.value)}/></label>
    </form>
  </Dialog>;
}

function PaperReceiptDialog({review,userId,thesisId,onClose,onDone}:{review:Review;userId:string;thesisId:string;onClose:()=>void;onDone:()=>Promise<void>}) {
 const [code,setCode]=useState(review.export_history[0]?.code||""),[reference,setReference]=useState(""),[confirmed,setConfirmed]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState("");
 return <Dialog open title="Ghi nhận bản giấy đã ký" onClose={onClose} busy={busy}>
 <form className="evaluation-form" onSubmit={async e=>{e.preventDefault();if(busy)return;setBusy(true);setError("");try{await mutate("/theses/"+thesisId+"/evaluation/reviews/"+review.id+"/paper-receipt",userId,{reference,export_code:code,confirm_paper:confirmed},review.row_version);await onDone();}catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}}}>
 <p>Đối chiếu chữ ký của đúng GV viết phiếu, nội dung và mã in trên bản giấy. Thao tác này ghi nhận hồ sơ đã nhận; không tạo chữ ký số.</p>
 {error&&<p className="alert alert-danger" role="alert">{error}</p>}
 <label className="evaluation-field">Mã bản xuất trên giấy<select required value={code} onChange={e=>setCode(e.target.value)}>{review.export_history.map(x=><option key={x.code} value={x.code}>{x.code} · {when(x.at)}</option>)}</select></label>
 <label className="evaluation-field">Số / căn cứ tiếp nhận bản giấy<input required minLength={5} maxLength={500} value={reference} onChange={e=>setReference(e.target.value)}/></label>
 <label className="evaluation-check"><input type="checkbox" required checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Tôi đã đối chiếu bản giấy có chữ ký đúng người, đúng nội dung và mã bản xuất.</label>
 <button className="btn btn-primary" disabled={busy||!confirmed||reference.trim().length<5}>Xác nhận đã nhận bản giấy</button>
 </form></Dialog>;
}
