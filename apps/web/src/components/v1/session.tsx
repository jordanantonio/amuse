'use client';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { ApiError, api, market } from '@/lib/market';
import type { Me } from '@/lib/market-types';

type Session = { me: Me; refresh: () => Promise<void>; signOut: () => Promise<void> };
const SessionContext = createContext<Session | null>(null);

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error('useSession must be used inside <RequireSession>');
  return session;
}

/** Guards signed-in pages: signed-out visitors go to the landing page (AUTH-3). */
export function RequireSession({
  children,
  fallback,
  allowIncomplete = false,
}: {
  children: React.ReactNode;
  fallback: React.ReactNode;
  allowIncomplete?: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    try {
      const next = await market<Me>('/me');
      setMe(next);
      setError('');
      if (!next.onboarded && !allowIncomplete) router.replace('/onboarding');
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        router.replace(`/?next=${encodeURIComponent(pathname)}`);
      } else setError((e as Error).message);
    }
  }, [router, pathname, allowIncomplete]);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  const signOut = useCallback(async () => {
    await api('/auth/signout', { method: 'POST' });
    router.replace('/');
  }, [router]);
  if (error)
    return (
      <main className="v1-center">
        <div className="v1-notice" role="alert">
          <h1>Shift can’t load your account</h1>
          <p>{error}</p>
          <button className="button button-primary" onClick={() => void refresh()}>
            Try again
          </button>
        </div>
      </main>
    );
  if (!me || (!me.onboarded && !allowIncomplete)) return <>{fallback}</>;
  return (
    <SessionContext.Provider value={{ me, refresh, signOut }}>{children}</SessionContext.Provider>
  );
}
