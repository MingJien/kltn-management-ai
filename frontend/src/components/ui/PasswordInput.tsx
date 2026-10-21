import { useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";

type PasswordInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "id"> & {
  id: string;
  label: string;
};

export default function PasswordInput({ id, label, className = "input", disabled, ...props }: PasswordInputProps) {
  const [visible, setVisible] = useState(false);

  return <div className="login-password-field">
    <input {...props} id={id} className={className} type={visible ? "text" : "password"} disabled={disabled} />
    <button type="button" className="login-password-toggle" disabled={disabled}
      aria-label={`${visible ? "Ẩn" : "Hiện"} ${label.toLowerCase()}`}
      aria-controls={id} aria-pressed={visible} onClick={() => setVisible((shown) => !shown)}>
      {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
    </button>
  </div>;
}
