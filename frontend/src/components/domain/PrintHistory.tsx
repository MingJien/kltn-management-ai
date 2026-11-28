import { useEffect, useState } from "react";
import type { PrintExport } from "../../api";
import { request } from "../../api";
import { errorMessage } from "../../errors";
import Badge from "../ui/Badge";
import { formatDate } from "./CoreForms";

export default function PrintHistory({endpoint, userId, version, refreshKey}: {
  endpoint: string; userId: string; version: number; refreshKey?: string | number;
}) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<PrintExport[] | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController(); setError("");
    void request<PrintExport[]>(endpoint, userId, {signal: controller.signal})
      .then(result => {if (!controller.signal.aborted) setRows(result);})
      .catch(cause => {if (!controller.signal.aborted) setError(errorMessage(cause));});
    return () => controller.abort();
  }, [open, endpoint, userId, refreshKey, retry]);
  return <details className="core-print-history" open={open} onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Lịch sử xuất bản in v{version}</summary>
    <div className="stack mt-3">
      {error ? <p role="alert">{error} <button type="button" className="btn btn-secondary btn-sm" onClick={() => setRetry(value => value + 1)}>Thử lại</button></p>
        : rows === null ? <p role="status">Đang tải lịch sử xuất…</p>
        : rows.length === 0 ? <p className="text-body-sm text-muted">Phiên bản này chưa được xuất bản in từ hệ thống.</p>
        : <>{rows.map(row => <div className="core-review" key={row.id}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <strong>{row.document_code}</strong>
            <Badge variant={row.copy_status === "APPROVED" ? "success" : "info"}>
              {row.copy_status === "APPROVED" ? "Xuất từ phiên bản đã duyệt" : "Bản nộp đăng ký — chưa xác nhận Khoa duyệt"}
            </Badge>
          </div>
          <p className="text-body-sm">{row.actor_name} · {formatDate(row.exported_at)}</p>
        </div>)}<p className="text-caption">Hiển thị tối đa 50 lần xuất gần nhất của đúng phiên bản này.</p></>}
    </div>
  </details>;
}
