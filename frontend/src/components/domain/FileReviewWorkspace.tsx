import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowLeft, Check, ChevronLeft, ChevronRight, Download, MapPin, MessageSquare, Plus, Save, Send, Trash2, Paperclip, ZoomIn, ZoomOut } from "lucide-react";
import type { ProgressAnnotation, ProgressAnnotationData, ProgressAnnotations, Review } from "../../api";
import { downloadFile, fetchReviewFile, request } from "../../api";
import { formatDate, Reviews } from "./CoreForms";
import type { CoreRun } from "./ThesisDocuments";
import ReviewPdfPage from "./ReviewPdfPage";
import ReviewTextDocument from "./ReviewTextDocument";
import ReviewCommentText from "./ReviewCommentText";
import ReviewAttachmentPreview from "./ReviewAttachmentPreview";
import "../../styles/review-workspace.css";

type Note = ProgressAnnotation & {dirty?: boolean; conflict?: boolean};
type Cache = {notes?: Note[]; page?: number; zoom?: number; scroll?: number; selectedId?: string; comment?: string; decision?: string};
const fields = (note: ProgressAnnotationData): ProgressAnnotationData => ({annotation_kind: note.annotation_kind || "PIN", page_number: note.page_number, x: note.x, y: note.y, location_label: note.location_label, quoted_text: note.quoted_text, comment: note.comment});

export type FileReviewTarget = {
  versionId: string; fileName: string; versionNo: number; submittedBy: string;
  rowVersion: number; annotationsPath: string; downloadPath: string; reviewPath: string;
  label: string; choices: {value: string; label: string}[]; reviews: Review[]; legacyCacheKey?: string;
};

export default function FileReviewWorkspace({target, userId, run, onClose}: {
  target: FileReviewTarget; userId: string; run: CoreRun; onClose: () => void;
}) {
  const key = `kltn-file-review:${userId}:${target.versionId}:${target.annotationsPath}`;
  const [cached] = useState<Cache>(() => {try {return JSON.parse(localStorage.getItem(key) || (target.legacyCacheKey && localStorage.getItem(target.legacyCacheKey)) || "{}");} catch {return {};}});
  const [notes, setNotes] = useState<Note[]>([]);
  const notesRef = useRef<Note[]>(cached.notes || []);
  const [loaded, setLoaded] = useState(false);
  const [canEdit, setCanEdit] = useState(false);
  const [readOnlyReason, setReadOnlyReason] = useState("");
  const [data, setData] = useState<ArrayBuffer | null>(null);
  const [page, setPage] = useState(Math.max(1, Math.min(10000, cached.page || 1)));
  const [pages, setPages] = useState(1);
  const [zoom, setZoom] = useState(Math.max(.75, Math.min(2, cached.zoom || 1)));
  const [selectedId, setSelectedId] = useState(cached.selectedId || "");
  const [pinMode, setPinMode] = useState(false);
  const [comment, setComment] = useState(cached.comment || "");
  const [decision, setDecision] = useState(cached.decision || "");
  const [status, setStatus] = useState("Đang mở hồ sơ nhận xét…");
  const [error, setError] = useState("");
  const [storageError, setStorageError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<ProgressAnnotation | null>(null);
  const [closing, setClosing] = useState(false);
  const dialog = useRef<HTMLDivElement>(null);
  const pane = useRef<HTMLDivElement>(null);
  const scroll = useRef(cached.scroll || 0);
  const restoreScroll = useRef(true);
  const jumpTo = useRef<string | null>(null);
  const focusNewNote = useRef<string | null>(null);
  const saveInFlight = useRef<Promise<boolean> | null>(null);
  const isPdf = /\.pdf$/i.test(target.fileName);
  const currentCache = useRef<Cache>({});
  currentCache.current = {notes, page, zoom, scroll: scroll.current, selectedId, comment, decision};
  const persist = useCallback(() => {
    try {localStorage.setItem(key, JSON.stringify({...currentCache.current, notes: notesRef.current.filter(note => note.state === "DRAFT"), scroll: scroll.current}));}
    catch {setStorageError(true);}
  }, [key]);
  const changeNotes = useCallback((update: (current: Note[]) => Note[]) => {
    const next = update(notesRef.current);
    notesRef.current = next; setNotes(next);
    currentCache.current.notes = next;
    persist();
  }, [persist]);
  useEffect(() => {if (loaded) persist();}, [page, zoom, selectedId, comment, decision, loaded, persist]);
  useEffect(() => {
    const controller = new AbortController();
    const path = target.annotationsPath;
    void request<ProgressAnnotations>(path, userId, {signal: controller.signal}).then(result => {
      if (controller.signal.aborted) return;
      const localDrafts = (cached.notes || []).filter(note => note.state === "DRAFT" && note.dirty);
      const merged: Note[] = result.annotations.map(remote => {
        const local = localDrafts.find(note => note.id === remote.id);
        if (!local || remote.state !== "DRAFT") return remote;
        const same = JSON.stringify(fields(local)) === JSON.stringify(fields(remote));
        return {...local, row_version: remote.row_version, dirty: !same,
          conflict: !same && local.row_version > 0 && local.row_version !== remote.row_version};
      });
      if (result.can_edit) for (const local of localDrafts) if (!merged.some(note => note.id === local.id)) merged.push(local);
      let summary = merged.find(note => note.annotation_kind === "SUMMARY" && note.state === "DRAFT");
      if (!summary && result.can_edit && cached.comment?.trim()) {
        summary = {...newDraft("SUMMARY"), comment:cached.comment, dirty:true}; merged.push(summary);
      }
      if (summary) setComment(summary.comment);
      notesRef.current = merged; setNotes(merged);
      setCanEdit(result.can_edit);
      setReadOnlyReason(result.read_only_reason || "Chỉ giảng viên được phân công mới nhận xét bản hiện hành còn chờ phản hồi.");
      setLoaded(true);
      setStatus(result.can_edit ? "Nháp riêng · tự lưu khi nhập nhận xét" : "Chế độ chỉ xem · không sửa phản hồi đã gửi");
    }).catch(cause => {if (!controller.signal.aborted) {setError(String(cause)); setStatus("Chưa tải được nhận xét");}});
    void fetchReviewFile(target.downloadPath, controller.signal).then(buffer => {if (!controller.signal.aborted) setData(buffer);})
      .catch(cause => {if (!controller.signal.aborted) setError(String(cause));});
    return () => {controller.abort();};
  }, [target.annotationsPath, target.downloadPath, userId, cached]);

  const flush = useCallback((): Promise<boolean> => {
    if (saveInFlight.current) return saveInFlight.current;
    const task = async () => {
      setSaving(true);
      try {
        while (true) {
          const note = notesRef.current.find(item => item.state === "DRAFT" && item.dirty);
          if (!note) break;
          if (note.conflict) throw new Error("Ghim đã được sửa ở phiên làm việc khác. Chọn ‘Giữ thành ghim riêng’ để lưu nội dung đang viết.");
          const payload = fields(note), signature = JSON.stringify(payload);
          setStatus("Đang tự lưu bản nháp…");
          const saved = await request<ProgressAnnotation>(`${target.annotationsPath}/${note.id}`, userId,
            {method: "PUT", headers: {"If-Match": String(note.row_version)}, body: JSON.stringify(payload)});
          changeNotes(current => current.map(item => item.id !== note.id ? item : {...item, row_version: saved.row_version,
            updated_at: saved.updated_at, dirty: JSON.stringify(fields(item)) !== signature}));
        }
        setStatus("Đã lưu bản nháp"); return true;
      } catch (cause) {
        setError(`${String(cause)} Bản đang viết được giữ trên trình duyệt này để mở lại.`);
        setStatus("Chưa đồng bộ hết bản nháp"); return false;
      } finally {setSaving(false); saveInFlight.current = null;}
    };
    const promise = task(); saveInFlight.current = promise;
    // Empty saves finish synchronously; ensure the completed promise does not block subsequent edits.
    void promise.finally(() => {if (saveInFlight.current === promise) saveInFlight.current = null;});
    return promise;
  }, [target.annotationsPath, userId, changeNotes]);
  useEffect(() => {
    if (!loaded || !canEdit || !notes.some(note => note.dirty) || notes.some(note => note.conflict)) return;
    const timer = window.setTimeout(() => {void flush();}, 800);
    return () => window.clearTimeout(timer);
  }, [notes, loaded, canEdit, flush]);
  const close = async () => {
    if (submitting || closing || uploading) return;
    setClosing(true); persist();
    if (canEdit) await flush();
    persist(); onClose();
  };
  const closeRef = useRef(close); closeRef.current = close;
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden"; dialog.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {event.preventDefault(); void closeRef.current();}
      if (event.key !== "Tab" || !dialog.current) return;
      const focusable = Array.from(dialog.current.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), a[href]'));
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.current)) {event.preventDefault(); last?.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first?.focus();}
    };
    const onLeave = () => persist();
    document.addEventListener("keydown", onKey); window.addEventListener("pagehide", onLeave);
    return () => {persist(); document.body.style.overflow = overflow; document.removeEventListener("keydown", onKey); window.removeEventListener("pagehide", onLeave); previousFocus?.focus();};
  }, [persist]);

  function newDraft(annotation_kind: ProgressAnnotation["annotation_kind"]): Note {
    return {id:crypto.randomUUID(), annotation_kind, reviewer_id:"", reviewer_name:"Bạn", state:"DRAFT", row_version:0,
      updated_at:new Date().toISOString(), published_at:null, page_number:null, x:null, y:null,
      location_label:"", quoted_text:"", comment:"", dirty:true};
  }
  function changeSummary(value: string) {
    setComment(value);
    changeNotes(current => {
      const existing=current.find(note=>note.annotation_kind === "SUMMARY" && note.state === "DRAFT");
      return existing ? current.map(note=>note.id === existing.id ? {...note,comment:value,dirty:true} : note)
        : [...current,{...newDraft("SUMMARY"),comment:value}];
    });
  }
  async function uploadFeedback(file: File, input: HTMLInputElement) {
    setUploading(true); setError("");
    try {
      if (!(await flush())) return;
      if (file.size > 10*1024*1024 || !/\.(pdf|docx)$/i.test(file.name)) throw new Error("Chọn PDF hoặc DOCX, tối đa 10 MB.");
      const saved=await request<ProgressAnnotation>(`${target.annotationsPath}/${crypto.randomUUID()}/attachment`,userId,{method:"POST",body:file,
        headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(file.name),"If-Match":"0"}});
      changeNotes(current=>[...current,saved]); setStatus("Đã lưu tệp phản hồi nháp trên máy chủ"); input.value="";
    } catch (cause) {setError(`${String(cause)} Nếu kết nối bị ngắt, mở lại hồ sơ để kiểm tra tệp đã lưu trước khi gửi lại.`);}
    finally {setUploading(false);}
  }
  async function rescanFeedback(note: Note) {
    if (!(await flush())) return;
    try {
      const current=notesRef.current.find(item=>item.id === note.id)!;
      const saved=await request<ProgressAnnotation>(`${target.annotationsPath}/${note.id}/attachment/scan`,userId,{method:"POST",headers:{"If-Match":String(current.row_version)}});
      changeNotes(items=>items.map(item=>item.id === note.id ? saved : item));
    } catch (cause) {setError(String(cause));}
  }
  function addNote(pageNumber: number | null = null, x: number | null = null, y: number | null = null, quotedText = "", locationLabel = "") {
    if (!canEdit || submitting) return;
    const id = crypto.randomUUID();
    focusNewNote.current = id;
    changeNotes(current => [...current, {id, annotation_kind:"PIN", reviewer_id: "", reviewer_name: "Bạn", state: "DRAFT", row_version: 0,
      updated_at: new Date().toISOString(), published_at: null, page_number: pageNumber, x, y,
      location_label: locationLabel, quoted_text: quotedText, comment: "", dirty: true}]);
    setSelectedId(id); setPinMode(false); setError("");
  }
  useEffect(() => {
    const id = focusNewNote.current;
    if (!id) return;
    const frame = requestAnimationFrame(() => {
      const input = document.getElementById(`note-comment-${id}`);
      if (!input) return;
      document.getElementById(`review-note-${id}`)?.scrollIntoView({block:"nearest"});
      input.focus({preventScroll:true}); focusNewNote.current = null;
    });
    return () => cancelAnimationFrame(frame);
  }, [selectedId, notes.length]);
  function editNote(id: string, values: Partial<ProgressAnnotationData>) {
    changeNotes(current => current.map(note => note.id === id ? {...note, ...values, dirty: true} : note));
  }
  async function removeNote(id: string) {
    if (!(await flush())) return;
    const note = notesRef.current.find(item => item.id === id);
    if (!note || note.state !== "DRAFT") return;
    try {
      await request(`${target.annotationsPath}/${id}`, userId, {method: "DELETE", headers: {"If-Match": String(note.row_version)}});
      changeNotes(current => current.filter(item => item.id !== id));
      setSelectedId(""); setError("");
    } catch (cause) {setError(String(cause));}
  }
  function selectNote(id: string) {
    const note = notesRef.current.find(item => item.id === id);
    if (!note) return;
    setSelectedId(id); setPinMode(false);
    jumpTo.current = id; if (note.page_number) setPage(note.page_number);
    if (!isPdf || note.page_number === page) requestAnimationFrame(onRendered);
    document.getElementById(`review-note-${id}`)?.scrollIntoView({block: "nearest", behavior: "smooth"});
  }
  function onRendered() {
    if (!pane.current) return;
    if (jumpTo.current) {
      const selector = `[data-note-id="${jumpTo.current}"]`;
      const pin = pane.current.querySelector<HTMLElement>(selector) || pane.current.querySelector(".review-text-sheet")?.shadowRoot?.querySelector<HTMLElement>(selector);
      if (pin) {pin.scrollIntoView({block: "center", behavior: "smooth"}); jumpTo.current = null;}
    } else if (restoreScroll.current) {
      pane.current.scrollTop = scroll.current * Math.max(0, pane.current.scrollHeight - pane.current.clientHeight);
    }
    restoreScroll.current = false;
  }
  useEffect(() => {if (jumpTo.current && (!isPdf || page === notesRef.current.find(note => note.id === jumpTo.current)?.page_number)) onRendered();}, [selectedId]);
  const pins = notes.filter(note => !note.annotation_kind || note.annotation_kind === "PIN");
  const drafts = pins.filter(note => note.state === "DRAFT");
  const attachments = notes.filter(note=>note.annotation_kind === "ATTACHMENT");
  const draftAttachments = attachments.filter(note=>note.state === "DRAFT");
  const feedbackAwaitingScan = draftAttachments.some(note=>note.attachment?.scan_state !== "CLEAN");
  const summary = notes.find(note=>note.annotation_kind === "SUMMARY" && note.state === "DRAFT");
  return createPortal(<div className="review-overlay">
    <div className="review-workspace" role="dialog" aria-modal="true" aria-labelledby="review-title" tabIndex={-1} ref={dialog}>
      <header className="review-header">
        <button type="button" className="review-back" onClick={() => void close()} disabled={submitting || closing || uploading}><ArrowLeft size={18} />{closing ? "Đang lưu…" : "Quay lại"}</button>
        <div className="review-heading"><span className="review-eyebrow">KHÔNG GIAN NHẬN XÉT</span><h2 id="review-title">{target.fileName}</h2>
          <p>{target.label} · lần nộp {target.versionNo} · {target.submittedBy}</p></div>
        <span className="review-save-status" role="status">{saving ? <Save size={16} /> : <Check size={16} />}{status}</span>
      </header>
      <div className="review-body">
        {preview ? <ReviewAttachmentPreview note={preview} endpoint={`${target.annotationsPath}/${preview.id}/attachment`} sourceVersion={target.versionNo}
          onBack={()=>{restoreScroll.current=true; setPreview(null);}} /> : <section className="review-document" aria-label="Tài liệu đang xem">
          <div className="review-toolbar">
            {isPdf && <><div className="review-page-controls"><button type="button" className="review-icon" aria-label="Trang trước" disabled={page <= 1} onClick={() => setPage(value => value - 1)}><ChevronLeft size={18} /></button>
              <label>Trang <input aria-label="Trang PDF" type="number" min={1} max={pages} value={page} onChange={event => setPage(Math.max(1, Math.min(pages, Number(event.target.value) || 1)))} /> / {pages}</label>
              <button type="button" className="review-icon" aria-label="Trang sau" disabled={page >= pages} onClick={() => setPage(value => value + 1)}><ChevronRight size={18} /></button></div>
              <div className="review-zoom-controls"><button type="button" className="review-icon" aria-label="Thu nhỏ PDF" disabled={zoom <= .75} onClick={() => setZoom(value => Math.max(.75, value - .25))}><ZoomOut size={17} /></button>
                <span>{Math.round(zoom * 100)}%</span><button type="button" className="review-icon" aria-label="Phóng to PDF" disabled={zoom >= 2} onClick={() => setZoom(value => Math.min(2, value + .25))}><ZoomIn size={17} /></button></div></>}
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => void downloadFile(target.downloadPath, target.fileName).catch(cause => setError(String(cause)))}><Download size={16} /> Tải bản gốc</button>
          </div>
          {loaded && <div className={`review-pin-hint${pinMode ? " review-pin-hint--active" : ""}`} role="note"><MapPin size={17} /><span>{canEdit ? pinMode ? "Bấm vào vị trí cần góp ý. Ô nhập nhận xét sẽ mở bên phải." : "Bôi chọn đoạn văn → ô Góp ý cần thực hiện tự mở bên phải. Hoặc bật Đặt ghim để chọn một vị trí." : readOnlyReason}</span></div>}
          <div className="review-document-scroll" ref={pane} onScroll={() => {if (pane.current) {scroll.current = pane.current.scrollTop / Math.max(1, pane.current.scrollHeight - pane.current.clientHeight); persist();}}}>
            {isPdf ? data ? <ReviewPdfPage data={data} pageNumber={page} zoom={zoom} notes={pins} selectedId={selectedId} pinMode={pinMode} canAnnotate={canEdit && !submitting}
              onSelect={selectNote} onPin={addNote} onPages={count => {setPages(count); setPage(value => Math.min(count, value));}} onRendered={onRendered} /> : <p className="review-empty">Đang tải PDF đã quét…</p>
              : data ? <ReviewTextDocument data={data} fileName={target.fileName} notes={pins} selectedId={selectedId} pinMode={pinMode} canAnnotate={canEdit && !submitting}
                onSelect={selectNote} onPin={(label, quote) => addNote(null, null, null, quote, label)} onRendered={onRendered} />
                : <p className="review-empty">Đang tải tệp đã quét…</p>}

          </div>
        </section>}
        <aside className="review-sidebar" aria-label="Danh sách nhận xét">
          <div className="review-sidebar-top"><div><h3><MessageSquare size={19} /> Nhận xét trên tệp <span>{pins.length}</span></h3><p>{canEdit ? "Ghim tự lưu, bản nháp chỉ mình bạn xem. SV thấy sau khi bạn gửi kết quả." : "Bấm nhận xét để xem đúng vị trí trong phiên bản này."}</p></div>
            {canEdit && <div className="review-add-actions">{<button type="button" className={`btn ${pinMode ? "btn-primary" : "btn-secondary"} btn-sm`} aria-pressed={pinMode} disabled={!data || submitting} onClick={() => setPinMode(value => !value)}><MapPin size={16} />{pinMode ? "Đang đặt ghim" : "Đặt ghim"}</button>}
              <button type="button" className="btn btn-secondary btn-sm" disabled={submitting || !loaded} onClick={() => addNote()}><Plus size={16} />Theo mục</button></div>}
          </div>
          {(error || storageError) && <div className="review-error" role="alert"><p>{error || "Trình duyệt không lưu được bản nháp cục bộ; hãy chờ ghim đồng bộ lên máy chủ trước khi thoát."}</p>{canEdit && <button type="button" className="btn btn-secondary btn-sm" disabled={saving} onClick={() => {setError(""); void flush();}}>Thử lưu lại</button>}</div>}
          <div className="review-notes">
            {(canEdit || attachments.length > 0) && <section className="review-feedback-files" aria-label="Tệp GV phản hồi">
              <h4><Paperclip size={16} /> Tệp GV phản hồi <small>{attachments.length}</small></h4>
              <p>Gắn với bản SV v{target.versionNo}; không thay tệp SV đã nộp.</p>
              {canEdit && <label>Đính kèm bản đã nhận xét (PDF/DOCX)
                <input type="file" accept=".pdf,.docx" disabled={submitting || uploading || draftAttachments.length >= 5}
                  onChange={event=>{const input=event.currentTarget;const file=input.files?.[0]; if(file) void uploadFeedback(file,input);}} />
                <small>Tối đa 5 tệp, 10 MB/tệp. Có thể ghi nhận xét, hình/bảng/biểu đồ trong Word/PDF rồi tải lên.</small></label>}
              {uploading && <p role="status">Đang tải và quét tệp phản hồi…</p>}
              {attachments.map(note=><article className="review-feedback-file" key={note.id}>
                <strong>{note.attachment?.file_name}</strong><small>{note.reviewer_name} · {((note.attachment?.byte_size || 0)/1024).toFixed(1)} KB</small>
                <span>{note.state === "DRAFT" ? "Nháp riêng — SV chưa thấy" : "Đã gửi cho SV"}</span>
                <div><button type="button" className="btn btn-secondary btn-sm" disabled={note.attachment?.scan_state !== "CLEAN"} onClick={()=>setPreview(note)}>Xem bản GV nhận xét</button>
                  <button type="button" className="btn btn-secondary btn-sm" disabled={note.attachment?.scan_state !== "CLEAN"} onClick={()=>void downloadFile(`${target.annotationsPath}/${note.id}/attachment`,note.attachment!.file_name).catch(cause=>setError(String(cause)))}>Tải tệp phản hồi</button></div>
                {note.attachment?.scan_state !== "CLEAN" && <p role="status">{note.attachment?.scan_state === "INFECTED" ? "Tệp có mã độc, không thể sử dụng." : "Tệp chưa quét sạch; chưa được xem hoặc gửi cho SV."}</p>}
                {canEdit && note.state === "DRAFT" && <div>
                  {["QUARANTINED","FAILED"].includes(note.attachment?.scan_state || "") && <button type="button" className="btn btn-secondary btn-sm" disabled={submitting || uploading} onClick={()=>void rescanFeedback(note)}>Quét lại tệp phản hồi</button>}
                  <button type="button" className="review-remove" disabled={submitting || uploading || saving} onClick={()=>{if(preview?.id === note.id) setPreview(null); void removeNote(note.id);}}>Bỏ tệp phản hồi nháp</button>
                </div>}
              </article>)}
            </section>}

            {loaded && pins.length === 0 && <div className="review-empty"><MessageSquare size={32} /><p>{canEdit ? "Chưa có ghim nào. Chọn một vị trí trên tệp hoặc thêm nhận xét theo mục." : "Chưa có nhận xét theo vị trí được gửi cho phiên bản này."}</p></div>}
            {pins.map((note, index) => <article key={note.id} id={`review-note-${note.id}`} className={`review-note${selectedId === note.id ? " review-note--selected" : ""}`}>
              <div className="review-note-heading"><button type="button" className="review-note-location" onClick={() => selectNote(note.id)}><span>{index + 1}</span>{note.page_number ? `Trang ${note.page_number}` : note.location_label || "Nhận xét theo mục"}</button><small>{note.state === "DRAFT" ? note.dirty ? "Chưa đồng bộ" : "Đã lưu nháp" : note.reviewer_name}</small></div>
              {note.state === "DRAFT" && canEdit ? <div className="review-note-fields">
                {note.x === null && note.y === null && <label>Mục / vị trí<input className="input" value={note.location_label} readOnly={/^(Đoạn|Dòng) \d+$/.test(note.location_label)} maxLength={255} placeholder="Ví dụ: Chương 2 · mục 2.3" disabled={submitting} onChange={event => editNote(note.id, {location_label: event.target.value})} /></label>}
                <label>Đoạn trích (không bắt buộc)<textarea aria-label="Đoạn trích (không bắt buộc)" className="input" rows={2} maxLength={1000} value={note.quoted_text} placeholder="Trích câu cần sửa để SV dễ đối chiếu" disabled={submitting} onChange={event => editNote(note.id, {quoted_text: event.target.value})} /></label>
                <label>Góp ý cần thực hiện<textarea aria-label="Góp ý cần thực hiện" id={`note-comment-${note.id}`} className="input" rows={3} maxLength={2000} value={note.comment} placeholder="Nêu rõ chỗ cần sửa và hướng cải thiện…" disabled={submitting} onChange={event => editNote(note.id, {comment: event.target.value})} /></label>
                {note.conflict && <button type="button" className="btn btn-secondary btn-sm" onClick={() => {changeNotes(current => current.map(item => item.id === note.id ? {...item, id: crypto.randomUUID(), row_version: 0, conflict: false, dirty: true} : item)); setError("");}}>Giữ thành ghim riêng</button>}
                <button type="button" className="review-remove" disabled={saving || submitting} onClick={() => void removeNote(note.id)}><Trash2 size={14} /> Bỏ ghim nháp</button>
              </div> : <div className="review-note-content">{note.quoted_text && <blockquote>{note.quoted_text}</blockquote>}<p><ReviewCommentText text={note.comment} /></p><small>{formatDate(note.published_at || note.updated_at)}</small></div>}
            </article>)}
            {!canEdit && target.reviews.length > 0 && <div className="review-conclusion"><h4>Kết quả phản hồi</h4><Reviews items={target.reviews} /></div>}
          </div>
          {canEdit && <form className="review-submit" onSubmit={async event => {
            event.preventDefault(); setSubmitting(true); setError("");
            try {
              if (!(await flush())) return;
              if (notesRef.current.some(note => note.state === "DRAFT" && note.annotation_kind !== "SUMMARY" && !note.comment.trim())) {setError("Có ghim chưa ghi góp ý. Hãy điền nội dung hoặc bỏ ghim đó trước khi gửi."); return;}
              const conclusion = comment.trim() || `Xem ${drafts.length} ghim và ${draftAttachments.length} tệp phản hồi của lần nộp ${target.versionNo}.`;
              const sent = await run(() => request(target.reviewPath, userId, {method: "POST", headers: {"If-Match": String(target.rowVersion)}, body: JSON.stringify({decision, comment: conclusion})}), "Đã gửi phản hồi cùng các ghim nhận xét đúng phiên bản.");
              if (sent) {
                notesRef.current = []; currentCache.current = {page, zoom, scroll: scroll.current}; persist(); onClose();
              } else setError("Chưa gửi được kết quả. Bản nháp vẫn được giữ; hãy quay lại tải mới hồ sơ để kiểm tra trạng thái phiên bản.");
            } finally {setSubmitting(false);}
          }}><h4>Gửi kết quả cho nhóm</h4><label htmlFor="review-final-decision">Kết quả<select aria-label="Kết quả" className="input" id="review-final-decision" required value={decision} disabled={submitting} onChange={event => setDecision(event.target.value)}>
              <option value="">Chọn kết quả trước khi gửi</option>
              {target.choices.map(choice => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
            </select></label><label htmlFor="review-final-comment">Nhận xét tổng quát<textarea aria-label="Nhận xét tổng quát" className="input" id="review-final-comment" rows={2} maxLength={2000} placeholder="Có thể để trống nếu đã có góp ý trên ghim" value={comment} disabled={submitting || uploading} onChange={event => changeSummary(event.target.value)} /></label>
            {summary?.conflict && <p role="alert">Nhận xét chung đã đổi ở phiên khác. Bản đang viết vẫn được giữ. <button type="button" className="btn btn-secondary btn-sm" onClick={()=>changeNotes(items=>items.map(item=>item.id === summary.id ? {...item,conflict:false,dirty:true} : item))}>Dùng bản đang viết</button></p>}
            <small>Nội dung nháp được lưu trên máy chủ; chọn kết quả khi hoàn thành. SV chỉ thấy sau khi bạn gửi. {drafts.length} ghim · {draftAttachments.length} tệp.</small>
            {feedbackAwaitingScan && <small role="status">Cần quét sạch hoặc bỏ tệp phản hồi chưa an toàn trước khi hoàn thành.</small>}
            <button className="btn btn-primary" disabled={submitting || uploading || feedbackAwaitingScan || !loaded || !decision || (!comment.trim() && drafts.length === 0 && draftAttachments.length === 0)}><Send size={16} />{submitting ? "Đang gửi…" : "Hoàn thành và gửi góp ý"}</button>
          </form>}
        </aside>
      </div>
    </div>
  </div>, document.body);
}
