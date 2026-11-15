import {useCallback, useEffect, useState} from "react";
import {downloadFile, request} from "../../api";
import {errorMessage} from "../../errors";
import {when} from "../../evaluation";

type Print = {id:string;form:number;filename:string;created_at:string;actor:string;code:string;course_code:string|null};

export default function DefensePrintHistory({endpoint, revision}: {endpoint:string;revision:number}) {
  const [open,setOpen] = useState(false);
  const [rows,setRows] = useState<Print[]>([]);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
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
    {error&&<p role="alert" className="alert alert-danger">{error} <button type="button" className="btn btn-secondary" onClick={()=>void load()}>Thử lại</button></p>}
    {busy&&<p role="status">Đang tải lịch sử bản in…</p>}
    {!busy&&!error&&!rows.length&&<p>Chưa có bản in được lưu từ chức năng xuất để ký.</p>}
    {!!rows.length&&<ul className="defense-print-list">{rows.map(row=><li key={row.id}>
      <div><strong>Mẫu {row.form} · {row.code}</strong>{row.course_code&&<span> · {row.course_code}</span>}
        <div className="text-muted text-body-sm">{when(row.created_at)} · {row.actor}</div><small>{row.filename}</small></div>
      <button type="button" className="btn btn-secondary" onClick={()=>void downloadFile(`/defense/prints/${row.id}`,row.filename).catch(cause=>setError(errorMessage(cause)))}>Tải lại bản đã lưu</button>
    </li>)}</ul>}
  </details>;
}
