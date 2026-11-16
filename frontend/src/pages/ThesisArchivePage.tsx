import {useCallback, useEffect, useState, type FormEvent} from "react";
import {Link, useSearchParams} from "react-router-dom";
import {downloadFile,request,type Context} from "../api";
import {errorMessage} from "../errors";
import {when} from "../evaluation";
import PageHeader from "../components/layout/PageHeader";
import "../styles/defense.css";

type Version = {id:string;number:number;revision:number;state:"SUBMITTED"|"ACCEPTED"|"RETURNED";filename:string;created_at:string;decided_at:string|null;decided_by:string|null;decision_note:string|null};
type Entry = {id:string;title:string;round_id:string;round:string;department:string;waiting:boolean;can_submit:boolean;can_decide:boolean;
  snapshot:{title:string;advisor:string;students:{name:string;code:string}[]}|null;versions:Version[];blockers?:{message:string;url:string}[]};
const versionLabels = {SUBMITTED:"Chờ bộ môn duyệt",ACCEPTED:"Đã duyệt lưu",RETURNED:"Cần nộp lại"};

export default function ThesisArchivePage({context}: {context:Context}) {
  const [params] = useSearchParams();
  const focus = params.get("focus");
  const [items,setItems] = useState<Entry[]|null>(null);
  const [round,setRound] = useState("");
  const [department,setDepartment] = useState("");
  const [state,setState] = useState("");
  const [search,setSearch] = useState("");
  const [limit,setLimit] = useState(20);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [message,setMessage] = useState("");
  const load = useCallback(async (signal?:AbortSignal) => {
    const data = await request<Entry[]>("/thesis-archive",context.user_id,{signal});
    if(!signal?.aborted)setItems(data);
  },[context.user_id]);
  useEffect(()=>{
    const controller = new AbortController();
    void load(controller.signal).catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));});
    return ()=>controller.abort();
  },[load]);
  useEffect(()=>{if(items&&focus)document.getElementById(`archive-${focus}`)?.scrollIntoView({block:"start"});},[items,focus]);

  async function action(work:()=>Promise<unknown>,notice:string) {
    if(busy)return;
    setBusy(true);setError("");setMessage("");
    try {
      await work();setMessage(notice);
      try {await load();} catch {setError("Thao tác đã lưu. Bấm Làm mới để xem trạng thái mới.");}
    }
    catch (cause) {setError(errorMessage(cause));return;}
    finally {setBusy(false);}
  }
  function submit(event:FormEvent<HTMLFormElement>, item:Entry) {
    event.preventDefault();
    const file = new FormData(event.currentTarget).get("file");
    if(!(file instanceof File)||!file.size||file.size>10*1024*1024||!/\.(pdf|docx)$/i.test(file.name)){
      setError("Chọn tệp PDF hoặc DOCX có dung lượng từ 1 byte đến 10 MB.");return;
    }
    void action(()=>request(`/thesis-archive/theses/${item.id}`,context.user_id,{method:"POST",body:file,
      headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(file.name)}}),"Đã nộp bản hoàn thiện. Bộ môn sẽ duyệt lưu và gửi thông báo.");
  }
  function decide(event:FormEvent<HTMLFormElement>, version:Version) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const decision = form.get("decision");
    void action(()=>request(`/thesis-archive/versions/${version.id}/decision`,context.user_id,{method:"POST",
      headers:{"If-Match":String(version.revision)},body:JSON.stringify({decision,reason:form.get("reason")})}),
      decision==="ACCEPTED"?"Đã duyệt lưu trong kho nội bộ.":"Đã gửi yêu cầu nộp lại cho nhóm sinh viên.");
  }
  const rounds = new Map(items?.map(row=>[row.round_id,row.round]));
  const departments = [...new Set(items?.filter(row=>!round||row.round_id===round).map(row=>row.department))];
  const visible = items?.filter(row=>(!round||row.round_id===round)&&(!department||row.department===department)&&(!state||(row.versions[0]?.state??"EMPTY")===state)&&
    `${row.title} ${row.snapshot?.advisor??""} ${row.snapshot?.students.map(student=>`${student.name} ${student.code}`).join(" ")??""}`.toLocaleLowerCase("vi").includes(search.trim().toLocaleLowerCase("vi")))??[];

  return <div className="stack defense-page">
    <PageHeader title="Kho khóa luận nội bộ" description="Tra cứu bản khóa luận sau bảo vệ và theo dõi hồ sơ nộp lưu trong phạm vi của bạn.">
      <button className="btn btn-secondary" disabled={busy} onClick={()=>{setError("");void load().catch(cause=>setError(errorMessage(cause)));}}>Làm mới</button>
    </PageHeader>
    {error&&<p className="alert alert-danger defense-notice" role="alert">{error}</p>}
    {message&&<p className="alert alert-success defense-notice" role="status">{message}</p>}
    {!items&&!error&&<p role="status">Đang tải hồ sơ lưu trữ…</p>}
    {items?.length===0&&<p>Chưa có khóa luận đã bảo vệ trong phạm vi của bạn.</p>}
    {!!items?.length&&<>
      <div className="defense-form-grid archive-filters">
        <label>Đợt KLTN<select className="input" value={round} onChange={e=>{setRound(e.target.value);setDepartment("");setLimit(20);}}><option value="">Tất cả đợt</option>{Array.from(rounds,([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
        <label>Bộ môn<select className="input" value={department} onChange={e=>{setDepartment(e.target.value);setLimit(20);}}><option value="">Tất cả bộ môn</option>{departments.map(value=><option key={value}>{value}</option>)}</select></label>
        <label>Trạng thái<select className="input" value={state} onChange={e=>{setState(e.target.value);setLimit(20);}}><option value="">Tất cả</option><option value="ACCEPTED">Đã duyệt lưu</option><option value="SUBMITTED">Chờ bộ môn duyệt</option><option value="RETURNED">Cần nộp lại</option><option value="EMPTY">Chưa nộp</option></select></label>
        <label>Tìm tên đề tài, sinh viên hoặc GVHD<input className="input" value={search} onChange={e=>{setSearch(e.target.value);setLimit(20);}}/></label>
      </div>
      <p>{visible.length} khóa luận trong phạm vi đang xem</p>
      {!visible.length&&<p>Không tìm thấy khóa luận phù hợp. Hãy đổi bộ lọc hoặc từ khóa.</p>}
      {visible.slice(0,limit).map(item=>{
        const latest = item.versions[0];
        return <details id={`archive-${item.id}`} key={item.id} className="defense-operation" open={focus===item.id||visible.length===1}>
          <summary>{item.snapshot?.title??item.title} · {latest?versionLabels[latest.state]:item.waiting?"Chờ chốt bảo vệ":"Chưa nộp"}</summary>
          <div className="stack">
            <p>{item.round} · {item.department}</p>
            {item.snapshot&&<><p>GVHD: {item.snapshot.advisor||"Chưa ghi nhận"}</p><p>Sinh viên: {item.snapshot.students.map(s=>`${s.name} (${s.code})`).join(", ")}</p></>}
            <Link to={`/theses/${item.id}`}>Mở hồ sơ khóa luận</Link>
            {item.waiting&&<p>Chờ kết quả của tất cả thành viên và khóa bảng điểm hội đồng.</p>}
            {!!item.blockers?.length&&<ul>{item.blockers.map((blocker,i)=><li key={i}>{blocker.message} · <Link to={blocker.url}>Mở hồ sơ đối chiếu</Link></li>)}</ul>}
            {!item.waiting&&!latest&&!item.can_submit&&<p className="text-muted">Nhóm sinh viên cần nộp bản hoàn thiện sau bảo vệ. TBM sẽ duyệt khi nhóm gửi hồ sơ.</p>}
            {item.versions.map(version=><section key={version.id} className="defense-operation stack">
              <strong>Phiên bản {version.number} · {versionLabels[version.state]}</strong>
              <span className="text-muted">{version.filename} · {when(version.created_at)}</span>
              {version.decided_by&&<p>{version.decided_by} · {when(version.decided_at)}<br/>{version.decision_note}</p>}
              <button type="button" className="btn btn-secondary" onClick={()=>void downloadFile(`/thesis-archive/versions/${version.id}/file`,version.filename).catch(cause=>setError(errorMessage(cause)))}>Tải phiên bản {version.number}</button>
            </section>)}
            {item.can_submit&&<form className="stack" key={latest?.id??"first"} onSubmit={event=>submit(event,item)}>
              <label>Bản khóa luận hoàn thiện sau bảo vệ (PDF/DOCX, tối đa 10 MB)<input required className="input" type="file" name="file" accept=".pdf,.docx" disabled={busy}/></label>
              <button className="btn btn-primary" disabled={busy}>{busy?"Đang xử lý…":"Nộp bản hoàn thiện"}</button>
            </form>}
            {item.can_decide&&latest&&<form className="stack" onSubmit={event=>decide(event,latest)}>
              <label>Kết quả kiểm tra<select className="input" name="decision" required defaultValue=""><option value="">Chọn kết quả</option><option value="ACCEPTED">Duyệt lưu nội bộ</option><option value="RETURNED">Yêu cầu nộp lại</option></select></label>
              <label>Nhận xét và căn cứ<textarea className="input" name="reason" required minLength={5} maxLength={2000} rows={3}/></label>
              <button className="btn btn-primary" disabled={busy}>{busy?"Đang xử lý…":"Lưu quyết định"}</button>
            </form>}
          </div>
        </details>;
      })}
      {visible.length>limit&&<button className="btn btn-secondary" onClick={()=>setLimit(value=>value+20)}>Xem thêm khóa luận</button>}
    </>}
  </div>;
}
