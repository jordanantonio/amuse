import { Check } from 'lucide-react';
import type { Dashboard } from '@/lib/types';
import { clock, day } from '@/lib/display';
import { Avatar } from '@/components/ui/avatar';
export function Calendar({ data, compact = false }: { data: Dashboard; compact?: boolean }) {
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
                <b>{i + 9}</b>
                {i === 0 && <span className="week-tag">DEMO WEEK</span>}
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
              {[9, 10, 11, 12, 13].map((d) => {
                const assignments = data.assignments.filter(
                    (a) =>
                      a.worker_id === w.id &&
                      a.status === 'confirmed' &&
                      Number(day(a.starts_at)) === d,
                  ),
                  published = w.availability.some((a) => Number(day(a.starts_at)) === d);
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
                        {w.busy.some((b) => Number(day(b.starts_at)) === d) && (
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
