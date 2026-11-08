'use client';
import { useEffect, useState } from 'react';
import { market } from '@/lib/market';
import { clock } from '@/lib/crew-types';
import { day } from '@/lib/format';
import { PersonAvatar } from './avatar';
import { ErrorNote, Skeleton } from './ui';

type PersonDay = {
  day: string;
  free: number[][];
  booked: number[][];
  shifts: { label: string; start_minute: number; end_minute: number }[];
};
type PersonRow = {
  user_id: string;
  name: string;
  headline: string;
  week_hours: number;
  days: PersonDay[];
};

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const pct = (m: number) => `${(m / 1440) * 100}%`;

function describe(p: PersonRow, d: PersonDay) {
  const free = d.free.map(([s, e]) => `${clock(s)}–${clock(e)}`).join(', ') || 'not available';
  const shifts = d.shifts.map(
    (s) => `${s.label.split(',')[0]} ${clock(s.start_minute)}–${clock(s.end_minute)}`,
  );
  return `${p.name}, ${day(d.day)}: free ${free}${shifts.length ? `; booked ${shifts.join(', ')}` : ''}`;
}

/** CREW-4: people x days heatmap of availability bars instead of a wall of text. */
export function PeopleView({ start }: { start: string }) {
  const [rows, setRows] = useState<PersonRow[] | null>(null);
  const [error, setError] = useState('');
  const [picked, setPicked] = useState<string | null>(null);
  useEffect(() => {
    setRows(null);
    market<PersonRow[]>(`/crew/people?start=${start}`).then(setRows, (e) =>
      setError((e as Error).message),
    );
  }, [start]);
  if (error) return <ErrorNote message={error} />;
  if (!rows) return <Skeleton lines={3} />;
  const detail = picked
    ? (() => {
        const [uid, d] = picked.split('|');
        const p = rows.find((r) => r.user_id === uid);
        const cell = p?.days.find((x) => x.day === d);
        return p && cell ? describe(p, cell) : '';
      })()
    : '';
  return (
    <div className="people-view light-card">
      <table className="people-table">
        <thead>
          <tr>
            <th scope="col">Crew</th>
            {rows[0]?.days.map((d, i) => (
              <th key={d.day} scope="col">
                {WEEKDAYS[i]} <span>{+d.day.slice(8, 10)}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.user_id}>
              <th scope="row">
                <span className="people-who">
                  <PersonAvatar id={p.user_id} name={p.name} size={32} />
                  <span>
                    <strong>{p.name}</strong>
                    <small>{p.week_hours} h this week</small>
                  </span>
                </span>
              </th>
              {p.days.map((d) => {
                const label = describe(p, d);
                const key = `${p.user_id}|${d.day}`;
                return (
                  <td key={d.day}>
                    <button
                      className={`heat-cell ${picked === key ? 'on' : ''}`}
                      title={label}
                      aria-label={label}
                      aria-pressed={picked === key}
                      onClick={() => setPicked(picked === key ? null : key)}
                    >
                      {d.free.map(([s, e], i) => (
                        <span
                          key={`f${i}`}
                          className="avail-free"
                          style={{ left: pct(s), width: pct(e - s) }}
                        />
                      ))}
                      {d.booked.map(([s, e], i) => (
                        <span
                          key={`b${i}`}
                          className="heat-booked"
                          style={{ left: pct(s), width: pct(e - s) }}
                        />
                      ))}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="people-detail" aria-live="polite">
        {detail || 'Tap a day to see exact times. Light = free, gold = booked.'}
      </p>
    </div>
  );
}
