function responseFileName(response:Response,fallback:string) {
  return decodeURIComponent(response.headers.get("Content-Disposition")?.match(/filename\*=UTF-8\x27\x27([^;]+)/i)?.[1]||fallback);
}
import { ApiError, apiMessage } from "./errors";

export type Context = {
  user_id: string;
  base_role: string;
  student_id: string | null;
  lecturer_id: string | null;
  actions: string[];
  display_name: string;
  department_id: string | null;
  department_code: string | null;
  department_name: string | null;
  email: string | null;
  student_code: string | null;
  class_name: string | null;
  major_code: string | null;
  major_name: string | null;
  lecturer_code: string | null;
  avatar_url?: string | null;
  lecturer_duties: {code: string; label: string; scope: string | null}[];
  csrf_token: string | null;
  can_change_password: boolean;
};
export type Topic = {
  id: string;
  round_id: string;
  title: string;
  description: string | null;
  max_students: number;
  state: string;
  row_version: number;
  department_id: string;
  proposer_user_id: string;
  decision_reason: string | null;
  code: string;
  round_label: string;
  proposer_type: string;
  receiving_lecturer_id: string | null;
  receiving_lecturer_name: string | null;
  requirements: Requirement[];
  title_versions: {version_no: number; title: string; change_reason: string | null; created_at: string}[];
  available: boolean;
  registered_member_count: number;
  remaining_slots: number;
  registration_state: string | null;
  archived_at: string | null;
  archive_reason: string | null;
  has_links: boolean;
  registered_students?: TopicRegisteredStudent[];
};
export type TopicRegisteredStudent = {
  student_id: string;
  student_code: string;
  display_name: string;
  class_name: string | null;
  is_coordinator: boolean;
  consent_status: string;
  registration_state: string | null;
};
export type Requirement = {requirement_type: "PREFERRED_GPA" | "SKILL" | "TECHNOLOGY" | "KNOWLEDGE" | "OTHER"; value_text: string; preferred_gpa: number | null};
export type Lecturer = {id: string; display_name: string; lecturer_code: string; department_name?: string | null; faculty_name?: string | null};
export type OpenRound = { id: string; code: string; closes_at: string; academic_year: string; label: string };
export type EligibleStudent = { id: string; display_name: string; student_code: string };
export type RegistrationMember = {
  student_id: string;
  student_code: string;
  display_name: string;
  is_coordinator: boolean;
  active: boolean;
  consent_status: "PENDING" | "ACCEPTED" | "DECLINED";
  evidence_file_name: string | null;
  evidence_scan_state: string | null;
  can_upload_evidence: boolean;
  can_withdraw: boolean;
};
export type Registration = {
  id: string;
  topic_id: string;
  round_id: string;
  state: string;
  row_version: number;
  expected_member_count: number;
  submitted_at: string | null;
  member_student_ids: string[];
  members: RegistrationMember[];
  lecturer_decided_at: string | null;
  thesis_id: string | null;
  topic_title: string;
  topic_proposer_user_id: string;
  topic_code: string;
  topic_state: string;
  proposer_type: string;
  receiving_lecturer_id: string | null;
  receiving_lecturer_user_id: string | null;
  receiving_lecturer_name: string | null;
  lecturer_reason: string | null;
};
export type SearchHit = {
  source_id: string;
  source_type: string;
  origin_type: string;
  title: string;
  score: number;
  provenance: string;
  source_ref: string | null;
  source_url: string | null;
  source_version: string;
  representation: string;
  excerpt: string;
};

export type RegistrationFormVersion = {id:string;version_no:number;form_code:"1A"|"1B";file_name:string;
  byte_size:number;scan_state:string;submitted_at:string;submitted_by_name:string;current:boolean};
export type RegistrationForms = {form_code:"1A"|"1B";can_submit:boolean;registration_version:number;versions:RegistrationFormVersion[]};

export function uploadRegistrationForm(registrationId:string,userId:string,forms:RegistrationForms,file:File) {
  return request<RegistrationForms>(`/topic-registrations/${registrationId}/forms`,userId,{method:"POST",body:file,
    headers:{"Content-Type":"application/octet-stream","X-File-Name":encodeURIComponent(file.name),
      "X-Form-Code":forms.form_code,"If-Match":String(forms.registration_version)}});
}

export async function downloadRegistrationForm(registrationId:string,version:RegistrationFormVersion,printCopy=false) {
  const response=await fetch(`${baseUrl}/api/v1/topic-registrations/${registrationId}/forms/${version.id}/${printCopy?"print-copy":"download"}`,{
    method:printCopy?"POST":"GET",credentials:"include",headers:{...(sessionCsrfToken?{"X-CSRF-Token":sessionCsrfToken}:{})}});
  if(!response.ok) {const body=await response.json().catch(()=>null);throw new Error(body?.detail||`HTTP ${response.status}`);}
  const url=URL.createObjectURL(await response.blob());const link=document.createElement("a");link.href=url;
  link.download=printCopy?responseFileName(response,"Ban-in-v"+version.version_no+"-"+version.file_name):version.file_name;
  link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

// Local dev uses Vite proxy so UI and API share one origin and session cookie.
const baseUrl = import.meta.env.VITE_API_URL
  || (import.meta.env.DEV ? "" : `${window.location.protocol}//${window.location.hostname}:8000`);
export const apiAssetUrl = (path:string) => baseUrl + path;
let sessionCsrfToken: string | null = null;

export function evidenceUrl(registrationId: string, studentId: string) {
  return `${baseUrl}/api/v1/topic-registrations/${registrationId}/members/${studentId}/evidence`;
}

export function uploadEvidence(registrationId: string, userId: string, file: File): Promise<Registration> {
  return request<Registration>(`/topic-registrations/${registrationId}/evidence`, userId, {
    method: "POST", body: file,
    headers: {"Content-Type": "application/octet-stream", "X-File-Name": encodeURIComponent(file.name)},
  });
}

export type AuthenticationMode = "development" | "university_oidc" | "local_email" | "unavailable";
export type DemoAccount = { key: string; email: string; role: string; label: string };

export function setSessionCsrfToken(token: string | null) {
  sessionCsrfToken = token;
}

export function universityLoginUrl() {
  return `${baseUrl}/api/v1/auth/login`;
}

export async function emailLogin(email: string, password: string): Promise<void> {
  await request<void>("/auth/login", "", {
    method: "POST", body: JSON.stringify({ email, password }),
  });
}

export function listDemoAccounts(): Promise<DemoAccount[]> {
  return request<DemoAccount[]>("/auth/demo-accounts", "");
}

export async function demoLogin(key: string): Promise<void> {
  await request<void>("/auth/demo-login", "", {
    method: "POST", body: JSON.stringify({ key }),
  });
}

export async function logout(): Promise<void> {
  await request<void>("/auth/logout", "", { method: "POST" });
}

export async function request<T>(
  path: string, userId: string, init: RequestInit = {},
): Promise<T> {
  let response: Response;
  const method = (init.method || "GET").toUpperCase();
  const abort = new AbortController();
  const fileOperation = init.body instanceof File || init.body instanceof FormData || path.endsWith("/scan") || path.startsWith("/school-forms/bootstrap/");
  const timer = window.setTimeout(() => abort.abort(), fileOperation ? 120000 : path.startsWith("/ai/") || path.includes("/roster") || path.endsWith("/activation-link") ? 90000 : 30000);
  try { response = await fetch(baseUrl + "/api/v1" + path, {
    ...init,
    credentials: "include",
    signal: init.signal || abort.signal,
    headers: {
      ...(!(init.body instanceof FormData) ? {"Content-Type": "application/json"} : {}),
      ...(sessionCsrfToken && !["GET", "HEAD", "OPTIONS"].includes(method)
        ? { "X-CSRF-Token": sessionCsrfToken } : {}),
      ...(init.headers || {}),
    },
  }); } catch {
    throw new Error("Không kết nối được máy chủ hoặc yêu cầu quá lâu. Kiểm tra kết nối rồi thử lại.");
  } finally {window.clearTimeout(timer);}
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    if (response.status === 401 && path !== "/auth/login" && path !== "/me/context") {
      sessionCsrfToken = null;
      window.dispatchEvent(new Event("kltn:session-expired"));
    }
    throw new ApiError(response.status, apiMessage(response.status, body?.detail, path));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function downloadLecturerImportTemplate() {
  const response = await fetch(`${baseUrl}/api/v1/admin/lecturers/import-template`, {credentials: "include"});
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, apiMessage(response.status, body?.detail));
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url; link.download = "danh-sach-giang-vien-mau.xlsx"; link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export type Thesis = {
  id: string;
  registration_id?: string;
  title: string;
  extension_until_at?: string | null;
  state: string;
  member_student_ids: string[];
  advisor_lecturer_id: string | null;
  advisor_name: string | null;
  row_version: number;
  round_id: string;
  round_label: string;
  members: {student_id: string; display_name: string; student_code: string; is_coordinator: boolean}[];
  advisor_history: {id: string; lecturer_id: string; display_name: string; state: string; effective_from: string; effective_to: string | null}[];
  pending_advisor: {lecturer_id: string; display_name: string} | null;
  cross_reviewers: {lecturer_id: string; display_name: string}[];
  actions: string[];
};
export type Milestone = {id: string; code: string; title: string; version_no: number; row_version: number; state: string; due_at: string | null; expected_ratio: number | null};
export type DocumentDeadline = {id: string; document_type: "PROPOSAL" | "PLAN" | "REPORT" | "SUPPORTING"; due_at: string; state: "OPEN" | "CLOSED"; row_version: number; reason: string};
export type Review = {reviewer_name: string; decision: string; comment: string; created_at: string};
export type ProgressReport = {id: string; milestone_id: string; version_no: number; row_version: number; state: string; summary: string; reported_ratio: number | null; submitted_by_name: string; submitted_by_student_id: string; submitted_at: string; due_at_at_submission: string | null; late: boolean; evidence_document_version_id: string | null; evidence_scan_state: string | null; evidence_file_name: string | null; reviews: Review[]};
export type ProgressAnnotationKind = "PIN" | "SUMMARY" | "ATTACHMENT";
export type ReviewAttachment = {file_name: string; byte_size: number; scan_state: string};
export type ProgressAnnotationData = {annotation_kind?: ProgressAnnotationKind; page_number: number | null; x: number | null; y: number | null; location_label: string; quoted_text: string; comment: string};
export type ProgressAnnotation = ProgressAnnotationData & {annotation_kind: ProgressAnnotationKind; attachment?: ReviewAttachment | null; id: string; reviewer_id: string; reviewer_name: string; state: "DRAFT" | "PUBLISHED"; row_version: number; updated_at: string; published_at: string | null};
export type ProgressAnnotations = {annotations: ProgressAnnotation[]; can_edit: boolean; read_only_reason?: string | null};

export function fetchProgressEvidence(thesisId: string, reportId: string, signal: AbortSignal): Promise<ArrayBuffer> {
  return fetchReviewFile(`/theses/${thesisId}/progress-reports/${reportId}/evidence`, signal);
}

export async function fetchReviewFile(path: string, signal?: AbortSignal): Promise<ArrayBuffer> {
  const response = await fetch(`${baseUrl}/api/v1${path}`, {credentials: "include", signal});
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, apiMessage(response.status, body?.detail));
  }
  return response.arrayBuffer();
}

export function uploadProgressEvidence(thesisId: string, report: ProgressReport, userId: string, file: File) {
  return request<ProgressReport>(`/theses/${thesisId}/progress-reports/${report.id}/evidence`, userId, {
    method: "POST", body: file,
    headers: {"Content-Type": "application/octet-stream", "X-File-Name": encodeURIComponent(file.name), "If-Match": String(report.row_version)},
  });
}

export function submitProgress(thesisId: string, userId: string, data: object, file: File | null) {
  if (!file) return request<ProgressReport>(`/theses/${thesisId}/progress-reports`, userId,
    {method:"POST", body:JSON.stringify(data)});
  const form = new FormData();
  form.append("report", JSON.stringify(data)); form.append("file", file);
  return request<ProgressReport>(`/theses/${thesisId}/progress-submissions`, userId, {method:"POST", body:form});
}

export async function downloadProgressEvidence(thesisId: string, report: ProgressReport) {
  const response = await fetch(`${baseUrl}/api/v1/theses/${thesisId}/progress-reports/${report.id}/evidence`, {credentials:"include"});
  if (!response.ok) {
    const body = await response.json().catch(()=>null);
    throw new Error(body?.detail || `HTTP ${response.status}`);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a"); link.href=url; link.download=report.evidence_file_name || "minh-chung"; link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export type DocumentVersion = {id: string; version_no: number; row_version: number; state: string; file_name: string; byte_size: number; sha256: string; scan_state: string; submitted_at: string; due_at_at_submission: string | null; late: boolean; submitted_by_name: string; reviews: Review[]};
export type ThesisDocument = {id: string; title: string; document_type: "PLAN" | "REPORT" | "PROPOSAL" | "SUPPORTING"; row_version: number; visibility: string; versions: DocumentVersion[]};
export type WorkAssignment = {id: string; student_id: string; student_name: string; version_no: number; row_version: number; work_description: string; expected_output: string; state: string; review_comment: string | null; reviewed_by_name: string | null};
export type AuditEvent = {action: string; actor_name: string; reason: string | null; occurred_at: string};
export type PrintExport = {id: string; actor_name: string; document_code: string; version_no: number; exported_at: string; copy_status: "SUBMITTED" | "APPROVED"};
export type Proposal = {
  id: string | null;
  thesis_id: string;
  state: string;
  row_version: number;
  current_version_no: number | null;
  versions: {id: string; version_no: number; file_name: string; byte_size: number; sha256: string; scan_state: string; submitted_by_name: string; submitted_at: string; due_at_at_submission: string | null; late: boolean; reviews: Review[]}[];
  reviewers: {lecturer_id: string; display_name: string}[];
  department_confirmed: boolean;
  dean_confirmed: boolean;
};

export function uploadProposal(thesisId: string, proposal: Proposal, userId: string, file: File) {
  return request<Proposal>(`/theses/${thesisId}/proposal/versions`, userId, {
    method: "POST", body: file,
    headers: {"Content-Type": "application/octet-stream", "X-File-Name": encodeURIComponent(file.name), "If-Match": String(proposal.row_version)},
  });
}

export async function downloadProposal(thesisId: string, version: Proposal["versions"][number], _userId: string, printCopy=false) {
  const response = await fetch(`${baseUrl}/api/v1/theses/${thesisId}/proposal/versions/${version.id}/${printCopy ? "print-copy" : "download"}`, {
    method: printCopy ? "POST" : "GET", credentials: "include",
    headers: { ...(sessionCsrfToken ? {"X-CSRF-Token": sessionCsrfToken} : {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `HTTP ${response.status}`);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download=printCopy?responseFileName(response,"Ban-in-v"+version.version_no+"-"+version.file_name):version.file_name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function uploadDocument(thesisId: string, doc: ThesisDocument, userId: string, file: File) {
  return request<ThesisDocument>(`/theses/${thesisId}/documents/${doc.id}/versions`, userId, {
    method: "POST", body: file,
    headers: {"Content-Type": "application/octet-stream", "X-File-Name": encodeURIComponent(file.name), "If-Match": String(doc.row_version)},
  });
}

export type OfficialFormTemplate = {
  id: string;
  title: string;
  filename: string;
  byte_size: number;
  extension: string;
};

export async function listFormTemplates(userId?: string, roundId?: string): Promise<OfficialFormTemplate[]> {
  return request<OfficialFormTemplate[]>("/form-templates"+(roundId ? `?round_id=${roundId}` : ""), userId || "");
}

export async function downloadOfficialTemplate(templateId: string, filename: string, roundId?: string) {
  const response = await fetch(`${baseUrl}/api/v1/form-templates/${templateId}/download${roundId ? `?round_id=${roundId}` : ""}`, {credentials: "include"});
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `HTTP ${response.status}`);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = decodeURIComponent(response.headers.get("Content-Disposition")?.match(/filename\*=UTF-8\'\'([^;]+)/i)?.[1] || filename);
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function exportThesisReview(thesisId:string, reviewId:string, version:number) {
  const response=await fetch(`${baseUrl}/api/v1/theses/${thesisId}/evaluation/reviews/${reviewId}/print-copy`, {
    method:"POST",credentials:"include",headers:{"If-Match":String(version),...(sessionCsrfToken?{"X-CSRF-Token":sessionCsrfToken}:{})},
  });
  if(!response.ok){const data=await response.json().catch(()=>null);throw new ApiError(response.status,apiMessage(response.status,data?.detail));}
  const url=URL.createObjectURL(await response.blob());const anchor=document.createElement("a");
  anchor.href=url;anchor.download=decodeURIComponent(response.headers.get("Content-Disposition")?.match(/filename\*=UTF-8\x27\x27([^;]+)/i)?.[1] || (response.headers.get("X-Document-Code")||"phieu-nhan-xet")+".docx");anchor.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

async function downloadFormTemplate(kind: "plan" | "proposal", name: string, roundId?: string) {
  const response = await fetch(`${baseUrl}/api/v1/form-templates/${kind}${roundId ? `?round_id=${roundId}` : ""}`, {credentials: "include"});
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `HTTP ${response.status}`);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = decodeURIComponent(response.headers.get("Content-Disposition")?.match(/filename\*=UTF-8\'\'([^;]+)/i)?.[1] || name);
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const downloadPlanTemplate = (roundId?: string) => downloadFormTemplate("plan", "mau-02-ke-hoach.docx", roundId);
export const downloadProposalTemplate = (roundId?: string) => downloadFormTemplate("proposal", "mau-03-de-cuong.docx", roundId);

export async function downloadDocument(thesisId: string, doc: ThesisDocument, version: DocumentVersion, _userId: string, printCopy=false) {
  const response = await fetch(`${baseUrl}/api/v1/theses/${thesisId}/documents/${doc.id}/versions/${version.id}/${printCopy ? "print-copy" : "download"}`, {
    method: printCopy ? "POST" : "GET", credentials: "include",
    headers: { ...(sessionCsrfToken ? {"X-CSRF-Token": sessionCsrfToken} : {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `HTTP ${response.status}`);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download=printCopy?responseFileName(response,"Ban-in-v"+version.version_no+"-"+version.file_name):version.file_name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export type Citation = {
  source_id: string; source_type: string; origin_type: string; title: string;
  provenance: string; source_ref: string | null; source_url: string | null;
  source_version: string; representation: string; excerpt: string;
};
export type ChatResult = {
  status: "NO_EVIDENCE" | "RETRIEVAL_ONLY" | "ANSWERED";
  answer: string | null;
  citations: Citation[];
  provider_status: "NOT_CONFIGURED";
};

export type SchoolFormRound = {id:string;label:string;state:string;can_manage:boolean;can_view_publications:boolean;can_export_list:boolean};

export async function exportRoundMau04(roundId:string) {
  const response=await fetch(`${baseUrl}/api/v1/school-forms/rounds/${encodeURIComponent(roundId)}/mau-04`,{
    method:"POST",credentials:"include",headers:sessionCsrfToken?{"X-CSRF-Token":sessionCsrfToken}:{},
  });
  if(!response.ok){const data=await response.json().catch(()=>null);throw new ApiError(response.status,apiMessage(response.status,data?.detail));}
  const url=URL.createObjectURL(await response.blob());const link=document.createElement("a");
  link.href=url;link.download="danh-sach-sv-gvhd-mau-04.xlsx";link.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export type SchoolFormVersion = {id:string;version_no:number;row_version:number;state:string;file_name:string;byte_size:number;scan_state:string;uploaded_at:string;uploaded_by_name:string;source_reference:string;change_reason:string;published_at:string|null};
export type SchoolForm = {id:string;round_id:string;code:string;title:string;document_kind:"FORM"|"PUBLICATION";audience:"STUDENT_AND_LECTURER"|"LECTURER";state:string;row_version:number;versions:SchoolFormVersion[]};
