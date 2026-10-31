// API Types

export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
  letta_agent_id?: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface Consent {
  id: string;
  user_id: string;
  purpose: string;
  granted: boolean;
  policy_version: string;
  granted_at?: string;
  withdrawn_at?: string;
  created_at: string;
}

export interface ChatResponse {
  workflow: 'routine' | 'follow_up' | 'urgent' | 'professional_referral' | 'review_unavailable';
  message: string;
  clarifying_question?: string;
  urgent_help_info?: string;
  service_unavailable?: boolean;
  support_url?: string;
}

export interface MemoryBlock {
  id: string;
  content: string;
  memory_type: string;
  created_at: string;
}