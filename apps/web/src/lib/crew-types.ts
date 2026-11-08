/** Mirror of apps/api/shift_api/crew_routes.py. */
export type Spot = {
  assignment_id: string;
  user_id: string;
  name: string;
  status: 'assigned' | 'proposed';
};
export type CertRef = { id: string; name: string };
export type CrewSlot = {
  id: string;
  day: string;
  start_minute: number;
  end_minute: number;
  label: string;
  needed: number;
  preferred_cert: CertRef | null;
  required_certs: CertRef[];
  spots: Spot[];
};
export type CrewRules = {
  max_consecutive_days: number;
  min_rest_hours: number;
  max_weekly_hours: number;
};
export type CrewWeek = {
  start: string;
  slots: CrewSlot[];
  rules: CrewRules;
  crew_size: number;
  proposed: number;
};
export type BreakdownRow = { kind: string; label: string; points: number; strength: number };
export type Candidate = {
  user_id: string;
  name: string;
  headline: string;
  on_crew: boolean;
  certs: { id: string; name: string; state: string; kind: 'required' | 'preferred' }[];
  score: number;
  breakdown: BreakdownRow[];
  warnings: string[];
  blockers: string[];
  bar: { free: number[][]; booked: number[][]; slot: number[] };
};
export type AutofillResult = {
  proposed: number;
  unfilled_slot_ids: string[];
  solver_status: string;
};

export function clock(minutes: number) {
  const m = ((minutes % 1440) + 1440) % 1440;
  const h = Math.floor(m / 60);
  const mm = m % 60;
  const suffix = h < 12 ? 'AM' : 'PM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return mm ? `${h12}:${String(mm).padStart(2, '0')} ${suffix}` : `${h12} ${suffix}`;
}

export const shiftTime = (s: CrewSlot) => `${clock(s.start_minute)}–${clock(s.end_minute)}`;
