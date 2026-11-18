import {useEffect,useState,type FormEvent} from 'react';
import {request} from '../../api';
import {errorMessage} from '../../errors';
import {when} from '../../evaluation';
type Student={id:string;name:string;code:string};
type Mark={scores:string[];note:string};
type Minutes={discussion?:string;conclusion?:string;objectives?:string;functions?:string;achievements?:string;recommendations?:string;no_recommendations?:boolean;classifications?:Record<string,string>;oral_comments?:Record<string,Record<string,string>>};
type Slot={id:string;version:number;roster:Student[];minutes:Minutes;marks:Record<string,Record<string,Mark>>;results:Record<string,{attendance:{status?:string}}>;
  council:{members:{id:string;name:string}[]}};
type Item={id:string;version:number;state:string;reason:string;reference:string;can_decide:boolean;can_cancel:boolean;decision_note:string|null;source_version?:number;requested_by_name?:string;created_at?:string;decided_by_name?:string|null;decided_at?:string|null;
  proposal:{kind:string;student_id:string;lecturer_id:string;scores:string[];note:string;minutes:Minutes};before:{marks:Slot['marks'];minutes:Minutes}};
const fields=[['objectives','Mục tiêu'],['functions','Chức năng'],['achievements','Kết quả đạt được'],['discussion','Nội dung trao đổi'],['conclusion','Kết luận'],['recommendations','Kiến nghị']] as const;
const states:Record<string,string>={PENDING:'Chờ TBM duyệt',APPROVED:'Đã duyệt',REJECTED:'Không duyệt',CANCELLED:'Đã hủy'};
export default function DefenseCorrections({slot,criteria,saved}:{slot:Slot;criteria:[string,string,string][];saved:()=>void}) {
  const [open,setOpen]=useState(false),[data,setData]=useState<{can_approve:boolean;missing:string[];items:Item[]}|null>(null);
  const [error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[reload,setReload]=useState(0);
  const [kind,setKind]=useState('MINUTES'),[student,setStudent]=useState(slot.roster.find(s=>slot.results[s.id].attendance.status==='PRESENT')?.id??''),[person,setPerson]=useState('');
  useEffect(()=>{if(!slot.marks[student]?.[person])setPerson(slot.council.members.find(p=>slot.marks[student]?.[p.id])?.id??'');},[student,person,slot.marks,slot.council.members]);
  const endpoint=`/defense/slots/${slot.id}/corrections`;
  useEffect(()=>{if(!open)return;const controller=new AbortController();void request<typeof data>(endpoint,'',{signal:controller.signal}).then(value=>{if(!controller.signal.aborted)setData(value);}).catch(e=>{if(!controller.signal.aborted)setError(errorMessage(e));});return()=>controller.abort();},[open,endpoint,reload,slot.version]);
  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();if(busy)return;const form=event.currentTarget;const values=new FormData(form);
    const proposal=kind==='BALLOT'?{student_id:student,lecturer_id:person,scores:criteria.map(([code])=>String(values.get('score-'+code))),note:values.get('note')}:
      {minutes:{...Object.fromEntries(fields.map(([key])=>[key,String(values.get(key)??'')])),no_recommendations:values.has('no_recommendations'),
        oral_comments:slot.minutes.oral_comments??{},
        classifications:Object.fromEntries(slot.roster.filter(row=>slot.results[row.id].attendance.status==='PRESENT').map(row=>[row.id,values.get('classification-'+row.id)]))}};
    setBusy(true);setError('');setMessage('');
    try {await request(endpoint,'',{method:'POST',headers:{'If-Match':String(slot.version)},body:JSON.stringify({kind,...proposal,reference:values.get('reference'),reason:values.get('reason')})});form.reset();form.dataset.dirty='false';setMessage('Đã gửi đề nghị. Kết quả đang khóa được giữ nguyên cho đến khi TBM khác người lập duyệt.');setReload(v=>v+1);}
    catch(e){setError(errorMessage(e));}finally{setBusy(false);}
  }
  return <details className="defense-operation" onToggle={e=>setOpen(e.currentTarget.open)}><summary>Đính chính hồ sơ sau khóa</summary><div className="stack">
    <p>Không mở khóa điểm. Lập đề nghị có căn cứ; TBM trong bộ môn, khác người lập, đối chiếu và quyết định. Bản cũ và bản in cũ vẫn được giữ.</p>
    {data?.can_approve&&<p>Bạn có quyền TBM duyệt: để chính bạn duyệt, thư ký hoặc chủ tịch cần lập đề nghị. Bạn không tự duyệt đề nghị do mình lập.</p>}
    {error&&<p role="alert" className="alert alert-danger">{error} <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>{setError('');setReload(v=>v+1);}}>Tải lại đề nghị</button></p>}{message&&<p role="status">{message}</p>}
    {data?.missing.length? <aside className="defense-blockers"><strong>Hồ sơ lịch sử còn thiếu</strong><ul>{data.missing.map(m=><li key={m}>{m}</li>)}</ul></aside>:null}
    {!data&&open&&<p>Đang tải đề nghị…</p>}
    {data?.items.map(item=><details className="defense-operation" key={item.id} open={item.state==='PENDING'}><summary>{states[item.state]} · {item.proposal.kind==='BALLOT'?'Phiếu chấm':'Biên bản'}</summary><div className="stack"><p>{item.reference} · {item.reason}</p>
      {item.requested_by_name&&<p>Người lập: {item.requested_by_name} · {when(item.created_at??null)} · Nguồn v{item.source_version}</p>}
      {item.decided_by_name&&<p>Người xử lý: {item.decided_by_name} · {when(item.decided_at??null)}{item.state==='APPROVED'&&` · Bản đính chính v${(item.source_version??0)+1}`}</p>}
      {item.proposal.kind==='BALLOT'?<><p>{slot.roster.find(s=>s.id===item.proposal.student_id)?.name} · {slot.council.members.find(m=>m.id===item.proposal.lecturer_id)?.name}</p><div className="defense-results"><table><thead><tr><th>Tiêu chí</th><th>Trước</th><th>Đề nghị</th></tr></thead><tbody>{criteria.map(([code,label],i)=><tr key={code}><td>{code} · {label}</td><td>{item.before.marks[item.proposal.student_id]?.[item.proposal.lecturer_id]?.scores[i]}</td><td>{item.proposal.scores[i]}</td></tr>)}</tbody></table></div><p>Nhận xét đề nghị: {item.proposal.note||'Không có'}</p></>:
        <div className="defense-results"><table className="defense-comparison-table"><thead><tr><th>Nội dung</th><th>Trước</th><th>Đề nghị</th></tr></thead><tbody>{fields.map(([key,label])=><tr key={key}><td>{label}</td><td>{item.before.minutes[key]||'Chưa ghi'}</td><td>{item.proposal.minutes[key]||'Không có'}</td></tr>)}{slot.roster.map(row=><tr key={row.id}><td>Xếp loại · {row.name}</td><td>{item.before.minutes.classifications?.[row.id]||'Chưa ghi'}</td><td>{item.proposal.minutes.classifications?.[row.id]||'Không ghi'}</td></tr>)}</tbody></table></div>}
      {item.decision_note&&<p>Kết quả xử lý: {item.decision_note}</p>}
      {item.state==='PENDING'&&(item.can_decide||item.can_cancel)&&<form onSubmit={async e=>{e.preventDefault();if(busy)return;const values=new FormData(e.currentTarget);setBusy(true);setError('');try{await request(`/defense/corrections/${item.id}/decision`,'',{method:'POST',headers:{'If-Match':String(item.version)},body:JSON.stringify({decision:values.get('decision'),reason:values.get('decision_reason')})});setReload(v=>v+1);setMessage('Đã ghi nhận quyết định đính chính.');saved();}catch(err){setError(errorMessage(err));}finally{setBusy(false);}}}>
        <label>Quyết định<select className="input" name="decision" required defaultValue=""><option value="">Chọn quyết định</option>{item.can_decide&&<><option value="APPROVED">Duyệt theo căn cứ</option><option value="REJECTED">Không duyệt</option></>}{item.can_cancel&&<option value="CANCELLED">Hủy đề nghị của tôi</option>}</select></label>
        <label>Nhận xét quyết định<textarea className="input" name="decision_reason" required minLength={10} maxLength={2000}/></label><button className="btn btn-primary" disabled={busy}>Lưu quyết định đính chính</button>
      </form>}
    </div></details>)}
    {data&&!data.items.some(item=>item.state==='PENDING')&&<form key={slot.version} onChange={e=>{e.currentTarget.dataset.dirty='true';}} onSubmit={submit}>
      <label>Phần cần đính chính<select className="input" value={kind} onChange={e=>setKind(e.target.value)}><option value="MINUTES">Nội dung biên bản / xếp loại còn thiếu</option><option value="BALLOT">Một phiếu chấm đã nhập</option></select></label>
      {kind==='BALLOT'?<><label>Sinh viên<select className="input" value={student} onChange={e=>setStudent(e.target.value)}>{slot.roster.filter(s=>slot.results[s.id].attendance.status==='PRESENT').map(s=><option key={s.id} value={s.id}>{s.name} · {s.code}</option>)}</select></label><label>Người chấm<select className="input" value={person} onChange={e=>setPerson(e.target.value)}>{slot.council.members.filter(p=>slot.marks[student]?.[p.id]).map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <fieldset key={student+person} className="defense-planning stack"><legend>Đối chiếu từng tiêu chí với phiếu có căn cứ</legend>{criteria.map(([code,label,max],i)=><label key={code}>{code} · {label} (tối đa {max})<input className="input" type="number" min="0" max={max} step="0.01" required name={'score-'+code} defaultValue={slot.marks[student]?.[person]?.scores[i]??''}/></label>)}<label>Nhận xét sau đính chính<textarea className="input" name="note" maxLength={3000} defaultValue={slot.marks[student]?.[person]?.note??''}/></label></fieldset></>:
        <fieldset className="defense-planning stack"><legend>Nội dung theo biên bản có căn cứ</legend>{fields.map(([key,label])=><label key={key}>{label}<textarea className="input" name={key} required={key!=='recommendations'} minLength={key==='discussion'||key==='conclusion'?5:1} maxLength={key==='discussion'?10000:key==='conclusion'||key==='recommendations'?5000:3000} defaultValue={String(slot.minutes[key]??'')}/></label>)}<label className="defense-check"><input type="checkbox" name="no_recommendations" defaultChecked={slot.minutes.no_recommendations}/>Xác nhận không có kiến nghị (để trống ô kiến nghị)</label>{slot.roster.filter(s=>slot.results[s.id].attendance.status==='PRESENT').map(s=><label key={s.id}>Xếp loại · {s.name}<select className="input" required name={'classification-'+s.id} defaultValue={slot.minutes.classifications?.[s.id]??''}><option value="">Chọn theo biên bản</option>{['Xuất sắc','Giỏi','Khá','Trung bình','Không đạt'].map(v=><option key={v}>{v}</option>)}</select></label>)}</fieldset>}
      <label>Số văn bản / căn cứ đính chính<input className="input" name="reference" required minLength={5} maxLength={500}/></label><label>Lý do đính chính<textarea className="input" name="reason" required minLength={10} maxLength={2000}/></label><button className="btn btn-primary" disabled={busy}>Gửi đề nghị đính chính</button>
    </form>}
  </div></details>;
}
