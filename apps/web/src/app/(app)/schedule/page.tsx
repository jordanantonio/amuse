'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { CalendarCheck, ChevronLeft, ChevronRight, Plus, Workflow } from 'lucide-react';
import { market } from '@/lib/market';
import type { ScheduleItem, ScheduleView } from '@/lib/market-types';
import { day, range, todayIso } from '@/lib/format';
import { useSession } from '@/components/v1/session';
import { EmptyState, ErrorNote, Modal, Skeleton } from '@/components/v1/ui';

const DAY = 86400000;
const toUtc = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
const iso = (ms: number) => new Date(ms).toISOString().slice(0, 10);
const addDays = (s: string, n: number) => iso(toUtc(s) + n * DAY);
const weekday = (s: string) => (new Date(toUtc(s)).getUTCDay() + 6) % 7; // Mon = 0
const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function SchedulePage() {
  const { me } = useSession();
  const router = useRouter();
  const [mode, setMode] = useState<'month' | 'week'>('month');
  const [anchor, setAnchor] = useState(todayIso());
  const [data, setData] = useState<ScheduleView | null>(null);
  const [error, setError] = useState('');
  const [adding, setAdding] = useState(false);
  const [selected, setSelected] = useState<ScheduleItem | null>(null);
  const today = todayIso();

  const { start, end, days, label } = useMemo(() => {
    if (mode === 'week') {
      const s = addDays(anchor, -weekday(anchor));
      const e = addDays(s, 6);
      return {
        start: s,
        end: e,
        days: Array.from({ length: 7 }, (_, i) => addDays(s, i)),
        label: range(s, e),
      };
    }
    const first = anchor.slice(0, 8) + '01';
    const s = addDays(first, -weekday(first));
    const next = new Date(toUtc(first));
    next.setUTCMonth(next.getUTCMonth() + 1);
    const last = iso(next.getTime() - DAY);
    const e = addDays(last, 6 - weekday(last));
    const count = (toUtc(e) - toUtc(s)) / DAY + 1;
    return {
      start: s,
      end: e,
      days: Array.from({ length: count }, (_, i) => addDays(s, i)),
      label: `${MONTHS[+first.slice(5, 7) - 1]} ${first.slice(0, 4)}`,
    };
  }, [mode, anchor]);

  const load = useCallback(async () => {
    try {
      setData(await market<ScheduleView>(`/schedule?start=${start}&end=${end}`));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, [start, end]);
  useEffect(() => {
    void load();
  }, [load]);

  const move = (dir: number) => {
    if (mode === 'week') setAnchor(addDays(anchor, dir * 7));
    else {
      const d = new Date(toUtc(anchor.slice(0, 8) + '01'));
      d.setUTCMonth(d.getUTCMonth() + dir);
      setAnchor(iso(d.getTime()));
    }
  };
  const itemsOn = (d: string) =>
    (data?.items || []).filter((i) => i.start_date <= d && i.end_date >= d);
  const upcoming = [...(data?.items || [])]
    .filter((i) => i.end_date >= today)
    .sort((a, b) => a.start_date.localeCompare(b.start_date));
  const open = (i: ScheduleItem) =>
    i.kind === 'engagement' && i.posting_id
      ? router.push(`/postings/${i.posting_id}`)
      : setSelected(i);
  const worker = me.mode === 'worker';

  return (
    <>
      <div className="page-head-row">
        <h1 className="page-title">Schedule</h1>
        <div className="actions">
          {me.mode === 'business' && me.planner_persona && (
            <Link
              className="text-button"
              href="/planner"
              onClick={() => {
                try {
                  localStorage.setItem('shift-persona', me.planner_persona!);
                } catch {}
              }}
            >
              <Workflow size={18} aria-hidden="true" /> Crew planner
            </Link>
          )}
          {worker && (
            <button className="button button-primary" onClick={() => setAdding(true)}>
              <Plus size={18} aria-hidden="true" />
              Mark unavailable
            </button>
          )}
        </div>
      </div>

      {worker && data && (
        <p className="calendar-status">
          {data.calendar_connected ? (
            <span className="status-chip ok">
              <CalendarCheck size={16} aria-hidden="true" />
              Google Calendar connected
            </span>
          ) : data.calendar_enabled ? (
            <a className="text-button" href="/api/v1/auth/google/calendar/start?next=/schedule">
              Connect Google Calendar
            </a>
          ) : (
            <span className="wallet-meta">
              Google Calendar sync isn’t set up on this server. Each contract has a Download .ics
              button instead.
            </span>
          )}
        </p>
      )}

      <div className="schedule-toolbar">
        <div className="segmented-v1" role="group" aria-label="View">
          {(['month', 'week'] as const).map((m) => (
            <button key={m} aria-pressed={mode === m} onClick={() => setMode(m)}>
              {m === 'month' ? 'Month' : 'Week'}
            </button>
          ))}
        </div>
        <div className="schedule-nav">
          <button
            className="icon-button tap"
            aria-label={`Previous ${mode}`}
            onClick={() => move(-1)}
          >
            <ChevronLeft size={20} />
          </button>
          <h2 aria-live="polite">{label}</h2>
          <button className="icon-button tap" aria-label={`Next ${mode}`} onClick={() => move(1)}>
            <ChevronRight size={20} />
          </button>
          <button className="text-button" onClick={() => setAnchor(today)}>
            Today
          </button>
        </div>
        <ul className="schedule-legend" aria-label="Legend">
          <li>
            <i className="swatch booked" aria-hidden="true" /> Booked contract
          </li>
          {worker && (
            <li>
              <i className="swatch unavailable" aria-hidden="true" /> Unavailable
            </li>
          )}
        </ul>
      </div>

      {error && <ErrorNote message={error} retry={() => void load()} />}
      {!data && !error && <Skeleton lines={2} />}
      {data && (
        <div className={`cal-grid ${mode}`} role="grid" aria-label={label}>
          <div className="cal-row cal-head" role="row">
            {WEEKDAYS.map((w) => (
              <span key={w} role="columnheader">
                {w}
              </span>
            ))}
          </div>
          {Array.from({ length: days.length / 7 }, (_, r) => (
            <div className="cal-row" role="row" key={r}>
              {days.slice(r * 7, r * 7 + 7).map((d) => {
                const items = itemsOn(d);
                const outside = mode === 'month' && d.slice(0, 7) !== anchor.slice(0, 7);
                const shown = mode === 'month' ? items.slice(0, 2) : items;
                return (
                  <div
                    key={d}
                    role="gridcell"
                    aria-label={`${day(d, true)}${items.length ? `, ${items.length} booked` : ''}`}
                    className={`cal-cell ${outside ? 'outside' : ''} ${d === today ? 'today' : ''}`}
                  >
                    <span className="cal-date">{+d.slice(8, 10)}</span>
                    {shown.map((i) => (
                      <button
                        key={i.id + d}
                        className={`cal-item ${i.kind}`}
                        onClick={() => open(i)}
                        title={`${i.title}${i.subtitle ? ` · ${i.subtitle}` : ''}`}
                      >
                        {i.title}
                      </button>
                    ))}
                    {items.length > shown.length && (
                      <span className="cal-more">+{items.length - shown.length} more</span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}

      <section className="v1-section" aria-labelledby="upcoming-title">
        <h2 id="upcoming-title">Coming up</h2>
        {data && !upcoming.length && (
          <EmptyState
            title="Nothing booked in this period"
            action={
              worker ? (
                <Link className="button button-outline" href="/home">
                  Find contracts
                </Link>
              ) : (
                <Link className="button button-outline" href="/work">
                  Go to Work
                </Link>
              )
            }
          >
            {worker
              ? 'Contracts you accept block their dates here.'
              : 'Accepted offers and crew start dates show up here.'}
          </EmptyState>
        )}
        <ul className="agenda">
          {upcoming.map((i) => (
            <li key={i.id}>
              <button className={`agenda-item ${i.kind}`} onClick={() => open(i)}>
                <i
                  className={`swatch ${i.kind === 'manual' ? 'unavailable' : 'booked'}`}
                  aria-hidden="true"
                />
                <span>
                  <strong>{i.title}</strong>
                  {range(i.start_date, i.end_date)}
                  {i.subtitle ? ` · ${i.subtitle}` : ''}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {adding && (
        <BlockDialog
          onClose={() => setAdding(false)}
          onSaved={async () => {
            setAdding(false);
            await load();
          }}
        />
      )}
      {selected && (
        <Modal
          title={selected.title}
          description={range(selected.start_date, selected.end_date)}
          onClose={() => setSelected(null)}
        >
          <div className="editor-actions">
            <button className="button button-outline" onClick={() => setSelected(null)}>
              Keep
            </button>
            <button
              className="button button-danger"
              onClick={async () => {
                await market(`/availability/${selected.id}`, { method: 'DELETE' });
                setSelected(null);
                await load();
              }}
            >
              Remove unavailable days
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}

function BlockDialog({ onClose, onSaved }: { onClose: () => void; onSaved: () => Promise<void> }) {
  const [start, setStart] = useState(todayIso());
  const [end, setEnd] = useState(todayIso());
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  return (
    <Modal
      title="Mark yourself unavailable"
      description="Only you see the reason. Businesses just see that you’re booked."
      onClose={onClose}
      busy={busy}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError('');
          try {
            await market('/availability', {
              method: 'POST',
              body: { start_date: start, end_date: end, note },
            });
            await onSaved();
          } catch (err) {
            setError((err as Error).message);
            setBusy(false);
          }
        }}
      >
        <div className="editor-fields">
          <div className="field-row">
            <label>
              From
              <input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                required
              />
            </label>
            <label>
              To
              <input
                type="date"
                value={end}
                min={start}
                onChange={(e) => setEnd(e.target.value)}
                required
              />
            </label>
          </div>
          <label>
            Reason <small>(optional, private)</small>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={200}
              placeholder="Family trip"
            />
          </label>
        </div>
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        <div className="editor-actions">
          <button type="button" className="button button-outline" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <button className="button button-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
