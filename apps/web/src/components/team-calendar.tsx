import { Check } from 'lucide-react';
import type { Dashboard } from '@/lib/types';
import { clock, day, localDate } from '@/lib/display';
import { Avatar } from '@/components/ui/avatar';
export function Calendar({ data, compact = false }: { data: Dashboard; compact?: boolean }) {
  const days = Array.from({ length: 5 }, (_, i) => {
    const date = new Date(data.week_start + 'T12:00:00Z');
    date.setUTCDate(date.getUTCDate() + i);
    return date.toISOString().slice(0, 10);
  });
  const workers = compact ? data.workers.slice(0, 4) : data.workers;
  return (
    <div className="calendar-scroll">
      <table className="team-calendar">
        <thead>
          <tr>
            <th>
              <span>{data.persona.role === 'worker' ? 'YOUR SCHEDULE' : 'TEAM MEMBER'}</span>
              <small>{workers.length} people</small>
            </th>
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map((d, i) => (
              <th key={d}>
                <span>{d}</span>
                <b>{day(days[i] + 'T12:00:00Z')}</b>
                {i === 0 && data.demo && <span className="week-tag">DEMO WEEK</span>}
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
              {days.map((d) => {
                const assignments = data.assignments.filter(
                    (a) =>
                      a.worker_id === w.id &&
                      a.status === 'confirmed' &&
                      localDate(a.starts_at) === d,
                  ),
                  published = w.availability.some((a) => localDate(a.starts_at) === d);
                return (
                  <td key={d}>
                    {assignments.length ? (
                      assignments.map((a) => (
                        <div
                          className="calendar-event"
                          key={a.id}
                          style={{ background: a.color + '1c', borderLeftColor: a.color }}
                          title={`${a.project_name}: ${a.task_name}`}
                        >
                          <strong>{a.task_name}</strong>
                          <span>
                            {clock(a.starts_at)} – {clock(a.ends_at)}
                          </span>
                          <small>
                            <Check size={10} />
                            Confirmed
                          </small>
                        </div>
                      ))
                    ) : (
                      <div className={`calendar-free ${published ? '' : 'unavailable'}`}>
                        <span className="available-dot" />
                        {published ? 'Available windows' : 'Not published'}
                        {w.busy.some((b) => localDate(b.starts_at) === d) && (
                          <small>Busy intervals apply</small>
                        )}
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
