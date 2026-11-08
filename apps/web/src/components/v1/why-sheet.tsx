'use client';
import { useEffect } from 'react';
import {
  Award,
  BadgeCheck,
  CalendarCheck,
  CalendarClock,
  CircleX,
  Clock3,
  History,
  MapPin,
  ShieldCheck,
  Wallet,
  type LucideIcon,
} from 'lucide-react';
import type { PostingCard } from '@/lib/market-types';
import { dollars } from '@/lib/format';
import { useSession } from './session';

type Row = { icon: LucideIcon; text: string; strength: number; chips?: React.ReactNode };

const daysUntil = (iso: string) =>
  Math.round((Date.parse(iso.slice(0, 10) + 'T12:00:00') - Date.now()) / 86400000);

/** WHY-1/2: each ranking reason as an icon, a plain sentence and a strength bar. */
export function WhySheet({
  card,
  onClose,
  onApply,
}: {
  card: PostingCard;
  onClose: () => void;
  onApply?: () => void;
}) {
  const { me } = useSession();
  const profile = me.worker_profile;
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', esc);
    return () => document.removeEventListener('keydown', esc);
  }, [onClose]);
  const rows: Row[] = [];
  if (card.distance_km != null && profile) {
    const r = profile.travel_radius_km;
    const d = card.distance_km;
    rows.push({
      icon: MapPin,
      text:
        d < 2
          ? `In your city, well inside your ${r} km radius`
          : d <= r
            ? `${d} km from you, ${d <= r / 2 ? 'well ' : ''}inside your ${r} km radius`
            : `${d} km from you, outside your ${r} km radius`,
      strength: Math.max(0, 1 - d / Math.max(r, 1)),
    });
  }
  const start = daysUntil(card.start_date);
  rows.push({
    icon: CalendarClock,
    text:
      start <= 0 ? 'Already started' : start === 1 ? 'Starts tomorrow' : `Starts in ${start} days`,
    strength: start <= 0 ? 0.2 : Math.max(0.15, 1 - start / 90),
  });
  const required = card.match.items.filter((i) => i.required);
  rows.push({
    icon: ShieldCheck,
    text: required.length
      ? `You hold ${card.match.required_held} of ${card.match.required_total} required certs`
      : 'No certifications required',
    strength: required.length ? card.match.required_held / card.match.required_total : 1,
    chips: (
      <ul className="cert-chips">
        {required.map((i) => (
          <li
            key={i.credential_type_id}
            className={`cert-chip ${i.state === 'ok' ? 'verified' : i.state === 'pending' ? 'unverified' : 'missing'}`}
          >
            {i.state === 'ok' ? (
              <BadgeCheck size={14} aria-hidden="true" />
            ) : i.state === 'pending' ? (
              <Clock3 size={14} aria-hidden="true" />
            ) : (
              <CircleX size={14} aria-hidden="true" />
            )}
            {i.name.split(' (')[0]}
          </li>
        ))}
      </ul>
    ),
  });
  const bonus = card.match.items.filter((i) => !i.required);
  if (bonus.length) {
    const held = bonus.filter((i) => i.state !== 'missing').map((i) => i.name.split(' (')[0]);
    rows.push({
      icon: Award,
      text: held.length
        ? `You also hold ${held.join(' and ')}, which this employer values.`
        : `This employer also values ${bonus.map((i) => i.name.split(' (')[0]).join(' and ')}.`,
      strength: held.length / bonus.length,
    });
  }
  if (profile?.rate_min_cents != null && card.pay_unit !== 'fixed') {
    const hourly =
      card.pay_unit === 'day' ? Math.round(card.pay_rate_cents / 8) : card.pay_rate_cents;
    const min = profile.rate_min_cents;
    rows.push({
      icon: Wallet,
      text:
        hourly >= min
          ? `Pays ${dollars(hourly)}/h, ${hourly > min ? 'above' : 'at'} your ${dollars(min)}/h minimum.`
          : `Pays ${dollars(hourly)}/h, below your ${dollars(min)}/h minimum.`,
      strength: Math.min(1, hourly / Math.max(min * 1.25, 1)),
    });
  }
  const booked = card.reasons.find((r) => r.startsWith('You’re booked'));
  rows.push({
    icon: CalendarCheck,
    text: booked || 'Fits your calendar with no conflicts.',
    strength: booked ? 0 : 1,
  });
  const hours = (Date.now() - Date.parse(card.created_at)) / 3600000;
  rows.push({
    icon: History,
    text:
      hours < 24
        ? 'Posted today'
        : hours < 48
          ? 'Posted yesterday'
          : `Posted ${Math.floor(hours / 24)} days ago`,
    strength: Math.max(0.1, 1 - hours / 168),
  });
  return (
    <div className="sheet-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside
        className="sheet why-sheet"
        role="dialog"
        aria-modal="true"
        aria-label="Why you’re seeing this"
      >
        <header className="sheet-head">
          <div>
            <p className="apply-kicker">Why you’re seeing this</p>
            <h2>{card.title}</h2>
            <p>{card.org.name}</p>
          </div>
          <button className="text-button" onClick={onClose}>
            Close
          </button>
        </header>
        <ul className="why-rows">
          {rows.map((r) => (
            <li key={r.text}>
              <r.icon size={22} aria-hidden="true" />
              <div>
                <p>{r.text}</p>
                {r.chips}
              </div>
              <span className="strength" aria-hidden="true">
                <i style={{ width: `${Math.round(r.strength * 100)}%` }} />
              </span>
            </li>
          ))}
        </ul>
        {card.score != null && (
          <p className="wallet-meta">
            Ranking score {card.score} of 100, from the weights in Shift’s ranking settings.
          </p>
        )}
        {onApply && card.eligible && (
          <footer className="apply-nav">
            <button className="button button-primary" onClick={onApply}>
              Apply
            </button>
          </footer>
        )}
      </aside>
    </div>
  );
}
