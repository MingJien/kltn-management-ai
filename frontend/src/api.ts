import { ApiError, apiMessage } from "./errors";

export type Context = {
  user_id: string;
  base_role: string;
  student_id: string | null;
  lecturer_id: string | null;
  actions: string[];
  display_name: string;
  department_id: string | null;
  email: string | null;
  student_code: string | null;
  class_name: string | null;
  major_code: string | null;
  lecturer_code: string | null;
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
};
export type Requirement = {requirement_type: "PREFERRED_GPA" | "SKILL" | "TECHNOLOGY" | "KNOWLEDGE" | "OTHER"; value_text: string; preferred_gpa: number | null};
export type Lecturer = {id: string; display_name: string; lecturer_code: string};
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

// Keep local API and UI on the same hostname (localhost or 127.0.0.1).
// A session cookie issued for one hostname is not sent to the other.
const baseUrl = import.meta.env.VITE_API_URL
  || `${window.location.protocol}//${window.location.hostname}:8000`;
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
  const timer = window.setTimeout(() => abort.abort(), path.startsWith("/ai/") || path.includes("/roster") ? 90000 : 30000);
  try { response = await fetch(baseUrl + "/api/v1" + path, {
    ...init,
    credentials: "include",
    signal: init.signal || abort.signal,
    headers: {
      "Content-Type": "application/json",
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

export type Thesis = {
  id: string;
  title: string;
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
export type Review = {reviewer_name: string; decision: string; comment: string; created_at: string};
export type ProgressReport = {id: string; milestone_id: string; version_no: number; row_version: number; state: string; summary: string; reported_ratio: number | null; submitted_by_name: string; submitted_at: string; due_at_at_submission: string | null; late: boolean; evidence_document_version_id: string | null; reviews: Review[]};
export type DocumentVersion = {id: string; version_no: number; row_version: number; state: string; file_name: string; byte_size: number; sha256: string; scan_state: string; submitted_at: string; submitted_by_name: string; reviews: Review[]};
export type ThesisDocument = {id: string; title: string; document_type: "PLAN" | "REPORT" | "PROPOSAL" | "SUPPORTING"; row_version: number; visibility: string; versions: DocumentVersion[]};
export type WorkAssignment = {id: string; student_id: string; student_name: string; version_no: number; row_version: number; work_description: string; expected_output: string; state: string; review_comment: string | null; reviewed_by_name: string | null};
export type AuditEvent = {action: string; actor_name: string; reason: string | null; occurred_at: string};
export type Proposal = {
  id: string | null;
  thesis_id: string;
  state: string;
  row_version: number;
  current_version_no: number | null;
  versions: {id: string; version_no: number; file_name: string; byte_size: number; sha256: string; scan_state: string; submitted_by_name: string; submitted_at: string; reviews: Review[]}[];
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
  link.download = printCopy ? `${response.headers.get("X-Document-Code") || `de-cuong-v${version.version_no}`}.${version.file_name.split(".").pop()}` : version.file_name;
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

export async function listFormTemplates(userId?: string): Promise<OfficialFormTemplate[]> {
  return request<OfficialFormTemplate[]>("/form-templates", userId || "");
}

export async function downloadOfficialTemplate(templateId: string, filename: string) {
  const response = await fetch(`${baseUrl}/api/v1/form-templates/${templateId}/download`, {credentials: "include"});
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `HTTP ${response.status}`);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function downloadFormTemplate(kind: "plan" | "proposal", name: string) {
  const response = await fetch(`${baseUrl}/api/v1/form-templates/${kind}`, {credentials: "include"});
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `HTTP ${response.status}`);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const downloadPlanTemplate = () => downloadFormTemplate("plan", "mau-02-ke-hoach.docx");
export const downloadProposalTemplate = () => downloadFormTemplate("proposal", "mau-03-de-cuong.docx");

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
  link.download = printCopy ? `${response.headers.get("X-Document-Code") || `ban-in-v${version.version_no}`}.${version.file_name.split(".").pop()}` : version.file_name;
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
