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

export type DemoAccount = {
  id: string;
  full_name: string;
  email: string;
  mode: Mode | null;
  label: string;
};
