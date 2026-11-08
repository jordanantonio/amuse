'use client';
import { useState } from 'react';
import { ArrowRight, Check, MessageSquare, ShieldCheck, Clock3 } from 'lucide-react';
import type { Recovery, Slot } from '@/lib/adaptive-types';
import { money, clock, shortDate } from '@/lib/display';
import { Button } from './ui/button';
const labels: Record<string, string> = {
  pending_approval: 'Pending manager approval',
  awaiting_confirmation: 'Awaiting worker acceptance',
  ready_to_publish: 'Ready to publish',
  published: 'Published',
  rejected: 'Rejected',
  revision_requested: 'Revision requested',
  expired: 'Expired',
};
export const stateLabel = (s: string) => labels[s] || s.replaceAll('_', ' ');
export function Gantt({
  slots,
  start,
  end,
  title,
}: {
  slots: Slot[];
  start: string;
  end: string;
  title: string;
}) {
  const lo = Date.parse(start),
    span = Math.max(3600000, Date.parse(end) - lo);
  return (
    <section className="gantt-panel">
      <h3>{title}</h3>
      {slots.length ? (
        slots.map((s, i) => (
          <div className="gantt-row" key={i}>
            <div>
              <strong>{s.task_name}</strong>
              <span>
                {s.worker_name} · {shortDate(s.starts_at)} {clock(s.starts_at)}
              </span>
            </div>
            <div className="gantt-track">
              <span
                style={{
                  left: `${Math.max(0, ((Date.parse(s.starts_at) - lo) / span) * 100)}%`,
                  width: `${Math.max(2, ((Date.parse(s.ends_at) - Date.parse(s.starts_at)) / span) * 100)}%`,
                }}
                title={`${clock(s.starts_at)}–${clock(s.ends_at)}`}
              />
            </div>
          </div>
        ))
      ) : (
        <p className="empty-card">No assignments in the original plan.</p>
      )}
      <div className="gantt-axis">
        <span>{shortDate(start)}</span>
        <span>{shortDate(end)}</span>
      </div>
    </section>
  );
}
export function ProposalComparison({
  proposal: p,
  manager,
  busy,
  onDecision,
  onPublish,
  onConfirm,
}: {
  proposal: Recovery;
  manager: boolean;
  busy: boolean;
  onDecision: (decision: string, comment: string) => void;
  onPublish: () => void;
  onConfirm: (decision: string) => void;
}) {
  const [comment, setComment] = useState('');
  const combined = [
    ...p.original_schedule.filter((s) => !p.replaces_assignment_ids.includes(s.id || '')),
    ...p.proposed_schedule,
  ];
  const all = [...p.original_schedule, ...combined],
    start = all.map((s) => s.starts_at).sort()[0] || p.created_at,
    end =
      all
        .map((s) => s.ends_at)
        .sort()
        .at(-1) || p.expires_at;
  const own = p.confirmations[0];
  return (
    <section className="panel comparison" id="proposal-comparison">
      <div className="section-heading">
        <div>
          <div className="eyebrow">
            {p.objective.replaceAll('_', ' ')} · {p.id.slice(0, 8)}
          </div>
          <h2>{p.project_name}</h2>
          <p>
            {stateLabel(p.status)} · Expires {shortDate(p.expires_at)}, {clock(p.expires_at)}
          </p>
        </div>
        <span className={`badge ${p.status === 'published' ? 'green' : 'purple'}`}>
          {stateLabel(p.status)}
        </span>
      </div>
      {p.stale && (
        <div className="banner error" role="alert">
          <Clock3 size={18} />
          <div>
            <strong>This proposal is stale.</strong>
            <p>Scheduling inputs changed. Generate another plan before approval or publication.</p>
          </div>
        </div>
      )}
      <div className="proposal-reason">
        <ShieldCheck size={18} />
        <div>
          <strong>Why SHIFT recommends this plan</strong>
          <p>{p.reason}</p>
        </div>
      </div>
      {manager && (
        <>
          <div className="comparison-metrics">
            <div>
              <span>Planned project labour</span>
              <strong>{money(Number(p.metrics.labour_cost_cents || 0))}</strong>
              <small>
                {Number(p.metrics.cost_difference_cents) >= 0 ? '+' : ''}
                {money(Number(p.metrics.cost_difference_cents || 0))} vs previously assigned work
              </small>
            </div>
            <div>
              <span>Projected completion</span>
              <strong>{shortDate(String(p.metrics.completion_at))}</strong>
              <small>
                {Number(p.metrics.completion_difference_minutes || 0) / 60}h vs original partial
                plan
              </small>
            </div>
            <div>
              <span>Changes / new assignments</span>
              <strong>
                {p.metrics.changed_assignments} / {p.metrics.new_assignments}
              </strong>
              <small>Other confirmed work stays fixed</small>
            </div>
            <div>
              <span>Contingency reserved / consumed</span>
              <strong>
                {Number(p.metrics.contingency_reserved_minutes || 0) / 60}h /{' '}
                {Number(p.metrics.contingency_consumed_minutes || 0) / 60}h
              </strong>
              <small>
                {Number(p.metrics.task_buffer_minutes || 0) / 60}h task buffer allocated
              </small>
            </div>
          </div>
          <div className="gantt-comparison">
            <Gantt
              slots={p.original_schedule}
              start={start}
              end={end}
              title="Original confirmed plan"
            />
            <Gantt slots={combined} start={start} end={end} title="Proposed complete plan" />
          </div>
        </>
      )}
      <div className="proposal-slots">
        {p.proposed_schedule.map((s, i) => (
          <div className="proposal-row" key={i}>
            <div>
              <strong>{s.task_name}</strong>
              <p>
                {s.worker_name} · {shortDate(s.starts_at)} · {clock(s.starts_at)}–{clock(s.ends_at)}
              </p>
            </div>
            <span className="badge purple">
              {p.status === 'published' ? 'Published' : 'Proposed'}
            </span>
            {manager && <strong>{money(s.cost_cents)}</strong>}
          </div>
        ))}
      </div>
      {p.confirmations.length > 0 && (
        <div className="confirmation-list">
          <h3>Worker confirmations</h3>
          {p.confirmations.map((c) => (
            <div key={c.id}>
              <span>{c.worker_name}</span>
              <span className={`badge ${c.status === 'accepted' ? 'green' : 'amber'}`}>
                {c.status}
              </span>
            </div>
          ))}
        </div>
      )}
      {manager && p.status === 'pending_approval' && (
        <div className="approval-controls">
          <label>
            Decision comment
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              maxLength={2000}
              placeholder="Explain your decision or requested revision…"
            />
          </label>
          <div className="actions">
            <Button disabled={busy || p.stale} onClick={() => onDecision('approve', comment)}>
              <Check size={15} />
              Approve & request acceptance
            </Button>
            <Button
              disabled={busy}
              variant="outline"
              onClick={() => onDecision('request_revision', comment)}
            >
              Request revision
            </Button>
            <Button disabled={busy} variant="danger" onClick={() => onDecision('reject', comment)}>
              Reject
            </Button>
          </div>
          <p>
            Approval sends worker confirmation requests. It does not publish or change confirmed
            assignments.
          </p>
        </div>
      )}
      {manager && p.status === 'ready_to_publish' && (
        <div className="approval-controls">
          <Button disabled={busy || p.stale} onClick={onPublish}>
            <ShieldCheck size={15} />
            Revalidate & publish schedule
          </Button>
          <p>All workers accepted. Publishing atomically replaces only the approved assignments.</p>
        </div>
      )}
      {!manager && p.status === 'awaiting_confirmation' && own?.status === 'pending' && (
        <div className="approval-controls">
          <div className="actions">
            <Button disabled={busy || p.stale} onClick={() => onConfirm('accept')}>
              Accept assignments
            </Button>
            <Button disabled={busy} variant="outline" onClick={() => onConfirm('decline')}>
              Decline & request revision
            </Button>
          </div>
          <p>
            Accepting reserves your proposed time. Your confirmed calendar changes after the manager
            publishes.
          </p>
        </div>
      )}
      {manager && ['awaiting_confirmation', 'ready_to_publish'].includes(p.status) && (
        <div className="approval-controls">
          <label>
            Revision comment
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              maxLength={2000}
              placeholder="Explain why this plan needs revision…"
            />
          </label>
          <Button
            disabled={busy}
            variant="outline"
            onClick={() => onDecision('request_revision', comment)}
          >
            Return for revision & release reservations
          </Button>
        </div>
      )}
      {p.history.length > 0 && (
        <div className="approval-history">
          <h3>
            <MessageSquare size={15} /> Decision history
          </h3>
          {p.history.map((h, i) => (
            <div key={i}>
              <strong>
                {h.actor} · {h.decision.replaceAll('_', ' ')}
              </strong>
              <span>
                {shortDate(h.created_at)} {clock(h.created_at)}
              </span>
              {h.comment && <p>{h.comment}</p>}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
