import { ClipboardList, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";
import "../../styles/assignment-tabs.css";

export default function AssignmentTabs() {
  return (
    <nav className="assignment-tabs" aria-label="Phân công và chức vụ">
      <NavLink to="/administration/assignments" end className={({isActive}) => isActive ? "assignment-tabs__link is-active" : "assignment-tabs__link"}>
        <ClipboardList size={18} aria-hidden="true" />
        <span>Phân công theo đợt</span>
      </NavLink>
      <NavLink to="/positions" end className={({isActive}) => isActive ? "assignment-tabs__link is-active" : "assignment-tabs__link"}>
        <ShieldCheck size={18} aria-hidden="true" />
        <span>Chức vụ và phạm vi</span>
      </NavLink>
    </nav>
  );
}
