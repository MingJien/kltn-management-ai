export type Context = {
  user_id: string;
  base_role: string;
  student_id: string | null;
  lecturer_id: string | null;
  actions: string[];
};
export type Topic = {
  id: string;
  round_id: string;
  title: string;
  description: string | null;
  max_students: number;
  state: string;
};
export type EligibleStudent = { id: string; display_name: string; student_code: string };
export type RegistrationMember = {
  student_id: string;
  student_code: string;
  display_name: string;
  is_coordinator: boolean;
  active: boolean;
  consent_status: "PENDING" | "ACCEPTED" | "DECLINED";
};
export type Registration = {
  id: string;
  topic_id: string;
  round_id: string;
  state: string;
  row_version: number;
  member_student_ids: string[];
  members: RegistrationMember[];
  lecturer_decided_at: string | null;
  thesis_id: string | null;
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

const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
let developmentAuthEnabled = false;

export type AuthenticationMode = "development" | "university_oidc" | "unavailable";

export function setDevelopmentAuthEnabled(enabled: boolean) {
  developmentAuthEnabled = enabled;
}

export function universityLoginUrl() {
  return `${baseUrl}/api/v1/auth/login`;
}

export async function request<T>(
  path: string, userId: string, init: RequestInit = {},
): Promise<T> {
  const response = await fetch(baseUrl + "/api/v1" + path, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(developmentAuthEnabled && userId ? { "X-Dev-User-Id": userId } : {}),
      ...(init.headers || {}),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type Thesis = {
  id: string;
  title: string;
  state: string;
  member_student_ids: string[];
  advisor_lecturer_id: string;
};
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
