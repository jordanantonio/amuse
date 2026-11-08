'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { CalendarPlus, Download, TriangleAlert, CircleCheck } from 'lucide-react';
import { market } from '@/lib/market';
import type { AcceptPreview, ApplicationView } from '@/lib/market-types';
import { googleEventUrl } from '@/lib/gcal';
import { range } from '@/lib/format';
import { ErrorNote, Modal, Skeleton } from './ui';

/** FLOW-3: accept with a conflict check and one-click withdrawal of overlapping work. */
export function AcceptOffer({
  application,
  onAccepted,
}: {
  application: ApplicationView;
  onAccepted: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="button button-primary" onClick={() => setOpen(true)}>
        Accept offer
      </button>
      {open && (
        <AcceptDialog
          application={application}
          onClose={async (accepted) => {
            setOpen(false);
            if (accepted) await onAccepted();
          }}
        />
      )}
    </>
  );
}

function AcceptDialog({
  application: a,
  onClose,
}: {
  application: ApplicationView;
  onClose: (accepted: boolean) => void;
}) {
  const [preview, setPreview] = useState<AcceptPreview | null>(null);
  const [withdraw, setWithdraw] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [accepted, setAccepted] = useState<ApplicationView | null>(null);
  useEffect(() => {
    market<AcceptPreview>(`/applications/${a.id}/accept-preview`).then(
      (p) => {
        setPreview(p);
        setWithdraw(p.overlapping.map((o) => o.id));
      },
      (e) => setError((e as Error).message),
    );
  }, [a.id]);
  const p = a.posting;
  const blocked = !!preview && (preview.conflicts.length > 0 || preview.ticket_problems.length > 0);
  const accept = async () => {
    if (
      withdraw.length &&
      !window.confirm(
        `Withdraw ${withdraw.length} overlapping ${withdraw.length === 1 ? 'application' : 'applications'} and accept this offer?`,
      )
    )
      return;
    setBusy(true);
    setError('');
    try {
      setAccepted(
        await market<ApplicationView>(`/applications/${a.id}/accept`, {
          method: 'POST',
          body: { withdraw_ids: withdraw },
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  if (accepted?.engagement)
    return (
      <Modal title="You’re booked" onClose={() => onClose(true)}>
        <div className="editor-fields accept-done">
          <p className="match-line ok">
            <CircleCheck size={20} aria-hidden="true" />
            {p.title} with {p.org.name},{' '}
            {range(accepted.engagement.start_date, accepted.engagement.end_date)}
          </p>
          <p className="v1-lede">
            Shift has blocked {p.is_exclusive ? 'these dates' : 'the scheduled days'} so you can’t
            be double-booked. Add them to your phone’s calendar too.
          </p>
          <CalendarButtons engagementId={accepted.engagement.id} event={eventFor(accepted)} />
        </div>
        <div className="editor-actions">
          <button className="text-button" onClick={() => onClose(true)}>
            Done
          </button>
        </div>
      </Modal>
    );
  return (
    <Modal
      title="Accept this offer?"
      description={`${p.title} with ${p.org.name}, ${range(p.start_date, p.end_date)}.`}
      onClose={() => onClose(false)}
      busy={busy}
    >
      <div className="editor-fields">
        {!preview && !error && <Skeleton lines={1} />}
        {preview?.conflicts.map((c) => (
          <p key={c.engagement_id} className="conflict-note" role="alert">
            <TriangleAlert size={20} aria-hidden="true" />
            {c.message}
          </p>
        ))}
        {preview?.ticket_problems.length ? (
          <p className="conflict-note" role="alert">
            <TriangleAlert size={20} aria-hidden="true" />
            Your certifications changed since you applied: {preview.ticket_problems.join(
              '; ',
            )}.{' '}
            <Link className="inline-link" href="/profile">
              Update your wallet
            </Link>
          </p>
        ) : null}
        {preview && !blocked && (
          <p className="v1-lede">
            {p.is_exclusive
              ? 'This is full-time, so every day from start to end will be blocked on your schedule.'
              : 'This is part-time, so only the scheduled days will be blocked.'}
          </p>
        )}
        {preview && !blocked && preview.overlapping.length > 0 && (
          <fieldset className="overlap-field">
            <legend>These open applications overlap these dates. Withdraw them?</legend>
            {preview.overlapping.map((o) => (
              <label key={o.id} className="overlap-item">
                <input
                  type="checkbox"
                  checked={withdraw.includes(o.id)}
                  onChange={(e) =>
                    setWithdraw((w) =>
                      e.target.checked ? [...w, o.id] : w.filter((x) => x !== o.id),
                    )
                  }
                />
                <span>
                  <strong>{o.posting.title}</strong>
                  {o.posting.org.name}, {range(o.posting.start_date, o.posting.end_date)}
                </span>
              </label>
            ))}
          </fieldset>
        )}
        {preview && !blocked && preview.manual_overlaps.length > 0 && (
          <p className="wallet-meta">
            You marked yourself unavailable{' '}
            {preview.manual_overlaps.map((m) => range(m.start_date, m.end_date)).join(', ')}. Check
            those days with {p.org.name}.
          </p>
        )}
        {error && <ErrorNote message={error} />}
      </div>
      <div className="editor-actions">
        <button className="button button-outline" disabled={busy} onClick={() => onClose(false)}>
          {blocked ? 'Close' : 'Not now'}
        </button>
        {!blocked && (
          <button
            className="button button-primary"
            disabled={busy || !preview}
            onClick={() => void accept()}
          >
            {busy ? 'Accepting…' : 'Accept and block dates'}
          </button>
        )}
      </div>
    </Modal>
  );
}

/** SCHED-2 / CAL-3: Google's event template link (no OAuth) and the .ics file. */
export function CalendarButtons({
  engagementId,
  event,
}: {
  engagementId: string;
  event: { title: string; start: string; end: string; details?: string; location?: string };
}) {
  return (
    <div className="calendar-buttons">
      <a
        className="button button-primary"
        href={googleEventUrl(event)}
        target="_blank"
        rel="noopener noreferrer"
      >
        <CalendarPlus size={18} aria-hidden="true" />
        Add to Google Calendar
      </a>
      <a
        className="button button-outline"
        href={`/api/v1/market/engagements/${engagementId}/calendar.ics`}
        download
      >
        <Download size={18} aria-hidden="true" />
        Download .ics
      </a>
    </div>
  );
}

export function eventFor(a: ApplicationView) {
  const p = a.posting;
  return {
    title: `Shift: ${p.title} @ ${p.org.name}`,
    start: a.engagement?.start_date || p.start_date,
    end: a.engagement?.end_date || p.end_date,
    details: `${p.trade} contract with ${p.org.name}, booked through Shift.`,
    location: p.site_address || p.city,
  };
}

/** Active contracts: calendar, schedule and cancel. */
export function EngagementActions({
  application: a,
  onChange,
}: {
  application: ApplicationView;
  onChange: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (!a.engagement) return null;
  return (
    <div className="engagement-actions">
      <CalendarButtons engagementId={a.engagement.id} event={eventFor(a)} />
      <div className="actions">
        <Link className="text-button" href="/schedule">
          See on Schedule
        </Link>
        <button
          className="text-button danger-text"
          disabled={busy}
          onClick={async () => {
            if (
              !window.confirm(
                'Cancel this contract? Its dates are freed and calendar events removed.',
              )
            )
              return;
            setBusy(true);
            setError('');
            try {
              await market(`/engagements/${a.engagement!.id}/cancel`, { method: 'POST' });
              await onChange();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Cancel contract
        </button>
      </div>
      {error && <ErrorNote message={error} />}
    </div>
  );
}
