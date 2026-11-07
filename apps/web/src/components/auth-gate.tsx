'use client';
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { Button } from './ui/button';
export function AuthGate({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState(!supabase),
    [ready, setReady] = useState(!supabase),
    [email, setEmail] = useState(''),
    [password, setPassword] = useState(''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => {
      setAuthenticated(!!data.session);
      setReady(true);
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setAuthenticated(!!session);
      setReady(true);
    });
    return () => subscription.unsubscribe();
  }, []);
  if (!ready) return <div className="loading-state">Checking your session…</div>;
  if (authenticated) return <>{children}</>;
  return (
    <main className="auth-screen">
      <form
        className="panel auth-card"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError('');
          try {
            const { error } = await supabase!.auth.signInWithPassword({ email, password });
            if (error) throw error;
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="eyebrow">SHIFT / YOUR WORKFORCE, IN SYNC</div>
        <h1>Welcome back.</h1>
        <p>Sign in to your organization’s workspace.</p>
        <label>
          Email
          <input
            type="email"
            required
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        <Button type="submit" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </Button>
        <p className="subtle">
          Access is granted through a company membership; contact your administrator for an
          invitation.
        </p>
      </form>
    </main>
  );
}
