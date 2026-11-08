'use client';
import { useState } from 'react';
import Link from 'next/link';
import {
  CircleCheck,
  CircleMinus,
  Clock3,
  Inbox,
  Mail,
  Star,
  CircleX,
  BadgeCheck,
  MapPin,
} from 'lucide-react';
import { market } from '@/lib/market';
import type { ApplicationStatus, ApplicationView } from '@/lib/market-types';
import { dollars, range } from '@/lib/format';
import { StatusChip, type Tone } from './ui';

const STATUS: Record<ApplicationStatus, { tone: Tone; label: string; icon: typeof Clock3 }> = {
  applied: { tone: 'muted', label: 'Applied', icon: Clock3 },
  invited: { tone: 'warn', label: 'Invited', icon: Mail },
  shortlisted: { tone: 'warn', label: 'Shortlisted', icon: Star },
  offered: { tone: 'warn', label: 'Offer waiting', icon: Inbox },
  accepted: { tone: 'ok', label: 'Accepted', icon: CircleCheck },
  declined: { tone: 'muted', label: 'Declined', icon: CircleMinus },
  withdrawn: { tone: 'muted', label: 'Withdrawn', icon: CircleMinus },
  completed: { tone: 'muted', label: 'Completed', icon: CircleCheck },
};

export function ApplicationChip({ status }: { status: ApplicationStatus }) {
  const s = STATUS[status];
  return <StatusChip tone={s.tone} label={s.label} icon={s.icon} />;
}

async function act(id: string, action: string) {
  return market<ApplicationView>(`/applications/${id}/action`, {
    method: 'POST',
    body: { action },
  });
}

/** What the applicant sees about their own application, with its one next step. */
export function ApplicationStatusBlock({
  application: a,
  onChange,
  acceptSlot,
}: {
  application: ApplicationView;
  onChange: () => Promise<void> | void;
  acceptSlot?: React.ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const run = async (action: string, confirm?: string) => {
    if (confirm && !window.confirm(confirm)) return;
    setBusy(true);
    setError('');
    try {
      await act(a.id, action);
      await onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="application-block">
      <div className="application-block-top">
        <ApplicationChip status={a.status} />
        <span className="wallet-meta">
          {a.status === 'offered'
            ? 'They’d like to hire you. Final dates, pay and site are above.'
            : a.status === 'accepted' && a.engagement
              ? `Booked ${range(a.engagement.start_date, a.engagement.end_date)}`
              : a.status === 'shortlisted'
                ? 'You’re on the shortlist.'
                : a.status === 'applied'
                  ? 'The business can see your profile and certifications.'
                  : ''}
        </span>
      </div>
      {error && (
        <p className="v1-inline-error" role="alert">
          {error}
        </p>
      )}
      <div className="actions">
        {a.status === 'offered' && acceptSlot}
        {a.status === 'offered' && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() => void run('decline_offer', 'Decline this offer?')}
          >
            Decline offer
          </button>
        )}
        {['applied', 'shortlisted', 'invited'].includes(a.status) && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() => void run('withdraw', 'Withdraw your application?')}
          >
            Withdraw application
          </button>
        )}
      </div>
    </div>
  );
}

/** A row in the applicant's Work lists. */
export function MyApplicationRow({
  application: a,
  children,
}: {
  application: ApplicationView;
  children?: React.ReactNode;
}) {
  const p = a.posting;
  return (
    <li className="work-row">
      <div className="work-row-main">
        <Link href={`/postings/${p.id}`} className="work-row-title">
          {p.title}
        </Link>
        <p className="wallet-meta">
          {p.org.name}, {p.city} · {range(p.start_date, p.end_date)} · {dollars(p.pay_rate_cents)}{' '}
          {p.pay_unit === 'hour' ? 'per hour' : p.pay_unit === 'day' ? 'per day' : 'fixed'}
        </p>
        {children}
      </div>
      <ApplicationChip status={a.status} />
    </li>
  );
}

/** Business view of one applicant: credential match at a glance + Shortlist / Offer / Decline. */
export function ApplicantRow({
  application,
  onChanged,
}: {
  application: ApplicationView;
  onChanged: () => void;
}) {
  const [a, setA] = useState(application);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const m = a.posting.match;
  const missing = m.items.filter((i) => i.required && i.state === 'missing');
  const pending = m.items.filter((i) => i.required && i.state === 'pending');
  const run = async (action: string, optimistic: ApplicationStatus, confirm?: string) => {
    if (confirm && !window.confirm(confirm)) return;
    const before = a;
    setBusy(true);
    setError('');
    setA({ ...a, status: optimistic });
    try {
      setA(await act(a.id, action));
      onChanged();
    } catch (e) {
      setA(before);
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <li className="applicant-row">
      <div className="applicant-main">
        <div className="applicant-name">
          <strong>{a.applicant.name}</strong>
          {a.applicant.kind === 'agency' && a.applicant.verified && (
            <span className="verified-mark">
              <BadgeCheck size={16} aria-hidden="true" />
              Verified
            </span>
          )}
        </div>
        {a.applicant.headline && <p>{a.applicant.headline}</p>}
        <p className="wallet-meta">
          <MapPin size={15} aria-hidden="true" />
          {a.applicant.city || 'City not set'}
          {a.applicant.distance_km == null
            ? ''
            : a.applicant.distance_km < 2
              ? ', same city as the site'
              : `, ${a.applicant.distance_km} km from the site`}
        </p>
        {a.crew_size && (
          <p className="wallet-meta">
            Crew of {a.crew_size}
            {a.proposed_rate_cents ? ` at ${dollars(a.proposed_rate_cents)} per worker` : ''}
          </p>
        )}
        <p className={`match-line ${missing.length ? 'bad' : pending.length ? 'warn' : 'ok'}`}>
          {missing.length ? (
            <CircleX size={18} aria-hidden="true" />
          ) : pending.length ? (
            <Clock3 size={18} aria-hidden="true" />
          ) : (
            <CircleCheck size={18} aria-hidden="true" />
          )}
          {m.required_held} of {m.required_total} required certs
          {pending.length ? `, ${pending.length} not yet verified` : ''}
          {missing.length ? `, missing ${missing.map((i) => i.name).join(', ')}` : ''}
        </p>
        {a.note && <p className="applicant-note">“{a.note}”</p>}
        {error && (
          <p className="v1-inline-error" role="alert">
            {error}
          </p>
        )}
      </div>
      <div className="applicant-side">
        <ApplicationChip status={a.status} />
        <div className="actions">
          {['applied', 'shortlisted'].includes(a.status) && (
            <button
              className="button button-primary button-sm"
              disabled={busy}
              onClick={() =>
                void run(
                  'offer',
                  'offered',
                  `Send ${a.applicant.name} an offer? They’ll see the final dates, pay and site address.`,
                )
              }
            >
              Send offer
            </button>
          )}
          {['applied', 'invited'].includes(a.status) && (
            <button
              className="button button-outline button-sm"
              disabled={busy}
              onClick={() => void run('shortlist', 'shortlisted')}
            >
              Shortlist
            </button>
          )}
          {['applied', 'invited', 'shortlisted'].includes(a.status) && (
            <button
              className="text-button"
              disabled={busy}
              onClick={() => void run('decline', 'declined', `Decline ${a.applicant.name}?`)}
            >
              Decline
            </button>
          )}
          {a.status === 'offered' && (
            <button
              className="text-button"
              disabled={busy}
              onClick={() => void run('withdraw_offer', 'withdrawn', 'Withdraw this offer?')}
            >
              Withdraw offer
            </button>
          )}
        </div>
      </div>
    </li>
  );
}
