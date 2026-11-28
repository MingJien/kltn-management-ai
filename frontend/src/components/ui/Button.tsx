import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "soft" | "secondary" | "ghost" | "destructive" | "danger" | "link";
export type ButtonSize = "sm" | "md" | "lg" | "icon";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
  iconRight?: ReactNode;
  loading?: boolean;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: "btn-primary",
  soft: "btn-soft",
  secondary: "btn-secondary",
  ghost: "btn-ghost",
  destructive: "btn-destructive",
  danger: "btn-danger",
  link: "btn-link",
};

const SIZE_CLASS: Record<ButtonSize, string> = {
  sm: "btn-sm",
  md: "",
  lg: "btn-lg",
  icon: "btn-icon",
};

/** Standardized action button matching DThU Academic Blue hierarchy. */
export default function Button({
  variant = "secondary",
  size = "md",
  icon,
  iconRight,
  loading = false,
  disabled,
  className = "",
  type = "button",
  children,
  ...rest
}: ButtonProps) {
  const classes = [
    "btn",
    VARIANT_CLASS[variant],
    SIZE_CLASS[size],
    className,
  ].filter(Boolean).join(" ");

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {icon ? <span className="inline-flex items-center" aria-hidden="true">{icon}</span> : null}
      {children}
      {iconRight ? <span className="inline-flex items-center" aria-hidden="true">{iconRight}</span> : null}
    </button>
  );
}
