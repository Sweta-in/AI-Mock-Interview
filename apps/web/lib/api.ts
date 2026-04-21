/**
 * PrepAI — API client for backend communication.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiOptions {
  method?: string;
  body?: Record<string, unknown>;
  token?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, options: ApiOptions = {}): Promise<T> {
    const { method = 'GET', body, token } = options;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new ApiError(response.status, error.detail || error.error || 'Request failed', error);
    }

    return response.json();
  }

  // ── Auth ──────────────────────────────────────────────────────────────

  async getProfile(token: string) {
    return this.request<{
      id: string;
      email: string;
      full_name: string;
      plan: string;
      interviews_used_this_month: number;
    }>('/api/v1/users/me', { token });
  }

  // ── Interview Roles ───────────────────────────────────────────────────

  async getRoles(token: string) {
    return this.request<Array<{
      id: string;
      slug: string;
      display_name: string;
      category: string;
      competencies: string[];
      is_active: boolean;
    }>>('/api/v1/interviews/roles', { token });
  }

  // ── Interviews ────────────────────────────────────────────────────────

  async createInterview(token: string, data: {
    role_slug: string;
    difficulty: string;
    interview_type: string;
    resume_text?: string;
  }) {
    return this.request<{
      id: string;
      session_token: string;
      status: string;
      role_slug: string;
    }>('/api/v1/interviews', { method: 'POST', body: data as Record<string, unknown>, token });
  }

  async listInterviews(token: string, page = 1, pageSize = 10) {
    return this.request<{
      interviews: Array<{
        id: string;
        role_slug: string;
        role_name: string;
        status: string;
        difficulty: string;
        interview_type: string;
        started_at: string | null;
        completed_at: string | null;
        duration_seconds: number | null;
        overall_score: number | null;
        question_count: number;
      }>;
      total: number;
      page: number;
      page_size: number;
    }>(`/api/v1/interviews?page=${page}&page_size=${pageSize}`, { token });
  }

  async getInterview(token: string, interviewId: string) {
    return this.request<Record<string, unknown>>(`/api/v1/interviews/${interviewId}`, { token });
  }

  async startInterview(token: string, interviewId: string) {
    return this.request<{
      interview_id: string;
      session_token: string;
      websocket_url: string;
    }>(`/api/v1/interviews/${interviewId}/start`, { method: 'POST', token });
  }

  async abandonInterview(token: string, interviewId: string) {
    return this.request<{ message: string }>(`/api/v1/interviews/${interviewId}/abandon`, {
      method: 'POST',
      token,
    });
  }

  async getReport(token: string, interviewId: string) {
    return this.request<{
      status: string;
      interview_id: string;
      executive_summary?: string;
      overall_score?: number;
      dimension_scores?: Record<string, number>;
      top_strengths?: string[];
      top_improvements?: string[];
      skill_breakdown?: Record<string, { score: number; summary: string }>;
      recommended_next_steps?: string[];
      comparison_benchmark?: string;
    }>(`/api/v1/interviews/${interviewId}/report`, { token });
  }

  // ── Feedback ──────────────────────────────────────────────────────────

  async getSkillSnapshots(token: string) {
    return this.request<{
      snapshots: Array<{
        snapshot_date: string;
        skill_scores: Record<string, number>;
        interviews_count: number;
        role_id: string | null;
      }>;
    }>('/api/v1/feedback/skills', { token });
  }
}

export class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;

  constructor(status: number, message: string, data: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

export const api = new ApiClient(API_BASE);
