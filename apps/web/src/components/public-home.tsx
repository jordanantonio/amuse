'use client';

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, CalendarDays, Heart, MapPin, Search, X } from 'lucide-react';
import { api } from '@/lib/market';
import { day, dollars, payUnit, range } from '@/lib/format';
import type { PublicContract, PublicContracts } from '@/lib/public-types';
import { Modal } from '@/components/v1/ui';

const trades = [
  { label: 'Electrical', value: 'Electrical', image: '/work/electrical-site.svg' },
  { label: 'Welding and fabrication', value: 'Welding', image: '/work/welding-bay.svg' },
  { label: 'Heavy equipment', value: 'Heavy equipment', image: '/work/excavator.svg' },
  { label: 'Carpentry', value: 'Carpentry', image: '/work/framing-site.svg' },
  { label: 'Food processing', value: 'Food processing', image: '/work/sanitation-line.svg' },
];
const saveKey = 'shift-public-saved-contracts';
const signIn = (next = '/home') => `/api/v1/auth/google/start?next=${encodeURIComponent(next)}`;
const imageFor = (trade: string) =>
  trades.find((item) => item.value === trade)?.image ||
  (trade === 'Framing' ? '/work/framing-site.svg' : '/work/forklift-dock.svg');

export function PublicHome() {
  const [data, setData] = useState<PublicContracts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [draftQuery, setDraftQuery] = useState('');
  const [query, setQuery] = useState('');
  const [trade, setTrade] = useState('');
  const [retry, setRetry] = useState(0);
  const [saved, setSaved] = useState<string[]>([]);
  const [notice, setNotice] = useState('');
  const [selected, setSelected] = useState<PublicContract | null>(null);
  const [nextPath, setNextPath] = useState('/home');
  const [canPrevious, setCanPrevious] = useState(false);
  const [canNext, setCanNext] = useState(false);
  const rail = useRef<HTMLDivElement>(null);
  const results = useRef<HTMLElement>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const next = params.get('next');
    if (next && next.startsWith('/') && !next.startsWith('//') && !next.includes('\\'))
      setNextPath(next);
    const oauthError = params.get('error');
    if (oauthError === 'google-cancelled')
      setNotice('Google sign-in was cancelled. You can try again when you’re ready.');
    if (oauthError === 'google-not-configured')
      setNotice('Google sign-in is not configured on this server yet.');
    try {
      const stored: unknown = JSON.parse(localStorage.getItem(saveKey) || '[]');
      if (Array.isArray(stored))
        setSaved(stored.filter((value): value is string => typeof value === 'string'));
    } catch {
      /* Browsing works when local storage is unavailable. */
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    const params = new URLSearchParams({ q: query, trade });
    api<PublicContracts>(`/public/contracts?${params}`, { signal: controller.signal })
      .then((response) => {
        if (!controller.signal.aborted) setData(response);
      })
      .catch((failure) => {
        if (!controller.signal.aborted) {
          setData(null);
          setError((failure as Error).message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [query, trade, retry]);

  useEffect(() => {
    const element = rail.current;
    if (!element) return;
    const update = () => {
      setCanPrevious(element.scrollLeft > 2);
      setCanNext(element.scrollLeft + element.clientWidth < element.scrollWidth - 2);
    };
    update();
    element.addEventListener('scroll', update, { passive: true });
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => {
      element.removeEventListener('scroll', update);
      observer.disconnect();
    };
  }, [data, loading]);

  const browse = useCallback((value = '') => {
    setTrade(value);
    setQuery('');
    setDraftQuery('');
    results.current?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'instant'
        : 'smooth',
      block: 'start',
    });
  }, []);

  function search(event: FormEvent) {
    event.preventDefault();
    setQuery(draftQuery.trim());
    setTrade('');
    results.current?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'instant'
        : 'smooth',
      block: 'start',
    });
  }

  function toggleSave(contract: PublicContract) {
    const alreadySaved = saved.includes(contract.id);
    const next = alreadySaved ? saved.filter((id) => id !== contract.id) : [...saved, contract.id];
    try {
      localStorage.setItem(saveKey, JSON.stringify(next));
      setSaved(next);
      setNotice(
        alreadySaved
          ? 'Contract removed from this device’s saved list.'
          : 'Contract saved on this device. Sign in when you’re ready to apply.',
      );
    } catch {
      setNotice(
        'Your browser cannot save contracts on this device. You can still browse and apply after signing in.',
      );
    }
  }

  const filtered = Boolean(query || trade);
  return (
    <div className="public-home">
      <a className="public-skip" href="#open-contracts">
        Skip to contracts
      </a>
      {data?.demo && (
        <div className="public-demo">
          Fictional demo. All companies, people and contracts shown are made up.
        </div>
      )}
      <section className="public-hero" aria-labelledby="public-title">
        <div className="public-hero-art" aria-hidden="true" />
        <div className="public-wrap public-hero-content">
          <header className="public-nav">
            <Link href="/" className="public-wordmark" aria-label="SHIFT public home">
              SHIFT
            </Link>
            <nav aria-label="Main navigation">
              <a
                href="#open-contracts"
                onClick={(event) => {
                  event.preventDefault();
                  browse();
                }}
              >
                Find work
              </a>
              <a href="#for-contractors">Hire a crew</a>
              <a href={signIn('/schedule')}>Schedule</a>
            </nav>
            <a className="public-signin" href={signIn(nextPath)}>
              Sign in
            </a>
          </header>
          <div className="public-hero-copy">
            <h1 id="public-title">Find skilled trades work across Alberta</h1>
            <p>Contracts from Alberta contractors, with pay and dates up front.</p>
            <form className="public-search" onSubmit={search} role="search">
              <Search size={21} aria-hidden="true" />
              <label htmlFor="public-search" className="sr-only">
                Search trades, contracts or cities
              </label>
              <input
                id="public-search"
                maxLength={100}
                value={draftQuery}
                onChange={(event) => setDraftQuery(event.target.value)}
                placeholder="What trade are you looking for?"
              />
              <button type="submit">Search</button>
            </form>
          </div>
        </div>
      </section>

      <main id="public-main">
        <section
          id="open-contracts"
          className="public-wrap public-contracts"
          ref={results}
          aria-labelledby="public-contracts-title"
        >
          <div className="public-section-heading">
            <div>
              <h2 id="public-contracts-title">Open contracts</h2>
              {filtered && (
                <p className="public-filter-note">
                  {query ? `Results for “${query}”` : trade}
                  <button onClick={() => browse()} aria-label="Clear search and trade filter">
                    <X size={14} /> Clear
                  </button>
                </p>
              )}
            </div>
            <div className="public-arrows">
              <button
                aria-label="Previous contracts"
                disabled={loading || !data?.contracts.length || !canPrevious}
                onClick={() =>
                  rail.current?.scrollBy({
                    left: -576,
                    behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
                      ? 'instant'
                      : 'smooth',
                  })
                }
              >
                <ArrowLeft size={18} />
              </button>
              <button
                aria-label="Next contracts"
                disabled={loading || !data?.contracts.length || !canNext}
                onClick={() =>
                  rail.current?.scrollBy({
                    left: 576,
                    behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
                      ? 'instant'
                      : 'smooth',
                  })
                }
              >
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
          <div aria-live="polite" aria-atomic="true" className="public-results-status">
            {loading
              ? 'Loading open contracts…'
              : !error && filtered
                ? `${data?.contracts.length || 0} contracts shown`
                : ''}
          </div>
          {error ? (
            <div className="public-state" role="alert">
              <h3>Contracts couldn’t load</h3>
              <p>{error}</p>
              <button className="public-button secondary" onClick={() => setRetry(retry + 1)}>
                Try again
              </button>
            </div>
          ) : loading ? (
            <div className="public-rail public-loading" aria-busy="true">
              {[0, 1, 2, 3].map((key) => (
                <div className="public-skeleton" key={key}>
                  <div />
                  <span />
                  <span />
                </div>
              ))}
            </div>
          ) : !data?.contracts.length ? (
            <div className="public-state">
              <h3>{filtered ? 'No contracts match this search' : 'No open contracts right now'}</h3>
              <p>
                {filtered
                  ? 'Try a different trade, city or keyword.'
                  : 'Check back soon for new opportunities across Alberta.'}
              </p>
              {filtered && (
                <button className="public-button secondary" onClick={() => browse()}>
                  View all contracts
                </button>
              )}
            </div>
          ) : (
            <div
              className="public-rail"
              ref={rail}
              role="region"
              aria-label="Open contract listings"
              tabIndex={0}
            >
              {data.contracts.map((contract) => (
                <article className="public-contract" key={contract.id}>
                  <button
                    className="public-contract-link"
                    onClick={() => setSelected(contract)}
                    aria-label={`View ${contract.title}`}
                  >
                    <div
                      className={`public-image public-image-${contract.trade.toLowerCase().replace(/[^a-z]+/g, '-')}`}
                    >
                      <img
                        src={imageFor(contract.trade)}
                        alt=""
                        loading="lazy"
                        width={320}
                        height={200}
                      />
                    </div>
                    <h3>{contract.title}</h3>
                    <p className="public-muted">
                      {contract.company} · {contract.city}
                    </p>
                    <p className="public-pay">
                      {dollars(contract.pay_rate_cents)}
                      <span>
                        {contract.pay_unit === 'hour'
                          ? '/hr'
                          : contract.pay_unit === 'day'
                            ? '/day'
                            : ' fixed'}{' '}
                        CAD
                      </span>
                    </p>
                    <p className="public-muted">Starts {day(contract.start_date)}</p>
                  </button>
                  <button
                    className={`public-save ${saved.includes(contract.id) ? 'is-saved' : ''}`}
                    aria-label={`${saved.includes(contract.id) ? 'Unsave' : 'Save'} ${contract.title}`}
                    aria-pressed={saved.includes(contract.id)}
                    onClick={() => toggleSave(contract)}
                  >
                    <Heart size={18} fill={saved.includes(contract.id) ? 'currentColor' : 'none'} />
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="public-wrap public-trades" aria-labelledby="public-trades-title">
          <h2 id="public-trades-title">Browse by trade</h2>
          <div className="public-trade-grid">
            {trades.map((item) => (
              <button
                key={item.value}
                className="public-trade"
                aria-pressed={trade === item.value}
                onClick={() => browse(item.value)}
              >
                <div className="public-image">
                  <img src={item.image} alt="" loading="lazy" width={320} height={200} />
                </div>
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="public-audiences" aria-label="Work with SHIFT">
          <div className="public-wrap public-audience-grid">
            <div>
              <h2>For tradespeople</h2>
              <p>
                Add your certifications and availability once. See contracts that match, with pay
                and dates up front, and accept offers when you’re ready.
              </p>
              <button className="public-button" onClick={() => browse()}>
                Find work <ArrowRight size={17} />
              </button>
            </div>
            <div id="for-contractors">
              <h2>For contractors and crews</h2>
              <p>
                Post a contract, compare applicants side by side, and send offers. Work only shows
                as confirmed after the worker accepts.
              </p>
              <a className="public-button secondary" href={signIn('/work')}>
                Hire a crew <ArrowRight size={17} />
              </a>
            </div>
          </div>
        </section>
      </main>
      <footer className="public-wrap public-footer">
        <span className="public-footer-brand">SHIFT</span>
        <p>
          {data?.demo ? 'Fictional demo prototype. ' : ''}Exact site addresses are shared only with
          offers.
        </p>
        <a href={signIn(nextPath)}>
          Sign in <ArrowRight size={14} />
        </a>
      </footer>
      {notice && (
        <div className="public-toast" role="status">
          <span>{notice}</span>
          <button aria-label="Dismiss message" onClick={() => setNotice('')}>
            <X size={18} />
          </button>
        </div>
      )}
      {selected && (
        <Modal
          title={selected.title}
          description={`${selected.company} · ${selected.city}`}
          onClose={() => setSelected(null)}
        >
          <div className="public-preview">
            <img src={imageFor(selected.trade)} alt="" width={640} height={240} />
            <p className="public-preview-pay">
              {dollars(selected.pay_rate_cents)} <span>{payUnit[selected.pay_unit]} CAD</span>
            </p>
            <p>
              <MapPin size={17} />
              {selected.city} · {selected.trade}
            </p>
            <p>
              <CalendarDays size={17} />
              {range(selected.start_date, selected.end_date)}
            </p>
            <p className="public-preview-note">
              Exact site addresses are shared only with offers. Sign in to check qualifications and
              availability before applying.
            </p>
            <a className="public-button" href={signIn(`/postings/${selected.id}`)}>
              Sign in to view and apply <ArrowRight size={17} />
            </a>
          </div>
        </Modal>
      )}
    </div>
  );
}
