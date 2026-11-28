import {useCallback,useEffect,useRef,useState} from "react";
import {createPortal} from "react-dom";
import {Link,useSearchParams} from "react-router-dom";
import {Archive,ArrowRight,BookOpen,ChevronDown,Download,Eye,FilePlus2,History,RefreshCw,RotateCcw,Upload} from "lucide-react";
import {downloadFile,request,type Context,type OfficialFormTemplate,type SchoolForm,type SchoolFormRound,type SchoolFormVersion} from "../api";
import PageHeader from "../components/layout/PageHeader";
import FileDropzone from "../components/ui/FileDropzone";
import EmptyState from "../components/ui/EmptyState";
import {SkeletonCard} from "../components/ui/Skeleton";
import Badge from "../components/ui/Badge";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import {formatDate} from "../components/domain/CoreForms";
import {ReadOnlyFilePreview} from "../components/domain/ReviewAttachmentPreview";
import {scanLabel} from "../components/domain/ThesisDocuments";
import {errorMessage} from "../errors";
import "../styles/review-workspace.css";
import "../styles/school-forms.css";

type PreviewTarget = {title:string; fileName:string; endpoint:string; caption:string; downloadOriginal?:()=>void};

function PdfPreview({target,onClose,busy}:{target:PreviewTarget;onClose:()=>void;busy:boolean}) {
  const dialog=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    const old=document.body.style.overflow;const focus=document.activeElement as HTMLElement|null;document.body.style.overflow="hidden";dialog.current?.focus();
    const key=(event:KeyboardEvent)=>{
      if(event.key==="Escape"){event.preventDefault();onClose();}
      if(event.key==="Tab"){
        const controls=Array.from(dialog.current?.querySelectorAll<HTMLElement>("button:not(:disabled),select,a[href]") || []),first=controls[0],last=controls[controls.length-1];
        if(event.shiftKey && (document.activeElement===first || document.activeElement===dialog.current)){event.preventDefault();last?.focus();}
        else if(!event.shiftKey && document.activeElement===last){event.preventDefault();first?.focus();}
      }
    };
    document.addEventListener("keydown",key);return()=>{document.removeEventListener("keydown",key);document.body.style.overflow=old;focus?.focus();};
  },[]);
  return createPortal(<div className="review-overlay"><div className="review-workspace" role="dialog" aria-modal="true" aria-label="Xem tài liệu Khoa" tabIndex={-1} ref={dialog}>
    <header className="review-header"><button type="button" className="review-back" onClick={onClose}>Quay lại</button><div className="review-heading"><h2>{target.title}</h2></div>
      {target.downloadOriginal && <button type="button" className="review-back school-forms-preview-download" disabled={busy} onClick={target.downloadOriginal}><Download size={16} aria-hidden="true"/>Tải tệp gốc</button>}</header>
    <div className="review-body school-forms-preview-body">
      <ReadOnlyFilePreview name={target.fileName} endpoint={target.endpoint} renderAsPdf onBack={onClose} backLabel="Đóng bản xem" label="Biểu mẫu và tài liệu Khoa" caption={target.caption}/>
    </div>
  </div></div>,document.body);
}

type CatalogAction = "versions" | "upload" | "visibility";
type CatalogRow = {item: SchoolForm; source?: OfficialFormTemplate} | {item?: undefined; source: OfficialFormTemplate};
const isPdf = (version: SchoolFormVersion) => /\.pdf$/i.test(version.file_name);

function mayViewCatalog(round: SchoolFormRound | undefined, role: string) {
  return !!round && (round.can_view_catalog ?? (round.can_manage || role === "ADMIN"));
}

function FormCard({item,userId,manage,run,busy,onPreview,action}:{action:CatalogAction;item:SchoolForm;userId:string;manage:boolean;busy:boolean;run:(action:()=>Promise<unknown>,message:string)=>Promise<boolean>;onPreview:(version:SchoolFormVersion)=>void}) {
  const [file,setFile]=useState<File|null>(null),[source,setSource]=useState(""),[reason,setReason]=useState("");
  const [title,setTitle]=useState(item.title),[audience,setAudience]=useState(item.audience),[metaReason,setMetaReason]=useState("");
  const [withdrawVersionId,setWithdrawVersionId]=useState<string|null>(null);
  const [withdrawReason,setWithdrawReason]=useState(""),[visibilityReason,setVisibilityReason]=useState("");
  const card=useRef<HTMLElement>(null);
  useEffect(()=>{card.current?.scrollIntoView({behavior:"smooth",block:"start"});},[action]);
  useEffect(()=>{setTitle(item.title);setAudience(item.audience);},[item.title,item.audience,item.state]);
  const endpoint=`/school-forms/${item.id}`;
  const download=(version:SchoolFormVersion)=>run(async()=>{
    await downloadFile(`${endpoint}/versions/${version.id}/download`,version.file_name);
  },"Đã tải đúng phiên bản tệp gốc.");
  const render=(version:SchoolFormVersion)=>{
    const highestActiveNo = Math.max(0, ...item.versions.filter(v => v.state !== "WITHDRAWN").map(v => v.version_no));
    const publishedNo = Math.max(0, ...item.versions.filter(v => v.state === "PUBLISHED").map(v => v.version_no));
    const canPublishVersion = version.state === "DRAFT" && version.version_no === highestActiveNo && version.version_no > publishedNo;
    return <div key={version.id} className="core-version stack">
    <div className="flex justify-between gap-2"><strong>v{version.version_no} · {version.file_name}</strong><ThesisStatusBadge state={version.state} label={{DRAFT:"Bản nháp",PUBLISHED:"Đang áp dụng",SUPERSEDED:"Bản cũ",WITHDRAWN:"Đã thu hồi"}[version.state] || version.state}/></div>
    <small>{version.uploaded_by_name} · {formatDate(version.uploaded_at)} · {(version.byte_size/1024).toFixed(1)} KB</small>
    <p className="text-body-sm">Nguồn: {version.source_reference}<br/>Lý do cập nhật: {version.change_reason}</p>
    {version.published_at && <small>Phát hành: {formatDate(version.published_at)}</small>}
    <div className="flex flex-wrap gap-2">{isPdf(version) && <button type="button" className="btn btn-secondary btn-sm" disabled={busy || version.scan_state!=="CLEAN"} onClick={()=>onPreview(version)}><Eye size={15} aria-hidden="true"/>Xem trực tiếp</button>}
      <button type="button" className="btn btn-secondary btn-sm" disabled={busy || version.scan_state!=="CLEAN"} onClick={()=>void download(version)}><Download size={15} aria-hidden="true"/>Tải tệp v{version.version_no}</button></div>
    {version.scan_state!=="CLEAN" && <p role="status">{scanLabel(version.scan_state)} — chưa được phát hành/xem.</p>}
    {manage && <><div className="school-form-version__actions">
      {version.state==="DRAFT" && ["QUARANTINED","FAILED"].includes(version.scan_state) && <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={()=>void run(()=>request(`${endpoint}/versions/${version.id}/scan`,userId,{method:"POST",headers:{"If-Match":String(version.row_version)}}),"Đã quét lại tệp.")}>Quét lại</button>}
      {version.state==="DRAFT" && <button type="button" className="btn btn-primary btn-sm" disabled={busy || version.scan_state!=="CLEAN" || item.state!=="ACTIVE" || !canPublishVersion} onClick={()=>void run(()=>request(`${endpoint}/versions/${version.id}/publish`,userId,{method:"POST",headers:{"If-Match":String(version.row_version)},body:JSON.stringify({reason:version.change_reason})}),"Đã phát hành; người dùng đúng quyền thấy phiên bản mới.")}>Phát hành v{version.version_no}</button>}
      {version.state!=="WITHDRAWN" && <button type="button" className="btn btn-secondary btn-sm" disabled={busy}
        aria-expanded={withdrawVersionId===version.id} onClick={()=>{
          setWithdrawVersionId(withdrawVersionId===version.id ? null : version.id);
          setWithdrawReason("");
        }}>Thu hồi v{version.version_no}</button>}
    </div>
    {version.state==="DRAFT" && <small>{canPublishVersion ? "Phát hành sử dụng lý do cập nhật đã lưu cùng phiên bản." : "Chỉ phát hành được bản nháp mới nhất (cao hơn bản đang áp dụng)."}</small>}
    {version.state!=="WITHDRAWN" && withdrawVersionId===version.id && <form className="school-form-version__withdraw" onSubmit={async event=>{
      event.preventDefault();
      if(busy || withdrawReason.trim().length<5)return;
      const saved=await run(()=>request(endpoint+"/versions/"+version.id+"/withdraw",userId,{
        method:"POST",headers:{"If-Match":String(version.row_version)},
        body:JSON.stringify({reason:withdrawReason.trim()}),
      }),"Đã thu hồi phiên bản; lịch sử vẫn giữ.");
      if(saved){setWithdrawVersionId(null);setWithdrawReason("");}
    }}>
      <label htmlFor={"withdraw-"+version.id}>Lý do thu hồi phiên bản</label>
      <textarea id={"withdraw-"+version.id} className="input" rows={2} required minLength={5} maxLength={2000}
        value={withdrawReason} disabled={busy} onChange={event=>setWithdrawReason(event.target.value)}/>
      <div className="school-form-version__actions">
        <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={()=>{setWithdrawVersionId(null);setWithdrawReason("");}}>Hủy</button>
        <button className="btn btn-destructive btn-sm" disabled={busy || withdrawReason.trim().length<5}>Xác nhận thu hồi v{version.version_no}</button>
      </div>
    </form>}</>}
  </div>;};
  const latest=item.versions.find(version=>version.state==="PUBLISHED") || item.versions[0];
  const pending=manage?item.versions.filter(version=>version.state==="DRAFT" && version.id!==latest?.id):[];
  const older=item.versions.filter(version=>version.id!==latest?.id && !pending.some(draft=>draft.id===version.id));
  return <article className="card school-form-card" ref={card}><div className="card-body stack">
    <div className="flex justify-between gap-2"><div><h2>{item.title}</h2><p className="text-body-sm text-muted">{item.code} · {item.document_kind==="FORM"?"Biểu mẫu / hướng dẫn":"Tài liệu công bố theo đợt"} · {item.audience==="LECTURER"?"Chỉ giảng viên":"Sinh viên và giảng viên"}</p></div>{item.state==="ARCHIVED" && <ThesisStatusBadge state="ARCHIVED" label="Ngừng sử dụng"/>}</div>
    {manage && <Link className="text-body-sm" to={`/activity?resource_type=official_form&resource_id=${item.id}`}>Lịch sử thao tác danh mục</Link>}
    {manage && item.state==="ACTIVE" && <details open={action==="upload"}><summary>Cập nhật tệp biểu mẫu / tài liệu</summary><div className="stack"><label htmlFor={`reason-${item.id}`}>Lý do thao tác / cập nhật phiên bản</label><textarea className="input" id={`reason-${item.id}`} value={reason} maxLength={2000} minLength={5} onChange={event=>setReason(event.target.value)} placeholder="Ví dụ: Khoa ban hành mẫu điều chỉnh cho đợt này"/>
      <form className="core-form" onSubmit={async event=>{
        event.preventDefault();const form=event.currentTarget;
        if(!file)return;const payload=new FormData();payload.append("file",file);payload.append("source_reference",source);payload.append("reason",reason);
        if(await run(()=>request(`${endpoint}/versions`,userId,{method:"POST",body:payload,headers:{"If-Match":String(item.row_version)}}),"Đã lưu bản nháp; kiểm tra rồi phát hành.")){setFile(null);setSource("");setReason("");form.reset();}
      }}><label htmlFor={`source-${item.id}`}>Nguồn / văn bản áp dụng</label><input className="input" id={`source-${item.id}`} value={source} required minLength={3} maxLength={500} onChange={event=>setSource(event.target.value)}/>
        <FileDropzone
          id={`file-${item.id}`}
          label="Tải phiên bản mới (PDF/DOCX/XLSX)"
          accept=".pdf,.docx,.xlsx"
          maxBytes={25 * 1024 * 1024}
          hint="Tối đa 25 MB/tệp · Tệp được quét trước khi phát hành."
          file={file}
          required
          disabled={busy}
          onChange={setFile}
        />
        <button className="btn btn-secondary" disabled={busy || !file || file.size>25*1024*1024 || source.trim().length<3 || reason.trim().length<5}><Upload size={16}/>Lưu bản nháp</button>
      </form>
    </div></details>}
    {manage && <details><summary>Sửa tên / đối tượng xem</summary><form className="core-form" onSubmit={async event=>{event.preventDefault();await run(()=>request(endpoint,userId,{method:"PATCH",headers:{"If-Match":String(item.row_version)},body:JSON.stringify({title,audience,state:item.state,reason:metaReason})}),"Đã cập nhật danh mục.");}}>
        <label>Tên hiển thị<input className="input" value={title} required minLength={3} maxLength={255} onChange={event=>setTitle(event.target.value)}/></label>
        <label>Đối tượng xem<select className="input" value={audience} onChange={event=>setAudience(event.target.value as SchoolForm["audience"])}><option value="STUDENT_AND_LECTURER" disabled={/^mau-(06|07|08|09|10|11)$/.test(item.code)}>Sinh viên và giảng viên</option><option value="LECTURER">Chỉ giảng viên</option></select></label>
        <label>Lý do sửa danh mục<textarea className="input" required minLength={5} maxLength={2000} value={metaReason} onChange={event=>setMetaReason(event.target.value)}/></label>
        <button className="btn btn-secondary" disabled={busy || metaReason.trim().length<5}>Lưu danh mục</button>
      </form></details>}
    {manage && action==="visibility" && <form className="core-form" onSubmit={async event=>{event.preventDefault();if(await run(()=>request(endpoint,userId,{method:"PATCH",headers:{"If-Match":String(item.row_version)},body:JSON.stringify({title:item.title,audience:item.audience,state:item.state==="ACTIVE"?"ARCHIVED":"ACTIVE",reason:visibilityReason})}),item.state==="ACTIVE"?"Đã gỡ khỏi kho SV/GV; lịch sử và các bản nộp vẫn được giữ.":"Đã khôi phục biểu mẫu; bản đã phát hành hiển thị lại cho đúng đối tượng."))setVisibilityReason("");}}>
      <h3>{item.state==="ACTIVE"?"Gỡ biểu mẫu khỏi kho SV/GV":"Khôi phục biểu mẫu"}</h3>
      <p>{item.state==="ACTIVE"?"Biểu mẫu sẽ ngừng hiển thị và không tải được bên SV/GV. Giữ tệp và lịch sử để đối chiếu; không xóa hồ sơ đã nộp. Có thể khôi phục sau.":"Khôi phục danh mục không tự phát hành bản nháp hoặc bản đã thu hồi. Chỉ bản đã phát hành mới hiển thị bên SV/GV."}</p>
      <label>Lý do gỡ / khôi phục<textarea className="input" required minLength={5} maxLength={2000} value={visibilityReason} onChange={event=>setVisibilityReason(event.target.value)}/></label>
      <button className="btn btn-secondary" disabled={busy || visibilityReason.trim().length<5}>{item.state==="ACTIVE"?"Xác nhận gỡ khỏi kho":"Xác nhận khôi phục"}</button>
    </form>}
    {latest ? render(latest) : <p>Chưa có tệp phiên bản.</p>}
    {pending.length>0 && <section className="stack"><h3>Bản nháp chờ phát hành</h3>{pending.map(render)}</section>}
    {older.length>0 && <details open={action==="versions"}><summary>{older.some(version=>version.version_no>(latest?.version_no||0))?`Phiên bản khác (${older.length} bản)`:`Lịch sử phiên bản (${older.length} bản trước)`}</summary><div className="stack">{older.map(version=><details key={version.id}><summary>v{version.version_no} · {version.file_name} · {formatDate(version.uploaded_at)}</summary>{render(version)}</details>)}</div></details>}
  </div></article>;
}

export default function SchoolFormsPage({context}:{context:Context}) {
  const [params,setParams]=useSearchParams();const roundId=params.get("round_id") || "";
  const requestedFormId = params.get("form_id");
  const [rounds,setRounds]=useState<SchoolFormRound[]>([]),[items,setItems]=useState<SchoolForm[]>([]);
  const [sources,setSources]=useState<OfficialFormTemplate[]>([]);
  const [sourceError,setSourceError]=useState("");
  const [error,setError]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true);
  const [code,setCode]=useState(""),[title,setTitle]=useState(""),[kind,setKind]=useState("FORM"),[audience,setAudience]=useState("STUDENT_AND_LECTURER"),[reason,setReason]=useState("");
  const [newFile,setNewFile]=useState<File|null>(null),[newSource,setNewSource]=useState("");
  const validNewFile=!!newFile && newFile.size>0 && newFile.size<=25*1024*1024 && /\.(pdf|docx|xlsx)$/i.test(newFile.name);
  const [selectedId,setSelectedId]=useState<string|null>(null),[selectedAction,setSelectedAction]=useState<CatalogAction>("versions");
  const [search,setSearch]=useState(""),[category,setCategory]=useState("ALL");
  const [preview,setPreview]=useState<PreviewTarget|null>(null);
  const load=useCallback(async(signal?:AbortSignal)=>{
    const available=await request<SchoolFormRound[]>("/school-forms/access",context.user_id,{signal});if(signal?.aborted)return;setRounds(available);
    if(!roundId && available.length){setParams({round_id:available[0].id},{replace:true});return;}
    if (!roundId) {setItems([]);setSources([]);setSourceError("");return;}
    const canViewCatalog = mayViewCatalog(available.find(round => round.id === roundId), context.base_role);
    const [rows, originals] = await Promise.allSettled([
      request<SchoolForm[]>(`/school-forms?round_id=${roundId}`,context.user_id,{signal}),
      canViewCatalog ? request<OfficialFormTemplate[]>(`/school-forms/rounds/${roundId}/sources`,context.user_id,{signal}) : [],
    ]);
    if (signal?.aborted) return;
    setSources(originals.status === "fulfilled" ? originals.value : []);
    setSourceError(originals.status === "rejected" ? errorMessage(originals.reason) : "");
    if (rows.status === "rejected") throw rows.reason;
    setItems(rows.value);
  },[roundId,context.base_role,context.user_id,setParams]);
  useEffect(()=>{const controller=new AbortController();setLoading(true);setError("");void load(controller.signal).catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[load]);
  const run=async(action:()=>Promise<unknown>,message:string)=>{
    setBusy(true);setError("");setNotice("");try{await action();await load();setNotice(message);return true;}catch(cause){setError(errorMessage(cause));return false;}finally{setBusy(false);}
  };
  const selected=rounds.find(row=>row.id===roundId),manage=!!selected?.can_manage;
  const canViewCatalog = mayViewCatalog(selected, context.base_role);
  const visibleItems = items.filter(item => item.round_id === roundId && (
    canViewCatalog || item.document_kind === "PUBLICATION" || item.id === requestedFormId
  ));
  const catalogByKey = new Map<string, CatalogRow>();
  if (canViewCatalog) {
    for (const source of sources) catalogByKey.set(`form:${source.id}`, {source});
  }
  for (const item of visibleItems) {
    const key = item.document_kind === "FORM" ? `form:${item.code}` : `publication:${item.id}`;
    catalogByKey.set(key, {item, source:catalogByKey.get(key)?.source});
  }
  const catalogRows = Array.from(catalogByKey.values());
  const hasMissingNumberedSources = catalogRows.some(({item, source}) => !item && source?.id.startsWith("mau-"));
  const showCategory = canViewCatalog && catalogRows.some(({item}) => item?.document_kind !== "PUBLICATION") && catalogRows.some(({item}) => item?.document_kind === "PUBLICATION");
  const query = search.toLocaleLowerCase().trim();
  const displayed = catalogRows.filter(({item, source}) =>
    (!showCategory || category === "ALL" || (item?.document_kind ?? "FORM") === category) &&
    [item?.code, item?.title, source?.id, source?.title, source?.filename].join(" ").toLocaleLowerCase().includes(query)
  );
  async function importOriginals(){
    await run(async()=>{
      try{
        let imported=0;
        for(let batch=0;batch<50;batch++){
          const result=await request<{created:number;remaining:number}>(`/school-forms/bootstrap/${roundId}`,context.user_id,{method:"POST"});
          imported+=result.created;
          setNotice(`Đã nhập ${imported} mẫu gốc; còn ${result.remaining} mẫu sẵn có chưa nhập.`);
          if(!result.remaining||!result.created)break;
        }
      }finally{await load();}
    },"Đã bổ sung các mẫu gốc sẵn có. Mẫu đã có được giữ nguyên; kiểm tra bản nháp nếu tệp chưa quét an toàn.");
  }
  const downloadPublished=(item:SchoolForm,version:SchoolFormVersion)=>run(async()=>{
    await downloadFile(`/school-forms/${item.id}/versions/${version.id}/download`,version.file_name);
  },"Đã tải bản đang áp dụng.");
  const downloadSource = (source: OfficialFormTemplate) => run(
    () => downloadFile(`/school-forms/rounds/${roundId}/sources/${source.id}`, source.filename),
    "Đã tải tệp nguồn của Khoa.",
  );
  const showSource = (source: OfficialFormTemplate) => setPreview({
    title:source.title, fileName:source.filename,
    endpoint:`/school-forms/rounds/${roundId}/sources/${source.id}/preview`,
    caption:"Bản xem PDF theo bố cục in của tệp nguồn Khoa.",
    downloadOriginal:()=>void downloadSource(source),
  });
  const showVersion = (item: SchoolForm, version: SchoolFormVersion) => setPreview({
    title:item.title, fileName:version.file_name,
    endpoint:`/school-forms/${item.id}/versions/${version.id}/download`,
    caption:`${item.code} · v${version.version_no} · ${version.state === "PUBLISHED" ? "Bản đang áp dụng" : "Bản lịch sử / nháp"} · ${version.source_reference}`,
  });
  useEffect(()=>{setSelectedId(null);setCategory("ALL");},[roundId,context.user_id]);
  useEffect(()=>{
    if(!roundId)return;
    const controller=new AbortController();
    const update=()=>{if(document.visibilityState==="visible")void load(controller.signal).catch(()=>{});};
    const timer=window.setInterval(update,30000);window.addEventListener("focus",update);
    return()=>{controller.abort();window.clearInterval(timer);window.removeEventListener("focus",update);};
  },[load,manage,roundId]);

  const catalogMode = canViewCatalog || context.base_role === "ADMIN";
  return <><PageHeader title={catalogMode ? "Kho biểu mẫu & tài liệu Khoa" : "Tài liệu Khoa công bố"} description={catalogMode ? "Theo dõi phiên bản biểu mẫu và tài liệu công bố theo đợt." : "Xem tài liệu Khoa đã phát hành cho đợt khóa luận của bạn."}>{context.base_role !== "ADMIN" && <Link className="btn btn-primary" to="/submissions">Mở hồ sơ nộp &amp; xét duyệt<ArrowRight size={15} aria-hidden="true"/></Link>}</PageHeader>
    <div className="stack school-forms-page"><div className="card"><div className="card-body school-forms-toolbar">
      <div className="school-forms-toolbar__filters"><label>Đợt KLTN<select className="input" value={roundId} disabled={busy} onChange={event=>setParams({round_id:event.target.value})}>{!rounds.length && <option value="">Chưa có đợt trong phạm vi</option>}{rounds.map(row=><option key={row.id} value={row.id}>{row.label}</option>)}</select></label><button type="button" className="btn btn-secondary" disabled={busy || loading} onClick={()=>void run(async()=>{},"Đã làm mới kho tài liệu Khoa.")}><RefreshCw size={16} aria-hidden="true"/>Làm mới kho</button><label>{catalogMode ? "Tìm biểu mẫu / tài liệu" : "Tìm tài liệu"}<input className="input" value={search} onChange={event=>setSearch(event.target.value)} placeholder="Nhập tên hoặc mã"/></label>{showCategory && <label>Nhóm tài liệu<select className="input" value={category} onChange={event=>setCategory(event.target.value)}><option value="ALL">Tất cả</option><option value="FORM">Biểu mẫu trắng / hướng dẫn</option><option value="PUBLICATION">Tài liệu công bố theo đợt</option></select></label>}</div>
      {selected?.can_export_list && <p className="school-forms-toolbar__export"><Link to={"/topics?round_id="+encodeURIComponent(roundId)}>Xuất danh sách theo Mẫu 4</Link> để lấy danh sách sinh viên, đề tài và GVHD của đợt.</p>}
      {(canViewCatalog || displayed.length > 0) && <p className="school-forms-toolbar__help">{canViewCatalog ? "Dùng nút Xem tệp nguồn để xem bố cục in. Tải tệp gốc để mở và in bằng Word hoặc Excel." : "Tải tệp gốc để mở và in bằng Word hoặc Excel."}</p>}
      <div className="school-forms-toolbar__actions">{context.base_role==="ADMIN" && <Link className="btn btn-secondary" to="/administration/assignments">Phân công thêm người quản lý biểu mẫu</Link>}

      </div>
    </div></div>
    {error && <p role="alert" className="alert alert-danger">{error}</p>}{notice && <p role="status" className="alert alert-success">{notice}</p>}
    {canViewCatalog && !loading && (sourceError
      ? <p role="alert" className="alert alert-danger">Không tải được danh sách tệp nguồn của Khoa. {sourceError}</p>
      : sources.length === 0 && <p className="text-body-sm text-muted">Thư mục biểu mẫu trên máy chủ chưa có tệp nguồn.</p>)}
    {manage && !loading && hasMissingNumberedSources && <details className="card school-form-create" key={roundId}>
      <summary className="school-form-create__summary"><Archive size={19} aria-hidden="true"/><strong>Bổ sung mẫu nguồn vào đợt</strong><ChevronDown className="school-form-create__chevron" size={18} aria-hidden="true"/></summary>
      <form className="card-body stack" onSubmit={e=>{e.preventDefault();void importOriginals();}}>
      <p>Bổ sung các mẫu đánh số còn thiếu vào danh mục đợt này. Tệp qua quét an toàn sẽ được phát hành cho đúng đối tượng.</p>
      <label className="checkbox-label"><input type="checkbox" required disabled={busy}/>Tôi đã đối chiếu bộ mẫu nguồn được Khoa chấp thuận.</label>
      <button className="btn btn-secondary" disabled={busy}>{busy?"Đang nhập và quét mẫu…":"Bổ sung các mẫu còn thiếu"}</button>
    </form></details>}
    {manage && <details className="card school-form-create"><summary className="school-form-create__summary"><FilePlus2 size={19} aria-hidden="true"/><span><strong>Thêm biểu mẫu hoặc tài liệu công bố</strong><small>Tạo danh mục và tải tệp trong một bước</small></span><ChevronDown className="school-form-create__chevron" size={18} aria-hidden="true"/></summary><div className="card-body school-form-create__body"><form className="school-form-create__form" onSubmit={async event=>{
      event.preventDefault();
      if(busy || !newFile || !validNewFile || newSource.trim().length<3 || reason.trim().length<5)return;
      const form=event.currentTarget;
      let created:SchoolForm|null=null;
      setBusy(true);setError("");setNotice("");
      try {
        created=await request<SchoolForm>("/school-forms",context.user_id,{method:"POST",body:JSON.stringify({round_id:roundId,code:code.trim(),title:title.trim(),document_kind:kind,audience,reason:reason.trim()})});
        setSearch("");setCategory("ALL");setSelectedId(created.id);setSelectedAction("versions");
        const payload=new FormData();payload.append("file",newFile);payload.append("source_reference",newSource.trim());payload.append("reason",reason.trim());
        await request("/school-forms/"+created.id+"/versions",context.user_id,{method:"POST",body:payload,headers:{"If-Match":String(created.row_version)}});
        await load();
        setNotice("Đã lưu tệp thành phiên bản nháp. Kiểm tra trạng thái quét và nội dung; chỉ phát hành khi biểu mẫu đã được Khoa chấp thuận.");
      } catch(cause) {
        if(created){
          await load().catch(()=>undefined);
          setSelectedId(created.id);setSelectedAction("versions");
          setError("Danh mục đã được tạo nhưng chưa xác nhận được kết quả tải tệp. Hãy kiểm tra lịch sử phiên bản bên dưới; nếu chưa có tệp, chọn Cập nhật tệp để tải lại. "+errorMessage(cause));
        } else setError(errorMessage(cause)+" Nếu kết nối bị gián đoạn, hãy tìm mã tài liệu trong danh sách trước khi thử tạo lại.");
      } finally {
        if(created){setCode("");setTitle("");setReason("");setNewSource("");setNewFile(null);form.reset();}
        setBusy(false);
      }
    }}><div className="school-form-create__grid">
      <label>Mã tài liệu<input className="input" required pattern="[a-z0-9][a-z0-9_-]{1,49}" value={code} placeholder="Ví dụ: huong-dan-bao-ve" onChange={event=>{setCode(event.target.value);if(/^mau-(06|07|08|09|10|11)$/.test(event.target.value))setAudience("LECTURER");}}/></label>
      <label>Tên tài liệu<input className="input" required minLength={3} maxLength={255} value={title} placeholder="Ví dụ: Hướng dẫn bảo vệ khóa luận" onChange={event=>setTitle(event.target.value)}/></label>
      <label htmlFor="catalog-kind">Phân loại<select id="catalog-kind" aria-label="Phân loại" className="input" value={kind} onChange={event=>setKind(event.target.value)}><option value="FORM">Biểu mẫu trắng / hướng dẫn</option><option value="PUBLICATION">Tài liệu công bố theo đợt</option></select></label>
      <label>Cho ai xem<select className="input" value={audience} onChange={event=>setAudience(event.target.value)}><option value="STUDENT_AND_LECTURER" disabled={/^mau-(06|07|08|09|10|11)$/.test(code)}>Sinh viên và giảng viên</option><option value="LECTURER">Chỉ giảng viên</option></select></label>
      <label>Nguồn / văn bản áp dụng<input className="input" required minLength={3} maxLength={500} value={newSource} onChange={event=>setNewSource(event.target.value)} placeholder="Ví dụ: Mẫu Khoa cung cấp"/></label>
      <div className="school-form-create__file">
        <FileDropzone
          id="new-school-form-file"
          label="Tệp biểu mẫu hoặc tài liệu (PDF, DOCX, XLSX)"
          accept=".pdf,.docx,.xlsx"
          maxBytes={25 * 1024 * 1024}
          hint="Tối đa 25 MB · Tệp được quét trước khi phát hành."
          file={newFile}
          required
          disabled={busy}
          onChange={setNewFile}
        />
      </div>
      <label className="school-form-create__wide">Lý do tạo danh mục<textarea className="input" rows={2} required minLength={5} maxLength={2000} value={reason} onChange={event=>setReason(event.target.value)}/></label>
    </div>
    <div className="school-form-create__footer"><p>Mẫu 6–11 chỉ dành cho GV. Tệp mới được lưu nháp; chỉ phát hành sau khi Khoa chấp thuận.</p>
      <button className="btn btn-primary" disabled={busy || !roundId || !validNewFile || newSource.trim().length<3 || reason.trim().length<5}><BookOpen size={16}/>{busy?"Đang lưu và quét tệp…":"Tạo và lưu tệp nháp"}</button>
    </div>
    </form></div></details>}
    {loading ? <div className="stack" role="status" aria-label="Đang tải tài liệu Khoa"><SkeletonCard /><SkeletonCard /></div>
      : displayed.length === 0 ? <EmptyState title="Chưa có tài liệu trong phạm vi này" description="Thử chọn đợt khác hoặc bỏ từ khóa tìm kiếm." />
      : <><div className="table-container" role="region" aria-label="Danh mục biểu mẫu Khoa" tabIndex={0}><table className="table">
        <thead><tr><th>Mã / tên biểu mẫu</th><th>Loại</th><th>Đối tượng</th><th>Bản đang áp dụng</th><th>Trạng thái</th><th>Thao tác</th></tr></thead>
        <tbody>{displayed.map(({item, source}) => {
          const published = item?.versions.find(version => version.state === "PUBLISHED");
          const historyOpen = !!item && selectedId === item.id && selectedAction === "versions";
          return <tr key={source?.id ?? item?.id}>
            <td><strong>{item?.title ?? source?.title}</strong><div className="text-caption">{item?.code ?? source?.id}</div>
              {source && <div className="text-caption school-form-source-name">{source.filename}</div>}</td>
            <td>{item?.document_kind === "PUBLICATION" ? "Tài liệu công bố" : "Biểu mẫu"}</td>
            <td>{item ? (item.audience === "LECTURER" ? "Giảng viên" : "SV và GV") : "—"}</td>
            <td>{published ? `v${published.version_no} · ${formatDate(published.published_at || published.uploaded_at)}` : "Chưa phát hành"}</td>
            <td>{item ? <ThesisStatusBadge state={item.state === "ACTIVE" ? "ACTIVE" : "ARCHIVED"} label={item.state === "ACTIVE" ? "Đang sử dụng" : "Đã ẩn / ngừng sử dụng"}/> : <Badge variant="info" dot>Tệp nguồn của Khoa</Badge>}</td>
            <td className="school-form-actions-cell"><div className="school-form-actions">
              {source && <>
                <button type="button" className="btn btn-secondary school-form-action-button" title="Xem tệp nguồn của Khoa" aria-label={`Xem tệp nguồn ${source.title}`} disabled={busy}
                  onClick={()=>showSource(source)}><Eye size={17} aria-hidden="true"/></button>
                <button type="button" className="btn btn-secondary school-form-action-button" title="Tải tệp nguồn của Khoa" aria-label={`Tải tệp nguồn ${source.title}`} disabled={busy}
                  onClick={()=>void downloadSource(source)}><Download size={17} aria-hidden="true"/></button>
              </>}
              {item && published && <>
                {isPdf(published) && <button type="button" className="btn btn-secondary school-form-action-button" title="Xem PDF bản đang áp dụng" aria-label="Xem trực tiếp" disabled={busy || published.scan_state!=="CLEAN"} onClick={()=>showVersion(item,published)}><Eye size={17} aria-hidden="true"/></button>}
                <button type="button" className="btn btn-secondary school-form-action-button" title="Tải tệp gốc bản đang áp dụng" aria-label="Tải tệp gốc" disabled={busy || published.scan_state!=="CLEAN"} onClick={()=>void downloadPublished(item,published)}><Download size={17} aria-hidden="true"/></button>
              </>}
              {item && manage && <>
                <button type="button" className="btn btn-secondary school-form-action-button" title="Tải tệp mới thành một phiên bản nháp" aria-label="Cập nhật tệp" disabled={busy || item.state!=="ACTIVE"} onClick={()=>{setSelectedId(item.id);setSelectedAction("upload");}}><Upload size={17} aria-hidden="true"/></button>
                <button type="button" className="btn btn-secondary school-form-action-button" title={item.state==="ACTIVE"?"Ẩn khỏi kho SV/GV, vẫn giữ tệp và lịch sử":"Khôi phục biểu mẫu đã ẩn"} aria-label={item.state==="ACTIVE"?"Gỡ khỏi kho":"Khôi phục"} disabled={busy} onClick={()=>{setSelectedId(item.id);setSelectedAction("visibility");}}>{item.state==="ACTIVE"?<Archive size={17} aria-hidden="true"/>:<RotateCcw size={17} aria-hidden="true"/>}</button>
              </>}
              {item && <button type="button" className="btn btn-secondary school-form-action-button" title="Xem bản nháp và lịch sử; mở từng bản để xem hoặc tải xuống" aria-label={historyOpen?"Thu gọn lịch sử phiên bản":"Lịch sử phiên bản"} aria-expanded={historyOpen} onClick={()=>{setSelectedId(historyOpen?null:item.id);setSelectedAction("versions");}}><History size={17} aria-hidden="true"/></button>}
            </div></td>
          </tr>;
        })}</tbody>
      </table></div>{displayed.flatMap(({item}) => item && item.id === selectedId
        ? [<FormCard key={item.id} item={item} userId={context.user_id} manage={manage} action={selectedAction} busy={busy} run={run} onPreview={version=>showVersion(item,version)}/>] : [])}</>}
    </div>{preview && <PdfPreview target={preview} busy={busy} onClose={()=>setPreview(null)}/>}</>;
}
