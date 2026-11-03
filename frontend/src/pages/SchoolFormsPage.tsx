import {useCallback,useEffect,useRef,useState} from "react";
import {createPortal} from "react-dom";
import {Link,useSearchParams} from "react-router-dom";
import {Archive,BookOpen,Download,Eye,FilePlus2,History,RefreshCw,RotateCcw,Upload} from "lucide-react";
import {fetchReviewFile,request,type Context,type SchoolForm,type SchoolFormRound,type SchoolFormVersion} from "../api";
import PageHeader from "../components/layout/PageHeader";
import {formatDate} from "../components/domain/CoreForms";
import {ReadOnlyFilePreview} from "../components/domain/ReviewAttachmentPreview";
import {scanLabel} from "../components/domain/ThesisDocuments";
import {errorMessage} from "../errors";
import "../styles/review-workspace.css";
import "../styles/school-forms.css";

function Preview({item,version,userId,onClose}:{item:SchoolForm;version:SchoolFormVersion;userId:string;onClose:()=>void}) {
  const dialog=useRef<HTMLDivElement>(null);
  const [sheets,setSheets]=useState<{name:string;rows:string[][];truncated:boolean}[]>([]),[sheet,setSheet]=useState(0),[error,setError]=useState("");
  const endpoint=`/school-forms/${item.id}/versions/${version.id}`;
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
  useEffect(()=>{
    if(!version.file_name.toLowerCase().endsWith(".xlsx"))return;
    const controller=new AbortController();void request<{sheets:typeof sheets}>(endpoint+"/spreadsheet",userId,{signal:controller.signal}).then(result=>setSheets(result.sheets))
      .catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));});return()=>controller.abort();
  },[endpoint,userId,version.file_name]);
  return createPortal(<div className="review-overlay"><div className="review-workspace" role="dialog" aria-modal="true" aria-label="Xem tài liệu Khoa" tabIndex={-1} ref={dialog}>
    <header className="review-header"><button type="button" className="review-back" onClick={onClose}>Quay lại</button><div className="review-heading"><h2>{item.title}</h2><p>{item.code} · v{version.version_no} · {version.state==="PUBLISHED"?"Bản đang áp dụng":"Bản lịch sử / nháp"}</p></div></header>
    <div className="review-body" style={{gridTemplateColumns:"minmax(0,1fr)"}}>
      {version.file_name.toLowerCase().endsWith(".xlsx") ? <section className="review-document"><div className="review-toolbar"><label>Trang tính <select className="input" value={sheet} onChange={event=>setSheet(Number(event.target.value))}>{sheets.map((row,index)=><option key={row.name} value={index}>{row.name}</option>)}</select></label><small>Bản xem nhanh dữ liệu. Tải tệp Excel gốc để giữ đầy đủ định dạng.</small></div>
        <div className="review-document-scroll" style={{padding:16}}>{error?<p role="alert">{error}</p>:!sheets.length?<p role="status">Đang mở bảng tính…</p>:<><div className="table-container"><table className="table"><tbody>{sheets[sheet].rows.map((row,index)=><tr key={index}><th>{index+1}</th>{row.map((value,column)=><td key={column} style={{whiteSpace:"pre-wrap",minWidth:100}}>{value}</td>)}</tr>)}</tbody></table></div>{sheets[sheet].truncated && <p>Bản xem giới hạn 200 dòng/30 cột; tải tệp để xem đầy đủ.</p>}</>}</div></section>
        : <ReadOnlyFilePreview name={version.file_name} endpoint={endpoint+"/download"} onBack={onClose} backLabel="Đóng bản xem" label="Biểu mẫu và tài liệu Khoa" caption={`${item.code} · phiên bản ${version.version_no} · ${version.source_reference}`}/>}
    </div>
  </div></div>,document.body);
}

type CatalogAction = "versions" | "upload" | "visibility";

function FormCard({item,userId,manage,run,busy,onPreview,action}:{action:CatalogAction;item:SchoolForm;userId:string;manage:boolean;busy:boolean;run:(action:()=>Promise<unknown>,message:string)=>Promise<boolean>;onPreview:(version:SchoolFormVersion)=>void}) {
  const [file,setFile]=useState<File|null>(null),[source,setSource]=useState(""),[reason,setReason]=useState("");
  const [title,setTitle]=useState(item.title),[audience,setAudience]=useState(item.audience),[metaReason,setMetaReason]=useState("");
  const [withdrawReason,setWithdrawReason]=useState(""),[visibilityReason,setVisibilityReason]=useState("");
  const card=useRef<HTMLElement>(null);
  useEffect(()=>{card.current?.scrollIntoView({behavior:"smooth",block:"start"});},[action]);
  useEffect(()=>{setTitle(item.title);setAudience(item.audience);},[item.title,item.audience,item.state]);
  const endpoint=`/school-forms/${item.id}`;
  const download=(version:SchoolFormVersion)=>run(async()=>{
    const buffer=await fetchReviewFile(`${endpoint}/versions/${version.id}/download`),url=URL.createObjectURL(new Blob([buffer]));
    const link=document.createElement("a");link.href=url;link.download=version.file_name;link.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  },"Đã tải đúng phiên bản tệp gốc.");
  const render=(version:SchoolFormVersion)=><div key={version.id} className="core-version stack">
    <div className="flex justify-between gap-2"><strong>v{version.version_no} · {version.file_name}</strong><span className="badge badge-primary">{{DRAFT:"Bản nháp",PUBLISHED:"Đang áp dụng",SUPERSEDED:"Bản cũ",WITHDRAWN:"Đã thu hồi"}[version.state] || version.state}</span></div>
    <small>{version.uploaded_by_name} · {formatDate(version.uploaded_at)} · {(version.byte_size/1024).toFixed(1)} KB</small>
    <p className="text-body-sm">Nguồn: {version.source_reference}<br/>Lý do cập nhật: {version.change_reason}</p>
    {version.published_at && <small>Phát hành: {formatDate(version.published_at)}</small>}
    <div className="flex gap-2" style={{flexWrap:"wrap"}}><button type="button" className="btn btn-secondary btn-sm" disabled={busy || version.scan_state!=="CLEAN"} onClick={()=>onPreview(version)}><Eye size={15}/>Xem trực tiếp</button>
      <button type="button" className="btn btn-secondary btn-sm" disabled={busy || version.scan_state!=="CLEAN"} onClick={()=>void download(version)}><Download size={15}/>Tải tệp v{version.version_no}</button></div>
    {version.scan_state!=="CLEAN" && <p role="status">{scanLabel(version.scan_state)} — chưa được phát hành/xem.</p>}
    {manage && <><div className="flex gap-2" style={{flexWrap:"wrap"}}>
      {version.state==="DRAFT" && ["QUARANTINED","FAILED"].includes(version.scan_state) && <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={()=>void run(()=>request(`${endpoint}/versions/${version.id}/scan`,userId,{method:"POST",headers:{"If-Match":String(version.row_version)}}),"Đã quét lại tệp.")}>Quét lại</button>}
      {version.state==="DRAFT" && <button type="button" className="btn btn-primary btn-sm" disabled={busy || version.scan_state!=="CLEAN" || item.state!=="ACTIVE"} onClick={()=>void run(()=>request(`${endpoint}/versions/${version.id}/publish`,userId,{method:"POST",headers:{"If-Match":String(version.row_version)},body:JSON.stringify({reason:version.change_reason})}),"Đã phát hành; người dùng đúng quyền thấy phiên bản mới.")}>Phát hành v{version.version_no}</button>}
      {version.state!=="WITHDRAWN" && <details><summary>Thu hồi v{version.version_no}</summary><label>Lý do thu hồi phiên bản<textarea className="input" value={withdrawReason} minLength={5} maxLength={2000} onChange={event=>setWithdrawReason(event.target.value)}/></label><button type="button" className="btn btn-secondary btn-sm" disabled={busy || withdrawReason.trim().length<5} onClick={()=>void run(()=>request(`${endpoint}/versions/${version.id}/withdraw`,userId,{method:"POST",headers:{"If-Match":String(version.row_version)},body:JSON.stringify({reason:withdrawReason})}),"Đã thu hồi phiên bản; lịch sử vẫn giữ.")}>Xác nhận thu hồi v{version.version_no}</button></details>}
    </div>{version.state==="DRAFT" && <small>Phát hành sử dụng lý do cập nhật đã lưu cùng phiên bản.</small>}</>}
  </div>;
  const latest=item.versions.find(version=>version.state==="PUBLISHED") || item.versions[0];
  const pending=manage?item.versions.filter(version=>version.state==="DRAFT" && version.id!==latest?.id):[];
  const older=item.versions.filter(version=>version.id!==latest?.id && !pending.some(draft=>draft.id===version.id));
  return <article className="card school-form-card" ref={card}><div className="card-body stack">
    <div className="flex justify-between gap-2"><div><h2>{item.title}</h2><p className="text-body-sm text-muted">{item.code} · {item.document_kind==="FORM"?"Biểu mẫu / hướng dẫn":"Tài liệu công bố theo đợt"} · {item.audience==="LECTURER"?"Chỉ giảng viên":"Sinh viên và giảng viên"}</p></div>{item.state==="ARCHIVED" && <span>Ngừng sử dụng</span>}</div>
    {manage && <Link className="text-body-sm" to={`/activity?resource_type=official_form&resource_id=${item.id}`}>Lịch sử thao tác danh mục</Link>}
    {manage && <details open={action==="upload"}><summary>Cập nhật tệp biểu mẫu / tài liệu</summary><div className="stack"><label htmlFor={`reason-${item.id}`}>Lý do thao tác / cập nhật phiên bản</label><textarea className="input" id={`reason-${item.id}`} value={reason} maxLength={2000} minLength={5} onChange={event=>setReason(event.target.value)} placeholder="Ví dụ: Khoa ban hành mẫu điều chỉnh cho đợt này"/>
      {item.state==="ACTIVE" && <form className="core-form" onSubmit={async event=>{
        event.preventDefault();const form=event.currentTarget;
        if(!file)return;const payload=new FormData();payload.append("file",file);payload.append("source_reference",source);payload.append("reason",reason);
        if(await run(()=>request(`${endpoint}/versions`,userId,{method:"POST",body:payload,headers:{"If-Match":String(item.row_version)}}),"Đã lưu bản nháp; kiểm tra rồi phát hành.")){setFile(null);form.reset();}
      }}><label htmlFor={`source-${item.id}`}>Nguồn / văn bản áp dụng</label><input className="input" id={`source-${item.id}`} value={source} required minLength={3} maxLength={500} onChange={event=>setSource(event.target.value)}/>
        <label htmlFor={`file-${item.id}`}>Tải phiên bản mới (PDF/DOCX/XLSX)</label><small>Tối đa 25 MB/tệp.</small><input id={`file-${item.id}`} type="file" accept=".pdf,.docx,.xlsx" required disabled={busy} onChange={event=>setFile(event.target.files?.[0] || null)}/>
        <button className="btn btn-secondary" disabled={busy || !file || file.size>25*1024*1024 || source.trim().length<3 || reason.trim().length<5}><Upload size={16}/>Lưu bản nháp</button>
        {file && file.size>25*1024*1024 && <p role="alert">Tệp biểu mẫu Khoa tối đa 25 MB.</p>}
      </form>}
    </div></details>}
    {manage && <details><summary>Sửa tên / đối tượng xem</summary><form className="core-form" onSubmit={async event=>{event.preventDefault();await run(()=>request(endpoint,userId,{method:"PATCH",headers:{"If-Match":String(item.row_version)},body:JSON.stringify({title,audience,state:item.state,reason:metaReason})}),"Đã cập nhật danh mục.");}}>
        <label>Tên hiển thị<input className="input" value={title} required minLength={3} maxLength={255} onChange={event=>setTitle(event.target.value)}/></label>
        <label>Đối tượng xem<select className="input" value={audience} onChange={event=>setAudience(event.target.value as SchoolForm["audience"])}><option value="STUDENT_AND_LECTURER">Sinh viên và giảng viên</option><option value="LECTURER">Chỉ giảng viên</option></select></label>
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
  const [rounds,setRounds]=useState<SchoolFormRound[]>([]),[items,setItems]=useState<SchoolForm[]>([]);
  const [error,setError]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true);
  const [bootstrapInfo,setBootstrapInfo]=useState<{created:number;published:number;drafts:number;missing:string[]}|null>(null);
  const [code,setCode]=useState(""),[title,setTitle]=useState(""),[kind,setKind]=useState("FORM"),[audience,setAudience]=useState("STUDENT_AND_LECTURER"),[reason,setReason]=useState("");
  const [selectedId,setSelectedId]=useState<string|null>(null),[selectedAction,setSelectedAction]=useState<CatalogAction>("versions");
  const [search,setSearch]=useState(""),[category,setCategory]=useState("ALL");
  const [preview,setPreview]=useState<{item:SchoolForm;version:SchoolFormVersion}|null>(null);
  const load=useCallback(async(signal?:AbortSignal)=>{
    const available=await request<SchoolFormRound[]>("/school-forms/access",context.user_id,{signal});if(signal?.aborted)return;setRounds(available);
    if(!roundId && available.length){setParams({round_id:available[0].id},{replace:true});return;}
    if(roundId){const rows=await request<SchoolForm[]>(`/school-forms?round_id=${roundId}`,context.user_id,{signal});if(!signal?.aborted)setItems(rows);}else setItems([]);
  },[roundId,context.user_id,setParams]);
  useEffect(()=>{const controller=new AbortController();setLoading(true);setError("");void load(controller.signal).catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[load]);
  const run=async(action:()=>Promise<unknown>,message:string)=>{
    setBusy(true);setError("");setNotice("");try{await action();await load();setNotice(message);return true;}catch(cause){setError(errorMessage(cause));return false;}finally{setBusy(false);}
  };
  const showCategory=items.some(item=>item.document_kind==="FORM") && items.some(item=>item.document_kind==="PUBLICATION");
  const displayed=items.filter(item=>(!showCategory || category==="ALL" || item.document_kind===category) && `${item.code} ${item.title}`.toLocaleLowerCase().includes(search.toLocaleLowerCase().trim()));
  const selected=rounds.find(row=>row.id===roundId),manage=!!selected?.can_manage;
  const downloadPublished=(item:SchoolForm,version:SchoolFormVersion)=>run(async()=>{
    const buffer=await fetchReviewFile(`/school-forms/${item.id}/versions/${version.id}/download`);
    const url=URL.createObjectURL(new Blob([buffer]));const link=document.createElement("a");link.href=url;link.download=version.file_name;link.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  },"Đã tải bản đang áp dụng.");
  useEffect(()=>{setSelectedId(null);setCategory("ALL");setBootstrapInfo(null);},[roundId,context.user_id]);
  useEffect(()=>{
    if(!roundId)return;
    const controller=new AbortController();
    const update=()=>{if(document.visibilityState==="visible")void load(controller.signal).catch(()=>{});};
    const timer=window.setInterval(update,30000);window.addEventListener("focus",update);
    return()=>{controller.abort();window.clearInterval(timer);window.removeEventListener("focus",update);};
  },[load,manage,roundId]);

  return <><PageHeader title="Kho biểu mẫu & tài liệu Khoa" description={manage ? "Quản lý mẫu trắng, hướng dẫn và tài liệu công bố theo đợt. Bản mới chỉ hiển thị cho đúng đối tượng sau khi phát hành." : "Xem và tải mẫu trắng, hướng dẫn hoặc tài liệu Khoa công bố. Bản đã điền được nộp tại Hồ sơ nộp & xét duyệt."}>{context.base_role !== "ADMIN" && <Link className="btn btn-primary" to="/submissions">Mở hồ sơ nộp & xét duyệt</Link>}</PageHeader>
    <div className="stack school-forms-page"><div className="card"><div className="card-body stack">
      <div className="flex gap-2" style={{alignItems:"end",flexWrap:"wrap"}}><label>Đợt KLTN<select className="input" value={roundId} disabled={busy} onChange={event=>setParams({round_id:event.target.value})}>{!rounds.length && <option value="">Chưa có đợt trong phạm vi</option>}{rounds.map(row=><option key={row.id} value={row.id}>{row.label}</option>)}</select></label><button type="button" className="btn btn-secondary" disabled={busy || loading} onClick={()=>void run(async()=>{},"Đã làm mới kho tài liệu Khoa.")}><RefreshCw size={16}/>Làm mới kho</button></div>
      <div className="flex gap-2" style={{flexWrap:"wrap"}}><label>Tìm biểu mẫu / tài liệu<input className="input" value={search} onChange={event=>setSearch(event.target.value)} placeholder="Nhập tên hoặc mã"/></label>{showCategory && <label>Nhóm tài liệu<select className="input" value={category} onChange={event=>setCategory(event.target.value)}><option value="ALL">Tất cả</option><option value="FORM">Biểu mẫu trắng / hướng dẫn</option><option value="PUBLICATION">Tài liệu công bố theo đợt</option></select></label>}</div>
      {manage ? <p>Bạn có quyền thêm, cập nhật và gỡ biểu mẫu của đợt này. Tải lên chỉ tạo nháp; phát hành để SV/GV đúng quyền xem bản mới. Bản cũ giữ trong lịch sử.</p> : <p>Mẫu trắng để điền và danh sách SV đã chốt được trình bày riêng. Tài liệu công bố chỉ hiện trong phạm vi đợt của bạn.</p>}
      {context.base_role==="ADMIN" && <Link className="btn btn-secondary" to="/administration/assignments">Phân công thêm người quản lý biểu mẫu</Link>}

      {manage && <details><summary>Bổ sung các mẫu có sẵn còn thiếu</summary><p>Chỉ thêm những mã mẫu chưa có trong đợt từ bộ mẫu nguồn của Khoa. Tệp quét sạch được phát hành cho đúng đối tượng. Không đặt lại kho và không thay thế các mẫu đã được cập nhật; muốn thay tệp, chọn Cập nhật tệp trên dòng tương ứng.</p><button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void run(async()=>{const total={created:0,published:0,drafts:0,missing:[] as string[]};
          let remaining=1;while(remaining>0){const result=await request<typeof total & {remaining:number}>(`/school-forms/bootstrap/${roundId}`,context.user_id,{method:"POST"});total.created+=result.created;total.published+=result.published;total.drafts+=result.drafts;total.missing=Array.from(new Set([...total.missing,...result.missing]));remaining=result.remaining;setBootstrapInfo({...total});}},"Đã khởi tạo bộ mẫu nguồn; kiểm tra trạng thái từng tệp.")}>Bổ sung mẫu còn thiếu</button></details>}
    </div></div>
    {bootstrapInfo && <p role="status" className="alert alert-info">Khởi tạo {bootstrapInfo.created} danh mục: {bootstrapInfo.published} bản phát hành, {bootstrapInfo.drafts} bản nháp. {bootstrapInfo.missing.length>0 && `Thiếu tệp nguồn: ${bootstrapInfo.missing.join(", ")}`}</p>}
    {error && <p role="alert" className="alert alert-danger">{error}</p>}{notice && <p role="status" className="alert alert-success">{notice}</p>}
    {manage && <details className="card"><summary style={{padding:20,fontWeight:600}}><FilePlus2 size={17}/>Thêm biểu mẫu hoặc tài liệu công bố</summary><div className="card-body"><form className="core-form" onSubmit={async event=>{
      event.preventDefault();if(await run(()=>request("/school-forms",context.user_id,{method:"POST",body:JSON.stringify({round_id:roundId,code,title,document_kind:kind,audience,reason})}),"Đã tạo danh mục; chọn tệp để lưu phiên bản đầu.")){setCode("");setTitle("");setReason("");}
    }}><label>Mã tài liệu<input className="input" required pattern="[a-z0-9][a-z0-9_-]{1,49}" value={code} placeholder="Ví dụ: ds-sv-thuc-hien" onChange={event=>{setCode(event.target.value);if(/^mau-(06|07|08|09|10|11)$/.test(event.target.value))setAudience("LECTURER");}}/></label>
      <label>Tên tài liệu<input className="input" required minLength={3} maxLength={255} value={title} onChange={event=>setTitle(event.target.value)}/></label>
      <label htmlFor="catalog-kind">Phân loại</label><select id="catalog-kind" className="input" value={kind} onChange={event=>setKind(event.target.value)}><option value="FORM">Biểu mẫu trắng / hướng dẫn</option><option value="PUBLICATION">Tài liệu công bố theo đợt (ví dụ Mẫu 4 đã điền)</option></select>
      <label>Cho ai xem<select className="input" value={audience} onChange={event=>setAudience(event.target.value)}><option value="STUDENT_AND_LECTURER">Sinh viên và giảng viên</option><option value="LECTURER">Chỉ giảng viên</option></select></label><small>Mẫu 6–11 chỉ dành cho GV. Danh sách đã điền phải chọn Tài liệu công bố theo đợt.</small>
      <label>Lý do tạo danh mục<textarea className="input" required minLength={5} maxLength={2000} value={reason} onChange={event=>setReason(event.target.value)}/></label>
      <button className="btn btn-primary" disabled={busy || !roundId || reason.trim().length<5}><BookOpen size={16}/>Tạo danh mục</button>
    </form></div></details>}
    {loading?<p role="status">Đang tải tài liệu Khoa…</p>:displayed.length===0?<p>Chưa có tài liệu trong phạm vi này.</p>:<><div className="table-container" role="region" aria-label="Danh mục biểu mẫu Khoa" tabIndex={0}><table className="table"><thead><tr><th>Mã / tên biểu mẫu</th><th>Loại</th><th>Đối tượng</th><th>Bản đang áp dụng</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{displayed.map(item=>{const published=item.versions.find(v=>v.state==="PUBLISHED");return <tr key={item.id}><td><strong>{item.title}</strong><div className="text-caption">{item.code}</div></td><td>{item.document_kind==="FORM"?"Biểu mẫu":"Tài liệu công bố"}</td><td>{item.audience==="LECTURER"?"Giảng viên":"SV và GV"}</td><td>{published?`v${published.version_no} · ${formatDate(published.published_at || published.uploaded_at)}`:"Chưa phát hành"}</td><td>{item.state==="ACTIVE"?"Đang sử dụng":"Đã ẩn / ngừng sử dụng"}</td><td className="school-form-actions-cell"><div className="school-form-actions">{published && <>
<button type="button" className="btn btn-secondary school-form-action-button" title="Xem trực tiếp bản đang áp dụng" aria-label="Xem trực tiếp" disabled={busy || published.scan_state!=="CLEAN"} onClick={()=>setPreview({item,version:published})}><Eye size={17}/></button>
<button type="button" className="btn btn-secondary school-form-action-button" title="Tải xuống bản đang áp dụng" aria-label="Tải xuống" disabled={busy || published.scan_state!=="CLEAN"} onClick={()=>void downloadPublished(item,published)}><Download size={17}/></button></>}{manage && <>
<button type="button" className="btn btn-secondary school-form-action-button" title="Tải tệp mới thành một phiên bản nháp" aria-label="Cập nhật tệp" disabled={busy || item.state!=="ACTIVE"} onClick={()=>{setSelectedId(item.id);setSelectedAction("upload");}}><Upload size={17}/></button>
<button type="button" className="btn btn-secondary school-form-action-button" title={item.state==="ACTIVE"?"Ẩn khỏi kho SV/GV, vẫn giữ tệp và lịch sử":"Khôi phục biểu mẫu đã ẩn"} aria-label={item.state==="ACTIVE"?"Gỡ khỏi kho":"Khôi phục"} disabled={busy} onClick={()=>{setSelectedId(item.id);setSelectedAction("visibility");}}>{item.state==="ACTIVE"?<Archive size={17}/>:<RotateCcw size={17}/>}</button></>}
<button type="button" className="btn btn-secondary school-form-action-button" title="Xem bản nháp và lịch sử; mở từng bản để xem hoặc tải xuống" aria-label={selectedId===item.id && selectedAction==="versions"?"Thu gọn lịch sử phiên bản":"Lịch sử phiên bản"} aria-expanded={selectedId===item.id && selectedAction==="versions"} onClick={()=>{setSelectedId(selectedId===item.id && selectedAction==="versions"?null:item.id);setSelectedAction("versions");}}><History size={17}/></button>
</div></td></tr>;})}</tbody></table></div>{displayed.filter(item=>item.id===selectedId).map(item=><FormCard key={item.id} item={item} userId={context.user_id} manage={manage} action={selectedAction} busy={busy} run={run} onPreview={version=>setPreview({item,version})}/>)}</>}
    </div>{preview && <Preview item={preview.item} version={preview.version} userId={context.user_id} onClose={()=>setPreview(null)}/>}</>;
}
