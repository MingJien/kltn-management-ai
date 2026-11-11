import {useEffect, useState} from "react";
import {request, uploadDocument, downloadDocument} from "../../api";
import type {Thesis, ThesisDocument} from "../../api";
import type {CoreRun} from "./ThesisDocuments";

type Claim = {id:string;state:string;row_version:number;evidence_version_id:string;
  details:{title:string;venue:string;reference:string;contribution:string;student_ids:string[];points?:Record<string,string>;decision_reference?:string};
  history:{state:string;reason:string;actor:string;at:string}[]};
type Workspace = {items:Claim[];can_submit:boolean;can_review:boolean;can_approve:boolean};
const labels:Record<string,string> = {SUBMITTED:"Đã gửi · Chờ GVHD",ADVISOR_CONFIRMED:"GVHD xác nhận · Chờ TBM",APPROVED:"TBM đã duyệt",REJECTED:"Không được duyệt",REVISION_REQUIRED:"Cần bổ sung"};

export default function PublicationClaims({thesis,docs,userId,busy,run,canUpload}:{thesis:Thesis;docs:ThesisDocument[];userId:string;busy:boolean;run:CoreRun;canUpload:boolean}) {
  const [data,setData] = useState<Workspace>();
  const [error,setError] = useState("");
  const [file,setFile] = useState<File|null>(null);
  const endpoint = `/theses/${thesis.id}/publication-claims`;
  const load = async () => {try {setData(await request<Workspace>(endpoint,userId));setError("");} catch(e){setError(String(e));}};
  useEffect(()=>{void load();},[endpoint,userId,docs]);
  const options=docs.filter(d=>d.document_type==="SUPPORTING").flatMap(d=>d.versions.filter(v=>v.scan_state==="CLEAN").map(v=>({id:v.id,label:`${d.title} · v${v.version_no} · ${v.file_name}`})));
  const taken=new Set(data?.items.filter(i=>["SUBMITTED","ADVISOR_CONFIRMED","APPROVED"].includes(i.state)).flatMap(i=>i.details.student_ids));
  return <section className="card" style={{overflowWrap:"anywhere",minWidth:0}}><div className="card-body stack">
    <h2>Minh chứng công bố khoa học · Xét điểm thưởng</h2>
    <p>SV nộp → GVHD xác nhận công bố và đóng góp → TBM duyệt mức thưởng từng SV → Hội đồng đối chiếu. Mỗi SV tối đa 1 điểm; nộp tệp chưa đồng nghĩa được thưởng.</p>
    {error&&<p role="alert" className="alert alert-danger">{error}<button className="btn btn-secondary" onClick={load}>Thử lại</button></p>}
    {data?.can_submit&&thesis.members.some(m=>!taken.has(m.student_id))&&<details><summary>Nộp hồ sơ xét điểm thưởng</summary><form className="core-form" onSubmit={async e=>{
      e.preventDefault();const form=e.currentTarget;const f=new FormData(form);
      const succeeded=await run(async()=>{
        if(!f.getAll("students").length)throw new Error("Chọn ít nhất một sinh viên đề nghị được hưởng thưởng.");
        let version=String(f.get("evidence")||"");
        if(file){
          const created=await request<ThesisDocument>(`/theses/${thesis.id}/documents`,userId,{method:"POST",body:JSON.stringify({document_type:"SUPPORTING",title:`Minh chứng công bố: ${String(f.get("title")).slice(0,220)}`})});
          const uploaded=await uploadDocument(thesis.id,created,userId,file);
          setFile(null);const input=form.querySelector<HTMLInputElement>('input[type="file"]');if(input)input.value="";
          const latest=uploaded.versions[0];
          if(!latest||latest.scan_state!=="CLEAN")throw new Error("Tệp đã lưu nhưng chưa quét an toàn. Sau khi quét xong, chọn tệp đã nộp để gửi hồ sơ; không cần tải lại.");
          version=latest.id;
        }
        await request(endpoint,userId,{method:"POST",body:JSON.stringify({title:f.get("title"),venue:f.get("venue"),reference:f.get("reference"),contribution:f.get("contribution"),student_ids:f.getAll("students"),evidence_version_id:version})});
      },"Đã gửi minh chứng đến GVHD kiểm tra.");
      if(succeeded){form.reset();setFile(null);} await load();
    }}>
      <label>Tên công bố<input className="input" name="title" required minLength={5} maxLength={300}/></label>
      <label>Tạp chí / hội nghị / đơn vị công bố<input className="input" name="venue" required minLength={3} maxLength={300}/></label>
      <label>Thông tin công bố (ngày, số, DOI hoặc đường dẫn)<input className="input" name="reference" required minLength={5} maxLength={500}/></label>
      <label>Liên quan đến khóa luận và đóng góp cụ thể của từng SV<textarea className="input" name="contribution" required minLength={10} maxLength={3000}/></label>
      <fieldset><legend>Sinh viên đề nghị được hưởng thưởng</legend>{thesis.members.map(m=><label key={m.student_id} style={{display:"flex",gap:".5rem",alignItems:"center"}}><input type="checkbox" name="students" value={m.student_id} disabled={taken.has(m.student_id)}/>{m.display_name} · {m.student_code}{taken.has(m.student_id)&&" · Đã có hồ sơ"}</label>)}</fieldset>
      {canUpload&&<label>Tải minh chứng mới (PDF, DOCX, TXT · tối đa 10 MB)<input className="input" type="file" accept=".pdf,.docx,.txt" onChange={e=>setFile(e.target.files?.[0]??null)}/></label>}
      <label>Hoặc chọn tệp đã nộp và quét an toàn<select className="input" name="evidence" required={!file} disabled={!!file}><option value="">Chọn đúng minh chứng công bố</option>{options.map(o=><option key={o.id} value={o.id}>{o.label}</option>)}</select></label>
      {!canUpload&&<p className="text-muted">Đợt đang đóng nhận tệp mới; bạn có thể chọn minh chứng đã nộp.</p>}
      <button className="btn btn-primary" disabled={busy||!!file&&(file.size>10*1024*1024||file.size===0)}>Gửi GVHD kiểm tra</button>
    </form></details>}
    {data?.items.length===0&&<p className="text-muted">Chưa có hồ sơ xét điểm thưởng.</p>}
    {data?.items.map(item=><article key={item.id} className="card"><div className="card-body stack">
      <strong>{item.details.title}</strong><p>{labels[item.state]}</p>
      <p>{item.details.venue} · {item.details.reference}</p><p style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{item.details.contribution}</p>
      <ul>{item.details.student_ids.map(s=><li key={s}>{thesis.members.find(m=>m.student_id===s)?.display_name??"Thành viên trước đây"}{item.details.points&&` · Được duyệt ${item.details.points[s]} / 1 điểm`}</li>)}</ul>
      <button className="btn btn-secondary" disabled={busy} onClick={()=>run(async()=>{const doc=docs.find(d=>d.versions.some(v=>v.id===item.evidence_version_id));const version=doc?.versions.find(v=>v.id===item.evidence_version_id);if(!doc||!version)throw new Error("Hãy làm mới hồ sơ để tải minh chứng.");await downloadDocument(thesis.id,doc,version,userId);},"Đã tải minh chứng.")}>Tải minh chứng để đối chiếu</button>
      <ol>{item.history.map((h,i)=><li key={i}><strong>{labels[h.state]}</strong> · {h.actor} · {new Date(h.at).toLocaleString("vi-VN")}<p>{h.reason}</p></li>)}</ol>
      {item.state==="REVISION_REQUIRED"&&data.can_submit&&<p className="alert alert-info">Đọc nhận xét, chuẩn bị bản bổ sung rồi dùng “Nộp hồ sơ xét điểm thưởng” phía trên. Hồ sơ cũ được giữ để đối chiếu.</p>}
      {((item.state==="SUBMITTED"&&data.can_review)||(item.state==="ADVISOR_CONFIRMED"&&data.can_approve))&&<form className="core-form" onSubmit={async e=>{
        e.preventDefault();const f=new FormData(e.currentTarget);const outcome=String(f.get("outcome"));
        await run(()=>request(`${endpoint}/${item.id}/decision`,userId,{method:"POST",headers:{"If-Match":String(item.row_version)},body:JSON.stringify({outcome,reason:f.get("reason"),points:outcome==="APPROVE"?Object.fromEntries(item.details.student_ids.map(s=>[s,f.get(`points-${s}`)])):{}})}),"Đã lưu kết quả và thông báo đến người liên quan.");await load();
      }}>
        <label>Kết quả<select className="input" name="outcome">{item.state==="SUBMITTED"?<option value="CONFIRM">Xác nhận liên quan khóa luận và đóng góp, chuyển TBM</option>:<><option value="APPROVE">Duyệt mức thưởng theo từng SV</option><option value="REJECT">Không duyệt</option></>}<option value="REVISION_REQUIRED">Yêu cầu SV bổ sung</option></select></label>
        {item.state==="ADVISOR_CONFIRMED"&&item.details.student_ids.map(s=><label key={s}>Mức thưởng · {thesis.members.find(m=>m.student_id===s)?.display_name}<input className="input" name={`points-${s}`} type="number" min={0} max={1} step=".01" defaultValue="0" required/></label>)}
        <label>{item.state==="SUBMITTED"?"Nhận xét kiểm tra công bố và đóng góp":"Căn cứ xét duyệt và giải thích mức thưởng"}<textarea className="input" name="reason" required minLength={5} maxLength={1000}/></label>
        <button className="btn btn-primary" disabled={busy}>Lưu kết quả {item.state==="SUBMITTED"?"GVHD":"TBM"}</button>
      </form>}
    </div></article>)}
  </div></section>;
}
