export type Narrative={key:string;label:string;text:string};
export type FieldStyle={bold?:boolean;italic?:boolean;font_size?:number;line_spacing?:number};
export type LayoutState={breaks:Record<string,number[]>;tabs:Record<string,number[]>;styles:Record<string,FieldStyle>};
export function displayNarrative(text:string,key:string,state:LayoutState) {
 const characters=Array.from(text);let result="";
 for(let i=0;i<=characters.length;i++){if(state.breaks[key]?.includes(i))result+="\n";if(state.tabs[key]?.includes(i))result+="\t";if(i<characters.length)result+=characters[i];}return result;
}
/** Decorate source-owned text inside the actual document. Only spacing events leave the browser. */
export function protectNarratives(root:ShadowRoot|HTMLElement,fields:Narrative[],state:()=>LayoutState,change:(key:string,kind:"breaks"|"tabs",positions:number[])=>void,select:(key:string)=>void,hint:(text:string)=>void) {
 for(const field of fields.filter(f=>f.text)){
  const displayed=displayNarrative(field.text,field.key,state());
  const needle=displayed.replace(/[\n\t]/g,"");
  const blocks=Array.from(root.querySelectorAll<HTMLElement>("p,td")).filter(p=>!p.querySelector("[data-print-field]")&&p.textContent?.replace(/[\n\t]/g,"").includes(needle));
  const block=blocks.find(b=>!Array.from(b.querySelectorAll("p,td")).some(child=>child.textContent?.replace(/[\n\t]/g,"").includes(needle)));
  if(!block||!needle)continue;
  // Map visible source text to DOM text offsets, keeping the template's labels and runs around it.
  const walker=document.createTreeWalker(block,NodeFilter.SHOW_TEXT),nodes:Text[]=[];let node:Node|null;
  while((node=walker.nextNode()))nodes.push(node as Text);
  const chars:{node:Text;offset:number}[]=[];let flat="";
  for(const n of nodes)for(let i=0;i<n.data.length;i++)if(!/[\n\t]/.test(n.data[i])){flat+=n.data[i];chars.push({node:n,offset:i});}
  const start=flat.indexOf(needle);if(start<0)continue;
  const end=chars[start+needle.length-1],first=chars[start];if(!end||!first)continue;
  const range=document.createRange();range.setStart(first.node,first.offset);range.setEnd(end.node,end.offset+1);
  const span=document.createElement("span");span.dataset.printField=field.key;span.contentEditable="true";span.spellcheck=false;span.setAttribute("role","textbox");span.setAttribute("aria-label",`Định dạng ${field.label}`);span.style.cssText="white-space:pre-wrap;outline:1px dashed #0f766e;cursor:text;tab-size:4";
  const initial=state().styles[field.key];if(initial?.bold!==undefined)span.style.fontWeight=initial.bold?"700":"400";if(initial?.italic!==undefined)span.style.fontStyle=initial.italic?"italic":"normal";if(initial?.font_size)span.style.fontSize=initial.font_size+"pt";if(initial?.line_spacing)span.style.lineHeight=String(initial.line_spacing);
  span.textContent=displayed;range.deleteContents();range.insertNode(span);
  span.onfocus=()=>select(field.key);
  span.onbeforeinput=e=>e.preventDefault();span.onpaste=e=>e.preventDefault();span.ondrop=e=>e.preventDefault();span.oncut=e=>e.preventDefault();
  span.oninput=()=>{span.textContent=displayNarrative(field.text,field.key,state());hint("Nội dung gốc được bảo vệ; chỉ chỉnh trình bày bằng thanh công cụ, Enter hoặc Tab.");};
  span.onkeydown=e=>{
   if(e.key==="Tab"&&e.shiftKey)return;
   if(["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","Home","End","Shift","Control","Meta","Escape"].includes(e.key)||(e.ctrlKey||e.metaKey)&&["a","c"].includes(e.key.toLowerCase()))return;
   e.preventDefault();if(!["Enter","Tab","Backspace","Delete"].includes(e.key))return;
   const selection=(root as ShadowRoot & {getSelection?:()=>Selection|null}).getSelection?.()??window.getSelection();
   if(!selection?.rangeCount||!span.contains(selection.anchorNode))return;
   const before=selection.getRangeAt(0).cloneRange();before.selectNodeContents(span);before.setEnd(selection.anchorNode!,selection.anchorOffset);const cursor=before.toString().length;
   let shown="";const boundaries:{offset:number;index:number}[]=[],insertions:{offset:number;index:number;kind:"breaks"|"tabs"}[]=[];
   const current=state();const original=Array.from(field.text);
   for(let i=0;i<=original.length;i++){
    boundaries.push({offset:shown.length,index:i});
    for(const kind of ["breaks","tabs"] as const)if(current[kind][field.key]?.includes(i)){insertions.push({offset:shown.length,index:i,kind});shown+=kind==="breaks"?"\n":"\t";boundaries.push({offset:shown.length,index:i});}
    if(i<original.length)shown+=original[i];
   }
   let nextCursor=cursor;
   if(e.key==="Enter"||e.key==="Tab"){
    const index=boundaries.filter(b=>b.offset<=cursor).at(-1)?.index??0,kind=e.key==="Enter"?"breaks":"tabs",positions=current[kind][field.key]??[];
    if(positions.includes(index)||positions.length>=20)return;
    if(index>0&&index<original.length&&!/\s/.test(original[index-1])&&!/\s/.test(original[index])){hint("Đặt con trỏ giữa các từ để xuống dòng hoặc thêm tab.");return;}
    change(field.key,kind,[...positions,index].sort((a,b)=>a-b));nextCursor++;
   }else{
    const found=insertions.find(p=>p.offset===(e.key==="Backspace"?cursor-1:cursor));if(!found){hint("Chỉ gỡ được dòng/tab đã thêm; nội dung gốc được bảo vệ.");return;}
    change(field.key,found.kind,(current[found.kind][field.key]??[]).filter(p=>p!==found.index));if(e.key==="Backspace")nextCursor--;
   }
   span.textContent=displayNarrative(field.text,field.key,state());const caret=document.createRange();caret.setStart(span.firstChild??span,Math.min(nextCursor,span.textContent.length));caret.collapse(true);selection.removeAllRanges();selection.addRange(caret);hint("Đã chỉnh trình bày. Áp dụng xem trước để kiểm tra bản xuất.");
  };
 }
}
