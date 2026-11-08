'use client';
import { useEffect, useState } from 'react';
import {
  BadgeCheck,
  CircleX,
  Clock3,
  MapPin,
  Search,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  CalendarCheck,
  type LucideIcon,
  Award,
} from 'lucide-react';
import { market } from '@/lib/market';
import type { BreakdownRow, Candidate, CrewSlot } from '@/lib/crew-types';
import { clock, shiftTime } from '@/lib/crew-types';
import { day } from '@/lib/format';
import { PersonAvatar } from './avatar';
import { ErrorNote, Skeleton } from './ui';

/** CREW-2: thin 24 h strip: free window (light), bookings (solid), this slot (outlined). */
export function AvailabilityBar({ bar, label }: { bar: Candidate['bar']; label: string }) {
  const pct = (m: number) => `${(m / 1440) * 100}%`;
  return (
    <div className="avail-bar" role="img" aria-label={label}>
      {bar.free.map(([s, e], i) => (
        <span key={`f${i}`} className="avail-free" style={{ left: pct(s), width: pct(e - s) }} />
      ))}
      {bar.booked.map(([s, e], i) => (
        <span key={`b${i}`} className="avail-booked" style={{ left: pct(s), width: pct(e - s) }} />
      ))}
      <span
        className="avail-slot"
        style={{ left: pct(bar.slot[0]), width: pct(bar.slot[1] - bar.slot[0]) }}
      />
      <span className="avail-ticks" aria-hidden="true">
        <i style={{ left: '25%' }} />
        <i style={{ left: '50%' }} />
        <i style={{ left: '75%' }} />
      </span>
    </div>
  );
}

const ROW_ICON: Record<string, LucideIcon> = {
  certs: ShieldCheck,
  bonus: Award,
  schedule: CalendarCheck,
  distance: MapPin,
  fatigue: TriangleAlert,
};

/** Breakdown rows in the same style as "Why am I seeing this?" (WHY-1, RANK-2). */
export function FitBreakdown({ rows }: { rows: BreakdownRow[] }) {
  return (
    <ul className="fit-rows">
      {rows.map((r) => {
        const Icon = ROW_ICON[r.kind] || Sparkles;
        return (
          <li key={r.kind + r.label} className={r.points < 0 ? 'negative' : ''}>
            <Icon size={18} aria-hidden="true" />
            <span>{r.label}</span>
            <span className="strength" aria-hidden="true">
              <i style={{ width: `${Math.round(r.strength * 100)}%` }} />
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export function ScoreBar({ score }: { score: number }) {
  return (
    <span className="score-bar" title={`Fit score ${score} of 100`}>
      <span className="score-track">
        <i style={{ width: `${score}%` }} />
      </span>
      <strong>{score}</strong>
    </span>
  );
}

/** CREW-2 candidate panel (side sheet; bottom sheet on phones). */
export function CandidatePanel({
  slot,
  initialScope,
  onClose,
  onAssigned,
}: {
  slot: CrewSlot;
  initialScope: 'crew' | 'market';
  onClose: () => void;
  onAssigned: (slot: CrewSlot, userId: string) => void;
}) {
  const [scope, setScope] = useState(initialScope);
  const [rows, setRows] = useState<Candidate[] | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => {
    setRows(null);
    market<Candidate[]>(`/crew/slots/${slot.id}/candidates?scope=${scope}`).then(setRows, (e) =>
      setError((e as Error).message),
    );
  }, [slot.id, scope]);
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', esc);
    return () => document.removeEventListener('keydown', esc);
  }, [onClose]);
  const assign = async (c: Candidate) => {
    setBusy(c.user_id);
    setError('');
    try {
      const updated = await market<CrewSlot>(`/crew/slots/${slot.id}/assign`, {
        method: 'POST',
        body: { user_id: c.user_id },
      });
      onAssigned(updated, c.user_id);
    } catch (e) {
      setError((e as Error).message);
      setBusy('');
    }
  };
  const open_spots = slot.needed - slot.spots.filter((s) => s.status === 'assigned').length;
  return (
    <div className="sheet-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside
        className="sheet light-card"
        role="dialog"
        aria-modal="true"
        aria-label={`Candidates for ${slot.label}`}
      >
        <header className="sheet-head">
          <div>
            <h2>{slot.label}</h2>
            <p>
              {day(slot.day)} · {shiftTime(slot)} ·{' '}
              {open_spots > 0 ? `${open_spots} open` : 'Fully staffed'}
            </p>
          </div>
          <button className="text-button" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="segmented-v1 sheet-scope" role="group" aria-label="Who to show">
          <button aria-pressed={scope === 'crew'} onClick={() => setScope('crew')}>
            Your crew
          </button>
          <button aria-pressed={scope === 'market'} onClick={() => setScope('market')}>
            <Search size={16} aria-hidden="true" /> Marketplace
          </button>
        </div>
        <p className="sheet-legend">
          <span>
            <i className="legend-free" /> Free
          </span>
          <span>
            <i className="legend-booked" /> Booked
          </span>
          <span>
            <i className="legend-slot" /> This shift
          </span>
          <span className="legend-hours">12 AM · 6 AM · 12 PM · 6 PM</span>
        </p>
        {error && <ErrorNote message={error} />}
        {!rows && !error && <Skeleton lines={3} />}
        {rows && !rows.length && <p className="v1-lede">Nobody to show here yet.</p>}
        <ul className="candidate-list">
          {rows?.map((c) => (
            <li key={c.user_id} className={`candidate ${c.blockers.length ? 'blocked' : ''}`}>
              <div className="candidate-top">
                <PersonAvatar id={c.user_id} name={c.name} size={44} />
                <div className="candidate-who">
                  <strong>{c.name}</strong>
                  <span>{c.on_crew ? 'On your crew' : c.headline}</span>
                </div>
                <button
                  className="score-button"
                  aria-expanded={open === c.user_id}
                  onClick={() => setOpen(open === c.user_id ? null : c.user_id)}
                  aria-label={`Fit score ${c.score}. Show breakdown`}
                >
                  <ScoreBar score={c.score} />
                </button>
              </div>
              <ul className="cert-chips">
                {c.certs.map((cert) => (
                  <li key={cert.id + cert.kind} className={`cert-chip ${cert.state}`}>
                    {cert.state === 'verified' ? (
                      <BadgeCheck size={14} aria-hidden="true" />
                    ) : cert.state === 'missing' ? (
                      <CircleX size={14} aria-hidden="true" />
                    ) : (
                      <Clock3 size={14} aria-hidden="true" />
                    )}
                    {cert.name.split(' (')[0]}
                    {cert.kind === 'preferred' ? ' · preferred' : ''}
                  </li>
                ))}
              </ul>
              <AvailabilityBar
                bar={c.bar}
                label={`Free ${c.bar.free.map(([s, e]) => `${clock(s)} to ${clock(e)}`).join(', ') || 'never'}; this shift ${clock(c.bar.slot[0])} to ${clock(c.bar.slot[1])}`}
              />
              {open === c.user_id && <FitBreakdown rows={c.breakdown} />}
              {c.warnings.length > 0 && (
                <ul className="warn-chips" aria-label="Fatigue advice">
                  {c.warnings.map((w) => (
                    <li key={w}>
                      <TriangleAlert size={14} aria-hidden="true" />
                      {w}
                    </li>
                  ))}
                </ul>
              )}
              <div className="candidate-actions">
                {c.blockers.length ? (
                  <span className="blocker">{c.blockers[0]}</span>
                ) : (
                  <button
                    className="button button-primary button-sm"
                    disabled={!!busy || open_spots <= 0}
                    onClick={() => void assign(c)}
                  >
                    {busy === c.user_id ? 'Assigning…' : 'Assign'}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
