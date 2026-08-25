// Resume Platform — API client (server base path /api/v1, proxied via Next rewrites).
// Auth: Bearer token (Keycloak OIDC access token).

export type ResumeStatus = "pending" | "processing" | "completed" | "failed";

export interface ATSScore {
  overall: number;
  keywords_match: number;
  formatting: number;
  completeness: number;
  section_scores: Record<string, number>;
  missing_keywords: string[];
  recommendations: string[];
}

export interface ResumeImprovement {
  rewritten_sections: Record<string, string>;
  suggestions: string[];
  keyword_suggestions: string[];
  formatting_tips: string[];
  ats_score_after?: number;
}

export interface ResumeResult {
  id: string;
  user_id?: string;
  filename: string;
  ocr_json: Record<string, unknown>;
  ats_score?: ATSScore | null;
  improvements?: ResumeImprovement | null;
  status: ResumeStatus;
  job_title?: string | null;
  experience_years?: number | null;
  created_at: string;
  updated_at?: string;
}

export interface ResumeListItem {
  id: string;
  filename: string;
  status: ResumeStatus;
  job_title?: string | null;
  created_at: string;
  ats_score?: number;
}

export interface ListResumesResponse {
  resumes: ResumeListItem[];
  total: number;
}

async function request<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 8000);
  try {
    const res = await fetch(`/api/v1${path}`, {
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      ...init,
      signal: ctrl.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Request failed" }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    if (res.status === 204) return {} as T;
    return (await res.json()) as T;
  } catch (e: any) {
    if (e?.name === "AbortError") throw new Error("Backend unreachable.");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  verify: (token: string) => request<{ valid: boolean; user: Record<string, unknown> }>("/auth/verify", token),

  list: (token: string) =>
    request<ListResumesResponse>("/resume/", token),

  get: (id: string, token: string) =>
    request<ResumeResult>(`/resume/${encodeURIComponent(id)}`, token),

  upload: async (
    token: string,
    file: File,
    jobTitle: string,
    experienceYears?: number,
  ): Promise<{ resume_id: string; status: ResumeStatus; message: string }> => {
    const fd = new FormData();
    fd.append("file", file);
    if (jobTitle) fd.append("job_title", jobTitle);
    if (experienceYears != null) fd.append("experience_years", String(experienceYears));
    const res = await fetch(`/api/v1/resume/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Upload failed" }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return (await res.json()) as { resume_id: string; status: ResumeStatus; message: string };
  },

  regenerate: (id: string, token: string) =>
    request<{ status: string; resume_id: string; ats_score: unknown; improvements: unknown }>(
      `/resume/${encodeURIComponent(id)}/regenerate`,
      token,
      { method: "POST" },
    ),

  remove: (id: string, token: string) =>
    request<{ message: string; deleted: boolean }>(`/resume/${encodeURIComponent(id)}`, token, {
      method: "DELETE",
    }),
};
