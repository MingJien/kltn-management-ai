import { FileText, Upload, X } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";

interface FileDropzoneProps {
  id?: string;
  name?: string;
  label: string;
  accept: string;
  maxBytes?: number;
  file: File | null;
  onChange: (file: File | null) => void;
  disabled?: boolean;
  required?: boolean;
  hint?: string;
  errorText?: string;
}

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function matchesAccept(fileName: string, accept: string): boolean {
  const extensions = accept
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter((s) => s.startsWith("."));
  if (!extensions.length) return true;
  const lower = fileName.toLowerCase();
  return extensions.some((ext) => lower.endsWith(ext));
}

/** Accessible drag-and-drop file selector wrapping a native <input type="file">. */
export default function FileDropzone({
  id,
  name,
  label,
  accept,
  maxBytes,
  file,
  onChange,
  disabled = false,
  required = false,
  hint,
  errorText,
}: FileDropzoneProps) {
  const autoId = useId();
  const inputId = id || autoId;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState("");

  const activeError = errorText || localError;

  function pickFile(candidate: File | null) {
    setLocalError("");
    if (!candidate) {
      onChange(null);
      return;
    }
    if (!matchesAccept(candidate.name, accept)) {
      setLocalError(`Tệp phải đúng định dạng cho phép (${accept}).`);
      onChange(null);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (candidate.size === 0) {
      setLocalError("Tệp đang rỗng (0 byte). Vui lòng chọn tệp có nội dung hợp lệ.");
      onChange(null);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (maxBytes && candidate.size > maxBytes) {
      setLocalError(`Tệp vượt quá dung lượng cho phép (${formatSize(maxBytes)}).`);
      onChange(null);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    onChange(candidate);
  }

  function clearFile() {
    setLocalError("");
    onChange(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
    if (disabled) return;
    const dropped = e.dataTransfer.files?.[0] || null;
    if (dropped && inputRef.current && typeof DataTransfer !== "undefined") {
      try {
        const dt = new DataTransfer();
        dt.items.add(dropped);
        inputRef.current.files = dt.files;
      } catch {
        // Fallback: state holds file even if programmatic input.files assignment is blocked
      }
    }
    pickFile(dropped);
  }

  return (
    <div className="file-dropzone-wrap">
      <label className="file-dropzone__label" htmlFor={inputId}>
        {label}
      </label>
      <div
        className={`file-dropzone ${dragging ? "file-dropzone--active" : ""} ${disabled ? "file-dropzone--disabled" : ""}`.trim()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setDragging(false);
        }}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          id={inputId}
          name={name}
          type="file"
          className="file-dropzone__input"
          accept={accept}
          disabled={disabled}
          required={required && !file}
          aria-describedby={[hint ? hintId : "", activeError ? errorId : ""].filter(Boolean).join(" ") || undefined}
          onChange={(e) => pickFile(e.target.files?.[0] || null)}
        />
        <div className="file-dropzone__prompt" aria-hidden="true">
          <Upload size={18} />
          <span>Kéo thả tệp vào đây hoặc <strong>chọn tệp từ máy</strong></span>
        </div>
        {hint && (
          <small id={hintId} className="file-dropzone__hint">
            {hint}
          </small>
        )}
      </div>

      {file && (
        <div className="file-dropzone__file">
          <FileText size={16} aria-hidden="true" />
          <span className="file-dropzone__filename">{file.name}</span>
          <span className="file-dropzone__size">{formatSize(file.size)}</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={disabled}
            onClick={clearFile}
            aria-label="Xóa tệp đã chọn"
          >
            <X size={14} aria-hidden="true" /> Xóa tệp
          </button>
        </div>
      )}

      {activeError && (
        <p id={errorId} role="alert" className="alert alert-danger mt-2">
          {activeError}
        </p>
      )}
    </div>
  );
}
