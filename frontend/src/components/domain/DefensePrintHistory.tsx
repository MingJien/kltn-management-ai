import {useCallback, useEffect, useState} from "react";
import {downloadFile, request} from "../../api";
import {errorMessage} from "../../errors";
import {when} from "../../evaluation";

type Print = {id:string;form:number;filename:string;created_at:string;actor:string;code:string;course_code:string|null;current?:boolean;pending_correction?:boolean;superseded_by?:string|null;withdrawn_reason?:string|null;can_withdraw?:boolean;print_number?:number};

export default function DefensePrintHistory({endpoint, revision}: {endpoint:string;revision:number}) {
  const [open,setOpen] = useState(false);
  const [rows,setRows] = useState<Print[]>([]);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [query,setQuery]=useState(''),[found,setFound]=useState<Print|null>(null);
  const load = useCallback(async (signal?:AbortSignal) => {
    setBusy(true);
    setError("");
    try {setRows(await request<Print[]>(endpoint,"",{signal}));}
    catch (cause) {if (!signal?.aborted) setError(errorMessage(cause));}
    finally {if (!signal?.aborted) setBusy(false);}
  },[endpoint]);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  },[load,open,revision]);
  return <details className="defense-operation" onToggle={event=>setOpen(event.currentTarget.open)}>
    <summary>Bản in đã lưu</summary>
    <p>Khi lưu bản mới cùng loại phiếu/hồ sơ, hệ thống tự đánh dấu bản trước đã được thay thế. Dùng mã tra cứu 12 ký tự trên footer để đối chiếu.</p>
    <div className="button-row"><label>Mã tra cứu bản in<input className="input" value={query} onChange={e=>{setQuery(e.target.value);setFound(null);}} maxLength={12}/></label><button type="button" className="btn btn-secondary" onClick={()=>{setError('');request<Print>('/defense/print-lookup/'+encodeURIComponent(query.trim()),'').then(setFound).catch(e=>setError(errorMessage(e)));}}>Tra cứu mã trên footer</button></div>
    {error&&<p role="alert" className="alert alert-danger">{error} <button type="button" className="btn btn-secondary" onClick={()=>void load()}>Thử lại</button></p>}
    {busy&&<p role="status">Đang tải lịch sử bản in…</p>}
    {!busy&&!error&&!rows.length&&<p>Chưa có bản in được lưu từ chức năng xuất để ký.</p>}
    {!!(found?[found]:rows).length&&<ul className="defense-print-list">{(found?[found]:rows).map(row=><li key={row.id}>
      <div><strong>Mẫu {row.form} · {row.code}{row.print_number?` · Bản ${row.print_number}`:''}</strong>{row.course_code&&<span> · {row.course_code}</span>}
        <p>{row.superseded_by?`Đã hết hiệu lực — được thay bằng bản ${row.superseded_by}.`:row.withdrawn_reason?`Đã thu hồi: ${row.withdrawn_reason}`:row.current===false?'Bản lịch sử — hồ sơ đã thay đổi. Xem trước và xuất bản mới để ký.':'Bản hiện hành khớp hồ sơ tại lần đối chiếu này.'}</p>
        {row.pending_correction&&<p>Có đề nghị đính chính đang chờ. Cần giải quyết trước khi phát hành bản mới.</p>}
        <div className="text-muted text-body-sm">{when(row.created_at)} · {row.actor}</div><small>{row.filename}</small></div>
      <div className="button-row"><button type="button" className="btn btn-secondary" onClick={()=>void downloadFile(`/defense/prints/${row.id}`,row.filename).catch(cause=>setError(errorMessage(cause)))}>Tải lại bản đã lưu</button>
      {row.current&&row.can_withdraw&&<button type="button" className="btn btn-secondary" onClick={async()=>{const reason=window.prompt('Lý do thu hồi bản này (ít nhất 5 ký tự). Tệp cũ vẫn giữ trong lịch sử:');if(reason===null)return;if(reason.trim().length<5){setError('Cần ghi rõ lý do thu hồi.');return;}try{await request(`/defense/prints/${row.id}/withdraw`,'',{method:'POST',body:JSON.stringify({reason})});setFound(null);await load();}catch(e){setError(errorMessage(e));}}}>Thu hồi bản dùng để ký</button>}</div>
    </li>)}</ul>}
  </details>;
}
