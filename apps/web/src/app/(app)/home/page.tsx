'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  CalendarCheck,
  Inbox,
  Search,
  TriangleAlert,
  UserPlus,
  BadgeCheck,
  MapPin,
} from 'lucide-react';
import { market } from '@/lib/market';
import type { Feed, HomeView, Meta, PostingCard, TalentCard } from '@/lib/market-types';
import { day, dollars, range } from '@/lib/format';
import { useSession } from '@/components/v1/session';
import { ContractCard } from '@/components/v1/contract';
import { ApplySheet } from '@/components/v1/apply-sheet';
import { EmptyState, ErrorNote, Modal, Skeleton } from '@/components/v1/ui';
import { CompanyBadge, PersonAvatar } from '@/components/v1/avatar';

export default function HomePage() {
  const { me } = useSession();
  if (me.mode === 'worker') return <WorkerHome />;
  if (me.mode === 'agency') return <AgencyHome />;
  return <BusinessHome />;
}

function useHome() {
  const [home, setHome] = useState<HomeView | null>(null);
  const load = useCallback(() => market<HomeView>('/home').then(setHome, () => undefined), []);
  useEffect(() => {
    void load();
  }, [load]);
  return { home, reload: load };
}

function Greeting() {
  const { me } = useSession();
  const hour = new Date().getHours();
  const part = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  return (
    <h1 className="page-title">
      {part}, {me.user.full_name.split(' ')[0]}
    </h1>
  );
}

/* ---------------- Worker ---------------- */

type Filters = {
  q: string;
  trade: string;
  max_km: string;
  starts_before: string;
  min_pay: string;
  qualified_only: boolean;
};
const DEFAULT_FILTERS: Filters = {
  q: '',
  trade: '',
  max_km: '',
  starts_before: '',
  min_pay: '',
  qualified_only: true,
};

function WorkerHome() {
  const { home } = useHome();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [feed, setFeed] = useState<Feed | null>(null);
  const [error, setError] = useState('');
  const [applied, setApplied] = useState<Record<string, 'sending' | 'done'>>({});
  const [applyError, setApplyError] = useState('');
  const [applying, setApplying] = useState<PostingCard | null>(null);
  useEffect(() => {
    market<Meta>('/meta').then(setMeta, () => undefined);
  }, []);
  const query = useMemo(() => {
    const q = new URLSearchParams();
    if (filters.q.trim()) q.set('q', filters.q.trim());
    if (filters.trade) q.set('trade', filters.trade);
    if (filters.max_km) q.set('max_km', filters.max_km);
    if (filters.starts_before) q.set('starts_before', filters.starts_before);
    if (filters.min_pay) q.set('min_pay_cents', String(Number(filters.min_pay) * 100));
    q.set('qualified_only', String(filters.qualified_only));
    return q.toString();
  }, [filters]);
  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setFeed(await market<Feed>(`/feed?${query}`, { signal }));
        setError('');
      } catch (e) {
        if ((e as Error).name !== 'AbortError') setError((e as Error).message);
      }
    },
    [query],
  );
  useEffect(() => {
    const controller = new AbortController();
    const id = setTimeout(() => void load(controller.signal), filters.q ? 250 : 0);
    return () => {
      clearTimeout(id);
      controller.abort();
    };
  }, [load, filters.q]);
  const set = (patch: Partial<Filters>) => setFilters((f) => ({ ...f, ...patch }));
  const filtered = JSON.stringify(filters) !== JSON.stringify(DEFAULT_FILTERS);

  const newest = feed?.items.filter((c) => c.is_new && c.eligible).slice(0, 3) || [];

  return (
    <>
      <Greeting />
      {feed && !filtered && feed.new_count > 0 && (
        <section className="new-since" aria-labelledby="new-title">
          <h2 id="new-title">
            {feed.new_count} new {feed.new_count === 1 ? 'contract fits' : 'contracts fit'} you
            since yesterday
          </h2>
          <ul>
            {newest.map((c) => (
              <li key={c.id}>
                <Link href={`/postings/${c.id}`}>
                  <strong>{c.title}</strong>
                  <span>
                    {c.org.name}, {c.city}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
      <TodayStrip home={home} />
      <section className="v1-section" aria-labelledby="foryou-title">
        <div className="v1-section-head">
          <h2 id="foryou-title">For you</h2>
        </div>
        <form className="filters" role="search" onSubmit={(e) => e.preventDefault()}>
          <label className="filter-search">
            <span className="sr-only">Search contracts</span>
            <Search size={18} aria-hidden="true" />
            <input
              type="search"
              placeholder="Search title, company or city"
              value={filters.q}
              onChange={(e) => set({ q: e.target.value })}
            />
          </label>
          <label>
            Trade
            <select value={filters.trade} onChange={(e) => set({ trade: e.target.value })}>
              <option value="">Any trade</option>
              {meta?.trades.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </label>
          <label>
            Distance
            <select value={filters.max_km} onChange={(e) => set({ max_km: e.target.value })}>
              <option value="">Any distance</option>
              {[25, 50, 100, 200].map((k) => (
                <option key={k} value={k}>
                  Within {k} km
                </option>
              ))}
            </select>
          </label>
          <label>
            Starts by
            <input
              type="date"
              value={filters.starts_before}
              onChange={(e) => set({ starts_before: e.target.value })}
            />
          </label>
          <label>
            Pay
            <select value={filters.min_pay} onChange={(e) => set({ min_pay: e.target.value })}>
              <option value="">Any pay</option>
              {[25, 35, 45].map((p) => (
                <option key={p} value={p}>
                  ${p}+ per hour
                </option>
              ))}
            </select>
          </label>
          <label className="toggle">
            <input
              type="checkbox"
              checked={filters.qualified_only}
              onChange={(e) => set({ qualified_only: e.target.checked })}
            />
            Only show ones I qualify for
          </label>
          {filtered && (
            <button
              type="button"
              className="text-button"
              onClick={() => setFilters(DEFAULT_FILTERS)}
            >
              Clear filters
            </button>
          )}
        </form>
        {applyError && <ErrorNote message={applyError} />}
        {error && <ErrorNote message={error} retry={() => void load()} />}
        {!feed && !error && <Skeleton lines={3} />}
        {feed && !feed.items.length && (
          <EmptyState
            title={filtered ? 'No contracts match these filters' : 'No contracts fit you right now'}
            action={
              filtered ? (
                <button
                  className="button button-outline"
                  onClick={() => setFilters(DEFAULT_FILTERS)}
                >
                  Clear filters
                </button>
              ) : (
                <Link className="button button-outline" href="/profile">
                  Add certifications to your wallet
                </Link>
              )
            }
          >
            {filtered
              ? 'Try a wider distance or turn off “Only show ones I qualify for”.'
              : 'New contracts are posted every day. Adding certifications opens up more of them.'}
          </EmptyState>
        )}
        <div className="feed-list">
          {feed?.items.map((c) => (
            <ContractCard
              key={c.id}
              card={c}
              onApply={c.eligible && !applied[c.id] ? () => setApplying(c) : undefined}
              action={
                c.eligible ? (
                  applied[c.id] ? (
                    <Link className="button button-outline applied-state" href="/work">
                      {applied[c.id] === 'sending' ? 'Applying…' : 'Applied, see Work'}
                    </Link>
                  ) : (
                    <button className="button button-primary" onClick={() => setApplying(c)}>
                      Apply
                    </button>
                  )
                ) : (
                  <Link className="button button-outline" href={`/postings/${c.id}`}>
                    See what’s missing
                  </Link>
                )
              }
            />
          ))}
        </div>
      </section>
      {applying && (
        <ApplySheet
          postingId={applying.id}
          onClose={() => setApplying(null)}
          onApplied={() => setApplied((a) => ({ ...a, [applying.id]: 'done' }))}
        />
      )}
    </>
  );
}

function TodayStrip({ home }: { home: HomeView | null }) {
  if (!home) return null;
  const items: React.ReactNode[] = [];
  if (home.next_shift)
    items.push(
      <Link key="next" href="/schedule" className="today-item ok">
        <CalendarCheck size={20} aria-hidden="true" />
        <span>
          <strong>Next: {home.next_shift.posting_title}</strong>
          {home.next_shift.org_name}, {range(home.next_shift.start_date, home.next_shift.end_date)}
        </span>
      </Link>,
    );
  if (home.offers.length)
    items.push(
      <Link key="offers" href="/work?tab=offers" className="today-item warn">
        <Inbox size={20} aria-hidden="true" />
        <span>
          <strong>
            {home.offers.length} {home.offers.length === 1 ? 'offer is' : 'offers are'} waiting for
            your reply
          </strong>
          {home.offers.map((o) => `${o.posting.title} (${o.posting.org.name})`).join(', ')}
        </span>
      </Link>,
    );
  for (const c of home.expiring)
    items.push(
      <Link key={c.id} href="/profile" className="today-item warn">
        <TriangleAlert size={20} aria-hidden="true" />
        <span>
          <strong>
            {c.name} expires {day(c.expires_on!)}
          </strong>
          Renew it to keep qualifying for contracts that need it.
        </span>
      </Link>,
    );
  if (!items.length) return null;
  return (
    <section className="today" aria-label="Today">
      {items}
    </section>
  );
}

/* ---------------- Business ---------------- */

function BusinessHome() {
  const { home } = useHome();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [q, setQ] = useState('');
  const [trade, setTrade] = useState('');
  const [talent, setTalent] = useState<TalentCard[] | null>(null);
  useEffect(() => {
    market<Meta>('/meta').then(setMeta, () => undefined);
  }, []);
  useEffect(() => {
    const params = new URLSearchParams();
    if (q.trim()) params.set('q', q.trim());
    if (trade) params.set('trade', trade);
    const id = setTimeout(
      () => market<TalentCard[]>(`/talent?${params}`).then(setTalent, () => setTalent([])),
      q ? 250 : 0,
    );
    return () => clearTimeout(id);
  }, [q, trade]);
  return (
    <>
      <Greeting />
      {home && (home.new_applicants.length > 0 || home.offers_awaiting > 0) && (
        <section className="today" aria-label="Today">
          {home.new_applicants.length > 0 && (
            <Link href="/work?tab=applicants" className="today-item warn">
              <UserPlus size={20} aria-hidden="true" />
              <span>
                <strong>
                  {home.new_applicants.length} new{' '}
                  {home.new_applicants.length === 1 ? 'applicant' : 'applicants'}
                </strong>
                {home.new_applicants
                  .slice(0, 3)
                  .map((a) => `${a.name} for ${a.posting_title}`)
                  .join(', ')}
              </span>
            </Link>
          )}
          {home.offers_awaiting > 0 && (
            <Link href="/work?tab=applicants" className="today-item">
              <Inbox size={20} aria-hidden="true" />
              <span>
                <strong>
                  {home.offers_awaiting} {home.offers_awaiting === 1 ? 'offer' : 'offers'} awaiting
                  a reply
                </strong>
                Workers see your offer on their Home screen.
              </span>
            </Link>
          )}
        </section>
      )}
      {home && (
        <p className="v1-lede">
          {home.open_postings} open {home.open_postings === 1 ? 'posting' : 'postings'},{' '}
          {home.active_contracts} active {home.active_contracts === 1 ? 'contract' : 'contracts'}.{' '}
          <Link className="inline-link" href="/work">
            Manage postings
          </Link>
        </p>
      )}
      <section className="v1-section" aria-labelledby="talent-title">
        <div className="v1-section-head">
          <h2 id="talent-title">Find workers</h2>
        </div>
        <form className="filters" role="search" onSubmit={(e) => e.preventDefault()}>
          <label className="filter-search">
            <span className="sr-only">Search workers</span>
            <Search size={18} aria-hidden="true" />
            <input
              type="search"
              placeholder="Search name, trade or city"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </label>
          <label>
            Trade
            <select value={trade} onChange={(e) => setTrade(e.target.value)}>
              <option value="">Any trade</option>
              {meta?.trades.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </label>
        </form>
        {!talent && <Skeleton lines={2} />}
        {talent && !talent.length && (
          <EmptyState title="No workers match">Try another trade or a shorter search.</EmptyState>
        )}
        <ul className="talent-list">
          {talent?.map((t) => (
            <li key={t.id} className="talent-row">
              <div className="with-face">
                <PersonAvatar id={t.id} name={t.name} size={52} />
                <div>
                  <strong>{t.name}</strong>
                  <p>{t.headline}</p>
                  <p className="wallet-meta">
                    <MapPin size={15} aria-hidden="true" />
                    {t.city}
                    {t.distance_km != null ? `, ${t.distance_km} km away` : ''}
                  </p>
                </div>
              </div>
              <div className="talent-side">
                <span className="status-chip ok">
                  <BadgeCheck size={15} aria-hidden="true" />
                  {t.verified_tickets} verified {t.verified_tickets === 1 ? 'cert' : 'certs'}
                </span>
                <span className="wallet-meta">{t.trades.join(', ')}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

/* ---------------- Agency ---------------- */

function AgencyHome() {
  const { home, reload } = useHome();
  const [feed, setFeed] = useState<Feed | null>(null);
  const [error, setError] = useState('');
  const [proposing, setProposing] = useState<PostingCard | null>(null);
  const load = useCallback(
    () =>
      market<Feed>('/agency-feed').then(
        (f) => {
          setFeed(f);
          setError('');
        },
        (e) => setError((e as Error).message),
      ),
    [],
  );
  useEffect(() => {
    void load();
  }, [load]);
  return (
    <>
      <Greeting />
      <TodayStrip home={home} />
      <section className="v1-section" aria-labelledby="crew-title">
        <div className="v1-section-head">
          <h2 id="crew-title">Crew contracts you qualify for</h2>
        </div>
        {error && <ErrorNote message={error} retry={() => void load()} />}
        {!feed && !error && <Skeleton lines={2} />}
        {feed && !feed.items.length && (
          <EmptyState
            title="No crew contracts fit your company right now"
            action={
              <Link className="button button-outline" href="/profile">
                Add company credentials
              </Link>
            }
          >
            Contracts that need a crew list company credentials like COR or WCB clearance.
          </EmptyState>
        )}
        <div className="feed-list">
          {feed?.items.map((c) => (
            <ContractCard
              key={c.id}
              card={c}
              action={
                <button className="button button-primary" onClick={() => setProposing(c)}>
                  Send proposal
                </button>
              }
            />
          ))}
        </div>
      </section>
      {proposing && (
        <ProposalDialog
          card={proposing}
          onClose={() => setProposing(null)}
          onSent={async () => {
            setProposing(null);
            await Promise.all([load(), reload()]);
          }}
        />
      )}
    </>
  );
}

function ProposalDialog({
  card,
  onClose,
  onSent,
}: {
  card: PostingCard;
  onClose: () => void;
  onSent: () => Promise<void>;
}) {
  const [crew, setCrew] = useState(String(card.headcount));
  const [rate, setRate] = useState(String(card.pay_rate_cents / 100));
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  return (
    <Modal
      title="Send a proposal"
      description={`${card.title} for ${card.org.name}. The business compares proposals before offering.`}
      onClose={onClose}
      busy={busy}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError('');
          try {
            await market(`/postings/${card.id}/apply`, {
              method: 'POST',
              body: {
                crew_size: Number(crew),
                proposed_rate_cents: Math.round(Number(rate) * 100),
                note,
              },
            });
            await onSent();
          } catch (err) {
            setError((err as Error).message);
            setBusy(false);
          }
        }}
      >
        <div className="editor-fields">
          <div className="field-row">
            <label>
              Crew size you can supply
              <input
                type="number"
                min={1}
                max={500}
                value={crew}
                onChange={(e) => setCrew(e.target.value)}
                required
              />
            </label>
            <label>
              Your rate per worker ({card.pay_unit === 'hour' ? 'per hour' : card.pay_unit})
              <input
                type="number"
                min={1}
                step="0.01"
                value={rate}
                onChange={(e) => setRate(e.target.value)}
                required
              />
            </label>
          </div>
          <label>
            Note <small>(earliest start, equipment, lead hand)</small>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
          </label>
          <p className="wallet-meta">
            They asked for {dollars(card.pay_rate_cents)} with a crew of {card.headcount}.
          </p>
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
            {busy ? 'Sending…' : 'Send proposal'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
