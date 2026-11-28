import {useCallback, useEffect, useState} from "react";
import {Download, RotateCcw, Search} from "lucide-react";
import {downloadFile, request} from "../../api";
import {errorMessage} from "../../errors";
import {when} from "../../evaluation";
import Dialog from "../ui/Dialog";
import Badge from "../ui/Badge";

type Print = {id:string;form:number;filename:string;created_at:string;actor:string;code:string;course_code:string|null;current?:boolean;pending_correction?:boolean;superseded_by?:string|null;withdrawn_reason?:string|null;can_withdraw?:boolean;print_number?:number};

export default function DefensePrintHistory({endpoint, revision}: {endpoint:string;revision:number}) {
  const [open,setOpen] = useState(false);
  const [rows,setRows] = useState<Print[]>([]);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [query,setQuery]=useState(''),[found,setFound]=useState<Print|null>(null);
  const [withdrawTarget,setWithdrawTarget]=useState<Print|null>(null);
  const [withdrawReason,setWithdrawReason]=useState("");
  const [withdrawBusy,setWithdrawBusy]=useState(false);
  const [withdrawError,setWithdrawError]=useState("");
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
  async function submitWithdraw() {
    if (!withdrawTarget || withdrawBusy) return;
    const trimmed = withdrawReason.trim();
    if (trimmed.length < 5) {
      setWithdrawError("Cần ghi rõ lý do thu hồi (ít nhất 5 ký tự).");
      return;
    }
    setWithdrawBusy(true);
    setWithdrawError("");
    try {
      await request(`/defense/prints/${withdrawTarget.id}/withdraw`, "", {
        method: "POST",
        body: JSON.stringify({ reason: trimmed }),
      });
      setWithdrawTarget(null);
      setWithdrawReason("");
      setFound(null);
      await load();
    } catch (e) {
      setWithdrawError(errorMessage(e));
    } finally {
      setWithdrawBusy(false);
    }
  }
  return <details className="defense-operation" onToggle={event=>setOpen(event.currentTarget.open)}>
    <summary>Bản in đã lưu</summary>
    <p>Khi lưu bản mới cùng loại phiếu/hồ sơ, hệ thống tự đánh dấu bản trước đã được thay thế. Dùng mã tra cứu 12 ký tự trên footer để đối chiếu.</p>
    <div className="button-row"><label>Mã tra cứu bản in<input className="input" value={query} onChange={e=>{setQuery(e.target.value);setFound(null);}} maxLength={12} placeholder="Ví dụ: A1B2C3D4E5F6"/></label><button type="button" className="btn btn-secondary" disabled={query.trim().length < 6} onClick={()=>{const code=query.trim();if(!/^[0-9a-f]{6,12}$/i.test(code)){setError("Mã tra cứu phải gồm ký tự hex hợp lệ.");return;}setError('');request<Print>('/defense/print-lookup/'+encodeURIComponent(code),'').then(setFound).catch(e=>setError(errorMessage(e)));}}><Search size={15} aria-hidden="true"/>Tra cứu mã trên footer</button></div>
    {error&&<p role="alert" className="alert alert-danger">{error} <button type="button" className="btn btn-secondary" onClick={()=>void load()}>Thử lại</button></p>}
    {busy&&<p role="status">Đang tải lịch sử bản in…</p>}
    {!busy&&!error&&!rows.length&&<p>Chưa có bản in được lưu từ chức năng xuất để ký.</p>}
    {!!(found?[found]:rows).length&&<ul className="defense-print-list">{(found?[found]:rows).map(row=><li key={row.id}>
      <div><div className="flex flex-wrap items-center gap-2"><strong>Mẫu {row.form} · {row.code}{row.print_number?` · Bản ${row.print_number}`:''}</strong>{row.course_code&&<span>· {row.course_code}</span>}<Badge variant={row.withdrawn_reason?"danger":row.superseded_by||row.current===false?"warning":"success"}>{row.withdrawn_reason?"Đã thu hồi":row.superseded_by?"Đã thay thế":row.current===false?"Cần xuất lại":"Bản hiện hành"}</Badge></div>
        <p>{row.superseded_by?`Đã hết hiệu lực — được thay bằng bản ${row.superseded_by}.`:row.withdrawn_reason?`Đã thu hồi: ${row.withdrawn_reason}`:row.current===false?'Bản lịch sử — hồ sơ đã thay đổi. Xem trước và xuất bản mới để ký.':'Bản hiện hành khớp hồ sơ tại lần đối chiếu này.'}</p>
        {row.pending_correction&&<p>Có đề nghị đính chính đang chờ. Cần giải quyết trước khi phát hành bản mới.</p>}
        <div className="text-muted text-body-sm">{when(row.created_at)} · {row.actor}</div><small>{row.filename}</small></div>
      <div className="button-row"><button type="button" className="btn btn-secondary" onClick={()=>void downloadFile(`/defense/prints/${row.id}`,row.filename).catch(cause=>setError(errorMessage(cause)))}><Download size={15} aria-hidden="true"/>Tải lại bản đã lưu</button>
      {row.current&&row.can_withdraw&&<button type="button" className="btn btn-danger btn-sm" onClick={()=>{setWithdrawTarget(row);setWithdrawReason("");setWithdrawError("");}}><RotateCcw size={14} aria-hidden="true"/>Thu hồi bản dùng để ký</button>}</div>
    </li>)}</ul>}
    <Dialog
      open={Boolean(withdrawTarget)}
      title="Thu hồi bản in dùng để ký"
      busy={withdrawBusy}
      onClose={()=>{if(!withdrawBusy){setWithdrawTarget(null);setWithdrawError("");}}}
      footer={<>
        <button type="button" className="btn btn-secondary" disabled={withdrawBusy} onClick={()=>setWithdrawTarget(null)}>Giữ nguyên</button>
        <button type="button" className="btn btn-danger" disabled={withdrawBusy || withdrawReason.trim().length < 5} onClick={()=>void submitWithdraw()}>Xác nhận thu hồi</button>
      </>}
    >
      <p>Tệp bản in cũ vẫn được lưu trong lịch sử đối chiếu nhưng sẽ bị đánh dấu đã thu hồi.</p>
      {withdrawError&&<p role="alert" className="alert alert-danger">{withdrawError}</p>}
      <div className="input-group">
        <label htmlFor="withdraw-print-reason">Lý do thu hồi (ít nhất 5 ký tự)</label>
        <textarea id="withdraw-print-reason" className="input" rows={3} maxLength={500} value={withdrawReason} onChange={e=>setWithdrawReason(e.target.value)} placeholder="Nêu rõ lý do cần thu hồi bản in này…"/>
      </div>
    </Dialog>
  </details>;
}
