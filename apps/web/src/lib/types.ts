export type Persona = { id: string; name: string; role: 'manager' | 'worker' | 'admin' };
export type Window = { starts_at: string; ends_at: string };
export type Worker = {
  id: string;
  name: string;
  title: string;
  location: string;
  hourly_rate_cents: number;
  employment_type: string;
  work_modes: string[];
  color: string;
  skills: string[];
  certifications: { name: string; expires_at: string }[];
  availability: Window[];
  busy: Window[];
};
export type Task = {
  id: string;
  project_id: string;
  name: string;
  duration_hours: number;
  crew_size: number;
  required_skills: string[];
  required_certifications: string[];
  work_mode: string;
  confirmed_count: number;
  predecessor_ids: string[];
};
export type Project = {
  id: string;
  name: string;
  client: string;
  starts_at: string;
  deadline: string;
  budget_cents: number | null;
  color: string;
  location: string;
  capacity: number;
  tasks: Task[];
};
export type Assignment = Window & {
  id: string;
  task_id: string;
  task_name: string;
  project_id: string;
  project_name: string;
  worker_id: string;
  worker_name: string;
  status: 'confirmed' | 'disrupted' | 'completed' | 'cancelled';
  color: string;
};
export type Job = {
  id: string;
  title: string;
  project_id: string;
  location: string;
  work_mode: string;
  skills: string[];
  rate_min_cents: number;
  rate_max_cents: number;
  status: string;
};
export type Dashboard = {
  organization: string;
  persona: Persona;
  demo: boolean;
  week_start: string;
  timezone: string;
  workers: Worker[];
  projects: Project[];
  assignments: Assignment[];
  jobs: Job[];
  staffing_gaps: number;
};
export type Proposal = Window & {
  task_id: string;
  task_name: string;
  worker_id: string;
  worker_name: string;
  cost_cents: number;
  state: 'proposed';
};
export type Draft = {
  id: string;
  project_id: string;
  created_at: string;
  input_fingerprint: string;
  status: string;
  solver_status: string;
  proposals: Proposal[];
  blockers: string[];
  cost_cents: number | null;
};

export type { PublicContract, PublicContracts } from './public-types';
