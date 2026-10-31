// API client for backend communication
import type {
  User,
  Token,
  Consent,
  ChatResponse,
  MemoryBlock,
} from '../types';

const API_BASE = '/api/v1';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('token');

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const text = await response.text();
    const contentType = response.headers.get('content-type')?.toLowerCase() ?? '';
    let message = `Request failed (${response.status})`;

    try {
      const json = JSON.parse(text);
      if (typeof json.detail === 'string') {
        message = json.detail;
      } else if (typeof json.message === 'string') {
        message = json.message;
      }
    } catch {
      if (!contentType.includes('text/html') && text.trim()) {
        message = text;
      }
    }

    if (response.status >= 500) {
      message = response.status === 502 || response.status === 503 || response.status === 504
        ? 'The server is temporarily unavailable. Please try again later.'
        : 'The server encountered an error. Please try again later.';
    }

    throw new ApiError(response.status, message);
  }

  return response.json();
}

// Auth API
export const authApi = {
  register: (email: string, password: string, fullName?: string) =>
    request<User>('/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName }),
    }),

  login: (email: string, password: string) =>
    request<Token>('/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>('/me'),
};

// Consent API
export const consentApi = {
  get: () => request<Consent[]>('/consent'),

  update: (purpose: string, granted: boolean, policyVersion = '1.0') =>
    request<Consent>('/consent', {
      method: 'PUT',
      body: JSON.stringify({ purpose, granted, policy_version: policyVersion }),
    }),

  getRequired: () =>
    request<{ purposes: Record<string, string>; required_for_ai: string[] }>(
      '/consent/required'
    ),
};

// Chat API
export const chatApi = {
  send: (message: string, countryCode?: string | null) =>
    request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, country_code: countryCode ?? null }),
    }),
};

// Optional, user-initiated IP-based country estimate
export const locationApi = {
  estimateCountry: () =>
    request<{ country_code: string }>('/location/country'),
};

// Memory API
export const memoryApi = {
  get: () => request<MemoryBlock[]>('/memory'),

  deleteAll: () =>
    request<{ success: boolean; message: string }>('/memory', {
      method: 'DELETE',
    }),
};

export { ApiError };