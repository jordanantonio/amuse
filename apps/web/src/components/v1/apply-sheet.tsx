'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  BadgeCheck,
  CalendarCheck,
  CalendarX,
  Check,
  CircleX,
  Clock3,
  HardHat,
  MapPin,
  Shirt,
  Sun,
  Wallet,
} from 'lucide-react';
import { market } from '@/lib/market';
import type { PostingDetail } from '@/lib/market-types';
import { day, dollars, duration, payUnit, range } from '@/lib/format';
import { CompanyBadge } from './avatar';
import { PATTERNS } from './contract';
import { ErrorNote, Skeleton } from './ui';

const STEPS = ['The job', 'Your fit', 'A few questions', 'Review and send'];

/** APPLY-1/2: one 4-step sheet for every posting. */
export function ApplySheet({
  postingId,
  onClose,
  onApplied,
}: {
  postingId: string;
  onClose: () => void;
  onApplied?: () => void;
}) {
  const [data, setData] = useState<PostingDetail | null>(null);
  const [error, setError] = useState('');
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  useEffect(() => {
    market<PostingDetail>(`/postings/${postingId}`).then(setData, (e) =>
      setError((e as Error).message),
    );
  }, [postingId]);
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && !busy && onClose();
    document.addEventListener('keydown', esc);
    return () => document.removeEventListener('keydown', esc);
  }, [busy, onClose]);

  const send = async () => {
    setBusy(true);
    setError('');
    try {
      await market(`/postings/${postingId}/apply`, { method: 'POST', body: { answers, note } });
      setSent(true);
      onApplied?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const p = data?.posting;
  const required = p?.match.items.filter((i) => i.required) || [];
  const bonus = p?.match.items.filter((i) => !i.required) || [];
  const blocked = !!p && (!p.eligible || data?.calendar?.status === 'conflict');
  return (
    <div
      className="sheet-backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && !busy && onClose()}
    >
      <aside
        className="sheet apply-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={p ? `Apply to ${p.title}` : 'Apply'}
      >
        <header className="sheet-head">
          <div>
            <p className="apply-kicker">
              {sent ? 'Application sent' : `Step ${step + 1} of 4 · ${STEPS[step]}`}
            </p>
            <h2>{p?.title || 'Loading…'}</h2>
          </div>
          <button className="text-button" onClick={onClose} disabled={busy}>
            Close
          </button>
        </header>
        {!sent && (
          <div
            className="apply-progress"
            role="progressbar"
            aria-valuemin={1}
            aria-valuemax={4}
            aria-valuenow={step + 1}
            aria-label="Application progress"
          >
            {STEPS.map((s, i) => (
              <span key={s} className={i <= step ? 'on' : ''} />
            ))}
          </div>
        )}
        {error && <ErrorNote message={error} />}
        {!data && !error && <Skeleton lines={3} />}

        {p && data && !sent && step === 0 && (
          <section className="apply-step">
            <div className="apply-org">
              <CompanyBadge name={p.org.name} industry={p.org.industry} size={52} />
              <div>
                <strong>
                  {p.org.name}
                  {p.org.verified && (
                    <span className="verified-mark">
                      <BadgeCheck size={15} aria-hidden="true" /> Verified
                    </span>
                  )}
                </strong>
                {data.org_about && <p>{data.org_about}</p>}
              </div>
            </div>
            <dl className="apply-facts">
              <Fact icon={MapPin} label="Site">
                {p.site_address || `${p.city} · exact address shared with an offer`}
              </Fact>
              <Fact icon={Clock3} label="Shift times">
                {data.shift_hours || PATTERNS[p.schedule_pattern]}
              </Fact>
              <Fact icon={Wallet} label="Pay">
                {dollars(p.pay_rate_cents)} {payUnit[p.pay_unit]}
              </Fact>
              <Fact icon={CalendarCheck} label="Length">
                {range(p.start_date, p.end_date)} · {duration(p.start_date, p.end_date)}
              </Fact>
              <Fact icon={Shirt} label="PPE provided">
                {data.ppe_provided?.length ? data.ppe_provided.join(', ') : 'Ask the business'}
              </Fact>
              <Fact icon={HardHat} label="Bring your own">
                {data.ppe_required?.length ? data.ppe_required.join(', ') : 'Nothing extra'}
              </Fact>
            </dl>
            <div className="apply-day">
              <h3>
                <Sun size={18} aria-hidden="true" /> A typical day
              </h3>
              <p>
                {data.typical_day ||
                  data.description ||
                  'The business will walk you through the day on your first shift.'}
              </p>
            </div>
          </section>
        )}

        {p && data && !sent && step === 1 && (
          <section className="apply-step">
            <h3>Required certifications</h3>
            <ul className="apply-certs">
              {required.map((i) => (
                <CertRow key={i.credential_type_id} name={i.name} state={i.state} />
              ))}
              {!required.length && <li>No certifications required.</li>}
            </ul>
            {bonus.length > 0 && (
              <>
                <h3>Bonus certifications</h3>
                <ul className="apply-certs">
                  {bonus.map((i) => (
                    <CertRow key={i.credential_type_id} name={i.name} state={i.state} />
                  ))}
                </ul>
              </>
            )}
            <h3>Your calendar</h3>
            <p className={`calendar-check ${data.calendar?.status || 'clear'}`}>
              {data.calendar?.status === 'conflict' ? (
                <CalendarX size={20} aria-hidden="true" />
              ) : (
                <CalendarCheck size={20} aria-hidden="true" />
              )}
              <span>
                <strong>{range(p.start_date, p.end_date)}</strong>
                {data.calendar?.message || 'No conflicts with your schedule'}
              </span>
            </p>
            {!p.eligible && (
              <p className="v1-inline-error">You can’t apply yet: {p.reasons.join('; ')}.</p>
            )}
          </section>
        )}

        {p && data && !sent && step === 2 && (
          <section className="apply-step apply-questions">
            {!data.questions?.length && (
              <p className="v1-lede">This business has no screening questions.</p>
            )}
            {data.questions?.map((q) =>
              q.kind === 'yes_no' ? (
                <fieldset key={q.id} className="yes-no">
                  <legend>{q.prompt}</legend>
                  {['Yes', 'No'].map((v) => (
                    <label key={v} className={`chip ${answers[q.id] === v ? 'on' : ''}`}>
                      <input
                        type="radio"
                        name={q.id}
                        checked={answers[q.id] === v}
                        onChange={() => setAnswers({ ...answers, [q.id]: v })}
                      />
                      {v}
                    </label>
                  ))}
                </fieldset>
              ) : (
                <label key={q.id}>
                  {q.prompt}
                  <input
                    type={q.kind === 'date' ? 'date' : 'text'}
                    value={answers[q.id] || ''}
                    min={q.kind === 'date' ? p.start_date : undefined}
                    onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                  />
                </label>
              ),
            )}
            <label>
              Note to {p.org.name} <small>(optional)</small>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                maxLength={1000}
                placeholder="Anything they should know"
              />
            </label>
          </section>
        )}

        {p && data && !sent && step === 3 && (
          <section className="apply-step">
            <dl className="apply-review">
              <div>
                <dt>Contract</dt>
                <dd>
                  {p.title}, {p.org.name}
                </dd>
              </div>
              <div>
                <dt>Dates</dt>
                <dd>{range(p.start_date, p.end_date)}</dd>
              </div>
              <div>
                <dt>Pay</dt>
                <dd>
                  {dollars(p.pay_rate_cents)} {payUnit[p.pay_unit]}
                </dd>
              </div>
              <div>
                <dt>Certifications</dt>
                <dd>
                  {p.match.required_held} of {p.match.required_total} required
                </dd>
              </div>
              {data.questions?.map((q) => (
                <div key={q.id}>
                  <dt>{q.prompt}</dt>
                  <dd>
                    {answers[q.id] ? (
                      q.kind === 'date' ? (
                        day(answers[q.id], true)
                      ) : (
                        answers[q.id]
                      )
                    ) : (
                      <em>Skipped</em>
                    )}
                  </dd>
                </div>
              ))}
              {note && (
                <div>
                  <dt>Note</dt>
                  <dd>{note}</dd>
                </div>
              )}
            </dl>
            <p className="wallet-meta">
              Your profile and certifications are included automatically.
            </p>
          </section>
        )}

        {sent && p && (
          <section className="apply-step apply-done">
            <p className="match-line ok">
              <Check size={20} aria-hidden="true" /> {p.org.name} has your application.
            </p>
            <ol className="mini-timeline" aria-label="What happens next">
              {['Applied', 'Reviewed', 'Offer', 'Booked'].map((s, i) => (
                <li key={s} className={i === 0 ? 'done' : ''}>
                  <span className="dot">{i === 0 && <Check size={14} aria-hidden="true" />}</span>
                  {s}
                </li>
              ))}
            </ol>
            <Link className="button button-primary" href="/work?tab=applied" onClick={onClose}>
              Track it in Work
            </Link>
          </section>
        )}

        {p && !sent && (
          <footer className="apply-nav">
            {step > 0 && (
              <button
                className="button button-outline"
                disabled={busy}
                onClick={() => setStep(step - 1)}
              >
                Back
              </button>
            )}
            {step < 3 ? (
              <button
                className="button button-primary"
                disabled={step === 1 && blocked}
                onClick={() => setStep(step + 1)}
              >
                Continue
              </button>
            ) : (
              <button
                className="button button-primary"
                disabled={busy || blocked}
                onClick={() => void send()}
              >
                {busy ? 'Sending…' : 'Send application'}
              </button>
            )}
          </footer>
        )}
      </aside>
    </div>
  );
}

function Fact({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof MapPin;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt>
        <Icon size={16} aria-hidden="true" /> {label}
      </dt>
      <dd>{children}</dd>
    </div>
  );
}

function CertRow({ name, state }: { name: string; state: 'ok' | 'pending' | 'missing' }) {
  const Icon = state === 'ok' ? BadgeCheck : state === 'pending' ? Clock3 : CircleX;
  const word = state === 'ok' ? 'Verified' : state === 'pending' ? 'Pending' : 'Missing';
  return (
    <li className={`apply-cert ${state}`}>
      <Icon size={18} aria-hidden="true" />
      <span>{name}</span>
      <strong>{word}</strong>
    </li>
  );
}
