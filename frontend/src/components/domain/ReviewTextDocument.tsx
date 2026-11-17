import { useEffect, useRef, useState } from "react";
import { parseAsync, renderDocument } from "docx-preview";
import DOMPurify from "dompurify";
import type { ProgressAnnotation } from "../../api";
import ReviewCommentText from "./ReviewCommentText";

type WordNode = {type?:string; id?:string; text?:string; children?:WordNode[]};
type NativeWordComment = {id:string; author:string; text:string; quote:string};
const wordText = (node:WordNode): string => (node.text || "") + (node.children || []).map(wordText).join("") + (node.type === "paragraph" ? "\n" : "");

// Styles stay inside a shadow root: Word styles cannot alter the application UI.
function safeStyles(source: string) {
  const sheet = new CSSStyleSheet();
  sheet.replaceSync(source);
  const result: string[] = [];
  for (const rule of Array.from(sheet.cssRules)) {
    if (!(rule instanceof CSSStyleRule)) continue; // no imports, external fonts or other at-rules
    for (const property of Array.from(rule.style)) {
      const value = rule.style.getPropertyValue(property).replace(/\\([0-9a-f]{1,6})\s?|\\(.)/gi,
        (_, hex: string, literal: string) => hex ? String.fromCodePoint(Math.min(parseInt(hex, 16), 0x10ffff)) : literal);
      if (/url\s*\(|expression|@import/i.test(value) || /^(behavior|-moz-binding)$/.test(property) ||
        (property === "position" && /fixed|sticky/.test(value))) rule.style.removeProperty(property);
    }
    result.push(rule.cssText);
  }
  return result.join("\n");
}

const previewStyles = `
:host { display:block; color:#000; font-family:"Times New Roman",serif; font-size:12pt; line-height:normal; }
.review-word-wrapper { padding:12px !important; background:transparent !important; }
section.review-word { margin:0 auto 18px; flex-shrink:0; box-shadow:0 3px 18px #1c354018; }
[data-review-block] { position:relative; }
.review-block--selected { outline:2px solid #81c8b7; background-color:#e8f8ef !important; }
.pinning [data-review-block]:hover { outline:2px dashed #59a59a; cursor:crosshair; }
.review-text-pin { position:absolute; right:-25px; top:0; display:inline-flex; align-items:center; justify-content:center; width:23px; height:23px; padding:0; border:1px solid white; border-radius:50%; background:#117b70; color:white; cursor:pointer; font:600 11px system-ui; }
.review-text-pin:focus-visible { outline:3px solid #e4a331; }
.review-txt { white-space:pre-wrap; font:14px/1.7 ui-monospace,monospace; background:white; padding:28px; }
.review-txt p { min-height:1.7em; margin:0; padding-right:25px; overflow-wrap:anywhere; }
`;

/** Anchors use paragraphs/lines of an immutable version; DOCX page breaks may vary by renderer. */
export default function ReviewTextDocument({data, fileName, notes, selectedId, pinMode, canAnnotate, showEmbeddedReviews=false, onSelect, onPin, onRendered,onDocumentReady}: {
  data: ArrayBuffer; fileName: string; notes: ProgressAnnotation[]; selectedId: string; pinMode: boolean; canAnnotate: boolean; showEmbeddedReviews?:boolean;
  onSelect: (id: string) => void; onPin: (label: string, quote: string) => void; onRendered: () => void;
  onDocumentReady?: (root:ShadowRoot)=>void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [nativeComments,setNativeComments] = useState<NativeWordComment[]>([]);
  const rendered = useRef(onRendered); rendered.current = onRendered;
  const documentReady=useRef(onDocumentReady);documentReady.current=onDocumentReady;
  const selected = useRef(onSelect); selected.current = onSelect;
  const pin = useRef(onPin); pin.current = onPin;
  const mode = useRef({pinMode, canAnnotate}); mode.current = {pinMode, canAnnotate};
  const isDocx = /\.docx$/i.test(fileName);
  useEffect(() => {
    let active = true;
    setReady(false); setError(""); setNativeComments([]);
    const root = host.current!.shadowRoot || host.current!.attachShadow({mode:"open"});
    root.replaceChildren();
    const load = async () => {
      const container = document.createElement("div");
      const styles: string[] = [];
      const isText = /\.txt$/i.test(fileName);
      if (isText) {
        const text = new TextDecoder("utf-8", {fatal:true}).decode(data);
        if (text.length > 1_000_000 || text.split("\n").length > 10000) throw new Error("Tệp văn bản quá dài để xem trực tiếp; hãy tải bản gốc.");
        container.className = "review-txt";
        for (const line of text.split(/\r?\n/)) {
          const p = document.createElement("p"); p.textContent = line || "\u00a0"; container.append(p);
        }
      } else if (/\.docx$/i.test(fileName)) {
        const options = {className:"review-word", ignoreWidth:false, ignoreHeight:false, ignoreFonts:true,
          breakPages:true, renderAltChunks:false, renderComments:false, renderChanges:showEmbeddedReviews, useBase64URL:true};
        const word = await parseAsync(data.slice(0), options);
        if(showEmbeddedReviews) {
          const ranges=new Map<string,string>(),activeRanges=new Set<string>();
          const visit=(node:WordNode)=>{
            if(node.type === "commentRangeStart" && node.id) activeRanges.add(node.id);
            if(node.text) for(const id of activeRanges) ranges.set(id,((ranges.get(id)||"")+node.text).slice(0,1000));
            for(const child of node.children || []) visit(child);
            if(node.type === "commentRangeEnd" && node.id) activeRanges.delete(node.id);
          };
          visit(word.documentPart.body);
          const comments=(word.commentsPart?.comments || []).slice(0,100).map((comment:WordNode & {author?:string})=>({
            id:comment.id || "", author:comment.author || "Tác giả trong tệp", text:wordText(comment).slice(0,5000), quote:ranges.get(comment.id || "") || "",
          }));
          if(active) setNativeComments(comments);
        }
        for (const node of await renderDocument(word, options)) {
          if (node.nodeName === "STYLE") styles.push(safeStyles(node.textContent || ""));
          else container.append(node);
        }
        DOMPurify.sanitize(container, {IN_PLACE:true, FORBID_TAGS:["style","svg","math","iframe","object","embed","form","input","button"], FORBID_ATTR:["href","srcset","id","name"]});
        for (const image of container.querySelectorAll("img")) if (!/^data:image\/(png|jpe?g|gif|webp);base64,/i.test(image.src)) image.remove();
        for (const element of container.querySelectorAll<HTMLElement>("[style]")) {
          const safe = safeStyles(`.inline {${element.getAttribute("style")}}`);
          element.style.cssText = safe.slice(safe.indexOf("{") + 1, safe.lastIndexOf("}"));
        }
      } else throw new Error("Định dạng này chưa có bản xem trực tiếp. Hãy tải bản gốc.");
      const blocks = Array.from(container.querySelectorAll<HTMLElement>("p"))
        .filter(block => isText || block.textContent?.trim() || block.querySelector("img"));
      blocks.forEach((block,index) => {block.dataset.reviewBlock = `${isText ? "Dòng" : "Đoạn"} ${index + 1}`;});
      if (!active) return;
      const style = document.createElement("style"); style.textContent = styles.join("\n") + "\n" + previewStyles;
      root.replaceChildren(style, container); setReady(true);documentReady.current?.(root);
    };
    const point = (event: Event) => {
      const target = event.target as HTMLElement;
      if (!mode.current.canAnnotate || target.closest("button")) return;
      const block = target.closest<HTMLElement>("[data-review-block]");
      if (!block) return;
      const selection = (root as ShadowRoot & {getSelection?: () => Selection | null}).getSelection?.() || window.getSelection();
      const quote = selection?.anchorNode && root.contains(selection.anchorNode) && root.contains(selection.focusNode) ? selection.toString().trim() : "";
      if (!mode.current.pinMode && !quote) return;
      const copy = block.cloneNode(true) as HTMLElement;
      copy.querySelectorAll("button").forEach(button => button.remove());
      const start = quote && selection?.rangeCount ? selection.getRangeAt(0).startContainer : null;
      const startElement = start instanceof Element ? start : start?.parentElement;
      const anchor = startElement?.closest<HTMLElement>("[data-review-block]");
      pin.current((anchor && root.contains(anchor) ? anchor : block).dataset.reviewBlock!, (quote || copy.textContent || "").slice(0,1000));
      selection?.removeAllRanges();
    };
    root.addEventListener("pointerup", point);
    const fit = () => {
      if (!root.querySelector("[data-review-block]")) return;
      const page = root.querySelector<HTMLElement>("section.review-word");
      const body = root.querySelector<HTMLElement>("div");
      if (page && body && host.current) body.style.zoom = String(Math.min(1, Math.max(.2, (host.current.clientWidth - 24) / page.offsetWidth)));
      requestAnimationFrame(() => rendered.current());
    };
    const observer = new ResizeObserver(fit); observer.observe(host.current!);
    void load().then(() => {if (active) fit();}).catch(cause => {if (active) setError(`Không mở được bản xem: ${String(cause)}`);});
    return () => {active = false; observer.disconnect(); root.removeEventListener("pointerup",point);};
  }, [data,fileName,showEmbeddedReviews]);

  function blockFor(note: ProgressAnnotation) {
    const blocks = Array.from(host.current?.shadowRoot?.querySelectorAll<HTMLElement>("[data-review-block]") || []);
    const normalize = (value: string) => value.replace(/\s+/g," ").trim();
    const text = (block: HTMLElement) => {const copy = block.cloneNode(true) as HTMLElement; copy.querySelectorAll("button").forEach(pin => pin.remove()); return normalize(copy.textContent || "");};
    const quote = normalize(note.quoted_text);
    const label = blocks.find(block => block.dataset.reviewBlock === note.location_label);
    if (label && (!quote || text(label).includes(quote))) return label;
    const texts = blocks.map(text);
    const matches = quote ? blocks.filter((_,index) => texts[index].includes(quote)) : [];
    if (matches.length === 1) return matches[0];
    // A selection spanning several paragraphs must still point to its first paragraph.
    const combined = texts.join(" ");
    const start = quote ? combined.indexOf(quote) : -1;
    if (start < 0 || combined.indexOf(quote,start+1) >= 0) return null;
    let offset = 0;
    return blocks.find((_,index) => {const begins=offset; offset += texts[index].length+1; return start >= begins && start < offset;}) || null;
  }
  useEffect(() => {
    if (!ready || !host.current?.shadowRoot) return;
    for (const pin of host.current.shadowRoot.querySelectorAll("[data-note-id]")) pin.remove();
    notes.forEach((note,index) => {
      const block = blockFor(note); if (!block) return;
      const button = document.createElement("button"); button.type="button"; button.className="review-text-pin";
      button.dataset.noteId=note.id; button.textContent=String(index+1); button.ariaLabel=`Mở nhận xét ${index+1}`;
      button.addEventListener("click",event => {event.stopPropagation(); selected.current(note.id);}); block.append(button);
    });
    requestAnimationFrame(() => rendered.current());
  }, [notes,ready]);
  useEffect(() => {
    const root = host.current?.shadowRoot; if (!root || !ready) return;
    root.querySelector("div")?.classList.toggle("pinning",pinMode);
    root.querySelectorAll(".review-block--selected").forEach(block => block.classList.remove("review-block--selected"));
    const note = notes.find(note => note.id === selectedId);
    if (note) blockFor(note)?.classList.add("review-block--selected");
  }, [selectedId,notes,ready,pinMode]);
  return <div className="review-text-preview">
    <p className="review-format-hint">{isDocx ? "Giữ style, font/cỡ chữ và khổ trang từ DOCX; tự thu vừa khung. Dàn trang có thể khác Word nếu thiếu font hoặc có cấu trúc phức tạp. PDF giữ bố cục đã xuất." : "Tệp TXT không chứa định dạng font/cỡ chữ; nhận xét gắn theo dòng."}</p>
    {error && <p role="alert" className="review-error">{error}</p>}
    {showEmbeddedReviews && nativeComments.length > 0 && <details open className="review-native-comments"><summary>Nhận xét Word có trong tệp ({nativeComments.length})</summary>
      {nativeComments.map((comment,index)=><article key={`${comment.id}-${index}`}><strong>{comment.author}</strong>
        {comment.quote && <blockquote>{comment.quote}</blockquote>}<p><ReviewCommentText text={comment.text}/></p>
        {comment.quote && <button type="button" className="btn btn-secondary btn-sm" onClick={()=>{
          const blocks=Array.from(host.current?.shadowRoot?.querySelectorAll<HTMLElement>("[data-review-block]") || []);
          const block=blocks.find(block=>block.textContent?.includes(comment.quote));
          if(block){host.current?.shadowRoot?.querySelectorAll(".review-block--selected").forEach(item=>item.classList.remove("review-block--selected"));block.classList.add("review-block--selected");block.scrollIntoView({block:"center"});}
        }}>Tới đoạn được nhận xét</button>}
      </article>)}</details>}
    {!ready && !error && <p className="review-empty">Đang dựng bản xem trên máy của bạn…</p>}
    <div className={`review-text-sheet${isDocx ? " review-text-sheet--docx" : ""}`} ref={host} />
  </div>;
}
