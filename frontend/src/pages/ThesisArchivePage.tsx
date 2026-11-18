import {useEffect, useState, type FormEvent} from "react";
import {Link, useSearchParams} from "react-router-dom";
import {downloadFile, request, type Context} from "../api";
import {errorMessage} from "../errors";
import {when} from "../evaluation";
import {ReadOnlyFilePreview} from "../components/domain/ReviewAttachmentPreview";
import PageHeader from "../components/layout/PageHeader";
import "../styles/defense.css";
import "../styles/review-workspace.css";

type State = "SUBMITTED" | "ACCEPTED" | "RETURNED" | "REOPENED";
type Identity = {title:string; advisor:string; students:{name:string; code:string}[]};
type Version = {id:string; number:number; revision:number; state:State; filename:string; created_at:string;
  submitted_by:string; decided_at:string|null; decided_by:string|null; decision_note:string|null;
  reopened?: {by:string; at:string; reason:string}|null};
type Entry = {id:string; title:string; topic_code:string; round:string; department:string; waiting:boolean;
  can_submit:boolean; can_decide:boolean; can_approve:boolean; can_reopen:boolean;
  snapshot:Identity; versions:Version[]; blockers:{message:string; url:string}[]};
type Scope = {round_id:string; round:string; department_id:string; department:string};
type Result = {id:string; current_title:string; topic_code:string; round:string; department:string;
  state:State|null; version_no:number|null; snapshot:Identity|null; advisor:string|null; approved_at:string|null};
type Listing = {items:Result[]; total:number; page:number; limit:number; scopes:Scope[]};
const labels:Record<State,string> = {
  SUBMITTED:"Chờ bộ môn duyệt", ACCEPTED:"Đã duyệt lưu", RETURNED:"Cần nộp lại", REOPENED:"Đã thu hồi bản lưu",
};
const versionPath = (version: Version) => `/thesis-archive/versions/${version.id}`;

function ArchiveDetail({item, userId, refresh}: {item:Entry; userId:string; refresh:()=>void}) {
  const [preview,setPreview] = useState<Version|null>(null);
  const [reopen,setReopen] = useState(false);
  const [decision,setDecision] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [message,setMessage] = useState("");
  const latest = item.versions[0];
  const title = item.snapshot?.title || item.title;
  const status = latest ? labels[latest.state] : item.waiting ? "Chờ chốt bảo vệ" : "Chưa nộp";

  async function action(work:()=>Promise<unknown>, notice:string) {
    if (busy) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await work();
      setMessage(notice);
      setReopen(false);
      setDecision("");
      refresh();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = new FormData(event.currentTarget).get("file");
    if (!(file instanceof File) || !file.size || file.size > 10*1024*1024 || !/\.(pdf|docx)$/i.test(file.name)) {
      setError("Chọn tệp PDF hoặc DOCX có nội dung và dung lượng tối đa 10 MB.");
      return;
    }
    void action(() => request(`/thesis-archive/theses/${item.id}`,userId,{method:"POST",body:file,
      headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(file.name)}}),
      "Đã nộp bản hoàn thiện. Bộ môn sẽ duyệt lưu và gửi thông báo.");
  }

  function decide(event:FormEvent<HTMLFormElement>, reopening = false) {
    event.preventDefault();
    if (!latest) return;
    const reason = String(new FormData(event.currentTarget).get("reason") ?? "").trim();
    if (reason.length < 5) {
      setError("Nhập nhận xét hoặc căn cứ từ 5 ký tự.");
      return;
    }
    const body = reopening ? {reason} : {decision, reason};
    const notice = reopening ? "Đã thu hồi bản đã duyệt. Nhóm sinh viên có thể nộp bản thay thế."
      : decision === "ACCEPTED" ? "Đã duyệt lưu trong kho nội bộ." : "Đã gửi yêu cầu nộp lại cho nhóm sinh viên.";
    void action(() => request(versionPath(latest)+(reopening?"/reopen":"/decision"),userId,{method:"POST",
      headers:{"If-Match":String(latest.revision)},body:JSON.stringify(body)}),notice);
  }

  function versionCard(version:Version) {
    return <section key={version.id} className="defense-operation stack archive-version">
      <strong>Phiên bản {version.number} · {labels[version.state]}</strong>
      <span className="text-muted">{version.filename} · {when(version.created_at)}{version.submitted_by && ` · ${version.submitted_by}`}</span>
      {version.decided_by && <p>{version.decided_by} · {when(version.decided_at)}<br/>{version.decision_note}</p>}
      {version.reopened && <p className="alert alert-warning">Thu hồi bởi {version.reopened.by} · {when(version.reopened.at)}<br/>{version.reopened.reason}</p>}
      <div className="button-row">
        <button type="button" className="btn btn-secondary" onClick={()=>setPreview(version)}>Xem nhanh v{version.number}</button>
        <button type="button" className="btn btn-secondary" onClick={()=>void downloadFile(versionPath(version)+"/file",version.filename).catch(cause=>setError(errorMessage(cause)))}>Tải phiên bản {version.number}</button>
      </div>
      {preview?.id===version.id && <ReadOnlyFilePreview key={version.id} name={version.filename}
        endpoint={versionPath(version)+"/file"} label={`Xem nhanh bản khóa luận v${version.number}`}
        caption={`Phiên bản ${version.number} · ${labels[version.state]}`} onBack={()=>setPreview(null)} backLabel="Đóng bản xem"/>}
    </section>;
  }

  return <section className="card"><div className="card-body stack">
    <div className="archive-heading"><div><p className="text-muted">{[item.topic_code,item.round,item.department].filter(Boolean).join(" · ")}</p>
      <h2>{title}</h2></div><span className="archive-status" data-state={latest?.state??"EMPTY"}>{status}</span></div>
    <dl className="archive-facts"><div><dt>Giảng viên hướng dẫn</dt><dd>{item.snapshot?.advisor||"Chưa ghi nhận"}</dd></div>
      <div><dt>Sinh viên</dt><dd>{item.snapshot?.students.map(s=>`${s.name} (${s.code})`).join(", ")||"Chưa ghi nhận"}</dd></div></dl>
    <Link to={`/theses/${item.id}`}>Mở hồ sơ khóa luận</Link>
    {error && <p className="alert alert-danger" role="alert">{error}</p>}
    {message && <p className="alert alert-success" role="status">{message}</p>}
    {!!item.blockers?.length && <section className="defense-blockers"><strong>Việc cần đối chiếu trước khi duyệt lưu</strong>
      <ul>{item.blockers.map(blocker=><li key={blocker.message}>{blocker.message} · <Link to={blocker.url}>Mở hồ sơ</Link></li>)}</ul></section>}
    {!latest && !item.waiting && <p>Nhóm sinh viên nộp bản hoàn thiện sau bảo vệ. Bộ môn kiểm tra và quyết định lưu.</p>}
    {latest && versionCard(latest)}
    {item.can_submit && <form className="archive-action stack" key={latest?.id??"first"} onSubmit={submit}>
      <label>Bản khóa luận hoàn thiện sau bảo vệ (PDF/DOCX, tối đa 10 MB)<input required className="input" type="file" name="file" accept=".pdf,.docx" disabled={busy}/></label>
      <button className="btn btn-primary" disabled={busy}>{busy?"Đang tải và quét tệp…":latest?"Nộp bản thay thế":"Nộp bản hoàn thiện"}</button>
    </form>}
    {item.can_decide && latest && <form className="archive-action stack" key={latest.id} onSubmit={event=>decide(event)}>
      <label>Kết quả kiểm tra<select className="input" required value={decision} onChange={event=>setDecision(event.target.value)}>
        <option value="">Chọn kết quả</option><option value="ACCEPTED" disabled={item.can_approve===false}>Duyệt lưu nội bộ</option>
        <option value="RETURNED">Yêu cầu nộp lại</option></select></label>
      <label>Nhận xét và căn cứ<textarea className="input" name="reason" required minLength={5} maxLength={2000} rows={3}/></label>
      <button className="btn btn-primary" disabled={busy}>{busy?"Đang xử lý…":"Lưu quyết định"}</button>
    </form>}
    {item.can_reopen && latest && <details className="defense-operation" open={reopen} onToggle={event=>setReopen(event.currentTarget.open)}>
      <summary>Thu hồi bản lưu và yêu cầu nộp lại</summary>
      <form className="archive-action stack" onSubmit={event=>decide(event,true)}>
        <p>Bản này sẽ rời danh sách tra cứu. Tệp và quyết định duyệt cũ vẫn có trong lịch sử để đối chiếu.</p>
        <label>Lý do thu hồi<textarea className="input" name="reason" required minLength={5} maxLength={2000} rows={3}/></label>
        <label className="defense-check"><input type="checkbox" required/>Tôi đã đối chiếu đúng bản cần thu hồi.</label>
        <button className="btn btn-destructive" disabled={busy}>{busy?"Đang xử lý…":"Thu hồi và thông báo nhóm"}</button>
      </form>
    </details>}
    {item.versions.length>1 && <details className="defense-operation"><summary>Lịch sử bản nộp ({item.versions.length-1} bản trước)</summary>
      <div className="stack">{item.versions.slice(1).map(versionCard)}</div></details>}
  </div></section>;
}

export default function ThesisArchivePage({context}: {context:Context}) {
  const [params,setParams] = useSearchParams();
  const focus = params.get("focus");
  const mode = params.get("mode")==="work" ? "work" : "catalog";
  const [list,setList] = useState<Listing|null>(null);
  const [detail,setDetail] = useState<Entry|null>(null);
  const [round,setRound] = useState("");
  const [department,setDepartment] = useState("");
  const [state,setState] = useState("");
  const [search,setSearch] = useState("");
  const [debounced,setDebounced] = useState("");
  const [page,setPage] = useState(1);
  const [revision,setRevision] = useState(0);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState("");
  const refresh = () => setRevision(value=>value+1);

  useEffect(()=>{
    const timer = setTimeout(()=>setDebounced(search.trim()),220);
    return ()=>clearTimeout(timer);
  },[search]);

  useEffect(()=>{
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const query = new URLSearchParams({mode,page:String(page),q:debounced});
    if(round) query.set("round_id",round);
    if(department) query.set("department_id",department);
    if(mode==="work"&&state) query.set("state",state);
    const path = focus ? `/thesis-archive/theses/${encodeURIComponent(focus)}` : `/thesis-archive/search?${query}`;
    void request<Entry|Listing>(path,context.user_id,{signal:controller.signal}).then(result=>{
      if(controller.signal.aborted)return;
      if("items" in result)setList(result);
      else setDetail(result);
    }).catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[focus,mode,page,round,department,state,debounced,revision,context.user_id]);

  const scopes = list?.scopes??[];
  const rounds = new Map(scopes.map(scope=>[scope.round_id,scope.round]));
  const departments = new Map(scopes.filter(scope=>!round||scope.round_id===round).map(scope=>[scope.department_id,scope.department]));
  const changeMode = (next:string) => {setPage(1);setParams(next==="work"?{mode:"work"}:{});};
  const closeDetail = () => setParams(mode==="work"?{mode:"work"}:{});
  const pageCount = list ? Math.max(1,Math.ceil(list.total/list.limit)) : 1;
  return <div className="stack defense-page archive-page">
    <PageHeader title="Kho khóa luận nội bộ" description="Tra cứu bản đã duyệt và theo dõi việc nộp lưu theo phạm vi được giao.">
      <button className="btn btn-secondary" disabled={loading} onClick={refresh}>Làm mới</button>
    </PageHeader>
    {error && <p className="alert alert-danger" role="alert">{error}</p>}
    {focus ? <>
      <div className="button-row"><button type="button" className="btn btn-secondary" onClick={closeDetail}>Quay về danh sách</button></div>
      {loading && detail?.id!==focus && <p role="status">Đang mở hồ sơ nộp lưu…</p>}
      {!error && detail?.id===focus && <ArchiveDetail key={focus} item={detail} userId={context.user_id} refresh={refresh}/>}
    </> : <>
      <nav className="defense-tabs" aria-label="Kho khóa luận">
        <button className={`btn ${mode==="catalog"?"btn-primary":"btn-secondary"}`} aria-pressed={mode==="catalog"} onClick={()=>changeMode("catalog")}>Tra cứu bản đã lưu</button>
        <button className={`btn ${mode==="work"?"btn-primary":"btn-secondary"}`} aria-pressed={mode==="work"} onClick={()=>changeMode("work")}>Hồ sơ nộp lưu</button>
      </nav>
      <section className="card"><div className="card-body stack">
        <div className="defense-form-grid archive-filters">
          <label>Đợt KLTN<select className="input" value={round} onChange={e=>{setRound(e.target.value);setDepartment("");setPage(1);}}>
            <option value="">Tất cả đợt</option>{Array.from(rounds,([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
          <label>Bộ môn<select className="input" value={department} onChange={e=>{setDepartment(e.target.value);setPage(1);}}>
            <option value="">Tất cả bộ môn</option>{Array.from(departments,([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
          {mode==="work" && <label>Trạng thái<select aria-label="Trạng thái" className="input" value={state} onChange={e=>{setState(e.target.value);setPage(1);}}>
            <option value="">Tất cả trạng thái</option><option value="SUBMITTED">Chờ bộ môn duyệt</option><option value="EMPTY">Chưa có bản nộp</option>
            <option value="RETURNED">Cần nộp lại</option><option value="REOPENED">Đã thu hồi bản lưu</option><option value="ACCEPTED">Đã duyệt lưu</option></select></label>}
          <label>Tìm khóa luận<input className="input" type="search" value={search} maxLength={150}
            placeholder="Tên, mã đề tài, MSSV, sinh viên hoặc GVHD" onChange={e=>{setSearch(e.target.value);setPage(1);}}/></label>
        </div>
        {(search||round||department||(mode==="work"&&state)) && <button className="btn btn-secondary archive-reset" onClick={()=>{
          setRound("");setDepartment("");setState("");setSearch("");setDebounced("");setPage(1);
        }}>Xóa bộ lọc</button>}
      </div></section>
      {loading && <p role="status">Đang tải danh sách khóa luận…</p>}
      {!loading && !error && list && <>
        <p role="status">{list.total} khóa luận · Trang {list.page}/{pageCount}</p>
        {!list.items.length && <div className="card"><div className="card-body stack">
          <p>{mode==="catalog"?"Chưa tìm thấy bản khóa luận đã duyệt trong phạm vi đang xem.":"Chưa có hồ sơ nộp lưu phù hợp."}</p>
          {mode==="catalog" && <div><button className="btn btn-secondary" onClick={()=>changeMode("work")}>Mở hồ sơ nộp lưu</button></div>}
        </div></div>}
        <ul className="archive-list">{list.items.map(item=><li className="card" key={item.id}><div className="card-body stack">
          <div className="archive-heading"><div>
            <p className="text-muted">{item.topic_code} · {item.round} · {item.department}</p>
            <h2><Link to={`/repository?mode=${mode}&focus=${item.id}`}>{item.snapshot?.title||item.current_title}</Link></h2>
          </div><span className="archive-status" data-state={item.state??"EMPTY"}>{item.state?labels[item.state]:"Chưa có bản nộp"}</span></div>
          <p>GVHD · {item.snapshot?.advisor||item.advisor||"Chưa ghi nhận"}{item.snapshot?.students.length
            ? ` · SV · ${item.snapshot.students.map(student=>student.name).join(", ")}`:""}</p>
          {item.version_no && <p className="text-muted">Phiên bản {item.version_no}{item.state==="ACCEPTED" && item.approved_at ? ` · Duyệt ${when(item.approved_at)}`:""}</p>}
        </div></li>)}</ul>
        {pageCount>1 && <nav className="button-row" aria-label="Trang kết quả tìm kiếm">
          <button className="btn btn-secondary" disabled={list.page<=1} onClick={()=>setPage(list.page-1)}>Trang trước</button>
          <button className="btn btn-secondary" disabled={list.page>=pageCount} onClick={()=>setPage(list.page+1)}>Trang sau</button>
        </nav>}
      </>}
    </>}
  </div>;
}
