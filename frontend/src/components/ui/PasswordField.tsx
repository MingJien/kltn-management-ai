import { useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";

export interface PasswordFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  id?: string;
  wrapperClassName?: string;
  toggleAriaLabelShow?: string;
  toggleAriaLabelHide?: string;
}

export default function PasswordField({
  className = "input",
  wrapperClassName = "login-password-field",
  toggleAriaLabelShow = "Hiện mật khẩu",
  toggleAriaLabelHide = "Ẩn mật khẩu",
  id,
  ...inputProps
}: PasswordFieldProps) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className={wrapperClassName}>
      <input
        {...inputProps}
        id={id}
        type={showPassword ? "text" : "password"}
        className={className}
      />
      <button
        type="button"
        className="login-password-toggle"
        aria-label={showPassword ? toggleAriaLabelHide : toggleAriaLabelShow}
        aria-pressed={showPassword}
        onClick={() => setShowPassword((visible) => !visible)}
      >
        {showPassword ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
      </button>
    </div>
  );
}
