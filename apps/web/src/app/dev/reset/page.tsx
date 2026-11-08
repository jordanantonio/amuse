'use client';
import { useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/market';

/** SEED-5: rehearsal helper. The API refuses this outside demo mode. */
export default function DevReset() {
  const [state, setState] = useState<'idle' | 'busy' | 'done'>('idle');
  const [error, setError] = useState('');
  return (
    <main className="v1-center">
      <div className="v1-notice">
        <h1>Reset the demo</h1>
        <p className="v1-lede">
          Restores every fictional account, posting, application and ticket to the starting state.
          New demo accounts are removed.
        </p>
        {error && (
          <p className="v1-inline-error" role="alert">
            {error}
          </p>
        )}
        {state === 'done' ? (
          <p>
            Demo restored.{' '}
            <Link className="inline-link" href="/signin/demo">
              Choose an account
            </Link>
          </p>
        ) : (
          <button
            className="button button-primary"
            disabled={state === 'busy'}
            onClick={async () => {
              setState('busy');
              setError('');
              try {
                await api('/dev/reset', { method: 'POST' });
                await api('/auth/signout', { method: 'POST' });
                setState('done');
              } catch (e) {
                setError((e as Error).message);
                setState('idle');
              }
            }}
          >
            {state === 'busy' ? 'Resetting…' : 'Reset demo data'}
          </button>
        )}
      </div>
    </main>
  );
}
