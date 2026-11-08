'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Quote } from 'lucide-react';
import { market } from '@/lib/market';
import type { Me } from '@/lib/market-types';
import { GoogleMark } from '@/components/v1/google-mark';
import { Blueprint } from '@/components/v1/blueprint';
import { PersonAvatar } from '@/components/v1/avatar';
import { TESTIMONIALS } from '@/data/people';

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
    <div className="landing-page">
      <Blueprint parallax />
      <main className="landing">
        <div className="landing-copy">
          <p className="landing-wordmark">
            shift<span>.</span>
          </p>
          <h1>Contract work, made easy.</h1>
          <p className="landing-lede">
            See the jobs you’re qualified and free for. Say yes, and Shift books it.
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
        <section className="testimonials" aria-labelledby="testimonials-title">
          <h2 id="testimonials-title" className="sr-only">
            What people say
          </h2>
          <ul>
            {TESTIMONIALS.map((t) => (
              <li key={t.id} className="testimonial">
                <Quote size={20} aria-hidden="true" className="testimonial-mark" />
                <blockquote>{t.quote}</blockquote>
                <div className="testimonial-who">
                  <PersonAvatar id={t.id} name={t.name} size={48} />
                  <span>
                    <strong>{t.name}</strong>
                    {t.role}
                  </span>
                </div>
              </li>
            ))}
          </ul>
          <p className="testimonials-note">Illustrative feedback from our prototype</p>
        </section>
      </main>
    </div>
  );
}
