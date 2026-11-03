import {fetchReviewFile, request} from "./api";

export type Kind = "ADVISOR" | "REVIEWER";
export type Review = {id:string;thesis_member_id:string;lecturer_id:string;lecturer_name:string;report_version_id:string;kind:Kind;version_no:number;row_version:number;sections:Record<string,string>;state:string;thesis_completed:boolean|null;allow_defense:boolean|null;source_reference:string|null;revision_reason:string;signed_file:{name:string;scan_state:string}|null;submitted_at:string|null;can_edit:boolean};
export type Eligibility = {state:string;conditions:{key:string;label:string;met:boolean}[];advisor_review_id:string|null;discipline_status:string;source_reference:string|null;reason:string|null;checked_at:string|null};
export type Evaluation = {workflow_blockers:{key:string;message:string}[];thesis_id:string;title:string;state:string;row_version:number;round_id:string;round_label:string;actions:string[];form_fields:Record<Kind,{key:string;label:string}[]>;members:{id:string;student_id:string;name:string;student_code:string;eligibility:Eligibility|null}[];reviews:Review[];report:{id:string;version_no:number;name:string;scan_state:string}|null;assignments:{id:string;lecturer_id:string;name:string;state:string;due_at:string|null;overdue:boolean;reason:string|null;source_reference:string|null}[];candidates:{id:string;name:string;code:string;active_load:number}[];eligibility_history:{id:string;thesis_member_id:string;version_no:number;state:string;discipline_status:string;source_reference:string;reason:string;checked_at:string;checked_by:string}[]};
export type EvaluationList = {total:number;items:{id:string;title:string;round_label:string;state:string;members:{name:string;code:string}[];reviewer_count:number;report_available:boolean;advisor_name:string|null}[]};
export const labels:Record<string,string> = {ACTIVE:"Đang thực hiện",PROPOSAL_APPROVED:"Đã duyệt đề cương",IN_PROGRESS:"Đang thực hiện",EXTENDED:"Đang gia hạn",READY_FOR_DEFENSE:"Đủ điều kiện bảo vệ",DEFENDED:"Đã bảo vệ",COMPLETED:"Đã hoàn thành",ARCHIVED:"Đã lưu trữ",WITHDRAWN:"Đã rút",ELIGIBLE:"Đủ điều kiện",BLOCKED:"Chưa đủ điều kiện",STALE:"Cần xét lại do hồ sơ thay đổi",NOT_CHECKED:"Chưa xét điều kiện",DRAFT:"Bản nháp riêng",SUBMITTED:"Đã gửi",REVOKED:"Đã thu hồi",CLEAN:"Đã quét an toàn",QUARANTINED:"Đang cách ly, chưa quét",FAILED:"Quét tệp thất bại",INFECTED:"Tệp không an toàn"};
export const when = (value:string|null) => value ? new Date(value).toLocaleString("vi-VN",{timeZone:"Asia/Ho_Chi_Minh"}) : "Chưa ghi nhận";
export function mutate<T>(path:string,userId:string,data:unknown,version?:number,method="POST") {
  return request<T>(path,userId,{method,body:JSON.stringify(data),headers:version ? {"If-Match":String(version)} : undefined});
}
export async function downloadEvaluationFile(path:string,name:string) {
  const bytes=await fetchReviewFile(path);
  const url=URL.createObjectURL(new Blob([bytes]));
  const anchor=document.createElement("a");anchor.href=url;anchor.download=name;anchor.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
