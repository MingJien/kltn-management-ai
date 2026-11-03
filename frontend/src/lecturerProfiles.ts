import {request} from "./api";

export type ProfileData={display_name:string;academic_degree:string|null;academic_title:string|null;professional_title:string|null;contact_email:string|null;contact_phone:string|null;show_phone:boolean;office_location:string|null;office_hours:string|null;website:string|null;biography:string|null;education:string|null;experience:string|null;specializations:string[];research_interests:string[]};
export type LecturerProfile={id:string;user_id:string|null;lecturer_code:string;display_name:string;department_id:string;department_code:string;department_name:string;faculty_name:string;data:ProfileData;avatar_url:string|null;row_version:number;verified_at:string|null;verification_kind:"SELF_CONFIRMED"|"REVIEWED"|null;positions:string[];account_email:string|null;account_status:string|null;can_manage_identity:boolean;is_owner:boolean};
export type ProfileChange={id:string;lecturer_id:string;lecturer_name:string;lecturer_code:string;department_name:string;version_no:number;row_version:number;state:string;base_profile_version:number;stale:boolean;proposed_data:ProfileData;original_data:ProfileData;avatar_changed:boolean;avatar_url:string|null;original_avatar_url:string|null;avatar_name:string|null;avatar_scan_state:string|null;submission_note:string|null;submitted_at:string|null;updated_at:string;reviewed_at:string|null;reviewed_by_name:string|null;decision_reason:string|null;can_review:boolean;reviewer_count:number|null};
export type ProfileWorkspace={profile:LecturerProfile;active_request:ProfileChange|null;history:ProfileChange[]};
export type Directory={total:number;items:LecturerProfile[];departments:{id:string;code:string;name:string}[]};
export const degreeLabels:Record<string,string>={BACHELOR:"Đại học (cử nhân / kỹ sư)",MASTER:"Thạc sĩ",DOCTOR:"Tiến sĩ",DOCTOR_OF_SCIENCE:"Tiến sĩ khoa học"};
export const titleLabels:Record<string,string>={NONE:"Không có học hàm",ASSOCIATE_PROFESSOR:"Phó giáo sư",PROFESSOR:"Giáo sư"};
export const changeLabels:Record<string,string>={DRAFT:"Bản nháp riêng",SUBMITTED:"Chờ duyệt",APPROVED:"Đã duyệt",RETURNED:"Cần bổ sung",WITHDRAWN:"Đã rút"};
export const scanLabels:Record<string,string>={CLEAN:"Đã quét an toàn",QUARANTINED:"Ảnh đang cách ly, chưa quét",FAILED:"Quét ảnh thất bại",INFECTED:"Ảnh không an toàn"};
export const fieldLabels:Record<keyof ProfileData,string>={display_name:"Họ và tên",academic_degree:"Trình độ đào tạo cao nhất",academic_title:"Học hàm",professional_title:"Chức danh nghề nghiệp",contact_email:"Email liên hệ công khai",contact_phone:"Số điện thoại",show_phone:"Công khai số điện thoại",office_location:"Phòng làm việc",office_hours:"Giờ tiếp sinh viên",website:"Trang cá nhân / chuyên môn",biography:"Giới thiệu",education:"Quá trình đào tạo",experience:"Kinh nghiệm giảng dạy và nghiên cứu",specializations:"Chuyên môn",research_interests:"Hướng nghiên cứu"};
export function formatField(key:keyof ProfileData,value:unknown):string {
  if(value===null||value===undefined||value===""||Array.isArray(value)&&!value.length)return "Chưa cập nhật";
  if(key==="academic_degree")return degreeLabels[String(value)]||String(value);
  if(key==="academic_title")return titleLabels[String(value)]||String(value);
  if(typeof value==="boolean")return value?"Có":"Không";
  return Array.isArray(value)?value.join(", "):String(value);
}
export const profileDataEqual=(a:ProfileData,b:ProfileData)=>JSON.stringify(Object.keys(fieldLabels).sort().map(k=>a[k as keyof ProfileData]))===JSON.stringify(Object.keys(fieldLabels).sort().map(k=>b[k as keyof ProfileData]));
export const profileTime=(value:string|null)=>value?new Date(value).toLocaleString("vi-VN",{timeZone:"Asia/Ho_Chi_Minh"}):"Chưa ghi nhận";
export const profileMutation=<T,>(path:string,userId:string,body:unknown,version:number,method="POST")=>request<T>(path,userId,{method,body:body===undefined?undefined:JSON.stringify(body),headers:{"If-Match":String(version)}});
