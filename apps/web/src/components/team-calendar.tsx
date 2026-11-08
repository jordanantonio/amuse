'use client';
import { useState } from 'react';
import { ChevronLeft, ChevronRight, CalendarDays, ShieldCheck } from 'lucide-react';
import type { Dashboard, Assignment } from '@/lib/types';
import type { Recovery, Slot } from '@/lib/adaptive-types';
import { clock, shortDate } from '@/lib/display';
import { addDays, dateKey, intersect, freeWindows } from '@/lib/calendar-time';
import { Avatar } from './ui/avatar';
import { Button } from './ui/button';
export function Calendar({
  data,
  compact = false,
  weekStart,
  onWeekChange,
  proposals = [],
  onSelect,
}: {
  data: Dashboard;
  compact?: boolean;
  weekStart?: string;
  onWeekChange?: (date: string) => void;
  proposals?: Recovery[];
  onSelect?: (a: Assignment | Slot) => void;
}) {
  const [internal, setInternal] = useState(data.week_start),
    [mode, setMode] = useState<'week' | 'day'>('week');
  const start = weekStart || internal,
    zone = data.timezone;
  const change = (s: string) => {
    setInternal(s);
    onWeekChange?.(s);
  };
  const dates = Array.from({ length: mode === 'week' ? 7 : 1 }, (_, i) => addDays(start, i));
  const workers = compact ? data.workers.slice(0, 4) : data.workers;
  return (
    <>
      <div className="calendar-toolbar">
        <div className="segmented">
          <button className={mode === 'week' ? 'selected' : ''} onClick={() => setMode('week')}>
            Week
          </button>
          <button className={mode === 'day' ? 'selected' : ''} onClick={() => setMode('day')}>
            Day
          </button>
        </div>
        <div className="calendar-navigation">
          <Button
            variant="ghost"
            aria-label="Previous period"
            onClick={() => change(addDays(start, mode === 'week' ? -7 : -1))}
          >
            <ChevronLeft size={16} />
          </Button>
          <label>
            <span className="sr-only">Calendar date</span>
            <input
              type="date"
              value={start}
              onChange={(e) => e.target.value && change(e.target.value)}
            />
          </label>
          <Button
            variant="ghost"
            aria-label="Next period"
            onClick={() => change(addDays(start, mode === 'week' ? 7 : 1))}
          >
            <ChevronRight size={16} />
          </Button>
          <Button variant="outline" size="sm" onClick={() => change(data.week_start)}>
            {data.demo ? 'Demo week' : 'Current week'}
          </Button>
        </div>
      </div>
      <div className="calendar-scroll">
        <table className={`team-calendar timed-calendar ${mode === 'day' ? 'single-day' : ''}`}>
          <thead>
            <tr>
              <th>
                Team member<small>{zone}</small>
              </th>
              {dates.map((d) => (
                <th key={d}>
                  <span>
                    {new Intl.DateTimeFormat('en-CA', { weekday: 'short', timeZone: 'UTC' }).format(
                      new Date(d + 'T12:00:00Z'),
                    )}
                  </span>
                  <b>{Number(d.slice(-2))}</b>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {workers.map((w) => (
              <tr key={w.id}>
                <th>
                  <div className="calendar-worker">
                    <Avatar worker={w} small />
                    <div>
                      <strong>{w.name}</strong>
                      <small>{w.title}</small>
                    </div>
                  </div>
                </th>
                {dates.map((d) => {
                  const actual = data.assignments.filter(
                    (a) =>
                      a.worker_id === w.id &&
                      a.status === 'confirmed' &&
                      intersect(a.starts_at, a.ends_at, d, zone),
                  );
                  const busy = w.busy
                    .map((b) => intersect(b.starts_at, b.ends_at, d, zone))
                    .filter((b): b is NonNullable<typeof b> => !!b);
                  const available = w.availability
                    .map((a) => intersect(a.starts_at, a.ends_at, d, zone))
                    .filter((a): a is NonNullable<typeof a> => !!a);
                  const free = freeWindows(available, [...busy, ...actual]);
                  const projected = proposals
                    .filter(
                      (p) =>
                        !['rejected', 'expired', 'revision_requested'].includes(p.status) &&
                        p.status !== 'published',
                    )
                    .flatMap((p) =>
                      p.proposed_schedule
                        .filter(
                          (s) => s.worker_id === w.id && intersect(s.starts_at, s.ends_at, d, zone),
                        )
                        .map((s) => ({ ...s, proposal: p })),
                    );
                  return (
                    <td key={d}>
                      {actual.map((a) => (
                        <button
                          className="calendar-event confirmed-event"
                          key={a.id}
                          style={{ borderLeftColor: a.color, background: a.color + '22' }}
                          onClick={() => onSelect?.(a)}
                        >
                          <strong>{a.task_name}</strong>
                          <span>
                            {shortDate(a.starts_at)} · {clock(a.starts_at)}–{clock(a.ends_at)}
                          </span>
                          <small>Confirmed</small>
                        </button>
                      ))}
                      {projected.map((s, i) => (
                        <button
                          className={`calendar-event proposed-event ${s.proposal.status === 'awaiting_confirmation' ? 'awaiting-event' : ''}`}
                          key={s.proposal.id + i}
                          onClick={() => onSelect?.(s)}
                        >
                          <strong>{s.task_name}</strong>
                          <span>
                            {clock(s.starts_at)}–{clock(s.ends_at)}
                          </span>
                          <small>
                            {s.proposal.stale
                              ? 'Stale proposal'
                              : s.proposal.status === 'awaiting_confirmation'
                                ? 'Awaiting acceptance'
                                : 'Proposed'}
                          </small>
                        </button>
                      ))}
                      {busy.map((b, i) => (
                        <div className="calendar-busy" key={i}>
                          Busy · {clock(b.starts_at)}–{clock(b.ends_at)}
                        </div>
                      ))}
                      {free.map((a, i) => (
                        <div className="free-window" key={i}>
                          Free {clock(a.starts_at)}–{clock(a.ends_at)}
                        </div>
                      ))}
                      {!actual.length && !projected.length && !busy.length && !free.length && (
                        <div className="calendar-unpublished">No availability published</div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="calendar-state-legend">
        <span>
          <i className="solid-swatch" />
          Confirmed
        </span>
        <span>
          <i className="dashed-swatch" />
          Proposed
        </span>
        <span>
          <i className="amber-swatch" />
          Awaiting acceptance
        </span>
        <span>
          <i className="busy-swatch" />
          Busy / unavailable
        </span>
        <span>
          <ShieldCheck size={12} /> Private details stay private
        </span>
      </div>
    </>
  );
}
