import {useEffect,useState} from "react";
import {Check,Download,Save,Send} from "lucide-react";
import {downloadOfficialTemplate,exportThesisReview,request,type Context} from "../../api";
import {errorMessage} from "../../errors";
import {labels,mutate,type Evaluation,type Review} from "../../evaluation";
import Dialog from "../ui/Dialog";

export default function ThesisReviewEditor({initial,data,context,onClose,onUpdated}:{initial:Review;data:Evaluation;context:Context;onClose:()=>void;onUpdated:()=>Promise<void>}) {
  const [review,setReview]=useState(initial),[sections,setSections]=useState(initial.sections);
  const [completed,setCompleted]=useState(initial.thesis_completed===null?"":String(initial.thesis_completed));
  const [allow,setAllow]=useState(initial.allow_defense===null?"":String(initial.allow_defense));
  const [reference,setReference]=useState(initial.source_reference||"");
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("");
  const [confirm,setConfirm]=useState(false),[discard,setDiscard]=useState(false),[attested,setAttested]=useState(false);
  const path=`/theses/${data.thesis_id}/evaluation/reviews/${review.id}`;
  const value={sections,thesis_completed:completed===""?null:completed==="true",allow_defense:allow===""?null:allow==="true",source_reference:reference||null};
  const dirty=JSON.stringify(value)!==JSON.stringify({sections:review.sections,thesis_completed:review.thesis_completed,allow_defense:review.allow_defense,source_reference:review.source_reference});
  useEffect(()=>{
    if(!dirty)return;
    const stop=(e:BeforeUnloadEvent)=>{e.preventDefault();e.returnValue="";};
    window.addEventListener("beforeunload",stop);return()=>window.removeEventListener("beforeunload",stop);
  },[dirty]);
  async function run(action:()=>Promise<Review>,message:string) {
    if(busy)return;setBusy(true);setError("");setNotice("");
    try{const updated=await action();setReview(updated);setSections(updated.sections);setReference(updated.source_reference||"");setCompleted(updated.thesis_completed===null?"":String(updated.thesis_completed));setAllow(updated.allow_defense===null?"":String(updated.allow_defense));await onUpdated();setNotice(message);return updated;}
    catch(e){setError(errorMessage(e));}finally{setBusy(false);}
  }
  const allFields=data.form_fields[review.kind].every(field=>sections[field.key]?.trim());
  const student=data.members.find(member=>member.id===review.thesis_member_id);
  return <Dialog open title={`Mẫu ${review.kind==="ADVISOR"?"7 · Nhận xét GVHD":"8 · Nhận xét phản biện"}`} size="lg" busy={busy}
    onClose={()=>dirty?setDiscard(true):onClose()} footer={<>
      <span className="evaluation-save-state" role="status">{busy?"Đang lưu…":dirty?"Có thay đổi chưa lưu":"Đã lưu nháp trên hệ thống"}</span>
      <button className="btn btn-secondary" disabled={busy} onClick={()=>dirty?setDiscard(true):onClose()}>Đóng</button>
      <button className="btn btn-primary" disabled={busy||!dirty} onClick={()=>void run(()=>mutate<Review>(path,context.user_id,value,review.row_version,"PUT"),"Đã lưu nháp riêng. Nếu thay đổi nội dung, cần đính kèm lại bản ký tương ứng.")}><Save size={16} aria-hidden="true"/>Lưu nháp</button>
    </>}>
    <div className="evaluation-editor">
      <div className="evaluation-note"><strong>{student?.name} · {student?.student_code}</strong><p>Phiếu v{review.version_no} · Bản báo cáo v{data.report?.version_no}. Nháp riêng, sinh viên chưa thấy.</p></div>
      {error&&<p className="alert alert-danger" role="alert">{error}</p>}{notice&&<p className="alert alert-success" role="status">{notice}</p>}
      {discard&&<div className="alert alert-warning" role="alert"><p>Nội dung đang viết chưa được lưu.</p><button className="btn btn-secondary" onClick={()=>setDiscard(false)}>Tiếp tục viết</button><button className="btn btn-danger" onClick={onClose}>Bỏ thay đổi và đóng</button></div>}
      <fieldset disabled={busy||confirm} className="evaluation-fieldset"><legend>1. Nội dung nhận xét theo biểu mẫu</legend>
        {data.form_fields[review.kind].map(field=><label className="evaluation-field" key={field.key}>{field.label}<textarea aria-label={field.label} rows={4} maxLength={6000} value={sections[field.key]||""} onChange={e=>setSections(old=>({...old,[field.key]:e.target.value}))}/><small>{(sections[field.key]||"").length}/6.000 ký tự</small></label>)}
        {review.kind==="ADVISOR"&&<div className="evaluation-two-fields">
          <label className="evaluation-field">Xác nhận hoàn thành khóa luận<select aria-label="Xác nhận hoàn thành khóa luận" value={completed} onChange={e=>setCompleted(e.target.value)}><option value="">Chọn kết quả</option><option value="true">Đã hoàn thành</option><option value="false">Chưa hoàn thành</option></select></label>
          <label className="evaluation-field">Đề nghị của GVHD<select aria-label="Đề nghị của GVHD" value={allow} onChange={e=>setAllow(e.target.value)}><option value="">Chọn đề nghị</option><option value="true">Đồng ý cho bảo vệ</option><option value="false">Không đồng ý cho bảo vệ</option></select></label>
        </div>}
        <label className="evaluation-field">Số hoặc căn cứ phiếu (nếu có)<input maxLength={500} value={reference} onChange={e=>setReference(e.target.value)}/></label>
      </fieldset>
      <fieldset className="evaluation-fieldset" disabled={busy||confirm}><legend>2. Xuất phiếu và bản ký (bổ sung sau)</legend>
        <p>Xuất phiếu đã điền từ mẫu chính thức của Khoa, kiểm tra rồi ký theo quy trình. Bạn có thể gửi nhận xét ngay trên hệ thống. Bản giấy được cán bộ phụ trách hoặc TBM ghi nhận sau; đính kèm bản quét là tùy chọn.</p>
        <button className="btn btn-primary" disabled={busy||dirty||!allFields||(review.kind==="ADVISOR"&&(!completed||!allow))} onClick={()=>{
          setBusy(true);setError("");void exportThesisReview(data.thesis_id,review.id,review.row_version)
            .then(()=>setNotice("Đã xuất phiếu đã điền để ký. Kiểm tra bản in trước khi ký và đính kèm lại."))
            .catch(e=>setError(errorMessage(e))).finally(()=>setBusy(false));
        }}><Download size={16} aria-hidden="true"/>Xuất phiếu đã điền để ký</button>{" "}
        <button className="btn btn-secondary" onClick={()=>void downloadOfficialTemplate(review.kind==="ADVISOR"?"mau-07":"mau-08",`mau-${review.kind==="ADVISOR"?"7":"8"}.docx`,data.round_id).catch(e=>setError(errorMessage(e)))}><Download size={16} aria-hidden="true"/>Tải Mẫu {review.kind==="ADVISOR"?"7":"8"} chính thức</button>
        <label className="evaluation-field">Đính kèm bản đã ký (PDF/DOCX, tối đa 10 MB)<input type="file" accept=".pdf,.docx" disabled={busy||dirty} onChange={e=>{
          const file=e.target.files?.[0];e.target.value="";if(!file)return;
          if(file.size>10*1024*1024||!file.size){setError("Chọn tệp có nội dung, tối đa 10 MB.");return;}
          void run(()=>request<Review>(path+"/signed-copy",context.user_id,{method:"POST",body:file,headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(file.name),"If-Match":String(review.row_version)}}),"Đã lưu bản ký; kiểm tra trạng thái quét trước khi gửi.");
        }}/>{dirty&&<small>Lưu nội dung nháp để bật đính kèm.</small>}</label>
        {review.signed_file&&<div className="evaluation-note"><strong>{review.signed_file.name}</strong><p>{labels[review.signed_file.scan_state]}</p>{review.signed_file.scan_state!=="CLEAN"&&<button className="btn btn-secondary" onClick={()=>void run(()=>mutate<Review>(path+"/scan",context.user_id,{},review.row_version),"Đã kiểm tra lại trạng thái quét.")}>Quét lại bản ký</button>}</div>}
      </fieldset>
      <fieldset className="evaluation-fieldset" disabled={busy}><legend>3. Gửi nhận xét</legend><p>Sau khi gửi, nội dung và bản ký được giữ nguyên. Bản sửa cần một phiên bản phiếu mới kèm lý do.</p>
        {!confirm?<button className="btn btn-primary" disabled={dirty||!allFields||(!!review.signed_file&&review.signed_file.scan_state!=="CLEAN")||(review.kind==="ADVISOR"&&(!completed||!allow))} onClick={()=>setConfirm(true)}><Send size={16} aria-hidden="true"/>Kiểm tra và gửi nhận xét</button>:<div className="evaluation-confirm">
          <label className="evaluation-check"><input type="checkbox" checked={attested} onChange={e=>setAttested(e.target.checked)}/>Tôi xác nhận nội dung nhận xét này là của tôi và đã kiểm tra đúng sinh viên, phiên bản báo cáo.</label>
          <div className="flex gap-2"><button className="btn btn-secondary" onClick={()=>{setConfirm(false);setAttested(false);}}>Quay lại kiểm tra</button><button className="btn btn-primary" disabled={!attested} onClick={()=>void run(()=>mutate<Review>(path+"/submit",context.user_id,{confirm_content:true},review.row_version),"Đã gửi nhận xét.").then(updated=>{if(updated)onClose();})}><Check size={16} aria-hidden="true"/>Xác nhận gửi nhận xét</button></div>
        </div>}
      </fieldset>
    </div>
  </Dialog>;
}
