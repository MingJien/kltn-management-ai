import {useEffect,useState} from 'react';
import {request,downloadFile} from '../../api';
import {when} from '../../evaluation';
import {errorMessage} from '../../errors';
type Snapshot={council:string;round:string;department:string;rows:{order:number;title:string;topic_code:string;advisor:string;students:{name:string;code:string;class_name:string}[];arrival_at:string;starts_at:string;ends_at:string;room:string}[]};
type Notice={id:string;version:number;published_at:string;current:boolean;snapshot:Snapshot};
export function SharedArrival({slots,save,busy}:{slots:{id:string;version:number;title:string;starts_at:string}[];save:(body:unknown)=>Promise<boolean>;busy:boolean}){
 const [selected,setSelected]=useState<string[]>([]);
 if(!slots.length)return null;
 return <details className="defense-operation"><summary>Áp dụng giờ tập trung / phòng cho lịch đã xếp</summary><form className="stack" onChange={e=>{e.currentTarget.dataset.dirty='true';}} onSubmit={async e=>{e.preventDefault();const form=e.currentTarget,f=new FormData(form);form.dataset.submitting='true';try{if(await save({slots:slots.filter(s=>selected.includes(s.id)).map(s=>({id:s.id,version:s.version})),arrival_at:String(f.get('arrival'))+':00+07:00',room:String(f.get('room'))||null})){form.dataset.dirty='false';setSelected([]);}}finally{form.removeAttribute('data-submitting');}}}>
 <p>Chọn các đề tài cùng buổi. Giữ giờ bảo vệ dự kiến của từng đề tài; thay giờ tập trung và phòng chung trong một lần. Sau đó công bố lại danh sách nếu đã công bố trước đó.</p>
 <fieldset className="defense-planning"><legend>Lịch chưa mở phiên</legend><button type="button" className="btn btn-secondary" onClick={()=>setSelected(selected.length?[]:slots.slice(0,30).map(s=>s.id))}>{selected.length?'Bỏ chọn':slots.length>30?'Chọn 30 lịch đầu':'Chọn tất cả lịch'}</button>{slots.map(s=><label className="defense-check" key={s.id}><input type="checkbox" checked={selected.includes(s.id)} disabled={!selected.includes(s.id)&&selected.length>=30} onChange={e=>setSelected(ids=>e.target.checked?[...ids,s.id]:ids.filter(id=>id!==s.id))}/>{s.title} · {when(s.starts_at)}</label>)}</fieldset>
 <div className="defense-form-grid"><label>Giờ tập trung chung<input className="input" type="datetime-local" name="arrival" required/></label><label>Phòng chung (để trống giữ phòng hiện tại)<input className="input" name="room" minLength={2} maxLength={200}/></label></div><button className="btn btn-primary" disabled={busy||!selected.length}>Áp dụng cho {selected.length} lịch đã chọn</button>
 </form></details>;
}
function ScheduleTable({snapshot}:{snapshot:Snapshot}){return <div className="defense-results"><table className="defense-schedule-table"><caption>{snapshot.council} · {snapshot.round}</caption><thead><tr><th>Thứ tự</th><th>Đề tài / SV</th><th>GVHD</th><th>Tập trung</th><th>Bảo vệ dự kiến</th><th>Phòng</th></tr></thead><tbody>{snapshot.rows.map(r=><tr key={r.order}><td>{r.order}</td><td><strong>{r.title}</strong><br/><small>{r.topic_code}</small>{r.students.map(s=><div key={s.code}>{s.name} · {s.code} · {s.class_name}</div>)}</td><td>{r.advisor}</td><td>{when(r.arrival_at)}</td><td>{when(r.starts_at)} → {when(r.ends_at)}</td><td>{r.room}</td></tr>)}</tbody></table></div>;}

export function PublishDefenseSchedule({councilId,save,busy}:{councilId:string;save:(body:unknown)=>Promise<boolean>;busy:boolean}){
 const [draft,setDraft]=useState<{snapshot:Snapshot;fingerprint:string}|null>(null),[error,setError]=useState('');
 return <details className="defense-operation"><summary>Công bố danh sách bảo vệ cho sinh viên</summary>
 <p>Đối chiếu danh sách toàn hội đồng rồi công bố. Sinh viên cùng bộ môn/đợt được xem thứ tự, giờ tập trung, đề tài, GVHD và tải Excel; điểm và hồ sơ riêng không nằm trong danh sách.</p>
 <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>{setError('');request<{snapshot:Snapshot;fingerprint:string}>(`/defense/councils/${councilId}/schedule-draft`,'').then(setDraft).catch(e=>setError(errorMessage(e)));}}>Xem trước danh sách cần công bố</button>
 {error&&<p role="alert">{error}</p>}
 {draft&&<><ScheduleTable snapshot={draft.snapshot}/><button type="button" className="btn btn-primary" disabled={busy||!draft.snapshot.rows.length} onClick={async()=>{if(window.confirm('Công bố danh sách này và gửi thông báo tới các tài khoản trong phạm vi?')){if(await save({fingerprint:draft.fingerprint}))setDraft(null);}}}>Công bố và thông báo danh sách</button></>}
 </details>;
}

export default function DefenseScheduleNotices({refresh}:{refresh:number}){
 const [items,setItems]=useState<Notice[]>([]),[error,setError]=useState('');
 useEffect(()=>{const controller=new AbortController();request<Notice[]>('/defense/schedule-notices','',{signal:controller.signal}).then(setItems).catch(e=>{if(!controller.signal.aborted)setError(errorMessage(e));});return()=>controller.abort();},[refresh]);
 return <section className="stack"><h2>Danh sách bảo vệ đã công bố</h2>{error&&<p role="alert">{error}</p>}{!items.length&&!error&&<p>Chưa có danh sách công bố trong phạm vi của bạn.</p>}
 {items.map(item=><details className="defense-operation" key={item.id}><summary>{item.snapshot.council} · {item.snapshot.round} · Bản {item.version}</summary><p>Công bố: {when(item.published_at)} · {item.snapshot.department} · Mã số: {item.id.replaceAll("-", "").slice(0,12)}</p>{!item.current&&<p className="alert alert-warning">Lịch đang được cập nhật, bản dưới đây chưa phản ánh thay đổi mới. Chờ người quản lý công bố lại.</p>}<ScheduleTable snapshot={item.snapshot}/><button type="button" className="btn btn-secondary" onClick={()=>downloadFile(`/defense/schedule-notices/${item.id}/download`,'Danh-sach-bao-ve.xlsx').catch(e=>setError(errorMessage(e)))}>Tải danh sách Excel · bản {item.version}</button></details>)}
 </section>;
}
