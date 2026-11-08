'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  Clock3,
  HardHat,
  LayoutDashboard,
  LoaderCircle,
  MapPin,
  Menu,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
  X,
  TriangleAlert,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar } from '@/components/ui/avatar';
import { Calendar } from '@/components/team-calendar';
import { ProjectCard } from '@/components/project-card';
import { clock, shortDate, money, initials } from '@/lib/display';
import { request } from '@/lib/api';
import type { Assignment, Dashboard, Draft, Persona, Project } from '@/lib/types';

type View = 'overview' | 'calendar' | 'projects' | 'talent' | 'schedule';
const navigation = [
  { id: 'overview' as View, label: 'Overview', icon: LayoutDashboard },
  { id: 'calendar' as View, label: 'Team calendar', icon: CalendarDays },
  { id: 'projects' as View, label: 'Projects', icon: BriefcaseBusiness },
  { id: 'talent' as View, label: 'Talent marketplace', icon: Users },
  { id: 'schedule' as View, label: 'Schedule lab', icon: Workflow },
];
export function Workspace() {
  const [view, setView] = useState<View>('overview'),
    [persona, setPersona] = useState('demo-manager'),
    [people, setPeople] = useState<Persona[]>([]),
    [data, setData] = useState<Dashboard | null>(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [mobile, setMobile] = useState(false),
    [selected, setSelected] = useState('eastside'),
    [draft, setDraft] = useState<Draft | null>(null),
    [search, setSearch] = useState(''),
    [notice, setNotice] = useState(''),
    [disruption, setDisruption] = useState<Assignment | null>(null),
    [projectDetail, setProjectDetail] = useState<Project | null>(null);
  const generation = useRef(0);
  const load = useCallback(async () => {
    const turn = ++generation.current;
    try {
      const response = await request<Dashboard>('/dashboard', persona);
      if (turn === generation.current) {
        setData(response);
        setError('');
      }
    } catch (e) {
      if (turn === generation.current) setError((e as Error).message);
    }
  }, [persona]);
  useEffect(() => {
    setData(null);
    setDraft(null);
    setDisruption(null);
    setProjectDetail(null);
    void load();
    const id = setInterval(() => void load(), 15000);
    return () => {
      clearInterval(id);
      generation.current++;
    };
  }, [load]);
  useEffect(() => {
    request<Persona[]>('/personas', 'demo-manager')
      .then(setPeople)
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (!notice) return;
    const id = setTimeout(() => setNotice(''), 6000);
    return () => clearTimeout(id);
  }, [notice]);
  const go = (next: View) => {
    setView(next);
    setMobile(false);
    setSearch('');
  };
  const mutate = async (path: string) => {
    setBusy(true);
    setError('');
    try {
      await request(path, persona, 'POST');
      await load();
      setDraft(null);
      setDisruption(null);
      setNotice('Worker marked unavailable for this project week. Confirmed history preserved.');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const generate = async () => {
    setBusy(true);
    setError('');
    try {
      setDraft(await request<Draft>(`/projects/${selected}/draft`, persona, 'POST'));
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const isWorker = data?.persona.role === 'worker',
    confirmed = data?.assignments.filter((a) => a.status === 'confirmed') || [],
    gaps = data?.staffing_gaps || 0;
  const navTitle =
    view === 'calendar' && isWorker ? 'My schedule' : navigation.find((n) => n.id === view)?.label;
  const projects = data?.projects || [];
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobile ? 'sidebar-open' : ''}`}>
        <a
          className="wordmark"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            go('overview');
          }}
          aria-label="SHIFT overview"
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
            <Building2 size={18} />
          </span>
          <div>
            <strong>Northline Works</strong>
            <small>Company workspace</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <p className="nav-caption">WORKSPACE</p>
        <nav aria-label="Workspace">
          {navigation
            .filter((n) => !isWorker || n.id !== 'schedule')
            .map((n) => (
              <button
                key={n.id}
                className={`nav-item ${view === n.id ? 'active' : ''}`}
                onClick={() => go(n.id)}
              >
                <n.icon size={18} />
                <span>{n.id === 'calendar' && isWorker ? 'My schedule' : n.label}</span>
                {n.id === 'projects' && data && <small>{projects.length}</small>}
                {n.id === 'schedule' && <span className="new-tag">LAB</span>}
              </button>
            ))}
        </nav>
        <div className="sidebar-projects">
          <p className="nav-caption">YOUR PROJECTS</p>
          {projects.map((p) => (
            <button
              key={p.id}
              className="project-nav"
              onClick={() => {
                go('projects');
                setProjectDetail(p);
              }}
            >
              <span className="project-dot" style={{ background: p.color }} />
              {p.name.split(' ').slice(0, 2).join(' ')}
            </button>
          ))}
        </div>
        <div className="sidebar-bottom">
          <div className="demo-card">
            <span>
              <Zap size={15} /> A more connected workforce
            </span>
            <p>
              People, projects, and possibilities.
              <br />
              All moving in the same direction.
            </p>
            <button onClick={() => go(isWorker ? 'calendar' : 'schedule')}>
              Explore {isWorker ? 'your schedule' : 'Schedule lab'} <ArrowUpRight size={14} />
            </button>
          </div>
          <div className="profile">
            <span className="avatar profile-avatar">
              {initials(data?.persona.name || 'Alex Morgan')}
            </span>
            <div>
              <strong>{data?.persona.name || 'Alex Morgan'}</strong>
              <small>
                {data?.persona.role === 'admin'
                  ? 'Company administrator'
                  : isWorker
                    ? 'Worker workspace'
                    : 'Project manager'}
              </small>
            </div>
            <span className="status-dot" />
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
            <ChevronRight size={13} />
            <strong>{navTitle}</strong>
          </div>
          <div className="topbar-right">
            <span className="demo-badge">
              <span /> FICTIONAL DEMO
            </span>
            <label className="persona-select">
              <span className="sr-only">Demo persona</span>
              <select
                value={persona}
                onChange={(e) => {
                  setPersona(e.target.value);
                  go('overview');
                }}
              >
                {people.length ? (
                  people.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} · {p.role}
                    </option>
                  ))
                ) : (
                  <option value="demo-manager">Alex Morgan · manager</option>
                )}
              </select>
              <ChevronDown size={13} />
            </label>
          </div>
        </header>
        <div className="content">
          {error && (
            <div className="banner error" role="alert">
              <TriangleAlert size={18} />
              <div>
                <strong>Couldn’t refresh the workspace.</strong>
                <p>
                  {error}
                  {data ? ' Displaying previously loaded data.' : ''}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => void load()}>
                Retry
              </Button>
            </div>
          )}
          {!data ? (
            <div className="loading-state">
              <LoaderCircle className="spin" size={26} />
              <h1>Getting your workspace ready</h1>
              <p>Connecting to the local SHIFT API…</p>
            </div>
          ) : (
            <>
              {view === 'overview' && (
                <>
                  <div className="page-heading">
                    <div>
                      <div className="eyebrow">YOUR WORKFORCE, IN SYNC</div>
                      <h1>
                        Good morning, {data.persona.name.split(' ')[0]}
                        <span className="greeting-dot">.</span>
                      </h1>
                      <p>Let’s make great work happen. Here’s your week at a glance.</p>
                    </div>
                    <div className="heading-actions">
                      <span className="date-pill">
                        <CalendarDays size={15} /> Nov 9 – 13, 2026
                      </span>
                      <Button onClick={() => go(isWorker ? 'calendar' : 'schedule')}>
                        {isWorker ? 'View my schedule' : 'Plan your workforce'}
                        <ArrowRight size={15} />
                      </Button>
                    </div>
                  </div>
                  <div className="stats-grid">
                    {[
                      {
                        label: isWorker ? 'My projects' : 'Active projects',
                        value: projects.length,
                        icon: BriefcaseBusiness,
                        detail: 'In this workspace',
                        color: 'purple',
                      },
                      {
                        label: isWorker ? 'Confirmed assignments' : 'Team members',
                        value: isWorker ? confirmed.length : data.workers.length,
                        icon: isWorker ? CheckCheck : Users,
                        detail: isWorker
                          ? 'Accepted work only'
                          : `${data.workers.filter((w) => w.employment_type === 'contractor').length} independent contractors`,
                        color: 'green',
                      },
                      {
                        label: isWorker ? 'Published windows' : 'Confirmed assignments',
                        value: isWorker
                          ? data.workers[0]?.availability.length || 0
                          : confirmed.length,
                        icon: CalendarDays,
                        detail: isWorker
                          ? 'Your shared availability'
                          : 'Across all visible projects',
                        color: 'blue',
                      },
                      {
                        label: isWorker ? 'Open opportunities' : 'Staffing gaps',
                        value: isWorker ? data.jobs.length : gaps,
                        icon: isWorker ? Search : TriangleAlert,
                        detail: isWorker
                          ? 'Explore project-based roles'
                          : gaps
                            ? 'Ready for your next move'
                            : 'All tasks staffed',
                        color: 'amber',
                      },
                    ].map((s) => (
                      <section className="stat-card" key={s.label}>
                        <div>
                          <span>{s.label}</span>
                          <span className={`stat-icon ${s.color}`}>
                            <s.icon size={17} />
                          </span>
                        </div>
                        <strong>{String(s.value).padStart(2, '0')}</strong>
                        <p>
                          <span className={`tiny-dot ${s.color}`} />
                          {s.detail}
                        </p>
                      </section>
                    ))}
                  </div>
                  {!isWorker && gaps > 0 && (
                    <div className="recovery-banner">
                      <div className="recovery-icon">
                        <Sparkles size={20} />
                      </div>
                      <div>
                        <strong>Great teams don’t miss a beat.</strong>
                        <p>
                          {gaps} task{gaps === 1 ? ' needs' : 's need'} coverage. Find qualified
                          people and build a feasible plan.
                        </p>
                      </div>
                      <Button variant="outline" onClick={() => go('schedule')}>
                        Review staffing gaps
                        <ArrowRight size={14} />
                      </Button>
                    </div>
                  )}
                  <section className="panel">
                    <div className="section-heading">
                      <div>
                        <h2>
                          {isWorker
                            ? 'Your week, clearly planned.'
                            : 'The right people. The right place.'}
                        </h2>
                        <p>
                          {isWorker
                            ? 'Confirmed assignments across your projects.'
                            : 'Your team’s confirmed assignments across projects.'}
                        </p>
                      </div>
                      <div className="section-actions">
                        <div className="avatar-stack">
                          {data.workers.slice(0, 4).map((w) => (
                            <Avatar key={w.id} worker={w} small />
                          ))}
                          {data.workers.length > 4 && (
                            <span className="stack-count">+{data.workers.length - 4}</span>
                          )}
                        </div>
                        <Button variant="outline" size="sm" onClick={() => go('calendar')}>
                          Open calendar
                          <ArrowUpRight size={14} />
                        </Button>
                      </div>
                    </div>
                    <Calendar data={data} compact />
                    <div className="calendar-footer">
                      <div className="legend">
                        {projects.map((p) => (
                          <span key={p.id}>
                            <i style={{ background: p.color }} />
                            {p.name.split(' ').slice(0, 2).join(' ')}
                          </span>
                        ))}
                      </div>
                      <span>
                        <ShieldCheck size={12} /> Confirmed assignments only
                      </span>
                    </div>
                  </section>
                  <div className="overview-bottom">
                    <section>
                      <div className="section-title">
                        <h2>
                          Projects in motion<span>{projects.length}</span>
                        </h2>
                        <button onClick={() => go('projects')}>
                          View projects
                          <ArrowRight size={14} />
                        </button>
                      </div>
                      <div className="project-grid">
                        {projects.slice(0, 2).map((p) => (
                          <ProjectCard
                            key={p.id}
                            project={p}
                            workers={data.workers}
                            assignments={confirmed}
                            open={() => {
                              setProjectDetail(p);
                              go('projects');
                            }}
                          />
                        ))}
                      </div>
                      {!projects.length && (
                        <div className="empty-card">Your assigned projects will appear here.</div>
                      )}
                    </section>
                    <section className="talent-teaser">
                      <div className="teaser-dots">
                        <i />
                        <i />
                        <i />
                      </div>
                      <span className="eyebrow">GOOD PEOPLE. GREAT POSSIBILITIES.</span>
                      <h2>
                        Your next great
                        <br />
                        teammate is out there.
                      </h2>
                      <p>
                        Connect with skilled professionals
                        <br />
                        ready for their next project.
                      </p>
                      <Button variant="outline" onClick={() => go('talent')}>
                        Explore the marketplace
                        <ArrowUpRight size={14} />
                      </Button>
                      <div className="teaser-footer">
                        <ShieldCheck size={13} /> Skills and certifications, front and center.
                      </div>
                    </section>
                  </div>
                </>
              )}
              {view === 'calendar' && (
                <>
                  <PageTitle
                    eyebrow="ONE TEAM. ONE SHARED VIEW."
                    title={
                      isWorker ? 'Make room for great work.' : 'Every project. Everyone in view.'
                    }
                    description="Confirmed assignments and published availability · America/Edmonton"
                    action={
                      <span className="date-pill">
                        <CalendarDays size={15} /> November 9–13, 2026
                      </span>
                    }
                  />
                  <div className="info-note">
                    <ShieldCheck size={17} /> Private calendar details stay private. Only published
                    availability and opaque busy intervals appear here.
                  </div>
                  <section className="panel">
                    <Calendar data={data} />
                    <div className="calendar-footer">
                      <span>Half-open time windows · local Edmonton time</span>
                      <span>Refreshes every 15 seconds</span>
                    </div>
                  </section>
                  <section className="panel availability-panel">
                    <div className="section-heading">
                      <div>
                        <h2>Published availability</h2>
                        <p>Shared by each worker. Busy windows do not disclose a reason.</p>
                      </div>
                    </div>
                    {data.workers.map((w) => (
                      <div className="availability-row" key={w.id}>
                        <div className="worker-name">
                          <Avatar worker={w} small />
                          <strong>{w.name}</strong>
                        </div>
                        <span>{w.availability.length} published windows</span>
                        <div>
                          {w.busy.length ? (
                            w.busy.map((b, i) => (
                              <span className="badge neutral" key={i}>
                                Busy · {shortDate(b.starts_at)} {clock(b.starts_at)}–
                                {clock(b.ends_at)}
                              </span>
                            ))
                          ) : (
                            <span className="available-label">No additional busy windows</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </section>
                </>
              )}
              {view === 'projects' && (
                <>
                  <PageTitle
                    eyebrow="WORK THAT MOVES US FORWARD"
                    title="A shared plan. A clear direction."
                    description="Project scopes, task requirements, and confirmed coverage."
                    action={
                      <Button
                        variant="outline"
                        onClick={() => {
                          setProjectDetail(null);
                          void load();
                        }}
                      >
                        <RefreshCw size={14} />
                        Refresh projects
                      </Button>
                    }
                  />
                  <div className="project-grid full-project-grid">
                    {projects.map((p) => (
                      <ProjectCard
                        key={p.id}
                        project={p}
                        workers={data.workers}
                        assignments={confirmed}
                        open={() => setProjectDetail(p)}
                      />
                    ))}
                  </div>
                  {projectDetail && (
                    <section className="panel project-detail">
                      <div className="section-heading">
                        <div>
                          <h2>{projectDetail.name}</h2>
                          <p>
                            {projectDetail.client} · {projectDetail.location}
                          </p>
                        </div>
                        <button
                          className="icon-button"
                          aria-label="Close project detail"
                          onClick={() => setProjectDetail(null)}
                        >
                          <X size={18} />
                        </button>
                      </div>
                      <div className="project-facts">
                        <span>
                          <Clock3 size={15} />
                          Deadline {shortDate(projectDetail.deadline)}
                        </span>
                        <span>
                          <Users size={15} />
                          Site capacity {projectDetail.capacity}
                        </span>
                        <span>
                          Labour budget{' '}
                          {projectDetail.budget_cents === null
                            ? 'Not set'
                            : money(projectDetail.budget_cents)}
                        </span>
                      </div>
                      <div className="task-table">
                        {projectDetail.tasks.map((t) => (
                          <div className="task-row" key={t.id}>
                            <span
                              className={`task-check ${t.confirmed_count >= t.crew_size ? 'filled' : ''}`}
                            >
                              {t.confirmed_count >= t.crew_size ? <Check size={13} /> : <span />}
                            </span>
                            <div>
                              <strong>{t.name}</strong>
                              <p>
                                {t.required_skills.join(', ')} ·{' '}
                                {t.required_certifications.join(', ')} · {t.duration_hours}h
                              </p>
                            </div>
                            <span
                              className={`badge ${t.confirmed_count >= t.crew_size ? 'green' : 'amber'}`}
                            >
                              {t.confirmed_count}/{t.crew_size} staffed
                            </span>
                          </div>
                        ))}
                      </div>
                      {!isWorker && (
                        <div className="panel-bottom">
                          <Button
                            onClick={() => {
                              setSelected(projectDetail.id);
                              go('schedule');
                            }}
                          >
                            Generate a schedule
                            <Workflow size={15} />
                          </Button>
                        </div>
                      )}
                    </section>
                  )}
                  <div className="foundation-note">
                    Foundation: project editing and dependency management are specified in the next
                    milestone. Existing project records are live database fixtures.
                  </div>
                </>
              )}
              {view === 'talent' && (
                <>
                  <PageTitle
                    eyebrow="FIND YOUR NEXT GREAT CONNECTION"
                    title={
                      isWorker
                        ? 'The next chapter starts here.'
                        : 'More talent. More possibilities.'
                    }
                    description="Project opportunities and skilled independent professionals."
                  />
                  <div className="talent-toolbar">
                    <label className="search-field">
                      <Search size={17} />
                      <input
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder={
                          isWorker
                            ? 'Search roles or skills…'
                            : 'Search people, skills, or qualifications…'
                        }
                        aria-label="Search marketplace"
                      />
                    </label>
                    <span className="subtle">Fictional demonstration profiles · CAD rates</span>
                  </div>
                  {!isWorker && (
                    <>
                      <div className="section-title">
                        <h2>Independent professionals</h2>
                        <span className="subtle">Profile data, not an availability guarantee</span>
                      </div>
                      <div className="talent-grid">
                        {data.workers
                          .filter(
                            (w) =>
                              w.employment_type === 'contractor' &&
                              `${w.name} ${w.skills.join(' ')} ${w.certifications.map((c) => c.name).join(' ')}`
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
                                <MapPin size={12} />
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
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    go('schedule');
                                    setNotice(
                                      'Choose a project. The solver checks availability and qualifications before proposing a contractor.',
                                    );
                                  }}
                                >
                                  Check fit
                                  <ArrowRight size={13} />
                                </Button>
                              </div>
                            </article>
                          ))}
                      </div>
                    </>
                  )}
                  <div className="section-title opportunities-title">
                    <h2>
                      Open project opportunities<span>{data.jobs.length}</span>
                    </h2>
                  </div>
                  <div className="jobs-list">
                    {data.jobs
                      .filter(
                        (j) =>
                          !isWorker ||
                          `${j.title} ${j.skills.join(' ')}`
                            .toLowerCase()
                            .includes(search.toLowerCase()),
                      )
                      .map((j) => (
                        <article className="panel job-card" key={j.id}>
                          <span className="job-icon">
                            <HardHat size={23} />
                          </span>
                          <div>
                            <h3>{j.title}</h3>
                            <p>
                              {j.location} · {j.work_mode.replace('_', ' ')} ·{' '}
                              {j.skills.join(' / ')}
                            </p>
                          </div>
                          <strong>
                            {money(j.rate_min_cents)}–{money(j.rate_max_cents)}
                            <small> / hr</small>
                          </strong>
                        </article>
                      ))}
                  </div>
                  <div className="foundation-note">
                    Applications, posting editors, and invitations are the next marketplace
                    milestone. Search filters the live profiles and roles above.
                  </div>
                </>
              )}
              {view === 'schedule' && !isWorker && (
                <>
                  <PageTitle
                    eyebrow="WHEN PLANS CHANGE, KEEP MOVING"
                    title="A better plan starts with the right fit."
                    description="Constraint-based scheduling, powered by Google OR-Tools CP-SAT."
                    action={
                      <Button variant="outline" onClick={() => void load()}>
                        <RefreshCw size={14} />
                        Refresh inputs
                      </Button>
                    }
                  />
                  <div className="solver-layout">
                    <section className="panel solver-input">
                      <div className="section-heading">
                        <div>
                          <h2>Plan your recovery</h2>
                          <p>Existing commitments stay fixed.</p>
                        </div>
                        <Workflow size={20} />
                      </div>
                      <div className="solver-body">
                        <label className="field-label">
                          Project
                          <select
                            value={selected}
                            onChange={(e) => {
                              setSelected(e.target.value);
                              setDraft(null);
                            }}
                          >
                            {projects.map((p) => (
                              <option value={p.id} key={p.id}>
                                {p.name}
                              </option>
                            ))}
                          </select>
                        </label>
                        <div className="constraints-list">
                          <span>
                            <Check size={14} /> Skills & valid certifications
                          </span>
                          <span>
                            <Check size={14} /> Availability & private busy windows
                          </span>
                          <span>
                            <Check size={14} /> Cross-project non-overlap
                          </span>
                          <span>
                            <Check size={14} /> Dependencies & shared site capacity
                          </span>
                          <span>
                            <Check size={14} /> Deadline & labour budget
                          </span>
                        </div>
                        <Button
                          className="full-button"
                          disabled={busy || !projects.length}
                          onClick={() => void generate()}
                        >
                          {busy ? (
                            <LoaderCircle size={15} className="spin" />
                          ) : (
                            <Sparkles size={15} />
                          )}
                          Generate draft schedule
                        </Button>
                        <p className="solver-disclaimer">
                          Drafts are proposals. Generating one never changes confirmed assignments.
                        </p>
                      </div>
                    </section>
                    <section className="panel">
                      <div className="section-heading">
                        <div>
                          <h2>Current confirmed plan</h2>
                          <p>Explicitly record a disruption before replanning.</p>
                        </div>
                        <span className="badge green">CONFIRMED</span>
                      </div>
                      {confirmed
                        .filter((a) => a.project_id === selected)
                        .map((a) => (
                          <div className="current-assignment" key={a.id}>
                            <div className="assignment-line" style={{ background: a.color }} />
                            <div>
                              <strong>{a.task_name}</strong>
                              <p>
                                {a.worker_name} · {shortDate(a.starts_at)}, {clock(a.starts_at)}–
                                {clock(a.ends_at)}
                              </p>
                            </div>
                            <Button size="sm" variant="ghost" onClick={() => setDisruption(a)}>
                              Record absence
                              <ArrowRight size={13} />
                            </Button>
                          </div>
                        ))}
                      {!confirmed.some((a) => a.project_id === selected) && (
                        <div className="empty-card">No confirmed assignments for this project.</div>
                      )}
                      <div className="solver-fixed-note">
                        <ShieldCheck size={15} />
                        No assignment will be moved without an approved change.
                      </div>
                    </section>
                  </div>
                  {draft ? (
                    <section className="panel draft-panel">
                      <div className="section-heading">
                        <div>
                          <h2>
                            {draft.proposals.length ? 'Your proposed schedule' : 'Solver result'}
                          </h2>
                          <p>
                            Draft {draft.id.slice(0, 8)} · persisted separately from confirmed work
                          </p>
                        </div>
                        <span
                          className={`badge ${['OPTIMAL', 'FEASIBLE'].includes(draft.solver_status) ? 'purple' : 'amber'}`}
                        >
                          {draft.solver_status}
                        </span>
                      </div>
                      {draft.blockers.length > 0 && (
                        <div className="blockers">
                          <TriangleAlert size={20} />
                          <div>
                            <strong>These constraints need attention.</strong>
                            {draft.blockers.map((b, i) => (
                              <p key={i}>{b}</p>
                            ))}
                          </div>
                        </div>
                      )}
                      {draft.proposals.map((p, i) => (
                        <div className="proposal-row" key={i}>
                          <span className="proposal-icon">
                            <Sparkles size={17} />
                          </span>
                          <div>
                            <strong>{p.task_name}</strong>
                            <p>
                              {p.worker_name} · {shortDate(p.starts_at)} · {clock(p.starts_at)}–
                              {clock(p.ends_at)}
                            </p>
                          </div>
                          <span className="badge purple">Proposed</span>
                          <strong className="proposal-cost">{money(p.cost_cents)}</strong>
                        </div>
                      ))}
                      <div className="draft-footer">
                        <div>
                          <span>Planned project labour</span>
                          <strong>
                            {draft.cost_cents === null
                              ? 'Not feasible / not calculated'
                              : money(draft.cost_cents)}
                          </strong>
                        </div>
                        <p>
                          Includes fixed confirmed work. Manager approval and contractor acceptance
                          are the next milestone; this draft does not reserve time or create
                          invitations.
                        </p>
                      </div>
                    </section>
                  ) : (
                    <div className="solver-empty">
                      <span>
                        <Workflow size={30} />
                      </span>
                      <h2>A plan you can trust, not a guess.</h2>
                      <p>
                        Select a project and generate a draft. The solver checks every modeled
                        constraint
                        <br />
                        and reports blockers when a feasible schedule cannot be found.
                      </p>
                      <div>
                        <span>01 &nbsp; Validate</span>
                        <ChevronRight size={14} />
                        <span>02 &nbsp; Solve</span>
                        <ChevronRight size={14} />
                        <span>03 &nbsp; Review draft</span>
                      </div>
                    </div>
                  )}
                  <div className="foundation-note">
                    Hourly, non-preemptive local-demo model. Travel, overtime laws, split shifts,
                    and partial-crew recovery are not yet modeled. No production scheduling claim is
                    made.
                  </div>
                  <div className="demo-reset">
                    <span>
                      Need a fresh fixture? Demo reset restores fictional data and removes drafts.
                    </span>
                    <Button
                      disabled={busy || data.persona.role !== 'admin'}
                      variant="ghost"
                      size="sm"
                      onClick={async () => {
                        if (
                          !window.confirm('Reset all fictional demo data and discard local drafts?')
                        )
                          return;
                        setBusy(true);
                        try {
                          await request('/demo/reset', persona, 'POST');
                          await load();
                          setDraft(null);
                          setNotice('Fictional demo restored.');
                        } catch (e) {
                          setError((e as Error).message);
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      Reset demo (admin only)
                    </Button>
                  </div>
                </>
              )}
              {view === 'schedule' && isWorker && (
                <div className="info-note">
                  Schedule drafts are available to managers. Choose My schedule to view your
                  confirmed work.
                </div>
              )}
              <footer className="footer">
                <span>
                  <span className="footer-brand">shift.</span> Workforce, in sync.
                </span>
                <span>Local foundation · Fictional data · natHacks 2026</span>
              </footer>
            </>
          )}
        </div>
      </main>
      {notice && (
        <div className="toast" role="status">
          <Check size={17} />
          {notice}
          <button aria-label="Dismiss notification" onClick={() => setNotice('')}>
            <X size={14} />
          </button>
        </div>
      )}
      {disruption && (
        <AbsenceDialog
          assignment={disruption}
          busy={busy}
          close={() => setDisruption(null)}
          confirm={() => void mutate(`/assignments/${disruption.id}/disrupt`)}
        />
      )}
    </div>
  );
}
function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
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
function AbsenceDialog({
  assignment,
  busy,
  close,
  confirm,
}: {
  assignment: Assignment;
  busy: boolean;
  close: () => void;
  confirm: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal-overlay"
      aria-labelledby="absence-title"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) close();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) close();
      }}
    >
      <section className="modal">
        <span className="modal-symbol">
          <TriangleAlert size={25} />
        </span>
        <h2 id="absence-title">Record this worker’s absence?</h2>
        <p>
          This explicitly marks <strong>{assignment.worker_name}</strong> unavailable for the
          project week, and marks <strong>{assignment.task_name}</strong> disrupted. The confirmed
          assignment remains in history; other work is preserved.
        </p>
        <p>A new draft will not be approved or accepted automatically.</p>
        <div className="modal-actions">
          <Button autoFocus disabled={busy} variant="outline" onClick={close}>
            Keep assignment
          </Button>
          <Button disabled={busy} variant="danger" onClick={confirm}>
            {busy ? 'Recording…' : 'Record absence'}
          </Button>
        </div>
      </section>
    </dialog>
  );
}
