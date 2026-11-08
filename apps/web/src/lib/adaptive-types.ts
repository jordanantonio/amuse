import type { Window } from './types';
export type Slot = Window & {
  id?: string;
  task_id: string;
  task_name: string;
  worker_id: string;
  worker_name: string;
  cost_cents: number;
  state?: string;
};
export type Recovery = {
  id: string;
  project_id: string;
  project_name: string;
  objective: string;
  status: string;
  reason: string;
  created_at: string;
  expires_at: string;
  published_at: string | null;
  stale: boolean;
  original_schedule: Slot[];
  proposed_schedule: Slot[];
  replaces_assignment_ids: string[];
  metrics: Record<string, number | string>;
  confirmations: { id: string; worker_id: string; worker_name: string; status: string }[];
  history: { decision: string; actor: string; comment: string; created_at: string }[];
};
export type Forecast = Window & {
  id: string;
  rain_probability: number;
  precipitation_mm: number;
  wind_kph: number;
  temperature_c: number;
  source: string;
  simulated: boolean;
  fetched_at: string;
};
export type Review = {
  project_id: string;
  risks: {
    task_id: string;
    task_name: string;
    kind: string;
    reason: string;
    assignment_ids: string[];
  }[];
  horizon_days: number;
  contingency_minutes: number;
  forecast_source: string;
  assumptions: string[];
};
export type Policy = {
  project_id?: string;
  task_buffer_percent: number;
  transition_minutes: number;
  contingency_minutes: number;
  freeze_hours: number;
  day_start_hour: number;
  day_end_hour: number;
  minimum_rest_hours: number;
  max_daily_hours: number;
  timezone: string;
  task_weather_rules: Record<string, Record<string, number>>;
};
export type Application = {
  id: string;
  job_id: string;
  job_title: string;
  worker_id: string;
  worker_name: string;
  project_id: string;
  status: string;
};
export type History = {
  id: string;
  action: string;
  actor: string;
  entity_id: string;
  created_at: string;
};
