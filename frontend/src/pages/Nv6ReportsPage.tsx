import {useEffect, useRef, useState} from "react";
import {Link} from "react-router-dom";
import {CalendarDays, GraduationCap, RefreshCw, ShieldCheck, UsersRound} from "lucide-react";
import {request,type Context} from "../api";
import {errorMessage} from "../errors";
import {labels,when} from "../evaluation";
import PageHeader from "../components/layout/PageHeader";
import Dialog from "../components/ui/Dialog";
import FilterBar from "../components/ui/FilterBar";
import {SkeletonCard} from "../components/ui/Skeleton";
import EmptyState from "../components/ui/EmptyState";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import "../styles/defense.css";

type Scope = {round_id:string;round_code:string;department_id:string;department:string};
type Row = {id:string;thesis_id:string;title:string;name:string;code:string;class_name:string|null;eligibility:string;result:string;grade:string|null;issues:string[];slot_id:string|null;classification:string|null;attendance:string|null};
type Summary = {generated_at:string;theses:number;students:number;sessions:number;councils:number;eligibility:Record<string,number>;results:Record<string,number>;score_counts:Record<string,number>;archives:Record<string,number>;attendance:Record<string,number>;classifications:Record<string,number>;incomplete_profiles:number;rows:Row[]};
const resultLabels: Record<string,string> = {GRADED:"Đã chốt điểm",ABSENT_FINAL:"Không đạt do vắng",PENDING:"Chờ kết quả hoặc quyết định",NOT_SCHEDULED:"Chưa xếp lịch",EXTENSION_EXPIRED:"Không đạt do hết hạn gia hạn"};
const archiveLabels: Record<string,string> = {ACCEPTED:"Đã duyệt lưu",SUBMITTED:"Chờ bộ môn duyệt",RETURNED:"Cần nộp lại",NOT_SUBMITTED:"Đủ điều kiện, chưa nộp",WAITING_RESULTS:"Chờ chốt trước khi nộp",REOPENED:"Đã thu hồi bản lưu"};
const attendanceLabels: Record<string,string> = {PRESENT:"Có mặt",ABSENT:"Vắng",NOT_RECORDED:"Chưa điểm danh"};
const searchable = (value:string) => value.toLocaleLowerCase("vi").normalize("NFD").replace(/\p{Diacritic}/gu,"").replace(/đ/g,"d").trim();

type Profile = {class_name:string;major_code:string;birth_date:string;training_cohort:string;revision:string;majors:{code:string;name:string}[]};

function ProfileCorrection({row,round,close,saved}:{row:Row;round:string;close:()=>void;saved:()=>void}) {
  const [profile,setProfile] = useState<Profile|null>(null);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const endpoint = `/nv6-reports/${round}/students/${row.id}`;
  useEffect(()=>{
    const controller = new AbortController();
    void request<Profile>(endpoint,"",{signal:controller.signal}).then(data=>{if(!controller.signal.aborted)setProfile(data);})
      .catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));});
    return ()=>controller.abort();
  },[endpoint]);
  return <Dialog open title={`Thông tin học vụ · ${row.name}`} onClose={close} busy={busy}>
    <p>{row.code} · {row.title}</p>
    {error&&<p role="alert" className="alert alert-danger">{error}</p>}
    {!profile&&!error&&<p role="status">Đang tải thông tin học vụ…</p>}
    {profile&&<form className="stack" onSubmit={async event=>{
      event.preventDefault();
      if(busy)return;
      const fields = Object.fromEntries(new FormData(event.currentTarget));
      setBusy(true);setError("");
      try {await request(endpoint,"",{method:"PUT",headers:{"If-Match":profile.revision},body:JSON.stringify({...fields,birth_date:fields.birth_date||null})});saved();}
      catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}
    }}>
      <div className="defense-form-grid">
        <label>Lớp<input className="input" name="class_name" defaultValue={profile.class_name} required maxLength={100}/></label>
        <label>Ngành<select className="input" name="major_code" defaultValue={profile.majors.some(m=>m.code===profile.major_code)?profile.major_code:""} required>
          <option value="">Chọn ngành từ danh mục</option>{profile.majors.map(major=><option key={major.code} value={major.code}>{major.code} · {major.name}</option>)}
        </select></label>
        <label>Khóa học<input className="input" name="training_cohort" defaultValue={profile.training_cohort} maxLength={50} placeholder="Ví dụ: 2022–2026"/></label>
        <label>Ngày sinh<input className="input" type="date" min="1900-01-01" name="birth_date" defaultValue={profile.birth_date}/></label>
      </div>
      {!profile.majors.length&&<p>Chưa có ngành đã xác minh trong danh mục bộ môn. Cập nhật danh mục trước khi lưu.</p>}
      <label>Căn cứ đối chiếu<input className="input" name="source_reference" required minLength={3} maxLength={500}/></label>
      <label>Lý do cập nhật<textarea className="input" name="reason" required minLength={5} maxLength={1000} rows={2}/></label>
      <button className="btn btn-primary" disabled={busy||!profile.majors.length}>Lưu thông tin học vụ</button>
    </form>}
  </Dialog>;
}

export default function Nv6ReportsPage({context}: {context:Context}) {
  const [scopes,setScopes] = useState<Scope[]|null>(null);
  const [round,setRound] = useState("");
  const [department,setDepartment] = useState("");
  const [data,setData] = useState<Summary|null>(null);
  const [error,setError] = useState("");
  const [revision,setRevision] = useState(0);
  const requestedRevision = useRef(0);
  const [filter,setFilter] = useState("");
  const [search,setSearch] = useState("");
  const [limit,setLimit] = useState(25);
  const [editing,setEditing] = useState<Row|null>(null);
  const [notice,setNotice] = useState("");
  const rounds = new Map(scopes?.map(scope=>[scope.round_id,scope.round_code]));

  useEffect(()=>{
    const controller = new AbortController();
    void request<Scope[]>("/nv6-reports/scopes",context.user_id,{signal:controller.signal}).then(result=>{
      if(controller.signal.aborted)return;
      setScopes(result);
      setRound(current=>current || (result.find(scope=>scope.round_code!=="SYN-DEMO")??result[0])?.round_id || "");
    }).catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));});
    return ()=>controller.abort();
  },[context.user_id,revision]);

  useEffect(()=>{
    setData(null);
    if(!round)return;
    const controller = new AbortController();
    const params = new URLSearchParams();
    if(department)params.set("department_id",department);
    if(revision !== requestedRevision.current)params.set("refresh","true");
    requestedRevision.current = revision;
    const path = `/nv6-reports/${round}${params.size?`?${params}`:""}`;
    void request<Summary>(path,context.user_id,{signal:controller.signal}).then(result=>{
      if(!controller.signal.aborted)setData(result);
    }).catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));});
    return ()=>controller.abort();
  },[round,department,context.user_id,revision]);

  const visible = data?.rows.filter(row=>(!filter||row.eligibility===filter||row.result===filter||(filter==="issues"&&row.issues.length))&&
    searchable(`${row.name} ${row.code} ${row.title}`).includes(searchable(search)))??[];
  function selectFilter(value:string, clearSearch=false) {
    if (clearSearch) setSearch("");
    setFilter(value);
    setLimit(25);
    document.getElementById("nv6-report-students")?.scrollIntoView({block:"start"});
  }
  function breakdown(title:string, values:Record<string,number>, names:Record<string,string>, links=false, archiveLink?:string) {
    return <section className="card"><div className="card-body"><h3>{title}</h3>
      {Object.keys(values).length?<ul className="dashboard-status-list">{Object.entries(values).map(([key,value])=><li key={key}>
        <span>{names[key]??key}</span>{links&&!!data?.rows.length?<button className="btn btn-secondary btn-sm" aria-label={`Xem ${value} · ${names[key]??key}`} onClick={()=>selectFilter(key,true)}>{value}</button>:<strong>{value}</strong>}
      </li>)}</ul>:<p className="text-muted">Chưa có dữ liệu trong phạm vi đang xem.</p>}
      {archiveLink&&<Link to={archiveLink}>Xem hồ sơ nộp lưu của đợt</Link>}
    </div></section>;
  }

  return <div className="stack defense-page">
    <PageHeader title="Báo cáo và thống kê KLTN" description="Theo dõi điều kiện bảo vệ, kết quả và tiến độ nộp lưu theo đợt và bộ môn.">
      <button type="button" className="btn btn-secondary" disabled={!round||(!data&&!error)} onClick={()=>{setError("");setRevision(value=>value+1);}}><RefreshCw size={15} aria-hidden="true"/>Làm mới thống kê</button>
    </PageHeader>
    {error&&<p className="alert alert-danger" role="alert">{error}</p>}
    {notice&&<p className="alert alert-success" role="status">{notice}</p>}
    {!scopes&&!error&&<div className="stack" role="status" aria-label="Đang tải phạm vi báo cáo"><SkeletonCard /><SkeletonCard /></div>}
    {scopes?.length===0&&<EmptyState title="Chưa được giao phạm vi báo cáo" description="Bạn chưa được giao xem báo cáo theo đợt hoặc bộ môn." />}
    {!!scopes?.length&&<div className="defense-form-grid">
      <label>Đợt KLTN<select className="input" value={round} onChange={event=>{setRound(event.target.value);setDepartment("");setFilter("");setError("");}}>
        {Array.from(rounds,([id,code])=><option key={id} value={id}>{code}</option>)}
      </select></label>
      <label>Bộ môn<select className="input" value={department} onChange={event=>{setDepartment(event.target.value);setFilter("");setError("");}}>
        <option value="">Tất cả bộ môn trong phạm vi</option>{scopes.filter(scope=>scope.round_id===round).map(scope=><option key={scope.department_id} value={scope.department_id}>{scope.department}</option>)}
      </select></label>
    </div>}
    {round&&!data&&!error&&<div className="dashboard-metrics" role="status" aria-label="Đang tổng hợp số liệu"><SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard /></div>}
    {data&&<>
      <div className="dashboard-metrics">{([
        ["Sinh viên", data.students, UsersRound],
        ["Khóa luận", data.theses, GraduationCap],
        ["Hội đồng có lịch", data.councils, ShieldCheck],
        ["Phiên bảo vệ", data.sessions, CalendarDays],
      ] as const).map(([name,value,Icon])=><div className="card metric-card" key={name}><span className="flex items-center justify-between gap-2">{name}<Icon size={16} className="metric-card__icon" aria-hidden="true"/></span><strong>{value}</strong></div>)}</div>
      <div className="dashboard-breakdown">
        {breakdown("Điều kiện dự bảo vệ · theo SV",data.eligibility,labels,true)}
        {breakdown("Kết quả bảo vệ · theo SV",data.results,resultLabels,true)}
        {breakdown("Nộp lưu · theo khóa luận",data.archives,archiveLabels,false,
          context.base_role==="LECTURER" ? `/repository?mode=work&round_id=${round}${department?"&department_id="+department:""}` : undefined)}
        {breakdown("Điểm danh · phiên sau cùng",data.attendance,attendanceLabels)}
        {breakdown("Xếp loại đã ghi trong biên bản",data.classifications,{})}
      </div>
      {Object.keys(data.score_counts).length>0&&breakdown("Phân bố điểm đã chốt",Object.fromEntries(Object.entries(data.score_counts).sort(([a],[b])=>Number(b)-Number(a)).map(([key,value])=>[`${key.replace(".",",")} điểm`,value])),{})}
      <p className="text-muted">Số liệu cập nhật lúc {when(data.generated_at)} · {data.incomplete_profiles} sinh viên cần bổ sung dữ liệu học vụ.{rounds.get(round)==="SYN-DEMO"?" Đợt đang xem là dữ liệu giả lập.":""}</p>
      {context.base_role==="LECTURER"&&<section id="nv6-report-students" className="stack">
        <h2>Đối chiếu từng sinh viên</h2>
        <FilterBar
          search={{
            value: search,
            onChange: (next) => { setSearch(next); setLimit(25); },
            placeholder: "Tìm tên, MSSV hoặc đề tài…",
            ariaLabel: "Tìm tên, MSSV hoặc đề tài",
          }}
          chips={[
            ...(search.trim() ? [{ key: "q", label: `Từ khóa: "${search.trim()}"`, onRemove: () => setSearch("") }] : []),
            ...(filter ? [{ key: "filter", label: `Nhóm: ${filter === "issues" ? "Dữ liệu học vụ cần đối chiếu" : labels[filter] ?? resultLabels[filter] ?? filter}`, onRemove: () => selectFilter("") }] : []),
          ]}
          onClearAll={() => { setSearch(""); selectFilter(""); }}
          summary={`${visible.length} sinh viên · Hiển thị ${Math.min(visible.length,limit)}`}
        >
          <select aria-label="Nhóm cần xem" className="input" value={filter} onChange={event=>selectFilter(event.target.value)}>
            <option value="">Tất cả</option>
            <option value="issues">Dữ liệu học vụ cần đối chiếu</option>
            {[...Object.keys(data.eligibility),...Object.keys(data.results)].map(key=><option key={key} value={key}>{labels[key]??resultLabels[key]}</option>)}
          </select>
        </FilterBar>
        <p role="status">{visible.length} sinh viên phù hợp · Hiển thị {Math.min(visible.length,limit)}</p>
        <div className="defense-results" role="region" tabIndex={0} aria-label="Danh sách đối chiếu sinh viên"><table className="table-responsive"><thead><tr><th>Sinh viên và đề tài</th><th>Điều kiện</th><th>Kết quả</th><th>Dữ liệu học vụ</th></tr></thead><tbody>{visible.slice(0,limit).map(row=><tr key={row.id}>
          <td data-label="Sinh viên & đề tài"><strong>{row.name}</strong><br/><small>{row.code} · {row.class_name||"Chưa có lớp"}</small><br/>{row.title}</td>
          <td data-label="Điều kiện"><Link to={`/evaluation/${row.thesis_id}`}><ThesisStatusBadge state={row.eligibility} label={labels[row.eligibility]??row.eligibility}/></Link></td><td data-label="Kết quả">{row.grade?.replace(".",",")??resultLabels[row.result]}{row.classification&&<><br/><small>{row.classification}</small></>}</td>
          <td data-label="Dữ liệu học vụ">{row.issues.length ? <>{row.issues.join(", ")}<br/>{row.slot_id?<Link to={`/defense?slot=${row.slot_id}&tab=results`}>Mở hồ sơ đối chiếu</Link>:
            <button type="button" className="btn btn-secondary btn-sm" onClick={()=>{setNotice("");setEditing(row);}}>Bổ sung thông tin</button>}</>:<ThesisStatusBadge state="CLEAR" label="Đủ"/>}</td>
        </tr>)}</tbody></table></div>
        {!visible.length&&<EmptyState compact title="Không có sinh viên phù hợp bộ lọc" />}
        {visible.length>limit&&<button type="button" className="btn btn-secondary" onClick={()=>setLimit(v=>v+25)}>Xem thêm sinh viên</button>}
      </section>}
    </>}
    {editing&&<ProfileCorrection row={editing} round={round} close={()=>setEditing(null)} saved={()=>{
      setEditing(null);setNotice(`Đã lưu thông tin học vụ của ${editing.name}.`);setRevision(value=>value+1);
    }}/>}
  </div>;
}
