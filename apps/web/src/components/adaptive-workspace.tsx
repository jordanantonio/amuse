'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  LayoutDashboard,
  CalendarDays,
  BriefcaseBusiness,
  Users,
  Workflow,
  Inbox,
  UserRound,
  ArrowRight,
  ArrowUpRight,
  RefreshCw,
  Plus,
  Search,
  CloudRain,
  ShieldCheck,
  TriangleAlert,
  Check,
  Clock3,
  Menu,
  X,
  MapPin,
  SlidersHorizontal,
  LogOut,
  History,
  LoaderCircle,
} from 'lucide-react';
import { Button } from './ui/button';
import { Avatar } from './ui/avatar';
import { Calendar } from './team-calendar';
import { ProjectCard } from './project-card';
import { DataEditor, type EditorSpec, type Field } from './data-editor';
import { ProposalComparison, stateLabel } from './proposal-comparison';
import { request } from '@/lib/api';
import { supabase } from '@/lib/supabase';
import { money, clock, shortDate, initials } from '@/lib/display';
import { addDays, localInput, inputInstant, zonedInstant } from '@/lib/calendar-time';
import type { Dashboard, Persona, Project, Task, Assignment } from '@/lib/types';
import type {
  Recovery,
  Forecast,
  Review,
  Policy,
  Application,
  History as Audit,
  Slot,
} from '@/lib/adaptive-types';

type View = 'overview' | 'calendar' | 'projects' | 'talent' | 'adaptive' | 'inbox' | 'profile';
const nav = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'calendar', label: 'Team calendar', icon: CalendarDays },
  { id: 'projects', label: 'Projects', icon: BriefcaseBusiness },
  { id: 'talent', label: 'Marketplace', icon: Users },
  { id: 'adaptive', label: 'SHIFT Adaptive', icon: Workflow },
  { id: 'inbox', label: 'Approval inbox', icon: Inbox },
  { id: 'profile', label: 'My profile', icon: UserRound },
] as const;
const objectives: Record<string, string> = {
  lowest_cost: 'Lowest cost',
  earliest_completion: 'Earliest completion',
  fewest_changes: 'Fewest changes',
};
const csv = (s: string) => [
  ...new Set(
    s
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean),
  ),
];
const dtField = (name: string, label: string, value: string): Field => ({
  name,
  label,
  type: 'datetime-local',
  value: localInput(value),
  required: true,
  help: 'America/Edmonton time',
});
const numField = (
  name: string,
  label: string,
  value: number,
  min = 0,
  max = 100000,
  step = 1,
): Field => ({ name, label, type: 'number', value, min, max, step, required: true });

export function AdaptiveWorkspace() {
  const [data, setData] = useState<Dashboard | null>(null),
    [people, setPeople] = useState<Persona[]>([]),
    [persona, setPersona] = useState('demo-manager'),
    [initialized, setInitialized] = useState(false);
  const [view, setView] = useState<View>('overview'),
    [projectId, setProjectId] = useState('eastside'),
    [proposalId, setProposalId] = useState(''),
    [week, setWeek] = useState('2026-11-09');
  const [proposals, setProposals] = useState<Recovery[]>([]),
    [apps, setApps] = useState<Application[]>([]),
    [audit, setAudit] = useState<Audit[]>([]),
    [weather, setWeather] = useState<Forecast[]>([]),
    [policy, setPolicy] = useState<Policy | null>(null),
    [review, setReview] = useState<Review | null>(null);
  const [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [busy, setBusy] = useState(false),
    [updated, setUpdated] = useState(0),
    [seconds, setSeconds] = useState(0),
    [mobile, setMobile] = useState(false),
    [search, setSearch] = useState(''),
    [editor, setEditor] = useState<EditorSpec | null>(null),
    [detail, setDetail] = useState<Assignment | Slot | null>(null),
    [overlay, setOverlay] = useState(false),
    [failedPlans, setFailedPlans] = useState<string[]>([]);
  const generation = useRef(0),
    projectRef = useRef(projectId);
  projectRef.current = projectId;
  const navigate = (next: View, pid = projectId, rid = '') => {
    setView(next);
    setProjectId(pid);
    setProposalId(rid);
    setMobile(false);
    setDetail(null);
    const url = new URL(location.href);
    url.searchParams.set('view', next);
    url.searchParams.set('project', pid);
    if (rid) url.searchParams.set('proposal', rid);
    else url.searchParams.delete('proposal');
    history.pushState({}, '', url);
  };
  useEffect(() => {
    const read = () => {
      const q = new URL(location.href).searchParams;
      const v = q.get('view');
      if (nav.some((n) => n.id === v)) setView(v as View);
      setProjectId(q.get('project') || 'eastside');
      setProposalId(q.get('proposal') || '');
    };
    read();
    setPersona(localStorage.getItem('shift-persona') || 'demo-manager');
    setInitialized(true);
    window.addEventListener('popstate', read);
    return () => window.removeEventListener('popstate', read);
  }, []);
  const load = useCallback(async () => {
    const turn = ++generation.current;
    try {
      const response = await request<Dashboard>('/dashboard', persona);
      const [ps, applications, events] = await Promise.all([
        request<Recovery[]>('/proposals', persona),
        request<Application[]>('/applications', persona),
        response.persona.role === 'worker'
          ? Promise.resolve([])
          : request<Audit[]>('/history', persona),
      ]);
      if (turn !== generation.current) return;
      setData(response);
      setProposals(ps);
      setApps(applications);
      setAudit(events);
      setUpdated(Date.now());
      setError('');
      if (!response.projects.some((p) => p.id === projectRef.current) && response.projects.length)
        setProjectId(response.projects[0].id);
    } catch (e) {
      if (turn === generation.current) setError((e as Error).message);
    }
  }, [persona]);
  const loadProject = useCallback(async () => {
    if (!data || data.persona.role === 'worker' || !projectId) return;
    try {
      const [forecasts, p] = await Promise.all([
        request<Forecast[]>(`/projects/${projectId}/weather`, persona),
        request<Policy>(`/projects/${projectId}/policy`, persona),
      ]);
      setWeather(forecasts);
      setPolicy(p);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [projectId, persona, data?.persona.role]);
  useEffect(() => {
    if (!initialized) return;
    setData(null);
    setReview(null);
    setPolicy(null);
    setWeather([]);
    setProposals([]);
    void load();
    const timer = setInterval(() => void load(), 15000);
    return () => {
      clearInterval(timer);
      generation.current++;
    };
  }, [initialized, load]);
  useEffect(() => {
    void loadProject();
    setReview(null);
    setFailedPlans([]);
  }, [loadProject]);
  useEffect(() => {
    const id = setInterval(
      () => setSeconds(updated ? Math.floor((Date.now() - updated) / 1000) : 0),
      1000,
    );
    return () => clearInterval(id);
  }, [updated]);
  useEffect(() => {
    if (!notice) return;
    const id = setTimeout(() => setNotice(''), 7000);
    return () => clearTimeout(id);
  }, [notice]);
  useEffect(() => {
    request<Persona[]>('/personas', 'demo-manager')
      .then(setPeople)
      .catch(() => setPeople([]));
  }, []);
  const mutate = async (
    path: string,
    method = 'POST',
    body?: unknown,
    message = 'Changes saved.',
  ) => {
    setBusy(true);
    setError('');
    try {
      const result = await request<unknown>(path, persona, method, body);
      await load();
      await loadProject();
      setNotice(message);
      return result;
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      setBusy(false);
    }
  };
  const action = (fn: () => Promise<unknown>) => void fn().catch(() => {});
  const project = data?.projects.find((p) => p.id === projectId),
    manager = !!data && data.persona.role !== 'worker',
    confirmed = data?.assignments.filter((a) => a.status === 'confirmed') || [];
  const pending = proposals.filter((p) =>
    ['pending_approval', 'awaiting_confirmation', 'ready_to_publish'].includes(p.status),
  );
  const chosen =
    proposals.find((p) => p.id === proposalId) ||
    proposals.find((p) => p.project_id === projectId && pending.includes(p));
  const activeProjects = data?.projects || [];
  const fieldsProject = (p?: Project): Field[] => [
    { name: 'name', label: 'Project name', value: p?.name, required: true },
    { name: 'client', label: 'Client / company', value: p?.client, required: true },
    {
      name: 'location',
      label: 'Worksite location',
      value: p?.location || 'Edmonton, AB',
      required: true,
    },
    dtField('starts_at', 'Project starts', p?.starts_at || zonedInstant(week, '08:00')),
    dtField('ends_at', 'Project deadline', p?.deadline || zonedInstant(addDays(week, 4), '17:00')),
    numField('capacity', 'Maximum people at worksite', p?.capacity || 4, 1, 100),
    {
      name: 'budget',
      label: 'Labour budget (CAD, optional)',
      type: 'number',
      value: p?.budget_cents == null ? '' : p.budget_cents / 100,
      min: 0,
      step: 0.01,
    },
  ];
  const projectEditor = (p?: Project) =>
    setEditor({
      title: p ? 'Edit project' : 'Create project',
      description: 'Existing confirmed work stays protected. Times use America/Edmonton.',
      fields: fieldsProject(p),
      save: async (f) => {
        const result = await mutate(p ? `/projects/${p.id}` : '/projects', p ? 'PUT' : 'POST', {
          name: f.name,
          client: f.client,
          location: f.location,
          starts_at: inputInstant(f.starts_at),
          ends_at: inputInstant(f.ends_at),
          capacity: Number(f.capacity),
          budget_cents: f.budget ? Math.round(Number(f.budget) * 100) : null,
        });
        if (!p && result) navigate('projects', (result as { id: string }).id);
      },
    });
  const taskEditor = (t?: Task) => {
    if (!project) return;
    setEditor({
      title: t ? 'Edit task' : 'Add project task',
      description: 'Skills and certifications are required for every crew member.',
      fields: [
        { name: 'name', label: 'Task name', value: t?.name, required: true },
        numField('duration_hours', 'Estimated working hours', t?.duration_hours || 4, 1, 16),
        numField('crew_size', 'Required crew size', t?.crew_size || 1, 1, 30),
        {
          name: 'skills',
          label: 'Required skills (comma separated)',
          value: t?.required_skills.join(', ') || '',
        },
        {
          name: 'certs',
          label: 'Required certifications (comma separated)',
          value: t?.required_certifications.join(', ') || '',
        },
        {
          name: 'mode',
          label: 'Work mode',
          value: t?.work_mode || 'on_site',
          options: [
            { value: 'on_site', label: 'On site' },
            { value: 'hybrid', label: 'Hybrid' },
            { value: 'remote', label: 'Remote' },
          ],
        },
        {
          name: 'predecessors',
          label: 'Tasks that must finish first',
          type: 'multiselect',
          value: t?.predecessor_ids?.join(', ') || '',
          options: project.tasks
            .filter((x) => x.id !== t?.id)
            .map((x) => ({ value: x.id, label: x.name })),
          help: 'Select all required predecessors. Use Ctrl or Command to select multiple tasks.',
        },
      ],
      save: async (f) => {
        await mutate(`/projects/${projectId}/tasks${t ? '/' + t.id : ''}`, t ? 'PUT' : 'POST', {
          name: f.name,
          duration_hours: Number(f.duration_hours),
          crew_size: Number(f.crew_size),
          required_skills: csv(f.skills),
          required_certifications: csv(f.certs),
          work_mode: f.mode,
          predecessor_ids: csv(f.predecessors),
        });
      },
    });
  };
  const absenceEditor = (a?: Assignment) =>
    setEditor({
      title: 'Report worker unavailability',
      description:
        'Confirmed work stays in place until an authorized recovery is accepted and published.',
      fields: [
        dtField('starts_at', 'Unavailable from', a?.starts_at || zonedInstant(week, '08:00')),
        dtField(
          'ends_at',
          'Unavailable until',
          a?.ends_at || zonedInstant(addDays(week, 4), '17:00'),
        ),
      ],
      save: async (f) => {
        await mutate(
          a ? `/assignments/${a.id}/disrupt` : '/me/absence',
          'POST',
          { starts_at: inputInstant(f.starts_at), ends_at: inputInstant(f.ends_at) },
          'Absence recorded. Confirmed work preserved; run an Adaptive review.',
        );
        setReview(null);
      },
    });
  const profileEditor = () => {
    const w = data?.workers[0];
    if (!w) return;
    setEditor({
      title: 'Edit professional profile',
      fields: [
        { name: 'title', label: 'Professional title', value: w.title, required: true },
        { name: 'location', label: 'Location', value: w.location, required: true },
        numField('rate', 'Hourly rate (CAD)', w.hourly_rate_cents / 100, 0, 1000, 0.01),
        {
          name: 'skills',
          label: 'Skills (comma separated)',
          value: w.skills.join(', '),
          required: true,
        },
        {
          name: 'modes',
          label: 'Preferred work modes',
          type: 'multiselect',
          options: [
            { value: 'on_site', label: 'On site' },
            { value: 'hybrid', label: 'Hybrid' },
            { value: 'remote', label: 'Remote' },
          ],
          value: w.work_modes.join(', '),
          required: true,
        },
        {
          name: 'certs',
          label: 'Certifications and expiry dates',
          type: 'textarea',
          value: w.certifications
            .map((c) => `${c.name} | ${localInput(c.expires_at).slice(0, 10)}`)
            .join('\n'),
          help: 'One per line: Red Seal Electrical | 2027-12-31',
        },
      ],
      save: async (f) => {
        await mutate('/me/profile', 'PUT', {
          title: f.title,
          location: f.location,
          hourly_rate_cents: Math.round(Number(f.rate) * 100),
          skills: csv(f.skills),
          work_modes: csv(f.modes),
          certifications: f.certs
            .split('\n')
            .filter(Boolean)
            .map((line) => {
              const [name, date] = line.split('|').map((s) => s.trim());
              if (!name || !date) throw Error('Each certification needs a name and expiry date');
              return { name, expires_at: zonedInstant(date, '23:30') };
            }),
        });
      },
    });
  };
  const availabilityEditor = () => {
    const w = data?.workers[0];
    if (!w) return;
    setEditor({
      title: 'Publish availability',
      description:
        'Busy calendar details remain private. Confirmed work must remain covered; use Report absence when plans change.',
      fields: [
        {
          name: 'windows',
          label: 'Available windows',
          type: 'textarea',
          value: w.availability
            .map(
              (v) =>
                `${localInput(v.starts_at).replace('T', ' ')} / ${localInput(v.ends_at).replace('T', ' ')}`,
            )
            .join('\n'),
          help: 'One per line: 2026-11-09 08:00 / 2026-11-09 17:00',
        },
      ],
      save: async (f) => {
        await mutate('/me/availability', 'PUT', {
          windows: f.windows
            .split('\n')
            .filter((x) => x.trim())
            .map((line) => {
              const [s, e] = line.split('/').map((x) => x.trim().replace(' ', 'T'));
              if (!s || !e) throw Error('Each window needs a start and end separated by /');
              return { starts_at: inputInstant(s), ends_at: inputInstant(e) };
            }),
        });
      },
    });
  };
  const jobEditor = () =>
    setEditor({
      title: 'Publish a project opportunity',
      fields: [
        {
          name: 'project_id',
          label: 'Project',
          value: projectId,
          required: true,
          options: activeProjects.map((p) => ({ value: p.id, label: p.name })),
        },
        { name: 'title', label: 'Role title', required: true },
        {
          name: 'location',
          label: 'Location',
          value: project?.location || 'Edmonton, AB',
          required: true,
        },
        {
          name: 'mode',
          label: 'Work mode',
          value: 'on_site',
          options: [
            { value: 'on_site', label: 'On site' },
            { value: 'hybrid', label: 'Hybrid' },
            { value: 'remote', label: 'Remote' },
          ],
        },
        { name: 'skills', label: 'Required skills (comma separated)', required: true },
        numField('min_rate', 'Minimum hourly rate (CAD)', 60, 0, 1000, 0.01),
        numField('max_rate', 'Maximum hourly rate (CAD)', 85, 0, 1000, 0.01),
      ],
      save: async (f) => {
        await mutate('/jobs', 'POST', {
          project_id: f.project_id,
          title: f.title,
          location: f.location,
          work_mode: f.mode,
          skills: csv(f.skills),
          rate_min_cents: Math.round(Number(f.min_rate) * 100),
          rate_max_cents: Math.round(Number(f.max_rate) * 100),
        });
      },
    });
  const policyEditor = () => {
    if (!project || !policy) return;
    const fields: Field[] = [
      numField(
        'task_buffer_percent',
        'Task duration buffer (%)',
        policy.task_buffer_percent,
        0,
        50,
      ),
      numField(
        'transition_minutes',
        'Setup / transition between shifts (minutes)',
        policy.transition_minutes,
        0,
        120,
        30,
      ),
      numField(
        'contingency_minutes',
        'Protected project contingency (minutes)',
        policy.contingency_minutes,
        0,
        2880,
        30,
      ),
      numField('freeze_hours', 'Near-term freeze window (hours)', policy.freeze_hours, 0, 168),
      numField(
        'minimum_rest_hours',
        'Minimum overnight rest (hours)',
        policy.minimum_rest_hours,
        0,
        24,
      ),
      numField('max_daily_hours', 'Maximum working hours per day', policy.max_daily_hours, 1, 16),
      numField('day_start_hour', 'Workday begins (hour, 0–23)', policy.day_start_hour, 0, 23),
      numField('day_end_hour', 'Workday ends (hour, 1–24)', policy.day_end_hour, 1, 24),
      { name: 'timezone', label: 'Worksite time zone', value: policy.timezone, required: true },
    ];
    for (const t of project.tasks) {
      for (const [key, label] of [
        ['max_rain_probability', 'maximum rain probability (%)'],
        ['max_precipitation_mm', 'maximum precipitation (mm)'],
        ['max_wind_kph', 'maximum wind (km/h)'],
      ] as const)
        fields.push({
          name: `${t.id}|${key}`,
          label: `${t.name}: ${label}`,
          type: 'number',
          value: policy.task_weather_rules[t.id]?.[key] ?? '',
          min: 0,
          max: key === 'max_rain_probability' ? 100 : 500,
          help: 'Leave blank if this condition does not constrain the task.',
        });
    }
    setEditor({
      title: 'Scheduling & weather policies',
      description:
        'These are project-specific planning settings, not universal construction safety standards. Confirmed shifts stay frozen unless an identified disruption explicitly requires recovery.',
      fields,
      save: async (f) => {
        const rules: Record<string, Record<string, number>> = {};
        for (const [key, value] of Object.entries(f)) {
          if (key.includes('|') && value !== '') {
            const [tid, condition] = key.split('|');
            (rules[tid] ??= {})[condition] = Number(value);
          }
        }
        const body: Record<string, unknown> = { timezone: f.timezone, task_weather_rules: rules };
        for (const key of [
          'task_buffer_percent',
          'transition_minutes',
          'contingency_minutes',
          'freeze_hours',
          'minimum_rest_hours',
          'max_daily_hours',
          'day_start_hour',
          'day_end_hour',
        ])
          body[key] = Number(f[key]);
        await mutate(`/projects/${projectId}/policy`, 'PUT', body);
        setReview(null);
      },
    });
  };
  const runReview = async () => {
    setBusy(true);
    try {
      setReview(await request<Review>(`/projects/${projectId}/review`, persona, 'POST'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const generate = async () => {
    setBusy(true);
    setFailedPlans([]);
    try {
      const result = await request<
        (Recovery | { solver_status: string; blockers: string[]; objective: string })[]
      >(`/projects/${projectId}/proposals`, persona, 'POST', {
        objectives: Object.keys(objectives),
      });
      const valid = result.filter((p): p is Recovery => 'id' in p);
      setFailedPlans(
        result
          .filter(
            (p): p is { solver_status: string; blockers: string[]; objective: string } =>
              !('id' in p),
          )
          .flatMap((p) => [
            `${objectives[p.objective]}: ${p.solver_status}. ${p.blockers.join(' ')}`,
          ]),
      );
      await load();
      if (valid[0]) navigate('adaptive', projectId, valid[0].id);
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const respond = (p: Recovery, action: string, body?: unknown) =>
    mutate(
      `/proposals/${p.id}/${action}`,
      'POST',
      body,
      action === 'publish'
        ? 'Schedule published. Both calendars now reflect confirmed changes.'
        : 'Response saved.',
    );
  const comparison = (p: Recovery) => (
    <ProposalComparison
      key={p.id}
      proposal={p}
      manager={manager}
      busy={busy}
      onDecision={(decision, comment) =>
        action(() => respond(p, 'decision', { decision, comment }))
      }
      onPublish={() => action(() => respond(p, 'publish'))}
      onConfirm={(decision) => action(() => respond(p, 'confirmation', { decision }))}
    />
  );
  const next =
    confirmed
      .filter((a) => new Date(a.ends_at) >= new Date())
      .sort((a, b) => a.starts_at.localeCompare(b.starts_at))[0] ||
    confirmed.slice().sort((a, b) => a.starts_at.localeCompare(b.starts_at))[0];
  return (
    <div className="app-shell adaptive-shell">
      <aside className={`sidebar ${mobile ? 'sidebar-open' : ''}`}>
        <a
          className="wordmark"
          href="?view=overview"
          onClick={(e) => {
            e.preventDefault();
            navigate('overview');
          }}
        >
          <span className="brand-symbol">
            <i />
            <i />
            <i />
          </span>
          shift<span className="brand-period">.</span>
        </a>
        <div className="org-switch">
          <span className="org-icon">
            <BriefcaseBusiness size={18} />
          </span>
          <div>
            <strong>{data?.organization || 'SHIFT'}</strong>
            <small>Connected workforce</small>
          </div>
        </div>
        <p className="nav-caption">WORKSPACE</p>
        <nav aria-label="Workspace">
          {nav
            .filter((n) => (manager ? n.id !== 'profile' : n.id !== 'adaptive'))
            .map((n) => (
              <a
                key={n.id}
                href={`?view=${n.id}&project=${projectId}`}
                className={`nav-item ${view === n.id ? 'active' : ''}`}
                onClick={(e) => {
                  e.preventDefault();
                  navigate(n.id);
                }}
              >
                <n.icon size={18} />
                <span>
                  {!manager && n.id === 'calendar'
                    ? 'My schedule'
                    : !manager && n.id === 'inbox'
                      ? 'My invitations'
                      : n.label}
                </span>
                {n.id === 'inbox' && pending.length > 0 && <small>{pending.length}</small>}
              </a>
            ))}
        </nav>
        <div className="sidebar-projects">
          <p className="nav-caption">PROJECTS</p>
          {activeProjects.map((p) => (
            <a
              key={p.id}
              href={`?view=projects&project=${p.id}`}
              className="project-nav"
              onClick={(e) => {
                e.preventDefault();
                navigate('projects', p.id);
              }}
            >
              <span className="project-dot" style={{ background: p.color }} />
              {p.name}
            </a>
          ))}
        </div>
        <div className="sidebar-bottom">
          <div className="demo-card">
            <span>
              <ShieldCheck size={15} />
              Human-approved scheduling
            </span>
            <p>
              SHIFT recommends.
              <br />
              Your team makes the decision.
            </p>
          </div>
          <div className="profile">
            <span className="avatar profile-avatar">{initials(data?.persona.name || 'SHIFT')}</span>
            <div>
              <strong>{data?.persona.name || 'Connecting…'}</strong>
              <small>{data?.persona.role || 'Workspace'}</small>
            </div>
            {supabase && (
              <button
                className="icon-button"
                aria-label="Sign out"
                onClick={() => void supabase?.auth.signOut()}
              >
                <LogOut size={16} />
              </button>
            )}
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="mobile-toggle"
              aria-label="Toggle menu"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <span>/</span>
            <strong>{nav.find((n) => n.id === view)?.label}</strong>
          </div>
          <div className="topbar-right">
            {data?.demo && <span className="demo-badge">FICTIONAL DEMO</span>}
            {data?.demo && people.length > 0 && (
              <label className="persona-select">
                <span className="sr-only">Demo persona</span>
                <select
                  value={persona}
                  onChange={(e) => {
                    localStorage.setItem('shift-persona', e.target.value);
                    setPersona(e.target.value);
                    navigate('overview');
                    setReview(null);
                  }}
                >
                  {people.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} · {p.role}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <span className={`freshness ${seconds > 30 ? 'outdated' : ''}`}>
              {updated ? `Updated ${seconds}s ago` : 'Connecting'}
            </span>
            <Button
              variant="ghost"
              aria-label="Refresh workspace"
              disabled={busy}
              onClick={() => void load()}
            >
              <RefreshCw size={15} />
            </Button>
          </div>
        </header>
        <div className="content">
          {error && (
            <div className="banner error" role="alert">
              <TriangleAlert size={20} />
              <div>
                <strong>Action could not complete</strong>
                <p>{error}</p>
                {data && <small>Previously loaded data remains visible.</small>}
              </div>
              <Button variant="outline" onClick={() => void load()}>
                Retry
              </Button>
            </div>
          )}
          {!data ? (
            <div className="loading-state">
              <LoaderCircle size={28} className="spin" />
              <h1>Opening your workspace…</h1>
            </div>
          ) : (
            <>
              {view === 'overview' && (
                <>
                  <PageHeading
                    title={
                      manager
                        ? 'A clear plan. A team in sync.'
                        : `Your next move, ${data.persona.name.split(' ')[0]}.`
                    }
                    eyebrow="WORKFORCE OPERATIONS"
                    description={
                      manager
                        ? 'Act on staffing risks, pending decisions, and upcoming project work.'
                        : 'Your assignments, invitations, and availability—all in one place.'
                    }
                    action={
                      <Button onClick={() => navigate(manager ? 'adaptive' : 'inbox')}>
                        <ArrowRight size={16} />
                        {manager ? 'Review & recover' : 'Review invitations'}
                      </Button>
                    }
                  />
                  <div className="stats-grid">
                    {[
                      {
                        label: manager ? 'Active projects' : 'My projects',
                        value: activeProjects.length,
                        icon: BriefcaseBusiness,
                      },
                      {
                        label: 'Confirmed assignments',
                        value: confirmed.length,
                        icon: CalendarDays,
                      },
                      {
                        label: manager ? 'Coverage gaps / absences' : 'Pending invitations',
                        value: manager ? data.staffing_gaps : pending.length,
                        icon: TriangleAlert,
                      },
                      {
                        label: manager ? 'Pending decisions' : 'Open opportunities',
                        value: manager ? pending.length : data.jobs.length,
                        icon: Inbox,
                      },
                    ].map((s) => (
                      <section className="stat-card" key={s.label}>
                        <div>
                          <span>{s.label}</span>
                          <span className="stat-icon purple">
                            <s.icon size={17} />
                          </span>
                        </div>
                        <strong>{String(s.value).padStart(2, '0')}</strong>
                        <p>From current workspace records</p>
                      </section>
                    ))}
                  </div>
                  {manager ? (
                    <div className="operations-grid">
                      <section className="panel">
                        <div className="section-heading">
                          <div>
                            <h2>Needs your attention</h2>
                            <p>Prioritized actions, not decorative analytics.</p>
                          </div>
                        </div>
                        <button className="operation-row" onClick={() => navigate('adaptive')}>
                          <TriangleAlert size={20} />
                          <div>
                            <strong>{data.staffing_gaps} coverage gaps or recorded absences</strong>
                            <p>Review affected tasks and generate feasible alternatives.</p>
                          </div>
                          <ArrowRight size={16} />
                        </button>
                        <button className="operation-row" onClick={() => navigate('inbox')}>
                          <Inbox size={20} />
                          <div>
                            <strong>
                              {pending.filter((p) => p.status === 'pending_approval').length}{' '}
                              proposals awaiting approval
                            </strong>
                            <p>
                              {pending.filter((p) => p.status === 'awaiting_confirmation').length}{' '}
                              awaiting workers ·{' '}
                              {pending.filter((p) => p.status === 'ready_to_publish').length} ready
                              to publish
                            </p>
                          </div>
                          <ArrowRight size={16} />
                        </button>
                      </section>
                      <section className="panel">
                        <div className="section-heading">
                          <div>
                            <h2>Recent activity</h2>
                            <p>Persisted scheduling audit trail.</p>
                          </div>
                          <History size={18} />
                        </div>
                        {audit.slice(0, 4).map((e) => (
                          <div className="activity-row" key={e.id}>
                            <span className="project-dot" />
                            <div>
                              <strong>{e.action.replaceAll('.', ' ').replaceAll('_', ' ')}</strong>
                              <p>
                                {e.actor} · {shortDate(e.created_at)} {clock(e.created_at)}
                              </p>
                            </div>
                          </div>
                        ))}
                        {!audit.length && (
                          <div className="empty-card">
                            Your scheduling decisions will appear here.
                          </div>
                        )}
                      </section>
                    </div>
                  ) : (
                    <section className="panel next-shift">
                      <div className="eyebrow">NEXT CONFIRMED ASSIGNMENT</div>
                      {next ? (
                        <>
                          <h2>{next.task_name}</h2>
                          <p>{next.project_name}</p>
                          <div className="next-shift-facts">
                            <span>
                              <CalendarDays size={18} />
                              {shortDate(next.starts_at)}
                            </span>
                            <span>
                              <Clock3 size={18} />
                              {clock(next.starts_at)}–{clock(next.ends_at)}
                            </span>
                            <span>
                              <MapPin size={18} />
                              {activeProjects.find((p) => p.id === next.project_id)?.location}
                            </span>
                          </div>
                          <div className="actions">
                            <Button onClick={() => setDetail(next)}>View assignment</Button>
                            <Button variant="outline" onClick={() => absenceEditor(next)}>
                              Report absence
                            </Button>
                          </div>
                        </>
                      ) : (
                        <>
                          <h2>Your next assignment starts with an invitation.</h2>
                          <p>No confirmed assignments yet.</p>
                          <Button onClick={() => navigate('talent')}>Explore opportunities</Button>
                        </>
                      )}
                    </section>
                  )}
                  <section className="panel dashboard-calendar">
                    <div className="section-heading">
                      <div>
                        <h2>{manager ? 'Team schedule' : 'Your confirmed schedule'}</h2>
                        <p>Actual available windows and commitments · {data.timezone}</p>
                      </div>
                      <Button variant="outline" onClick={() => navigate('calendar')}>
                        Open calendar
                        <ArrowUpRight size={15} />
                      </Button>
                    </div>
                    <Calendar
                      data={data}
                      compact
                      weekStart={week}
                      onWeekChange={setWeek}
                      onSelect={setDetail}
                    />
                  </section>
                  <div className="section-title spaced-title">
                    <h2>Projects in motion</h2>
                    <Button variant="ghost" onClick={() => navigate('projects')}>
                      View all
                      <ArrowRight size={14} />
                    </Button>
                  </div>
                  <div className="project-grid full-project-grid">
                    {activeProjects.map((p) => (
                      <ProjectCard
                        key={p.id}
                        project={p}
                        workers={data.workers}
                        assignments={confirmed}
                        open={() => navigate('projects', p.id)}
                      />
                    ))}
                  </div>
                </>
              )}
              {view === 'calendar' && (
                <>
                  <PageHeading
                    title={
                      manager
                        ? 'Everyone’s time, clearly planned.'
                        : 'Your work. Your availability.'
                    }
                    eyebrow="CONNECTED CALENDARS"
                    description="Switch weeks or inspect a single day. Private calendar reasons are never shared."
                    action={
                      !manager ? (
                        <div className="actions">
                          <Button onClick={availabilityEditor}>Edit availability</Button>
                          <Button variant="outline" onClick={() => absenceEditor()}>
                            Report absence
                          </Button>
                        </div>
                      ) : (
                        <label className="overlay-toggle">
                          <input
                            type="checkbox"
                            checked={overlay}
                            onChange={(e) => setOverlay(e.target.checked)}
                          />
                          Overlay latest proposal
                        </label>
                      )
                    }
                  />
                  <section className="panel">
                    <Calendar
                      data={data}
                      weekStart={week}
                      onWeekChange={setWeek}
                      proposals={overlay && chosen ? [chosen] : []}
                      onSelect={setDetail}
                    />
                  </section>
                  <div className="info-note">
                    <ShieldCheck size={17} />
                    Free windows subtract confirmed assignments and busy intervals. Proposed work
                    does not become confirmed until approved, accepted, and published.
                  </div>
                </>
              )}
              {view === 'projects' && (
                <>
                  <PageHeading
                    title="Turn scope into a shared plan."
                    eyebrow="PROJECT WORKSPACE"
                    description="Manage tasks, dependencies, staffing requirements, and deadlines."
                    action={
                      manager ? (
                        <Button onClick={() => projectEditor()}>
                          <Plus size={16} />
                          New project
                        </Button>
                      ) : undefined
                    }
                  />
                  <ProjectPicker
                    projects={activeProjects}
                    selected={projectId}
                    select={(pid) => navigate('projects', pid)}
                  />
                  {project ? (
                    <section className="panel project-detail">
                      <div className="section-heading">
                        <div>
                          <h2>{project.name}</h2>
                          <p>
                            {project.client} · {project.location} · Deadline{' '}
                            {shortDate(project.deadline)}
                          </p>
                        </div>
                        {manager && (
                          <div className="actions">
                            <Button variant="outline" onClick={() => projectEditor(project)}>
                              Edit project
                            </Button>
                            <Button onClick={() => taskEditor()}>
                              <Plus size={15} />
                              Add task
                            </Button>
                          </div>
                        )}
                      </div>
                      <div className="project-facts">
                        <span>Capacity: {project.capacity}</span>
                        <span>
                          Labour budget:{' '}
                          {project.budget_cents == null ? 'Not set' : money(project.budget_cents)}
                        </span>
                        <span>{project.tasks.length} tasks</span>
                      </div>
                      {project.tasks.map((t) => (
                        <div className="task-row" key={t.id}>
                          <span
                            className={`task-check ${t.confirmed_count >= t.crew_size ? 'filled' : ''}`}
                          >
                            {t.confirmed_count >= t.crew_size && <Check size={13} />}
                          </span>
                          <div>
                            <strong>{t.name}</strong>
                            <p>
                              {t.duration_hours}h · {t.work_mode.replace('_', ' ')} · Skills:{' '}
                              {t.required_skills.join(', ') || 'None'}
                            </p>
                            <p>
                              Certifications: {t.required_certifications.join(', ') || 'None'} ·
                              Depends on:{' '}
                              {t.predecessor_ids
                                ?.map((id) => project.tasks.find((x) => x.id === id)?.name)
                                .join(', ') || 'No predecessors'}
                            </p>
                          </div>
                          <span
                            className={`badge ${t.confirmed_count >= t.crew_size ? 'green' : 'amber'}`}
                          >
                            {t.confirmed_count}/{t.crew_size} confirmed
                          </span>
                          {manager && (
                            <Button size="sm" variant="ghost" onClick={() => taskEditor(t)}>
                              Edit task
                            </Button>
                          )}
                        </div>
                      ))}
                      {!project.tasks.length && (
                        <div className="empty-card">Add the first task to begin planning.</div>
                      )}
                      {manager && (
                        <div className="panel-bottom">
                          <Button onClick={() => navigate('adaptive', project.id)}>
                            Review schedule
                            <Workflow size={15} />
                          </Button>
                        </div>
                      )}
                    </section>
                  ) : (
                    <div className="empty-card">No projects yet. Create one to begin.</div>
                  )}
                </>
              )}
              {view === 'talent' && (
                <>
                  <PageHeading
                    title={manager ? 'Find the right fit for the work.' : 'Find your next project.'}
                    eyebrow="PROJECT MARKETPLACE"
                    description="Search skills and certifications, publish roles, and turn applications into validated offers."
                    action={
                      manager ? (
                        <Button onClick={jobEditor}>
                          <Plus size={16} />
                          Post an opportunity
                        </Button>
                      ) : undefined
                    }
                  />
                  <div className="talent-toolbar">
                    <label className="search-field">
                      <Search size={17} />
                      <input
                        aria-label="Search marketplace"
                        placeholder="Search roles, people, or skills…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                    </label>
                    <span className="subtle">
                      CAD hourly rates · Qualifications checked before assignment
                    </span>
                  </div>
                  {manager && (
                    <div className="talent-grid">
                      {data.workers
                        .filter(
                          (w) =>
                            w.employment_type === 'contractor' &&
                            `${w.name} ${w.skills} ${w.certifications.map((c) => c.name)}`
                              .toLowerCase()
                              .includes(search.toLowerCase()),
                        )
                        .map((w) => (
                          <article className="panel talent-card" key={w.id}>
                            <div className="talent-card-top">
                              <Avatar worker={w} />
                              <span className="badge neutral">Contractor</span>
                            </div>
                            <h3>{w.name}</h3>
                            <p>{w.title}</p>
                            <span className="location">
                              <MapPin size={13} />
                              {w.location}
                            </span>
                            <div className="skill-tags">
                              {w.skills.map((s) => (
                                <span key={s}>{s}</span>
                              ))}
                            </div>
                            <div className="certifications">
                              {w.certifications.map((c) => (
                                <span key={c.name}>
                                  <ShieldCheck size={13} />
                                  {c.name} · expires {shortDate(c.expires_at)}
                                </span>
                              ))}
                            </div>
                            <div className="talent-card-bottom">
                              <strong>
                                {money(w.hourly_rate_cents)}
                                <small> / hour</small>
                              </strong>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => navigate('adaptive')}
                              >
                                Check schedule fit
                              </Button>
                            </div>
                          </article>
                        ))}
                    </div>
                  )}
                  <div className="section-title spaced-title">
                    <h2>Open opportunities</h2>
                  </div>
                  <div className="jobs-list">
                    {data.jobs
                      .filter((j) =>
                        `${j.title} ${j.skills} ${j.location}`
                          .toLowerCase()
                          .includes(search.toLowerCase()),
                      )
                      .map((j) => (
                        <article className="panel job-card" key={j.id}>
                          <BriefcaseBusiness size={25} />
                          <div>
                            <h3>{j.title}</h3>
                            <p>
                              {j.location} · {j.work_mode.replace('_', ' ')} · {j.skills.join(', ')}
                            </p>
                          </div>
                          <strong>
                            {money(j.rate_min_cents)}–{money(j.rate_max_cents)}
                            <small> / hour</small>
                          </strong>
                          {manager ? (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={busy}
                              onClick={() =>
                                action(() =>
                                  mutate(
                                    `/jobs/${j.id}`,
                                    'PATCH',
                                    { status: 'closed' },
                                    'Opportunity closed.',
                                  ),
                                )
                              }
                            >
                              Close posting
                            </Button>
                          ) : (
                            <Button
                              disabled={busy || apps.some((a) => a.job_id === j.id)}
                              onClick={() =>
                                action(() =>
                                  mutate(
                                    `/jobs/${j.id}/apply`,
                                    'POST',
                                    undefined,
                                    'Application submitted.',
                                  ),
                                )
                              }
                            >
                              {apps.some((a) => a.job_id === j.id) ? 'Applied' : 'Apply for role'}
                            </Button>
                          )}
                        </article>
                      ))}
                  </div>
                  {!data.jobs.some((j) =>
                    `${j.title} ${j.skills} ${j.location}`
                      .toLowerCase()
                      .includes(search.toLowerCase()),
                  ) && <div className="empty-card">No opportunities match your search.</div>}
                  <div className="section-title spaced-title">
                    <h2>{manager ? 'Applications to review' : 'My applications'}</h2>
                  </div>
                  <section className="panel">
                    {apps.map((a) => (
                      <div className="application-row" key={a.id}>
                        <div>
                          <strong>{a.job_title}</strong>
                          <p>
                            {a.worker_name} · {a.status}
                          </p>
                        </div>
                        {manager && a.status !== 'withdrawn' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const p = activeProjects.find((p) => p.id === a.project_id);
                              setEditor({
                                title: 'Prepare a validated contractor offer',
                                description:
                                  'Select an unstaffed task. SHIFT checks qualifications and generates a proposal for manager approval before inviting the worker.',
                                fields: [
                                  {
                                    name: 'task_id',
                                    label: 'Project task',
                                    required: true,
                                    options: (
                                      p?.tasks.filter((t) => t.confirmed_count < t.crew_size) || []
                                    ).map((t) => ({ value: t.id, label: t.name })),
                                  },
                                ],
                                save: async (f) => {
                                  const proposal = (await mutate(
                                    `/applications/${a.id}/invite`,
                                    'POST',
                                    { task_id: f.task_id },
                                  )) as Recovery;
                                  navigate('adaptive', a.project_id, proposal.id);
                                },
                              });
                            }}
                          >
                            Review & invite
                          </Button>
                        ) : (
                          !manager &&
                          a.status !== 'withdrawn' && (
                            <Button
                              variant="ghost"
                              disabled={busy}
                              onClick={() => action(() => mutate(`/applications/${a.id}/withdraw`))}
                            >
                              Withdraw
                            </Button>
                          )
                        )}
                      </div>
                    ))}
                    {!apps.length && (
                      <div className="empty-card">
                        Applications will appear here when a worker applies.
                      </div>
                    )}
                  </section>
                </>
              )}
              {view === 'adaptive' && manager && (
                <>
                  <PageHeading
                    title="When conditions change, recover with confidence."
                    eyebrow="SHIFT ADAPTIVE"
                    description="Weather-aware CP-SAT planning. Every schedule change remains human-approved."
                    action={
                      <Button variant="outline" disabled={!policy || busy} onClick={policyEditor}>
                        <SlidersHorizontal size={16} />
                        Scheduling policies
                      </Button>
                    }
                  />
                  <ProjectPicker
                    projects={activeProjects}
                    selected={projectId}
                    select={(pid) => {
                      navigate('adaptive', pid);
                      setReview(null);
                      setWeather([]);
                      setPolicy(null);
                    }}
                  />
                  {project && (
                    <>
                      <div className="adaptive-controls">
                        <Button disabled={busy} onClick={() => void runReview()}>
                          <ShieldCheck size={16} />
                          Run 14-day review
                        </Button>
                        <Button
                          disabled={busy}
                          variant="outline"
                          onClick={() =>
                            action(async () => {
                              await mutate(
                                `/projects/${projectId}/weather`,
                                'POST',
                                { adverse: true },
                                'Simulated heavy-rain forecast loaded.',
                              );
                              await runReview();
                            })
                          }
                        >
                          <CloudRain size={16} />
                          Simulate heavy rain
                        </Button>
                        <Button
                          disabled={busy}
                          variant="ghost"
                          onClick={() =>
                            action(async () => {
                              await mutate(
                                `/projects/${projectId}/weather`,
                                'POST',
                                { adverse: false },
                                'Baseline simulated weather restored.',
                              );
                              await runReview();
                            })
                          }
                        >
                          Restore baseline weather
                        </Button>
                        <Button disabled={busy} onClick={() => void generate()}>
                          {busy ? (
                            <LoaderCircle size={16} className="spin" />
                          ) : (
                            <Workflow size={16} />
                          )}
                          Generate recovery options
                        </Button>
                      </div>
                      <div className="policy-summary">
                        <span>
                          Task buffer <b>{policy?.task_buffer_percent || 0}%</b>
                        </span>
                        <span>
                          Transition <b>{policy?.transition_minutes || 0}m</b>
                        </span>
                        <span>
                          Protected contingency <b>{(policy?.contingency_minutes || 0) / 60}h</b>
                        </span>
                        <span>
                          Freeze window <b>{policy?.freeze_hours ?? 48}h</b>
                        </span>
                        <span>
                          Rest / day limit{' '}
                          <b>
                            {policy?.minimum_rest_hours ?? 11}h / {policy?.max_daily_hours ?? 9}h
                          </b>
                        </span>
                      </div>
                      <section className="panel weather-panel">
                        <div className="section-heading">
                          <div>
                            <h2>Worksite forecast timeline</h2>
                            <p>
                              {weather[0]?.source || 'No forecast loaded'} ·{' '}
                              {weather[0]
                                ? `Updated ${shortDate(weather[0].fetched_at)} ${clock(weather[0].fetched_at)}`
                                : 'No provider update yet'}
                            </p>
                          </div>
                          <span className="demo-badge">SIMULATED WEATHER</span>
                        </div>
                        <div className="weather-timeline">
                          {weather.map((f) => (
                            <div
                              className={`weather-day ${f.precipitation_mm > 10 ? 'rain-risk' : ''}`}
                              key={f.id}
                            >
                              <span>{shortDate(f.starts_at)}</span>
                              <CloudRain size={23} />
                              <strong>{f.rain_probability}% rain</strong>
                              <small>
                                {f.precipitation_mm} mm · {f.temperature_c}°C
                              </small>
                              <small>Wind {f.wind_kph} km/h</small>
                            </div>
                          ))}
                        </div>
                        <p className="weather-assumption">
                          Only tasks with configured thresholds are constrained by weather. No live
                          forecast or background review service is claimed.
                        </p>
                      </section>
                      {review && (
                        <section className="panel risk-panel">
                          <div className="section-heading">
                            <div>
                              <h2>Review: {review.risks.length} risks identified</h2>
                              <p>
                                Rolling {review.horizon_days}-day inputs · project-specific
                                assumptions
                              </p>
                            </div>
                          </div>
                          {review.risks.map((r, i) => (
                            <div className="risk-row" key={i}>
                              <TriangleAlert size={19} />
                              <div>
                                <strong>{r.task_name}</strong>
                                <p>{r.reason}</p>
                              </div>
                              <span className="badge amber">{r.kind.replace('_', ' ')}</span>
                            </div>
                          ))}
                          {!review.risks.length && (
                            <div className="empty-card">
                              No modeled risks identified. This is not a guarantee against unmodeled
                              disruptions.
                            </div>
                          )}
                        </section>
                      )}
                      <section className="panel current-plan">
                        <div className="section-heading">
                          <div>
                            <h2>Confirmed work stays protected</h2>
                            <p>
                              Report exact absence dates. Frozen work is changed only through
                              explicit approval.
                            </p>
                          </div>
                        </div>
                        {confirmed
                          .filter((a) => a.project_id === projectId)
                          .map((a) => (
                            <div className="current-assignment" key={a.id}>
                              <div>
                                <strong>{a.task_name}</strong>
                                <p>
                                  {a.worker_name} · {shortDate(a.starts_at)} {clock(a.starts_at)}–
                                  {clock(a.ends_at)}
                                </p>
                              </div>
                              <Button variant="outline" size="sm" onClick={() => absenceEditor(a)}>
                                Record absence
                              </Button>
                            </div>
                          ))}
                      </section>
                      {failedPlans.map((f, i) => (
                        <div className="banner error" key={i} role="alert">
                          <TriangleAlert size={19} />
                          <p>{f}</p>
                        </div>
                      ))}
                      <div className="section-title spaced-title">
                        <h2>Recovery alternatives</h2>
                        <span className="subtle">
                          Different objectives may produce the same feasible plan.
                        </span>
                      </div>
                      <div className="alternative-grid">
                        {proposals
                          .filter((p) => p.project_id === projectId)
                          .slice(0, 3)
                          .map((p) => (
                            <button
                              className={`panel alternative-card ${chosen?.id === p.id ? 'chosen' : ''}`}
                              key={p.id}
                              onClick={() => navigate('adaptive', projectId, p.id)}
                            >
                              <div>
                                <Workflow size={19} />
                                <span className="badge purple">{p.metrics.solver_status}</span>
                              </div>
                              <h3>{objectives[p.objective]}</h3>
                              <strong>{money(Number(p.metrics.labour_cost_cents || 0))}</strong>
                              <p>
                                Finish {shortDate(String(p.metrics.completion_at))} ·{' '}
                                {p.metrics.changed_assignments} existing assignments changed
                              </p>
                              <span>{p.stale ? 'Stale — regenerate' : stateLabel(p.status)}</span>
                            </button>
                          ))}
                      </div>
                      {chosen && chosen.project_id === projectId && comparison(chosen)}
                      <div className="info-note">
                        <ShieldCheck size={18} />
                        Contingency is protected, not silently consumed to force a plan. Hard
                        constraints include qualifications, availability, busy windows, daily hours,
                        rest, setup time, capacity, dependencies, weather and budget.
                      </div>
                    </>
                  )}
                  <div className="demo-reset">
                    <span>
                      Fictional demo reset restores projects, workers, weather and proposal history.
                    </span>
                    <Button
                      disabled={busy || data.persona.role !== 'admin'}
                      variant="ghost"
                      onClick={() => {
                        if (window.confirm('Reset all fictional demo data?'))
                          action(async () => {
                            await mutate('/demo/reset', 'POST', undefined, 'Demo reset.');
                            setReview(null);
                            setProposalId('');
                          });
                      }}
                    >
                      Reset demo (admin only)
                    </Button>
                  </div>
                </>
              )}
              {view === 'inbox' && (
                <>
                  <PageHeading
                    title={
                      manager
                        ? 'Every decision has a clear next step.'
                        : 'Your next assignments are ready to review.'
                    }
                    eyebrow={manager ? 'APPROVAL INBOX' : 'WORKER CONFIRMATIONS'}
                    description={
                      manager
                        ? 'Approve, request revisions, and publish only after worker acceptance.'
                        : 'Review the proposed hours before accepting. Declining sends the plan back for revision.'
                    }
                  />
                  <div className="inbox-layout">
                    <div className="proposal-list">
                      {proposals.map((p) => (
                        <button
                          key={p.id}
                          className={`panel inbox-card ${chosen?.id === p.id ? 'chosen' : ''}`}
                          onClick={() => navigate('inbox', p.project_id, p.id)}
                        >
                          <strong>{p.project_name}</strong>
                          <span>{objectives[p.objective]}</span>
                          <small>
                            {p.stale ? 'Stale — re-optimization required' : stateLabel(p.status)}
                          </small>
                        </button>
                      ))}
                      {!proposals.length && (
                        <div className="empty-card">
                          No proposals yet.{' '}
                          {manager
                            ? 'Generate recovery options in SHIFT Adaptive.'
                            : 'An invitation appears after a manager approves a plan.'}
                        </div>
                      )}
                    </div>
                    <div>
                      {chosen ? (
                        comparison(chosen)
                      ) : (
                        <div className="empty-card">
                          Select a proposal to review its details and next action.
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
              {view === 'profile' && !manager && (
                <>
                  <PageHeading
                    title="Your skills. Your terms. Your time."
                    eyebrow="MY PROFESSIONAL PROFILE"
                    description="Keep qualifications current and publish the availability you want companies to see."
                    action={<Button onClick={profileEditor}>Edit profile</Button>}
                  />
                  {data.workers[0] && (
                    <section className="panel profile-overview">
                      <Avatar worker={data.workers[0]} />
                      <div>
                        <h2>{data.workers[0].name}</h2>
                        <p>
                          {data.workers[0].title} · {data.workers[0].location}
                        </p>
                        <strong>{money(data.workers[0].hourly_rate_cents)} / hour</strong>
                        <div className="skill-tags">
                          {data.workers[0].skills.map((s) => (
                            <span key={s}>{s}</span>
                          ))}
                        </div>
                        <div className="certifications">
                          {data.workers[0].certifications.map((c) => (
                            <span key={c.name}>
                              <ShieldCheck size={16} />
                              {c.name} · expires {shortDate(c.expires_at)}
                            </span>
                          ))}
                        </div>
                      </div>
                    </section>
                  )}
                  <section className="panel availability-panel">
                    <div className="section-heading">
                      <div>
                        <h2>Published availability</h2>
                        <p>
                          Only time windows are shared; private commitment descriptions stay
                          private.
                        </p>
                      </div>
                      <Button onClick={availabilityEditor}>Edit availability</Button>
                    </div>
                    {data.workers[0]?.availability.map((w, i) => (
                      <div className="availability-row" key={i}>
                        {shortDate(w.starts_at)} · {clock(w.starts_at)}–{clock(w.ends_at)}
                      </div>
                    ))}
                  </section>
                </>
              )}
              <footer className="footer">
                <span>
                  <span className="footer-brand">shift.</span> Workforce, in sync.
                </span>
                <span>
                  {data.demo ? 'Fictional demo · ' : ''}Human-approved scheduling · {data.timezone}
                </span>
              </footer>
            </>
          )}
        </div>
      </main>
      {editor && <DataEditor spec={editor} close={() => setEditor(null)} />}{' '}
      {detail && (
        <AssignmentDetail
          slot={detail}
          close={() => setDetail(null)}
          onAbsence={
            manager && 'id' in detail
              ? () => {
                  setDetail(null);
                  absenceEditor(detail as Assignment);
                }
              : undefined
          }
        />
      )}{' '}
      {notice && (
        <div className="toast" role="status">
          <Check size={17} />
          {notice}
          <button aria-label="Dismiss notification" onClick={() => setNotice('')}>
            <X size={15} />
          </button>
        </div>
      )}
    </div>
  );
}
function PageHeading({
  title,
  eyebrow,
  description,
  action,
}: {
  title: string;
  eyebrow: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action && <div className="heading-actions">{action}</div>}
    </div>
  );
}
function ProjectPicker({
  projects,
  selected,
  select,
}: {
  projects: Project[];
  selected: string;
  select: (id: string) => void;
}) {
  return (
    <label className="project-picker">
      Project
      <select value={selected} onChange={(e) => select(e.target.value)}>
        {projects.map((p) => (
          <option value={p.id} key={p.id}>
            {p.name}
          </option>
        ))}
      </select>
    </label>
  );
}
function AssignmentDetail({
  slot,
  close,
  onAbsence,
}: {
  slot: Assignment | Slot;
  close: () => void;
  onAbsence?: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    return () => ref.current?.close();
  }, []);
  return (
    <dialog ref={ref} className="editor-dialog assignment-drawer" onCancel={close}>
      <div className="editor-heading">
        <div>
          <div className="eyebrow">ASSIGNMENT DETAILS</div>
          <h2>{slot.task_name}</h2>
        </div>
        <button className="icon-button" aria-label="Close assignment" onClick={close}>
          <X size={20} />
        </button>
      </div>
      <div className="assignment-detail-body">
        <p>
          <strong>{slot.worker_name}</strong>
        </p>
        <p>
          {shortDate(slot.starts_at)}, {clock(slot.starts_at)}–{clock(slot.ends_at)}
        </p>
        {'project_name' in slot && <p>{slot.project_name}</p>}
        <span className="badge purple">{'status' in slot ? slot.status : 'Proposed'}</span>
        <p>
          Worksite: see the project record. Confirmed hours remain unchanged until an approved
          proposal is accepted and published.
        </p>
        {onAbsence && (
          <Button variant="outline" onClick={onAbsence}>
            Report exact absence dates
          </Button>
        )}
      </div>
    </dialog>
  );
}
