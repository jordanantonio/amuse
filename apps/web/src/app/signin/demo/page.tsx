'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { LoaderCircle } from 'lucide-react';
import { api } from '@/lib/market';
import { PEOPLE } from '@/data/people';
import { Blueprint } from '@/components/v1/blueprint';
import { CompanyBadge, PersonAvatar } from '@/components/v1/avatar';

/** DEMO-1: one card per demo role. Other personas stay in the seed data (DEMO-3). */
const CARDS = [
  { id: 'u-ilya', title: 'I’m looking for work', org: null, industry: null, tag: 'Worker' },
  {
    id: 'u-rahul',
    title: 'I’m hiring',
    org: 'Prairie Harvest Foods',
    industry: 'Food processing',
    tag: 'Hiring business',
  },
  {
    id: 'u-jordan',
    title: 'I run a contracting company',
    org: 'Timberline Framing Crew',
    industry: 'Residential construction',
    tag: 'Contracting company',
  },
] as const;

export default function DemoSignIn() {
  const router = useRouter();
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const signIn = async (body: { user_id?: string; full_name?: string }, key: string) => {
    setBusy(key);
    setError('');
    try {
      const destination = new URLSearchParams(window.location.search).get('next');
      const path = destination
        ? `/auth/demo?next=${encodeURIComponent(destination)}`
        : '/auth/demo';
      const { next } = await api<{ next: string }>(path, { method: 'POST', body });
      router.push(next);
    } catch (e) {
      setError((e as Error).message);
      setBusy('');
    }
  };
  return (
    <div className="landing-page">
      <Blueprint />
      <main className={`demo-picker ${busy ? 'is-leaving' : ''}`}>
        <p className="landing-wordmark">
          shift<span>.</span>
        </p>
        <h1>How do you want to use Shift?</h1>
        {error && (
          <p className="v1-inline-error" role="alert">
            {error}
          </p>
        )}
        <ul className="persona-cards">
          {CARDS.map((c) => {
            const person = PEOPLE[c.id];
            return (
              <li key={c.id}>
                <button
                  className="persona-card"
                  disabled={!!busy}
                  aria-busy={busy === c.id}
                  onClick={() => void signIn({ user_id: c.id }, c.id)}
                >
                  <span className="persona-tag">{c.tag}</span>
                  <PersonAvatar id={c.id} name={person.name} size={88} ring />
                  <strong className="persona-title">{c.title}</strong>
                  <span className="persona-name">{person.name.split(' ')[0]}</span>
                  {c.org ? (
                    <span className="persona-org">
                      <CompanyBadge name={c.org} industry={c.industry} size={28} />
                      {c.org}
                    </span>
                  ) : (
                    <span className="persona-org muted">Independent worker</span>
                  )}
                  {busy === c.id && (
                    <span className="persona-loading">
                      <LoaderCircle size={18} className="spin" aria-hidden="true" />
                      Signing in…
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
        {!creating ? (
          <button className="text-button on-blue" onClick={() => setCreating(true)}>
            or create a new account
          </button>
        ) : (
          <form
            className="demo-new"
            onSubmit={(e) => {
              e.preventDefault();
              void signIn({ full_name: name.trim() }, 'new');
            }}
          >
            <label>
              Your name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={160}
                autoComplete="name"
                autoFocus
              />
            </label>
            <button className="button button-primary" disabled={!!busy || !name.trim()}>
              {busy === 'new' ? 'Creating…' : 'Create account'}
            </button>
          </form>
        )}
        <p className="landing-fine">Demo sign-in. Accounts and data are for demonstration only.</p>
      </main>
    </div>
  );
}
