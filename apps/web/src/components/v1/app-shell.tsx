'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  House,
  BriefcaseBusiness,
  CalendarDays,
  UserRound,
  Bell,
  LogOut,
  Workflow,
  ChevronDown,
} from 'lucide-react';
import { market } from '@/lib/market';
import type { Notifications, Notification } from '@/lib/market-types';
import { initials } from '@/lib/format';
import { useSession } from './session';

const TABS = [
  { href: '/home', label: 'Home', icon: House },
  { href: '/work', label: 'Work', icon: BriefcaseBusiness },
  { href: '/schedule', label: 'Schedule', icon: CalendarDays },
  { href: '/profile', label: 'Profile', icon: UserRound },
] as const;

/** Plain sentences for each notification type. */
export function describe(n: Notification): string {
  const p = n.payload;
  switch (n.type) {
    case 'application.received':
      return `${p.applicant} applied to ${p.posting}`;
    case 'application.shortlisted':
      return `You’re on the shortlist for ${p.posting}`;
    case 'application.declined':
      return `${p.org} passed on your application for ${p.posting}`;
    case 'offer.received':
      return `${p.org} sent you an offer for ${p.posting}`;
    case 'offer.accepted':
      return `${p.applicant} accepted your offer for ${p.posting}`;
    case 'offer.declined':
      return `${p.applicant} declined your offer for ${p.posting}`;
    case 'application.withdrawn':
      return `${p.applicant} withdrew from ${p.posting}`;
    case 'offer.withdrawn':
      return `${p.org} withdrew the offer for ${p.posting}`;
    case 'engagement.cancelled':
      return `The contract for ${p.posting} was cancelled`;
    default:
      return String(p.message || 'Update on your work');
  }
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, signOut } = useSession();
  const pathname = usePathname();
  const [notes, setNotes] = useState<Notifications | null>(null);
  const [bellOpen, setBellOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const load = useCallback(() => {
    market<Notifications>('/notifications').then(setNotes, () => undefined);
  }, []);
  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load, pathname]);
  const name = me.organization?.name || me.user.full_name;
  const openPlanner = () => {
    // The crew planner uses its own demo persona; hand it this business's manager.
    try {
      if (me.planner_persona) localStorage.setItem('shift-persona', me.planner_persona);
    } catch {}
  };
  return (
    <div className="v1-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="v1-sidebar" aria-label="Main">
        <Link href="/home" className="v1-wordmark">
          shift<span>.</span>
        </Link>
        <nav className="v1-nav">
          {TABS.map((t) => (
            <NavLink
              key={t.href}
              tab={t}
              active={pathname.startsWith(t.href)}
              badge={t.href === '/work' ? notes?.work_badge : 0}
            />
          ))}
        </nav>
      </aside>
      <div className="v1-body">
        <header className="v1-header">
          <Link href="/home" className="v1-wordmark mobile-only">
            shift<span>.</span>
          </Link>
          <div className="v1-header-right">
            <Popover
              open={bellOpen}
              setOpen={(o) => {
                setBellOpen(o);
                setMenuOpen(false);
                if (o && notes?.unread) void market('/notifications/read', { method: 'POST' });
                if (!o) load();
              }}
              button={
                <>
                  <Bell size={20} aria-hidden="true" />
                  {!!notes?.unread && <span className="dot-count">{notes.unread}</span>}
                  <span className="sr-only">
                    Notifications{notes?.unread ? `, ${notes.unread} unread` : ''}
                  </span>
                </>
              }
              buttonClass="icon-button tap bell"
            >
              <div className="popover-panel notifications">
                <p className="popover-title">Notifications</p>
                {notes?.items.length ? (
                  <ul>
                    {notes.items.map((n) => (
                      <li key={n.id} className={n.read_at ? '' : 'unread'}>
                        <Link href="/work" onClick={() => setBellOpen(false)}>
                          {describe(n)}
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="popover-empty">
                    Nothing yet. Offers, applicants and status changes show up here.
                  </p>
                )}
              </div>
            </Popover>
            <Popover
              open={menuOpen}
              setOpen={(o) => {
                setMenuOpen(o);
                setBellOpen(false);
              }}
              buttonClass="account-button"
              button={
                <>
                  <span className="account-avatar" aria-hidden="true">
                    {initials(name)}
                  </span>
                  <span className="account-name">{name}</span>
                  <ChevronDown size={16} aria-hidden="true" />
                </>
              }
            >
              <div className="popover-panel account-menu">
                <p className="popover-title">
                  {me.user.full_name}
                  <small>{me.user.email}</small>
                </p>
                {me.planner_persona && (
                  <Link href="/planner" onClick={openPlanner} className="menu-item">
                    <Workflow size={18} aria-hidden="true" />
                    Crew planner
                  </Link>
                )}
                <button className="menu-item" onClick={() => void signOut()}>
                  <LogOut size={18} aria-hidden="true" />
                  Sign out
                </button>
              </div>
            </Popover>
          </div>
        </header>
        <main id="main" className="v1-main">
          {children}
        </main>
      </div>
      <nav className="v1-tabbar" aria-label="Main">
        {TABS.map((t) => (
          <NavLink
            key={t.href}
            tab={t}
            active={pathname.startsWith(t.href)}
            badge={t.href === '/work' ? notes?.work_badge : 0}
          />
        ))}
      </nav>
    </div>
  );
}

function NavLink({
  tab,
  active,
  badge,
}: {
  tab: (typeof TABS)[number];
  active: boolean;
  badge?: number;
}) {
  return (
    <Link
      href={tab.href}
      className={`v1-tab ${active ? 'active' : ''}`}
      aria-current={active ? 'page' : undefined}
    >
      <tab.icon size={22} aria-hidden="true" />
      <span>{tab.label}</span>
      {!!badge && (
        <span className="tab-badge" aria-label={`${badge} waiting`}>
          {badge}
        </span>
      )}
    </Link>
  );
}

function Popover({
  open,
  setOpen,
  button,
  buttonClass,
  children,
}: {
  open: boolean;
  setOpen: (o: boolean) => void;
  button: React.ReactNode;
  buttonClass: string;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (
        e instanceof KeyboardEvent ? e.key === 'Escape' : !ref.current?.contains(e.target as Node)
      )
        setOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, [open, setOpen]);
  return (
    <div className="popover" ref={ref}>
      <button className={buttonClass} aria-expanded={open} onClick={() => setOpen(!open)}>
        {button}
      </button>
      {open && children}
    </div>
  );
}
