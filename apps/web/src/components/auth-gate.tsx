'use client';
import { useEffect, useState, type FormEvent } from 'react';
import type { Session } from '@supabase/supabase-js';
import { authClient } from '@/lib/auth';
import { request } from '@/lib/api';
import type { Identity } from '@/lib/types';
import { Workspace } from './workspace';
import { Button } from './ui/button';

export function AuthGate({ demo }: { demo: boolean }) {
  const [ready, setReady] = useState(false);
  const [configurationError, setConfigurationError] = useState('');
  const [session, setSession] = useState<Session | null>(null);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let alive = true;
    let unsubscribe: (() => void) | undefined;
    fetch('/api/v1/health', { cache: 'no-store' })
      .then(async (response) => {
        if (!response.ok) throw new Error('SHIFT API unavailable.');
        const health = await response.json();
        if (health.demo !== demo)
          throw new Error('Website and API modes do not match. Contact your administrator.');
        if (!alive) return;
        if (demo) {
          setReady(true);
          return;
        }
        const { data } = authClient().auth.onAuthStateChange((_event, next) => {
          if (alive) {
            setSession(next);
            setReady(true);
          }
        });
        unsubscribe = () => data.subscription.unsubscribe();
      })
      .catch((e) => {
        if (alive) {
          setConfigurationError(e.message);
          setReady(true);
        }
      });
    return () => {
      alive = false;
      unsubscribe?.();
    };
  }, [demo]);
  const userId = session?.user.id;
  useEffect(() => {
    let alive = true;
    setIdentity(null);
    if (!userId) return;
    setError('');
    request<Identity>('/me', '')
      .then((me) => {
        if (me.demo) throw new Error('Hosted identity is unavailable. Contact your administrator.');
        if (alive) setIdentity(me);
      })
      .catch((e) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, [userId, attempt]);
  useEffect(() => {
    const expire = () => {
      setIdentity(null);
      setSession(null);
      setError('Session expired. Please sign in again.');
      void authClient().auth.signOut({ scope: 'local' });
    };
    window.addEventListener('shift-session-expired', expire);
    return () => window.removeEventListener('shift-session-expired', expire);
  }, []);
  async function signOut() {
    setBusy(true);
    const { error } = await authClient().auth.signOut({ scope: 'local' });
    setBusy(false);
    if (error) setError(error.message);
    else {
      setSession(null);
      setIdentity(null);
      setError('');
    }
  }
  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError('');
    try {
      const { error } = await authClient().auth.signInWithPassword({
        email: String(form.get('email')),
        password: String(form.get('password')),
      });
      if (error) setError(error.message);
    } catch {
      setError('Could not connect to sign-in. Please try again.');
    } finally {
      setBusy(false);
    }
  }
  if (ready && !configurationError && demo) return <Workspace demo />;
  if (ready && !configurationError && session && identity) {
    return <Workspace key={identity.persona.id} demo={false} onSignOut={signOut} />;
  }
  return (
    <main className="auth-shell">
      <section className="auth-card" aria-busy={busy || !ready}>
        <div className="eyebrow">SHIFT</div>
        <h1>{!ready ? 'Connecting to SHIFT…' : session ? 'Your workspace' : 'Sign in'}</h1>
        {configurationError ? (
          <>
            <p role="alert">{configurationError}</p>
            <Button onClick={() => window.location.reload()}>Retry connection</Button>
          </>
        ) : (
          <>
            {error && <p role="alert">{error}</p>}
            {ready && !session && (
              <form onSubmit={signIn}>
                <label>
                  Email
                  <input name="email" type="email" autoComplete="username" required />
                </label>
                <label>
                  Password
                  <input name="password" type="password" autoComplete="current-password" required />
                </label>
                <Button type="submit" disabled={busy}>
                  {busy ? 'Signing in…' : 'Sign in'}
                </Button>
                <p>Your administrator provides your account and organization access.</p>
              </form>
            )}
            {ready && session && (
              <>
                {!error && <p>Checking organization access…</p>}
                {error && <Button onClick={() => setAttempt(attempt + 1)}>Retry access</Button>}
                <Button variant="outline" disabled={busy} onClick={() => void signOut()}>
                  Sign out
                </Button>
              </>
            )}
          </>
        )}
      </section>
    </main>
  );
}
