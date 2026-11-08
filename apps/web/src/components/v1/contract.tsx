'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  BadgeCheck,
  CalendarRange,
  CircleCheck,
  CircleX,
  Clock3,
  MapPin,
  TriangleAlert,
  Users,
} from 'lucide-react';
import type { MatchItem, PostingCard } from '@/lib/market-types';
import { dollars, duration, payUnit, range } from '@/lib/format';

export const PATTERNS: Record<string, string> = {
  mon_fri: 'Mon–Fri, days',
  nights: 'Mon–Fri, nights',
  four_on_four_off: '4 on, 4 off',
  weekends: 'Weekends only',
};

export function MatchLine({ card }: { card: PostingCard }) {
  const { required_total, required_held } = card.match;
  if (!card.eligible) {
    return (
      <p className="match-line bad">
        <CircleX size={18} aria-hidden="true" />
        {card.reasons[0]}
      </p>
    );
  }
  const pending = card.match.items.some((i) => i.required && i.state === 'pending');
  return (
    <p className={`match-line ${pending ? 'warn' : 'ok'}`}>
      {pending ? (
        <Clock3 size={18} aria-hidden="true" />
      ) : (
        <CircleCheck size={18} aria-hidden="true" />
      )}
      {required_total
        ? `You have ${required_held} of ${required_total} required tickets${pending ? ', some pending review' : ''}`
        : 'No tickets required'}
    </p>
  );
}

export function ContractFacts({ card }: { card: PostingCard }) {
  return (
    <ul className="contract-facts">
      <li>
        <MapPin size={16} aria-hidden="true" />
        {card.city}
        {card.distance_km == null
          ? ''
          : card.distance_km < 2
            ? ', in your city'
            : `, ${card.distance_km} km away`}
      </li>
      <li>
        <CalendarRange size={16} aria-hidden="true" />
        {range(card.start_date, card.end_date)}, {duration(card.start_date, card.end_date)}
      </li>
      <li>
        <Clock3 size={16} aria-hidden="true" />
        {PATTERNS[card.schedule_pattern] || card.schedule_pattern}
        {card.is_exclusive ? ', full-time' : ', part-time'}
      </li>
      {card.posting_type === 'agency' && (
        <li>
          <Users size={16} aria-hidden="true" />
          Crew of {card.headcount}
        </li>
      )}
    </ul>
  );
}

export function Pay({ card }: { card: PostingCard }) {
  return (
    <p className="contract-pay">
      {dollars(card.pay_rate_cents)} <small>{payUnit[card.pay_unit]}</small>
    </p>
  );
}

export function OrgLine({ card }: { card: PostingCard }) {
  return (
    <p>
      {card.org.name}
      {card.org.verified && (
        <span className="verified-mark">
          <BadgeCheck size={16} aria-hidden="true" />
          Verified
        </span>
      )}
    </p>
  );
}

export function ContractCard({
  card,
  action,
  footer,
}: {
  card: PostingCard;
  action?: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <article className={`contract-card ${card.eligible ? '' : 'ineligible'}`}>
      <div className="contract-card-head">
        <h3>
          <Link href={`/postings/${card.id}`}>{card.title}</Link>
        </h3>
        <OrgLine card={card} />
      </div>
      <ContractFacts card={card} />
      <div className="contract-card-row">
        <Pay card={card} />
        {card.is_new && <span className="new-chip">New</span>}
      </div>
      <MatchLine card={card} />
      <div className="contract-card-actions">
        {action}
        {card.score_breakdown && card.score_breakdown.length > 0 && <WhyPopover card={card} />}
      </div>
      {footer}
    </article>
  );
}

/** "Why am I seeing this?" — the exact points from the ranking config (FEED-2). */
export function WhyPopover({ card }: { card: PostingCard }) {
  const [open, setOpen] = useState(false);
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
  }, [open]);
  return (
    <div className="popover why" ref={ref}>
      <button className="text-button" aria-expanded={open} onClick={() => setOpen(!open)}>
        Why am I seeing this?
      </button>
      {open && (
        <div className="popover-panel why-panel" role="dialog" aria-label="Why you’re seeing this">
          <p className="popover-title">You qualify for every required ticket. Then:</p>
          <ul>
            {card.score_breakdown!.map((b) => (
              <li key={b.label}>
                <span>{b.label}</span>
                <strong>+{b.points}</strong>
              </li>
            ))}
          </ul>
          <p className="why-total">
            Ranking score <strong>{card.score}</strong>
          </p>
        </div>
      )}
    </div>
  );
}

const STATE_ICON = { ok: CircleCheck, pending: Clock3, missing: CircleX };
const STATE_WORD = { ok: 'Verified', pending: 'Pending verification', missing: 'Missing' };

/** POST-2: each required credential with a green check, amber pending or red missing. */
export function EligibilityBox({ items, reasons }: { items: MatchItem[]; reasons: string[] }) {
  const required = items.filter((i) => i.required);
  const nice = items.filter((i) => !i.required);
  const booked = reasons.filter((r) => r.startsWith('You’re booked'));
  return (
    <section className="eligibility" aria-labelledby="eligibility-title">
      <h2 id="eligibility-title">Your tickets for this contract</h2>
      {!required.length && <p className="v1-lede">This contract doesn’t require any tickets.</p>}
      <ul>
        {required.map((i) => (
          <EligibilityRow key={i.credential_type_id} item={i} />
        ))}
      </ul>
      {nice.length > 0 && (
        <>
          <h3>Nice to have</h3>
          <ul>
            {nice.map((i) => (
              <EligibilityRow key={i.credential_type_id} item={i} />
            ))}
          </ul>
        </>
      )}
      {booked.map((r) => (
        <p key={r} className="match-line bad">
          <TriangleAlert size={18} aria-hidden="true" />
          {r}
        </p>
      ))}
    </section>
  );
}

function EligibilityRow({ item }: { item: MatchItem }) {
  const Icon = STATE_ICON[item.state];
  return (
    <li className={`elig-row ${item.state}`}>
      <Icon size={20} aria-hidden="true" />
      <span>
        {item.name}
        {item.must_be_verified && <small>Must be verified</small>}
      </span>
      <strong>{STATE_WORD[item.state]}</strong>
    </li>
  );
}
