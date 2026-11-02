import {BriefcaseBusiness,GraduationCap,MapPin,Mail,Clock,Phone,Link as LinkIcon,ShieldCheck} from "lucide-react";
import {degreeLabels,titleLabels,profileTime,type LecturerProfile} from "../../lecturerProfiles";
import LecturerAvatar from "./LecturerAvatar";

export default function LecturerProfileView({profile:p}:{profile:LecturerProfile}) {
  const d=p.data;
  return <div className="lecturer-profile-view">
    <div className="lecturer-profile-hero"><LecturerAvatar url={p.avatar_url} name={p.display_name} size="lg"/><div><span className="lecturer-eyebrow">HỒ SƠ GIẢNG VIÊN</span><h2>{p.display_name}</h2><p>{[d.academic_title&&d.academic_title!=="NONE"?titleLabels[d.academic_title]:null,d.academic_degree?degreeLabels[d.academic_degree]:null].filter(Boolean).join(" · ")||"Chưa cập nhật học hàm, học vị"}</p><p>{p.lecturer_code} · {p.department_name}</p><span className={`lecturer-verification ${p.verified_at?"is-verified":""}`}><ShieldCheck size={14} aria-hidden="true"/>{p.verified_at?"Hồ sơ đã được Khoa duyệt":"Thông tin định danh từ Khoa"}</span></div></div>
    <dl className="lecturer-profile-facts"><div><dt><GraduationCap size={16} aria-hidden="true"/>Khoa</dt><dd>{p.faculty_name}</dd></div><div><dt><BriefcaseBusiness size={16} aria-hidden="true"/>Chức danh nghề nghiệp</dt><dd>{d.professional_title||"Chưa cập nhật"}</dd></div><div><dt>Chức vụ theo phân công</dt><dd>{p.positions?.length?p.positions.join(", "):"Giảng viên"}</dd></div></dl>
    <section><h3>Thông tin liên hệ</h3><dl className="lecturer-contact-grid">
      <div><dt><Mail size={16} aria-hidden="true"/>Email liên hệ</dt><dd>{d.contact_email?<a href={`mailto:${d.contact_email}`}>{d.contact_email}</a>:"Chưa công khai"}</dd></div>
      <div><dt><Phone size={16} aria-hidden="true"/>Số điện thoại</dt><dd>{d.contact_phone?<a href={`tel:${d.contact_phone.replace(/[^+0-9]/g,"")}`}>{d.contact_phone}</a>:"Chưa công khai"}</dd></div>
      <div><dt><MapPin size={16} aria-hidden="true"/>Phòng làm việc</dt><dd>{d.office_location||"Chưa cập nhật"}</dd></div><div><dt><Clock size={16} aria-hidden="true"/>Giờ tiếp sinh viên</dt><dd>{d.office_hours||"Chưa cập nhật"}</dd></div>
      <div><dt><LinkIcon size={16} aria-hidden="true"/>Trang cá nhân / chuyên môn</dt><dd>{d.website?<a href={d.website} target="_blank" rel="noopener noreferrer">{d.website}</a>:"Chưa cập nhật"}</dd></div>
    </dl></section>
    <section><h3>Chuyên môn</h3>{d.specializations.length?<div className="lecturer-tags">{d.specializations.map(x=><span key={x}>{x}</span>)}</div>:<p className="text-muted">Chưa cập nhật chuyên môn.</p>}</section>
    <section><h3>Hướng nghiên cứu</h3>{d.research_interests.length?<div className="lecturer-tags">{d.research_interests.map(x=><span key={x}>{x}</span>)}</div>:<p className="text-muted">Chưa cập nhật hướng nghiên cứu.</p>}</section>
    {[{key:"biography",title:"Giới thiệu"},{key:"education",title:"Quá trình đào tạo"},{key:"experience",title:"Kinh nghiệm giảng dạy và nghiên cứu"}].map(({key,title})=><section key={key}><h3>{title}</h3><p className="lecturer-prose">{d[key as "biography"|"education"|"experience"]||"Chưa cập nhật"}</p></section>)}
    <p className="lecturer-profile-updated">{p.verified_at?`Khoa duyệt cập nhật lúc ${profileTime(p.verified_at)}. Chỉ hiển thị nội dung đã được duyệt.`:"Giảng viên có thể bổ sung thông tin tại Tài khoản của tôi; nội dung bổ sung được công bố sau khi Khoa duyệt."}</p>
  </div>;
}
