import {useState,type FormEvent} from "react";
type Council={id:string;name:string;round_id:string;department_id:string;closed_at:string|null;can_manage:boolean;members:{id:string}[]};
type Thesis={id:string;title:string;round_id:string;department_id:string;advisor_ids?:string[];schedule_reason?:string|null;can_review_eligibility?:boolean};
export default function BatchDefenseSchedule({data,save,busy}:{data:{councils:Council[];eligible:Thesis[];slots:{thesis_id:string}[];planning_theses?:Thesis[]};save:(body:unknown)=>Promise<boolean>;busy:boolean}) {
 const [councilId,setCouncil]=useState(""),[selected,setSelected]=useState<string[]>([]),[start,setStart]=useState(""),[duration,setDuration]=useState(45),[gap,setGap]=useState(5);
 const [sharedArrival,setSharedArrival]=useState(true),[arrival,setArrival]=useState("");
 const council=data.councils.find(c=>c.id===councilId),taken=new Set(data.slots.map(s=>s.thesis_id));
 const options=data.eligible.filter(t=>t.round_id===council?.round_id&&t.department_id===council?.department_id&&!taken.has(t.id)&&!council?.members.some(m=>t.advisor_ids?.includes(m.id)));
 const pending=(data.planning_theses??[]).filter(t=>t.round_id===council?.round_id&&t.department_id===council?.department_id&&t.schedule_reason&&!taken.has(t.id));
 const conflicts=data.eligible.filter(t=>t.round_id===council?.round_id&&t.department_id===council?.department_id&&!taken.has(t.id)&&council?.members.some(m=>t.advisor_ids?.includes(m.id)));
 const time=(index:number,end=false)=>start?new Date(Date.parse(start+":00+07:00")+(index*(duration+gap)+(end?duration:0))*60000).toISOString():"";
 const display=(value:string)=>value?new Date(value).toLocaleString("vi-VN",{timeZone:"Asia/Ho_Chi_Minh"}):"Chọn giờ bắt đầu";
 function move(index:number,offset:number){setSelected(current=>{const next=[...current];[next[index],next[index+offset]]=[next[index+offset],next[index]];return next;});}
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();const f=new FormData(e.currentTarget);await save({slots:selected.map((id,i)=>({council_id:councilId,thesis_id:id,starts_at:time(i),ends_at:time(i,true),arrival_at:sharedArrival?(arrival||start)+":00+07:00":time(i),room:String(f.get("room")),confirmed_no_conflict:f.has("conflict")}))});}
 return <form className="defense-schedule-form" onChange={e=>{e.currentTarget.dataset.dirty="true";}} onSubmit={async e=>{const form=e.currentTarget;form.dataset.submitting="true";try{await submit(e);}finally{form.removeAttribute("data-submitting");}}}>
  <p>Một hội đồng có thể chấm một hoặc nhiều đề tài. Chọn các đề tài theo thứ tự, hệ thống chia giờ liên tiếp trong cùng phòng; mỗi đề tài vẫn có điểm và biên bản riêng.</p>
  <label className="defense-wide">Hội đồng<select className="input" value={councilId} required onChange={e=>{setCouncil(e.target.value);setSelected([]);}}><option value="">Chọn hội đồng</option>{data.councils.filter(c=>c.can_manage&&!c.closed_at).map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
  <fieldset className="defense-planning"><legend>Đề tài đủ điều kiện · chọn tối đa 30</legend>
   {options.length>0&&<button type="button" className="btn btn-secondary" onClick={()=>setSelected(selected.length?[]:options.slice(0,30).map(t=>t.id))}>{selected.length?"Bỏ chọn tất cả":"Chọn tất cả"}</button>}
   {!options.length&&<p>{council?"Chưa có đề tài đủ điều kiện trong phạm vi hội đồng.":"Chọn hội đồng trước."}</p>}
   {options.map(t=><label className="defense-check" key={t.id}><input type="checkbox" checked={selected.includes(t.id)} disabled={!selected.includes(t.id)&&selected.length>=30} onChange={e=>setSelected(ids=>e.target.checked?[...ids,t.id]:ids.filter(id=>id!==t.id))}/>{t.title}</label>)}
  </fieldset>
  <details className="defense-wide"><summary>Vì sao đề tài chưa có trong danh sách?</summary><p>Cùng đợt và bộ môn; mọi SV đã đủ điều kiện trên đúng báo cáo, đủ Mẫu 8 của các phản biện đang được giao (nếu có), chưa có lịch và không có GVHD trong hội đồng. Khi lưu, hệ thống kiểm tra tiếp trùng giờ, phòng, giảng viên và hạn gia hạn.</p>
  {conflicts.map(t=><p key={t.id}><strong>{t.title}</strong> · GVHD đang có trong thành phần hội đồng; cần chọn hội đồng phù hợp khác.</p>)}
  {pending.map(t=><p key={t.id}><strong>{t.title}</strong> · {t.schedule_reason} {t.can_review_eligibility&&<a href={`/evaluation/${t.id}`}>Mở xét điều kiện</a>}</p>)}</details>
  <label>Bắt đầu (giờ Việt Nam)<input className="input" type="datetime-local" value={start} onChange={e=>setStart(e.target.value)} required/></label>
  <label>Phòng bảo vệ<input className="input" name="room" minLength={2} maxLength={200} required/></label>
  <label className="defense-check defense-wide"><input type="checkbox" checked={sharedArrival} onChange={e=>setSharedArrival(e.target.checked)}/>Áp dụng cùng giờ tập trung và phòng cho tất cả đề tài đã chọn</label>
  {sharedArrival&&<label className="defense-wide">Giờ tập trung chung (giờ Việt Nam)<input className="input" type="datetime-local" value={arrival||start} max={start||undefined} onChange={e=>setArrival(e.target.value)} required/><small>Ví dụ SV cùng tập trung lúc 07:00, bảo vệ lần lượt từ 07:30. Bỏ chọn để mỗi đề tài tập trung theo giờ bảo vệ dự kiến.</small></label>}
  <label>Thời lượng mỗi đề tài (phút)<input className="input" type="number" min={5} max={240} value={duration} required onChange={e=>setDuration(Number(e.target.value))}/></label>
  <label>Nghỉ giữa hai đề tài (phút)<input className="input" type="number" min={0} max={120} value={gap} required onChange={e=>setGap(Number(e.target.value))}/></label>
  {selected.length>0&&<section className="defense-wide"><h4>Xem lịch dự kiến · {selected.length} đề tài</h4><ol className="defense-schedule-order">{selected.map((id,i)=><li key={id}><strong>{options.find(t=>t.id===id)?.title}</strong><span>{display(time(i))} → {display(time(i,true))}</span><div className="button-row"><button type="button" className="btn btn-secondary" aria-label={`Chuyển lên đề tài ${i+1}`} disabled={i===0} onClick={()=>move(i,-1)}>↑</button><button type="button" className="btn btn-secondary" aria-label={`Chuyển xuống đề tài ${i+1}`} disabled={i===selected.length-1} onClick={()=>move(i,1)}>↓</button></div></li>)}</ol></section>}
  <label className="defense-check defense-wide"><input type="checkbox" name="conflict" required/>Đã đối chiếu không có quan hệ thân nhân với SV của các đề tài đã chọn.</label>
  <button className="btn btn-primary" disabled={busy||!selected.length}>Lưu lịch cho {selected.length} đề tài</button>
 </form>;
}
