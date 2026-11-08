'use client';
import { Suspense, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Plus, Workflow } from 'lucide-react';
import { market } from '@/lib/market';
import type { ApplicationView, OrgWork, PostingCard, WorkView } from '@/lib/market-types';
import { dollars, range } from '@/lib/format';
import { useSession } from '@/components/v1/session';
import {
  ApplicantRow,
  ApplicationStatusBlock,
  MyApplicationRow,
} from '@/components/v1/applications';
import { AcceptOffer, EngagementActions } from '@/components/v1/accept';
import { PostingForm } from '@/components/v1/posting-form';
import { EmptyState, ErrorNote, Skeleton, StatusChip } from '@/components/v1/ui';

export default function WorkPage() {
  return (
    <Suspense fallback={<Skeleton lines={3} />}>
      <Work />
    </Suspense>
  );
}

function Work() {
  const { me } = useSession();
  return me.mode === 'business' ? <BusinessWork /> : <ApplicantWork />;
}

function Tabs<T extends string>({
  tabs,
  current,
  counts,
}: {
  tabs: [T, string][];
  current: T;
  counts?: Partial<Record<T, number>>;
}) {
  const router = useRouter();
  const params = useSearchParams();
  return (
    <div className="v1-tabs" role="tablist" aria-label="Work sections">
      {tabs.map(([id, label]) => (
        <button
          key={id}
          role="tab"
          aria-selected={current === id}
          className={current === id ? 'active' : ''}
          onClick={() => {
            const q = new URLSearchParams(params.toString());
            q.set('tab', id);
            q.delete('posting');
            router.replace(`/work?${q}`, { scroll: false });
          }}
        >
          {label}
          {!!counts?.[id] && <span className="tab-count">{counts[id]}</span>}
        </button>
      ))}
    </div>
  );
}

/* ---------------- Workers and agencies ---------------- */

type ApplicantTab = 'applied' | 'offers' | 'active' | 'past';

function ApplicantWork() {
  const { me } = useSession();
  const params = useSearchParams();
  const tab = (params.get('tab') as ApplicantTab) || 'offers';
  const [work, setWork] = useState<WorkView | null>(null);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    try {
      setWork(await market<WorkView>('/work'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  const current: ApplicantTab = ['applied', 'offers', 'active', 'past'].includes(tab)
    ? tab
    : 'offers';
  const list = work?.[current] || [];
  const empty: Record<ApplicantTab, [string, string]> = {
    applied: ['No open applications', 'Contracts that fit you are on Home.'],
    offers: ['No offers yet', 'Contracts that fit you are on Home.'],
    active: [
      'No active contracts',
      'When you accept an offer it shows up here and on your Schedule.',
    ],
    past: ['Nothing here yet', 'Finished contracts and closed applications are kept here.'],
  };
  return (
    <>
      <h1 className="page-title">Work</h1>
      <Tabs<ApplicantTab>
        tabs={[
          ['applied', 'Applied'],
          ['offers', 'Offers & invites'],
          ['active', 'Active'],
          ['past', 'Past'],
        ]}
        current={current}
        counts={{ offers: work?.offers.length, applied: work?.applied.length }}
      />
      {error && <ErrorNote message={error} retry={() => void load()} />}
      {!work && !error && <Skeleton lines={3} />}
      {work && !list.length && (
        <EmptyState
          title={empty[current][0]}
          action={
            current !== 'past' && (
              <Link className="button button-outline" href="/home">
                Go to Home
              </Link>
            )
          }
        >
          {me.mode === 'agency' && current !== 'active'
            ? 'Crew contracts you qualify for are on Home.'
            : empty[current][1]}
        </EmptyState>
      )}
      <ul className="work-list">
        {list.map((a) =>
          current === 'offers' ? (
            <OfferRow key={a.id} application={a} onChange={load} />
          ) : (
            <MyApplicationRow key={a.id} application={a}>
              {current === 'applied' && <ApplicationStatusBlock application={a} onChange={load} />}
              {current === 'active' && a.engagement && (
                <EngagementActions application={a} onChange={load} />
              )}
            </MyApplicationRow>
          ),
        )}
      </ul>
    </>
  );
}

function OfferRow({
  application: a,
  onChange,
}: {
  application: ApplicationView;
  onChange: () => Promise<void>;
}) {
  const p = a.posting;
  return (
    <li className="offer-card">
      <div className="offer-head">
        <Link href={`/postings/${p.id}`} className="work-row-title">
          {p.title}
        </Link>
        <p className="wallet-meta">{p.org.name}</p>
      </div>
      <dl className="offer-terms">
        <div>
          <dt>Dates</dt>
          <dd>{range(p.start_date, p.end_date)}</dd>
        </div>
        <div>
          <dt>Pay</dt>
          <dd>
            {dollars(p.pay_rate_cents)}{' '}
            {p.pay_unit === 'hour' ? 'per hour' : p.pay_unit === 'day' ? 'per day' : 'fixed'}
          </dd>
        </div>
        <div>
          <dt>Site</dt>
          <dd>{p.site_address || p.city}</dd>
        </div>
        <div>
          <dt>Commitment</dt>
          <dd>
            {p.is_exclusive ? 'Full-time, blocks every day' : 'Part-time, scheduled days only'}
          </dd>
        </div>
      </dl>
      <ApplicationStatusBlock
        application={a}
        onChange={onChange}
        acceptSlot={<AcceptOffer application={a} onAccepted={onChange} />}
      />
    </li>
  );
}

/* ---------------- Businesses ---------------- */

type BizTab = 'postings' | 'applicants' | 'active' | 'past';

function BusinessWork() {
  const { me } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const tab = (params.get('tab') as BizTab) || 'postings';
  const [data, setData] = useState<OrgWork | null>(null);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState<PostingCard | 'new' | null>(null);
  const load = useCallback(async () => {
    try {
      setData(await market<OrgWork>('/org/work'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  const current: BizTab = ['postings', 'applicants', 'active', 'past'].includes(tab)
    ? tab
    : 'postings';
  const live = data?.postings.filter((p) => p.status === 'open' || p.status === 'draft') || [];
  const closed = data?.postings.filter((p) => p.status === 'closed' || p.status === 'filled') || [];
  const newCount = data?.postings.reduce((n, p) => n + (p.new_applicants || 0), 0);
  return (
    <>
      <div className="page-head-row">
        <h1 className="page-title">Work</h1>
        <div className="actions">
          {me.planner_persona && (
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
          <button className="button button-primary" onClick={() => setEditing('new')}>
            <Plus size={18} aria-hidden="true" />
            New posting
          </button>
        </div>
      </div>
      <Tabs<BizTab>
        tabs={[
          ['postings', 'Postings'],
          ['applicants', 'Applicants'],
          ['active', 'Active'],
          ['past', 'Past'],
        ]}
        current={current}
        counts={{ applicants: newCount }}
      />
      {error && <ErrorNote message={error} retry={() => void load()} />}
      {!data && !error && <Skeleton lines={3} />}
      {data && current === 'postings' && (
        <>
          {!live.length && (
            <EmptyState
              title="No open postings"
              action={
                <button className="button button-primary" onClick={() => setEditing('new')}>
                  Post a contract
                </button>
              }
            >
              Post a contract and workers who hold the right tickets will see it on their Home.
            </EmptyState>
          )}
          <ul className="work-list">
            {live.map((p) => (
              <PostingRow
                key={p.id}
                posting={p}
                onEdit={() => setEditing(p)}
                onReview={() => router.replace(`/work?tab=applicants&posting=${p.id}`)}
                onChange={load}
              />
            ))}
          </ul>
        </>
      )}
      {data && current === 'applicants' && (
        <ApplicantsTab postings={data.postings} selected={params.get('posting')} onChanged={load} />
      )}
      {data && current === 'active' && (
        <EngagementList
          items={data.active}
          empty="No active contracts yet. Accepted offers show up here."
        />
      )}
      {data && current === 'past' && (
        <>
          <EngagementList items={data.past} empty="Finished contracts appear here." />
          {closed.length > 0 && (
            <ul className="work-list closed-list">
              {closed.map((p) => (
                <li key={p.id} className="work-row">
                  <div className="work-row-main">
                    <Link href={`/postings/${p.id}`} className="work-row-title">
                      {p.title}
                    </Link>
                    <p className="wallet-meta">
                      {range(p.start_date, p.end_date)} · {p.hired || 0} hired
                    </p>
                  </div>
                  <StatusChip status="closed" label={p.status === 'filled' ? 'Filled' : 'Closed'} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {editing && (
        <PostingForm
          posting={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await load();
          }}
        />
      )}
    </>
  );
}

function PostingRow({
  posting: p,
  onEdit,
  onReview,
  onChange,
}: {
  posting: PostingCard;
  onEdit: () => void;
  onReview: () => void;
  onChange: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <li className="work-row posting-row">
      <div className="work-row-main">
        <Link href={`/postings/${p.id}`} className="work-row-title">
          {p.title}
        </Link>
        <p className="wallet-meta">
          {p.posting_type === 'agency' ? 'Crew' : 'Individual'} · {p.city} ·{' '}
          {range(p.start_date, p.end_date)} · {dollars(p.pay_rate_cents)}{' '}
          {p.pay_unit === 'hour' ? 'per hour' : p.pay_unit}
        </p>
        <p className="posting-counts">
          {p.applicants || 0} {p.applicants === 1 ? 'applicant' : 'applicants'}
          {p.new_applicants ? `, ${p.new_applicants} new` : ''} · {p.offers_out || 0} offers out ·{' '}
          {p.hired || 0} of {p.headcount} hired
        </p>
      </div>
      <div className="posting-row-side">
        {p.status === 'draft' && <StatusChip status="self_reported" label="Draft" />}
        <div className="actions">
          <button className="button button-primary button-sm" onClick={onReview}>
            Review applicants
          </button>
          <button className="text-button" onClick={onEdit}>
            {p.status === 'draft' ? 'Edit and publish' : 'Edit'}
          </button>
          <button
            className="text-button"
            disabled={busy}
            onClick={async () => {
              if (!window.confirm(`Close “${p.title}”? It stops taking applications.`)) return;
              setBusy(true);
              try {
                await market(`/postings/${p.id}/close`, { method: 'POST' });
                await onChange();
              } finally {
                setBusy(false);
              }
            }}
          >
            Close
          </button>
        </div>
      </div>
    </li>
  );
}

function ApplicantsTab({
  postings,
  selected,
  onChanged,
}: {
  postings: PostingCard[];
  selected: string | null;
  onChanged: () => void;
}) {
  const router = useRouter();
  const withApplicants = postings.filter((p) => p.status !== 'draft');
  const fallback = [...withApplicants].sort(
    (a, b) => (b.new_applicants || 0) - (a.new_applicants || 0),
  )[0];
  const postingId = selected || fallback?.id || '';
  const [apps, setApps] = useState<ApplicationView[] | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!postingId) return;
    setApps(null);
    market<ApplicationView[]>(`/postings/${postingId}/applicants`).then(
      (a) => {
        setApps(a);
        setError('');
      },
      (e) => setError((e as Error).message),
    );
  }, [postingId]);
  if (!withApplicants.length)
    return (
      <EmptyState title="No postings yet">
        Applicants appear here once you post a contract.
      </EmptyState>
    );
  return (
    <>
      <label className="posting-select">
        Posting
        <select
          value={postingId}
          onChange={(e) => router.replace(`/work?tab=applicants&posting=${e.target.value}`)}
        >
          {withApplicants.map((p) => (
            <option key={p.id} value={p.id}>
              {p.title} ({p.applicants || 0})
            </option>
          ))}
        </select>
      </label>
      {error && <ErrorNote message={error} />}
      {!apps && !error && <Skeleton lines={2} />}
      {apps && !apps.length && (
        <EmptyState title="No applicants yet">
          Workers who hold the required tickets see this posting on their Home.
        </EmptyState>
      )}
      <ul className="work-list">
        {apps?.map((a) => (
          <ApplicantRow key={a.id} application={a} onChanged={onChanged} />
        ))}
      </ul>
    </>
  );
}

function EngagementList({ items, empty }: { items: OrgWork['active']; empty: string }) {
  if (!items.length) return <EmptyState title="Nothing here yet">{empty}</EmptyState>;
  return (
    <ul className="work-list">
      {items.map((e) => (
        <li key={e.engagement.id} className="work-row">
          <div className="work-row-main">
            <Link href={`/postings/${e.posting_id}`} className="work-row-title">
              {e.posting_title}
            </Link>
            <p className="wallet-meta">
              {e.applicant.name} · {range(e.engagement.start_date, e.engagement.end_date)}
            </p>
          </div>
          <StatusChip
            tone={e.engagement.status === 'active' ? 'ok' : 'muted'}
            label={
              e.engagement.status === 'active'
                ? 'Active'
                : e.engagement.status === 'completed'
                  ? 'Completed'
                  : 'Cancelled'
            }
          />
        </li>
      ))}
    </ul>
  );
}
