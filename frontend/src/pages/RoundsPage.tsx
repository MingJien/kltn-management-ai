import { useCallback, useEffect, useState } from "react";
import { CalendarPlus, CalendarRange, Check, Edit3, Lock, Plus, Unlock } from "lucide-react";
import type { Context } from "../api";
import { request } from "../api";
import { ApiError, errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";
import Dialog from "../components/ui/Dialog";
import EmptyState from "../components/ui/EmptyState";
import { SkeletonCard } from "../components/ui/Skeleton";
import { ActivityTimeline, inferTimelineTone } from "../components/ui/Timeline";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import "../styles/rounds.css";

type Round = {
  id: string; code: string; state: "DRAFT" | "OPEN" | "CLOSED" | "ARCHIVED";
  round_type: "MAIN" | "SUPPLEMENTARY"; academic_year_code: string;
  year_starts_on: string; year_ends_on: string;
  opens_at: string; closes_at: string; row_version: number;
};

function localDateTime(value: string) {
  return new Date(Date.parse(value) + 7 * 3600000).toISOString().slice(0, 16);
}

type HistoryRow={id:string;action:string;reason:string|null;reference:string|null;at:string;actor:string};
function RoundHistory({roundId,userId,version}:{roundId:string;userId:string;version:number}) {
  const [open,setOpen]=useState(false);
  const [rows,setRows]=useState<HistoryRow[]>();
  const [error,setError]=useState("");
  useEffect(()=>{
    if(!open)return;
    const controller=new AbortController();
    setError("");
    void request<HistoryRow[]>(`/admin/rounds/${roundId}/history`,userId,{signal:controller.signal})
      .then(setRows).catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));});
    return ()=>controller.abort();
  },[open,roundId,userId,version]);
  const labels:Record<string,string>={ROUND_CREATED:"Tạo đợt",ROUND_OPENED:"Mở đợt",ROUND_CLOSED:"Đóng đợt",
    ROUND_REGISTRATION_EXTENDED:"Gia hạn đăng ký",ROUND_REGISTRATION_REOPENED:"Gia hạn và mở lại",
    ROUND_SCHEDULE_UPDATED:"Sửa lịch bản nháp",WITHDRAWAL_START_RECORDED:"Thiết lập ngày bắt đầu thực hiện"};
  return <details className="round-history" open={open} onToggle={e=>setOpen(e.currentTarget.open)}>
    <summary>Lịch sử đợt</summary>
    {error&&<p role="alert">{error}</p>}
    {!rows&&!error&&<p role="status">Đang tải lịch sử…</p>}
    {rows&&<ActivityTimeline
      items={rows.map(row=>({
        id: row.id,
        title: labels[row.action]||"Cập nhật đợt",
        actor: row.actor,
        timestamp: new Date(row.at).toLocaleString("vi-VN",{timeZone:"Asia/Ho_Chi_Minh"}),
        badge: row.reference ? <span className="code-chip">{row.reference}</span> : undefined,
        note: row.reason || undefined,
        tone: inferTimelineTone(row.action),
      }))}
      ariaLabel="Lịch sử đợt KLTN"
    />}
  </details>;
}

export default function RoundsPage({context}: {context: Context}) {
  const [rounds, setRounds] = useState<Round[]>([]);
  const [loading, setLoading] = useState(true);
  const [yearCode, setYearCode] = useState("");
  const [yearStart, setYearStart] = useState("");
  const [yearEnd, setYearEnd] = useState("");
  const [code, setCode] = useState("");
  const [roundType, setRoundType] = useState<"MAIN" | "SUPPLEMENTARY">("MAIN");
  const [opensAt, setOpensAt] = useState("");
  const [closesAt, setClosesAt] = useState("");
  const [basis, setBasis] = useState("");
  const [editing, setEditing] = useState<Round | null>(null);
  const [target, setTarget] = useState<{round: Round; state: "OPEN" | "CLOSED"} | null>(null);
  const [reason, setReason] = useState("");
  const [extension, setExtension] = useState<Round | null>(null);
  const [newDeadline, setNewDeadline] = useState("");
  const [extensionBasis, setExtensionBasis] = useState("");
  const [extensionReason, setExtensionReason] = useState("");
  const [reopen,setReopen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const reload = useCallback(async () => {
    setRounds(await request<Round[]>("/admin/rounds", context.user_id));
  }, [context.user_id]);
  useEffect(() => {
    setLoading(true);
    void reload()
      .catch(cause => setError(errorMessage(cause)))
      .finally(() => setLoading(false));
  }, [reload]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const schedule = {code: code.trim(), round_type: roundType,
        opens_at: new Date(opensAt+"+07:00").toISOString(), closes_at: new Date(closesAt+"+07:00").toISOString()};
      if (editing) {
        await request(`/admin/rounds/${editing.id}/schedule`, context.user_id, {
          method: "PATCH", headers: {"If-Match": String(editing.row_version)},
          body: JSON.stringify({...schedule, reason: basis.trim()}),
        });
      } else {
        await request("/admin/rounds", context.user_id, {method: "POST", body: JSON.stringify({
          academic_year_code: yearCode.trim(), year_starts_on: yearStart, year_ends_on: yearEnd,
          ...schedule, basis_ref: basis.trim(),
        })});
      }
      await reload();
      setEditing(null);
      setCode(""); setOpensAt(""); setClosesAt(""); setBasis("");
      setNotice(editing ? "Đã cập nhật bản nháp. Kiểm lại thời hạn trước khi mở." :
        "Đã tạo đợt ở trạng thái bản nháp. Kiểm lại thời hạn trước khi mở.");
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }

  async function changeState() {
    if (!target || busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await request(`/admin/rounds/${target.round.id}`, context.user_id, {
        method: "PATCH", headers: {"If-Match": String(target.round.row_version)},
        body: JSON.stringify({state: target.state, reason: reason.trim()}),
      });
      await reload();
      setNotice(target.state === "OPEN" ? "Đã mở đợt. Đăng ký chỉ nhận trong thời hạn đã đặt." : "Đã đóng đợt đăng ký.");
      setTarget(null); setReason("");
    } catch (cause) { setError(errorMessage(cause)); await reload().catch(() => undefined); }
    finally { setBusy(false); }
  }

  async function extendRegistration(event: React.FormEvent) {
    event.preventDefault();
    if (!extension || busy || !newDeadline) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await request("/admin/rounds/"+extension.id+"/extend", context.user_id, {
        method:"POST", headers:{"If-Match":String(extension.row_version)},
        body:JSON.stringify({closes_at:new Date(newDeadline+"+07:00").toISOString(),
          basis_ref:extensionBasis.trim(),reason:extensionReason.trim(),reopen_closed:reopen}),
      });
      await reload();
      setExtension(null); setNewDeadline(""); setExtensionBasis(""); setExtensionReason("");
      setNotice("Đã gia hạn thời gian đăng ký và thông báo trên hệ thống.");
    } catch (cause) {
      setError(errorMessage(cause));
      if (cause instanceof ApiError && cause.status === 409) {
        setExtension(null);
        await reload().catch(() => undefined);
      }
    } finally { setBusy(false); }
  }

  return <><PageHeader title="Quản lý đợt KLTN" description="Tạo năm học và đợt đăng ký; kiểm thời hạn trước khi mở" />
    <div className="stack">
      {error ? <p role="alert" className="alert alert-danger">{error}</p> : null}
      {notice ? <p role="status" className="alert alert-success">{notice}</p> : null}
      <section className="card"><div className="card-body stack"><h2>Các đợt đã tạo</h2>
        {loading ? <div className="stack" role="status" aria-label="Đang tải danh sách đợt"><SkeletonCard /></div>
          : !rounds.length ? <EmptyState icon={<CalendarRange aria-hidden="true" />} title="Chưa có đợt nào" description="Tạo đợt KLTN đầu tiên bằng biểu mẫu bên dưới." />
          : <div className="account-list">{rounds.map(row => <div className="account-list__row" key={row.id}>
          <div><div className="flex flex-wrap items-center gap-2"><strong>{row.academic_year_code} · {row.code}</strong>
            <ThesisStatusBadge state={row.state} label={row.state === "DRAFT" ? "Bản nháp" : row.state === "OPEN" ? "Đã mở" : row.state === "CLOSED" ? "Đã đóng" : "Lưu trữ"} /></div>
            <span className="text-body-sm text-muted">{row.round_type === "MAIN" ? "Đợt chính" : "Đợt bổ sung"}</span><br />
            <span className="text-caption">{new Date(row.opens_at).toLocaleString("vi-VN",{timeZone:"Asia/Ho_Chi_Minh"})} – {new Date(row.closes_at).toLocaleString("vi-VN",{timeZone:"Asia/Ho_Chi_Minh"})}</span>
          </div>
          <div className="rounds-row-actions">{row.state === "DRAFT" ? <button className="btn btn-secondary btn-sm" disabled={busy}
            onClick={() => {
              setEditing(row); setYearCode(row.academic_year_code); setYearStart(row.year_starts_on);
              setYearEnd(row.year_ends_on); setCode(row.code); setRoundType(row.round_type);
              setOpensAt(localDateTime(row.opens_at)); setClosesAt(localDateTime(row.closes_at));
              setBasis(""); setError(""); document.getElementById("round-editor")?.scrollIntoView({block: "start", behavior: "smooth"});
            }}><Edit3 size={14} aria-hidden="true" />Sửa bản nháp</button> : null}
          {["OPEN","CLOSED"].includes(row.state) && <button className="btn btn-secondary btn-sm" disabled={busy}
            onClick={()=>{setExtension(row);setNewDeadline("");setExtensionBasis("");setExtensionReason("");setReopen(false);setError("");}}><CalendarPlus size={14} aria-hidden="true" />{row.state==="CLOSED"?"Gia hạn và mở lại":"Gia hạn đăng ký"}</button>}
          <RoundHistory roundId={row.id} userId={context.user_id} version={row.row_version}/>
          {row.state === "DRAFT" || row.state === "OPEN" ? <button className="btn btn-secondary btn-sm" disabled={busy}
            onClick={() => {setTarget({round: row, state: row.state === "DRAFT" ? "OPEN" : "CLOSED"}); setReason(""); setError("");}}>
            {row.state === "DRAFT" ? <><Unlock size={14} aria-hidden="true" />Mở đợt</> : <><Lock size={14} aria-hidden="true" />Đóng đợt</>}</button> : null}</div>
        </div>)}</div>}
      </div></section>
      <section className="card" id="round-editor"><div className="card-body stack"><h2>{editing ? "Sửa bản nháp " + editing.code : "Tạo đợt mới"}</h2>
        <form className="stack" onSubmit={event => void create(event)}>
          <div className="grid grid-auto">
            <label className="input-group">Năm học (ví dụ 2026-2027)
              <input className="input" required disabled={!!editing} pattern="[0-9]{4}-[0-9]{4}" value={yearCode} onChange={e => setYearCode(e.target.value)} /></label>
            <label className="input-group">Ngày bắt đầu năm học
              <input className="input" type="date" required disabled={!!editing} value={yearStart} onChange={e => setYearStart(e.target.value)} /></label>
            <label className="input-group">Ngày kết thúc năm học
              <input className="input" type="date" required disabled={!!editing} value={yearEnd} onChange={e => setYearEnd(e.target.value)} /></label>
          </div>
          <div className="rounds-form-grid">
            <label className="input-group rounds-form-grid__full">Mã đợt
              <input className="input" required maxLength={32} placeholder="KLTN-26-27-D01" value={code} onChange={e => setCode(e.target.value)} /></label>
            <label className="input-group">Loại đợt
              <select className="input" value={roundType} onChange={e => setRoundType(e.target.value as typeof roundType)}>
                <option value="MAIN">Đợt chính</option><option value="SUPPLEMENTARY">Đợt bổ sung</option>
              </select></label>
            <label className="input-group">{editing ? "Lý do sửa lịch" : "Căn cứ lịch đợt"}
              <input className="input" required minLength={3} maxLength={500} value={basis} onChange={e => setBasis(e.target.value)}
                placeholder="Kế hoạch hoặc thông báo của Khoa" /></label>
            <label className="input-group">Mở đăng ký lúc (giờ Việt Nam)
              <input className="input" type="datetime-local" required value={opensAt} onChange={e => setOpensAt(e.target.value)} /></label>
            <label className="input-group">Đóng đăng ký lúc (giờ Việt Nam)
              <input className="input" type="datetime-local" required min={opensAt || undefined} value={closesAt} onChange={e => setClosesAt(e.target.value)} /></label>
          </div>
          <div className="flex gap-2"><button className="btn btn-primary" disabled={busy || (!!opensAt && !!closesAt && closesAt <= opensAt)}>
            {editing ? <Check size={15} aria-hidden="true" /> : <Plus size={15} aria-hidden="true" />}
            {busy ? "Đang lưu…" : editing ? "Lưu bản nháp" : "Tạo bản nháp"}</button>
            {editing ? <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => {
              setEditing(null); setCode(""); setOpensAt(""); setClosesAt(""); setBasis("");
            }}>Hủy sửa</button> : null}</div>
        </form>
      </div></section>
    </div>
    <Dialog open={!!extension} onClose={()=>{setExtension(null);setError("");}} busy={busy} title="Gia hạn thời gian đăng ký"
      footer={<><button className="btn btn-secondary" type="button" disabled={busy} onClick={()=>{setExtension(null);setError("");}}>Quay lại</button>
        <button className="btn btn-primary" form="round-extension-form" type="submit" disabled={busy || !newDeadline || extensionBasis.trim().length<3 || extensionReason.trim().length<5 || (extension?.state==="CLOSED"&&!reopen)}>Xác nhận gia hạn</button></>}>
      <form id="round-extension-form" className="round-extension-form" onSubmit={event=>void extendRegistration(event)}>
        <p><strong>{extension?.academic_year_code} · {extension?.code}</strong><br/>Hạn hiện tại: {extension && new Date(extension.closes_at).toLocaleString("vi-VN",{timeZone:"Asia/Ho_Chi_Minh"})}</p>
        <p className="text-caption">Gia hạn thời gian đăng ký cho cả đợt. Hạn tiến độ và tài liệu được quản lý riêng. Nếu đợt vẫn mở nhưng đã quá hạn, đăng ký được nhận lại đến hạn mới.</p>
        <label className="input-group">Hạn đăng ký mới (giờ Việt Nam)
          <input className="input" type="datetime-local" required min={extension?localDateTime(extension.closes_at):undefined} value={newDeadline} onChange={e=>setNewDeadline(e.target.value)}/></label>
        {extension?.state==="CLOSED"&&<label className="round-reopen-confirm"><input type="checkbox" required checked={reopen} onChange={e=>setReopen(e.target.checked)}/> Tôi xác nhận mở nhận đăng ký trở lại đến hạn mới.</label>}
        <label className="input-group">Căn cứ / số văn bản
          <input className="input" required minLength={3} maxLength={500} value={extensionBasis} onChange={e=>setExtensionBasis(e.target.value)}/></label>
        <label className="input-group">Lý do gia hạn
          <textarea className="input" required minLength={5} maxLength={1000} rows={2} value={extensionReason} onChange={e=>setExtensionReason(e.target.value)}/></label>
        {error && <p role="alert" className="alert alert-danger">{error}</p>}
      </form>
    </Dialog>
    <Dialog open={!!target} onClose={() => setTarget(null)} busy={busy}
      title={target?.state === "OPEN" ? "Xác nhận mở đợt" : "Xác nhận đóng đợt"}
      footer={<><button className="btn btn-secondary" disabled={busy} onClick={() => setTarget(null)}>Quay lại</button>
        <button className="btn btn-primary" disabled={busy || reason.trim().length < 3} onClick={() => void changeState()}>
          {target?.state === "OPEN" ? "Mở đợt" : "Đóng đợt"}</button></>}>
      <p>{target?.round.academic_year_code} · {target?.round.code}</p>
      <p className="text-caption">{target?.state === "OPEN" ? "Sau khi mở, GV và SV chỉ tạo hoặc gửi hồ sơ trong thời hạn đăng ký." : "Sau khi đóng, không thể tạo hoặc gửi đăng ký mới. Hồ sơ đã gửi vẫn được xét."}</p>
      <label className="input-group">Lý do / căn cứ
        <input className="input" required minLength={3} maxLength={500} value={reason} onChange={e => setReason(e.target.value)} /></label>
      {error ? <p role="alert" className="alert alert-danger">{error}</p> : null}
    </Dialog>
  </>;
}
