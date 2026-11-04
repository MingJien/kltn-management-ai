import {useEffect,useState,type FormEvent} from "react";
import {request} from "../../api";
import {errorMessage} from "../../errors";

type Report={title:string;version_id:string;version_no:number};
type Result={
  text_matches:{left:string;right:string;left_kind:string;right_kind:string;left_excerpt:string;right_excerpt:string;common_phrases:number;example:string}[];
  image_matches:{left:string;right:string;distance:number;exact:boolean}[];
  coverage:{images_seen:number;images_ocr:number;warnings:string[]}[];
};

export default function ReportSimilarity({userId}:{userId:string}) {
  const [reports,setReports]=useState<Report[]>();
  const [left,setLeft]=useState("");
  const [right,setRight]=useState("");
  const [result,setResult]=useState<Result>();
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  useEffect(()=>{
    let active=true;
    void request<Report[]>("/ai/reports",userId).then(rows=>{if(active)setReports(rows);})
      .catch(e=>{if(active)setError(errorMessage(e));});
    return ()=>{active=false;};
  },[userId]);
  async function submit(e:FormEvent) {
    e.preventDefault();setBusy(true);setError("");setResult(undefined);
    try {
      const query=new URLSearchParams({left_version_id:left,right_version_id:right});
      setResult(await request<Result>("/ai/compare-reports?"+query,userId,{method:"POST"}));
    } catch(e){setError(errorMessage(e));}
    finally{setBusy(false);}
  }
  function options(excluded:string) {
    return <><option value="">Chọn báo cáo</option>{reports?.filter(r=>r.version_id!==excluded).map(r=>
      <option value={r.version_id} key={r.version_id}>{r.title} · phiên bản {r.version_no}</option>)}</>;
  }
  return <section className="card"><div className="card-body stack">
    <p>Đối chiếu hai báo cáo bằng văn bản, chữ nhận dạng trong ảnh và dấu hiệu ảnh giống nhau. Dùng các vị trí trùng để kiểm tra thủ công.</p>
    {error&&<p role="alert" className="alert alert-danger">{error}</p>}
    {!reports&&!error&&<p role="status">Đang tải danh sách báo cáo…</p>}
    {reports&&reports.length<2&&<p>Cần ít nhất hai báo cáo Word/PDF đã qua kiểm tra tệp trong phạm vi được giao.</p>}
    {!!reports&&reports.length>=2&&<form className="stack" onSubmit={submit}>
      <label>Đề tài thứ nhất<select className="input" value={left} disabled={busy} required onChange={e=>{setLeft(e.target.value);setResult(undefined);}}>{options(right)}</select></label>
      <label>Đề tài thứ hai<select className="input" value={right} disabled={busy} required onChange={e=>{setRight(e.target.value);setResult(undefined);}}>{options(left)}</select></label>
      <button className="btn btn-primary" disabled={busy||!left||!right}>{busy?"Đang đọc và đối chiếu…":"Đối chiếu báo cáo"}</button>
    </form>}
    {result&&<>
      <h3>Phạm vi đọc</h3>
      {result.coverage.map((c,i)=><div key={i}><p>Báo cáo {i+1} · OCR {c.images_ocr}/{c.images_seen} ảnh</p>
        {!!c.warnings.length&&<ul>{c.warnings.map(w=><li key={w}>{w}</li>)}</ul>}
      </div>)}
      <h3>Đoạn chữ tương đồng</h3>
      {!result.text_matches.length&&<p>Chưa thấy đoạn chữ trùng đáng chú ý trong phần đã đọc.</p>}
      {result.text_matches.map((m,i)=><article key={i}><strong>{m.left} ↔ {m.right} · {m.common_phrases} cụm trùng</strong>
        <p>Cụm tìm thấy · “{m.example}”</p>
        <p>{m.left_kind==="OCR"?"Chữ từ ảnh · ":""}{m.left_excerpt}</p>
        <p>{m.right_kind==="OCR"?"Chữ từ ảnh · ":""}{m.right_excerpt}</p>
      </article>)}
      <h3>Ảnh có dấu hiệu giống nhau</h3>
      {!result.image_matches.length&&<p>Chưa thấy cặp ảnh gần giống trong phần đã đọc.</p>}
      {!!result.image_matches.length&&<ul>{result.image_matches.map((m,i)=><li key={i}>{m.left} ↔ {m.right} · {m.exact?"Tệp ảnh trùng":"Ảnh gần giống"}</li>)}</ul>}
    </>}
  </div></section>;
}
