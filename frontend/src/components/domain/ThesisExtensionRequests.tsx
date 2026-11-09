import {useState,type FormEvent} from "react";
import {request} from "../../api";
import {errorMessage} from "../../errors";
import {when} from "../../evaluation";
import Dialog from "../ui/Dialog";

export type ExtensionRequest={id:string;thesis_id:string;title:string;state:string;row_version:number;reason:string;
  submitted_at:string;original_due_at:string;requested_until_at:string;extension_until_at:string|null;consent_due_at:string|null;
  advisor_reason:string|null;decision_reason:string|null;decided_at:string|null;extension_starts_at:string|null;all_agreed:boolean;
  members:{student_id:string;user_id:string;name:string;decision:string;responded_at:string|null}[];
  can_consent:boolean;can_review:boolean;can_decide:boolean;can_cancel:boolean;can_manage_consent:boolean};
type Thesis={id:string;title:string;row_version:number;can_request_extension:boolean;extension_request_blocker:string;baseline_due:string|null};
type Operation={kind:"create";thesis:Thesis}|{kind:"consent"|"review"|"decision"|"deadline"|"cancel";item:ExtensionRequest};
const labels:Record<string,string>={SUBMITTED:"Đang lấy ý kiến",ADVISOR_REVIEWED:"Chờ TBM quyết định",APPROVED:"Đã ghi nhận gia hạn",REJECTED:"Không chấp thuận",CANCELLED:"Đã hủy yêu cầu",EXPIRED:"Hết hạn"};
const local=(value:string)=>new Date(Date.parse(value)+7*3600000).toISOString().slice(0,16);
const iso=(value:string)=>value?value+":00+07:00":null;

function ExtensionDialog({op,userId,close,saved}:{op:Operation;userId:string;close:()=>void;saved:()=>Promise<void>}) {
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  const [answer,setAnswer]=useState(op.kind==="decision"?"REJECT":"AGREE");
  const [confirmed,setConfirmed]=useState(false);
  const item="item" in op?op.item:null;
  const ready=!!item?.all_agreed&&item?.state==="ADVISOR_REVIEWED";
  const titles={create:"Xin gia hạn thực hiện KLTN",consent:"Xác nhận nguyện vọng gia hạn",review:"GVHD cho ý kiến gia hạn",decision:"TBM quyết định gia hạn",deadline:"Hạn lấy ý kiến và nhắc xác nhận",cancel:"Hủy yêu cầu gia hạn"};
  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();if(busy)return;
    const data=new FormData(event.currentTarget);const get=(key:string)=>String(data.get(key)||"");
    let path="",body:object={},version=0;
    if(op.kind==="create") {path=`/theses/${op.thesis.id}/extension-requests`;version=op.thesis.row_version;body={until_at:iso(get("until")),reason:get("reason"),confirm_consequences:confirmed};}
    else {
      version=op.item.row_version;path=`/thesis-extension-requests/${op.item.id}/`;
      if(op.kind==="consent"){path+="consent";body={decision:answer};}
      if(op.kind==="review"){path+="advisor-review";body={decision:answer,reason:get("reason")};}
      if(op.kind==="decision"){path+="decision";body={decision:answer,reason:get("reason"),...(answer==="APPROVE"?{
        decision_on:get("day"),extension_starts_at:iso(get("starts")),until_at:iso(get("until")),reference:get("reference"),confirm_decision:confirmed}:{})};}
      if(op.kind==="deadline"){path+="consent-deadline";body={due_at:iso(get("due")),reason:get("reason")};}
      if(op.kind==="cancel")path+="cancel";
    }
    setBusy(true);setError("");
    try {await request(path,userId,{method:"POST",headers:{"If-Match":String(version)},body:JSON.stringify(body)});await saved();close();}
    catch(cause){setError(errorMessage(cause));}finally{setBusy(false);}
  }
  return <Dialog open size="lg" title={titles[op.kind]} busy={busy} onClose={()=>{if(!busy)close();}} footer={<>
    <button className="btn btn-secondary" disabled={busy} onClick={close}>Quay lại</button>
    <button className="btn btn-primary" form="extension-operation" type="submit" disabled={busy||((op.kind==="create"||(op.kind==="decision"&&answer==="APPROVE"))&&!confirmed)}>{busy?"Đang xử lý…":op.kind==="create"?"Gửi yêu cầu gia hạn":op.kind==="deadline"?"Lưu và nhắc xác nhận":"Xác nhận"}</button>
  </>}><form id="extension-operation" className="change-form" onSubmit={event=>void submit(event)}>
    {error&&<p role="alert" className="alert alert-danger">{error}</p>}
    <fieldset disabled={busy} className="change-fieldset">
      <p className="change-context"><strong>{op.kind==="create"?op.thesis.title:op.item.title}</strong></p>
      {op.kind==="create"&&<>
        <p>Đề nghị chỉ có hiệu lực sau khi đủ đồng thuận nhóm, GVHD đồng ý và TBM ghi nhận quyết định. Trong lúc chờ, hạn hiện tại vẫn áp dụng.</p>
        <p>Hạn báo cáo hiện hành: <strong>{when(op.thesis.baseline_due)}</strong></p>
        <label>Hạn hoàn thành đề nghị (giờ Việt Nam)<input className="input" name="until" type="datetime-local" required/></label>
        <label>Lý do xin gia hạn<textarea className="input" name="reason" minLength={10} maxLength={3000} required rows={4}/></label>
        <label className="change-checkbox"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} required/><span>Tôi đồng ý xin gia hạn và hiểu rằng các thành viên khác phải tự xác nhận nguyện vọng.</span></label>
      </>}
      {op.kind==="cancel"&&<p>Chỉ hủy yêu cầu đang chờ. Bạn và các thành viên vẫn tiếp tục KLTN theo hồ sơ và hạn hiện tại.</p>}
      {["consent","review","decision"].includes(op.kind)&&<label>Kết quả<select aria-label="Kết quả" className="input" value={answer} onChange={e=>setAnswer(e.target.value)}>
        {op.kind==="decision"?<><option value="REJECT">Không chấp thuận</option><option value="APPROVE" disabled={!ready}>Chấp thuận và ghi nhận quyết định</option></>:
        <><option value="AGREE">Đồng ý</option><option value={op.kind==="consent"?"DECLINE":"REJECT"}>Không đồng ý</option></>}
      </select></label>}
      {op.kind==="consent"&&<p>Bạn xác nhận nguyện vọng của chính mình. Không đồng ý sẽ kết thúc yêu cầu gia hạn nhóm, không hủy quyền tham gia KLTN của ai.</p>}
      {op.kind==="decision"&&!ready&&<p className="alert alert-info">Chưa đủ đồng thuận của các thành viên hoặc ý kiến đồng ý của GVHD. Bạn có thể từ chối kèm lý do; chưa thể chấp thuận.</p>}
      {op.kind==="decision"&&answer==="APPROVE"&&<>
        <p className="change-note">Theo hướng dẫn của GV, nếu kỳ bảo vệ dự kiến tháng 4 mà chưa bảo vệ thì gia hạn từ tháng 5 đến hết tháng 9; kỳ bảo vệ tiếp theo phải diễn ra trong tháng 9. Nhập đúng ngày theo quyết định của Khoa; thời hạn không quá 5 tháng.</p>
        <div className="change-field-grid"><label>Ngày quyết định<input className="input" name="day" type="date" required/></label>
          <label>Bắt đầu gia hạn theo quyết định (giờ Việt Nam)<input className="input" name="starts" type="datetime-local" required/></label></div>
        <label>Hạn mới được duyệt (giờ Việt Nam)<input className="input" name="until" type="datetime-local" required defaultValue={item?local(item.requested_until_at):""}/></label>
        <label>Số hoặc căn cứ quyết định<input className="input" name="reference" required minLength={5} maxLength={500}/></label>
        <label className="change-checkbox"><input type="checkbox" required checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/><span>Tôi đã đối chiếu quyết định và mốc thời gian ghi nhận.</span></label>
      </>}
      {op.kind==="deadline"&&<><p>Chỉ nhắc các thành viên chưa xác nhận. Hết hạn chỉ kết thúc yêu cầu gia hạn, không hủy hồ sơ tham gia KLTN.</p>
        <label>Hạn xác nhận (giờ Việt Nam)<input className="input" name="due" type="datetime-local" defaultValue={item?.consent_due_at?local(item.consent_due_at):""}/></label><small>Để trống nếu chỉ gửi nhắc theo hạn hiện có.</small></>}
      {["review","decision","deadline"].includes(op.kind)&&<label>Ý kiến và căn cứ<textarea name="reason" className="input" required minLength={5} maxLength={2000} rows={4}/></label>}
    </fieldset>
  </form></Dialog>;
}

export default function ThesisExtensionRequests({userId,thesis,items,reload}:{userId:string;thesis:Thesis|undefined;items:ExtensionRequest[];reload:()=>Promise<void>}) {
  const [op,setOp]=useState<Operation|null>(null);
  const [history,setHistory]=useState(false);
  const visible=items.filter(item=>(!thesis||item.thesis_id===thesis.id)&&(history||["SUBMITTED","ADVISOR_REVIEWED","APPROVED"].includes(item.state)||(item.state==="EXPIRED"&&item.decision_reason?.startsWith("KLTN không đạt"))));
  return <div className="stack">
    <div className="changes-toolbar"><h2>Yêu cầu gia hạn thực hiện KLTN</h2><div className="change-actions">
      {thesis?.can_request_extension&&<button className="btn btn-primary" onClick={()=>setOp({kind:"create",thesis})}>Xin gia hạn KLTN</button>}
      <label className="change-checkbox"><input type="checkbox" checked={history} onChange={e=>setHistory(e.target.checked)}/>Xem cả lịch sử</label>
    </div></div>
    {thesis?.extension_request_blocker&&<p className="change-note">{thesis.extension_request_blocker}</p>}
    <p className="change-note">Gia hạn thực hiện KLTN được xét theo hồ sơ, tách riêng hạn báo cáo tuần và hạn chung của đợt. Nhóm chỉ được xét khi tất cả thành viên đồng ý.</p>
    {!visible.length&&<div className="changes-empty card"><p>Chưa có yêu cầu trong bộ lọc. Chọn hồ sơ ở bên trái để xem thao tác phù hợp với quyền của bạn.</p></div>}
    {visible.map(item=><article className="change-card card" key={item.id}><div className="card-body stack">
      <div className="change-card__heading"><h3>{item.title}</h3><span className={"change-status change-status--"+item.state.toLowerCase()}>{item.state==="EXPIRED"&&item.decision_reason?.startsWith("KLTN không đạt")?"Không đạt":labels[item.state]}</span></div>
      <ol className="change-steps" aria-label="Tiến trình gia hạn">{["Thành viên đồng ý","GVHD cho ý kiến","TBM quyết định","Kết quả"].map((label,index)=>
        <li key={label} className={(index===0?item.all_agreed:index===1?!!item.advisor_reason:index===2?!!item.decided_at:!["SUBMITTED","ADVISOR_REVIEWED"].includes(item.state))?"is-done":""}><span>{index+1}</span>{label}</li>)}</ol>
      <div className="extension-date-grid"><div><span>Hạn tại thời điểm gửi</span><p>{when(item.original_due_at)}</p></div><div><span>Hạn SV đề nghị</span><p>{when(item.requested_until_at)}</p></div>{item.extension_until_at&&<div><span>Hạn gia hạn được ghi nhận</span><p>{when(item.extension_until_at)}</p></div>}</div>
      <p className="change-prose">{item.reason}</p>
      <ul className="change-people">{item.members.map(member=><li key={member.student_id}><strong>{member.name}{member.user_id===userId?" (bạn)":""}</strong><span>{member.decision==="AGREE"?"Đồng ý":member.decision==="DECLINE"?"Không đồng ý":"Chờ xác nhận"}</span></li>)}</ul>
      {item.consent_due_at&&<p>Hạn xác nhận: <strong>{when(item.consent_due_at)}</strong></p>}
      {item.advisor_reason&&<p className="change-review"><strong>Ý kiến GVHD</strong><br/>{item.advisor_reason}</p>}
      {item.decision_reason&&<p className="change-result"><strong>Kết quả</strong><br/>{item.decision_reason}</p>}
      {item.state==="EXPIRED"&&<p className={"alert "+(item.decision_reason?.startsWith("KLTN không đạt")?"alert-danger":"alert-info")}>{item.decision_reason||"Yêu cầu đã hết hạn xác nhận. Hồ sơ KLTN và quyền tham gia của các thành viên vẫn giữ nguyên."}</p>}
      <div className="change-actions">
        {item.can_consent&&<button className="btn btn-primary" onClick={()=>setOp({kind:"consent",item})}>Xác nhận xin gia hạn</button>}
        {item.can_review&&<button className="btn btn-primary" onClick={()=>setOp({kind:"review",item})}>GVHD cho ý kiến</button>}
        {item.can_decide&&<button className="btn btn-primary" onClick={()=>setOp({kind:"decision",item})}>TBM xét gia hạn</button>}
        {item.can_manage_consent&&<button className="btn btn-secondary" onClick={()=>setOp({kind:"deadline",item})}>Hạn lấy ý kiến / nhắc xác nhận</button>}
        {item.can_cancel&&<button className="btn btn-secondary" onClick={()=>setOp({kind:"cancel",item})}>Hủy yêu cầu gia hạn</button>}
      </div><small>Gửi lúc {when(item.submitted_at)} · phiên bản {item.row_version}</small>
    </div></article>)}
    {op&&<ExtensionDialog key={op.kind+("item" in op?op.item.id:op.thesis.id)} op={op} userId={userId} close={()=>setOp(null)} saved={reload}/>}
  </div>;
}
