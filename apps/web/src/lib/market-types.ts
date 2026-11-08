/** Frontend mirror of apps/api/shift_api/market_schemas.py. */
export type Mode = 'worker' | 'business' | 'agency';

export type UserView = {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  is_admin: boolean;
};

export type WorkerProfileView = {
  handle: string;
  headline: string;
  trades: string[];
  city: string;
  travel_radius_km: number;
  rate_min_cents: number | null;
  rate_max_cents: number | null;
  bio: string;
  linkedin_url: string | null;
  is_public: boolean;
};

export type OrgView = {
  id: string;
  name: string;
  kind: 'business' | 'agency';
  handle: string | null;
  industry: string | null;
  city: string | null;
  website: string | null;
  about: string | null;
  verification_status: string;
};

export type Me = {
  user: UserView;
  mode: Mode | null;
  onboarded: boolean;
  worker_profile: WorkerProfileView | null;
  organization: OrgView | null;
  planner_persona: string | null;
  calendar_connected: boolean;
};

export type Meta = {
  trades: string[];
  industries: string[];
  cities: { name: string; lat: number; lng: number }[];
  schedule_patterns: Record<string, string>;
};

export type CredentialStatus = 'self_reported' | 'pending' | 'verified' | 'expired' | 'rejected';

export type CredentialType = {
  id: string;
  name: string;
  category: string;
  default_issuer: string;
  applies_to: 'worker' | 'org';
  has_expiry: boolean;
};

export type Credential = {
  id: string;
  credential_type_id: string | null;
  name: string;
  category: string;
  issuer: string;
  number: string | null;
  issued_on: string | null;
  expires_on: string | null;
  status: CredentialStatus;
  expiring_soon: boolean;
  days_to_expiry: number | null;
  has_document: boolean;
  document_name: string | null;
  rejection_reason: string | null;
};

export type WorkHistory = {
  id: string;
  role: string;
  company: string;
  city: string;
  start_date: string;
  end_date: string | null;
  description: string;
  reference_name: string | null;
  reference_contact: string | null;
  engagement_id: string | null;
};

export type Completeness = {
  percent: number;
  steps: { key: string; label: string; done: boolean }[];
  next_step: { key: string; label: string; credential_type_id?: string | null } | null;
};

export type Profile = {
  user: UserView;
  profile: WorkerProfileView;
  credentials: Credential[];
  history: WorkHistory[];
  completeness: Completeness;
};

export type OrgProfile = { organization: OrgView; credentials: Credential[] };

export type Notification = {
  id: string;
  type: string;
  payload: Record<string, string | number | null>;
  read_at: string | null;
  created_at: string;
};
export type Notifications = { unread: number; work_badge: number; items: Notification[] };

export type DemoAccount = {
  id: string;
  full_name: string;
  email: string;
  mode: Mode | null;
  label: string;
};
