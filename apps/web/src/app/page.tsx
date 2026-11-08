'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BadgeCheck, MapPin, CalendarRange, CircleCheck } from 'lucide-react';
import { market } from '@/lib/market';
import type { Me } from '@/lib/market-types';
import { GoogleMark } from '@/components/v1/google-mark';

const errors: Record<string, string> = {
  'google-cancelled': 'Google sign-in was cancelled. Try again when you’re ready.',
  'google-not-configured': 'Google sign-in isn’t set up on this server yet.',
};

export default function Landing() {
  const router = useRouter();
  const [next, setNext] = useState('/home');
  const [error, setError] = useState('');
  useEffect(() => {
    const q = new URLSearchParams(location.search);
    setNext(q.get('next') || '/home');
    setError(errors[q.get('error') || ''] || '');
    market<Me>('/me')
      .then((me) => router.replace(me.onboarded ? '/home' : '/onboarding'))
      .catch(() => undefined);
  }, [router]);
  return (
    <main className="landing">
      <div className="landing-copy">
        <p className="landing-wordmark">
          shift<span>.</span>
        </p>
        <h1>Contract work in the trades, matched to the tickets you hold.</h1>
        <p className="landing-lede">
          See the contracts you’re qualified and free for. When you say yes, Shift blocks the dates
          so you never double-book.
        </p>
        {error && (
          <p className="v1-inline-error" role="alert">
            {error}
          </p>
        )}
        <a
          className="google-button"
          href={`/api/v1/auth/google/start?next=${encodeURIComponent(next)}`}
        >
          <GoogleMark />
          Continue with Google
        </a>
        <p className="landing-fine">
          For workers, hiring businesses and contracting crews in Alberta.
        </p>
      </div>
      <aside className="landing-example" aria-label="Example contract">
        <p className="landing-example-label">What a contract looks like on Shift</p>
        <article className="contract-card is-example">
          <div className="contract-card-head">
            <h2>Electrical rough-in, 4-plex</h2>
            <p>
              Northline Homes
              <span className="verified-mark">
                <BadgeCheck size={16} aria-hidden="true" />
                Verified
              </span>
            </p>
          </div>
          <ul className="contract-facts">
            <li>
              <MapPin size={16} aria-hidden="true" />
              Edmonton, 12 km away
            </li>
            <li>
              <CalendarRange size={16} aria-hidden="true" />
              Jan 6 – Jun 30, 6 months
            </li>
          </ul>
          <p className="contract-pay">
            $48 <small>per hour</small>
          </p>
          <p className="match-line ok">
            <CircleCheck size={18} aria-hidden="true" />
            You have 4 of 4 required tickets
          </p>
        </article>
      </aside>
    </main>
  );
}
