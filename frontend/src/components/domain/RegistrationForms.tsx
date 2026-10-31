import {useCallback,useEffect,useState} from "react";
import type {Registration,RegistrationForms as Forms} from "../../api";
import {downloadOfficialTemplate,downloadRegistrationForm,request,uploadRegistrationForm} from "../../api";
import {errorMessage} from "../../errors";
import {formatDate} from "./CoreForms";
import {scanLabel} from "./ThesisDocuments";
import PrintHistory from "./PrintHistory";

export default function RegistrationForms({row,userId,onChanged,defaultOpen=false}:{row:Registration;userId:string;onChanged:()=>Promise<void>;defaultOpen?:boolean}) {
  const [open,setOpen]=useState(defaultOpen);
  const [forms,setForms]=useState<Forms|null>(null);
  const [file,setFile]=useState<File|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const path=`/topic-registrations/${row.id}/forms`;
  const load=useCallback(async(signal?:AbortSignal)=>{
    const result=await request<Forms>(path,userId,{signal});if(!signal?.aborted)setForms(result);
  },[path,userId]);
  useEffect(()=>{
    if(!open)return;const controller=new AbortController();
    void load(controller.signal).catch(cause=>{if(!controller.signal.aborted)setError(errorMessage(cause));});
    return ()=>controller.abort();
  },[open,row.row_version,load]);
  async function run(action:()=>Promise<unknown>,message:string) {
    if(busy)return;setBusy(true);setError("");setNotice("");
    try {await action();await load();await onChanged();setNotice(message);return true;}
    catch(cause) {setError(errorMessage(cause));return false;}finally{setBusy(false);}
  }
  const valid=!!file && /\.(pdf|docx)$/i.test(file.name) && file.size>0 && file.size<=20*1024*1024;
  return <details className="registration-forms" open={open} onToggle={event=>setOpen(event.currentTarget.open)}>
    <summary>Đơn đăng ký Mẫu 1a/1b · tệp nộp và bản in</summary>
    {open && <div className="stack" style={{marginTop:"var(--space-3)"}}>
      <p className="text-body-sm">Điền đúng mẫu cá nhân hoặc nhóm, nộp tệp tại đây rồi mở hồ sơ đăng ký để gửi hoặc xem quyết định tiếp nhận.</p>
      <p className="text-body-sm text-muted">Trạng thái đăng ký và bản nộp được theo dõi riêng. Tệp đã nộp chưa phải xác nhận Khoa duyệt.</p>
      <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void run(()=>load(),"Đã làm mới các phiên bản đơn.")}>Làm mới đơn đăng ký</button>
      {error && <p role="alert" className="alert alert-danger">{error}</p>}
      {notice && <p role="status" className="alert alert-info">{notice}</p>}
      {!forms ? <p role="status">Đang tải đơn đăng ký…</p> : <>
        <p><strong>Mẫu áp dụng: {forms.form_code === "1A" ? "1a — cá nhân" : "1b — theo nhóm"}</strong></p>
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void run(()=>downloadOfficialTemplate(
          forms.form_code==="1A"?"mau-01a":"mau-01b",`mau-${forms.form_code.toLowerCase()}.docx`,row.round_id),"Đã tải mẫu trắng; hãy điền nội dung trước khi nộp.")}>Tải mẫu trắng {forms.form_code.toLowerCase()}</button>
        {forms.can_submit ? <form className="core-form" onSubmit={async event=>{
          event.preventDefault();const element=event.currentTarget;
          if(file && valid && await run(()=>uploadRegistrationForm(row.id,userId,forms,file),"Đã lưu phiên bản đơn mới; chưa xác nhận Khoa duyệt.")){setFile(null);element.reset();}
        }}>
          <label htmlFor={`registration-form-${row.id}`}>Nộp đơn Mẫu {forms.form_code.toLowerCase()} (PDF/DOCX, tối đa 20 MB)</label>
          <input className="input" id={`registration-form-${row.id}`} type="file" accept=".pdf,.docx" required disabled={busy}
            onChange={event=>setFile(event.target.files?.[0]||null)}/>
          {file && !valid && <p role="alert">Chọn PDF/DOCX không rỗng, tối đa 20 MB.</p>}
          <button className="btn btn-primary" disabled={busy||!valid}>{busy?"Đang lưu và quét tệp…":"Nộp phiên bản đơn"}</button>
        </form> : <p className="text-body-sm text-muted">Chưa thể nộp: kiểm tra điều kiện tham gia đợt, hạn nhận và trạng thái hồ sơ. Các bản đã nộp vẫn được lưu để đối chiếu.</p>}
        {forms.versions.length===0 && <p>Chưa có tệp đơn đăng ký được nộp.</p>}
        {forms.versions.map(version=><section key={version.id} className="core-version stack">
          <strong>Mẫu {version.form_code.toLowerCase()} · phiên bản {version.version_no} · {version.file_name}</strong>
          <p className="text-body-sm">{version.submitted_by_name} · {formatDate(version.submitted_at)} · {scanLabel(version.scan_state)}</p>
          <p className="text-caption">{version.current?"Bản hiện hành — bản nộp, chưa xác nhận Khoa duyệt":"Bản lịch sử hoặc thông tin nhóm/đề tài đã thay đổi; cần nộp bản mới để xuất."}</p>
          {["FAILED","QUARANTINED"].includes(version.scan_state)&&<button type="button" className="btn btn-secondary" disabled={busy}
            onClick={()=>void run(()=>request(`${path}/${version.id}/scan`,userId,{method:"POST"}),"Đã quét lại; xem trạng thái tệp.")}>Quét lại đơn đăng ký</button>}
          <button type="button" className="btn btn-secondary" disabled={busy||version.scan_state!=="CLEAN"}
            onClick={()=>void run(()=>downloadRegistrationForm(row.id,version),"Đã tải đúng tệp nộp gốc, không thêm footer.")}>Tải đơn gốc v{version.version_no}</button>
          {version.current && <button type="button" className="btn btn-secondary" disabled={busy||version.scan_state!=="CLEAN"}
            onClick={()=>void run(()=>downloadRegistrationForm(row.id,version,true),"Đã xuất bản nộp có footer; đây không phải xác nhận Khoa duyệt.")}>Xuất bản nộp có footer v{version.version_no}</button>}
          <PrintHistory endpoint={`${path}/${version.id}/print-history`} userId={userId} version={version.version_no} refreshKey={notice} />
        </section>)}
      </>}
    </div>}
  </details>;
}
