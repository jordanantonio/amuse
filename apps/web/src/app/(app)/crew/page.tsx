'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  ChevronLeft,
  ChevronRight,
  Settings2,
  Sparkles,
  Search,
  Check,
  Repeat,
} from 'lucide-react';
import { market } from '@/lib/market';
import type { AutofillResult, CrewRules, CrewSlot, CrewWeek, Spot } from '@/lib/crew-types';
import { shiftTime } from '@/lib/crew-types';
import { range, todayIso } from '@/lib/format';
import { useSession } from '@/components/v1/session';
import { PersonAvatar } from '@/components/v1/avatar';
import { CandidatePanel } from '@/components/v1/crew';
import { EmptyState, ErrorNote, Skeleton } from '@/components/v1/ui';

const DAY = 86400000;
const addDays = (iso: string, n: number) =>
  new Date(Date.parse(iso + 'T00:00:00Z') + n * DAY).toISOString().slice(0, 10);
const monday = (iso: string) => {
  const wd = (new Date(iso + 'T00:00:00Z').getUTCDay() + 6) % 7;
  return addDays(iso, -wd);
};
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function CrewPlannerPage() {
  const { me } = useSession();
  if (me.mode !== 'business')
    return (
      <EmptyState title="The crew planner is for hiring businesses">
        Workers see their bookings on Schedule.
      </EmptyState>
    );
  return <CrewPlanner />;
}

function CrewPlanner() {
  const [start, setStart] = useState(monday(todayIso()));
  const [week, setWeek] = useState<CrewWeek | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [unfilled, setUnfilled] = useState<string[]>([]);
  const [lastRun, setLastRun] = useState<AutofillResult | null>(null);
  const [panel, setPanel] = useState<{ slot: CrewSlot; scope: 'crew' | 'market' } | null>(null);
  const [snapped, setSnapped] = useState<string | null>(null);
  const [rulesOpen, setRulesOpen] = useState(false);
  const load = useCallback(async () => {
    try {
      setWeek(await market<CrewWeek>(`/crew/week?start=${start}`));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, [start]);
  useEffect(() => {
    setUnfilled([]);
    setLastRun(null);
    void load();
  }, [load]);

  const autofill = async () => {
    setBusy(true);
    setError('');
    try {
      const r = await market<AutofillResult>(`/crew/autofill?start=${start}`, { method: 'POST' });
      setLastRun(r);
      setUnfilled(r.unfilled_slot_ids);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const acceptAll = async (ids: string[] = []) => {
    setBusy(true);
    try {
      setWeek(
        await market<CrewWeek>('/crew/proposals/accept', {
          method: 'POST',
          body: { start, assignment_ids: ids },
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const clearAll = async () => {
    setBusy(true);
    try {
      setWeek(await market<CrewWeek>(`/crew/proposals/clear?start=${start}`, { method: 'POST' }));
      setLastRun(null);
      setUnfilled([]);
    } finally {
      setBusy(false);
    }
  };
  const swap = async (slot: CrewSlot, spot: Spot) => {
    await market(`/crew/assignments/${spot.assignment_id}`, { method: 'DELETE' });
    await load();
    setPanel({
      slot: { ...slot, spots: slot.spots.filter((s) => s.assignment_id !== spot.assignment_id) },
      scope: 'crew',
    });
  };

  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i));
  const today = todayIso();
  return (
    <>
      <div className="page-head-row">
        <div>
          <h1 className="page-title">Crew planner</h1>
          <p className="crew-sub">
            {week ? `${week.crew_size} people on your crew` : ''} ·{' '}
            <Link className="inline-link" href="/planner">
              Weather and absence recovery
            </Link>
          </p>
        </div>
        <div className="actions">
          <RulesButton
            open={rulesOpen}
            setOpen={setRulesOpen}
            rules={week?.rules}
            onSaved={(r) => week && setWeek({ ...week, rules: r })}
          />
          <button
            className="button button-primary"
            disabled={busy || !week}
            onClick={() => void autofill()}
          >
            <Sparkles size={18} aria-hidden="true" />
            {busy ? 'Solving…' : 'Auto-fill week'}
          </button>
        </div>
      </div>

      <div className="schedule-toolbar">
        <div className="schedule-nav">
          <button
            className="icon-button tap"
            aria-label="Previous week"
            onClick={() => setStart(addDays(start, -7))}
          >
            <ChevronLeft size={20} />
          </button>
          <h2 aria-live="polite">{range(start, addDays(start, 6))}</h2>
          <button
            className="icon-button tap"
            aria-label="Next week"
            onClick={() => setStart(addDays(start, 7))}
          >
            <ChevronRight size={20} />
          </button>
          <button className="text-button" onClick={() => setStart(monday(todayIso()))}>
            This week
          </button>
        </div>
        <ul className="schedule-legend" aria-label="Legend">
          <li>
            <span className="legend-dot filled" aria-hidden="true" /> Assigned
          </li>
          <li>
            <span className="legend-dot ghost" aria-hidden="true" /> Proposed
          </li>
          <li>
            <span className="legend-dot open" aria-hidden="true" /> Open spot
          </li>
        </ul>
      </div>

      {(week?.proposed || 0) > 0 && (
        <div className="proposal-bar light-card" role="status">
          <Sparkles size={20} aria-hidden="true" />
          <span>
            <strong>
              Auto-fill proposed {week!.proposed}{' '}
              {week!.proposed === 1 ? 'assignment' : 'assignments'}
            </strong>
            {lastRun ? ` with CP-SAT (${lastRun.solver_status.toLowerCase()})` : ''}
            {unfilled.length
              ? `. ${unfilled.length} ${unfilled.length === 1 ? 'shift still needs' : 'shifts still need'} people.`
              : '.'}
          </span>
          <div className="actions">
            <button
              className="button button-primary button-sm"
              disabled={busy}
              onClick={() => void acceptAll()}
            >
              <Check size={16} aria-hidden="true" /> Accept all
            </button>
            <button className="text-button" disabled={busy} onClick={() => void clearAll()}>
              Clear proposals
            </button>
          </div>
        </div>
      )}
      {lastRun && !week?.proposed && (
        <p className="crew-note" role="status">
          Auto-fill found no new assignments ({lastRun.solver_status.toLowerCase()}).
          {unfilled.length ? ' Use Find a replacement on the open shifts.' : ''}
        </p>
      )}

      {error && <ErrorNote message={error} retry={() => void load()} />}
      {!week && !error && <Skeleton lines={3} />}
      {week && (
        <div className="crew-board" role="list" aria-label="Shifts this week">
          {days.map((d, i) => {
            const slots = week.slots.filter((s) => s.day === d);
            return (
              <section
                key={d}
                className={`crew-day ${d === today ? 'today' : ''}`}
                role="listitem"
                aria-label={`${WEEKDAYS[i]} ${d}`}
              >
                <h3>
                  {WEEKDAYS[i]} <span>{+d.slice(8, 10)}</span>
                </h3>
                {!slots.length && <p className="crew-empty">No shifts</p>}
                {slots.map((s) => (
                  <SlotCard
                    key={s.id}
                    slot={s}
                    unfilled={unfilled.includes(s.id)}
                    snapped={snapped}
                    onOpen={(scope) => setPanel({ slot: s, scope })}
                    onAcceptGhost={(spot) => void acceptAll([spot.assignment_id])}
                    onSwap={(spot) => void swap(s, spot)}
                  />
                ))}
              </section>
            );
          })}
        </div>
      )}
      {panel && (
        <CandidatePanel
          slot={panel.slot}
          initialScope={panel.scope}
          onClose={() => setPanel(null)}
          onAssigned={(updated, userId) => {
            setPanel(null);
            setUnfilled((u) =>
              updated.spots.length >= updated.needed ? u.filter((x) => x !== updated.id) : u,
            );
            setWeek((w) =>
              w ? { ...w, slots: w.slots.map((x) => (x.id === updated.id ? updated : x)) } : w,
            );
            setSnapped(`${updated.id}:${userId}`);
          }}
        />
      )}
    </>
  );
}

function SlotCard({
  slot,
  unfilled,
  snapped,
  onOpen,
  onAcceptGhost,
  onSwap,
}: {
  slot: CrewSlot;
  unfilled: boolean;
  snapped: string | null;
  onOpen: (scope: 'crew' | 'market') => void;
  onAcceptGhost: (spot: Spot) => void;
  onSwap: (spot: Spot) => void;
}) {
  const [menu, setMenu] = useState<string | null>(null);
  const open = Math.max(0, slot.needed - slot.spots.length);
  return (
    <article className={`slot-card light-card ${unfilled && open ? 'needs-people' : ''}`}>
      <button
        className="slot-main"
        onClick={() => onOpen('crew')}
        aria-label={`${slot.label}, ${shiftTime(slot)}, needs ${slot.needed}. Open candidates`}
      >
        <strong>{slot.label}</strong>
        <span className="slot-time">{shiftTime(slot)}</span>
        <span className="slot-needs">
          Needs {slot.needed}
          {slot.preferred_cert ? ` · ${slot.preferred_cert.name.split(' (')[0]} preferred` : ''}
          {slot.required_certs.length
            ? ` · ${slot.required_certs.map((c) => c.name.split(' (')[0]).join(', ')} required`
            : ''}
        </span>
      </button>
      <div className="slot-spots">
        {slot.spots.map((p, i) => (
          <div key={p.assignment_id} className="spot-wrap">
            <button
              className={`spot ${p.status} ${snapped === `${slot.id}:${p.user_id}` ? 'snap-in' : ''}`}
              style={{ animationDelay: p.status === 'proposed' ? `${i * 120}ms` : undefined }}
              aria-label={`${p.name}${p.status === 'proposed' ? ', proposed by Auto-fill' : ''}`}
              onClick={() => setMenu(menu === p.assignment_id ? null : p.assignment_id)}
              title={p.name}
            >
              <PersonAvatar id={p.user_id} name={p.name} size={36} />
            </button>
            {menu === p.assignment_id && p.status === 'proposed' && (
              <div className="spot-menu light-card">
                <p>{p.name}</p>
                <button className="text-button" onClick={() => onAcceptGhost(p)}>
                  <Check size={14} aria-hidden="true" /> Accept
                </button>
                <button className="text-button" onClick={() => onSwap(p)}>
                  <Repeat size={14} aria-hidden="true" /> Swap
                </button>
              </div>
            )}
            {menu === p.assignment_id && p.status === 'assigned' && (
              <div className="spot-menu light-card">
                <p>{p.name}</p>
                <button className="text-button" onClick={() => onSwap(p)}>
                  <Repeat size={14} aria-hidden="true" /> Swap
                </button>
              </div>
            )}
          </div>
        ))}
        {Array.from({ length: open }, (_, i) => (
          <button
            key={`open${i}`}
            className="spot open"
            aria-label={`Open spot in ${slot.label}. Choose someone`}
            onClick={() => onOpen('crew')}
          />
        ))}
      </div>
      {unfilled && open > 0 && (
        <button
          className="button button-outline button-sm find-replacement"
          onClick={() => onOpen('market')}
        >
          <Search size={15} aria-hidden="true" /> Find a replacement
        </button>
      )}
    </article>
  );
}

function RulesButton({
  open,
  setOpen,
  rules,
  onSaved,
}: {
  open: boolean;
  setOpen: (o: boolean) => void;
  rules?: CrewRules;
  onSaved: (r: CrewRules) => void;
}) {
  const [form, setForm] = useState<CrewRules | null>(rules || null);
  const [error, setError] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => setForm(rules || null), [rules, open]);
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
      <button className="button button-outline" aria-expanded={open} onClick={() => setOpen(!open)}>
        <Settings2 size={18} aria-hidden="true" /> Rules
      </button>
      {open && form && (
        <form
          className="popover-panel rules-panel"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              onSaved(await market<CrewRules>('/crew/rules', { method: 'PUT', body: form }));
              setOpen(false);
            } catch (err) {
              setError((err as Error).message);
            }
          }}
        >
          <p className="popover-title">
            Fatigue advice
            <small>Warnings never block an assignment. Auto-fill follows them.</small>
          </p>
          {(
            [
              ['max_consecutive_days', 'Max days in a row', 1, 14],
              ['min_rest_hours', 'Min rest between shifts (h)', 0, 24],
              ['max_weekly_hours', 'Max hours per week', 1, 84],
            ] as const
          ).map(([key, label, min, max]) => (
            <label key={key}>
              {label}
              <input
                type="number"
                min={min}
                max={max}
                value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: Number(e.target.value) })}
              />
            </label>
          ))}
          {error && <p className="v1-inline-error">{error}</p>}
          <button className="button button-primary">Save rules</button>
        </form>
      )}
    </div>
  );
}
