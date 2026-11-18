import {useEffect,useRef,useState} from "react";
import {downloadFile,request} from "../../api";
import {errorMessage} from "../../errors";
import {ReadOnlyFilePreview} from "./ReviewAttachmentPreview";
import {protectNarratives,type Narrative,type FieldStyle,type LayoutState} from "./ProtectedPrintLayout";
import "../../styles/review-workspace.css";

type Cell={text:string;rowspan:number;colspan:number;bold:boolean;italic:boolean;size:number;color?:string;rule_below?:boolean;align:"left"|"center"|"right";segments?:{text:string;bold:boolean;italic:boolean}[]};
type Sheet={name:string;rows:Cell[][];widths?:number[];row_heights?:(number|null)[];truncated?:boolean};
const empty=():LayoutState=>({breaks:{},tabs:{},styles:{}});
export default function DefensePrintPreview({endpoint,name,label,record=false,onRecord}:{endpoint:string;name:string;label:string;record?:boolean;onRecord?:()=>void}) {
 const [layout,setLayout]=useState<LayoutState>(empty),current=useRef(layout);current.current=layout;
 const [active,setActive]=useState(""),[revision,setRevision]=useState(""),[sheets,setSheets]=useState<Sheet[]>([]),[fields,setFields]=useState<Narrative[]>([]),[selected,setSelected]=useState(""),[hint,setHint]=useState("");
 const [wordReady,setWordReady]=useState(false),[attempt,setAttempt]=useState(0);
 const [error,setError]=useState(""),[busy,setBusy]=useState(false);const pane=useRef<HTMLDivElement>(null),wordRoot=useRef<ShadowRoot|null>(null);
 const isWord=name.endsWith(".docx"),hasNarrative=/\/forms\/(6|9)(\?|$)/.test(endpoint);
 const query=new URLSearchParams();
 if(Object.keys(layout.breaks).length)query.set("line_breaks",JSON.stringify(layout.breaks));
 if(Object.keys(layout.tabs).length)query.set("tabs",JSON.stringify(layout.tabs));
 if(Object.keys(layout.styles).length)query.set("field_styles",JSON.stringify(layout.styles));
 const path=endpoint+(endpoint.includes("?")?"&":"?")+query.toString();
 function spacing(key:string,kind:"breaks"|"tabs",positions:number[]){const next={...current.current,[kind]:{...current.current[kind],[key]:positions}};current.current=next;setLayout(next);}
 function decorate(root:ShadowRoot|HTMLElement){protectNarratives(root,fields,()=>current.current,spacing,setSelected,setHint);}
 useEffect(()=>{if(pane.current&&sheets.length)decorate(pane.current);},[sheets,fields]);
 function style(change:FieldStyle){if(!selected)return;const next={...current.current,styles:{...current.current.styles,[selected]:{...current.current.styles[selected],...change}}};current.current=next;setLayout(next);
  for(const root of [pane.current,wordRoot.current])for(const span of root?.querySelectorAll<HTMLElement>("[data-print-field]")??[]){if(span.dataset.printField!==selected)continue;const s=next.styles[selected];if(s.bold!==undefined)span.style.fontWeight=s.bold?"700":"400";if(s.italic!==undefined)span.style.fontStyle=s.italic?"italic":"normal";if(s.font_size)span.style.fontSize=s.font_size+"pt";if(s.line_spacing)span.style.lineHeight=String(s.line_spacing);if(s.alignment&&span.closest("p"))span.closest("p")!.style.textAlign=s.alignment;if(s.space_after!==undefined&&span.closest("p"))span.closest("p")!.style.marginBottom=s.space_after+"pt";}
 }
 async function preview(){setBusy(true);setError("");setRevision("");setActive("");setWordReady(false);try{
  if(hasNarrative){const result=await request<{fields:Narrative[]}>(endpoint+(endpoint.includes("?")?"&":"?")+"layout_fields=true","");setFields(result.fields);}
  const source=await request<{revision:string}>(path+"&preview_revision=true","");
  if(!isWord)setSheets((await request<{sheets:Sheet[]}>(path+"&expected_revision="+encodeURIComponent(source.revision)+"&preview_sheet=true","")).sheets);
  setAttempt(value=>value+1);setActive(path);setRevision(source.revision);
 }catch(e){setError(errorMessage(e));}finally{setBusy(false);}}
 const selectedStyle=layout.styles[selected]??{};
 return <details className="defense-operation defense-print"><summary>Xem trước & định dạng · {label}</summary>
  <p>{hasNarrative?"Mở bản xem theo mẫu gốc. Thư ký chọn phần diễn giải ngay trên bản xem để chỉnh trình bày; nội dung, thông tin và điểm được giữ nguyên.":"Đối chiếu bảng toàn đợt theo mẫu gốc trước khi lưu và tải."}</p>
  <div className="button-row"><button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void preview()}>Áp dụng & xem trước</button>
   <button type="button" className="btn btn-primary" disabled={busy||!revision||active!==path||(isWord&&!wordReady)} onClick={async()=>{setBusy(true);setError("");try{await downloadFile(path+"&expected_revision="+encodeURIComponent(revision),name,record?"POST":"GET");if(record)onRecord?.();}catch(e){setRevision("");setError(errorMessage(e));}finally{setBusy(false);}}}>{record?"Lưu và tải bản dùng để ký":"Tải bản theo định dạng đã chọn"}</button>
   <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>{current.current=empty();setLayout(current.current);setActive("");setRevision("");setWordReady(false);setSheets([]);setSelected("");setHint("");}}>Khôi phục định dạng mẫu</button></div>
  {error&&<p role="alert" className="alert alert-danger">{error}</p>}
  {active&&hasNarrative&&<div className="review-toolbar defense-layout-toolbar" role="toolbar" aria-label="Định dạng bản xuất">
   <span>{fields.find(f=>f.key===selected)?.label??"Bấm phần diễn giải có khung để định dạng"}</span>
   <button type="button" className="btn btn-secondary" aria-pressed={!!selectedStyle.bold} disabled={!selected} onClick={()=>style({bold:!selectedStyle.bold})}>Đậm</button>
   <button type="button" className="btn btn-secondary" aria-pressed={!!selectedStyle.italic} disabled={!selected} onClick={()=>style({italic:!selectedStyle.italic})}>Nghiêng</button>
   <label>Cỡ chữ<select className="input" disabled={!selected} value={selectedStyle.font_size??""} onChange={e=>style({font_size:Number(e.target.value)})}><option value="" disabled>Theo mẫu</option>{[10,11,12,13,14].map(n=><option key={n} value={n}>{n}</option>)}</select></label>
   {isWord&&<label>Giãn dòng<select className="input" disabled={!selected} value={selectedStyle.line_spacing??""} onChange={e=>style({line_spacing:Number(e.target.value)})}><option value="" disabled>Theo mẫu</option>{[1,1.15,1.3,1.5].map(n=><option key={n}>{n}</option>)}</select></label>}
   {isWord&&<><label>Căn đoạn<select className="input" disabled={!selected} value={selectedStyle.alignment??""} onChange={e=>style({alignment:e.target.value as FieldStyle['alignment']})}><option value="" disabled>Theo mẫu</option><option value="left">Trái</option><option value="center">Giữa</option><option value="right">Phải</option><option value="justify">Đều hai bên</option></select></label><label>Cách sau đoạn<select className="input" disabled={!selected} value={selectedStyle.space_after??""} onChange={e=>style({space_after:Number(e.target.value)})}><option value="" disabled>Theo mẫu</option>{[0,3,6,8].map(n=><option key={n} value={n}>{n} pt</option>)}</select></label></>}
   <small>Enter: xuống dòng · Tab: thêm khoảng tab · Backspace/Delete: gỡ khoảng vừa thêm. Shift+Tab: rời ô.</small>
  </div>}
  {hint&&<p role="status">{hint}</p>}
  {active&&active!==path&&<p role="status">Trình bày đã đổi. Bấm “Áp dụng & xem trước” để cập nhật tệp trước khi tải.</p>}
  {active&&<><p className="text-muted">Kiểm tra phân trang và vùng ký trong Word/Excel trước khi in.</p>
   {isWord?<ReadOnlyFilePreview key={attempt} name={name} endpoint={active+"&expected_revision="+encodeURIComponent(revision)} onBack={()=>setActive("")} label={label} backLabel="Đóng bản xem" caption="Bản điền từ biểu mẫu gốc của Khoa." onDocumentReady={root=>{wordRoot.current=root;decorate(root);setWordReady(true);}}/>
   :<div ref={pane}>{sheets.map(s=><section key={s.name}><h5>{s.name}</h5>{s.truncated&&<p>Bản xem giới hạn 1.000 dòng và 30 cột. Tải tệp để xem toàn bộ.</p>}<div className="defense-sheet-preview" role="region" tabIndex={0} aria-label={`Bản xem ${label} · ${s.name}`}><table aria-label={label}><colgroup>{s.widths?.map((w,i)=><col key={i} style={{width:w}}/>)}</colgroup><tbody>{s.rows.map((r,i)=><tr key={i} style={{height:s.row_heights?.[i]?s.row_heights[i]+"pt":undefined}}>{r.map((c,j)=><td key={j} rowSpan={c.rowspan} colSpan={c.colspan} style={{fontWeight:c.bold?700:400,fontStyle:c.italic?"italic":"normal",fontSize:c.size+"pt",textAlign:c.align,color:c.color}}>{c.segments?c.segments.map((part,k)=><span key={k} style={{fontWeight:part.bold?700:400,fontStyle:part.italic?"italic":"normal"}}>{part.text}</span>):c.text}{c.rule_below&&<span className="defense-template-rule" aria-hidden="true"/>}</td>)}</tr>)}</tbody></table></div></section>)}</div>}</>}
 </details>;
}
