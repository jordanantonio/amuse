'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/market';
import type { DemoAccount } from '@/lib/market-types';

const groups: { title: string; test: (a: DemoAccount) => boolean }[] = [
  { title: 'Workers', test: (a) => a.mode === 'worker' },
  { title: 'Hiring businesses', test: (a) => a.mode === 'business' },
  { title: 'Contracting companies', test: (a) => a.mode === 'agency' },
];

export default function DemoSignIn() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<DemoAccount[] | null>(null);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  useEffect(() => {
    api<DemoAccount[]>('/auth/demo-accounts')
      .then(setAccounts)
      .catch((e) => setError((e as Error).message));
  }, []);
  const signIn = async (body: { user_id?: string; full_name?: string }, key: string) => {
    setBusy(key);
    setError('');
    try {
      const { next } = await api<{ next: string }>('/auth/demo', { method: 'POST', body });
      router.push(next);
    } catch (e) {
      setError((e as Error).message);
      setBusy('');
    }
  };
  return (
    <main className="v1-center">
      <div className="demo-signin">
        <h1>Choose a demo account</h1>
        <p className="v1-lede">
          Google sign-in isn’t set up on this server yet, so this local demo uses fictional
          accounts. Nothing here is real data.
        </p>
        {error && (
          <p className="v1-inline-error" role="alert">
            {error}
          </p>
        )}
        {!accounts && !error && <div className="skeleton-block" aria-label="Loading accounts" />}
        {accounts &&
          groups.map((g) => {
            const list = accounts.filter(g.test);
            if (!list.length) return null;
            return (
              <section key={g.title} className="demo-group">
                <h2>{g.title}</h2>
                <ul>
                  {list.map((a) => (
                    <li key={a.id}>
                      <button
                        className="demo-account"
                        disabled={!!busy}
                        onClick={() => void signIn({ user_id: a.id }, a.id)}
                      >
                        <strong>{a.full_name}</strong>
                        <span>{a.mode === 'worker' ? 'Worker' : a.label}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        <section className="demo-group">
          <h2>Start a new account</h2>
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
              />
            </label>
            <button className="button button-primary" disabled={!!busy || !name.trim()}>
              {busy === 'new' ? 'Creating…' : 'Create account'}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
