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

export type MatchItem = {
  credential_type_id: string;
  name: string;
  required: boolean;
  must_be_verified: boolean;
  state: 'ok' | 'pending' | 'missing';
};

export type PostingCard = {
  id: string;
  title: string;
  trade: string;
  posting_type: 'individual' | 'agency';
  org: { id: string; name: string; kind: string; verified: boolean };
  city: string;
  start_date: string;
  end_date: string;
  schedule_pattern: string;
  is_exclusive: boolean;
  pay_rate_cents: number;
  pay_unit: 'hour' | 'day' | 'fixed';
  headcount: number;
  status: 'draft' | 'open' | 'filled' | 'closed';
  created_at: string;
  match: { required_total: number; required_held: number; items: MatchItem[] };
  eligible: boolean;
  reasons: string[];
  distance_km?: number | null;
  score?: number | null;
  score_breakdown?: { label: string; points: number }[];
  is_new?: boolean;
  site_address?: string | null;
  description?: string | null;
  applicants?: number | null;
  new_applicants?: number | null;
  offers_out?: number | null;
  hired?: number | null;
};

export type Feed = { items: PostingCard[]; new_count: number };

export type ApplicantSummary = {
  kind: 'worker' | 'agency';
  id: string;
  name: string;
  headline: string;
  city: string;
  distance_km?: number | null;
  verified?: boolean | null;
};

export type EngagementSummary = {
  id: string;
  start_date: string;
  end_date: string;
  is_exclusive: boolean;
  schedule_pattern: string;
  status: 'active' | 'completed' | 'cancelled';
  calendar_synced: boolean;
};

export type ApplicationStatus =
  | 'applied'
  | 'invited'
  | 'shortlisted'
  | 'offered'
  | 'accepted'
  | 'declined'
  | 'withdrawn'
  | 'completed';

export type ApplicationView = {
  id: string;
  status: ApplicationStatus;
  note: string;
  proposed_rate_cents: number | null;
  crew_size: number | null;
  initiated_by: string;
  created_at: string;
  updated_at: string;
  applicant: ApplicantSummary;
  posting: PostingCard;
  engagement: EngagementSummary | null;
};

export type PostingDetail = {
  posting: PostingCard;
  description: string;
  is_owner: boolean;
  my_application: ApplicationView | null;
};

export type WorkView = {
  applied: ApplicationView[];
  offers: ApplicationView[];
  active: ApplicationView[];
  past: ApplicationView[];
};

export type OrgEngagement = {
  engagement: EngagementSummary;
  application_id: string;
  posting_id: string;
  posting_title: string;
  applicant: ApplicantSummary;
};

export type OrgWork = { postings: PostingCard[]; active: OrgEngagement[]; past: OrgEngagement[] };

export type HomeView = {
  next_shift: {
    application_id: string;
    posting_title: string;
    org_name: string;
    start_date: string;
    end_date: string;
    city: string;
  } | null;
  offers: ApplicationView[];
  expiring: Credential[];
  new_applicants: {
    application_id: string;
    posting_id: string;
    posting_title: string;
    name: string;
    created_at: string;
  }[];
  offers_awaiting: number;
  open_postings: number;
  active_contracts: number;
};

export type TalentCard = {
  id: string;
  name: string;
  headline: string;
  trades: string[];
  city: string;
  distance_km: number | null;
  verified_tickets: number;
  tickets: number;
};

export type AcceptPreview = {
  is_exclusive: boolean;
  conflicts: { engagement_id: string; title: string; message: string }[];
  ticket_problems: string[];
  overlapping: ApplicationView[];
  manual_overlaps: { id: string; start_date: string; end_date: string; note: string }[];
};

export type CalendarResult = {
  status: 'added' | 'needs_auth' | 'unavailable';
  url?: string | null;
  count?: number | null;
  message?: string | null;
};

export type ScheduleItem = {
  id: string;
  kind: 'engagement' | 'manual';
  start_date: string;
  end_date: string;
  title: string;
  subtitle: string;
  posting_id?: string | null;
  engagement_id?: string | null;
  status?: string | null;
};

export type ScheduleView = {
  items: ScheduleItem[];
  calendar_enabled: boolean;
  calendar_connected: boolean;
};

export type DemoAccount = {
  id: string;
  full_name: string;
  email: string;
  mode: Mode | null;
  label: string;
};
