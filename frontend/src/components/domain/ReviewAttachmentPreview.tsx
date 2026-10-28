import {useEffect, useRef, useState} from "react";
import {ArrowLeft, ChevronLeft, ChevronRight} from "lucide-react";
import {fetchReviewFile, type ProgressAnnotation} from "../../api";
import ReviewPdfPage from "./ReviewPdfPage";
import ReviewTextDocument from "./ReviewTextDocument";

export default function ReviewAttachmentPreview({note,endpoint,sourceVersion,onBack}: {
  note:ProgressAnnotation; endpoint:string; sourceVersion:number; onBack:()=>void;
}) {
  return <ReadOnlyFilePreview name={note.attachment?.file_name || ""} endpoint={endpoint} onBack={onBack}
    label="Bản GV đã nhận xét" backLabel="Về bản SV" caption={`Bản ${note.reviewer_name} phản hồi cho bản SV v${sourceVersion} · ${note.state === "DRAFT" ? "nháp riêng, SV chưa thấy" : "đã gửi"}.`} />;
}

export function ReadOnlyFilePreview({name,endpoint,onBack,label,backLabel,caption}: {
  name:string;endpoint:string;onBack:()=>void;label:string;backLabel:string;caption:string;
}) {
  const [data,setData]=useState<ArrayBuffer|null>(null);
  const [error,setError]=useState("");
  const [page,setPage]=useState(1),[pages,setPages]=useState(1);
  const pane=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    const controller=new AbortController();setData(null);setError("");
    void fetchReviewFile(endpoint,controller.signal).then(setData).catch(cause=>{if(!controller.signal.aborted)setError(String(cause));});
    return()=>controller.abort();
  },[endpoint]);
  return <section className="review-document" aria-label={label}>
    <div className="review-toolbar"><button type="button" className="btn btn-secondary btn-sm" onClick={onBack}><ArrowLeft size={15}/>{backLabel}</button>
      {/\.pdf$/i.test(name) && <div className="review-page-controls">
        <button type="button" className="review-icon" aria-label="Trang phản hồi trước" disabled={page<=1} onClick={()=>setPage(value=>value-1)}><ChevronLeft size={17}/></button>
        <span>Trang {page} / {pages}</span>
        <button type="button" className="review-icon" aria-label="Trang phản hồi sau" disabled={page>=pages} onClick={()=>setPage(value=>value+1)}><ChevronRight size={17}/></button></div>}
    </div>
    <div className="review-pin-hint"><span><strong>{name}</strong><br/>{caption}</span></div>
    <div className="review-document-scroll" ref={pane}>
      {error ? <p role="alert" className="review-error">{error}</p> : !data ? <p className="review-empty">Đang mở tệp phản hồi đã quét…</p>
        : /\.pdf$/i.test(name) ? <ReviewPdfPage data={data} pageNumber={page} zoom={1} notes={[]} selectedId="" pinMode={false} canAnnotate={false} showEmbeddedReviews
          onSelect={()=>{}} onPin={()=>{}} onPages={setPages} onRendered={()=>{}} />
        : <ReviewTextDocument data={data} fileName={name} notes={[]} selectedId="" pinMode={false} canAnnotate={false} showEmbeddedReviews
          onSelect={()=>{}} onPin={()=>{}} onRendered={()=>{}} />}
    </div>
  </section>;
}
