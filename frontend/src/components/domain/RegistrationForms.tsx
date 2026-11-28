import {useCallback,useEffect,useState} from "react";
import {Download, FileCheck2, RefreshCw, RotateCcw, Upload} from "lucide-react";
import type {Registration,RegistrationForms as Forms} from "../../api";
import {downloadOfficialTemplate,downloadRegistrationForm,request,uploadRegistrationForm} from "../../api";
import {errorMessage} from "../../errors";
import FileDropzone from "../ui/FileDropzone";
import ThesisStatusBadge from "./ThesisStatusBadge";
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
    {open && <div className="stack mt-3">
      <p className="text-body-sm">Điền đúng mẫu cá nhân hoặc nhóm, nộp tệp tại đây rồi mở hồ sơ đăng ký để gửi hoặc xem quyết định tiếp nhận.</p>
      <p className="text-body-sm text-muted">Trạng thái đăng ký và bản nộp được theo dõi riêng. Tệp đã nộp chưa phải xác nhận Khoa duyệt.</p>
      <p className="text-body-sm text-muted">Nếu nhóm đã có thành viên được giải quyết cho thôi, nộp phiên bản Mẫu 1 theo nhóm hiện tại tại đây. Còn một người dùng Mẫu 1a; giữ hồ sơ cũ và tiếp tục cập nhật Mẫu 2, Mẫu 3.</p>
      <div><button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void run(()=>load(),"Đã làm mới các phiên bản đơn.")}><RefreshCw size={15} aria-hidden="true"/>Làm mới đơn đăng ký</button></div>
      {error && <p role="alert" className="alert alert-danger">{error}</p>}
      {notice && <p role="status" className="alert alert-info">{notice}</p>}
      {!forms ? <p role="status">Đang tải đơn đăng ký…</p> : <>
        <p><strong>Mẫu áp dụng: {forms.form_code === "1A" ? "1a — cá nhân" : "1b — theo nhóm"}</strong></p>
        <div><button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void run(()=>downloadOfficialTemplate(
          forms.form_code==="1A"?"mau-01a":"mau-01b",`mau-${forms.form_code.toLowerCase()}.docx`,row.round_id),"Đã tải mẫu trắng; hãy điền nội dung trước khi nộp.")}><Download size={15} aria-hidden="true"/>Tải mẫu trắng {forms.form_code.toLowerCase()}</button></div>
        {forms.can_submit ? <form className="core-form" onSubmit={async event=>{
          event.preventDefault();const element=event.currentTarget;
          if(file && valid && await run(()=>uploadRegistrationForm(row.id,userId,forms,file),"Đã lưu phiên bản đơn mới; chưa xác nhận Khoa duyệt.")){setFile(null);element.reset();}
        }}>
          <FileDropzone
            id={`registration-form-${row.id}`}
            label={`Nộp đơn Mẫu ${forms.form_code.toLowerCase()} (PDF/DOCX, tối đa 20 MB)`}
            accept=".pdf,.docx"
            maxBytes={20 * 1024 * 1024}
            hint="PDF hoặc DOCX · Tối đa 20 MB"
            file={file}
            required
            disabled={busy}
            onChange={setFile}
          />
          {file && !valid && <p role="alert">Chọn PDF/DOCX không rỗng, tối đa 20 MB.</p>}
          <button className="btn btn-primary" disabled={busy||!valid}><Upload size={15} aria-hidden="true"/>{busy?"Đang lưu và quét tệp…":"Nộp phiên bản đơn"}</button>
        </form> : <p className="text-body-sm text-muted">Chưa thể nộp: kiểm tra điều kiện tham gia đợt, hạn nhận và trạng thái hồ sơ. Các bản đã nộp vẫn được lưu để đối chiếu.</p>}
        {forms.versions.length===0 && <p>Chưa có tệp đơn đăng ký được nộp.</p>}
        {forms.versions.map(version=><section key={version.id} className="core-version stack">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <strong>Mẫu {version.form_code.toLowerCase()} · phiên bản {version.version_no} · {version.file_name}</strong>
            <ThesisStatusBadge state={version.scan_state} label={scanLabel(version.scan_state)}/>
          </div>
          <p className="text-body-sm">{version.submitted_by_name} · {formatDate(version.submitted_at)}</p>
          <p className="text-caption">{version.current?"Bản hiện hành — bản nộp, chưa xác nhận Khoa duyệt":"Bản lịch sử hoặc thông tin nhóm/đề tài đã thay đổi; cần nộp bản mới để xuất."}</p>
          {["FAILED","QUARANTINED"].includes(version.scan_state)&&<button type="button" className="btn btn-secondary" disabled={busy}
            onClick={()=>void run(()=>request(`${path}/${version.id}/scan`,userId,{method:"POST"}),"Đã quét lại; xem trạng thái tệp.")}><RotateCcw size={15} aria-hidden="true"/>Quét lại đơn đăng ký</button>}
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn btn-secondary" disabled={busy||version.scan_state!=="CLEAN"}
              onClick={()=>void run(()=>downloadRegistrationForm(row.id,version),"Đã tải đúng tệp nộp gốc, không thêm footer.")}><Download size={15} aria-hidden="true"/>Tải đơn gốc v{version.version_no}</button>
            {version.current && <button type="button" className="btn btn-secondary" disabled={busy||version.scan_state!=="CLEAN"}
              onClick={()=>void run(()=>downloadRegistrationForm(row.id,version,true),"Đã xuất bản nộp có footer; đây không phải xác nhận Khoa duyệt.")}><FileCheck2 size={15} aria-hidden="true"/>Xuất bản nộp có footer v{version.version_no}</button>}
          </div>
          <PrintHistory endpoint={`${path}/${version.id}/print-history`} userId={userId} version={version.version_no} refreshKey={notice} />
        </section>)}
      </>}
    </div>}
  </details>;
}
