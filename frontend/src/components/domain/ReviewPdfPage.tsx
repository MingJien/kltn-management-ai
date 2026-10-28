import { useEffect, useRef, useState, type CSSProperties } from "react";
import { getDocument, GlobalWorkerOptions, TextLayer, type PDFDocumentProxy } from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import type { ProgressAnnotation } from "../../api";
import ReviewCommentText from "./ReviewCommentText";

GlobalWorkerOptions.workerSrc = pdfWorker;

export default function ReviewPdfPage({data, pageNumber, zoom, notes, selectedId, pinMode, canAnnotate, showEmbeddedReviews=false, onSelect, onPin, onPages, onRendered}: {
  data: ArrayBuffer; pageNumber: number; zoom: number; notes: ProgressAnnotation[]; selectedId: string;
  pinMode: boolean; canAnnotate: boolean; showEmbeddedReviews?:boolean; onSelect: (id: string) => void;
  onPin: (page: number, x: number, y: number, quote: string) => void;
  onPages: (count: number) => void; onRendered: () => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const text = useRef<HTMLDivElement>(null);
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null);
  const [width, setWidth] = useState(680);
  const [size, setSize] = useState({width: 680, height: 920, scale: 1});
  const [error, setError] = useState("");
  const [rendering, setRendering] = useState(true);
  const [embedded,setEmbedded] = useState<{author:string; text:string}[]>([]);
  const onPagesRef = useRef(onPages); onPagesRef.current = onPages;
  const renderedRef = useRef(onRendered); renderedRef.current = onRendered;
  useEffect(() => {
    const task = getDocument({data: new Uint8Array(data.slice(0)), enableXfa: false, useSystemFonts: true});
    let disposed = false;
    task.promise.then(document => {if (!disposed) {setPdf(document); onPagesRef.current(document.numPages);}})
      .catch(() => {if (!disposed) {setError("Không đọc được PDF. Tệp có thể bị hỏng hoặc được bảo vệ bằng mật khẩu; bạn vẫn có thể tải bản gốc và nhận xét theo mục."); setRendering(false);}});
    return () => {disposed = true; void task.destroy();};
  }, [data]);
  useEffect(() => {
    if (!host.current) return;
    const observer = new ResizeObserver(entries => setWidth(Math.max(220, entries[0].contentRect.width - 32)));
    observer.observe(host.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!pdf || !canvas.current || !text.current) return;
    let disposed = false;
    let renderTask: ReturnType<Awaited<ReturnType<PDFDocumentProxy["getPage"]>>["render"]> | undefined;
    let textLayer: TextLayer | undefined;
    setRendering(true); setError(""); setEmbedded([]);
    void (async () => {
      const page = await pdf.getPage(Math.min(Math.max(1, pageNumber), pdf.numPages));
      if(showEmbeddedReviews) {
        const comments=await page.getAnnotations({intent:"display"});
        if(!disposed) setEmbedded(comments.filter(item=>typeof item.contentsObj?.str === "string" && item.contentsObj.str.trim()).slice(0,100)
          .map(item=>({author:String(item.titleObj?.str || "Nhận xét trong PDF"),text:item.contentsObj.str.slice(0,5000)})));
      }
      if (disposed || !canvas.current || !text.current) return;
      const original = page.getViewport({scale: 1});
      const viewport = page.getViewport({scale: width / original.width * zoom});
      const outputScale = Math.min(window.devicePixelRatio || 1, 2);
      canvas.current.width = Math.floor(viewport.width * outputScale);
      canvas.current.height = Math.floor(viewport.height * outputScale);
      setSize({width: viewport.width, height: viewport.height, scale: viewport.scale});
      renderTask = page.render({canvas: canvas.current, viewport, transform: [outputScale, 0, 0, outputScale, 0, 0]});
      await renderTask.promise;
      if (disposed || !text.current) return;
      text.current.replaceChildren();
      textLayer = new TextLayer({textContentSource: await page.getTextContent(), container: text.current, viewport});
      await textLayer.render();
      if (!disposed) {setRendering(false); renderedRef.current();}
    })().catch(error => {if (!disposed && error?.name !== "RenderingCancelledException") {setError("Chưa hiển thị được trang PDF. Hãy thử đổi trang hoặc tải bản gốc."); setRendering(false);}});
    return () => {disposed = true; renderTask?.cancel(); textLayer?.cancel();};
  }, [pdf, pageNumber, width, zoom, showEmbeddedReviews]);
  return <div ref={host} className="review-pdf-host">
    {embedded.length > 0 && <details open className="review-native-comments"><summary>Nhận xét có trong PDF · trang {pageNumber} ({embedded.length})</summary>
      {embedded.map((item,index)=><article key={index}><strong>{item.author}</strong><p><ReviewCommentText text={item.text}/></p></article>)}
    </details>}
    {error && <p className="alert alert-danger" role="alert">{error}</p>}
    {rendering && !error && <p className="review-pdf-loading" role="status">Đang hiển thị trang…</p>}
    <div className={`review-pdf-sheet${pinMode ? " review-pdf-sheet--pinning" : ""}`} style={{width: size.width, height: size.height, "--total-scale-factor": size.scale} as CSSProperties}
      onPointerUp={event => {
        if (!canAnnotate || rendering || (event.target as HTMLElement).closest("button")) return;
        const rect = event.currentTarget.getBoundingClientRect();
        const selection = window.getSelection();
        const quote = selection?.anchorNode && event.currentTarget.contains(selection.anchorNode) && event.currentTarget.contains(selection.focusNode) ? selection.toString().trim().slice(0, 1000) : "";
        if (!pinMode && !quote) return;
        onPin(pageNumber, Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)), Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)), quote);
        selection?.removeAllRanges();
      }}>
      <canvas ref={canvas} style={{width: size.width, height: size.height}} aria-label={`Nội dung PDF trang ${pageNumber}`} />
      <div ref={text} className="textLayer" />
      {!rendering && notes.map((note, index) => note.page_number === pageNumber && note.x !== null && note.y !== null &&
        <button key={note.id} type="button" className={`review-pin${selectedId === note.id ? " review-pin--selected" : ""}${note.state === "DRAFT" ? " review-pin--draft" : ""}`}
          style={{left: `${note.x * 100}%`, top: `${note.y * 100}%`}} title={note.comment || "Ghim chưa ghi nội dung"}
          data-note-id={note.id} aria-label={`Mở nhận xét ${index + 1} tại trang ${pageNumber}`} onClick={() => onSelect(note.id)}>{index + 1}</button>)}
    </div>
  </div>;
}
