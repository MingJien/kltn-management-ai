import { useCallback, useEffect, useRef, useState } from "react";
import { Download, RefreshCw, Send, Upload } from "lucide-react";
import { downloadLecturerImportTemplate, request } from "../../api";
import { errorMessage } from "../../errors";

type PreviewRow = {line: number; lecturer_code: string; display_name: string; email: string; department_code: string; department_name: string | null; errors: string[]};
type Preview = {sha256: string; count: number; valid_count: number; can_import: boolean; rows: PreviewRow[]};
type Lecturer = {user_id: string; lecturer_code: string; display_name: string; email: string; department_code: string; department_name: string; mail_status: string; delivery_mode: string; account_status: string; last_attempt_at: string | null; retry_at: string | null; can_send: boolean};
type Directory = {items: Lecturer[]; delivery_mode: string; mail_ready: boolean};

export default function LecturerImport({userId, departments, refreshVersion, onCreated, directoryMode=false}: {directoryMode?:boolean;userId: string; departments: {code: string; name: string}[]; refreshVersion: number; onCreated: () => Promise<void>}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [directory, setDirectory] = useState<Directory>({items: [], delivery_mode: "", mail_ready: false});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [pendingOnly, setPendingOnly] = useState(!directoryMode);
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({});
  const fileRef = useRef<HTMLInputElement>(null);
  const selectRef = useRef<HTMLInputElement>(null);
  const operation = useRef(false);
  const generation = useRef(0);

  const reload = useCallback(async () => {
    const data = await request<Directory>("/admin/lecturers", userId);
    setDirectory(data);
    setSelected(current => new Set([...current].filter(id => data.items.some(row => row.user_id === id && row.can_send))));
  }, [userId]);
  useEffect(() => {void reload().catch(cause => setError(errorMessage(cause)));}, [reload, refreshVersion]);

  const fold = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[đĐ]/g, "d").toLowerCase();
  const matching = directory.items.filter(row => (!pendingOnly || row.mail_status !== "ACTIVATED")
    && fold(`${row.lecturer_code} ${row.display_name} ${row.email} ${row.department_code}`).includes(fold(query.trim())));
  const candidates = matching.filter(row => row.can_send);
  const allSelected = candidates.length > 0 && candidates.every(row => selected.has(row.user_id));
  const selectedCandidates = candidates.filter(row => selected.has(row.user_id));
  const pageCount = Math.max(1, Math.ceil(matching.length / 20));
  const currentPage = Math.min(page, pageCount - 1);
  const visible = matching.slice(currentPage * 20, (currentPage + 1) * 20);
  useEffect(() => {if (selectRef.current) selectRef.current.indeterminate = !allSelected && selectedCandidates.length > 0;}, [allSelected, selectedCandidates.length]);

  async function inspectFile() {
    if (!file || operation.current) return;
    operation.current = true; setBusy(true); setError(""); setNotice(""); setPreview(null); setConfirmed(false);
    const version = generation.current;
    try {
      const result = await request<Preview>("/admin/lecturers/import/preview", userId, {
        method: "POST", body: file, headers: {"Content-Type": "application/octet-stream", "X-File-Name": encodeURIComponent(file.name)},
      });
      if (version === generation.current) setPreview(result);
    } catch (cause) {setError(errorMessage(cause));}
    finally {operation.current = false; setBusy(false);}
  }

  async function importFile() {
    if (!file || !preview?.can_import || !confirmed || operation.current) return;
    operation.current = true; setBusy(true); setError(""); setNotice("");
    try {
      const result = await request<{created_count: number; user_ids: string[]}>("/admin/lecturers/import", userId, {
        method: "POST", body: file, headers: {"Content-Type": "application/octet-stream", "X-File-Name": encodeURIComponent(file.name), "X-Preview-SHA256": preview.sha256},
      });
      setPreview(null); setFile(null); setConfirmed(false);
      if (fileRef.current) fileRef.current.value = "";
      setQuery(""); setPage(0); setPendingOnly(true);
      setNotice(`Đã tạo ${result.created_count} tài khoản GV chờ kích hoạt. Chưa gửi email. Chọn người nhận ở danh sách bên dưới để gửi link.`);
      // A refresh failure cannot make a successful import look like a failed creation.
      try {await reload(); await onCreated();} catch {setError("Đã tạo tài khoản nhưng chưa làm mới được danh sách. Bấm Làm mới danh sách GV.");}
    } catch (cause) {setError(errorMessage(cause)); setPreview(null); setConfirmed(false);}
    finally {operation.current = false; setBusy(false);}
  }

  async function sendLinks(ids: string[]) {
    if (!ids.length || operation.current) return;
    operation.current = true; setSending(true); setError(""); setNotice(""); setRowErrors({});
    let sent = 0;
    for (const [index, id] of ids.entries()) {
      setProgress(`Đang gửi ${index + 1}/${ids.length}…`);
      try {
        const result = await request<{sent: boolean}>(`/admin/lecturers/${id}/activation-link`, userId, {method: "POST"});
        if (result.sent) sent += 1;
        else setRowErrors(old => ({...old, [id]: "Gửi thất bại. Kiểm tra dịch vụ thư và thử lại sau 60 giây."}));
        setDirectory(old => ({...old, items: old.items.map(row => row.user_id === id ? {...row,
          mail_status: result.sent ? "SENT" : "FAILED", can_send: false, last_attempt_at: new Date().toISOString()} : row)}));
      } catch (cause) {setRowErrors(old => ({...old, [id]: errorMessage(cause)}));}
    }
    setSelected(new Set()); setProgress("");
    setNotice(`Đã xử lý ${ids.length} người: ${sent} gửi thành công, ${ids.length - sent} chưa gửi được. Xem kết quả từng dòng.`);
    try {await reload();} catch {setError("Chưa làm mới được trạng thái. Bấm Làm mới danh sách GV để đối chiếu kết quả gửi.");}
    operation.current = false; setSending(false);
  }

  function mailLabel(row: Lecturer) {
    if (row.mail_status === "ACTIVATED") return "Đã kích hoạt";
    if (row.mail_status === "BLOCKED") return "Tài khoản đang khóa/không thể kích hoạt";
    if (row.mail_status === "SENT") return row.delivery_mode === "smtp" ? "Đã gửi tới máy chủ thư" : row.delivery_mode === "development_outbox" ? "Đã lưu thư thử nghiệm" : "Dịch vụ thư đã tiếp nhận";
    if (row.mail_status === "FAILED") return "Gửi thất bại";
    if (row.mail_status === "SENDING") return "Đang xử lý gửi";
    if (row.mail_status === "UNKNOWN") return "Chưa xác định kết quả; có thể gửi lại";
    return "Chưa ghi nhận gửi link";
  }

  return <section className="card stack lecturer-import" aria-label="Nhập và mời danh sách giảng viên" style={{padding: "var(--space-5, 24px)"}}>
    <div className="lecturer-import__intro">
      <h2>Nhập danh sách giảng viên bằng Excel</h2>
      <p>1. Chọn tệp → 2. Xem trước và xác nhận tạo → 3. Chọn người nhận và gửi link kích hoạt.</p>
      <p className="text-caption">Mỗi dòng gồm Mã GV, Họ tên, Email, Mã bộ môn. Tối đa 1.000 GV, 2 MB; một trang tính. Mã và email phải duy nhất.</p>
    </div>
    {error ? <p role="alert" className="alert alert-danger">{error}</p> : null}
    {notice ? <p role="status" className="alert alert-success">{notice}</p> : null}
    <div className="import-step">
      <div className="import-step__head">
        <span className="import-step__num">1</span>
        <div className="import-step__title">
          <h3>Nhập tệp danh sách GV</h3>
          <p className="text-caption">Tải tệp mẫu để điền đúng cấu trúc, chọn tệp rồi xem trước kết quả kiểm tra.</p>
        </div>
      </div>
      <div className="import-step__body">
        <button className="btn btn-secondary" disabled={busy || sending} onClick={() => void downloadLecturerImportTemplate().catch(cause => setError(errorMessage(cause)))}><Download size={16} aria-hidden="true" /> Tải Excel mẫu GV</button>
        <label className="input-group import-step__file">Tệp danh sách GV<input ref={fileRef} className="input" type="file" accept=".xlsx" disabled={busy || sending}
          onChange={e => {generation.current++; setFile(e.target.files?.[0] || null); setPreview(null); setConfirmed(false); setError(""); setNotice("");}} /></label>
        <button className="btn btn-secondary" disabled={!file || busy || sending} onClick={() => void inspectFile()}><Upload size={16} aria-hidden="true" />{busy ? "Đang xử lý…" : "Xem trước danh sách GV"}</button>
      </div>
      <details className="import-step__details"><summary>Xem mã bộ môn đang hoạt động để điền Excel</summary>
        <ul>{departments.map((department, index) => <li key={`${department.code}-${index}`}><code>{department.code}</code> · {department.name}</li>)}</ul>
        {!departments.length ? <p>Chưa tải được danh mục bộ môn. Hãy làm mới trang trước khi nhập.</p> : null}
      </details>
      {preview ? <div className="preview-box stack">
        <p className="preview-box__title" role="status">Kết quả xem trước: {preview.valid_count}/{preview.count} dòng hợp lệ.{!preview.can_import ? " Sửa tất cả dòng lỗi trong Excel rồi tải lại tệp." : " Chưa có tài khoản nào được tạo."}</p>
        <div className="table-scroll" role="region" aria-label="Kết quả kiểm tra tệp giảng viên" tabIndex={0} style={{maxHeight: 400}}><table className="account-table" style={{minWidth: 880}}><thead><tr><th>Dòng</th><th>Mã GV</th><th>Họ tên</th><th>Email</th><th>Bộ môn</th><th>Kết quả kiểm tra</th></tr></thead>
          <tbody>{preview.rows.map(row => <tr key={row.line}><td>{row.line}</td><td>{row.lecturer_code}</td><td>{row.display_name}</td><td>{row.email}</td><td>{row.department_code} · {row.department_name}</td>
            <td>{row.errors.length ? <ul className="text-danger">{row.errors.map(text => <li key={text}>{text}</li>)}</ul> : "Hợp lệ"}</td></tr>)}</tbody></table></div>
        <div className="preview-box__confirm">
          <label className="checkbox-label"><input type="checkbox" checked={confirmed} disabled={!preview.can_import || busy} onChange={e => setConfirmed(e.target.checked)} /> Tôi đã đối chiếu danh sách và xác nhận tạo {preview.count} tài khoản GV chờ kích hoạt.</label>
          <button className="btn btn-primary" disabled={!preview.can_import || !confirmed || busy || sending} onClick={() => void importFile()}>Xác nhận tạo tài khoản GV</button>
        </div>
      </div> : null}
    </div>
    <div className="import-step">
      <div className="import-step__head">
        <span className="import-step__num">2</span>
        <div className="import-step__title">
          <h3>Gửi link kích hoạt giảng viên</h3>
          <p className="text-caption">Tạo từ Excel chưa gửi thư. Mỗi GV nhận một liên kết riêng tại email đã đăng ký. Chỉ chọn tài khoản đang chờ kích hoạt; chờ 60 giây giữa hai lần gửi cho cùng người. Khi gửi theo danh sách, giữ trang mở đến khi có kết quả.</p>
        </div>
      </div>
      {directory.delivery_mode === "development_outbox" ? <p className="alert alert-warning">Máy chủ đang dùng hộp thư thử nghiệm: thư được lưu trên máy, chưa gửi ra email thật.</p> : null}
      {!directory.mail_ready ? <p className="alert alert-warning">Dịch vụ gửi thư chưa sẵn sàng. Có thể tạo tài khoản trước và gửi sau khi cấu hình hoàn tất.</p> : null}
      <div className="import-step__filters">
        <label className="input-group">Tìm GV để gửi link<input className="input" value={query} disabled={sending} onChange={e => {setQuery(e.target.value); setPage(0); setSelected(new Set());}} placeholder="Mã GV, tên, email hoặc bộ môn" /></label>
        <label className="checkbox-label"><input type="checkbox" checked={pendingOnly} disabled={sending} onChange={e => {setPendingOnly(e.target.checked); setPage(0); setSelected(new Set());}} /> Chỉ hiển thị GV chưa kích hoạt</label>
        <span className="import-step__filters-spacer" />
        <button className="btn btn-secondary" disabled={busy || sending} onClick={() => void reload().then(() => setError("")).catch(cause => setError(errorMessage(cause)))}><RefreshCw size={16} aria-hidden="true" /> Làm mới danh sách GV</button>
      </div>
      <div className="table-scroll import-step__table" role="region" aria-label="Danh sách tài khoản giảng viên" tabIndex={0}><table className="account-table" style={{minWidth: 980}}><thead><tr><th>Chọn</th><th>Mã GV · Họ tên</th><th>Email</th><th>Bộ môn</th><th>Tài khoản</th><th>Trạng thái gửi</th><th>Thao tác</th></tr></thead>
        <tbody>{visible.map(row => <tr key={row.user_id}>
          <td><input type="checkbox" aria-label={`Chọn GV ${row.lecturer_code}`} checked={selected.has(row.user_id)} disabled={!row.can_send || sending || busy} onChange={e => setSelected(old => {const next = new Set(old); if (e.target.checked) next.add(row.user_id); else next.delete(row.user_id); return next;})} /></td>
          <td style={{minWidth: 175}}><strong>{row.lecturer_code}</strong><div>{row.display_name}</div></td>
          <td style={{minWidth: 180, maxWidth: 250, overflowWrap: "anywhere"}}>{row.email}</td>
          <td style={{minWidth: 150}}>{row.department_code}<div className="text-caption">{row.department_name}</div></td>
          <td>{row.account_status === "ACTIVE" ? "Đang hoạt động" : row.account_status === "LOCKED" ? "Đã khóa" : row.mail_status === "BLOCKED" ? "Vô hiệu hóa" : "Chờ kích hoạt"}</td><td><span>{mailLabel(row)}</span>{row.last_attempt_at ? <div className="text-caption">{new Date(row.last_attempt_at).toLocaleString("vi-VN")}</div> : null}
            {row.retry_at && !row.can_send && row.mail_status !== "ACTIVATED" && row.mail_status !== "BLOCKED" ? <div className="text-caption">Có thể gửi lại sau {new Date(row.retry_at).toLocaleTimeString("vi-VN")}; bấm làm mới khi đến giờ.</div> : null}
            {rowErrors[row.user_id] ? <p role="alert" className="text-danger">{rowErrors[row.user_id]}</p> : null}</td>
          <td><button className="btn btn-secondary" aria-label={`Gửi link cho ${row.lecturer_code}`} disabled={!row.can_send || !directory.mail_ready || busy || sending} onClick={() => void sendLinks([row.user_id])}>Gửi link</button></td>
        </tr>)}</tbody></table>{!matching.length ? <p className="import-step__empty">Chưa có GV phù hợp bộ lọc.</p> : null}</div>
      <div className="import-step__footerbar">
        <label className="checkbox-label"><input ref={selectRef} type="checkbox" checked={allSelected} disabled={!candidates.length || sending || busy} onChange={e => setSelected(e.target.checked ? new Set(candidates.map(row => row.user_id)) : new Set())} /> Chọn tất cả GV có thể gửi trong kết quả tìm kiếm ({candidates.length} người, tất cả trang)</label>
        <p role="status" aria-live="polite" className="import-step__status">{progress || `${matching.length} GV trong danh sách; đã chọn ${selectedCandidates.length} người.`}</p>
      </div>
      <div className="import-step__actions">
        <div className="pagination import-step__pagination">
          <button className="btn btn-secondary" disabled={currentPage === 0 || sending} onClick={() => setPage(currentPage - 1)}>Trang GV trước</button>
          <span>Trang {currentPage + 1}/{pageCount}</span><button className="btn btn-secondary" disabled={currentPage + 1 >= pageCount || sending} onClick={() => setPage(currentPage + 1)}>Trang GV sau</button>
        </div>
        <button className="btn btn-primary" disabled={!selectedCandidates.length || !directory.mail_ready || busy || sending} onClick={() => void sendLinks(selectedCandidates.map(row => row.user_id))}><Send size={16} aria-hidden="true" /> Gửi link cho GV đã chọn ({selectedCandidates.length})</button>
      </div>
    </div>
  </section>;
}
