import {useRef,useState} from "react";
import {request} from "../../api";
import {downloadEvaluationFile} from "../../evaluation";
import {errorMessage} from "../../errors";
import {ReadOnlyFilePreview} from "./ReviewAttachmentPreview";
import "../../styles/review-workspace.css";

type Cell={text:string;rowspan:number;colspan:number;bold:boolean;italic:boolean;size:number;color?:string;align:"left"|"center"|"right"};
type Sheet={name:string;rows:Cell[][];widths?:number[];truncated?:boolean};
type Narrative={key:string;label:string;text:string};

function BreakEditor({field,positions,onChange}:{field:Narrative;positions:number[];onChange:(positions:number[])=>void}) {
  const [hint,setHint]=useState("");
  const input=useRef<HTMLTextAreaElement>(null);
  const chars=Array.from(field.text),boundaries:{offset:number;index:number}[]=[],insertions:{offset:number;index:number}[]=[];
  let displayed="";
  for(let i=0;i<=chars.length;i++){
    boundaries.push({offset:displayed.length,index:i});
    if(positions.includes(i)){insertions.push({offset:displayed.length,index:i});displayed+="\n";boundaries.push({offset:displayed.length,index:i});}
    if(i<chars.length)displayed+=chars[i];
  }
  return <div className="stack"><label>Ngắt dòng · {field.label}
    <textarea ref={input} className="input" value={displayed} readOnly rows={4} disabled={!field.text} style={{resize:"vertical"}}
      placeholder="Chưa có nội dung đã lưu để định dạng" onPaste={e=>e.preventDefault()} onKeyDown={e=>{
        const cursor=e.currentTarget.selectionStart;
        if(e.key==="Enter"){
          e.preventDefault();
          const index=boundaries.filter(b=>b.offset<=cursor).at(-1)?.index??0;
          if(positions.includes(index))return;
          if(positions.length>=20){setHint("Tối đa 20 vị trí ngắt dòng cho một phần.");return;}
          if(index>0&&index<chars.length&&!/\s/.test(chars[index-1])&&!/\s/.test(chars[index])){setHint("Đặt con trỏ giữa các từ để ngắt dòng.");return;}
          onChange([...positions,index].sort((a,b)=>a-b));setHint("");
          requestAnimationFrame(()=>input.current?.setSelectionRange(cursor+1,cursor+1));
        }else if(e.key==="Backspace"||e.key==="Delete"){
          e.preventDefault();
          const found=insertions.find(p=>p.offset===(e.key==="Backspace"?cursor-1:cursor));
          if(found){onChange(positions.filter(p=>p!==found.index));requestAnimationFrame(()=>input.current?.setSelectionRange(Math.max(0,cursor-(e.key==="Backspace"?1:0)),Math.max(0,cursor-(e.key==="Backspace"?1:0))));}
        }
      }}/></label>
    {hint&&<small role="status">{hint}</small>}
    <button type="button" className="btn btn-secondary" disabled={!positions.length} onClick={()=>onChange([])}>Xóa ngắt dòng đã thêm · {field.label}</button>
  </div>;
}
/** Format-only controls: the server supplies all document content and results. */
export default function DefensePrintPreview({endpoint,name,label}:{endpoint:string;name:string;label:string}) {
  const [font,setFont]=useState(""),[spacing,setSpacing]=useState(""),[space,setSpace]=useState("");
  const [breakPage,setBreakPage]=useState(false),[active,setActive]=useState<string|null>(null);
  const [sheets,setSheets]=useState<Sheet[]>([]),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const isWord=name.endsWith(".docx");
  const hasNarrative=/\/forms\/(6|9)(\?|$)/.test(endpoint);
  const [fields,setFields]=useState<Narrative[]>([]),[breaks,setBreaks]=useState<Record<string,number[]>>({});
  const [bold,setBold]=useState(""),[italic,setItalic]=useState("");
  const query=new URLSearchParams();
  if(font)query.set("font_size",font);
  if(spacing)query.set("line_spacing",spacing);
  if(space)query.set("paragraph_space",space);
  if(breakPage)query.set("break_recommendations","true");
  if(bold)query.set("narrative_bold",bold);
  if(italic)query.set("narrative_italic",italic);
  if(Object.keys(breaks).length)query.set("line_breaks",JSON.stringify(breaks));
  const path=endpoint+(endpoint.includes("?")?"&":"?")+query.toString();
  async function preview(){
    setError("");setBusy(true);
    try{
      if(!isWord)setSheets((await request<{sheets:Sheet[]}>(path+"&preview_sheet=true","")).sheets);
      setActive(path);
    }catch(e){setError(errorMessage(e));}finally{setBusy(false);}
  }
  return <details className="defense-operation defense-print"><summary>Xem trước & định dạng · {label}</summary>
    <p>Nội dung, điểm và kết quả chỉ đọc. Định dạng áp dụng riêng cho lần xuất này; mẫu gốc được giữ nguyên khi chọn “Theo mẫu”.</p>
    <div className="defense-form-grid">
      <label>Cỡ chữ<select className="input" value={font} onChange={e=>setFont(e.target.value)}><option value="">Theo mẫu</option>{[11,12,13,14].map(n=><option key={n}>{n}</option>)}</select></label>
      {isWord&&<><label>Giãn dòng<select className="input" value={spacing} onChange={e=>setSpacing(e.target.value)}><option value="">Theo mẫu</option>{[1,1.15,1.3,1.5].map(n=><option key={n}>{n}</option>)}</select></label>
        <label>Cách sau đoạn<select className="input" value={space} onChange={e=>setSpace(e.target.value)}><option value="">Theo mẫu</option>{[0,3,6,8].map(n=><option key={n} value={n}>{n} pt</option>)}</select></label></>}
    </div>
    {hasNarrative&&<details><summary>Ngắt dòng và định dạng phần diễn giải</summary>
      <p>Đặt con trỏ rồi nhấn Enter để thêm ngắt dòng; Backspace/Delete chỉ bỏ ngắt dòng vừa thêm. Chữ gốc và các giá trị điểm không sửa được tại đây.</p>
      <div className="defense-form-grid">{[["Chữ đậm",bold,setBold],["Chữ nghiêng",italic,setItalic]].map(([label,value,setValue])=><label key={String(label)}>{String(label)} phần diễn giải<select className="input" value={String(value)} onChange={e=>(setValue as (value:string)=>void)(e.target.value)}><option value="">Theo mẫu</option><option value="true">Bật</option><option value="false">Tắt</option></select></label>)}</div>
      <button type="button" className="btn btn-secondary" disabled={busy} onClick={async()=>{setBusy(true);setError("");try{const result=await request<{fields:Narrative[]}>(endpoint+(endpoint.includes("?")?"&":"?")+"layout_fields=true","");setFields(result.fields);setBreaks({});}catch(e){setError(errorMessage(e));}finally{setBusy(false);}}}>Tải nội dung chỉ đọc để ngắt dòng</button>
      {fields.map(field=><BreakEditor key={field.key} field={field} positions={breaks[field.key]??[]} onChange={positions=>setBreaks(current=>{const next={...current};if(positions.length)next[field.key]=positions;else delete next[field.key];return next;})}/>)}
    </details>}
    {isWord&&hasNarrative&&<label className="defense-check"><input type="checkbox" checked={breakPage} onChange={e=>setBreakPage(e.target.checked)}/>Chuyển phần kết quả, kiến nghị và ký tên sang trang mới</label>}
    <div className="button-row"><button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void preview()}>Áp dụng & xem trước</button>
      <button type="button" className="btn btn-primary" disabled={busy} onClick={async()=>{setError("");setBusy(true);try{await downloadEvaluationFile(path,name);}catch(e){setError(errorMessage(e));}finally{setBusy(false);}}}>Tải bản theo định dạng đã chọn</button>
      <button type="button" className="btn btn-secondary" onClick={()=>{setFont("");setSpacing("");setSpace("");setBreakPage(false);setBold("");setItalic("");setBreaks({});setFields([]);setActive(null);setSheets([]);}}>Khôi phục định dạng mẫu</button></div>
    {error&&<p role="alert" className="alert alert-danger">{error}</p>}
    {active&&active!==path&&<p role="status">Định dạng đã đổi. Bấm “Áp dụng & xem trước” để cập nhật bản xem.</p>}
    {active&&<><p className="text-body-sm text-muted">Bản xem trên trình duyệt có thể ngắt trang khác Word/Excel. Kiểm tra Print Preview trong ứng dụng trước khi in ký. Mã bố trí được ghi ở chân trang.</p>
      {isWord?<ReadOnlyFilePreview name={name} endpoint={active} onBack={()=>setActive(null)} label={label} backLabel="Đóng bản xem" caption="Dữ liệu lấy từ hồ sơ đã lưu, không sửa nội dung tại đây."/>
        :sheets.map(s=><section key={s.name}><h5>{s.name}</h5>{s.truncated&&<p>Bản xem giới hạn 1.000 dòng và 30 cột. Tải tệp để xem toàn bộ dữ liệu.</p>}<div className="defense-sheet-preview" tabIndex={0} role="region" aria-label={`Bản xem ${label} · ${s.name}`}><table aria-label={label}><colgroup>{s.widths?.map((w,i)=><col key={i} style={{width:w}}/>)}</colgroup><tbody>{s.rows.map((r,i)=><tr key={i}>{r.map((c,j)=><td key={j} rowSpan={c.rowspan} colSpan={c.colspan} style={{fontWeight:c.bold?700:400,fontStyle:c.italic?"italic":"normal",fontSize:Math.min(c.size,18)+"pt",textAlign:c.align,color:c.color}}>{c.text}</td>)}</tr>)}</tbody></table></div></section>)}</>}
  </details>;
}
