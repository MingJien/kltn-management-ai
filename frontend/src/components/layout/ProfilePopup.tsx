import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { UserRound, KeyRound, LogOut } from "lucide-react";
import type { Context } from "../../api";
import { roleLabel } from "./roleLabel";
import { initialsOf } from "./initials";
import LecturerAvatar from "../domain/LecturerAvatar";

interface ProfilePopupProps {
  context: Context;
  onLogout: () => void;
}

export default function ProfilePopup({ context, onLogout }: ProfilePopupProps) {
  const root = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="header__profile" ref={root}>
      <button
        type="button"
        className={`header__icon-btn ${open ? "header__icon-btn--active" : ""}`}
        aria-label="Xem hồ sơ cá nhân"
        title={`Hồ sơ cá nhân: ${context.display_name}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((prev) => !prev)}
      >
        {context.base_role==="LECTURER"?<LecturerAvatar url={context.avatar_url} name={context.display_name} size="xs"/>:<UserRound size={19} aria-hidden="true" />}
      </button>

      {open && (
        <section className="profile-popup" role="dialog" aria-label="Hồ sơ cá nhân">
          <div className="profile-popup__header">
            <span className="header__avatar profile-popup__avatar" aria-hidden="true">
              {context.base_role==="LECTURER"?<LecturerAvatar url={context.avatar_url} name={context.display_name} size="md"/>:initialsOf(context.display_name)}
            </span>
            <div className="profile-popup__title-group">
              <strong className="profile-popup__name">{context.display_name}</strong>
              <span className="badge badge-primary">{roleLabel(context)}</span>
            </div>
          </div>

          <div className="profile-popup__body">
            <div className="profile-popup__row">
              <span className="profile-popup__label">Email</span>
              <span className="profile-popup__value">{context.email || "Chưa có"}</span>
            </div>
            {context.student_code ? (
              <div className="profile-popup__row">
                <span className="profile-popup__label">MSSV</span>
                <span className="profile-popup__value font-mono">{context.student_code}</span>
              </div>
            ) : null}
            {context.lecturer_code ? (
              <div className="profile-popup__row">
                <span className="profile-popup__label">Mã GV</span>
                <span className="profile-popup__value font-mono">{context.lecturer_code}</span>
              </div>
            ) : null}
            {context.class_name ? (
              <div className="profile-popup__row">
                <span className="profile-popup__label">Lớp</span>
                <span className="profile-popup__value">{context.class_name}</span>
              </div>
            ) : null}
            {context.department_name ? (
              <div className="profile-popup__row">
                <span className="profile-popup__label">Bộ môn</span>
                <span className="profile-popup__value">
                  {context.department_name}
                  {context.department_code ? ` (${context.department_code})` : ""}
                </span>
              </div>
            ) : null}
            {context.major_name || context.major_code ? (
              <div className="profile-popup__row">
                <span className="profile-popup__label">Ngành</span>
                <span className="profile-popup__value">
                  {context.major_name || context.major_code}
                </span>
              </div>
            ) : null}
          </div>

          <div className="profile-popup__footer">
            <Link
              to="/account"
              className="btn btn-secondary btn-sm profile-popup__action"
              onClick={() => setOpen(false)}
            >
              <KeyRound size={14} aria-hidden="true" /> Đổi mật khẩu & Tài khoản
            </Link>
            <button
              type="button"
              className="btn btn-ghost btn-sm profile-popup__logout"
              onClick={() => {
                setOpen(false);
                onLogout();
              }}
            >
              <LogOut size={14} aria-hidden="true" /> Đăng xuất
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
